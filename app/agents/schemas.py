from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="The task or question the agent should solve.",
        examples=[
            "Create a FastAPI and LangGraph project, explain the files, and document the graph nodes and edges."
        ],
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured context for the agent.",
    )
    max_revisions: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum number of critique and repair loops.",
    )


class AgentResponse(BaseModel):
    answer: str
    status: str
    plan: list[str]
    artifacts: dict[str, Any]
    critique: dict[str, Any]
    trace: list[str]
    route_history: list[str]


class GraphDescription(BaseModel):
    mermaid: str
    nodes: list[dict[str, str]]
    edges: list[dict[str, str]]
