from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


Intent = Literal[
    "product_search",
    "add_to_cart",
    "checkout",
    "calculation",
    "software_delivery",
    "documentation",
    "general_assistance",
]
QuestionType = Literal["text", "choice", "yes_no"]


class ModelConfigurationError(RuntimeError):
    """Raised when the product model cannot be configured."""


class ModelExecutionError(RuntimeError):
    """Raised when the configured product model cannot complete a request."""


class ModelQuestion(BaseModel):
    id: str
    question: str
    type: QuestionType
    options: list[str] = Field(default_factory=list)
    required: bool = True


class ProductRequestAnalysis(BaseModel):
    intent: Intent
    normalized_request: str
    product_type: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    unit_price: float | None = None
    quantity: int | None = Field(default=None, ge=1, le=20)
    budget: float | None = None
    currency: str = "USD"
    color: str | None = None
    size: str | None = None
    strict_budget: bool | None = None
    shipping_name: str | None = None
    shipping_address: str | None = None
    shipping_city: str | None = None
    shipping_region: str | None = None
    shipping_postal_code: str | None = None
    shipping_country: str | None = None
    contact_email: str | None = None
    order_confirmed: bool | None = None
    missing_fields: list[str] = Field(default_factory=list)
    questions: list[ModelQuestion] = Field(default_factory=list)
    reasoning_summary: str


class AppliedProductFilters(BaseModel):
    product_type: str | None = None
    budget: float | None = None
    currency: str = "USD"
    color: str | None = None
    size: str | None = None
    strict_budget: bool | None = None


class ProductRecommendation(BaseModel):
    name: str
    category: str
    price: float | None = None
    currency: str = "USD"
    color: str | None = None
    size_options: list[str] = Field(default_factory=list)
    reason: str
    source_url: str | None = None
    availability_note: str | None = None
    over_budget: bool | None = None


class ProductSearchResult(BaseModel):
    summary: str
    applied_filters: AppliedProductFilters
    matches: list[ProductRecommendation] = Field(default_factory=list)
    alternatives: list[ProductRecommendation] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    source: str
    model: str
    search_used: bool


class ProductModel(Protocol):
    model_name: str

    def analyze_request(
        self,
        query: str,
        collected_context: dict[str, Any],
    ) -> ProductRequestAnalysis:
        """Classify the request and return any missing human questions."""

    def recommend_products(
        self,
        query: str,
        analysis: ProductRequestAnalysis,
    ) -> ProductSearchResult:
        """Return model-generated product recommendations."""


class GeminiProductModel:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        enable_google_search: bool,
    ) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ModelConfigurationError(
                'The Google Gen AI SDK is not installed. Run: pip install -e ".[gemini,test]"'
            ) from exc

        self.model_name = model_name
        self.enable_google_search = enable_google_search
        self._client = genai.Client(api_key=api_key)
        self._types = types

    def analyze_request(
        self,
        query: str,
        collected_context: dict[str, Any],
    ) -> ProductRequestAnalysis:
        prompt = (
            f"{_ANALYSIS_SYSTEM_PROMPT}\n\n"
            f"Original request:\n{query}\n\n"
            "Collected conversation context, including human answers, "
            "previous products, and cart:\n"
            f"{json.dumps(collected_context, indent=2, sort_keys=True)}"
        )
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=_gemini_structured_config(ProductRequestAnalysis),
            )
            return ProductRequestAnalysis.model_validate_json(response.text)
        except Exception as exc:
            raise ModelExecutionError(f"Gemini request analysis failed: {exc}") from exc

    def recommend_products(
        self,
        query: str,
        analysis: ProductRequestAnalysis,
    ) -> ProductSearchResult:
        research_text = self._research_products(query, analysis)
        prompt = (
            f"{_PRODUCT_RESULT_SYSTEM_PROMPT}\n\n"
            f"Original request:\n{query}\n\n"
            "Validated request analysis:\n"
            f"{analysis.model_dump_json(indent=2)}\n\n"
            "Grounded research to convert into the response schema:\n"
            f"{research_text}"
        )
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=_gemini_structured_config(ProductSearchResult),
            )
            result = ProductSearchResult.model_validate_json(response.text)
        except Exception as exc:
            raise ModelExecutionError(f"Gemini product structuring failed: {exc}") from exc

        result.model = self.model_name
        result.search_used = self.enable_google_search
        return result

    def _research_products(
        self,
        query: str,
        analysis: ProductRequestAnalysis,
    ) -> str:
        config = None
        if self.enable_google_search:
            grounding_tool = self._types.Tool(
                google_search=self._types.GoogleSearch()
            )
            config = self._types.GenerateContentConfig(tools=[grounding_tool])

        prompt = (
            f"{_PRODUCT_RESEARCH_SYSTEM_PROMPT}\n\n"
            f"Original request:\n{query}\n\n"
            f"Resolved preferences:\n{analysis.model_dump_json(indent=2)}"
        )
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise ModelExecutionError(f"Gemini product research failed: {exc}") from exc

        text = str(response.text or "").strip()
        if not text:
            raise ModelExecutionError("Gemini returned no product research.")

        sources = _gemini_grounding_sources(response)
        if sources:
            text += "\n\nGrounding sources:\n" + json.dumps(sources, indent=2)
        return text


