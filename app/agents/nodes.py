from __future__ import annotations

import re
from typing import Any, Literal

from app.agents.commerce import get_order_gateway
from app.agents.llm import get_model_client
from app.agents.product_model import (
    ModelConfigurationError,
    ModelExecutionError,
    ProductRequestAnalysis,
    get_product_model,
)
from app.agents.state import AgentState, HumanQuestion, ToolName
from app.agents.tools import calculate_from_text, inspect_workspace, local_research

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
    return {
        "normalized_request": normalized,
        "trace": _append(state, "trace", "intake: normalized request"),
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
        "route_history": _append(state, "route_history", "safety_guard->model_analyzer"),
    }


def model_analyzer_node(state: AgentState) -> dict[str, Any]:
    query = state.get("normalized_request", state["request"])
    try:
        model = get_product_model()
        analysis = model.analyze_request(query, _model_context(state))
    except (ModelConfigurationError, ModelExecutionError) as exc:
        message = str(exc)
        return {
            "status": "error",
            "model_error": message,
            "trace": _append(state, "trace", f"model_analyzer: {message}"),
            "route_history": _append(state, "route_history", "model_analyzer->finalize"),
        }

    return {
        "intent": analysis.intent,
        "normalized_request": analysis.normalized_request,
        "model_analysis": analysis.model_dump(),
        "model_used": model.model_name,
        "trace": _append(
            state,
            "trace",
            f"model_analyzer: detected intent '{analysis.intent}' with {model.model_name}",
        ),
        "route_history": _append(state, "route_history", "model_analyzer->planner"),
    }


def planner_node(state: AgentState) -> dict[str, Any]:
    intent = state.get("intent", "general_assistance")
    plan = [
        "Use the model analysis as the structured source of request intent.",
        "Gather supporting context with the minimum required tools.",
        "Draft a practical answer from the model and tool artifacts.",
        "Critique the draft and repair it when needed.",
        "Return the final answer with traceable graph state.",
    ]

    if intent == "product_search":
        plan = [
            "Analyze the shopping request and merge previous human answers.",
            "Ask the human only for important missing preferences.",
            "Ask for size when the selected product requires it.",
            "Use the model and optional web search to find matching products.",
            "Return sourced recommendations and verification caveats.",
        ]
    elif intent == "add_to_cart":
        plan = [
            "Resolve the selected product and requested variant.",
            "Ask for any required size, color, or quantity.",
            "Add the confirmed item to the current cart.",
            "Return the updated cart for the next API call.",
        ]
    elif intent == "checkout":
        plan = [
            "Read the current cart and collect required shipping details.",
            "Ask for explicit final order confirmation.",
            "Place the order only after the user answers yes.",
            "Return an order receipt and clear the completed cart.",
        ]
    elif intent == "documentation":
        plan.insert(2, "Map the relevant files, nodes, edges, and API behavior.")

    pending_tools = _select_tools(intent)

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
    questions = [
        question
        for question in _model_questions(state)
        if question.get("id") != "size"
    ]

    if questions:
        return _human_input_update(
            state,
            questions,
            "I need a little more information before I continue:",
            "human_clarification",
        )

    artifacts = dict(state.get("artifacts", {}))
    answers = _human_answers(state)
    if answers:
        artifacts["human_input"] = answers

    return {
        "artifacts": artifacts,
        "human_questions": [],
        "trace": _append(state, "trace", "human_clarification: enough context to continue"),
        "route_history": _append(
            state,
            "route_history",
            "human_clarification->product_size_clarification",
        ),
    }


