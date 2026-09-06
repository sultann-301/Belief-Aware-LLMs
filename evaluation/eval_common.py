"""eval_common.py — Shared utilities for the evaluation framework.

Provides:
  - DomainConfig: dataclass for domain evaluation configuration
  - Belief management helpers (init, accumulate, filter, serialize)
  - Prompt construction helpers
  - OllamaClient factory
  - Result processing and logging
  - CSV header utilities
"""

from __future__ import annotations

import csv
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Callable, cast

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.llm_client import OllamaClient
from evaluation.prompting import (
    build_eval_system_prompt,
    build_store_prompt as _build_store_prompt,
    get_eval_prompt_version,
)
from evaluation.answer_extraction import extract_answer_with_confidence
from evaluation.eval_metrics import extract_answer_logprob_confidence


# ────────────────────────────────────────────────────────────────────
# Domain Configuration
# ────────────────────────────────────────────────────────────────────

@dataclass
class DomainConfig:
    """Configuration for a domain evaluation.

    Attributes:
        name: Human-readable domain name.
        setup_fn: Function to register rules in a BeliefStore.
        initial_beliefs: Starting state for all turns.
        turns: List of turn dicts with beliefs, question, options, correct answer.
        baseline_rules: Text rules for the NO STORE baseline.
        eval_prompt_version: Prompt profile for WITH STORE evals (e.g., "v5").
        default_entities: Fallback entities for turns without "attributes" key.
        is_conversational: Whether store persists across turns.
        accumulate_prior_beliefs: Whether to accumulate prior turn beliefs.
    """
    name: str
    setup_fn: Callable[[BeliefStore], None]
    initial_beliefs: dict[str, Any]
    turns: list[dict]
    baseline_rules: str
    eval_prompt_version: str | None = None
    default_entities: str = "applicant, loan"
    is_conversational: bool = True
    accumulate_prior_beliefs: bool = False
    seed_fn: Callable[[], list[dict]] | None = None


# ────────────────────────────────────────────────────────────────────
# Belief Management Helpers
# ────────────────────────────────────────────────────────────────────

def _init_store(config: DomainConfig) -> BeliefStore:
    """Initialize a fresh belief store with domain setup and initial beliefs."""
    store = BeliefStore()
    config.setup_fn(store)
    for key, value in config.initial_beliefs.items():
        store.add_hypothesis(key, value)
    return store


def _accumulate_prior_beliefs(config: DomainConfig, turn_idx: int) -> dict[str, Any]:
    """Gather all prior turn beliefs up to (but not including) turn_idx."""
    accumulated = {}
    for prev_idx in range(turn_idx):
        prev_turn = config.turns[prev_idx]
        if prev_turn.get("beliefs"):
            accumulated.update(prev_turn["beliefs"])
    return accumulated


def _get_filter_spec(turn: dict, default: str) -> tuple[list[str], bool]:
    """Determine what beliefs to include in the prompt.

    Returns (filter_items, is_attribute_mode) where:
      - is_attribute_mode=True uses attribute-level HopWalker filtering
      - is_attribute_mode=False uses entity-level filtering
    """
    if "attributes" in turn:
        return list(turn["attributes"]), True
    entities = turn.get("entities", default).split(", ")
    return [e.strip() for e in entities], False


def _resolve_and_serialize(
    store: BeliefStore, filter_spec: list[str], is_attribute_mode: bool,
) -> str:
    """Resolve dirty beliefs and serialize to prompt text."""
    if is_attribute_mode:
        store.resolve_dirty_for_attributes(filter_spec)
        beliefs_text, _ = store.to_prompt_attributes(filter_spec)
    else:
        store.resolve_dirty(filter_spec)
        beliefs_text, _ = store.to_prompt(filter_spec)
    return beliefs_text


def _format_question(turn: dict) -> str:
    """Format a turn's question and options into readable prompt text."""
    lines = [
        turn["question"],
        "",
        "Choose exactly one of the following exact phrases:",
    ]
    for _, text in turn["options"].items():
        lines.append(f"  [{text}]")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────
# Prompt & Client Helpers
# ────────────────────────────────────────────────────────────────────

def _resolve_eval_system_prompt(config: DomainConfig) -> str:
    """Resolve full eval system prompt for this run."""
    return build_eval_system_prompt(prompt_version=config.eval_prompt_version)


def _build_cache_path(cache_dir: str | None, namespace: str) -> str | None:
    if not cache_dir:
        return None
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", namespace)
    return os.path.join(cache_dir, f"{safe}.sqlite")


def _create_ollama_client(
    model: str,
    temperature: float,
    ollama_options: dict[str, object] | None,
    cache_path: str | None,
    cache_enabled: bool,
) -> OllamaClient:
    options = ollama_options or {}
    return OllamaClient(
        model=model,
        temperature=temperature,
        cache_enabled=cache_enabled,
        cache_path=cache_path,
        num_predict=cast(int | None, options.get("num_predict")),
        num_ctx=cast(int | None, options.get("num_ctx")),
        repeat_penalty=cast(float | None, options.get("repeat_penalty")),
        repeat_last_n=cast(int | None, options.get("repeat_last_n")),
        top_k=cast(int | None, options.get("top_k")),
        top_p=cast(float | None, options.get("top_p")),
        keep_alive=cast(str | int | None, options.get("keep_alive")),
    )


