from __future__ import annotations

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("fastapi")

from app.agents.graph import GRAPH_EDGES, GRAPH_MERMAID, GRAPH_NODES, run_agent
from app.agents.nodes import checkout_tool_node
from app.agents.product_model import (
    ModelConfigurationError,
    ProductRequestAnalysis,
    get_product_model,
)
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_agent_runs_complex_delivery_route() -> None:
    result = run_agent(
        "Create a FastAPI LangGraph project, document the files, and explain nodes and edges.",
        max_revisions=2,
    )

    assert result["status"] == "ok"
    assert result["model_used"] == "test-product-model"
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


def test_general_greeting_returns_personal_assistant_response() -> None:
    result = run_agent("Hi, how are you man?", max_revisions=1)

    assert result["status"] == "ok"
    assert result["intent"] == "general_assistance"
    assert result["completed_tools"] == []
    assert result["final_answer"].startswith("Hi!")
    assert "product" in result["final_answer"].lower()
    assert "anything else" in result["final_answer"].lower()
    assert "Plan:" not in result["final_answer"]


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


def test_add_to_cart_requests_required_shoe_size() -> None:
    result = run_agent("Add Blue Running Shoe to cart.", max_revisions=1)

    assert result["intent"] == "add_to_cart"
    assert result["status"] == "needs_input"
    assert result["human_questions"][0]["id"] == "size"
    assert "tool_router->cart" not in result["route_history"]


def test_add_to_cart_creates_cart_artifact() -> None:
    result = run_agent(
        "Add Blue Running Shoe to cart.",
        context={
            "human_answers": {
                "size": "9",
                "color": "blue",
                "quantity": "2",
                "unit_price": "39.99",
            }
        },
        max_revisions=1,
    )

    cart = result["artifacts"]["cart"]

    assert result["status"] == "ok"
    assert "tool_router->cart" in result["route_history"]
    assert cart["item_count"] == 2
    assert cart["subtotal"] == 79.98
    assert cart["items"][0]["size"] == "9"


def test_checkout_collects_shipping_before_confirmation() -> None:
    result = run_agent(
        "Checkout my cart and place the order.",
        context={
            "cart": {
                "items": [
                    {
                        "name": "Blue Running Shoe",
                        "quantity": 1,
                        "unit_price": 39.99,
                        "line_total": 39.99,
                        "currency": "USD",
                    }
                ]
            }
        },
        max_revisions=1,
    )

    question_ids = {question["id"] for question in result["human_questions"]}

    assert result["intent"] == "checkout"
    assert result["status"] == "needs_input"
    assert "shipping_address" in question_ids
    assert "contact_email" in question_ids
    assert "confirm_order" not in question_ids


def test_checkout_asks_final_confirmation_after_shipping_details() -> None:
    result = run_agent(
        "Checkout my cart and place the order.",
        context={
            "cart": {
                "items": [
                    {
                        "name": "Blue Running Shoe",
                        "quantity": 1,
                        "unit_price": 39.99,
                        "line_total": 39.99,
                        "currency": "USD",
                    }
                ]
            },
            "human_answers": _shipping_answers(),
        },
        max_revisions=1,
    )

    assert result["status"] == "needs_input"
    assert result["human_questions"] == [
        {
            "id": "confirm_order",
            "question": "Place this demo order now?",
            "type": "yes_no",
            "options": ["yes", "no"],
            "required": True,
        }
    ]


def test_confirmed_checkout_places_demo_order_and_clears_cart() -> None:
    answers = _shipping_answers()
    answers["confirm_order"] = "yes"
    result = run_agent(
        "Checkout my cart and place the order.",
        context={
            "cart": {
                "items": [
                    {
                        "name": "Blue Running Shoe",
                        "quantity": 1,
                        "unit_price": 39.99,
                        "line_total": 39.99,
                        "currency": "USD",
                    }
                ]
            },
            "human_answers": answers,
        },
        max_revisions=1,
    )

    assert result["status"] == "ok"
    assert result["artifacts"]["order"]["status"] == "simulated_placed"
    assert result["artifacts"]["order"]["mode"] == "demo"
    assert result["artifacts"]["cart"]["items"] == []
    assert "tool_router->checkout" in result["route_history"]


