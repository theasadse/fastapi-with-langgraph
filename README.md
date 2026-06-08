# FastAPI With LangGraph

A complete example project that combines FastAPI with a multi-step LangGraph
agent. The agent is intentionally more advanced than a hello-world workflow: it
normalizes the request, checks safety, plans work, routes through local tools,
drafts an answer, critiques the draft, repairs weak drafts, and finalizes the
response.

## Project Structure

```text
.
|-- app/
|   |-- main.py                 # FastAPI application and HTTP endpoints
|   `-- agents/
|       |-- graph.py            # LangGraph nodes, edges, and compiled graph
|       |-- nodes.py            # Agent node functions
|       |-- tools.py            # Local research, calculator, and code tools
|       |-- state.py            # Shared graph state schema
|       |-- schemas.py          # API request and response models
|       `-- llm.py              # Optional OpenAI-backed model adapter
|-- docs/
|   |-- ARCHITECTURE.md         # File-by-file and runtime overview
|   `-- NODES_AND_EDGES.md      # Node and edge connection guide
|-- tests/
|   `-- test_agent_graph.py
|-- pyproject.toml
`-- .env.example
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

The project runs without an external LLM by default. It uses deterministic local
logic so you can learn the graph flow without paying for API calls.

To enable an OpenAI-backed synthesis step:

```bash
pip install -e ".[openai,test]"
cp .env.example .env
```

Then set `AGENT_USE_OPENAI=true`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in
`.env` or your shell environment.

## Run The API

```bash
uvicorn app.main:app --reload
```

Open the generated API docs at:

```text
http://127.0.0.1:8000/docs
```

## Try The Agent

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a FastAPI and LangGraph project, explain the files, and document the nodes and edges.",
    "max_revisions": 2
  }'
```

Useful endpoints:

- `GET /`: redirects to the interactive API docs.
- `GET /health`: service health check.
- `GET /agent/graph`: static graph metadata and Mermaid diagram.
- `POST /agent/run`: runs the complex delivery agent.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Nodes and Edges](docs/NODES_AND_EDGES.md)

## LangGraph References

This project follows the current LangGraph `StateGraph` pattern with `START`,
`END`, normal edges, and conditional edges:

- [LangGraph graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph StateGraph reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph)
- [add_conditional_edges reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges)
