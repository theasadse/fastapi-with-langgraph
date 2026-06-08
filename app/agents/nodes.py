from __future__ import annotations

import re
from typing import Any, Literal

from app.agents.llm import get_model_client
from app.agents.state import AgentState, ToolName
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
    lowered = normalized.lower()

    if any(word in lowered for word in ["code", "api", "project", "fastapi", "langgraph"]):
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


def route_tools(state: AgentState) -> Literal["research", "calculator", "code", "synthesize"]:
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
    return "\n\n".join(
        [
            "Summary:\n"
            f"I treated the request as a {state.get('intent', 'general')} task and ran a "
            "LangGraph workflow that plans, uses tools, drafts, critiques, and finalizes.",
            "User request:\n" + request,
            "Plan:\n" + _format_plan(state.get("plan", [])),
            "Tool findings:\n" + _format_artifacts(state.get("artifacts", {})),
            "Recommended answer:\n"
            "Build the FastAPI service around the compiled LangGraph agent. Keep node logic "
            "small and testable, keep graph wiring centralized, and document every dynamic "
            "route so future maintainers can see why the agent moved from one node to the next.",
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
