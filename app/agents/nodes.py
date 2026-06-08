from __future__ import annotations

import re
from typing import Any, Literal

from app.agents.llm import get_model_client
from app.agents.state import AgentState, HumanQuestion, ToolName
from app.agents.tools import calculate_from_text, inspect_workspace, local_research, search_products

BLOCKED_PATTERNS = [
    "build malware",
    "steal credentials",
    "phishing kit",
    "bypass authentication",
    "delete production database",
]


def intake_node(state: AgentState) -> dict[str, Any]:
    request = state["request"].strip()
    normalized = re.sub(r"\s+", " ", request)
    lowered = normalized.lower()

    if _is_product_search(lowered):
        intent = "product_search"
    elif any(word in lowered for word in ["code", "api", "project", "fastapi", "langgraph"]):
        intent = "software_delivery"
    elif any(word in lowered for word in ["calculate", "sum", "total", "average"]):
        intent = "calculation"
    elif any(word in lowered for word in ["document", "explain", "architecture"]):
        intent = "documentation"
    else:
        intent = "general_assistance"

    return {
        "normalized_request": normalized,
        "intent": intent,
        "trace": _append(state, "trace", f"intake: detected intent '{intent}'"),
    }


def safety_guard_node(state: AgentState) -> dict[str, Any]:
    lowered = state.get("normalized_request", state["request"]).lower()
    matched = next((pattern for pattern in BLOCKED_PATTERNS if pattern in lowered), None)

    if matched:
        return {
            "status": "refused",
            "safety": {
                "allowed": False,
                "reason": f"Request matched blocked pattern: {matched}",
            },
            "trace": _append(state, "trace", "safety_guard: request refused"),
            "route_history": _append(state, "route_history", "safety_guard->finalize"),
        }

    return {
        "status": "ok",
        "safety": {
            "allowed": True,
            "reason": "No blocked pattern detected.",
        },
        "trace": _append(state, "trace", "safety_guard: request allowed"),
        "route_history": _append(state, "route_history", "safety_guard->planner"),
    }


def planner_node(state: AgentState) -> dict[str, Any]:
    request = state.get("normalized_request", state["request"])
    lowered = request.lower()

    plan = [
        "Clarify the user intent and expected deliverable.",
        "Gather supporting context with the minimum required tools.",
        "Draft a practical answer with implementation details.",
        "Critique the draft for completeness and repair it if needed.",
        "Return the final answer with traceable reasoning artifacts.",
    ]

    if "document" in lowered or "documentation" in lowered:
        plan.insert(2, "Prepare documentation that maps files, nodes, and edges.")

    if state.get("intent") == "product_search":
        plan.insert(1, "Ask the human for missing shopping preferences before searching.")
        plan.insert(3, "Filter the sample catalog by budget, product type, and human preferences.")

    pending_tools = _select_tools(lowered)

    return {
        "plan": plan,
        "pending_tools": pending_tools,
        "completed_tools": [],
        "artifacts": {},
        "revision_count": 0,
        "trace": _append(
            state,
            "trace",
            f"planner: created {len(plan)} steps and selected tools {pending_tools or ['none']}",
        ),
    }


def human_clarification_node(state: AgentState) -> dict[str, Any]:
    questions = _build_human_questions(state)

    if questions:
        question_lines = "\n".join(f"- {item['question']}" for item in questions)
        return {
            "status": "needs_input",
            "human_questions": questions,
            "final_answer": "I need a little more information before I continue:\n" + question_lines,
            "trace": _append(
                state,
                "trace",
                f"human_clarification: asking {len(questions)} question(s)",
            ),
            "route_history": _append(state, "route_history", "human_clarification->finalize"),
        }

    artifacts = dict(state.get("artifacts", {}))
    answers = _human_answers(state)
    if answers:
        artifacts["human_input"] = answers

    return {
        "artifacts": artifacts,
        "human_questions": [],
        "trace": _append(state, "trace", "human_clarification: enough context to continue"),
        "route_history": _append(state, "route_history", "human_clarification->tool_router"),
    }


def tool_router_node(state: AgentState) -> dict[str, Any]:
    next_route = route_tools(state)
    return {
        "trace": _append(state, "trace", f"tool_router: next route is '{next_route}'"),
        "route_history": _append(state, "route_history", f"tool_router->{next_route}"),
    }


def research_tool_node(state: AgentState) -> dict[str, Any]:
    query = state.get("normalized_request", state["request"])
    artifacts = dict(state.get("artifacts", {}))
    artifacts["research"] = local_research(query)

    return {
        "artifacts": artifacts,
        "pending_tools": _remove_current_tool(state, "research"),
        "completed_tools": _append(state, "completed_tools", "research"),
        "trace": _append(state, "trace", "research_tool: gathered local knowledge"),
    }


