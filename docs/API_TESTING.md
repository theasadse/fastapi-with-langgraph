# API Testing

This project gives you three practical ways to test the agent API:

- Browser test UI at `http://127.0.0.1:8000/`
- Swagger UI at `http://127.0.0.1:8000/docs`
- Command-line calls with `curl`

## CRUD-Style Mental Model

In CRUD applications, the first operation is usually create. For this agent API,
the create operation is:

```text
POST /agent/run
```

This creates a new agent execution. The project does not persist agent runs in a
database, so the run exists only for the lifetime of that HTTP request.

| CRUD Idea | Current Endpoint | Meaning |
| --- | --- | --- |
| Create | `POST /agent/run` | Create one new agent run from a user query. |
| Read | `GET /health` | Read service status. |
| Read | `GET /agent/graph` | Read graph metadata, nodes, edges, and Mermaid diagram. |
| Read | `GET /docs` | Read and test the OpenAPI contract. |
| Update | Not implemented | A completed stateless run is not updated. |
| Delete | Not implemented | No stored run exists to delete. |

If you later add a database, the next CRUD endpoints could be:

```text
POST   /agent/runs
GET    /agent/runs/{run_id}
GET    /agent/runs
PATCH  /agent/runs/{run_id}
DELETE /agent/runs/{run_id}
```

## Browser Test UI

Open:

```text
http://127.0.0.1:8000/
```

The UI sends a real `fetch()` request to `POST /agent/run` with this JSON shape:

```json
{
  "query": "Create a FastAPI and LangGraph project, explain the files, document the nodes and edges, and show how the agent API works.",
  "context": {
    "source": "test-ui",
    "priority": "learning",
    "scenario": "local-ui-test"
  },
  "max_revisions": 2
}
```

The response panel shows:

- `answer`: final agent answer.
- `status`: `ok`, `needs_input`, `refused`, or `error`.
- `human_questions`: questions the UI should ask the user when status is `needs_input`.
- `plan`: steps created by the planner node.
- `artifacts`: outputs from tools such as research, calculator, and code inspection.
- `critique`: score and repair decision from the critic.
- `trace`: node-level execution log.
- `route_history`: conditional edges selected during the run.

## Swagger Testing

Open:

```text
http://127.0.0.1:8000/docs
```

Use `POST /agent/run`, select `Try it out`, paste a request body, and execute it.
Swagger uses the same API route as the browser UI.

## Human-In-The-Loop Product Example

Start with an under-specified request:

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find a product under 50 dollars.",
    "context": {
      "source": "curl"
    },
    "max_revisions": 1
  }'
```

The agent returns `status: "needs_input"` and structured questions:

```json
{
  "status": "needs_input",
  "human_questions": [
    {
      "id": "product_type",
      "question": "What product type should I search for?",
      "type": "text"
    },
    {
      "id": "color",
      "question": "Which color do you want?",
      "type": "choice",
      "options": ["black", "white", "blue", "green", "any"]
    },
    {
      "id": "strict_budget",
      "question": "Should I only show products under the stated budget?",
      "type": "yes_no",
      "options": ["yes", "no"]
    }
  ]
}
```

Continue by sending another create-run request with human answers in context:

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find a product under 50 dollars.",
    "context": {
      "source": "curl",
      "human_answers": {
        "product_type": "backpack",
        "color": "black",
        "strict_budget": "yes"
      }
    },
    "max_revisions": 1
  }'
```

That second request continues past the human clarification step and runs the
product tool. The response includes product matches in `artifacts.products`.

Different human answers change the product results:

| Human Answers | Expected Top Product |
| --- | --- |
| `product_type=speaker`, `color=blue`, `strict_budget=yes` | `Compact Bluetooth Speaker` |
| `product_type=backpack`, `color=blue`, `strict_budget=yes` | `City Blue Backpack` |
| `product_type=backpack`, `color=black`, `strict_budget=yes` | `Canvas Day Backpack` |
| `product_type=backpack`, `color=black`, `strict_budget=no` | `Weatherproof Travel Backpack` |

The `strict_budget=no` answer allows flexible budget results. Those products are
marked with `over_budget: true` in `artifacts.products.matches`.

## Curl Testing

Create a new agent run:

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create documentation for the FastAPI LangGraph project and explain the nodes and edges.",
    "context": {
      "source": "curl"
    },
    "max_revisions": 2
  }'
```

Read graph metadata:

```bash
curl http://127.0.0.1:8000/agent/graph
```

Read service health:

```bash
curl http://127.0.0.1:8000/health
```

## How The Agent API Works

`POST /agent/run` receives an `AgentRequest` from `app/agents/schemas.py`.
FastAPI validates the JSON body before the graph starts.

The endpoint calls `run_agent()` in `app/agents/graph.py`. That function creates
the initial `AgentState`:

```python
{
    "request": query,
    "context": context or {},
    "max_revisions": max_revisions,
    "revision_count": 0,
    "trace": [],
    "route_history": [],
    "pending_tools": [],
    "completed_tools": [],
    "artifacts": {},
}
```

The compiled LangGraph workflow then runs through these main phases:

1. `intake`: normalize the query and detect intent.
2. `safety_guard`: allow or refuse the request.
3. `planner`: create a plan and choose tools.
4. `human_clarification`: ask for missing human context when needed.
5. `tool_router`: run selected tools until none remain.
6. `synthesize`: create the draft answer.
7. `critic`: score the draft and decide whether repair is needed.
8. `repair`: improve the draft when needed.
9. `finalize`: return the final API response.

The endpoint converts the final graph state into `AgentResponse`, then returns
JSON to the browser UI, Swagger, or curl.
