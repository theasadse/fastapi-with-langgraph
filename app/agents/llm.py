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
    use_openai = _env_flag("AGENT_USE_OPENAI")
    model_name = os.getenv("OPENAI_MODEL", "gpt-5.5").strip() or "gpt-5.5"
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not use_openai or not api_key:
        return LocalHeuristicModel()

    try:
        return OpenAITextModel(api_key=api_key, model_name=model_name)
    except ImportError:
        return LocalHeuristicModel()