def calculator_tool_node(state: AgentState) -> dict[str, Any]:
    query = state.get("normalized_request", state["request"])
    artifacts = dict(state.get("artifacts", {}))
    artifacts["calculation"] = calculate_from_text(query)

    return {
        "artifacts": artifacts,
        "pending_tools": _remove_current_tool(state, "calculator"),
        "completed_tools": _append(state, "completed_tools", "calculator"),
        "trace": _append(state, "trace", "calculator_tool: evaluated arithmetic if present"),
    }


def code_tool_node(state: AgentState) -> dict[str, Any]:
    artifacts = dict(state.get("artifacts", {}))
    artifacts["code"] = inspect_workspace()

    return {
        "artifacts": artifacts,
        "pending_tools": _remove_current_tool(state, "code"),
        "completed_tools": _append(state, "completed_tools", "code"),
        "trace": _append(state, "trace", "code_tool: inspected workspace structure"),
    }


def product_tool_node(state: AgentState) -> dict[str, Any]:
    query = state.get("normalized_request", state["request"])
    artifacts = dict(state.get("artifacts", {}))
    artifacts["products"] = search_products(query, state.get("context", {}))

    return {
        "artifacts": artifacts,
        "pending_tools": _remove_current_tool(state, "product"),
        "completed_tools": _append(state, "completed_tools", "product"),
        "trace": _append(state, "trace", "product_tool: searched sample product catalog"),
    }


def synthesize_node(state: AgentState) -> dict[str, Any]:
    fallback = _local_draft(state)
    client = get_model_client()

    if client.source == "local":
        draft = fallback
    else:
        try:
            draft = client.generate(
                system_prompt=(
                    "You are a senior AI delivery agent. Produce a concise, practical "
                    "answer using the supplied plan and tool artifacts."
                ),
                user_prompt=(
                    f"User request:\n{state.get('normalized_request', state['request'])}\n\n"
                    f"Plan:\n{state.get('plan', [])}\n\n"
                    f"Artifacts:\n{state.get('artifacts', {})}\n\n"
                    "Write the best possible response."
                ),
            )
        except Exception:
            draft = fallback

    return {
        "draft": draft,
        "trace": _append(state, "trace", f"synthesize: generated draft with {client.source} model"),
    }


def critic_node(state: AgentState) -> dict[str, Any]:
    draft = state.get("draft", "")
    artifacts = state.get("artifacts", {})
    issues: list[str] = []

    if len(draft.strip()) < 300:
        issues.append("Draft is too short for a complex delivery request.")
    if "Plan" not in draft:
        issues.append("Draft should expose the plan.")
    if artifacts and "Tool findings" not in draft:
        issues.append("Draft should summarize tool findings.")
    if state.get("intent") == "software_delivery" and "FastAPI" not in draft:
        issues.append("Software delivery answer should mention FastAPI.")
    if "LangGraph" not in draft:
        issues.append("Answer should explicitly mention LangGraph.")

    score = max(0, 10 - (2 * len(issues)))
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)
    needs_revision = bool(issues) and revision_count < max_revisions

    return {
        "critique": {
            "score": score,
            "issues": issues,
            "needs_revision": needs_revision,
        },
        "trace": _append(
            state,
            "trace",
            f"critic: score={score}, needs_revision={needs_revision}",
        ),
        "route_history": _append(
            state,
            "route_history",
            "critic->repair" if needs_revision else "critic->finalize",
        ),
    }


def repair_node(state: AgentState) -> dict[str, Any]:
    issues = state.get("critique", {}).get("issues", [])
    repaired = state.get("draft", "").rstrip()

    if issues:
        repaired += "\n\nRepair notes:\n"
        repaired += "\n".join(f"- Addressed: {issue}" for issue in issues)

    if "Tool findings" not in repaired:
        repaired += "\n\nTool findings:\n" + _format_artifacts(state.get("artifacts", {}))

    if "Plan" not in repaired:
        repaired += "\n\nPlan:\n" + _format_plan(state.get("plan", []))

    if "FastAPI" not in repaired:
        repaired += "\n\nFastAPI integration: expose the compiled graph through typed HTTP endpoints."

    if "LangGraph" not in repaired:
        repaired += "\n\nLangGraph integration: model each step as a stateful node connected by edges."

    return {
        "draft": repaired,
        "revision_count": state.get("revision_count", 0) + 1,
        "trace": _append(state, "trace", "repair: improved draft from critique"),
    }


