"""eval_metrics.py — Calibration, evidence, and retrieval metrics.

Provides:
  - Logprob-based confidence extraction
  - Calibration metrics: Brier score, Log Loss, ECE, MacroCE
  - Evidence reasoning metrics: precision, recall, F1
  - Retrieval fidelity: BCR, SBIR
  - Dual-agent split metrics
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any

from belief_store.store import BeliefStore
from belief_store.text_utils import normalize_for_match as _normalize_for_match


# ────────────────────────────────────────────────────────────────────
# Text Normalization
# ────────────────────────────────────────────────────────────────────

def _normalize_reasoning_text(text: str) -> str:
    """Normalize conclusion text for deterministic reasoning grading."""
    lowered = _normalize_for_match(text)
    lowered = re.sub(r"[^a-z0-9\s,._=-]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


# ────────────────────────────────────────────────────────────────────
# Dual-Agent Response Construction & Metrics
# ────────────────────────────────────────────────────────────────────

def _build_dual_agent_response(dual_agent_result: dict[str, Any]) -> str:
    """Build structured dual-agent trace text for logging and extraction."""
    evidence_keys = dual_agent_result.get("agent1_evidence_keys", [])
    if isinstance(evidence_keys, list):
        evidence_text = ", ".join(str(item) for item in evidence_keys)
    else:
        evidence_text = ""

    # Use the matched label so extraction is deterministic (no phrase matching)
    matched_label = dual_agent_result.get("agent2_matched_option_label", "")
    matched_phrase = dual_agent_result.get("agent2_matched_option_text", "")

    return f"""[AGENT 1 CONCLUSION]
{dual_agent_result.get('agent1_conclusion', '')}

[AGENT 1 EVIDENCE KEYS]
{evidence_text}

[AGENT 1 REASONING]
{dual_agent_result.get('agent1_reasoning', '')}

[AGENT 2 MATCHER RATIONALE]
{dual_agent_result.get('agent2_matcher_rationale', '')}

