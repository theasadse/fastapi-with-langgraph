# Architecture

This project is a FastAPI application that exposes a complex LangGraph agent.
The goal is to show how a practical agent can be split into clear files, clear
state, testable node functions, and explicit graph wiring.

## Main Files

| File | Purpose |
| --- | --- |
| `app/main.py` | Creates the FastAPI app and exposes `/health`, `/agent/graph`, and `/agent/run`. |
| `app/agents/graph.py` | Defines the LangGraph workflow, registers every node, connects edges, exports static graph metadata, and runs the compiled graph. |
| `app/agents/nodes.py` | Holds the node functions that perform intake, safety checks, planning, human clarification, tool routing, synthesis, critique, repair, and finalization. |
| `app/agents/tools.py` | Provides local tool functions used by graph nodes: built-in research, safe arithmetic, workspace inspection, and sample product search. |
| `app/agents/state.py` | Defines the shared `AgentState` typed dictionary passed between nodes. |
| `app/agents/schemas.py` | Defines Pydantic request and response models for the API. |
| `app/agents/llm.py` | Provides a deterministic local model and an optional `langchain-openai` adapter. |
| `app/ui.py` | Returns the small HTML, CSS, and JavaScript browser UI for local API testing. |
| `docs/API_TESTING.md` | Explains UI testing, Swagger testing, curl requests, and CRUD-style API mapping. |
| `docs/NODES_AND_EDGES.md` | Documents every node and connection in the graph. |
| `docs/TOPICS.md` | Lists every topic covered by the project and where to read about it. |
| `tests/test_agent_graph.py` | Verifies successful routing, tool use, metadata, and refusal behavior. |

## Main Runtime Flow

1. A client sends `POST /agent/run` with a `query`.
2. `app/main.py` validates the request with `AgentRequest`.
3. `run_agent()` in `app/agents/graph.py` creates the initial `AgentState`.
4. The compiled LangGraph workflow runs from `START` to `END`.
5. Each node reads state and returns only the updates it owns.
6. Conditional edges route based on safety, human context, pending tools, and critique results.
7. If context is missing, the graph returns `status: needs_input` with human questions.
8. FastAPI returns `AgentResponse` with the answer, questions, artifacts, trace, and route history.

## Agent State

The graph state is defined in `app/agents/state.py`. Important keys:

| State Key | Meaning |
| --- | --- |
| `request` | Original user input. |
| `normalized_request` | Cleaned request produced by `intake_node`. |
| `intent` | Broad intent classification such as `software_delivery`. |
| `safety` | Safety decision and reason. |
| `plan` | Ordered plan created by `planner_node`. |
| `human_questions` | Structured questions returned when the agent needs human input. |
| `pending_tools` | Tool queue selected by the planner and consumed by tool nodes. |
| `completed_tools` | Tools that already ran. |
| `artifacts` | Tool outputs used by the synthesis step. |
| `draft` | Draft answer produced before critique. |
| `critique` | Score, issues, and repair decision. |
| `revision_count` | Number of completed repair loops. |
| `final_answer` | Final output returned by the API. |
| `status` | Run status: `ok`, `needs_input`, `refused`, or `error`. |
| `trace` | Human-readable node execution trace. |
| `route_history` | Conditional routes selected during execution. |

## FastAPI Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | `GET` | Opens the small browser test UI. |
| `/health` | `GET` | Confirms the service is running. |
| `/agent/graph` | `GET` | Returns static node, edge, and Mermaid graph metadata. |
| `/agent/run` | `POST` | Creates a new stateless LangGraph agent run for a user query. |

## Model Behavior

The project is local-first. By default, synthesis uses deterministic local logic
so the graph can be tested without network access or paid model calls.

Optional OpenAI-backed synthesis is available when all of these are true:

- `AGENT_USE_OPENAI=true`
- `OPENAI_API_KEY` is set
- `OPENAI_MODEL` is set
- `langchain-openai` is installed with `pip install -e ".[openai]"`

If the optional model cannot be loaded, the agent falls back to local synthesis.

## Why This Agent Is Complex

This example includes the main patterns used in real agent systems:

- A typed state object shared across nodes.
- A safety branch before planning.
- A human clarification branch before tool use.
- A planner that selects tools dynamically.
- A tool loop controlled by conditional edges.
- Multiple tool nodes with separate responsibilities.
- A synthesis step that combines plan and artifacts.
- A critique and repair loop with a maximum revision count.
- A finalizer that handles both success and refusal paths.