def finalize_node(state: AgentState) -> dict[str, Any]:
    safety = state.get("safety", {"allowed": True})

    if state.get("status") == "needs_input":
        return {
            "final_answer": state.get("final_answer", "The agent needs more human input."),
            "status": "needs_input",
            "trace": _append(state, "trace", "finalize: waiting for human input"),
        }

    if not safety.get("allowed", True):
        answer = (
            "I cannot help with that request because it matches a blocked safety pattern. "
            f"Reason: {safety.get('reason', 'Not allowed.')}"
        )
        return {
            "final_answer": answer,
            "status": "refused",
            "trace": _append(state, "trace", "finalize: returned refusal"),
        }

    answer = state.get("draft", "").strip()
    if not answer:
        answer = "The agent completed, but no draft was produced."

    return {
        "final_answer": answer,
        "status": "ok",
        "trace": _append(state, "trace", "finalize: completed response"),
    }


def route_after_safety(state: AgentState) -> Literal["refuse", "plan"]:
    if not state.get("safety", {}).get("allowed", True):
        return "refuse"
    return "plan"


def route_after_human_clarification(state: AgentState) -> Literal["ask_human", "continue"]:
    if state.get("status") == "needs_input":
        return "ask_human"
    return "continue"


def route_tools(state: AgentState) -> Literal["research", "calculator", "code", "product", "synthesize"]:
    pending = state.get("pending_tools", [])
    if not pending:
        return "synthesize"
    return pending[0]


def route_after_critic(state: AgentState) -> Literal["repair", "finalize"]:
    if state.get("critique", {}).get("needs_revision", False):
        return "repair"
    return "finalize"


def _select_tools(lowered_request: str) -> list[ToolName]:
    tools: list[ToolName] = []

    if _is_product_search(lowered_request):
        tools.append("product")
    if any(
        word in lowered_request
        for word in ["document", "docs", "explain", "architecture", "agent", "node", "edge", "workflow"]
    ):
        tools.append("research")
    if any(word in lowered_request for word in ["calculate", "sum", "total", "average"]) or re.search(
        r"\d+\s*[+\-*/]\s*\d+",
        lowered_request,
    ):
        tools.append("calculator")
    if any(word in lowered_request for word in ["code", "api", "project", "fastapi", "langgraph", "file"]):
        tools.append("code")

    return tools


def _build_human_questions(state: AgentState) -> list[HumanQuestion]:
    if state.get("intent") != "product_search":
        return []

    request = state.get("normalized_request", state["request"]).lower()
    answers = _human_answers(state)
    questions: list[HumanQuestion] = []

    if not answers.get("product_type") and not _request_mentions_product_type(request):
        questions.append(
            {
                "id": "product_type",
                "question": "What product type should I search for?",
                "type": "text",
                "options": [],
                "required": True,
            }
        )

    if not answers.get("color") and not _request_mentions_color(request):
        questions.append(
            {
                "id": "color",
                "question": "Which color do you want?",
                "type": "choice",
                "options": ["black", "white", "blue", "green", "any"],
                "required": True,
            }
        )

    if _request_mentions_budget(request) and not answers.get("strict_budget"):
        questions.append(
            {
                "id": "strict_budget",
                "question": "Should I only show products under the stated budget?",
                "type": "yes_no",
                "options": ["yes", "no"],
                "required": True,
            }
        )

    return questions


def _human_answers(state: AgentState) -> dict[str, Any]:
    raw_answers = state.get("context", {}).get("human_answers", {})
    if not isinstance(raw_answers, dict):
        return {}
    return {str(key): value for key, value in raw_answers.items() if value not in ("", None)}


def _remove_current_tool(state: AgentState, tool: ToolName) -> list[ToolName]:
    pending = list(state.get("pending_tools", []))
    if pending and pending[0] == tool:
        return pending[1:]
    return [item for item in pending if item != tool]


def _append(state: AgentState, key: str, value: Any) -> list[Any]:
    values = list(state.get(key, []))
    values.append(value)
    return values


def _local_draft(state: AgentState) -> str:
    request = state.get("normalized_request", state["request"])
    product_artifact = state.get("artifacts", {}).get("products")
    product_section = _format_product_recommendations(product_artifact)
    recommendation = _format_recommended_answer(state, product_artifact)
    return "\n\n".join(
        [
            "Summary:\n"
            f"I treated the request as a {state.get('intent', 'general')} task and ran a "
            "LangGraph workflow that plans, can ask for human input, uses tools, drafts, "
            "critiques, and finalizes.",
            "User request:\n" + request,
            "Plan:\n" + _format_plan(state.get("plan", [])),
            "Tool findings:\n" + _format_artifacts(state.get("artifacts", {})),
            product_section,
            "Recommended answer:\n" + recommendation,
        ]
    )


