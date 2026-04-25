"""Shared answer extraction and normalization helpers.

These helpers are reused by chat and evaluation flows to keep output parsing
behavior consistent.
"""

from __future__ import annotations

import re


def normalize_for_match(text: str) -> str:
    """Normalize model text for robust matching and comparisons."""
    normalized = text.strip().lower()
    normalized = normalized.translate(str.maketrans({
        "\u2018": "'", "\u2019": "'",  # smart single quotes
        "\u201c": '"', "\u201d": '"',  # smart double quotes
        "\u2013": "-", "\u2014": "-", "\u2212": "-",  # dash variants
        "\u2192": "->",  # unicode right arrow
    }))
    normalized = re.sub(r"^[\[(\{\"']+|[\]\)\}\"']+$", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def extract_last_answer_line(response: str) -> str | None:
    """Return the content of the last ANSWER: line if present."""
    answer_lines = re.findall(r"(?im)^\s*answer\s*:\s*(.+?)\s*$", response)
    return answer_lines[-1] if answer_lines else None


def canonicalize_answer_line(response: str, exact_phrase: str) -> str:
    """Rewrite or append the final ANSWER: line in a stable format."""
    if re.search(r"(?im)^\s*answer\s*:", response):
        return re.sub(
            r"(?im)^\s*answer\s*:.*$",
            f"ANSWER: {exact_phrase}",
            response,
        )
    return response.rstrip() + f"\nANSWER: {exact_phrase}"