# ────────────────────────────────────────────────────────────────────
# Result Processing & Logging
# ────────────────────────────────────────────────────────────────────

def _debug_log_path(log_dir: str | None, filename: str) -> str:
    base_dir = log_dir or os.path.dirname(__file__)
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, filename)


def log_none_answer(
    condition: str,
    turn: int,
    response: str,
    log_dir: str | None = None,
) -> None:
    """Log failures to extract an answer from the LLM response."""
    log_file = _debug_log_path(log_dir, "failed_extractions.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}]\n{response}\n{'-'*60}\n")


def log_incorrect_answer(
    condition: str,
    turn: int,
    question: str,
    actual: str,
    expected: str,
    response: str,
    log_dir: str | None = None,
) -> None:
    """Log incorrect answers with full reasoning for post-analysis."""
    log_file = _debug_log_path(log_dir, "incorrect_answers.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}] LLM chose {actual}, Correct was {expected}\n")
        f.write(f"QUESTION: {question}\n")
        f.write(f"{response}\n{'-'*60}\n")


def _process_result(
    condition: str,
    turn_idx: int,
    turn: dict,
    response: str,
    extra_fields: dict[str, Any] | None = None,
    logprobs_data: list[dict] | None = None,
    debug_log_dir: str | None = None,
    debug_logs_enabled: bool = True,
) -> dict:
    """Extract answer with extraction-quality tracking, log if needed, and return result dict."""
    extraction_result = extract_answer_with_confidence(response, turn.get("options", {}))

    if extraction_result is None:
        answer = None
        confidence = None
        extraction_method = None
        if debug_logs_enabled:
            log_none_answer(condition, turn_idx, response, log_dir=debug_log_dir)
    else:
        answer = extraction_result["answer"]
        confidence = extraction_result["confidence"]
        extraction_method = extraction_result["method"]

    correct = turn["correct"]
    hit = answer == correct

    if answer is not None and not hit and debug_logs_enabled:
        log_incorrect_answer(
            condition,
            turn_idx,
            turn["question"],
            answer,
            correct,
            response,
            log_dir=debug_log_dir,
        )

    # Confidence scores (Logprob-based)
    # We pass the extracted answer phrase as a hint to help locate tokens
    # even if brackets were missing in the raw output.
    extracted_phrase = None
    if extraction_result and "answer" in extraction_result:
        label = extraction_result["answer"]
        extracted_phrase = turn.get("options", {}).get(label)

    logprob_conf = extract_answer_logprob_confidence(logprobs_data, response, extracted_phrase)

    # We use 'decision_prob' as the primary calibration signal for Brier/ECE
    # because it represents certainty relative to competitors (Decision Certainty)
    p_model = logprob_conf.get("decision_prob")

    lp_label = ""
    if p_model is not None:
        lp_label = f" [p_dec={p_model:.3f}]"
    elif logprob_conf.get("mean_answer_prob") is not None:
        # Fallback to mean if top_logprobs was missing (unlikely in this setup)
        lp_label = f" [p_avg={logprob_conf['mean_answer_prob']:.3f}]"

    confidence_label = f" ({confidence})" if confidence else ""
    print(f"  Turn {turn_idx}: LLM={answer}{confidence_label}{lp_label}  correct={correct}  {'✓' if hit else '✗'}", flush=True)

    result = {
        "turn": turn_idx,
        "answer": answer,
        "confidence": confidence,
        "extraction_method": extraction_method,
        "correct": correct,
        "hit": hit,
        "end_to_end_correct": hit,
        "response": response,
        "mean_answer_prob": logprob_conf.get("mean_answer_prob"),
        "decision_prob": logprob_conf.get("decision_prob"),
        "min_answer_prob": logprob_conf.get("min_answer_prob"),
    }

    if extra_fields:
        result.update(extra_fields)

    return result


# ────────────────────────────────────────────────────────────────────
# CSV Utilities
# ────────────────────────────────────────────────────────────────────

def _ensure_csv_header(csv_filename: str, header: list[str]) -> None:
    """Ensure CSV has the expected header; upgrade if a new trailing column was added."""
    os.makedirs(os.path.dirname(csv_filename) or ".", exist_ok=True)
    if not os.path.isfile(csv_filename):
        return

    try:
        with open(csv_filename, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
    except Exception:
        return

    if not rows:
        return

    existing_header = rows[0]
    if existing_header == header:
        return

    if existing_header == header[: len(existing_header)]:
        new_rows = [header]
        pad_len = len(header)
        for row in rows[1:]:
            if len(row) < pad_len:
                row = row + [""] * (pad_len - len(row))
            new_rows.append(row)

        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(new_rows)


def _resolve_gold_phrase(turn: dict[str, Any]) -> str:
    options = turn.get("options", {})
    correct_label = turn.get("correct")
    if correct_label in options:
        return options[correct_label]
    return str(correct_label) if correct_label is not None else ""


def _resolve_pred_phrase(turn: dict[str, Any], answer_label: str | None) -> str:
    if answer_label is None:
        return "NO_ANSWER"

    options = turn.get("options", {})
    if answer_label in options:
        return options[answer_label]
    return "NO_ANSWER"
