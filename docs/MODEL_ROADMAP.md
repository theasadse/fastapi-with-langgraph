# Model Implementation Roadmap

## What Changed

The earlier learning version used static keyword intent detection and a sample
catalog. That was useful for proving graph mechanics before paying for model
calls, but it was not a real product agent.

The current version moves these responsibilities to the model:

1. Intent classification.
2. Product constraint extraction.
3. Missing-information questions.
4. Live product research when web search is enabled.
5. Structured product recommendations.

LangGraph still owns orchestration, state, pauses, routes, retries, and final
response behavior. The model supplies judgment and content inside those nodes.

## Delivery Phases

### Phase 1: Typed Model Boundary

- Define Pydantic schemas for analysis, questions, filters, and products.
- Define a provider-neutral `ProductModel` protocol.
- Fail clearly when the provider is not configured.

Status: implemented.

### Phase 2: Human-In-The-Loop Graph

- Analyze the original query.
- Pause for base product details.
- Reanalyze with human answers.
- Pause separately for size when required.
- Continue only when model analysis reports enough context.

Status: implemented with stateless resubmission.

### Phase 3: Current Product Research

- Use Gemini Google Search grounding for current candidates.
- Prefer retailer or official product pages.
- Structure results with sources and caveats.
- Avoid invented price, stock, color, and size claims.

Status: implemented; final quality depends on model and available web evidence.

### Phase 4: Persistent Resume

- Add a LangGraph checkpointer.
- Generate a `thread_id` or `run_id`.
- Add an endpoint for human responses.
- Resume the existing graph state instead of replaying the query.

Status: recommended next step.

### Phase 5: Commerce Integrations

- The current demo implements cart state, shipping collection, final
  confirmation, cancellation, and simulated placement.
- Add retailer APIs, affiliate feeds, or internal inventory tools.
- Replace `DemoOrderGateway` with a real authenticated order gateway.
- Use provider-hosted, tokenized payment collection; never send raw card data
  through model prompts or graph state.
- Normalize currency, shipping, tax, stock, variants, and seller trust.
- Use deterministic filters after model extraction.
- Keep the model for interpretation and ranking, not authoritative inventory.

Status: production roadmap.

### Phase 6: Reliability And Evaluation

- Add retry, timeout, and circuit-breaker policies.
- Evaluate intent accuracy and question usefulness.
- Measure grounded-product rate and broken-link rate.
- Track token cost, web-search cost, latency, and conversion outcomes.
- Add prompt and model versioning.

Status: production roadmap.

## Recommended Production Shape

The strongest architecture is hybrid:

- Model: understand natural language, decide missing details, rank and explain.
- LangGraph: control workflow, human pauses, retries, and state.
- Product APIs or search tools: provide current factual inventory.
- Deterministic code: enforce budget, currency, stock, and compliance rules.

This project uses web search as the factual tool because no retailer API was
provided. For a real store, replace or supplement web search with the store's
catalog API while keeping the same `ProductModel` and graph contracts.
