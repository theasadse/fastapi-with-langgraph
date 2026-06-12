from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    calculator_tool_node,
    cart_tool_node,
    checkout_tool_node,
    code_tool_node,
    critic_node,
    finalize_node,
    human_clarification_node,
    intake_node,
    model_analyzer_node,
    planner_node,
    product_size_clarification_node,
    product_tool_node,
    repair_node,
    research_tool_node,
    route_after_critic,
    route_after_human_clarification,
    route_after_model_analysis,
    route_after_action_tool,
    route_after_product_size_clarification,
    route_after_safety,
    route_tools,
    safety_guard_node,
    synthesize_node,
    tool_router_node,
)
from app.agents.state import AgentState

GRAPH_NODES = [
    {
        "id": "intake",
        "purpose": "Normalize the raw user request before model analysis.",
    },
    {
        "id": "safety_guard",
        "purpose": "Block disallowed requests before planning or tool use.",
    },
    {
        "id": "model_analyzer",
        "purpose": "Use structured model output to infer intent, constraints, and missing questions.",
    },
    {
        "id": "planner",
        "purpose": "Create the work plan and choose tools from the model-derived intent.",
    },
    {
        "id": "human_clarification",
        "purpose": "Ask the human for missing product requirements before tool use.",
    },
    {
        "id": "product_size_clarification",
        "purpose": "Ask for shirt or shoe size when the selected product needs sizing.",
    },
    {
        "id": "tool_router",
        "purpose": "Route to the next pending tool or skip to synthesis.",
    },
    {
        "id": "research_tool",
        "purpose": "Read from a small built-in knowledge base for grounding.",
    },
    {
        "id": "calculator_tool",
        "purpose": "Safely evaluate arithmetic expressions found in the request.",
    },
    {
        "id": "code_tool",
        "purpose": "Inspect the local workspace structure for code context.",
    },
    {
        "id": "product_tool",
        "purpose": "Use the model and optional web search to generate sourced products.",
    },
    {
        "id": "cart_tool",
        "purpose": "Add a model-resolved product and variant to the current cart.",
    },
    {
        "id": "checkout_tool",
        "purpose": "Place a confirmed order through the configured order gateway.",
    },
    {
        "id": "synthesize",
        "purpose": "Draft the answer using the plan and tool artifacts.",
    },
    {
        "id": "critic",
        "purpose": "Score the draft and decide whether it needs repair.",
    },
    {
        "id": "repair",
        "purpose": "Address critique issues before another critic pass.",
    },
    {
        "id": "finalize",
        "purpose": "Return success, human input, refusal, or error results.",
    },
]

GRAPH_EDGES = [
    {"from": "START", "to": "intake", "condition": "always"},
    {"from": "intake", "to": "safety_guard", "condition": "always"},
    {"from": "safety_guard", "to": "model_analyzer", "condition": "allowed"},
    {"from": "safety_guard", "to": "finalize", "condition": "refused"},
    {"from": "model_analyzer", "to": "planner", "condition": "model analysis succeeds"},
    {"from": "model_analyzer", "to": "finalize", "condition": "model analysis fails"},
    {"from": "planner", "to": "human_clarification", "condition": "always"},
    {"from": "human_clarification", "to": "finalize", "condition": "missing human input"},
    {"from": "human_clarification", "to": "product_size_clarification", "condition": "base product context is complete"},
    {"from": "product_size_clarification", "to": "finalize", "condition": "missing size input"},
    {"from": "product_size_clarification", "to": "tool_router", "condition": "size context is complete"},
    {"from": "tool_router", "to": "research_tool", "condition": "next tool is research"},
    {"from": "tool_router", "to": "calculator_tool", "condition": "next tool is calculator"},
    {"from": "tool_router", "to": "code_tool", "condition": "next tool is code"},
    {"from": "tool_router", "to": "product_tool", "condition": "next tool is product"},
    {"from": "tool_router", "to": "cart_tool", "condition": "next tool is cart"},
    {"from": "tool_router", "to": "checkout_tool", "condition": "next tool is checkout"},
    {"from": "tool_router", "to": "synthesize", "condition": "no pending tools"},
    {"from": "research_tool", "to": "tool_router", "condition": "always"},
    {"from": "calculator_tool", "to": "tool_router", "condition": "always"},
    {"from": "code_tool", "to": "tool_router", "condition": "always"},
    {"from": "product_tool", "to": "tool_router", "condition": "model product search succeeds"},
    {"from": "product_tool", "to": "finalize", "condition": "model product search fails"},
    {"from": "cart_tool", "to": "tool_router", "condition": "cart update succeeds"},
    {"from": "cart_tool", "to": "finalize", "condition": "cart update fails"},
    {"from": "checkout_tool", "to": "tool_router", "condition": "checkout succeeds or is cancelled"},
    {"from": "checkout_tool", "to": "finalize", "condition": "checkout validation fails"},
    {"from": "synthesize", "to": "critic", "condition": "always"},
    {"from": "critic", "to": "repair", "condition": "critique needs revision"},
    {"from": "critic", "to": "finalize", "condition": "critique passes or max revisions reached"},
    {"from": "repair", "to": "critic", "condition": "always"},
    {"from": "finalize", "to": "END", "condition": "always"},
]

