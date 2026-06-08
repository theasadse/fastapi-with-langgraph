from __future__ import annotations

import ast
import operator
import re
from collections import Counter
from pathlib import Path
from typing import Any

KNOWLEDGE_BASE = {
    "langgraph": [
        "LangGraph models agent workflows as stateful graphs.",
        "Nodes are Python callables that read state and return state updates.",
        "Edges define which node runs next. Conditional edges choose a route from state.",
        "START and END are virtual graph boundaries used to enter and finish the workflow.",
    ],
    "fastapi": [
        "FastAPI exposes Python functions as typed HTTP endpoints.",
        "Pydantic models give request validation and documented response schemas.",
        "Uvicorn is the common ASGI server used during local development.",
    ],
    "agent": [
        "Useful production agents separate planning, tool use, synthesis, and critique.",
        "A repair loop lets the graph improve weak drafts before returning the final answer.",
        "Trace data makes agent behavior easier to debug and test.",
    ],
    "documentation": [
        "Good docs map runtime behavior back to files, nodes, and edges.",
        "A graph diagram helps readers understand dynamic routing faster than prose alone.",
    ],
}

PRODUCT_CATALOG = [
    {
        "name": "Everyday Wireless Mouse",
        "category": "mouse",
        "price": 24.99,
        "color": "black",
        "reason": "Reliable for office work and travel.",
    },
    {
        "name": "Arctic Wireless Mouse",
        "category": "mouse",
        "price": 27.99,
        "color": "white",
        "reason": "Clean desk setup option with quiet clicks.",
    },
    {
        "name": "Compact Bluetooth Speaker",
        "category": "speaker",
        "price": 39.99,
        "color": "blue",
        "reason": "Portable, rechargeable, and below the budget.",
    },
    {
        "name": "Studio Mini Speaker",
        "category": "speaker",
        "price": 59.99,
        "color": "black",
        "reason": "Better bass and volume when the budget is flexible.",
    },
    {
        "name": "Noise-Isolating Earbuds",
        "category": "earbuds",
        "price": 46.5,
        "color": "white",
        "reason": "Good lightweight option for calls and music.",
    },
    {
        "name": "Sport Wireless Earbuds",
        "category": "earbuds",
        "price": 32.99,
        "color": "green",
        "reason": "Sweat-resistant pick for workouts.",
    },
    {
        "name": "Adjustable Desk Lamp",
        "category": "lamp",
        "price": 34.99,
        "color": "black",
        "reason": "Useful home-office pick with adjustable brightness.",
    },
    {
        "name": "Blue Reading Lamp",
        "category": "lamp",
        "price": 29.99,
        "color": "blue",
        "reason": "Compact reading light with a softer color finish.",
    },
    {
        "name": "Insulated Water Bottle",
        "category": "bottle",
        "price": 21.99,
        "color": "green",
        "reason": "Budget-friendly daily carry item.",
    },
    {
        "name": "Minimal White Water Bottle",
        "category": "bottle",
        "price": 18.99,
        "color": "white",
        "reason": "Simple low-cost option for daily hydration.",
    },
    {
        "name": "Canvas Day Backpack",
        "category": "backpack",
        "price": 49.99,
        "color": "black",
        "reason": "Large enough for laptop accessories while staying under 50.",
    },
    {
        "name": "City Blue Backpack",
        "category": "backpack",
        "price": 44.99,
        "color": "blue",
        "reason": "Lighter everyday backpack with a bright color.",
    },
    {
        "name": "Weatherproof Travel Backpack",
        "category": "backpack",
        "price": 68.99,
        "color": "black",
        "reason": "More durable option when the budget can stretch.",
    },
]

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def local_research(query: str) -> dict[str, Any]:
    text = query.lower()
    matches: list[str] = []

    for topic, facts in KNOWLEDGE_BASE.items():
        if topic in text:
            matches.extend(facts)

    if not matches:
        matches.extend(
            [
                "Break the task into intent, constraints, tools, synthesis, and verification.",
                "Keep graph state explicit so every node can be tested independently.",
            ]
        )

    return {
        "source": "built-in knowledge base",
        "facts": matches,
    }


def calculate_from_text(text: str) -> dict[str, Any]:
    expression = _extract_expression(text)
    if not expression:
        return {
            "expression": None,
            "result": None,
            "error": "No arithmetic expression was found.",
        }

    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_ast(tree.body)
    except Exception as exc:
        return {
            "expression": expression,
            "result": None,
            "error": f"Could not evaluate expression: {exc}",
        }

    return {
        "expression": expression,
        "result": result,
        "error": None,
    }


