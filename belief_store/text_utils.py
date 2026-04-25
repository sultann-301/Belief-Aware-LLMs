"""Shared text normalization utilities for belief-aware reasoning.

Used by both the dual-agent pipeline and the evaluation harness to
ensure consistent phrase matching behaviour.
"""

from __future__ import annotations

import re


def normalize_for_match(text: str) -> str:
    """Normalize text for robust phrase matching.

    Transforms include:
      - lowercasing
      - smart-quote / dash / arrow normalization
      - stripping leading/trailing brackets, quotes, parens
      - collapsing internal whitespace
    """
    text = text.strip().lower()
    text = text.translate(str.maketrans({
        "\u2018": "'", "\u2019": "'",       # smart single quotes
        "\u201c": '"', "\u201d": '"',       # smart double quotes
        "\u2013": "-", "\u2014": "-", "\u2212": "-",  # dash variants
        "\u2192": "->",                     # unicode right arrow
    }))
    text = re.sub(r"^[\[\(\{\"']+|[\]\)\}\"']+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