ANSWER: [{matched_phrase}]
"""


def _get_expected_agent1_conclusion(turn: dict[str, Any]) -> str:
    correct_opt = turn.get("options", {}).get(turn.get("correct", ""), "")
    if "Cannot Answer" in correct_opt or "not in the provided beliefs" in correct_opt.lower():
        return "Not in belief store"

    val = correct_opt.split(" — ")[0].strip()
    return val


def _compute_dual_agent_metrics(turn: dict[str, Any], dual_agent_result: dict[str, Any]) -> dict[str, Any]:
    """Compute split metrics for dual-agent runs."""
    expected_label = turn.get("correct")
    derived_label = dual_agent_result.get("agent2_matched_option_label") or ""
    match_status = dual_agent_result.get("agent2_match_status") or "phrase-not-found"
    agent1_conclusion = dual_agent_result.get("agent1_conclusion", "")

    binding_scored = False
    binding_correct = False
    binding_status = "not-scored"

    if turn.get("options") and agent1_conclusion:
        expected_conclusion = _get_expected_agent1_conclusion(turn)
        binding_scored = True
        if expected_conclusion.lower() in agent1_conclusion.lower():
            binding_correct = True
            binding_status = "matched"
        else:
            binding_correct = False
            binding_status = "wrong-conclusion"

    # Extract matcher confidence from logprobs (decision_prob for the matched label)
    matcher_confidence = None
    matcher_logprobs = dual_agent_result.get("agent2_matcher_logprobs")
    matched_label = dual_agent_result.get("agent2_matched_option_label", "")
    if matcher_logprobs and matched_label:
        # Reuse extract_answer_logprob_confidence with the matched label as the phrase
        logprob_conf = extract_answer_logprob_confidence(matcher_logprobs, "", matched_label)
        matcher_confidence = logprob_conf.get("decision_prob")

    # Do not fallback to 1.0 if logprobs unavailable - this breaks calibration metrics.
    # If logprobs are unavailable, matcher_confidence remains None.

    return {
        "binding_correct": binding_correct,
        "binding_scored": binding_scored,
        "binding_status": binding_status,
        "agent1_conclusion": dual_agent_result.get("agent1_conclusion", ""),
        "agent1_evidence_keys": dual_agent_result.get("agent1_evidence_keys", []),
        "agent1_reasoning": dual_agent_result.get("agent1_reasoning", ""),
        "agent2_matched_option_text": dual_agent_result.get("agent2_matched_option_text", ""),
        "agent2_matcher_rationale": dual_agent_result.get("agent2_matcher_rationale", ""),
        "agent2_matched_option_label": derived_label,
        "agent2_match_status": match_status,
        "agent2_matcher_confidence": matcher_confidence,
    }


def _compute_reasoner_metrics(binding_metrics: list[tuple[bool, bool]]) -> dict[str, float]:
    """Compute binding accuracy for the reasoner (Agent 1).

    The reasoner produces a free-text conclusion per turn which is checked
    against the expected answer.  This is a binary per-turn outcome (correct
    or not), so the natural metric is **accuracy** — there is no distinct
    FP/TN class the way there is for set-based evidence F1.

    Args:
        binding_metrics: list of (binding_scored, binding_correct) tuples.

    Returns:
        dict with binding_accuracy, correct/scored counts, mirroring the
        structure of ``_compute_reasoning_metrics``.
    """
    empty: dict[str, float] = {
        "reasoner_binding_accuracy": 0.0,
        "reasoner_correct_count": 0.0,
        "reasoner_scored_count": 0.0,
    }

    if not binding_metrics:
        return empty

    scored = [correct for scored, correct in binding_metrics if scored]
    if not scored:
        return empty

    correct_count = sum(1 for c in scored if c)
    accuracy = correct_count / len(scored)

    return {
        "reasoner_binding_accuracy": accuracy,
        "reasoner_correct_count": float(correct_count),
        "reasoner_scored_count": float(len(scored)),
    }


# ────────────────────────────────────────────────────────────────────
# Logprob-Based Confidence & Calibration Metrics
# ────────────────────────────────────────────────────────────────────

def extract_answer_logprob_confidence(
    logprobs_data: list[dict] | None,
    response_text: str,
    extracted_answer_phrase: str | None = None
) -> dict:
    """Extract model confidence from logprobs for the answer phrase tokens.

    Locates the tokens corresponding to the bracketed answer phrase
    (between ``[`` and ``]`` after the last ``ANSWER:`` marker) and
    computes confidence metrics from their logprobs.

    Returns a dict with:
        mean_answer_logprob: average logprob across answer phrase tokens
        mean_answer_prob:    exp(mean_answer_logprob) — the "confidence" [0, 1]
        min_answer_prob:     weakest-link token probability
        commitment_prob:     probability of the first answer token
    All values are None if logprobs are unavailable or answer phrase
    cannot be located.
    """
    empty = {
        "mean_answer_prob": None,
        "decision_prob": None,
        "min_answer_prob": None,
        "first_token_prob": None,
    }

    if not logprobs_data:
        return empty

    # Reconstruct token stream
    tokens = [entry.get("token", "") for entry in logprobs_data]
    cumulative = "".join(tokens)

    # Check if this is a Matcher JSON response
    json_match = re.search(r'"matched_option_label"\s*:\s*["\']?([A-Za-z0-9_]+)["\']?', cumulative)
    if not json_match:
        json_match = re.search(r"'matched_option_label'\s*:\s*[\"']?([A-Za-z0-9_]+)[\"']?", cumulative)

    if json_match:
        # Direct character matching for Matcher JSON format
        start_idx = json_match.start(1)
        end_idx = json_match.end(1)
    else:
        # Fall back to single-agent free-text anchor extraction
        # Locate the anchor (the last mention of "Answer:")
        anchor_idx = -1
        for m in re.finditer(r"(?i)\banswer\s*:", cumulative):
            anchor_idx = m.end()

        # If no "Answer:" found, anchor to the last ~50 chars to avoid reasoning leakage
        if anchor_idx == -1:
            anchor_idx = max(0, len(cumulative) - 50)

        search_range = cumulative[anchor_idx:]

        # Strategy 1: Brackets within the anchor range
        bracket_open = search_range.find("[")
        start_idx = -1
        end_idx = -1

        if bracket_open != -1:
            bracket_close = search_range.find("]", bracket_open + 1)
            if bracket_close != -1:
                start_idx = anchor_idx + bracket_open + 1
                end_idx = anchor_idx + bracket_close

        # Strategy 2: Phrase fallback within the anchor range
        if start_idx == -1 and extracted_answer_phrase:
            phrase_pos = search_range.find(extracted_answer_phrase)
            if phrase_pos != -1:
                start_idx = anchor_idx + phrase_pos
                end_idx = start_idx + len(extracted_answer_phrase)

    if start_idx == -1 or end_idx == -1:
        return empty
    # Map character positions back to token indices using an overlap check
    # we want tokens that fall (at least partially) between bracket_open and bracket_close
    char_pos = 0
    answer_token_indices = []
    for i, tok in enumerate(tokens):
        tok_start = char_pos
        tok_end = char_pos + len(tok)

        # Token is part of the answer if it overlaps with (start_idx, end_idx)
        overlap_start = max(tok_start, start_idx)
        overlap_end = min(tok_end, end_idx)

        if overlap_start < overlap_end:
            answer_token_indices.append(i)

        char_pos = tok_end
    if not answer_token_indices:
        return empty

    if not answer_token_indices:
        return empty

    # 1. Heuristic: Mean probability across the phrase (Fluency proxy)
    answer_logprobs = [
        logprobs_data[i]["logprob"]
        for i in answer_token_indices
        if "logprob" in logprobs_data[i]
    ]
    mean_lp = sum(answer_logprobs) / len(answer_logprobs) if answer_logprobs else None

    # 2. Decision Certainty: Minimum Relative Probability across the phrase (Choice proxy)
    # This identifies the "bottleneck" or most uncertain branching point.
    decision_prob = None
    relative_probs = []

    if answer_token_indices:
        for idx in answer_token_indices:
            token_data = logprobs_data[idx]
            token_str = token_data.get("token", "").strip()

            # Gap 2 Fix: Filter out noise (punctuation, brackets, whitespace)
            # We only care about the decision certainty of meaningful content
            if not token_str or token_str in "[](){}:=,._-":
                continue

            if "top_logprobs" in token_data and token_data["top_logprobs"]:
                denom = sum(math.exp(tp["logprob"]) for tp in token_data["top_logprobs"])
                chosen_prob = math.exp(token_data["logprob"])

                if denom > 0:
                    relative_probs.append(chosen_prob / denom)
                else:
                    relative_probs.append(chosen_prob)
            elif "logprob" in token_data:
                relative_probs.append(math.exp(token_data["logprob"]))

        # Gap 5 Fix: Use a composite of Min (Decision) and Mean (Fluency)
        # Min represents the hardest branching point; Mean represents overall shakiness.
        if relative_probs:
            min_rel = min(relative_probs)
            mean_rel = sum(relative_probs) / len(relative_probs)

            # Composite Score: 80% weight on the hardest decision, 20% on overall consistency
            decision_prob = (0.8 * min_rel) + (0.2 * mean_rel)

    return {
        "mean_answer_prob": math.exp(mean_lp) if mean_lp is not None else None,
        "decision_prob": decision_prob,
        "min_answer_prob": math.exp(min(answer_logprobs)) if answer_logprobs else None,
        "first_token_prob": math.exp(answer_logprobs[0]) if answer_logprobs else None,
    }


def brier_score(predictions: list[tuple[float, int]]) -> float:
    """Brier Score: mean squared error between predicted probability and outcome.

    Args:
        predictions: list of (p_model, outcome) where p_model ∈ [0, 1] is the
            model's confidence and outcome ∈ {0, 1} is the actual correctness.

    Returns:
        Brier score ∈ [0, 1]. Lower is better.
        0.0 = perfect calibration. 0.25 = random baseline (always predicting 0.5).
    """
    if not predictions:
        return 0.0
    return sum((p - o) ** 2 for p, o in predictions) / len(predictions)


def log_loss_score(predictions: list[tuple[float, int]], eps: float = 1e-15) -> float:
    """Log Loss (cross-entropy): penalizes confident wrong predictions heavily.

    Args:
        predictions: list of (p_model, outcome).
        eps: clipping epsilon to avoid log(0).

    Returns:
        Mean negative log-likelihood. Lower is better.
    """
    if not predictions:
        return 0.0
    total = 0.0
    for p, o in predictions:
        p = max(eps, min(1 - eps, p))
        total += -(o * math.log(p) + (1 - o) * math.log(1 - p))
    return total / len(predictions)


def expected_calibration_error(predictions: list[tuple[float, int]], n_bins: int = 3) -> float:
    """Expected Calibration Error (ECE).

    Weights the absolute difference between confidence and accuracy in each bin
    by the number of samples in that bin.

    Args:
        predictions: list of (p_model, outcome).
        n_bins: number of confidence bins (e.g. 10 bins of size 0.1).

    Returns:
        ECE value [0, 1]. Lower is better.
    """
    if not predictions:
        return 0.0

    bins = [[] for _ in range(n_bins)]
    for p, o in predictions:
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, o))

    ece = 0.0
    total_n = len(predictions)
    for bin_items in bins:
        if not bin_items:
            continue
        bin_n = len(bin_items)
        bin_acc = sum(o for _, o in bin_items) / bin_n
        bin_conf = sum(p for p, _ in bin_items) / bin_n
        ece += (bin_n / total_n) * abs(bin_acc - bin_conf)

    return ece

def macro_calibration_error(predictions: list[tuple[float, int]]) -> float:
    """Macro-average Calibration Error (MacroCE).

    Calculates separate calibration errors for correct (Positive) and incorrect (Negative)
    predictions, then averages them. This ensures that calibration on errors is
    weighted equally with calibration on correct answers, regardless of accuracy.

    Formula:
      ICE_pos = mean(1 - conf) for all correct predictions
      ICE_neg = mean(conf - 0) for all incorrect predictions
      MacroCE = 0.5 * (ICE_pos + ICE_neg)
    """
    if not predictions:
        return 0.0

    pos_scores = [p for p, o in predictions if o == 1]
    neg_scores = [p for p, o in predictions if o == 0]

    ice_pos = sum(1.0 - p for p in pos_scores) / len(pos_scores) if pos_scores else 0.0
    ice_neg = sum(p for p in neg_scores) / len(neg_scores) if neg_scores else 0.0

    if not pos_scores:
        return ice_neg
    if not neg_scores:
        return ice_pos

    return 0.5 * (ice_pos + ice_neg)


# ────────────────────────────────────────────────────────────────────
# Evidence-Based Reasoning Metrics
# ────────────────────────────────────────────────────────────────────

_BELIEF_KEY_RE = re.compile(r'\b([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)\b')


def _extract_evidence_keys_from_response(
    response: str, known_keys: set[str],
) -> set[str]:
    """Extract belief-store keys referenced in model response text.

    Matches ``entity.attribute`` patterns (e.g. ``applicant.credit_score``)
    and filters to keys that actually exist in the store.
    """
    candidates = set(_BELIEF_KEY_RE.findall(response.lower()))
    return candidates & known_keys


def _compute_reasoning_metrics(
    canonical: set[str], cited: set[str],
) -> dict[str, float]:
    """Compute precision / recall / F1 over evidence key sets."""
    if not canonical:
        return {
            "evidence_precision": 0.0,
            "evidence_recall": 0.0,
            "evidence_f1": 0.0,
            "evidence_cited_count": 0.0,
            "evidence_canonical_count": 0.0,
        }

    true_positives = len(canonical & cited)
    precision = true_positives / len(cited) if cited else 0.0
    recall = true_positives / len(canonical)

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return {
        "evidence_precision": precision,
        "evidence_recall": recall,
        "evidence_f1": f1,
        "evidence_cited_count": float(len(cited)),
        "evidence_canonical_count": float(len(canonical)),
    }


def _compute_retrieval_fidelity(
    beliefs_text: str,
    canonical: set[str],
    known_keys: set[str],
) -> dict[str, float]:
    """Compute BCR (Belief Coverage Rate) and SBIR (Spurious Belief Injection Rate).

    BCR:  fraction of canonical keys that appear in the serialised beliefs text.
          BCR < 1.0 means the retrieval pipeline dropped required beliefs.
    SBIR: fraction of injected keys that are NOT in the canonical set.
          High SBIR means noise is being added to the prompt.
    """
    if not canonical:
        return {}
    injected = set(_BELIEF_KEY_RE.findall(beliefs_text.lower())) & known_keys
    true_positives = len(canonical & injected)
    bcr  = true_positives / len(canonical) if canonical else 1.0
    sbir = (len(injected) - true_positives) / len(injected) if injected else 0.0
    return {
        "bcr": bcr,
        "sbir": sbir,
        "retrieval_injected_count": float(len(injected)),
        "retrieval_canonical_count": float(len(canonical)),
    }


def _get_reasoning_metrics(
    store: BeliefStore,
    filter_spec: list[str],
    is_attr: bool,
    response: str,
    cited_keys_override: set[str] | None = None,
    beliefs_text: str = "",
) -> dict[str, float]:
    """Compute reasoning and retrieval metrics for a single turn.

    Args:
        store: The resolved BeliefStore for this turn.
        filter_spec: Target attributes (or entities) for this turn.
        is_attr: True if filter_spec contains attribute-level keys.
        response: Model response text (used for single-agent extraction).
        cited_keys_override: If provided, use these as the model's cited
            keys instead of extracting from response (for dual-agent).
        beliefs_text: The serialised beliefs string sent to the model.
            When provided, BCR and SBIR retrieval metrics are computed.
    """
    if not is_attr:
        # Entity-level turns don't have specific target attributes.
        return {}

    canonical = store.get_canonical_evidence_keys(filter_spec)
    if not canonical:
        return {}

    known_keys = (set(store.rule_index.keys()) | set(store.beliefs.keys())) - store.removed

    if cited_keys_override is not None:
        cited = cited_keys_override | _extract_evidence_keys_from_response(response, known_keys)
    else:
        # Use both rule_index (computed rules) and beliefs (input hypotheses)
        # store.beliefs contains explicitly set/resolved values, rule_index has computed rules.
        # Together they cover both input assumptions and derived facts.
        cited = _extract_evidence_keys_from_response(response, known_keys)

    # Exclude target attributes from cited keys (they are the targets, not evidence)
    targets = set(filter_spec)
    cited = cited - targets

    metrics = _compute_reasoning_metrics(canonical, cited)

    # Retrieval fidelity (BCR / SBIR) — only when beliefs_text is available
    if beliefs_text:
        retrieval = _compute_retrieval_fidelity(beliefs_text, canonical, known_keys)
        metrics.update(retrieval)

    return metrics
