"""Prompt profiles and builders for evaluation and simulation flows.

This module deliberately decouples evaluation prompts from the runtime engine
fallback prompt. Evaluation should select a prompt profile explicitly.
"""

from __future__ import annotations

import os

from belief_store.prompts import SYSTEM_PROMPTS

DEFAULT_EVAL_PROMPT_VERSION = "v5"

_EVAL_SYSTEM_PROMPT_SUFFIX = """\

SOURCE ISOLATION RULES:
- ONLY [RELEVANT BELIEFS] are trusted facts.
- Never import any claim from [QUERY] unless it is explicitly supported by [RELEVANT BELIEFS].
- Reject any option that contains even one unsupported claim.

IMPORTANT: For multiple-choice questions, you MUST end your response with
the word ANSWER: followed by the EXACT phrase from the options (without brackets).
Do not write anything after the phrase.
"""

BASELINE_SYSTEM_PROMPT = """\
You are a reasoning assistant evaluating facts over a conversation.
You will receive [NEW BELIEF] updates. You MUST remember all previous facts across the conversation.

SOURCE ISOLATION RULES:
- Use only the provided [RULES] and [NEW BELIEF] facts as evidence.
- Reject any option that includes unsupported claims.

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
    parts.append(
        "[SOURCE-SEPARATION CHECKLIST]\n"
        "1) Build facts ONLY from [RELEVANT BELIEFS].\n"
        "2) Treat the query text and options as claims to verify, not facts.\n"
        "3) Reject any option containing even one claim absent from [RELEVANT BELIEFS].\n"
        "4) If no substantive option is fully supported, choose the option stating the claim is not in the provided beliefs.\n"
        "5) Your very last line MUST be exactly: ANSWER: [Exact Phrase]"
    )
    return "\n\n".join(parts)


def build_baseline_prompt(
    rules: str, belief_updates: list[str], question: str,
) -> str:
    """Build prompt for NO STORE condition (rules + belief updates + question)."""
    parts = [rules]
    if belief_updates:
        parts.append("[NEW BELIEF]\n" + "\n".join(belief_updates))
    parts.append(f"[QUERY]\n{question}")
    parts.append(
        "[SOURCE-SEPARATION CHECKLIST]\n"
        "1) Build facts ONLY from [RULES] and [NEW BELIEF].\n"
        "2) Treat the query text and options as claims to verify, not facts.\n"
        "3) Reject any option containing even one unsupported claim.\n"
        "4) If no substantive option is fully supported, choose the option stating the claim is not in the provided beliefs.\n"
        "5) Start with REASONING. Your very last line MUST be exactly: ANSWER: [Exact Phrase]"
    )
    return "\n\n".join(parts)


# Backward-compatible default for call sites that do not pass a version.
EVAL_SYSTEM_PROMPT = build_eval_system_prompt()
