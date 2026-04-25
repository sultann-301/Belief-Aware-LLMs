"""Prompt profiles and builders for evaluation and simulation flows.

This module deliberately decouples evaluation prompts from the runtime engine
fallback prompt. Evaluation should select a prompt profile explicitly.
"""

from __future__ import annotations

import os

from belief_store.prompts import SYSTEM_PROMPTS

DEFAULT_EVAL_PROMPT_VERSION = "v5"

_EVAL_SYSTEM_PROMPT_SUFFIX = """\

ANSWER FORMAT:
For multiple-choice questions, you MUST format your final answer exactly as:
ANSWER: [exact phrase from options]

Rules:
1. Wrap the phrase in square brackets: [like this]
2. Use the EXACT text from the options (case-sensitive, match punctuation)
3. Do NOT add anything after the closing bracket
4. This MUST be the last line of your response
Example: ANSWER: [approved, manual_review]
"""

BASELINE_SYSTEM_PROMPT = """\
You are a reasoning assistant evaluating facts over a conversation.
You will receive [NEW BELIEF] updates. You MUST remember all previous facts across the conversation.

First, output your reasoning starting with REASONING:
IMPORTANT: For multiple-choice questions, you MUST end your response with
the word ANSWER: followed by the EXACT phrase from the options (without brackets).
Do not write anything after the phrase.
"""


def get_eval_prompt_version(prompt_version: str | None = None) -> str:
    """Resolve prompt version from explicit input or environment."""
    return prompt_version or os.getenv("EVAL_BASE_PROMPT_VERSION", DEFAULT_EVAL_PROMPT_VERSION)


def _get_eval_base_prompt(prompt_version: str | None = None) -> str:
    """Return the base system prompt text for evaluation."""
    version = get_eval_prompt_version(prompt_version)
    prompt = SYSTEM_PROMPTS.get(version)
    if prompt is None:
        available = ", ".join(sorted(SYSTEM_PROMPTS))
        raise ValueError(
            f"Unknown eval prompt version: {version}. Available versions: {available}"
        )
    return prompt


def build_eval_system_prompt(prompt_version: str | None = None) -> str:
    """Build full system prompt used by evaluation runs."""
    base_prompt = _get_eval_base_prompt(prompt_version)
    return base_prompt.rstrip() + _EVAL_SYSTEM_PROMPT_SUFFIX


def build_store_prompt(beliefs_text: str, question: str) -> str:
    """Build prompt for WITH STORE conditions (beliefs + question)."""
    parts = []
    if beliefs_text:
        parts.append("[RELEVANT BELIEFS]\n" + beliefs_text)
    parts.append(f"[QUERY]\n{question}")
    parts.append("Your final answer: ANSWER: [exact phrase]")
    return "\n\n".join(parts)


def build_baseline_prompt(
    rules: str, belief_updates: list[str], question: str,
) -> str:
    """Build prompt for NO STORE condition (rules + belief updates + question)."""
    parts = [rules]
    if belief_updates:
        parts.append("[NEW BELIEF]\n" + "\n".join(belief_updates))
    parts.append(f"[QUERY]\n{question}")
    parts.append("Your final answer: ANSWER: [exact phrase]")
    return "\n\n".join(parts)


# Backward-compatible default for call sites that do not pass a version.
EVAL_SYSTEM_PROMPT = build_eval_system_prompt()
