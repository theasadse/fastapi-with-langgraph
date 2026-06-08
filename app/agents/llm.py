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


class LangChainChatModel:
    source = "openai"

    def __init__(self, model_name: str) -> None:
        from langchain_openai import ChatOpenAI

        self._model = ChatOpenAI(model=model_name, temperature=0.2)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._model.invoke(
            [
                ("system", system_prompt),
                ("user", user_prompt),
            ]
        )
        return str(response.content)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_model_client() -> ModelClient:
    use_openai = _env_flag("AGENT_USE_OPENAI")
    model_name = os.getenv("OPENAI_MODEL", "").strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not use_openai or not model_name or not api_key:
        return LocalHeuristicModel()

    try:
        return LangChainChatModel(model_name=model_name)
    except ImportError:
        return LocalHeuristicModel()