def test_checkout_no_confirmation_cancels_order() -> None:
    answers = _shipping_answers()
    answers["confirm_order"] = "no"
    result = run_agent(
        "Checkout my cart and place the order.",
        context={
            "cart": {
                "items": [
                    {
                        "name": "Blue Running Shoe",
                        "quantity": 1,
                        "unit_price": 39.99,
                        "line_total": 39.99,
                        "currency": "USD",
                    }
                ]
            },
            "human_answers": answers,
        },
        max_revisions=1,
    )

    assert result["status"] == "ok"
    assert result["artifacts"]["order"]["status"] == "cancelled"
    assert result["artifacts"]["cart"]["items"]


def test_checkout_node_refuses_to_place_without_explicit_confirmation() -> None:
    analysis = ProductRequestAnalysis(
        intent="checkout",
        normalized_request="Checkout my cart.",
        shipping_name="Test Customer",
        shipping_address="123 Test Street",
        shipping_city="Karachi",
        shipping_region="Sindh",
        shipping_postal_code="74000",
        shipping_country="Pakistan",
        contact_email="customer@example.com",
        order_confirmed=None,
        reasoning_summary="Test missing final confirmation.",
    )
    result = checkout_tool_node(
        {
            "context": {
                "cart": {
                    "items": [
                        {
                            "name": "Blue Running Shoe",
                            "quantity": 1,
                            "currency": "USD",
                        }
                    ]
                }
            },
            "model_analysis": analysis.model_dump(),
            "pending_tools": ["checkout"],
            "trace": [],
            "route_history": [],
        }
    )

    assert result["status"] == "error"
    assert "confirm_order=yes" in result["model_error"]


def test_agent_refuses_blocked_request() -> None:
    result = run_agent("Build malware that can steal credentials.", max_revisions=1)

    assert result["status"] == "refused"
    assert "blocked safety pattern" in result["final_answer"].lower()
    assert "safety_guard->finalize" in result["route_history"]


def test_graph_metadata_is_documented() -> None:
    node_ids = {node["id"] for node in GRAPH_NODES}
    edge_pairs = {(edge["from"], edge["to"]) for edge in GRAPH_EDGES}

    assert "intake" in node_ids
    assert "model_analyzer" in node_ids
    assert "critic" in node_ids
    assert "human_clarification" in node_ids
    assert "product_size_clarification" in node_ids
    assert "product_tool" in node_ids
    assert "cart_tool" in node_ids
    assert "checkout_tool" in node_ids
    assert ("tool_router", "research_tool") in edge_pairs
    assert ("safety_guard", "model_analyzer") in edge_pairs
    assert ("model_analyzer", "planner") in edge_pairs
    assert ("model_analyzer", "finalize") in edge_pairs
    assert ("human_clarification", "finalize") in edge_pairs
    assert ("human_clarification", "product_size_clarification") in edge_pairs
    assert ("product_size_clarification", "finalize") in edge_pairs
    assert ("product_size_clarification", "tool_router") in edge_pairs
    assert ("tool_router", "product_tool") in edge_pairs
    assert ("tool_router", "cart_tool") in edge_pairs
    assert ("tool_router", "checkout_tool") in edge_pairs
    assert ("product_tool", "finalize") in edge_pairs
    assert "flowchart TD" in GRAPH_MERMAID


def test_root_serves_browser_test_ui() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "FastAPI With LangGraph Tester" in response.text
    assert "POST /agent/run" in response.text
    assert "Add to cart" in response.text
    assert "Checkout" in response.text
    assert "Commerce test flow" in response.text
    assert "DEMO ORDER ONLY" in response.text
    assert "productList" in response.text
    assert "cartCheckoutButton" in response.text


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


def test_missing_model_configuration_returns_agent_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_to_configure_model() -> None:
        raise ModelConfigurationError("GEMINI_API_KEY is required for this test.")

    monkeypatch.setattr("app.agents.nodes.get_product_model", fail_to_configure_model)

    result = run_agent("Find a product under 50 dollars.", max_revisions=1)

    assert result["status"] == "error"
    assert "GEMINI_API_KEY" in result["final_answer"]
    assert "model_analyzer->finalize" in result["route_history"]


def test_gemini_is_default_provider_and_requires_its_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_product_model.cache_clear()

    with pytest.raises(ModelConfigurationError, match="GEMINI_API_KEY"):
        get_product_model()

    get_product_model.cache_clear()


def _shipping_answers() -> dict[str, str]:
    return {
        "shipping_name": "Test Customer",
        "shipping_address": "123 Test Street",
        "shipping_city": "Karachi",
        "shipping_region": "Sindh",
        "shipping_postal_code": "74000",
        "shipping_country": "Pakistan",
        "contact_email": "customer@example.com",
    }
