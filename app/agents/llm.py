from __future__ import annotations

import os
from functools import lru_cache
from typing import Protocol


class ModelClient(Protocol):
    source: str

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return text from the configured model."""


class LocalHeuristicModel:
    source = "local"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        lines = [line.strip() for line in user_prompt.splitlines() if line.strip()]
        useful_lines = lines[:8]
        return "\n".join(useful_lines)


class GeminiTextModel:
    source = "gemini"

    def __init__(self, api_key: str, model_name: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=f"{system_prompt}\n\n{user_prompt}",
        )
        return str(response.text or "")


class OpenAITextModel:
    source = "openai"

    def __init__(self, api_key: str, model_name: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.responses.create(
            model=self._model_name,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_model_client() -> ModelClient:
    use_model = _env_flag(
        "AGENT_USE_MODEL",
        default=_env_flag("AGENT_USE_OPENAI"),
    )
    provider = os.getenv("MODEL_PROVIDER", "gemini").strip().lower() or "gemini"

    if not use_model:
        return LocalHeuristicModel()

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model_name = (
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
            or "gemini-3.5-flash"
        )
        if not api_key:
            return LocalHeuristicModel()
        try:
            return GeminiTextModel(api_key=api_key, model_name=model_name)
        except ImportError:
            return LocalHeuristicModel()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model_name = os.getenv("OPENAI_MODEL", "gpt-5.5").strip() or "gpt-5.5"
        if not api_key:
            return LocalHeuristicModel()
        try:
            return OpenAITextModel(api_key=api_key, model_name=model_name)
        except ImportError:
            return LocalHeuristicModel()

    return LocalHeuristicModel()
