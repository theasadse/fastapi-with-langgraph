# Covered Topics

This project covers the following FastAPI, LangGraph, agent, UI, and testing
topics.

## Project Setup

| Topic | Where To Read |
| --- | --- |
| Python virtual environment setup | `README.md` |
| Installing project dependencies | `README.md` |
| Optional OpenAI model configuration | `README.md`, `docs/ARCHITECTURE.md` |
| Running Uvicorn locally | `README.md` |
| Local-first deterministic agent behavior | `README.md`, `docs/ARCHITECTURE.md` |

## FastAPI Topics

| Topic | Where To Read |
| --- | --- |
| FastAPI application entrypoint | `app/main.py`, `docs/ARCHITECTURE.md` |
| Health endpoint | `GET /health`, `docs/ARCHITECTURE.md` |
| Graph metadata endpoint | `GET /agent/graph`, `docs/API_TESTING.md` |
| Agent run endpoint | `POST /agent/run`, `docs/API_TESTING.md` |
| Browser test UI endpoint | `GET /`, `docs/API_TESTING.md` |
| Favicon handling | `GET /favicon.ico`, `app/main.py` |
| Pydantic request and response schemas | `app/agents/schemas.py`, `docs/ARCHITECTURE.md` |
| Swagger/OpenAPI testing | `http://127.0.0.1:8000/docs`, `docs/API_TESTING.md` |

## LangGraph Topics

| Topic | Where To Read |
| --- | --- |
| `StateGraph` workflow setup | `app/agents/graph.py`, `docs/NODES_AND_EDGES.md` |
| `START` and `END` graph boundaries | `app/agents/graph.py`, `docs/NODES_AND_EDGES.md` |
| Normal edges | `docs/NODES_AND_EDGES.md` |
| Conditional edges | `docs/NODES_AND_EDGES.md` |
| Node registration | `app/agents/graph.py` |
| Graph compilation | `create_agent_graph()` in `app/agents/graph.py` |
| Graph metadata and Mermaid diagram | `GET /agent/graph`, `docs/NODES_AND_EDGES.md` |

## Agent Workflow Topics

| Topic | Node Or File |
| --- | --- |
| Intake and intent detection | `intake_node` |
| Safety guard and refusal path | `safety_guard_node` |
| Planning | `planner_node` |
| Human clarification | `human_clarification_node` |
| Tool routing | `tool_router_node` |
| Research tool | `research_tool_node` |
| Calculator tool | `calculator_tool_node` |
| Code/workspace inspection tool | `code_tool_node` |
| Product search tool | `product_tool_node` |
| Answer synthesis | `synthesize_node` |
| Critique and repair loop | `critic_node`, `repair_node` |
| Final response handling | `finalize_node` |

## Human-In-The-Loop Topics

| Topic | Where To Read |
| --- | --- |
| Returning `status: needs_input` | `docs/API_TESTING.md`, `docs/NODES_AND_EDGES.md` |
| Structured human questions | `human_questions` in `AgentResponse` |
| Text questions | `product_type` question |
| Choice questions | `color` question |
| Yes/no questions | `strict_budget` question |
| Continuing with answers | `context.human_answers` in `docs/API_TESTING.md` |
| UI follow-up form | `app/ui.py` |

## Product Search Topics

| Topic | Where To Read |
| --- | --- |
| Sample product catalog | `PRODUCT_CATALOG` in `app/agents/tools.py` |
| Product type filtering | `search_products()` |
| Color filtering | `search_products()` |
| Strict budget filtering | `strict_budget=yes` |
| Flexible budget filtering | `strict_budget=no` |
| Different products from different answers | `docs/API_TESTING.md` |
| Over-budget product marking | `over_budget` in `artifacts.products.matches` |
| Relaxed alternatives | `alternatives` in `artifacts.products` |

## API Testing Topics

| Topic | Where To Read |
| --- | --- |
| CRUD-style API mapping | `docs/API_TESTING.md` |
| Create operation for agent runs | `POST /agent/run` |
| Read operation for health | `GET /health` |
| Read operation for graph metadata | `GET /agent/graph` |
| Swagger testing | `docs/API_TESTING.md` |
| Curl testing | `docs/API_TESTING.md` |
| Browser UI testing | `app/ui.py`, `docs/API_TESTING.md` |

## UI Topics

| Topic | Where To Read |
| --- | --- |
| Small test UI served by FastAPI | `app/ui.py` |
| Running the agent from the browser | `Run agent` button |
| Loading calculator sample | `Load calculator sample` button |
| Loading product sample | `Load product sample` button |
| Rendering human questions | `renderHumanQuestions()` in `app/ui.py` |
| Continuing with human answers | `Continue with answers` button |
| Viewing trace and route counts | API response panel |

## State And Response Topics

| Topic | Where To Read |
| --- | --- |
| Shared graph state | `AgentState` in `app/agents/state.py` |
| Request schema | `AgentRequest` in `app/agents/schemas.py` |
| Response schema | `AgentResponse` in `app/agents/schemas.py` |
| Graph description schema | `GraphDescription` in `app/agents/schemas.py` |
| Trace logging | `trace` state key |
| Route history logging | `route_history` state key |
| Tool artifacts | `artifacts` state key |
| Human questions | `human_questions` state key |

## Testing Topics

| Topic | Where To Read |
| --- | --- |
| Graph route tests | `tests/test_agent_graph.py` |
| Calculator route test | `test_agent_can_route_to_calculator_tool` |
| Human input required test | `test_product_search_requests_human_input_when_context_is_missing` |
| Human answer continuation test | `test_product_search_continues_after_human_answers` |
| Different product result tests | `test_product_search_changes_results_from_human_answers` |
| Flexible budget test | `test_product_search_budget_answer_changes_results` |
| Refusal test | `test_agent_refuses_blocked_request` |
| API route tests | `test_agent_run_api_creates_agent_execution` |
| UI route test | `test_root_serves_browser_test_ui` |

## Documentation Topics

| Document | Covers |
| --- | --- |
| `README.md` | Setup, run commands, endpoint overview, human interaction example, docs links. |
| `docs/ARCHITECTURE.md` | File roles, runtime flow, state, endpoints, model behavior, agent complexity. |
| `docs/API_TESTING.md` | CRUD mapping, browser UI testing, Swagger, curl, human-in-loop API flow. |
| `docs/NODES_AND_EDGES.md` | Graph diagram, nodes, edges, tool loop, human interaction loop, critique loop. |
| `docs/TOPICS.md` | Complete topic index for the project. |