class OpenAIProductModel:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        enable_web_search: bool,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ModelConfigurationError(
                'The OpenAI SDK is not installed. Run: pip install -e ".[openai,test]"'
            ) from exc

        self.model_name = model_name
        self.enable_web_search = enable_web_search
        self._client = OpenAI(api_key=api_key)

    def analyze_request(
        self,
        query: str,
        collected_context: dict[str, Any],
    ) -> ProductRequestAnalysis:
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                input=[
                    {
                        "role": "system",
                        "content": _ANALYSIS_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Original request:\n{query}\n\n"
                            "Collected conversation context, including human answers, "
                            "previous products, and cart:\n"
                            f"{json.dumps(collected_context, indent=2, sort_keys=True)}"
                        ),
                    },
                ],
                text_format=ProductRequestAnalysis,
            )
        except Exception as exc:
            raise ModelExecutionError(f"OpenAI request analysis failed: {exc}") from exc

        if response.output_parsed is None:
            raise ModelExecutionError("OpenAI returned no structured request analysis.")
        return response.output_parsed

    def recommend_products(
        self,
        query: str,
        analysis: ProductRequestAnalysis,
    ) -> ProductSearchResult:
        research_text = self._research_products(query, analysis)
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                input=[
                    {
                        "role": "system",
                        "content": _PRODUCT_RESULT_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": (
                            "Original request:\n"
                            f"{query}\n\n"
                            "Validated request analysis:\n"
                            f"{analysis.model_dump_json(indent=2)}\n\n"
                            "Model research to convert into the response schema:\n"
                            f"{research_text}"
                        ),
                    },
                ],
                text_format=ProductSearchResult,
            )
        except Exception as exc:
            raise ModelExecutionError(f"OpenAI product structuring failed: {exc}") from exc

        if response.output_parsed is None:
            raise ModelExecutionError("OpenAI returned no structured product recommendations.")

        result = response.output_parsed
        result.model = self.model_name
        result.search_used = self.enable_web_search
        return result

    def _research_products(
        self,
        query: str,
        analysis: ProductRequestAnalysis,
    ) -> str:
        tools = [{"type": "web_search"}] if self.enable_web_search else []
        request: dict[str, Any] = {
            "model": self.model_name,
            "input": [
                {
                    "role": "system",
                    "content": _PRODUCT_RESEARCH_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Original request:\n{query}\n\n"
                        "Resolved preferences:\n"
                        f"{analysis.model_dump_json(indent=2)}"
                    ),
                },
            ],
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"

        try:
            response = self._client.responses.create(**request)
        except Exception as exc:
            raise ModelExecutionError(f"OpenAI product research failed: {exc}") from exc

        text = response.output_text.strip()
        if not text:
            raise ModelExecutionError("OpenAI returned no product research.")
        return text


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_product_model() -> ProductModel:
    provider = os.getenv("MODEL_PROVIDER", "gemini").strip().lower() or "gemini"

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model_name = (
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
            or "gemini-3.5-flash"
        )
        if not api_key:
            raise ModelConfigurationError(
                "GEMINI_API_KEY is required because Gemini is the configured "
                "model provider."
            )
        return GeminiProductModel(
            api_key=api_key,
            model_name=model_name,
            enable_google_search=_env_flag(
                "GEMINI_ENABLE_GOOGLE_SEARCH",
                default=True,
            ),
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model_name = os.getenv("OPENAI_MODEL", "gpt-5.5").strip() or "gpt-5.5"
        if not api_key:
            raise ModelConfigurationError(
                "OPENAI_API_KEY is required because OpenAI is the configured "
                "model provider."
            )
        return OpenAIProductModel(
            api_key=api_key,
            model_name=model_name,
            enable_web_search=_env_flag("OPENAI_ENABLE_WEB_SEARCH", default=True),
        )

    raise ModelConfigurationError(
        f"Unsupported MODEL_PROVIDER '{provider}'. Use 'gemini' or 'openai'."
    )


def _gemini_structured_config(schema: type[BaseModel]) -> dict[str, Any]:
    return {
        "response_mime_type": "application/json",
        "response_json_schema": schema.model_json_schema(),
    }


def _gemini_grounding_sources(response: Any) -> list[dict[str, str]]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []

    metadata = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(metadata, "grounding_chunks", None) or []
    sources: list[dict[str, str]] = []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        uri = str(getattr(web, "uri", "") or "").strip()
        title = str(getattr(web, "title", "") or "").strip()
        if uri:
            sources.append({"title": title or uri, "url": uri})
    return sources


_ANALYSIS_SYSTEM_PROMPT = """
You are the request-analysis node in a LangGraph agent.

Return a truthful structured analysis for the complete request. Infer intent from
meaning rather than fixed keyword rules. The possible intents are product_search,
add_to_cart, checkout, calculation, software_delivery, documentation, and
general_assistance.

For product_search:
- Extract product type or name, maximum budget, currency, color, size, and whether
  the budget is strict.
- Treat the supplied human answers as authoritative and merge them with the
  original request.
- Ask only for information that is still missing and useful for producing
  relevant products.
- A generic request such as "find a product under 50 dollars" should ask for
  product_type, color, and strict_budget.
- If the selected product is clothing or footwear and size is missing, include a
  size question. Use suitable options when the answer set is reasonably bounded.
- Use question type yes_no for strict_budget, choice for bounded options, and text
  for open answers.
- Put each unanswered field in missing_fields and questions. Do not ask again for
  a field already answered.

For add_to_cart:
- Resolve product_name from the request, previous product results, or human
  answers. Extract product_url and unit_price only when present in context.
- Default quantity to 1 unless the user requests another quantity.
- Ask for color or size only when the selected product needs that variant and it
  is still missing.
- Do not ask for shipping or payment details.

For checkout:
- Read cart items from context.cart. If the cart is empty and no product was
  supplied, ask which product should be added first.
- Collect shipping_name, shipping_address, shipping_city, shipping_region,
  shipping_postal_code, shipping_country, and contact_email.
- Never ask for card numbers, bank details, passwords, or security codes.
- Ask confirm_order as a yes_no question only after the cart and all required
  shipping fields are complete. This must be the final human checkpoint.
- If confirm_order is no, set order_confirmed=false and ask no more questions.
- If confirm_order is yes, set order_confirmed=true.

For other intents, return no commerce questions. Keep reasoning_summary short
and do not expose private chain-of-thought.
""".strip()


_PRODUCT_RESEARCH_SYSTEM_PROMPT = """
You are the live product-research node in a LangGraph shopping agent. Find
products that satisfy the resolved preferences. Use web search when available.

Requirements:
- Never invent a product, price, retailer, source URL, size, color, or availability.
- Prefer current product or retailer pages over generic list articles.
- Respect a strict budget. If the budget is flexible, clearly identify products
  over budget and keep the stretch modest.
- Return several exact matches when evidence supports them, followed by useful
  alternatives only when exact matches are weak.
- Include full source URLs and note that price and availability can change.
- If live search is unavailable, say that the recommendations are based on model
  knowledge and avoid claiming real-time price or stock.
""".strip()


_PRODUCT_RESULT_SYSTEM_PROMPT = """
Convert the supplied product research into ProductSearchResult without inventing
missing facts.

Use the validated request analysis for applied_filters. Put products satisfying
all important constraints in matches. Put close but imperfect options in
alternatives and explain the difference. Set over_budget by comparing each known
price with the analyzed budget. Use null when price, color, URL, availability, or
budget status is unknown. Keep source URLs from the research. State in caveats
that users should verify final price, shipping, stock, color, and size on the
retailer page. The caller will overwrite model and search_used with runtime
configuration values.
""".strip()
