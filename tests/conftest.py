from __future__ import annotations

import re
from typing import Any

import pytest

from app.agents.product_model import (
    AppliedProductFilters,
    ModelQuestion,
    ProductRecommendation,
    ProductRequestAnalysis,
    ProductSearchResult,
)


class FakeProductModel:
    model_name = "test-product-model"

    def analyze_request(
        self,
        query: str,
        collected_context: dict[str, Any],
    ) -> ProductRequestAnalysis:
        human_answers = collected_context.get("human_answers", collected_context)
        cart = collected_context.get("cart", {})
        lowered = query.lower()
        if any(word in lowered for word in ["checkout", "place the order", "buy my cart"]):
            intent = "checkout"
        elif "cart" in lowered and any(word in lowered for word in ["add", "put"]):
            intent = "add_to_cart"
        elif any(word in lowered for word in ["product", "shoe", "shirt", "backpack", "speaker"]):
            intent = "product_search"
        elif "calculate" in lowered:
            intent = "calculation"
        elif "document" in lowered or "docs" in lowered:
            intent = "documentation"
        elif any(word in lowered for word in ["fastapi", "langgraph", "project", "api"]):
            intent = "software_delivery"
        else:
            intent = "general_assistance"

        product_type = str(human_answers.get("product_type", "")).strip().lower() or None
        if not product_type:
            product_type = next(
                (
                    item
                    for item in ["shirt", "shoe", "backpack", "speaker"]
                    if item in lowered
                ),
                None,
            )

        product_name = str(human_answers.get("product_name", "")).strip() or None
        if not product_name:
            for candidate in [
                "Blue Running Shoe",
                "Black Oxford Shirt",
                "Canvas Day Backpack",
            ]:
                if candidate.lower() in lowered:
                    product_name = candidate
                    break

        color = str(human_answers.get("color", "")).strip().lower() or None
        strict_answer = str(human_answers.get("strict_budget", "")).strip().lower()
        strict_budget = None if not strict_answer else strict_answer == "yes"
        size = str(human_answers.get("size", "")).strip() or None
        quantity = int(human_answers.get("quantity", 1) or 1)
        unit_price = (
            float(human_answers["unit_price"])
            if human_answers.get("unit_price") not in (None, "")
            else None
        )
        budget_match = re.search(r"(?:under|below)\s+\$?(\d+)", lowered)
        budget = float(budget_match.group(1)) if budget_match else None
        order_answer = str(human_answers.get("confirm_order", "")).strip().lower()
        order_confirmed = None if not order_answer else order_answer == "yes"

        shipping_fields = {
            "shipping_name": str(human_answers.get("shipping_name", "")).strip() or None,
            "shipping_address": str(human_answers.get("shipping_address", "")).strip() or None,
            "shipping_city": str(human_answers.get("shipping_city", "")).strip() or None,
            "shipping_region": str(human_answers.get("shipping_region", "")).strip() or None,
            "shipping_postal_code": str(
                human_answers.get("shipping_postal_code", "")
            ).strip()
            or None,
            "shipping_country": str(human_answers.get("shipping_country", "")).strip() or None,
            "contact_email": str(human_answers.get("contact_email", "")).strip() or None,
        }

        questions: list[ModelQuestion] = []
        if intent == "product_search":
            if not product_type:
                questions.append(
                    ModelQuestion(
                        id="product_type",
                        question="Which product name or type should I search for?",
                        type="text",
                    )
                )
            if not color:
                questions.append(
                    ModelQuestion(
                        id="color",
                        question="Which color do you want?",
                        type="choice",
                        options=["black", "white", "blue", "green", "any"],
                    )
                )
            if strict_budget is None:
                questions.append(
                    ModelQuestion(
                        id="strict_budget",
                        question="Should I only show products under the stated budget?",
                        type="yes_no",
                        options=["yes", "no"],
                    )
                )
            if product_type == "shirt" and not size:
                questions.append(
                    ModelQuestion(
                        id="size",
                        question="What shirt size do you want?",
                        type="choice",
                        options=["S", "M", "L", "XL"],
                    )
                )
            if product_type == "shoe" and not size:
                questions.append(
                    ModelQuestion(
                        id="size",
                        question="What shoe size do you want?",
                        type="choice",
                        options=["7", "8", "9", "10", "11"],
                    )
                )
        elif intent == "add_to_cart":
            if not product_name:
                questions.append(
                    ModelQuestion(
                        id="product_name",
                        question="Which product should I add to your cart?",
                        type="text",
                    )
                )
            if product_name and "shoe" in product_name.lower() and not size:
                questions.append(
                    ModelQuestion(
                        id="size",
                        question="What shoe size should I add?",
                        type="choice",
                        options=["7", "8", "9", "10", "11"],
                    )
                )
        elif intent == "checkout":
            if not cart.get("items") and not product_name:
                questions.append(
                    ModelQuestion(
                        id="product_name",
                        question="Your cart is empty. Which product should I add first?",
                        type="text",
                    )
                )
            shipping_questions = {
                "shipping_name": "What name should I use for shipping?",
                "shipping_address": "What is the shipping street address?",
                "shipping_city": "What is the shipping city?",
                "shipping_region": "What is the state or region?",
                "shipping_postal_code": "What is the postal code?",
                "shipping_country": "What is the shipping country?",
                "contact_email": "What email should receive the order receipt?",
            }
            for field, question in shipping_questions.items():
                if not shipping_fields[field]:
                    questions.append(ModelQuestion(id=field, question=question, type="text"))
            cart_ready = bool(cart.get("items") or product_name)
            shipping_ready = all(shipping_fields.values())
            if cart_ready and shipping_ready and order_confirmed is None:
                questions.append(
                    ModelQuestion(
                        id="confirm_order",
                        question="Place this demo order now?",
                        type="yes_no",
                        options=["yes", "no"],
                    )
                )

        return ProductRequestAnalysis(
            intent=intent,
            normalized_request=" ".join(query.split()),
            product_type=product_type,
            product_name=product_name,
            unit_price=unit_price,
            quantity=quantity,
            budget=budget,
            color=color,
            size=size,
            strict_budget=strict_budget,
            order_confirmed=order_confirmed,
            missing_fields=[question.id for question in questions],
            questions=questions,
            reasoning_summary="Deterministic fake model analysis for graph tests.",
            **shipping_fields,
        )

    def recommend_products(
        self,
        query: str,
        analysis: ProductRequestAnalysis,
    ) -> ProductSearchResult:
        product = self._product_for(analysis)
        return ProductSearchResult(
            summary="The model found a product matching the supplied preferences.",
            applied_filters=AppliedProductFilters(
                product_type=analysis.product_type,
                budget=analysis.budget,
                color=analysis.color,
                size=analysis.size,
                strict_budget=analysis.strict_budget,
            ),
            matches=[product],
            alternatives=[],
            caveats=["Verify final price, stock, color, and size on the retailer page."],
            source="injected fake model used only by automated tests",
            model=self.model_name,
            search_used=True,
        )

    def _product_for(self, analysis: ProductRequestAnalysis) -> ProductRecommendation:
        product_type = analysis.product_type
        if product_type == "shirt":
            return ProductRecommendation(
                name="Black Oxford Shirt",
                category="shirt",
                price=38.99,
                color=analysis.color,
                size_options=["M", "L", "XL"],
                reason="The fake model matched the requested shirt preferences.",
                source_url="https://example.test/black-oxford-shirt",
                over_budget=False,
            )
        if product_type == "shoe":
            return ProductRecommendation(
                name="Blue Running Shoe",
                category="shoe",
                price=39.99,
                color=analysis.color,
                size_options=["8", "9", "10", "11"],
                reason="The fake model matched the requested shoe preferences.",
                source_url="https://example.test/blue-running-shoe",
                over_budget=False,
            )
        if product_type == "speaker":
            return ProductRecommendation(
                name="Compact Bluetooth Speaker",
                category="speaker",
                price=39.99,
                color=analysis.color,
                reason="The fake model matched the requested speaker preferences.",
                source_url="https://example.test/compact-speaker",
                over_budget=False,
            )
        if product_type == "backpack" and analysis.strict_budget is False:
            return ProductRecommendation(
                name="Weatherproof Travel Backpack",
                category="backpack",
                price=68.99,
                color=analysis.color,
                reason="The fake model selected a modest stretch option.",
                source_url="https://example.test/weatherproof-backpack",
                over_budget=True,
            )
        if product_type == "backpack" and analysis.color == "blue":
            return ProductRecommendation(
                name="City Blue Backpack",
                category="backpack",
                price=44.99,
                color="blue",
                reason="The fake model matched the requested blue backpack preferences.",
                source_url="https://example.test/city-blue-backpack",
                over_budget=False,
            )
        return ProductRecommendation(
            name="Canvas Day Backpack",
            category=product_type or "backpack",
            price=49.99,
            color=analysis.color,
            reason="The fake model matched the requested backpack preferences.",
            source_url="https://example.test/canvas-day-backpack",
            over_budget=False,
        )


@pytest.fixture(autouse=True)
def inject_fake_product_model(monkeypatch: pytest.MonkeyPatch) -> FakeProductModel:
    model = FakeProductModel()
    monkeypatch.setattr("app.agents.nodes.get_product_model", lambda: model)
    return model
