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


def _extract_expression(text: str) -> str | None:
    candidates = re.findall(r"(?<!\w)[0-9][0-9\s+\-*/().%^]{2,}[0-9)]", text)
    if not candidates:
        return None
    return max(candidates, key=len).replace("^", "**").strip()


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
