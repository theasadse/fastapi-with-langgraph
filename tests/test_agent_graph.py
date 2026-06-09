from __future__ import annotations

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("fastapi")

from app.agents.graph import GRAPH_EDGES, GRAPH_MERMAID, GRAPH_NODES, run_agent
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


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


def test_product_search_requests_human_input_when_context_is_missing() -> None:
    result = run_agent("Find a product under 50 dollars.", max_revisions=1)

    question_ids = {question["id"] for question in result["human_questions"]}

    assert result["status"] == "needs_input"
    assert "product_type" in question_ids
    assert "color" in question_ids
    assert "strict_budget" in question_ids
    assert "human_clarification->finalize" in result["route_history"]
    assert "tool_router->product" not in result["route_history"]


def test_generic_product_prompts_share_product_search_flow() -> None:
    give_result = run_agent("Give me product under 50 dollar.", max_revisions=1)
    find_result = run_agent("Find product under 40 dollar.", max_revisions=1)

    assert give_result["intent"] == "product_search"
    assert find_result["intent"] == "product_search"
    assert give_result["status"] == "needs_input"
    assert find_result["status"] == "needs_input"
    assert {question["id"] for question in give_result["human_questions"]} == {
        "product_type",
        "color",
        "strict_budget",
    }


def test_product_search_continues_after_human_answers() -> None:
    result = run_agent(
        "Find a product under 50 dollars.",
        context={
            "human_answers": {
                "product_type": "backpack",
                "color": "black",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )

    assert result["status"] == "ok"
    assert result["human_questions"] == []
    assert "human_clarification->product_size_clarification" in result["route_history"]
    assert "product_size_clarification->tool_router" in result["route_history"]
    assert "tool_router->product" in result["route_history"]
    assert result["artifacts"]["products"]["matches"][0]["name"] == "Canvas Day Backpack"


def test_shirt_answer_requests_size_before_product_search() -> None:
    result = run_agent(
        "Give me product under 40 dollar.",
        context={
            "human_answers": {
                "product_type": "shirt",
                "color": "black",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )

    assert result["status"] == "needs_input"
    assert result["human_questions"] == [
        {
            "id": "size",
            "question": "What shirt size do you want?",
            "type": "choice",
            "options": ["S", "M", "L", "XL"],
            "required": True,
        }
    ]
    assert "product_size_clarification->finalize" in result["route_history"]
    assert "tool_router->product" not in result["route_history"]


def test_shirt_search_uses_human_size_answer() -> None:
    result = run_agent(
        "Give me product under 40 dollar.",
        context={
            "human_answers": {
                "product_type": "shirt",
                "color": "black",
                "size": "M",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )

    products = result["artifacts"]["products"]

    assert result["status"] == "ok"
    assert products["applied_filters"]["size"] == "M"
    assert products["matches"][0]["name"] == "Black Oxford Shirt"
    assert "M" in products["matches"][0]["size_options"]


def test_shoe_answer_requests_size_before_product_search() -> None:
    result = run_agent(
        "Find product under 40 dollar.",
        context={
            "human_answers": {
                "product_type": "shoe",
                "color": "blue",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )

    question = result["human_questions"][0]

    assert result["status"] == "needs_input"
    assert question["id"] == "size"
    assert question["question"] == "What shoe size do you want?"
    assert question["options"] == ["7", "8", "9", "10", "11"]


def test_shoe_search_uses_human_size_answer() -> None:
    result = run_agent(
        "Find product under 40 dollar.",
        context={
            "human_answers": {
                "product_type": "shoe",
                "color": "blue",
                "size": "9",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )

    products = result["artifacts"]["products"]

    assert result["status"] == "ok"
    assert products["applied_filters"]["budget"] == 40.0
    assert products["applied_filters"]["size"] == "9"
    assert products["matches"][0]["name"] == "Blue Running Shoe"


def test_product_search_changes_results_from_human_answers() -> None:
    speaker_result = run_agent(
        "Find a product under 50 dollars.",
        context={
            "human_answers": {
                "product_type": "speaker",
                "color": "blue",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )
    backpack_result = run_agent(
        "Find a product under 50 dollars.",
        context={
            "human_answers": {
                "product_type": "backpack",
                "color": "blue",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )

    speaker_names = [item["name"] for item in speaker_result["artifacts"]["products"]["matches"]]
    backpack_names = [item["name"] for item in backpack_result["artifacts"]["products"]["matches"]]

    assert speaker_names[0] == "Compact Bluetooth Speaker"
    assert backpack_names[0] == "City Blue Backpack"
    assert speaker_names != backpack_names


def test_product_search_budget_answer_changes_results() -> None:
    strict_result = run_agent(
        "Find a product under 50 dollars.",
        context={
            "human_answers": {
                "product_type": "backpack",
                "color": "black",
                "strict_budget": "yes",
            }
        },
        max_revisions=1,
    )
    flexible_result = run_agent(
        "Find a product under 50 dollars.",
        context={
            "human_answers": {
                "product_type": "backpack",
                "color": "black",
                "strict_budget": "no",
            }
        },
        max_revisions=1,
    )

    strict_names = [item["name"] for item in strict_result["artifacts"]["products"]["matches"]]
    flexible_products = flexible_result["artifacts"]["products"]["matches"]
    flexible_names = [item["name"] for item in flexible_products]

    assert strict_names == ["Canvas Day Backpack"]
    assert flexible_names[0] == "Weatherproof Travel Backpack"
    assert flexible_products[0]["over_budget"] is True


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
    assert "human_clarification" in node_ids
    assert "product_size_clarification" in node_ids
    assert "product_tool" in node_ids
    assert ("tool_router", "research_tool") in edge_pairs
    assert ("human_clarification", "finalize") in edge_pairs
    assert ("human_clarification", "product_size_clarification") in edge_pairs
    assert ("product_size_clarification", "finalize") in edge_pairs
    assert ("product_size_clarification", "tool_router") in edge_pairs
    assert ("tool_router", "product_tool") in edge_pairs
    assert "flowchart TD" in GRAPH_MERMAID


def test_root_serves_browser_test_ui() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "FastAPI With LangGraph Tester" in response.text
    assert "POST /agent/run" in response.text


def test_agent_run_api_creates_agent_execution() -> None:
    response = client.post(
        "/agent/run",
        json={
            "query": "Create docs for this FastAPI LangGraph agent and explain the API.",
            "context": {"source": "test-client"},
            "max_revisions": 1,
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["answer"]
    assert body["plan"]
    assert body["human_questions"] == []
    assert "trace" in body


def test_agent_run_api_can_return_human_questions() -> None:
    response = client.post(
        "/agent/run",
        json={
            "query": "Find a product under 50 dollars.",
            "context": {"source": "test-client"},
            "max_revisions": 1,
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "needs_input"
    assert body["answer"]
    assert body["human_questions"]
