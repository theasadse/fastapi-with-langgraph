# FastAPI With LangGraph

A model-backed LangGraph example with FastAPI, a browser test UI, structured
Gemini outputs, optional Google Search grounding, human clarification, tool
routing, cart actions, confirmed checkout, critique, repair, and traceable graph
state.

The production product flow contains no sample catalog. The model analyzes the
request, generates missing questions, researches products, and returns typed
recommendations.

## Project Structure

```text
.
|-- app/
|   |-- main.py                    # FastAPI app and HTTP endpoints
|   |-- ui.py                      # Small browser UI for manual testing
|   `-- agents/
|       |-- graph.py               # LangGraph nodes, edges, and compiled graph
|       |-- nodes.py               # Node behavior and routing functions
|       |-- product_model.py       # Gemini/OpenAI analysis and product search
|       |-- commerce.py            # Order gateway protocol and safe demo gateway
|       |-- llm.py                 # Optional non-product model synthesis
|       |-- tools.py               # Research, calculator, and workspace tools
|       |-- state.py               # Shared graph state
|       `-- schemas.py             # FastAPI request and response models
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- API_TESTING.md
|   |-- MODEL_ROADMAP.md
|   |-- NODES_AND_EDGES.md
|   `-- TOPICS.md
|-- tests/
|   |-- conftest.py                # Injected fake model for offline tests
|   `-- test_agent_graph.py
|-- pyproject.toml
`-- .env.example
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[gemini,test]"
cp .env.example .env
```

Set your key in `.env`:

```dotenv
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash
GEMINI_ENABLE_GOOGLE_SEARCH=true
AGENT_USE_MODEL=true
```

Create a key in [Google AI Studio](https://aistudio.google.com/apikey).
`GEMINI_API_KEY` is required for request analysis and product recommendations.
Google may provide free-tier quota, but current limits depend on its pricing and
your account.

OpenAI remains an optional provider:

```dotenv
MODEL_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-5.5
```

## Run

```bash
uvicorn app.main:app --reload
```

- Browser UI: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Graph metadata: [http://127.0.0.1:8000/agent/graph](http://127.0.0.1:8000/agent/graph)

## Model Product Flow

First request:

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find a product under 50 dollars.",
    "max_revisions": 1
  }'
```

The model typically returns questions for product type, color, and whether the
budget is strict. Send the same query again with the answers:

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
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

If size is still missing, the graph returns `needs_input` again. After size is
provided, the product node performs model research and returns products in
`artifacts.products.matches`, including reasons, prices when supported, source
URLs, and verification caveats.

## Cart And Checkout Flow

The model also recognizes `add_to_cart` and `checkout`.

```text
Add Blue Running Shoe to my cart.
```

The graph asks for missing variants such as shoe size, then `cart_tool` returns
the updated cart in `artifacts.cart`. The browser UI copies that cart into the
next request context.

```text
Checkout my cart and place the order.
```

Checkout happens in three stages:

1. Collect shipping name, address, city, region, postal code, country, and email.
2. Ask the final yes/no question `confirm_order`.
3. Run `checkout_tool` only when the answer is `yes`.

The included `DemoOrderGateway` returns `status=simulated_placed`, clears the
cart, and creates a demo order ID. It never requests card details and does not
charge a retailer or payment processor. Replace this gateway with authenticated
commerce and payment integrations for real ordering.

## API Semantics

`POST /agent/run` behaves like the create operation in a CRUD API: each call
creates one graph execution. Human continuation is currently stateless. The
client resends the original query plus accumulated `context.human_answers`,
`context.previous_products`, and `context.cart`.

Product completion can involve these model calls:

1. Structured request analysis.
2. Another structured analysis after each human response.
3. Product research, optionally using Google Search grounding.
4. Structured conversion of research into the product response schema.

Tests do not call Gemini or OpenAI. They inject a fake implementation of the typed
model protocol.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API testing and human interaction](docs/API_TESTING.md)
- [Model implementation roadmap](docs/MODEL_ROADMAP.md)
- [Nodes and edges](docs/NODES_AND_EDGES.md)
- [Complete project guide and all covered topics](docs/TOPICS.md)

## References

- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini Google Search grounding](https://ai.google.dev/gemini-api/docs/google-search)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
