# Architecture

## Runtime Overview

FastAPI accepts an agent request and invokes a compiled LangGraph `StateGraph`.
Each node returns a partial state update. Normal and conditional edges decide
which node runs next.

Product intent, product constraints, missing questions, and product results are
model-backed. The production application does not contain a product catalog.

## Files

| File | Responsibility |
|---|---|
| `app/main.py` | Loads `.env`, creates FastAPI, serves the UI, and exposes the API. |
| `app/ui.py` | Renders the test UI and resubmits accumulated human answers. |
| `app/agents/graph.py` | Registers nodes, connects edges, compiles the graph, and exports graph metadata. |
| `app/agents/nodes.py` | Implements intake, safety, model analysis, clarification, tools, synthesis, critique, repair, and finalization. |
| `app/agents/product_model.py` | Defines typed schemas, the provider protocol, Gemini/OpenAI implementations, grounded search, and errors. |
| `app/agents/commerce.py` | Defines the order gateway protocol and non-charging demo implementation. |
| `app/agents/llm.py` | Optionally uses the configured provider for non-product synthesis. |
| `app/agents/tools.py` | Provides local knowledge, safe arithmetic, and workspace inspection. |
| `app/agents/state.py` | Defines the shared `AgentState` keys. |
| `app/agents/schemas.py` | Defines FastAPI request and response bodies. |
| `tests/conftest.py` | Injects a fake model for deterministic offline tests. |
| `tests/test_agent_graph.py` | Verifies routes, human pauses, results, API behavior, and errors. |

## Model Boundary

`ProductModel` has two operations:

```python
analyze_request(query, collected_context) -> ProductRequestAnalysis
recommend_products(query, analysis) -> ProductSearchResult
```

The default Gemini implementation uses:

- `models.generate_content(...)` with a JSON schema for typed analysis.
- Gemini Google Search grounding for current product research.
- A second JSON-schema call for validated product results.

Set `MODEL_PROVIDER=openai` to use the optional OpenAI implementation.

This boundary keeps LangGraph independent from the provider implementation and
allows tests to inject a fake model without changing graph code.

## State

Important state keys include:

| Key | Meaning |
|---|---|
| `request` | Original user query. |
| `context.human_answers` | Answers accumulated by the client. |
| `normalized_request` | Model-normalized request. |
| `intent` | Model-derived intent. |
| `model_analysis` | Structured constraints and unanswered questions. |
| `model_used` | Runtime model name. |
| `model_error` | Configuration or execution error. |
| `pending_tools` | Ordered tools waiting to run. |
| `artifacts.products` | Structured model product results. |
| `context.cart` | Cart persisted by the client between stateless runs. |
| `artifacts.cart` | Updated cart returned by `cart_tool` or `checkout_tool`. |
| `artifacts.order` | Cancelled or confirmed demo order receipt. |
| `human_questions` | Questions returned to the client. |
| `trace` | Node execution observations. |
| `route_history` | Dynamic edge choices. |

## Human Interaction

The current API is stateless:

1. The model analyzes the request.
2. A clarification node returns `status: needs_input`.
3. The client collects answers.
4. The client creates another run using the same query and merged answers.
5. The model analyzes the enriched request again.
6. The graph either asks another question or continues to product, cart, or
   checkout tools.

## Checkout Guard

`checkout_tool` enforces confirmation independently of the model:

- `order_confirmed=None`: checkout returns an error instead of placing.
- `order_confirmed=false`: checkout records cancellation and keeps the cart.
- `order_confirmed=true`: checkout validates shipping fields and calls the
  configured order gateway.

The current `DemoOrderGateway` produces a simulated receipt. It masks the email
in the receipt, stores no payment credentials, charges nobody, and clears the
cart only after confirmed placement.

For a persistent production workflow, add a checkpointer and `thread_id` so the
same LangGraph execution can resume instead of replaying accumulated context.

## Error Behavior

There is no catalog fallback. A missing provider key or SDK, or a failed model
call, produces `status: error`, a user-facing message, trace details, and a
conditional edge to `finalize`.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | `GET` | Browser test UI. |
| `/health` | `GET` | Process health. |
| `/agent/graph` | `GET` | Node, edge, and Mermaid metadata. |
| `/agent/run` | `POST` | Create one agent execution. |

## Production Considerations

- Store API keys in a secret manager.
- Add authentication, rate limiting, request IDs, and structured logs.
- Add timeouts and retries around model and web-search calls.
- Add a LangGraph checkpointer for resumable conversations.
- Cache safe repeated searches where freshness requirements allow it.
- Validate retailer URLs and add an approved-domain policy if needed.
- Record model, token, latency, and tool-use metrics.
- Treat price, stock, shipping, color, and size as changeable external facts.
- Use tokenized payment methods and provider-hosted checkout for real payments.
- Preserve an auditable record of the user's final order confirmation.
