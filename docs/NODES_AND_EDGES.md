# Nodes And Edges

This document explains how the LangGraph workflow is connected. The source of
truth is `app/agents/graph.py`.

## Graph Diagram

```mermaid
flowchart TD
    START([START]) --> intake
    intake --> safety_guard
    safety_guard -- allowed --> planner
    safety_guard -- refused --> finalize
    planner --> tool_router
    tool_router -- research --> research_tool
    tool_router -- calculator --> calculator_tool
    tool_router -- code --> code_tool
    tool_router -- no pending tools --> synthesize
    research_tool --> tool_router
    calculator_tool --> tool_router
    code_tool --> tool_router
    synthesize --> critic
    critic -- needs revision --> repair
    repair --> critic
    critic -- pass or max revisions --> finalize
    finalize --> END([END])
```

## Nodes

| Node | Function | What It Does |
| --- | --- | --- |
| `intake` | `intake_node` | Cleans the user request and classifies the broad intent. |
| `safety_guard` | `safety_guard_node` | Checks for blocked request patterns before the agent plans or uses tools. |
| `planner` | `planner_node` | Builds the plan and chooses tools for the request. |
| `tool_router` | `tool_router_node` | Looks at `pending_tools` and decides which tool should run next. |
| `research_tool` | `research_tool_node` | Adds local knowledge-base facts to `artifacts["research"]`. |
| `calculator_tool` | `calculator_tool_node` | Safely evaluates arithmetic and stores the result in `artifacts["calculation"]`. |
| `code_tool` | `code_tool_node` | Inspects the current workspace and stores file metadata in `artifacts["code"]`. |
| `synthesize` | `synthesize_node` | Creates a draft answer from the plan and artifacts. |
| `critic` | `critic_node` | Scores the draft and decides whether repair is needed. |
| `repair` | `repair_node` | Adds missing sections or details identified by the critic. |
| `finalize` | `finalize_node` | Produces the final answer or refusal message. |

## Edges

| From | To | Type | Condition |
| --- | --- | --- | --- |
| `START` | `intake` | Normal | Every run starts here. |
| `intake` | `safety_guard` | Normal | Intake always hands off to safety. |
| `safety_guard` | `planner` | Conditional | `route_after_safety()` returns `plan`. |
| `safety_guard` | `finalize` | Conditional | `route_after_safety()` returns `refuse`. |
| `planner` | `tool_router` | Normal | Planning always routes into the tool loop. |
| `tool_router` | `research_tool` | Conditional | `route_tools()` returns `research`. |
| `tool_router` | `calculator_tool` | Conditional | `route_tools()` returns `calculator`. |
| `tool_router` | `code_tool` | Conditional | `route_tools()` returns `code`. |
| `tool_router` | `synthesize` | Conditional | `route_tools()` returns `synthesize` when no tools remain. |
| `research_tool` | `tool_router` | Normal | Tool completes and returns to the router. |
| `calculator_tool` | `tool_router` | Normal | Tool completes and returns to the router. |
| `code_tool` | `tool_router` | Normal | Tool completes and returns to the router. |
| `synthesize` | `critic` | Normal | Every draft is reviewed. |
| `critic` | `repair` | Conditional | `route_after_critic()` returns `repair`. |
| `critic` | `finalize` | Conditional | `route_after_critic()` returns `finalize`. |
| `repair` | `critic` | Normal | Repaired drafts are reviewed again. |
| `finalize` | `END` | Normal | Final output ends the graph run. |

## Tool Loop

The planner stores selected tools in `pending_tools`. The router always reads the
first item:

- If the first item is `research`, the graph runs `research_tool`.
- If the first item is `calculator`, the graph runs `calculator_tool`.
- If the first item is `code`, the graph runs `code_tool`.
- If no items remain, the graph moves to `synthesize`.

Each tool removes itself from `pending_tools`, adds its output to `artifacts`,
adds itself to `completed_tools`, and returns to `tool_router`.

## Critique And Repair Loop

The `critic` node checks the draft for length, plan visibility, tool findings,
FastAPI mention, and LangGraph mention. If issues remain and `revision_count` is
below `max_revisions`, the graph routes to `repair`. The repair node updates the
draft and sends it back to `critic`.

The loop stops when either:

- The critic finds no required repair.
- The maximum revision count is reached.

After that, the graph routes to `finalize`.
