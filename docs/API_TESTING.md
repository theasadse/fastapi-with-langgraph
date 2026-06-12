# API Testing

## Start The Service

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open:

- UI: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`

## CRUD Analogy

The example begins with the create operation:

```text
POST /agent/run
```

Each POST creates a new graph execution. It is not yet a stored AgentRun
resource, so read, update, delete, and resume-by-ID endpoints are not included.
A production CRUD expansion could add:

| Operation | Suggested endpoint |
|---|---|
| Create run | `POST /agent/runs` |
| Read run | `GET /agent/runs/{run_id}` |
| Continue run | `POST /agent/runs/{run_id}/responses` |
| Cancel/delete run | `DELETE /agent/runs/{run_id}` |

## First Product Request

```bash
curl -sS -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find a product under 50 dollars.",
    "max_revisions": 1
  }'
```

An incomplete request returns HTTP 200 with an application status:

```json
{
  "status": "needs_input",
  "human_questions": [
    {
      "id": "product_type",
      "question": "Which product name or type should I search for?",
      "type": "text",
      "options": [],
      "required": true
    }
  ]
}
```

Question wording and options come from the model and may differ. Use each
question's `id` as the key in `context.human_answers`.

## Continue With Answers

```bash
curl -sS -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find a product under 50 dollars.",
    "context": {
      "human_answers": {
        "product_type": "running shoe",
        "color": "blue",
        "strict_budget": "yes"
      }
    },
    "max_revisions": 1
  }'
```

If the model decides size is required, the response remains `needs_input`.
Resubmit all previous answers plus size:

```json
{
  "human_answers": {
    "product_type": "running shoe",
    "color": "blue",
    "strict_budget": "yes",
    "size": "9"
  }
}
```

The completed response stores structured results under:

```text
artifacts.products.applied_filters
artifacts.products.matches
artifacts.products.alternatives
artifacts.products.caveats
artifacts.products.model
artifacts.products.search_used
```

Each recommendation can include `name`, `category`, `price`, `currency`,
`color`, `size_options`, `reason`, `source_url`, `availability_note`, and
`over_budget`.

## Add To Cart

```bash
curl -sS -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Add Blue Running Shoe to my cart.",
    "context": {
      "human_answers": {
        "size": "9",
        "color": "blue",
        "quantity": "1",
        "unit_price": "39.99"
      }
    }
  }'
```

Copy `artifacts.cart` into `context.cart` for the next stateless request. The
browser UI does this automatically.

## Checkout

First send `Checkout my cart and place the order` with `context.cart`. The model
asks for shipping fields. Resubmit the accumulated answers:

```json
{
  "shipping_name": "Test Customer",
  "shipping_address": "123 Test Street",
  "shipping_city": "Karachi",
  "shipping_region": "Sindh",
  "shipping_postal_code": "74000",
  "shipping_country": "Pakistan",
  "contact_email": "customer@example.com"
}
```

The next response asks only:

```json
{
  "id": "confirm_order",
  "type": "yes_no",
  "options": ["yes", "no"]
}
```

Resubmit all answers with `"confirm_order": "yes"`. The demo gateway returns
`artifacts.order.status=simulated_placed`. Answering `no` returns
`status=cancelled` and leaves the cart unchanged.

No payment card or bank fields are collected. A real order requires a retailer
API and tokenized payment integration behind `OrderGateway`.

## Model Error

Without `OPENAI_API_KEY`, the API returns a normal `AgentResponse` with:

```json
{
  "status": "error",
  "answer": "The model-backed agent could not complete this request..."
}
```

This is deliberate. Product requests never fall back to static products.

## Browser UI

1. Select `Load product sample`.
2. Run the agent.
3. Complete the generated controls.
4. Select `Continue with answers`.
5. Repeat if the model asks a size question.
6. Use `Add to cart`, complete variant questions, and inspect `artifacts.cart`.
7. Use `Checkout`, complete shipping fields, and confirm yes or no.
8. Inspect `trace`, `route_history`, `artifacts.order`, and the cleared cart.

The UI merges new answers with earlier answers before creating the next run.

## Automated Tests

```bash
.venv/bin/python -m pytest -q
```

Tests inject `FakeProductModel` through `get_product_model`. This checks graph
behavior and response schemas without a network call. It is test data, not a
runtime product fallback.

## Useful Assertions

- Generic shopping prompts produce `intent=product_search`.
- Missing preferences produce `status=needs_input`.
- Shirt or shoe requests can produce a second size checkpoint.
- Different human answers reach different fake-model outputs.
- Model errors route directly to `finalize`.
- Product results contain source links when web search is reported as used.
- Unsafe requests finish before model analysis.
- Cart actions preserve product variants and quantity.
- Checkout collects shipping before asking for final confirmation.
- Confirmed checkout creates a simulated order and clears the cart.
- A `no` answer cancels checkout and keeps the cart.