GRAPH_MERMAID = """flowchart TD
    START([START]) --> intake
    intake --> safety_guard
    safety_guard -- allowed --> model_analyzer
    safety_guard -- refused --> finalize
    model_analyzer -- success --> planner
    model_analyzer -- error --> finalize
    planner --> human_clarification
    human_clarification -- missing input --> finalize
    human_clarification -- enough base context --> product_size_clarification
    product_size_clarification -- missing size --> finalize
    product_size_clarification -- enough size context --> tool_router
    tool_router -- research --> research_tool
    tool_router -- calculator --> calculator_tool
    tool_router -- code --> code_tool
    tool_router -- product --> product_tool
    tool_router -- cart --> cart_tool
    tool_router -- checkout --> checkout_tool
    tool_router -- no pending tools --> synthesize
    research_tool --> tool_router
    calculator_tool --> tool_router
    code_tool --> tool_router
    product_tool -- success --> tool_router
    product_tool -- error --> finalize
    cart_tool -- success --> tool_router
    cart_tool -- error --> finalize
    checkout_tool -- success or cancelled --> tool_router
    checkout_tool -- error --> finalize
    synthesize --> critic
    critic -- needs revision --> repair
    repair --> critic
    critic -- pass or max revisions --> finalize
    finalize --> END([END])
"""


def create_agent_graph() -> Any:
    workflow = StateGraph(AgentState)

    workflow.add_node("intake", intake_node)
    workflow.add_node("safety_guard", safety_guard_node)
    workflow.add_node("model_analyzer", model_analyzer_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("human_clarification", human_clarification_node)
    workflow.add_node("product_size_clarification", product_size_clarification_node)
    workflow.add_node("tool_router", tool_router_node)
    workflow.add_node("research_tool", research_tool_node)
    workflow.add_node("calculator_tool", calculator_tool_node)
    workflow.add_node("code_tool", code_tool_node)
    workflow.add_node("product_tool", product_tool_node)
    workflow.add_node("cart_tool", cart_tool_node)
    workflow.add_node("checkout_tool", checkout_tool_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("repair", repair_node)
    workflow.add_node("finalize", finalize_node)

    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "safety_guard")
    workflow.add_conditional_edges(
        "safety_guard",
        route_after_safety,
        {
            "analyze": "model_analyzer",
            "refuse": "finalize",
        },
    )
    workflow.add_conditional_edges(
        "model_analyzer",
        route_after_model_analysis,
        {
            "plan": "planner",
            "error": "finalize",
        },
    )
    workflow.add_edge("planner", "human_clarification")
    workflow.add_conditional_edges(
        "human_clarification",
        route_after_human_clarification,
        {
            "ask_human": "finalize",
            "continue": "product_size_clarification",
        },
    )
    workflow.add_conditional_edges(
        "product_size_clarification",
        route_after_product_size_clarification,
        {
            "ask_human": "finalize",
            "continue": "tool_router",
        },
    )
    workflow.add_conditional_edges(
        "tool_router",
        route_tools,
        {
            "research": "research_tool",
            "calculator": "calculator_tool",
            "code": "code_tool",
            "product": "product_tool",
            "cart": "cart_tool",
            "checkout": "checkout_tool",
            "synthesize": "synthesize",
        },
    )
    workflow.add_edge("research_tool", "tool_router")
    workflow.add_edge("calculator_tool", "tool_router")
    workflow.add_edge("code_tool", "tool_router")
    workflow.add_conditional_edges(
        "product_tool",
        route_after_action_tool,
        {
            "continue": "tool_router",
            "error": "finalize",
        },
    )
    workflow.add_conditional_edges(
        "cart_tool",
        route_after_action_tool,
        {
            "continue": "tool_router",
            "error": "finalize",
        },
    )
    workflow.add_conditional_edges(
        "checkout_tool",
        route_after_action_tool,
        {
            "continue": "tool_router",
            "error": "finalize",
        },
    )
    workflow.add_edge("synthesize", "critic")
    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "repair": "repair",
            "finalize": "finalize",
        },
    )
    workflow.add_edge("repair", "critic")
    workflow.add_edge("finalize", END)

    return workflow.compile()


@lru_cache(maxsize=1)
def get_compiled_agent() -> Any:
    return create_agent_graph()


def run_agent(
    query: str,
    context: dict[str, Any] | None = None,
    max_revisions: int = 2,
) -> AgentState:
    initial_state: AgentState = {
        "request": query,
        "context": context or {},
        "max_revisions": max_revisions,
        "revision_count": 0,
        "trace": [],
        "route_history": [],
        "pending_tools": [],
        "completed_tools": [],
        "human_questions": [],
        "artifacts": {},
    }

    return get_compiled_agent().invoke(initial_state)
