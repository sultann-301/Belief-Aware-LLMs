"""eval_harness.py — Unified evaluation framework for MCQ domain evaluations.

Provides:
  - DomainConfig: dataclass describing domain setup, beliefs, turns, and rules.
  - Three comparison conditions:
    [1] run_with_store: WITH Store (stateless, no chat history)
    [2] run_with_store_with_history: WITH Store + Chat History
    [3] run_without_store: NO Store (baseline rules + chat history only)
  - run_single_eval: runs all 3 conditions and prints results table.
  - run_multi_eval: parallel N-run benchmark with summary statistics.
"""

from __future__ import annotations

import csv
import os
import re
import sys
import time
from difflib import SequenceMatcher
import concurrent.futures
import statistics
from dataclasses import dataclass
from typing import Any, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.llm_client import OllamaClient
from belief_store.langgraph_dual_agent import run_dual_agent, build_dual_agent_graph
from belief_store.text_utils import normalize_for_match as _normalize_for_match
from evaluation.prompting import (
    BASELINE_SYSTEM_PROMPT,
    EVAL_SYSTEM_PROMPT,
    build_baseline_prompt as _build_baseline_prompt,
    build_eval_system_prompt,
    build_store_prompt as _build_store_prompt,
    get_eval_prompt_version,
)


# ────────────────────────────────────────────────────────────────────
# System Prompts
# ────────────────────────────────────────────────────────────────────


# If enabled, normalize non-exact answers into exact option phrases using
# deterministic parsing only (no second LLM call).
ENFORCE_EXACT_PHRASE = os.getenv("EVAL_ENFORCE_EXACT_PHRASE", "1") != "0"


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


# ────────────────────────────────────────────────────────────────────
# Answer Extraction & Logging
# ────────────────────────────────────────────────────────────────────

# _normalize_for_match is imported from belief_store.text_utils (see imports above).


def _normalize_reasoning_text(text: str) -> str:
    """Normalize conclusion text for deterministic reasoning grading."""
    lowered = _normalize_for_match(text)
    lowered = re.sub(r"[^a-z0-9\s,._=-]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


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
    }


def _extract_last_answer_line(response: str) -> str | None:
    """Return the content of the last ANSWER: line if present."""
    answer_lines = re.findall(r"(?im)\banswer\s*:\s*(.+?)\s*$", response)
    return answer_lines[-1] if answer_lines else None


def _canonicalize_answer_line(response: str, exact_phrase: str) -> str:
    """Rewrite/add final answer line using an exact option phrase with brackets."""
    if re.search(r"(?im)\banswer\s*:", response):
        return re.sub(
            r"(?im)\banswer\s*:.*$",
            f"ANSWER: [{exact_phrase}]",
            response,
        )
    return response.rstrip() + f"\nANSWER: [{exact_phrase}]"


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

def _extract_bracketed_answer(answer_line: str) -> str | None:
    """Extract bracketed content from ANSWER: line.
    
    Expected format: ANSWER: [exact phrase]
    Returns the content inside brackets, or None if no brackets found.
    """
    match = re.search(r"\[([^\[\]]+)\]", answer_line)
    if match:
        return match.group(1).strip()
    return None


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


def log_none_answer(condition: str, turn: int, response: str) -> None:
    """Log failures to extract an answer from the LLM response."""
    log_file = os.path.join(os.path.dirname(__file__), "failed_extractions.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}]\n{response}\n{'-'*60}\n")


def log_incorrect_answer(
    condition: str, turn: int, question: str, actual: str, expected: str, response: str,
) -> None:
    """Log incorrect answers with full reasoning for post-analysis."""
    log_file = os.path.join(os.path.dirname(__file__), "incorrect_answers.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}] LLM chose {actual}, Correct was {expected}\n")
        f.write(f"QUESTION: {question}\n")
        f.write(f"{response}\n{'-'*60}\n")


# ────────────────────────────────────────────────────────────────────
# Helper Functions for Belief Management & Prompts
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
# Prompt Selection
# ────────────────────────────────────────────────────────────────────

def _resolve_eval_system_prompt(config: DomainConfig) -> str:
    """Resolve full eval system prompt for this run."""
    return build_eval_system_prompt(prompt_version=config.eval_prompt_version)


# ────────────────────────────────────────────────────────────────────
# Result Processing
# ────────────────────────────────────────────────────────────────────

