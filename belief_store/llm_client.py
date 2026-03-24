"""
LLM client abstraction for the belief-aware system.

Provides:
  - ``LLMClient`` — protocol (interface) for any LLM backend.
  - ``OllamaClient`` — concrete implementation using a local Ollama server.

The LLM is the *explanation layer only*: it reads clean beliefs and
produces reasoning/answers.  It never writes to the BeliefStore.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import ollama as _ollama


# ── Abstract protocol ────────────────────────────────────────────────


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every LLM backend must satisfy."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send system + user messages and return the model's text reply."""
        ...


# ── Ollama implementation ────────────────────────────────────────────


class OllamaClient:
    """Thin wrapper around the ``ollama`` Python library.

    Parameters
    ----------
    model:
        Name of the Ollama model to use (default: ``gemma3:1b``).
    host:
        Base URL of the Ollama server (default: ``http://localhost:11434``).
    """

    def __init__(
        self,
        model: str = "gemma3:1b",
        host: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self._client = _ollama.Client(host=host)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama and return the assistant's text response.

        Raises
        ------
        ``ollama.ResponseError``
            If the model is not found or the server returns an error.
        ``httpx.ConnectError``
            If the Ollama server is unreachable.
        """
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.message.content
