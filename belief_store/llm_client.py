"""LLM client abstraction — protocol + Ollama implementation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import ollama as _ollama


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every LLM backend must satisfy."""

    def generate(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str: ...

    def generate_with_history(self, messages: list[dict[str, str]], model: str | None = None) -> str: ...


class OllamaClient:
    """Wrapper around the ``ollama`` Python library."""

    def __init__(
        self,
        model: str = "qwen3:4b",
        host: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self._client = _ollama.Client(host=host)

    def generate(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        response = self._client.chat(
            model=model or self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            think=False,
        )
        return response.message.content

    def generate_with_history(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        """Call LLM with an explicit list of conversation messages."""
        response = self._client.chat(
            model=model or self.model,
            messages=messages,
            think=False,
        )
        return response.message.content