def product_size_clarification_node(state: AgentState) -> dict[str, Any]:
    questions = [
        question
        for question in _model_questions(state)
        if question.get("id") == "size"
    ]

    if questions:
        return _human_input_update(
            state,
            questions,
            "I need size information before I continue:",
            "product_size_clarification",
        )

    return {
        "trace": _append(state, "trace", "product_size_clarification: size context is complete"),
        "route_history": _append(
            state,
            "route_history",
            "product_size_clarification->tool_router",
        ),
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

    try:
        analysis = ProductRequestAnalysis.model_validate(state.get("model_analysis", {}))
        model = get_product_model()
        result = model.recommend_products(query, analysis)
    except (ModelConfigurationError, ModelExecutionError, ValueError) as exc:
        message = str(exc)
        return {
            "status": "error",
            "model_error": message,
            "pending_tools": _remove_current_tool(state, "product"),
            "trace": _append(state, "trace", f"product_tool: {message}"),
            "route_history": _append(state, "route_history", "product_tool->finalize"),
        }

    artifacts["products"] = result.model_dump()
    return {
        "artifacts": artifacts,
        "pending_tools": _remove_current_tool(state, "product"),
        "completed_tools": _append(state, "completed_tools", "product"),
        "trace": _append(
            state,
            "trace",
            f"product_tool: generated recommendations with {model.model_name}",
        ),
    }


def cart_tool_node(state: AgentState) -> dict[str, Any]:
    artifacts = dict(state.get("artifacts", {}))
    analysis = ProductRequestAnalysis.model_validate(state.get("model_analysis", {}))

    if not analysis.product_name:
        return _commerce_error(state, "cart", "A product name is required before adding to cart.")

    cart = _current_cart(state)
    items = list(cart.get("items", []))
    item = _cart_item_from_analysis(analysis)
    matching_item = next(
        (
            existing
            for existing in items
            if _cart_item_key(existing) == _cart_item_key(item)
        ),
        None,
    )
    if matching_item:
        matching_item["quantity"] = int(matching_item.get("quantity", 1)) + item["quantity"]
        if matching_item.get("unit_price") is not None:
            matching_item["line_total"] = round(
                matching_item["unit_price"] * matching_item["quantity"],
                2,
            )
    else:
        items.append(item)

    updated_cart = _summarize_cart(items)
    artifacts["cart"] = updated_cart
    return {
        "artifacts": artifacts,
        "pending_tools": _remove_current_tool(state, "cart"),
        "completed_tools": _append(state, "completed_tools", "cart"),
        "trace": _append(
            state,
            "trace",
            f"cart_tool: added {item['quantity']} x {item['name']}",
        ),
    }


def checkout_tool_node(state: AgentState) -> dict[str, Any]:
    artifacts = dict(state.get("artifacts", {}))
    analysis = ProductRequestAnalysis.model_validate(state.get("model_analysis", {}))
    cart = _current_cart(state)

    if not cart.get("items") and analysis.product_name:
        cart = _summarize_cart([_cart_item_from_analysis(analysis)])

    if not cart.get("items"):
        return _commerce_error(state, "checkout", "The cart is empty.")

    if analysis.order_confirmed is False:
        artifacts["cart"] = cart
        artifacts["order"] = {
            "status": "cancelled",
            "mode": "demo",
            "message": "The order was not placed because the user answered no.",
        }
        return {
            "artifacts": artifacts,
            "pending_tools": _remove_current_tool(state, "checkout"),
            "completed_tools": _append(state, "completed_tools", "checkout"),
            "trace": _append(state, "trace", "checkout_tool: order cancelled by user"),
        }

    if analysis.order_confirmed is not True:
        return _commerce_error(
            state,
            "checkout",
            "Explicit confirm_order=yes is required before placing an order.",
        )

    shipping = _shipping_from_analysis(analysis)
    missing = [name for name, value in shipping.items() if not value]
    if missing:
        return _commerce_error(
            state,
            "checkout",
            f"Missing checkout fields: {', '.join(missing)}.",
        )

    gateway = get_order_gateway()
    artifacts["order"] = gateway.place_order(cart, shipping)
    artifacts["cart"] = _summarize_cart([])
    return {
        "artifacts": artifacts,
        "pending_tools": _remove_current_tool(state, "checkout"),
        "completed_tools": _append(state, "completed_tools", "checkout"),
        "trace": _append(
            state,
            "trace",
            f"checkout_tool: placed confirmed {gateway.mode} order",
        ),
    }


def synthesize_node(state: AgentState) -> dict[str, Any]:
    fallback = _local_draft(state)

    if state.get("intent") in {"product_search", "add_to_cart", "checkout"}:
        return {
            "draft": fallback,
            "trace": _append(
                state,
                "trace",
                "synthesize: formatted structured commerce results",
            ),
        }

    client = get_model_client()
    if client.source == "local":
        draft = fallback
    else:
        try:
            draft = client.generate(
                system_prompt=_synthesis_system_prompt(state),
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

    intent = state.get("intent")
    if intent == "product_search":
        products = artifacts.get("products", {})
        if len(draft.strip()) < 100:
            issues.append("Product answer is too short to explain the recommendations.")
        if not products.get("matches") and not products.get("alternatives"):
            issues.append("Product answer has no model-generated recommendations.")
        if products.get("search_used") and "http" not in draft:
            issues.append("Live product recommendations should include source links.")
    elif intent == "general_assistance":
        if len(draft.strip()) < 10:
            issues.append("Conversational answer is too short to be helpful.")
    elif intent == "add_to_cart":
        if not artifacts.get("cart", {}).get("items"):
            issues.append("Cart response should contain the selected item.")
    elif intent == "checkout":
        if not artifacts.get("order"):
            issues.append("Checkout response should contain an order result.")
    else:
        if len(draft.strip()) < 300:
            issues.append("Draft is too short for a complex delivery request.")
        if "Plan" not in draft:
            issues.append("Draft should expose the plan.")
        if artifacts and "Tool findings" not in draft:
            issues.append("Draft should summarize tool findings.")
        if state.get("intent") == "software_delivery" and "FastAPI" not in draft:
            issues.append("Software delivery answer should mention FastAPI.")
        if state.get("intent") in {"software_delivery", "documentation"} and "LangGraph" not in draft:
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
        repaired += "\n\nAdditional checks:\n"
        repaired += "\n".join(f"- {issue}" for issue in issues)

    if state.get("intent") not in {
        "product_search",
        "add_to_cart",
        "checkout",
        "general_assistance",
    }:
        if "Tool findings" not in repaired:
            repaired += "\n\nTool findings:\n" + _format_artifacts(state.get("artifacts", {}))
        if "Plan" not in repaired:
            repaired += "\n\nPlan:\n" + _format_plan(state.get("plan", []))
        if state.get("intent") == "software_delivery" and "FastAPI" not in repaired:
            repaired += "\n\nFastAPI integration: expose the compiled graph through typed HTTP endpoints."
        if state.get("intent") in {"software_delivery", "documentation"} and "LangGraph" not in repaired:
            repaired += "\n\nLangGraph integration: connect stateful nodes with explicit edges."

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

    if state.get("status") == "error":
        return {
            "final_answer": (
                "The model-backed agent could not complete this request. "
                f"{state.get('model_error', 'Check the model configuration and try again.')}"
            ),
            "status": "error",
            "trace": _append(state, "trace", "finalize: returned model error"),
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


def route_after_safety(state: AgentState) -> Literal["refuse", "analyze"]:
    if not state.get("safety", {}).get("allowed", True):
        return "refuse"
    return "analyze"


def route_after_model_analysis(state: AgentState) -> Literal["error", "plan"]:
    if state.get("status") == "error":
        return "error"
    return "plan"


def route_after_human_clarification(state: AgentState) -> Literal["ask_human", "continue"]:
    if state.get("status") == "needs_input":
        return "ask_human"
    return "continue"


def route_after_product_size_clarification(state: AgentState) -> Literal["ask_human", "continue"]:
    if state.get("status") == "needs_input":
        return "ask_human"
    return "continue"


def route_after_action_tool(state: AgentState) -> Literal["error", "continue"]:
    if state.get("status") == "error":
        return "error"
    return "continue"


def route_tools(
    state: AgentState,
) -> Literal["research", "calculator", "code", "product", "cart", "checkout", "synthesize"]:
    pending = state.get("pending_tools", [])
    if not pending:
        return "synthesize"
    return pending[0]


def route_after_critic(state: AgentState) -> Literal["repair", "finalize"]:
    if state.get("critique", {}).get("needs_revision", False):
        return "repair"
    return "finalize"


def _select_tools(intent: str) -> list[ToolName]:
    by_intent: dict[str, list[ToolName]] = {
        "product_search": ["product"],
        "add_to_cart": ["cart"],
        "checkout": ["checkout"],
        "calculation": ["calculator"],
        "software_delivery": ["research", "code"],
        "documentation": ["research", "code"],
        "general_assistance": [],
    }
    return list(by_intent.get(intent, []))


def _model_questions(state: AgentState) -> list[HumanQuestion]:
    if state.get("intent") not in {"product_search", "add_to_cart", "checkout"}:
        return []

    raw_questions = state.get("model_analysis", {}).get("questions", [])
    questions: list[HumanQuestion] = []
    for raw in raw_questions:
        if not isinstance(raw, dict):
            continue
        question: HumanQuestion = {
            "id": str(raw.get("id", "")).strip(),
            "question": str(raw.get("question", "")).strip(),
            "type": raw.get("type", "text"),
            "options": [str(option) for option in raw.get("options", [])],
            "required": bool(raw.get("required", True)),
        }
        if question["id"] and question["question"]:
            questions.append(question)
    return questions


def _human_input_update(
    state: AgentState,
    questions: list[HumanQuestion],
    heading: str,
    node_name: str,
) -> dict[str, Any]:
    question_lines = "\n".join(f"- {item['question']}" for item in questions)
    return {
        "status": "needs_input",
        "human_questions": questions,
        "final_answer": f"{heading}\n{question_lines}",
        "trace": _append(
            state,
            "trace",
            f"{node_name}: asking {len(questions)} question(s)",
        ),
        "route_history": _append(state, "route_history", f"{node_name}->finalize"),
    }


def _human_answers(state: AgentState) -> dict[str, Any]:
    raw_answers = state.get("context", {}).get("human_answers", {})
    if not isinstance(raw_answers, dict):
        return {}
    return {str(key): value for key, value in raw_answers.items() if value not in ("", None)}


def _model_context(state: AgentState) -> dict[str, Any]:
    context = state.get("context", {})
    return {
        "human_answers": _human_answers(state),
        "cart": context.get("cart", {}),
        "previous_products": context.get("previous_products", {}),
    }


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
    intent = state.get("intent")
    if intent == "product_search":
        return _format_product_recommendations(state.get("artifacts", {}).get("products"))
    if intent == "add_to_cart":
        return _format_cart(state.get("artifacts", {}).get("cart"))
    if intent == "checkout":
        return _format_order(state.get("artifacts", {}).get("order"))
    if intent == "general_assistance":
        return (
            "Hi! I'm doing well, thanks for asking. Is there a product you would "
            "like me to help you find, or is there anything else I can help you with?"
        )

    request = state.get("normalized_request", state["request"])
    return "\n\n".join(
        [
            "Summary:\n"
            f"I treated the request as a {state.get('intent', 'general')} task and ran a "
            "LangGraph workflow that plans, can ask for human input, uses tools, drafts, "
            "critiques, and finalizes.",
            "User request:\n" + request,
            "Plan:\n" + _format_plan(state.get("plan", [])),
            "Tool findings:\n" + _format_artifacts(state.get("artifacts", {})),
            "Recommended answer:\n"
            "Build the FastAPI service around the compiled LangGraph agent. Keep node "
            "logic small and testable, graph wiring centralized, and dynamic routes documented.",
        ]
    )


def _synthesis_system_prompt(state: AgentState) -> str:
    if state.get("intent") == "general_assistance":
        return (
            "You are a warm, natural shopping assistant. Reply personally and directly "
            "to casual conversation. For a greeting or 'how are you' message, answer in "
            "one or two friendly sentences, then gently ask whether the user wants help "
            "finding a product or needs help with anything else. Do not mention plans, "
            "tools, artifacts, intent labels, APIs, or LangGraph."
        )

    return (
        "You are a senior AI delivery agent. Produce a concise, practical answer "
        "using the supplied plan and tool artifacts."
    )


def _format_plan(plan: list[str]) -> str:
    if not plan:
        return "- No explicit plan was generated."
    return "\n".join(f"- {step}" for step in plan)


def _format_artifacts(artifacts: dict[str, Any]) -> str:
    if not artifacts:
        return "- No tool artifacts were required."
    return "\n".join(f"- {name}: {value}" for name, value in artifacts.items())


def _format_product_recommendations(product_artifact: Any) -> str:
    if not isinstance(product_artifact, dict):
        return "No model-generated product recommendations were returned."

    lines = [product_artifact.get("summary", "Product recommendations")]
    matches = product_artifact.get("matches", [])
    alternatives = product_artifact.get("alternatives", [])

    if matches:
        lines.append("\nRecommendations:")
        lines.extend(_format_product_lines(matches))
    if alternatives:
        lines.append("\nClose alternatives:")
        lines.extend(_format_product_lines(alternatives))
    if not matches and not alternatives:
        lines.append("\nNo sufficiently supported product match was found.")

    caveats = product_artifact.get("caveats", [])
    if caveats:
        lines.append("\nBefore buying:")
        lines.extend(f"- {caveat}" for caveat in caveats)

    source = product_artifact.get("source")
    model = product_artifact.get("model")
    if source or model:
        lines.append(f"\nSource: {source or 'model'}; model: {model or 'not reported'}.")

    return "\n".join(lines)


def _format_product_lines(products: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for product in products:
        price = product.get("price")
        currency = product.get("currency", "USD")
        price_text = f"{currency} {price:.2f}" if isinstance(price, (int, float)) else "price unverified"
        details = [price_text]
        if product.get("color"):
            details.append(str(product["color"]))
        if product.get("size_options"):
            details.append("sizes: " + ", ".join(product["size_options"]))
        if product.get("over_budget") is True:
            details.append("over budget")

        source_url = product.get("source_url")
        name = product.get("name", "Unnamed product")
        linked_name = f"[{name}]({source_url})" if source_url else name
        availability = (
            f" Availability: {product['availability_note']}."
            if product.get("availability_note")
            else ""
        )
        lines.append(
            f"- {linked_name} ({', '.join(details)}): "
            f"{product.get('reason', 'No reason supplied.')}{availability}"
        )
    return lines


def _cart_item_from_analysis(analysis: ProductRequestAnalysis) -> dict[str, Any]:
    quantity = analysis.quantity or 1
    item = {
        "name": analysis.product_name,
        "product_type": analysis.product_type,
        "product_url": analysis.product_url,
        "unit_price": analysis.unit_price,
        "currency": analysis.currency,
        "quantity": quantity,
        "color": analysis.color,
        "size": analysis.size,
    }
    item["line_total"] = (
        round(analysis.unit_price * quantity, 2)
        if analysis.unit_price is not None
        else None
    )
    return item


def _cart_item_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("name", "")).strip().lower(),
        str(item.get("color", "")).strip().lower(),
        str(item.get("size", "")).strip().lower(),
    )


def _current_cart(state: AgentState) -> dict[str, Any]:
    cart = state.get("context", {}).get("cart", {})
    return cart if isinstance(cart, dict) else {}


def _summarize_cart(items: list[dict[str, Any]]) -> dict[str, Any]:
    known_totals = [
        item["line_total"]
        for item in items
        if isinstance(item.get("line_total"), (int, float))
    ]
    all_prices_known = len(known_totals) == len(items)
    return {
        "items": items,
        "item_count": sum(int(item.get("quantity", 1)) for item in items),
        "subtotal": round(sum(known_totals), 2) if all_prices_known else None,
        "currency": items[0].get("currency", "USD") if items else "USD",
    }


def _shipping_from_analysis(analysis: ProductRequestAnalysis) -> dict[str, str]:
    return {
        "name": analysis.shipping_name or "",
        "address": analysis.shipping_address or "",
        "city": analysis.shipping_city or "",
        "region": analysis.shipping_region or "",
        "postal_code": analysis.shipping_postal_code or "",
        "country": analysis.shipping_country or "",
        "contact_email": analysis.contact_email or "",
    }


def _commerce_error(state: AgentState, tool: ToolName, message: str) -> dict[str, Any]:
    return {
        "status": "error",
        "model_error": message,
        "pending_tools": _remove_current_tool(state, tool),
        "trace": _append(state, "trace", f"{tool}_tool: {message}"),
        "route_history": _append(state, "route_history", f"{tool}_tool->finalize"),
    }


def _format_cart(cart: Any) -> str:
    if not isinstance(cart, dict) or not cart.get("items"):
        return "I could not add the product because the cart item was incomplete."
    item = cart["items"][-1]
    details = [
        detail
        for detail in [item.get("color"), item.get("size")]
        if detail
    ]
    variant = f" ({', '.join(details)})" if details else ""
    return (
        f"Added {item.get('quantity', 1)} x {item.get('name')}{variant} to your cart. "
        f"Your cart now contains {cart.get('item_count', 0)} item(s). "
        "Say \"checkout\" when you are ready to provide shipping details."
    )


def _format_order(order: Any) -> str:
    if not isinstance(order, dict):
        return "The checkout could not be completed."
    if order.get("status") == "cancelled":
        return "No problem. I did not place the order, and your cart is unchanged."
    return (
        f"Your demo order {order.get('order_id')} was placed after your confirmation. "
        "No real retailer or payment processor was charged."
    )
