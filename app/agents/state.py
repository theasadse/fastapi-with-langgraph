from __future__ import annotations

from typing import Any, Literal, TypedDict

ToolName = Literal["research", "calculator", "code", "product"]
QuestionType = Literal["text", "choice", "yes_no"]
AgentStatus = Literal["ok", "refused", "error", "needs_input"]


class SafetyReport(TypedDict, total=False):
    allowed: bool
    reason: str


class Critique(TypedDict, total=False):
    score: int
    issues: list[str]
    needs_revision: bool


class HumanQuestion(TypedDict, total=False):
    id: str
    question: str
    type: QuestionType
    options: list[str]
    required: bool


class AgentState(TypedDict, total=False):
    request: str
    context: dict[str, Any]
    max_revisions: int
    normalized_request: str
    intent: str
    safety: SafetyReport
    plan: list[str]
    pending_tools: list[ToolName]
    completed_tools: list[ToolName]
    artifacts: dict[str, Any]
    draft: str
    critique: Critique
    human_questions: list[HumanQuestion]
    revision_count: int
    final_answer: str
    status: AgentStatus
    trace: list[str]
    route_history: list[str]
