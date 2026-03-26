"""LLM client abstraction — protocol + Ollama implementation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import ollama as _ollama


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every LLM backend must satisfy."""

    def generate(self, system_prompt: str, user_prompt: str) -> str: ...

    def generate_with_history(self, messages: list[dict[str, str]]) -> str: ...


class OllamaClient:
    """Wrapper around the ``ollama`` Python library."""

    def __init__(
        self,
        model: str = "gemma3:1b",
        host: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self._client = _ollama.Client(host=host)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.message.content

    def generate_with_history(self, messages: list[dict[str, str]]) -> str:
        """Call LLM with an explicit list of conversation messages."""
        response = self._client.chat(
            model=self.model,
            messages=messages,
        )
        return response.message.content