def _process_result(
    condition: str,
    turn_idx: int,
    turn: dict,
    response: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict:
    """Extract answer with confidence tracking, log if needed, and return result dict."""
    extraction_result = extract_answer_with_confidence(response, turn.get("options", {}))
    
    if extraction_result is None:
        answer = None
        confidence = None
        extraction_method = None
        log_none_answer(condition, turn_idx, response)
    else:
        answer = extraction_result["answer"]
        confidence = extraction_result["confidence"]
        extraction_method = extraction_result["method"]

    correct = turn["correct"]
    hit = answer == correct

    if answer is not None and not hit:
        log_incorrect_answer(condition, turn_idx, turn["question"], answer, correct, response)

    confidence_label = f" ({confidence})" if confidence else ""
    print(f"  Turn {turn_idx}: LLM={answer}{confidence_label}  correct={correct}  {'✓' if hit else '✗'}", flush=True)

    result = {
        "turn": turn_idx,
        "answer": answer,
        "confidence": confidence,
        "extraction_method": extraction_method,
        "correct": correct,
        "hit": hit,
        "end_to_end_correct": hit,
        "response": response,
    }

    if extra_fields:
        result.update(extra_fields)

    return result


# ────────────────────────────────────────────────────────────────────
# Evaluation Conditions
# ────────────────────────────────────────────────────────────────────

def run_with_store(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """[1] WITH Store (Stateless): Fresh store per turn, no chat history."""
    results = []
    eval_system_prompt = _resolve_eval_system_prompt(config)

    for i, turn in enumerate(config.turns):
        store = _init_store(config)

        # Accumulate prior turn beliefs if configured
        if config.is_conversational or config.accumulate_prior_beliefs:
            accumulated = _accumulate_prior_beliefs(config, i)
            for key, value in accumulated.items():
                store.add_hypothesis(key, value)

        # Add current turn beliefs
        if turn.get("beliefs"):
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)

        # Serialize beliefs for the prompt
        filter_spec, is_attr = _get_filter_spec(turn, config.default_entities)
        beliefs_text = _resolve_and_serialize(store, filter_spec, is_attr)

        # Build and send prompt
        question = _format_question(turn)
        prompt = _build_store_prompt(beliefs_text, question)

        raw_response = llm.generate(eval_system_prompt, prompt)
        response = _enforce_exact_phrase_output(turn, raw_response)
        results.append(_process_result("WITH STORE", i + 1, turn, response))

    return results


def run_with_store_with_history(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """[2] WITH Store + Chat History: Store-derived beliefs + conversational context."""
    results = []
    eval_system_prompt = _resolve_eval_system_prompt(config)
    
    # Base messages tracking
    base_messages = [{"role": "system", "content": eval_system_prompt}]
    messages = base_messages.copy()

    # For conversational: maintain one store across all turns
    store: BeliefStore | None = _init_store(config) if config.is_conversational else None

    for i, turn in enumerate(config.turns):
        # Store management
        if config.is_conversational:
            assert store is not None
            # Add turn beliefs to persistent store
            if turn.get("beliefs"):
                for key, value in turn["beliefs"].items():
                    store.add_hypothesis(key, value)
            current_store = store
        else:
            # Snapshot mode: fresh store per turn
            current_store = _init_store(config)

            # Optionally accumulate prior beliefs
            if config.accumulate_prior_beliefs:
                accumulated = _accumulate_prior_beliefs(config, i)
                for key, value in accumulated.items():
                    current_store.add_hypothesis(key, value)

            # Add current turn beliefs
            if turn.get("beliefs"):
                for key, value in turn["beliefs"].items():
                    current_store.add_hypothesis(key, value)

        # Serialize beliefs for the prompt
        filter_spec, is_attr = _get_filter_spec(turn, config.default_entities)
        beliefs_text = _resolve_and_serialize(current_store, filter_spec, is_attr)

        # Build and send prompt as part of chat history
        question = _format_question(turn)
        prompt = _build_store_prompt(beliefs_text, question)

        if not config.is_conversational:
            # Snapshot mode: start from a fresh chat history each turn
            messages = base_messages.copy()

        messages.append({"role": "user", "content": prompt})
        raw_response = llm.generate_with_history(messages)
        response = _enforce_exact_phrase_output(turn, raw_response)
        messages.append({"role": "assistant", "content": response})

        results.append(_process_result("WITH STORE (+History)", i + 1, turn, response))

    return results


def run_without_store(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """[3] NO Store (Baseline): Rules + chat history only, no explicit belief tracking."""
    results = []
    base_messages = [{"role": "system", "content": BASELINE_SYSTEM_PROMPT}]
    messages = base_messages.copy()
    initial_belief_lines = [f"{k} = {v}" for k, v in config.initial_beliefs.items()]

    for i, turn in enumerate(config.turns):
        if config.is_conversational:
            # Conversational mode: relying on chat history for prior context
            if i == 0:
                belief_lines = initial_belief_lines
            else:
                belief_lines = [f"{k} = {v}" for k, v in (turn.get("beliefs") or {}).items()]
        else:
            # Snapshot mode: start from fresh history and reconstruct full belief state
            messages = base_messages.copy()
            belief_state = config.initial_beliefs.copy()
            
            if config.accumulate_prior_beliefs:
                accumulated = _accumulate_prior_beliefs(config, i)
                belief_state.update(accumulated)
                
            if turn.get("beliefs"):
                belief_state.update(turn["beliefs"])
                
            belief_lines = [f"{k} = {v}" for k, v in belief_state.items()]

        # Build and send prompt as part of chat history
        question = _format_question(turn)
        prompt = _build_baseline_prompt(config.baseline_rules, belief_lines, question)

        messages.append({"role": "user", "content": prompt})
        raw_response = llm.generate_with_history(messages)
        response = _enforce_exact_phrase_output(turn, raw_response)
        messages.append({"role": "assistant", "content": response})

        results.append(_process_result("NO STORE", i + 1, turn, response))

    return results


def run_with_store_dual_agent(
    llm: OllamaClient,
    config: DomainConfig,
    reasoner_model: str | None = None,
    matcher_model: str | None = None,
) -> list[dict]:
    """[4] WITH Store (Dual-Agent): Fresh store per turn, decoupled reasoning+decision, no chat history."""
    results = []
    # Pre-compile graph once for all turns
    graph = build_dual_agent_graph(llm, reasoner_model=reasoner_model, matcher_model=matcher_model)

    for i, turn in enumerate(config.turns):
        store = _init_store(config)

        # Accumulate prior turn beliefs if configured
        if config.is_conversational or config.accumulate_prior_beliefs:
            accumulated = _accumulate_prior_beliefs(config, i)
            for key, value in accumulated.items():
                store.add_hypothesis(key, value)

        # Add current turn beliefs
        if turn.get("beliefs"):
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)

        # Serialize beliefs for the prompt
        filter_spec, is_attr = _get_filter_spec(turn, config.default_entities)
        beliefs_text = _resolve_and_serialize(store, filter_spec, is_attr)

        # Run dual-agent system
        dual_agent_result = run_dual_agent(
            llm=llm,
            relevant_beliefs=beliefs_text,
            query=turn["question"],
            options=turn.get("options", {}),
            compiled_graph=graph,
        )

        # Build a response string for logging and extraction compatibility
        response = _build_dual_agent_response(dual_agent_result)

        # Enforce exact phrase output format for compatibility with extraction logic
        response = _enforce_exact_phrase_output(turn, response)
        split_metrics = _compute_dual_agent_metrics(turn, dual_agent_result)
        results.append(
            _process_result(
                "WITH STORE (Dual-Agent)",
                i + 1,
                turn,
                response,
                extra_fields=split_metrics,
            )
        )

    return results


def run_with_store_with_history_dual_agent(
    llm: OllamaClient,
    config: DomainConfig,
    reasoner_model: str | None = None,
    matcher_model: str | None = None,
) -> list[dict]:
    """[5] WITH Store + Chat History (Dual-Agent): Store-derived beliefs + conversational context, dual-agent reasoning."""
    results = []
    # Pre-compile graph once for all turns
    graph = build_dual_agent_graph(llm, reasoner_model=reasoner_model, matcher_model=matcher_model)

    # For conversational: maintain one store and one chat history across all turns
    store: BeliefStore | None = _init_store(config) if config.is_conversational else None
    messages: list[dict[str, str]] = []

    for i, turn in enumerate(config.turns):
        # Store management (same logic as run_with_store_with_history)
        if config.is_conversational:
            assert store is not None
            if turn.get("beliefs"):
                for key, value in turn["beliefs"].items():
                    store.add_hypothesis(key, value)
            current_store = store
        else:
            current_store = _init_store(config)
            if config.accumulate_prior_beliefs:
                accumulated = _accumulate_prior_beliefs(config, i)
                for key, value in accumulated.items():
                    current_store.add_hypothesis(key, value)
            if turn.get("beliefs"):
                for key, value in turn["beliefs"].items():
                    current_store.add_hypothesis(key, value)

        # Serialize beliefs for the prompt
        filter_spec, is_attr = _get_filter_spec(turn, config.default_entities)
        beliefs_text = _resolve_and_serialize(current_store, filter_spec, is_attr)

        # Run dual-agent system
        dual_agent_result = run_dual_agent(
            llm=llm,
            relevant_beliefs=beliefs_text,
            query=turn["question"],
            options=turn.get("options", {}),
            chat_history=messages if config.is_conversational else None,
            compiled_graph=graph,
        )

        # Build response string for logging
        response = _build_dual_agent_response(dual_agent_result)

        # Enforce exact phrase output format for compatibility
        response = _enforce_exact_phrase_output(turn, response)

        if config.is_conversational:
            # Update history for next turn
            user_prompt = f"""[RELEVANT BELIEFS]\n{beliefs_text}\n\n[QUERY]\n{turn['question']}"""
            messages.append({"role": "user", "content": user_prompt})
            messages.append({"role": "assistant", "content": response})

        split_metrics = _compute_dual_agent_metrics(turn, dual_agent_result)
        results.append(
            _process_result(
                "WITH STORE +History (Dual-Agent)",
                i + 1,
                turn,
                response,
                extra_fields=split_metrics,
            )
        )

    return results


# ────────────────────────────────────────────────────────────────────
# Evaluation Orchestrators
# ────────────────────────────────────────────────────────────────────

def run_single_eval(config: DomainConfig, model: str = "gemma3:1b", temperature: float = 0.0) -> None:
    """Run single evaluation: all 3 conditions, print results table."""
    print(f"Connecting to Ollama ({model}) with temperature {temperature}...\n")
    llm = OllamaClient(model=model, temperature=temperature)
    n_turns = len(config.turns)

    print("=" * 75)
    print("[1] WITH Store (Stateless, no chat history)")
    print("=" * 75)
    with_store = run_with_store(llm, config)
    score_with = sum(r["hit"] for r in with_store)

    print()
    print("=" * 75)
    print("[2] WITH Store + Chat History")
    print("=" * 75)
    with_history = run_with_store_with_history(llm, config)
    score_with_history = sum(r["hit"] for r in with_history)

    print()
    print("=" * 75)
    print("[3] NO Store (Baseline: rules + chat history only)")
    print("=" * 75)
    no_store = run_without_store(llm, config)
    score_no_store = sum(r["hit"] for r in no_store)

    # Results table
    print()
    print("=" * 75)
    print("RESULTS SUMMARY")
    print("=" * 75)
    print()
    print(f"  {'Turn':<6} {'[1] Store':<18} {'[2] +History':<18} {'[3] NO Store':<18}")
    print(f"  {'─'*6} {'─'*18} {'─'*18} {'─'*18}")
    for r1, r2, r3 in zip(with_store, with_history, no_store):
        t = r1["turn"]
        s1 = "✓" if r1["hit"] else f"✗ ({r1['answer']})"
        s2 = "✓" if r2["hit"] else f"✗ ({r2['answer']})"
        s3 = "✓" if r3["hit"] else f"✗ ({r3['answer']})"
        print(f"  {t:<6} {s1:<18} {s2:<18} {s3:<18}")

    print()
    print(f"  [1] WITH STORE:             {score_with}/{n_turns}  ({score_with * 100 // n_turns}%)")
    print(f"  [2] WITH STORE (+History):  {score_with_history}/{n_turns}  ({score_with_history * 100 // n_turns}%)")
    print(f"  [3] NO STORE:               {score_no_store}/{n_turns}  ({score_no_store * 100 // n_turns}%)")
    print()


def run_multi_eval(
    config: DomainConfig,
    runs: int = 10,
    workers: int = 4,
    model: str = "gemma3:1b",
    temperature: float = 0.0,
    model_alias: str | None = None,
) -> None:
    """Run evaluation N times in parallel, print summary statistics and export results."""
    print(f"Connecting to Ollama ({model})...\n")
    llm = OllamaClient(model=model, temperature=temperature)
    n_turns = len(config.turns)

    print(f"Launching {runs} runs ({runs * 3} total tasks) in pool of {workers} workers\n", flush=True)
    start = time.time()

    scores: list[list[int]] = [[], [], []]
    hits_per_turn: list[list[int]] = [[0] * n_turns for _ in range(3)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_task: dict[concurrent.futures.Future, tuple[int, int]] = {}
        for i in range(runs):
            idx = i + 1
            future_to_task[pool.submit(run_with_store, llm, config)] = (idx, 0)
            future_to_task[pool.submit(run_with_store_with_history, llm, config)] = (idx, 1)
            future_to_task[pool.submit(run_without_store, llm, config)] = (idx, 2)

        run_results: dict[int, list[int | None]] = {i + 1: [None, None, None] for i in range(runs)}

        for future in concurrent.futures.as_completed(future_to_task):
            run_idx, condition_idx = future_to_task[future]
            res = future.result()
            hits = sum(r["hit"] for r in res)

            for r in res:
                if r["hit"]:
                    hits_per_turn[condition_idx][r["turn"] - 1] += 1

            run_results[run_idx][condition_idx] = hits
            scores[condition_idx].append(hits)

            if all(v is not None for v in run_results[run_idx]):
                s1, s2, s3 = run_results[run_idx]
                print(f"✓ Run {run_idx:>2}: [1] {s1}/{n_turns} | [2] {s2}/{n_turns} | [3] {s3}/{n_turns}", flush=True)

    elapsed = time.time() - start
    n = len(scores[0])

    print("\n" + "=" * 80)
    print(f"SUMMARY OVER {n} RUNS")
    print("=" * 80)

    condition_labels = [
        "[1] WITH STORE            ",
        "[2] WITH STORE (+History) ",
        "[3] NO STORE              ",
    ]

    for label, sc in zip(condition_labels, scores):
        avg = sum(sc) / n
        var = statistics.variance(sc) if n > 1 else 0.0
        std = statistics.stdev(sc) if n > 1 else 0.0
        sc_str = ", ".join(str(x) for x in sc)
        print(f"  {label} | Avg: {avg:.2f}/{n_turns} | Var: {var:.2f} | StdDev: {std:.2f} | Scores: [{sc_str}]")

    print("\n  PER-TURN ACCURACY:")
    print(f"    {'Turn':<4} | {'[1]':<24} | {'[2]':<24} | {'[3]':<24}")
    print(f"    {'─'*4} | {'─'*24} | {'─'*24} | {'─'*24}")
    for t in range(n_turns):
        acc1, acc2, acc3 = hits_per_turn[0][t], hits_per_turn[1][t], hits_per_turn[2][t]
        s1 = f"{acc1:>2}/{n} ({acc1 * 100 // n:>3}%)"
        s2 = f"{acc2:>2}/{n} ({acc2 * 100 // n:>3}%)"
        s3 = f"{acc3:>2}/{n} ({acc3 * 100 // n:>3}%)"
        print(f"    {t+1:>4} | {s1:<24} | {s2:<24} | {s3:<24}")

    print("=" * 80)
    print(f"Total wall-clock time: {elapsed:.1f}s\n")

    # Export results to CSV
    csv_filename = "eval_results.csv"
    file_exists = os.path.isfile(csv_filename)
    prompt_ver = get_eval_prompt_version(config.eval_prompt_version)
    try:
        with open(csv_filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Domain", "Model", "Temp", "Prompt_Ver", "Runs", "Summary_Metric",
                    "With_Store", "Store_History", "No_Store"
                ])

            # Accuracy per domain
            display_model = model_alias or model
            avg0 = (sum(scores[0]) / n) / n_turns if n_turns > 0 else 0
            avg1 = (sum(scores[1]) / n) / n_turns if n_turns > 0 else 0
            avg2 = (sum(scores[2]) / n) / n_turns if n_turns > 0 else 0
            writer.writerow([
                config.name, display_model, temperature, prompt_ver, runs, "Average_Accuracy",
                f"{avg0:.4f}", f"{avg1:.4f}", f"{avg2:.4f}"
            ])

            # Variance in raw score
            var0 = statistics.variance(scores[0]) if n > 1 else 0.0
            var1 = statistics.variance(scores[1]) if n > 1 else 0.0
            var2 = statistics.variance(scores[2]) if n > 1 else 0.0
            writer.writerow([
                config.name, display_model, temperature, prompt_ver, runs, "Variance_Raw_Score",
                f"{var0:.4f}", f"{var1:.4f}", f"{var2:.4f}"
            ])

            # StdDev in raw score
            std0 = statistics.stdev(scores[0]) if n > 1 else 0.0
            std1 = statistics.stdev(scores[1]) if n > 1 else 0.0
            std2 = statistics.stdev(scores[2]) if n > 1 else 0.0
            writer.writerow([
                config.name, display_model, temperature, prompt_ver, runs, "StdDev_Raw_Score",
                f"{std0:.4f}", f"{std1:.4f}", f"{std2:.4f}"
            ])

        print(f"Results exported to {csv_filename}")
    except Exception as e:
        print(f"Failed to write CSV: {e}")


def run_multi_eval_dual_agent(
    config: DomainConfig,
    runs: int = 10,
    workers: int = 4,
    model: str = "gemma3:1b",
    temperature: float = 0.0,
    model_alias: str | None = None,
    reasoner_model: str | None = None,
    matcher_model: str | None = None,
) -> None:
    """Run evaluation N times with dual-agent conditions in parallel.
    
    Tests:
      [1] WITH STORE (Dual-Agent): Stateless, fresh store per turn
      [2] WITH STORE + Chat History (Dual-Agent): Conversational, persistent store
    
    Provides summary statistics and exports results to CSV.
    
    Args:
        config: Domain configuration.
        runs: Number of evaluation runs.
        workers: Number of parallel workers.
        model: Default model for both agents (used if reasoner_model/matcher_model not provided).
        temperature: Sampling temperature.
        model_alias: Optional display name for the model.
        reasoner_model: Optional override for reasoning agent model.
        matcher_model: Optional override for matcher agent model.
    """
    # Apply fallbacks: use --model if individual model args not provided
    reasoner_model = reasoner_model or model
    matcher_model = matcher_model or model
    
    print(f"Connecting to Ollama (Reasoner: {reasoner_model}, Matcher: {matcher_model})...\n")
    llm = OllamaClient(model=model, temperature=temperature)
    n_turns = len(config.turns)

    print(f"Launching {runs} runs ({runs * 2} total tasks) with DUAL-AGENT in pool of {workers} workers\n", flush=True)
    start = time.time()

    scores: list[list[int]] = [[], []]  # End-to-end raw hits for run-level trace
    metric_scores: list[dict[str, list[float]]] = [
        {"binding": [], "end_to_end": []},
        {"binding": [], "end_to_end": []},
    ]
    hits_per_turn: list[list[int]] = [[0] * n_turns for _ in range(2)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_task: dict[concurrent.futures.Future, tuple[int, int]] = {}
        for i in range(runs):
            idx = i + 1
            future_to_task[pool.submit(run_with_store_dual_agent, llm, config, reasoner_model, matcher_model)] = (idx, 0)
            future_to_task[pool.submit(run_with_store_with_history_dual_agent, llm, config, reasoner_model, matcher_model)] = (idx, 1)

        run_results: dict[int, list[int | None]] = {i + 1: [None, None] for i in range(runs)}

        for future in concurrent.futures.as_completed(future_to_task):
            run_idx, condition_idx = future_to_task[future]
            res = future.result()
            end_to_end_hits = sum(1 for r in res if r.get("end_to_end_correct", False))
            binding_total = sum(1 for r in res if r.get("binding_scored", False))
            binding_hits = sum(1 for r in res if r.get("binding_scored", False) and r.get("binding_correct", False))

            end_to_end_ratio = (end_to_end_hits / n_turns) if n_turns else 0.0
            binding_ratio = (binding_hits / binding_total) if binding_total else 0.0

            for r in res:
                if r.get("end_to_end_correct", False):
                    hits_per_turn[condition_idx][r["turn"] - 1] += 1

            run_results[run_idx][condition_idx] = end_to_end_hits
            scores[condition_idx].append(end_to_end_hits)

            metric_scores[condition_idx]["end_to_end"].append(end_to_end_ratio)
            metric_scores[condition_idx]["binding"].append(binding_ratio)

            if all(v is not None for v in run_results[run_idx]):
                s1, s2 = run_results[run_idx]
                print(f"✓ Run {run_idx:>2}: [1 DA] {s1}/{n_turns} | [2 DA] {s2}/{n_turns}", flush=True)

    elapsed = time.time() - start
    n = len(scores[0])

    print("\n" + "=" * 80)
    print(f"SUMMARY OVER {n} RUNS (DUAL-AGENT)")
    print("=" * 80)

    condition_labels = [
        "[1] WITH STORE (Dual-Agent)            ",
        "[2] WITH STORE +History (Dual-Agent)   ",
    ]

    for idx, label in enumerate(condition_labels):
        print(f"  {label}")
        for metric_name, metric_label in (
            ("binding", "Belief Binding Rate (BBR)"),
            ("end_to_end", "End-to-End (BTR if counterfactual)"),
        ):
            sc = metric_scores[idx][metric_name]
            avg = sum(sc) / n
            var = statistics.variance(sc) if n > 1 else 0.0
            std = statistics.stdev(sc) if n > 1 else 0.0
            print(f"    - {metric_label:<10} Avg: {avg:.4f} | Var: {var:.6f} | StdDev: {std:.4f}")

        raw_hits = ", ".join(str(x) for x in scores[idx])
        print(f"    - End-to-End raw hits: [{raw_hits}]")

    print("\n  PER-TURN ACCURACY:")
    print(f"    {'Turn':<4} | {'[1 DA]':<24} | {'[2 DA]':<24}")
    print(f"    {'─'*4} | {'─'*24} | {'─'*24}")
    for t in range(n_turns):
        acc1, acc2 = hits_per_turn[0][t], hits_per_turn[1][t]
        s1 = f"{acc1:>2}/{n} ({acc1 * 100 // n:>3}%)"
        s2 = f"{acc2:>2}/{n} ({acc2 * 100 // n:>3}%)"
        print(f"    {t+1:>4} | {s1:<24} | {s2:<24}")

    print("=" * 80)
    print(f"Total wall-clock time: {elapsed:.1f}s\n")

    # Export results to CSV
    csv_filename = "eval_results_dual_agent.csv"
    file_exists = os.path.isfile(csv_filename)
    prompt_ver = get_eval_prompt_version(config.eval_prompt_version)
    try:
        with open(csv_filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Domain",
                    "Model",
                    "Reasoner_Model",
                    "Matcher_Model",
                    "Temp",
                    "Prompt_Ver",
                    "Runs",
                    "Metric_Family",
                    "Summary_Metric",
                    "Dual_Agent_Store",
                    "Dual_Agent_Store_History",
                ])

            display_model = model_alias or model
            for metric_key, metric_family in (
                ("binding", "Binding"),
                ("end_to_end", "End_to_End"),
            ):
                avg0 = sum(metric_scores[0][metric_key]) / n if n > 0 else 0.0
                avg1 = sum(metric_scores[1][metric_key]) / n if n > 0 else 0.0
                writer.writerow([
                    config.name,
                    display_model,
                    reasoner_model,
                    matcher_model,
                    temperature,
                    prompt_ver,
                    runs,
                    metric_family,
                    "Average_Accuracy",
                    f"{avg0:.4f}",
                    f"{avg1:.4f}",
                ])

                var0 = statistics.variance(metric_scores[0][metric_key]) if n > 1 else 0.0
                var1 = statistics.variance(metric_scores[1][metric_key]) if n > 1 else 0.0
                writer.writerow([
                    config.name,
                    display_model,
                    reasoner_model,
                    matcher_model,
                    temperature,
                    prompt_ver,
                    runs,
                    metric_family,
                    "Variance_Accuracy",
                    f"{var0:.6f}",
                    f"{var1:.6f}",
                ])

                std0 = statistics.stdev(metric_scores[0][metric_key]) if n > 1 else 0.0
                std1 = statistics.stdev(metric_scores[1][metric_key]) if n > 1 else 0.0
                writer.writerow([
                    config.name,
                    display_model,
                    reasoner_model,
                    matcher_model,
                    temperature,
                    prompt_ver,
                    runs,
                    metric_family,
                    "Standard_Deviation_Accuracy",
                    f"{std0:.6f}",
                    f"{std1:.6f}",
                ])

        print(f"Results exported to {csv_filename}")
    except Exception as e:
        print(f"Failed to write CSV: {e}")