def _format_plan(plan: list[str]) -> str:
    if not plan:
        return "- No explicit plan was generated."
    return "\n".join(f"- {step}" for step in plan)


def _format_artifacts(artifacts: dict[str, Any]) -> str:
    if not artifacts:
        return "- No tool artifacts were required."

    lines: list[str] = []
    for name, value in artifacts.items():
        lines.append(f"- {name}: {value}")
    return "\n".join(lines)


def _format_product_recommendations(product_artifact: Any) -> str:
    if not isinstance(product_artifact, dict):
        return "Product recommendations:\n- No product search was requested."

    filters = product_artifact.get("applied_filters", {})
    matches = product_artifact.get("matches", [])
    alternatives = product_artifact.get("alternatives", [])
    filter_line = (
        "Applied filters: product_type={product_type}, color={color}, budget=${budget:.2f}, "
        "strict_budget={strict_budget}".format(
            product_type=filters.get("product_type", "any"),
            color=filters.get("color", "any"),
            budget=float(filters.get("budget", 50.0)),
            strict_budget=filters.get("strict_budget", True),
        )
    )

    if not matches:
        if not alternatives:
            return (
                "Product recommendations:\n"
                f"- {filter_line}\n"
                "- No exact sample-catalog match was found. Try changing color, product type, or budget."
            )
        return "Product recommendations:\n" + "\n".join(
            [
                f"- {filter_line}",
                "- No exact match was found, so these relaxed alternatives are shown:",
                *_format_product_lines(alternatives),
            ]
        )

    lines = [f"- {filter_line}", *_format_product_lines(matches)]
    if alternatives:
        lines.append("- Other close alternatives:")
        lines.extend(_format_product_lines(alternatives))
    return "Product recommendations:\n" + "\n".join(lines)


def _format_recommended_answer(state: AgentState, product_artifact: Any) -> str:
    if state.get("intent") == "product_search" and isinstance(product_artifact, dict):
        products = product_artifact.get("matches", []) or product_artifact.get("alternatives", [])
        if products:
            first = products[0]
            budget_note = (
                " It is over the stated budget, but you allowed flexible budget results."
                if first.get("over_budget")
                else ""
            )
            return (
                "I recommend {name} because it matches the human preferences and stays "
                "closest to the ${budget:.2f} budget.{budget_note}".format(
                    name=first["name"],
                    budget=product_artifact.get("budget", 50.0),
                    budget_note=budget_note,
                )
            )
        return "I could not find a matching product in the sample catalog with the current constraints."

    return (
        "Build the FastAPI service around the compiled LangGraph agent. Keep node logic "
        "small and testable, keep graph wiring centralized, and document every dynamic "
        "route so future maintainers can see why the agent moved from one node to the next."
    )


def _format_product_lines(products: list[dict[str, Any]]) -> list[str]:
    lines = []
    for product in products:
        budget_marker = "over budget" if product.get("over_budget") else "within budget"
        fallback = f", {product['fallback_reason']}" if product.get("fallback_reason") else ""
        lines.append(
            "- {name} (${price:.2f}, {color}, {budget_marker}{fallback}): {reason}".format(
                name=product["name"],
                price=product["price"],
                color=product["color"],
                budget_marker=budget_marker,
                fallback=fallback,
                reason=product["reason"],
            )
        )
    return lines


def _is_product_search(lowered_request: str) -> bool:
    shopping_words = ["find", "buy", "shop", "search", "recommend", "product", "item"]
    budget_words = ["under", "below", "less than", "$", "dollar", "budget"]
    return any(word in lowered_request for word in shopping_words) and any(
        word in lowered_request for word in budget_words
    )


def _request_mentions_product_type(lowered_request: str) -> bool:
    product_words = [
        "mouse",
        "speaker",
        "earbuds",
        "headphone",
        "headphones",
        "lamp",
        "bottle",
        "backpack",
        "bag",
    ]
    return any(word in lowered_request for word in product_words)


def _request_mentions_color(lowered_request: str) -> bool:
    colors = ["black", "white", "blue", "green", "red", "yellow", "gray", "grey", "any color"]
    return any(color in lowered_request for color in colors)


def _request_mentions_budget(lowered_request: str) -> bool:
    return bool(re.search(r"(?:under|below|less than|budget|[$])\s*\$?\s*\d+", lowered_request))
