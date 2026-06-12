from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse

from app.agents.graph import (
    GRAPH_EDGES,
    GRAPH_MERMAID,
    GRAPH_NODES,
    run_agent,
)
from app.agents.schemas import AgentRequest, AgentResponse, GraphDescription
from app.ui import render_test_ui

load_dotenv()

app = FastAPI(
    title="FastAPI With LangGraph",
    description="Example API that runs a complex LangGraph delivery agent.",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root() -> HTMLResponse:
    return HTMLResponse(render_test_ui())


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/agent/graph", response_model=GraphDescription)
def describe_graph() -> GraphDescription:
    return GraphDescription(
        mermaid=GRAPH_MERMAID,
        nodes=GRAPH_NODES,
        edges=GRAPH_EDGES,
    )


@app.post("/agent/run", response_model=AgentResponse)
def run_delivery_agent(payload: AgentRequest) -> AgentResponse:
    try:
        result = run_agent(
            query=payload.query,
            context=payload.context,
            max_revisions=payload.max_revisions,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AgentResponse(
        answer=result.get("final_answer", ""),
        status=result.get("status", "error"),
        human_questions=result.get("human_questions", []),
        plan=result.get("plan", []),
        artifacts=result.get("artifacts", {}),
        critique=result.get("critique", {}),
        trace=result.get("trace", []),
        route_history=result.get("route_history", []),
    )
