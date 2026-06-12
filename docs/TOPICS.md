# Covered Topics

This index lists the concepts implemented or documented in the project.

## FastAPI

- Application creation and metadata.
- Root browser UI route.
- Health endpoint.
- Typed POST request and response models.
- Swagger/OpenAPI documentation.
- HTTP exception boundary.
- CRUD create-operation analogy and future run-resource endpoints.

## LangGraph

- `StateGraph` and typed shared state.
- `START` and `END`.
- Normal edges.
- Conditional edges.
- Tool router loop.
- Human clarification branches.
- Separate product size branch.
- Critic and repair loop.
- Revision limits.
- Trace and route history.
- Graph metadata and Mermaid diagram.
- Stateless continuation today.
- Checkpointer and `thread_id` roadmap.

## Model Integration

- Provider-neutral model protocol.
- OpenAI Responses API.
- Structured outputs with Pydantic.
- Model-derived intent.
- Model-derived product constraints.
- Model-generated human questions.
- Model errors and configuration errors.
- Optional OpenAI non-product synthesis.
- Model name recorded in state and artifacts.
- No production static product catalog.

## Product Agent

- Generic prompts such as `give me product under 50 dollars`.
- Budget and currency extraction.
- Strict or flexible budget confirmation.
- Product type or name clarification.
- Color clarification.
- Shirt, clothing, shoe, and footwear size clarification.
- Multiple human interaction rounds.
- Different recommendations from different answers.
- Exact matches and alternatives.
- Prices, currencies, colors, sizes, and availability notes.
- Over-budget marking.
- Source URLs.
- Price and stock verification caveats.
- Live web search toggle.

## Cart And Checkout

- `add_to_cart` intent.
- `checkout` intent.
- Product name, quantity, color, and size collection.
- Cart item merging and subtotal calculation.
- Cart persistence between stateless UI requests.
- Shipping name, address, city, region, postal code, country, and email.
- Final `confirm_order` yes/no checkpoint.
- Deterministic confirmation enforcement outside the model.
- Automatic demo placement after explicit yes.
- Cancellation and unchanged cart after no.
- Demo order IDs and masked receipt email.
- Cart clearing after confirmed placement.
- No card, bank, password, or security-code collection.
- `OrderGateway` integration boundary for real commerce.

## Conversational Behavior

- `general_assistance` intent for greetings and casual messages.
- Warm, brief, personal replies.
- Gentle offer to help find a product or assist with another request.
- No internal plans, tools, intent labels, or graph details in casual replies.

## API Calling And UI

- `POST /agent/run` creates one execution.
- `GET /agent/graph` returns graph structure.
- Dynamic rendering of text, choice, and yes/no questions.
- Accumulating `context.human_answers`.
- Resubmitting the same query.
- Status, trace, and route inspection.
- Product and calculator samples.
- Add-to-cart and checkout samples.
- Error display.

## Testing

- Fake model dependency injection.
- No paid or network model calls in tests.
- Complex delivery route.
- Calculator route.
- Generic product intent.
- Missing human input.
- Shirt size pause and completion.
- Shoe size pause and completion.
- Different answers and recommendations.
- Flexible budget behavior.
- Safety refusal.
- Graph node and edge metadata.
- Root UI response.
- Agent API response.
- Missing model configuration.
- Add-to-cart size checkpoint and cart creation.
- Shipping collection before confirmation.
- Confirmed demo placement and cart clearing.
- Checkout cancellation.

## Production Roadmap

- Persistent LangGraph checkpoints.
- Run and conversation IDs.
- Retailer or inventory APIs.
- Authentication and authorization.
- Secret management.
- Rate limiting.
- Timeouts, retries, and circuit breakers.
- Approved-source policies.
- Observability and token-cost tracking.
- Caching with freshness controls.
- Prompt and model versioning.
- Evaluation datasets and quality metrics.

See `ARCHITECTURE.md`, `API_TESTING.md`, `MODEL_ROADMAP.md`, and
`NODES_AND_EDGES.md` for the detailed implementation.