def inspect_workspace(root: Path | None = None, max_files: int = 60) -> dict[str, Any]:
    root = root or Path.cwd()
    excluded_dirs = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    files: list[Path] = []

    for path in root.rglob("*"):
        if any(part in excluded_dirs for part in path.parts):
            continue
        if path.is_file():
            files.append(path)

    files = sorted(files)
    shown = files[:max_files]
    extension_counts = Counter(path.suffix or "[no extension]" for path in files)

    return {
        "root": str(root),
        "file_count": len(files),
        "top_extensions": dict(extension_counts.most_common(8)),
        "files": [str(path.relative_to(root)) for path in shown],
        "truncated": len(files) > max_files,
    }


def search_products(query: str, context: dict[str, Any]) -> dict[str, Any]:
    answers = context.get("human_answers", {})
    budget = _extract_budget(query) or _to_float(answers.get("budget")) or 50.0
    color = _normalize_optional_filter(answers.get("color"))
    product_type = _normalize_optional_filter(answers.get("product_type"))
    strict_budget = str(answers.get("strict_budget", "yes")).strip().lower() != "no"

    exact_matches = []
    relaxed_matches = []
    for product in PRODUCT_CATALOG:
        product_view = _product_view(product, budget)
        if not _budget_allowed(product, budget, strict_budget):
            continue
        if not _filter_color(product, color):
            continue
        if not _filter_product_type(product, product_type):
            continue
        exact_matches.append(product_view)

    if not exact_matches:
        for product in PRODUCT_CATALOG:
            if not _budget_allowed(product, budget, strict_budget):
                continue
            if product_type and _filter_product_type(product, product_type):
                relaxed_matches.append(_product_view(product, budget, fallback_reason="color relaxed"))
                continue
            if color and _filter_color(product, color):
                relaxed_matches.append(_product_view(product, budget, fallback_reason="product type relaxed"))

    matches = _rank_products(exact_matches, strict_budget)
    alternatives = _rank_products(relaxed_matches, strict_budget)

    return {
        "budget": budget,
        "strict_budget": strict_budget,
        "color": color or "not specified",
        "product_type": product_type or "not specified",
        "applied_filters": {
            "budget": budget,
            "strict_budget": strict_budget,
            "color": color or "any",
            "product_type": product_type or "any",
        },
        "matches": matches[:5],
        "alternatives": alternatives[:5],
        "match_count": len(matches),
        "alternative_count": len(alternatives),
        "message": _product_search_message(matches, alternatives),
        "source": "local sample product catalog",
    }


def _extract_expression(text: str) -> str | None:
    candidates = re.findall(r"(?<!\w)[0-9][0-9\s+\-*/().%^]{2,}[0-9)]", text)
    if not candidates:
        return None
    return max(candidates, key=len).replace("^", "**").strip()


def _extract_budget(text: str) -> float | None:
    match = re.search(r"(?:under|below|less than|budget|[$])\s*\$?\s*(\d+(?:\.\d+)?)", text.lower())
    if not match:
        return None
    return _to_float(match.group(1))


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_filter(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"", "any", "all", "no preference", "none"}:
        return ""
    return normalized


def _budget_allowed(product: dict[str, Any], budget: float, strict_budget: bool) -> bool:
    if strict_budget:
        return product["price"] <= budget
    return product["price"] <= budget + 30


def _filter_color(product: dict[str, Any], color: str) -> bool:
    return not color or product["color"] == color


def _filter_product_type(product: dict[str, Any], product_type: str) -> bool:
    return not product_type or _product_matches(product_type, product["category"], product["name"])


def _product_view(product: dict[str, Any], budget: float, fallback_reason: str | None = None) -> dict[str, Any]:
    view = dict(product)
    view["over_budget"] = product["price"] > budget
    view["budget_delta"] = round(product["price"] - budget, 2)
    if fallback_reason:
        view["fallback_reason"] = fallback_reason
    return view


def _rank_products(products: list[dict[str, Any]], strict_budget: bool) -> list[dict[str, Any]]:
    if strict_budget:
        return sorted(products, key=lambda product: (product["price"], product["name"]))
    return sorted(products, key=lambda product: (not product["over_budget"], -product["price"], product["name"]))


def _product_search_message(matches: list[dict[str, Any]], alternatives: list[dict[str, Any]]) -> str:
    if matches:
        return "Exact matches found for the human answers."
    if alternatives:
        return "No exact match; returned relaxed alternatives based on the closest human answers."
    return "No product matched the current human answers."


def _product_matches(user_text: str, category: str, name: str) -> bool:
    aliases = {
        "headphone": {"earbuds"},
        "headphones": {"earbuds"},
        "earphone": {"earbuds"},
        "earphones": {"earbuds"},
        "bag": {"backpack"},
        "bags": {"backpack"},
        "light": {"lamp"},
    }
    normalized = user_text.lower().strip()
    accepted = {normalized, *aliases.get(normalized, set())}
    return category in accepted or normalized in name.lower()


def _eval_ast(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPERATORS:
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise ValueError("exponent is too large")
        return SAFE_OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPERATORS:
        return SAFE_OPERATORS[type(node.op)](_eval_ast(node.operand))

    raise ValueError(f"unsupported expression: {ast.dump(node)}")
