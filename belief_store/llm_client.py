"""LLM client abstraction — protocol + Ollama implementation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import hashlib
import json
import os
import sqlite3
import threading

import ollama as _ollama # type: ignore


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every LLM backend must satisfy."""

    def generate(self, system_prompt: str, user_prompt: str, model: str | None = None, json_mode: bool = False) -> str: ...

    def generate_with_history(self, messages: list[dict[str, str]], model: str | None = None, json_mode: bool = False) -> str: ...

    def generate_with_logprobs(self, system_prompt: str, user_prompt: str, model: str | None = None) -> tuple[str, list | None]: ...

    def generate_with_history_and_logprobs(self, messages: list[dict[str, str]], model: str | None = None) -> tuple[str, list | None]: ...


class OllamaClient:
    """Wrapper around the ``ollama`` Python library."""

    def __init__(
        self,
        model: str = "qwen3:4b",
        host: str = "http://localhost:11434",
        think: bool = False,
        temperature: float = 0.5,
        num_predict: int | None = None,
        num_ctx: int | None = None,
        repeat_penalty: float | None = None,
        repeat_last_n: int | None = None,
        top_k: int | None = None,
        top_p: float | None = None,
        keep_alive: str | int | None = None,
        cache_enabled: bool = False,
        cache_path: str | None = None,
    ) -> None:
        self.model = model
        self._client = _ollama.Client(host=host)
        self.think = think
        self.temperature = temperature
        self.num_predict = num_predict
        self.num_ctx = num_ctx
        self.repeat_penalty = repeat_penalty
        self.repeat_last_n = repeat_last_n
        self.top_k = top_k
        self.top_p = top_p
        self.keep_alive = keep_alive
        self._cache = _ResponseCache(cache_path) if cache_enabled and cache_path else None

    def _options(self) -> dict[str, object]:
        """Generation defaults that reduce repetition and runaway loops."""
        return {
            "temperature": self.temperature,
            "num_predict": self.num_predict if self.num_predict is not None else 1024,
            "num_ctx": self.num_ctx if self.num_ctx is not None else 8192,
            "repeat_penalty": self.repeat_penalty if self.repeat_penalty is not None else 1.15,
            "repeat_last_n": self.repeat_last_n if self.repeat_last_n is not None else 128,
            "top_k": self.top_k if self.top_k is not None else 40,
            "top_p": self.top_p if self.top_p is not None else 0.9,
            "think": self.think,
        }

    def _cache_key(self, payload: dict[str, object]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def generate(self, system_prompt: str, user_prompt: str, model: str | None = None, json_mode: bool = False) -> str:
        options = self._options()
        cache_key = None
        if self._cache is not None:
            cache_key = self._cache_key(
                {
                    "mode": "single",
                    "model": model or self.model,
                    "json_mode": json_mode,
                    "system": system_prompt,
                    "user": user_prompt,
                    "options": options,
                }
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        chat_kwargs = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json" if json_mode else None,
            "options": options,
            "think": False,
        }
        if self.keep_alive is not None:
            chat_kwargs["keep_alive"] = self.keep_alive
        response = self._client.chat(**chat_kwargs)
        content = response.message.content
        if self._cache is not None and cache_key is not None:
            self._cache.set(cache_key, content)
        return content

    def generate_with_logprobs(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> tuple[str, list | None]:
        """Generate a response and return (content, logprobs_list).

        logprobs_list is a list of dicts with keys: token, logprob, top_logprobs.
        Returns (content, None) if logprobs are not available.
        """
        options = self._options()
        chat_kwargs = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": options,
            "think": False,
            "logprobs": True,
            "top_logprobs": 3,
        }
        if self.keep_alive is not None:
            chat_kwargs["keep_alive"] = self.keep_alive
        response = self._client.chat(**chat_kwargs)
        content = response.message.content
        raw_logprobs = getattr(response, "logprobs", None)
        logprobs_list = None
        if raw_logprobs:
            logprobs_list = [
                {
                    "token": lp.token,
                    "logprob": lp.logprob,
                    "top_logprobs": [
                        {"token": t.token, "logprob": t.logprob}
                        for t in (lp.top_logprobs or [])
                    ],
                }
                for lp in raw_logprobs
            ]
        return content, logprobs_list

    def generate_with_history(self, messages: list[dict[str, str]], model: str | None = None, json_mode: bool = False) -> str:
        """Call LLM with an explicit list of conversation messages."""
        options = self._options()
        cache_key = None
        if self._cache is not None:
            cache_key = self._cache_key(
                {
                    "mode": "history",
                    "model": model or self.model,
                    "json_mode": json_mode,
                    "messages": messages,
                    "options": options,
                }
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        chat_kwargs = {
            "model": model or self.model,
            "messages": messages,
            "format": "json" if json_mode else None,
            "options": options,
            "think": False,
        }
        if self.keep_alive is not None:
            chat_kwargs["keep_alive"] = self.keep_alive
        response = self._client.chat(**chat_kwargs)
        content = response.message.content
        if self._cache is not None and cache_key is not None:
            self._cache.set(cache_key, content)
        return content

    def generate_with_history_and_logprobs(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> tuple[str, list | None]:
        """Call LLM with conversation history and return (content, logprobs_list)."""
        options = self._options()
        chat_kwargs = {
            "model": model or self.model,
            "messages": messages,
            "options": options,
            "think": False,
            "logprobs": True,
            "top_logprobs": 3,
        }
        if self.keep_alive is not None:
            chat_kwargs["keep_alive"] = self.keep_alive
        response = self._client.chat(**chat_kwargs)
        content = response.message.content
        raw_logprobs = getattr(response, "logprobs", None)
        logprobs_list = None
        if raw_logprobs:
            logprobs_list = [
                {
                    "token": lp.token,
                    "logprob": lp.logprob,
                    "top_logprobs": [
                        {"token": t.token, "logprob": t.logprob}
                        for t in (lp.top_logprobs or [])
                    ],
                }
                for lp in raw_logprobs
            ]
        return content, logprobs_list


_CACHE_INIT_LOCKS: dict[str, threading.Lock] = {}


class _ResponseCache:
    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        init_lock = _CACHE_INIT_LOCKS.setdefault(path, threading.Lock())
        with init_lock:
            self._conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
            try:
                self._conn.execute("PRAGMA journal_mode=WAL;")
            except sqlite3.OperationalError:
                # Another thread/process may be initializing WAL; safe to continue.
                pass
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)"
            )
            self._conn.commit()

    def get(self, key: str) -> str | None:
        with self._lock:
            cursor = self._conn.execute("SELECT value FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)",
                (key, value),
            )
            self._conn.commit()
