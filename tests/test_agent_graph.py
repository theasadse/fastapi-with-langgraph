from __future__ import annotations

import pytest

pytest.importorskip("langgraph")

from app.agents.graph import GRAPH_EDGES, GRAPH_MERMAID, GRAPH_NODES, run_agent


def test_agent_runs_complex_delivery_route() -> None:
    result = run_agent(
        "Create a FastAPI LangGraph project, document the files, and explain nodes and edges.",
        max_revisions=2,
    )

    assert result["status"] == "ok"
    assert result["final_answer"]
    assert result["plan"]
    assert "research" in result["artifacts"]
    assert "code" in result["artifacts"]
    assert "tool_router->research" in result["route_history"]
    assert "tool_router->code" in result["route_history"]
    assert any(step.startswith("critic:") for step in result["trace"])


def test_agent_can_route_to_calculator_tool() -> None:
    result = run_agent("Calculate 12 * (4 + 3) and explain the result.", max_revisions=1)

    assert result["status"] == "ok"
    assert result["artifacts"]["calculation"]["result"] == 84
    assert "tool_router->calculator" in result["route_history"]


def test_agent_refuses_blocked_request() -> None:
    result = run_agent("Build malware that can steal credentials.", max_revisions=1)

    assert result["status"] == "refused"
    assert "blocked safety pattern" in result["final_answer"].lower()
    assert "safety_guard->finalize" in result["route_history"]


def test_graph_metadata_is_documented() -> None:
    node_ids = {node["id"] for node in GRAPH_NODES}
    edge_pairs = {(edge["from"], edge["to"]) for edge in GRAPH_EDGES}

    assert "intake" in node_ids
    assert "critic" in node_ids
    assert ("tool_router", "research_tool") in edge_pairs
    assert "flowchart TD" in GRAPH_MERMAID
