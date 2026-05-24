"""answer_extraction.py — Parse and extract MCQ answers from LLM responses.

Provides:
  - extract_answer: Primary extraction API (returns option letter or None)
  - extract_answer_with_confidence: Extraction with method/confidence tracking
  - ENFORCE_EXACT_PHRASE: Flag to enable exact-phrase canonicalization
"""

from __future__ import annotations

import os
import re

from belief_store.text_utils import normalize_for_match as _normalize_for_match

# If enabled, normalize non-exact answers into exact option phrases using
# deterministic parsing only (no second LLM call).
ENFORCE_EXACT_PHRASE = os.getenv("EVAL_ENFORCE_EXACT_PHRASE", "1") != "0"


# ────────────────────────────────────────────────────────────────────
# Low-Level Helpers
# ────────────────────────────────────────────────────────────────────

def _extract_last_answer_line(response: str) -> str | None:
    """Return the content of the last ANSWER: line if present."""
    answer_lines = re.findall(r"(?im)\banswer\s*:\s*(.+?)\s*$", response)
    return answer_lines[-1] if answer_lines else None


def _extract_bracketed_answer(answer_line: str) -> str | None:
    """Extract bracketed content from ANSWER: line.

    Expected format: ANSWER: [exact phrase]
    Returns the content inside brackets, or None if no brackets found.
    """
    match = re.search(r"\[([^\[\]]+)\]", answer_line)
    if match:
        return match.group(1).strip()
    return None


def _canonicalize_answer_line(response: str, exact_phrase: str) -> str:
    """Rewrite/add final answer line using an exact option phrase with brackets."""
    if re.search(r"(?im)\banswer\s*:", response):
        return re.sub(
            r"(?im)\banswer\s*:.*$",
            f"ANSWER: [{exact_phrase}]",
            response,
        )
    return response.rstrip() + f"\nANSWER: [{exact_phrase}]"


# ────────────────────────────────────────────────────────────────────
# Primary Extraction APIs
# ────────────────────────────────────────────────────────────────────

def extract_answer_with_confidence(response: str, options: dict[str, str]) -> dict | None:
    """Extract answer with method tracking.

    Returns:
        {
            "answer": "A",
            "method": "bracketed_exact" | "bracketed_normalized" | "unbracketed_normalized" | None,
            "confidence": "HIGH" | "LOW"
        }
        Returns None if no answer found.
    """
    if not options:
        return None

    answer_line = _extract_last_answer_line(response)
    if not answer_line:
        return None

    # Strategy 1: Bracketed format (HIGH confidence)
    bracketed = _extract_bracketed_answer(answer_line)
    if bracketed:
        # Direct label check: if the bracketed content is itself a valid option key (e.g. [A], [B])
        if bracketed.upper() in options:
            return {"answer": bracketed.upper(), "method": "bracketed_label", "confidence": "HIGH"}

        # Exact match (case-sensitive)
        for letter, option_text in options.items():
            if bracketed == option_text:
                return {"answer": letter, "method": "bracketed_exact", "confidence": "HIGH"}

        # Normalized match
        normalized_bracketed = _normalize_for_match(bracketed)
        normalized_options = {letter: _normalize_for_match(text) for letter, text in options.items()}
        for letter, norm_option in normalized_options.items():
            if normalized_bracketed == norm_option:
                return {"answer": letter, "method": "bracketed_normalized", "confidence": "HIGH"}

        # Substring match
        if len(normalized_bracketed) >= 5:
            substring_matches = []
            for letter, norm_option in normalized_options.items():
                if normalized_bracketed in norm_option or norm_option in normalized_bracketed:
                    substring_matches.append(letter)
            if len(substring_matches) == 1:
                return {"answer": substring_matches[0], "method": "bracketed_substring", "confidence": "LOW"}

        # Bracketed but didn't match
        return None

    # Strategy 2: Unbracketed fallback (LOW confidence)
    candidate = _normalize_for_match(answer_line)
    if not candidate:
        return None

    normalized_options = {letter: _normalize_for_match(text) for letter, text in options.items()}
    # Exact normalized match
    for letter, norm_option in normalized_options.items():
        if candidate == norm_option:
            return {"answer": letter, "method": "unbracketed_normalized", "confidence": "LOW"}

    # Substring match
    if len(candidate) >= 5:
        substring_matches = []
        for letter, norm_option in normalized_options.items():
            if candidate in norm_option or norm_option in candidate:
                substring_matches.append(letter)
        if len(substring_matches) == 1:
            return {"answer": substring_matches[0], "method": "unbracketed_substring", "confidence": "LOW"}

    return None


def extract_answer(response: str, options: dict[str, str]) -> str | None:
    """Extract answer phrase and map to option letter.

    Strategy (in order of priority):
      1) Extract from ANSWER: [bracketed phrase] format (PRIMARY)
      2) Extract from ANSWER: unbracketed phrase (FALLBACK)
      3) Return None (no guessing)

    Returns the option letter (A/B/C/...) if found, else None.
    """
    if not options:
        return None

    # Get the last ANSWER: line content
    answer_line = _extract_last_answer_line(response)
    if not answer_line:
        return None

    # Strategy 1: Try bracketed format [exact phrase]
    bracketed = _extract_bracketed_answer(answer_line)
    if bracketed:
        # Direct label check: if bracketed content is itself a valid option key (e.g. [A], [B])
        if bracketed.upper() in options:
            return bracketed.upper()

        # Try exact match first (case-sensitive, space-sensitive)
        for letter, option_text in options.items():
            if bracketed == option_text:
                return letter

        # Try normalized match if exact fails
        normalized_bracketed = _normalize_for_match(bracketed)
        normalized_options = {letter: _normalize_for_match(text) for letter, text in options.items()}
        for letter, norm_option in normalized_options.items():
            if normalized_bracketed == norm_option:
                return letter

        # Try substring match if normalized fails
        if len(normalized_bracketed) >= 5:
            substring_hits = []
            for letter, norm_option in normalized_options.items():
                if normalized_bracketed in norm_option or norm_option in normalized_bracketed:
                    substring_hits.append(letter)
            if len(substring_hits) == 1:
                return substring_hits[0]

        # Bracketed content didn't match any option
        return None

    # Strategy 2: Try unbracketed phrase match (fallback for models that ignore bracket instruction)
    candidate = _normalize_for_match(answer_line)
    if not candidate:
        return None

    normalized_options = {letter: _normalize_for_match(text) for letter, text in options.items()}

    # Exact normalized match
    for letter, norm_option in normalized_options.items():
        if candidate == norm_option:
            return letter

    # Try substring match
    if len(candidate) >= 5:
        substring_hits = []
        for letter, norm_option in normalized_options.items():
            if candidate in norm_option or norm_option in candidate:
                substring_hits.append(letter)
        if len(substring_hits) == 1:
            return substring_hits[0]

    # If nothing matched, return None (don't guess with fragments)
    return None


def _enforce_exact_phrase_output(turn: dict, response: str) -> str:
    """Ensure response ends with an exact option phrase with brackets if enforcement is enabled."""
    options = turn.get("options", {})
    if not options or not ENFORCE_EXACT_PHRASE:
        return response

    # Extract answer and fully canonicalize to guarantee exact phrase and brackets format
    answer_letter = extract_answer(response, options)
    if answer_letter is not None:
        return _canonicalize_answer_line(response, options[answer_letter])

    return response
