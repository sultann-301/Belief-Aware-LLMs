"""Prompt profiles and builders for evaluation and simulation flows.

This module deliberately decouples evaluation prompts from the runtime engine
fallback prompt. Evaluation should select a prompt profile explicitly.
"""

from __future__ import annotations

import os

from belief_store.prompts import SYSTEM_PROMPTS

DEFAULT_EVAL_PROMPT_VERSION = "v15"
DEFAULT_BASELINE_PROMPT_VERSION = "v1"

_EVAL_SYSTEM_PROMPT_SUFFIX = """\

ANSWER FORMAT:
For multiple-choice questions, you MUST format your final answer exactly as:
ANSWER: [exact phrase from options]


Rules:
1. Wrap the phrase in square brackets: [like this]
2. Use the EXACT text from the options (case-sensitive, match punctuation)
3. Do NOT add anything after the closing bracket
4. The ANSWER line MUST be the last line of your response
"""

_BASELINE_SYSTEM_PROMPT_V1 = """\

You are a reasoning assistant evaluating facts over a conversation.
You will receive [NEW BELIEF] updates. You MUST remember all previous facts across the conversation.

First, output your reasoning starting with REASONING:

IMPORTANT: For multiple-choice questions, you MUST end your response with:
1. An ANSWER line with the EXACT phrase from the options (without extra text)
2. The ANSWER line must be the last line of your response
Example:
  Based on my analysis, I believe the answer is [option text]
  ANSWER: [option text]
"""


_BASELINE_SYSTEM_PROMPT_V2 = """\

You are a reasoning assistant evaluating facts over a conversation.
You will receive [NEW BELIEF] updates. You MUST remember all previous facts across the conversation.

Do not provide a reasoning block.

For every answer, first list the exact belief keys that support your answer, then give the answer.

IMPORTANT: For multiple-choice questions, you MUST end your response with:
1. A CITED KEYS line containing only the exact belief keys used to support YOUR CHOSEN ANSWER
2. An ANSWER line with the EXACT phrase from the options (without extra text)
3. The CITED KEYS and ANSWER lines must be consecutive, with CITED KEYS first

Your cited keys must be tied to your answer, not arbitrary.
Example:
    CITED KEYS: [applicant.credit_score, loan.min_credit]
    ANSWER: [option text]
"""


def get_baseline_prompt_version(prompt_version: str | None = None) -> str:
    """Resolve baseline prompt version from explicit input or environment."""
    return prompt_version or os.getenv("EVAL_BASELINE_PROMPT_VERSION", DEFAULT_BASELINE_PROMPT_VERSION)


def build_baseline_system_prompt(prompt_version: str | None = None) -> str:
    """Build full system prompt used by baseline runs."""
    version = get_baseline_prompt_version(prompt_version)
    if version == "v1":
        return _BASELINE_SYSTEM_PROMPT_V1
    if version == "v2":
        return _BASELINE_SYSTEM_PROMPT_V2

    available = ", ".join(["v1", "v2"])
    raise ValueError(f"Unknown baseline prompt version: {version}. Available versions: {available}")


BASELINE_SYSTEM_PROMPT = build_baseline_system_prompt()


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
