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
|   |-- agents/
|   |   |-- graph.py            # LangGraph nodes, edges, and compiled graph
|   |   |-- nodes.py            # Agent node functions
|   |   |-- tools.py            # Local research, calculator, and code tools
|   |   |-- state.py            # Shared graph state schema
|   |   |-- schemas.py          # API request and response models
|   |   `-- llm.py              # Optional OpenAI-backed model adapter
|   `-- ui.py                   # Small browser UI for manual agent testing
|-- docs/
|   |-- ARCHITECTURE.md         # File-by-file and runtime overview
|   |-- API_TESTING.md          # UI, Swagger, curl, and CRUD-style API notes
|   |-- NODES_AND_EDGES.md      # Node and edge connection guide
|   `-- TOPICS.md               # Complete list of covered topics
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

Open the small browser test UI at:

```text
http://127.0.0.1:8000/
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

- `GET /`: browser test UI for running the agent.
- `GET /health`: service health check.
- `GET /agent/graph`: static graph metadata and Mermaid diagram.
- `POST /agent/run`: creates a new agent run and returns the answer.

## Human Interaction Example

For under-specified requests, the graph can stop and ask the human for more
context. Try this in the browser UI:

```text
Find a product under 50 dollars.
```

The first run returns `status: needs_input` with questions such as:

- Which product name or type should I search for?
- Which color do you want?
- Should I only show products under the stated budget?

After you answer, the UI sends a second `POST /agent/run` request with:

```json
{
  "context": {
    "human_answers": {
      "product_type": "backpack",
      "color": "black",
      "strict_budget": "yes"
    }
  }
}
```

Then the graph continues to the product tool and returns matching products from
the sample catalog.

If the product is a `shirt` or `shoe`, the graph can pause a second time and ask
for size before searching. For example, `product_type=shirt` asks for shirt size
with `S`, `M`, `L`, or `XL`; `product_type=shoe` asks for shoe size with `7`,
`8`, `9`, `10`, or `11`.

Different answers produce different products. For example, blue speaker answers
return `Compact Bluetooth Speaker`, blue backpack answers return
`City Blue Backpack`, and flexible budget answers can return premium products
with `over_budget: true`.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Testing](docs/API_TESTING.md)
- [Nodes and Edges](docs/NODES_AND_EDGES.md)
- [Covered Topics](docs/TOPICS.md)

## LangGraph References

This project follows the current LangGraph `StateGraph` pattern with `START`,
`END`, normal edges, and conditional edges:

- [LangGraph graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph StateGraph reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph)
- [add_conditional_edges reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges)
