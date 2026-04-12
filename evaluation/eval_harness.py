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
import concurrent.futures
import statistics
from dataclasses import dataclass
from typing import Any, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.engine import SYSTEM_PROMPT
from belief_store.llm_client import OllamaClient


# ────────────────────────────────────────────────────────────────────
# System Prompts
# ────────────────────────────────────────────────────────────────────

EVAL_SYSTEM_PROMPT = SYSTEM_PROMPT.rstrip() + """

IMPORTANT: For multiple-choice questions, you MUST end your response with
the word ANSWER: followed by exactly one capital letter (A, B, or C).
Do not write anything after the letter.
"""

BASELINE_SYSTEM_PROMPT = """\
You are a reasoning assistant evaluating facts over a conversation.
You will receive [NEW BELIEF] updates. You MUST remember all previous facts across the conversation.

IMPORTANT: For multiple-choice questions, you MUST end your response with
the word ANSWER: followed by exactly one capital letter (A, B, or C).
Do not write anything after the letter.
"""


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
        default_entities: Fallback entities for turns without "attributes" key.
        is_conversational: Whether store persists across turns.
        accumulate_prior_beliefs: Whether to accumulate prior turn beliefs.
    """
    name: str
    setup_fn: Callable[[BeliefStore], None]
    initial_beliefs: dict[str, Any]
    turns: list[dict]
    baseline_rules: str
    default_entities: str = "applicant, loan"
    is_conversational: bool = True
    accumulate_prior_beliefs: bool = False


# ────────────────────────────────────────────────────────────────────
# Answer Extraction & Logging
# ────────────────────────────────────────────────────────────────────

def extract_answer(response: str) -> str | None:
    """Extract the letter answer (A/B/C) from LLM response."""
    m = re.search(r"ANSWER[:\s]+.*?([A-C])\b", response, re.DOTALL)
    if m:
        return m.group(1)
    m = re.findall(r"\b([A-C])\b", response)
    return m[-1] if m else None


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
    lines = [turn["question"], "\nChoose exactly one:"]
    for letter, text in turn["options"].items():
        lines.append(f"  {letter}) {text}")
    lines.append("\nRespond with REASONING then ANSWER: [Letter]")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────
# Prompt Construction
# ────────────────────────────────────────────────────────────────────

def _build_store_prompt(beliefs_text: str, question: str) -> str:
    """Build prompt for WITH STORE conditions (beliefs + question)."""
    parts = []
    if beliefs_text:
        parts.append("[RELEVANT BELIEFS]\n" + beliefs_text)
    parts.append(f"[QUERY]\n{question}")
    return "\n\n".join(parts)


def _build_baseline_prompt(
    rules: str, belief_updates: list[str], question: str
) -> str:
    """Build prompt for NO STORE condition (rules + belief updates + question)."""
    parts = [rules]
    if belief_updates:
        parts.append("[NEW BELIEF]\n" + "\n".join(belief_updates))
    parts.append(f"[QUERY]\n{question}")
    return "\n\n".join(parts)


# ────────────────────────────────────────────────────────────────────
# Result Processing
# ────────────────────────────────────────────────────────────────────

def _process_result(condition: str, turn_idx: int, turn: dict, response: str) -> dict:
    """Extract answer, log if needed, and return result dict."""
    answer = extract_answer(response)
    if answer is None:
        log_none_answer(condition, turn_idx, response)

    correct = turn["correct"]
    hit = answer == correct

    if answer is not None and not hit:
        log_incorrect_answer(condition, turn_idx, turn["question"], answer, correct, response)

    print(f"  Turn {turn_idx}: LLM={answer}  correct={correct}  {'✓' if hit else '✗'}", flush=True)

    return {
        "turn": turn_idx,
        "answer": answer,
        "correct": correct,
        "hit": hit,
        "response": response,
    }


# ────────────────────────────────────────────────────────────────────
# Evaluation Conditions
# ────────────────────────────────────────────────────────────────────

def run_with_store(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """[1] WITH Store (Stateless): Fresh store per turn, no chat history."""
    results = []

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

        response = llm.generate(EVAL_SYSTEM_PROMPT, prompt)
        results.append(_process_result("WITH STORE", i + 1, turn, response))

    return results


def run_with_store_with_history(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """[2] WITH Store + Chat History: Store-derived beliefs + conversational context."""
    results = []
    messages = [{"role": "system", "content": EVAL_SYSTEM_PROMPT}]

    # For conversational: maintain one store across all turns
    if config.is_conversational:
        store = _init_store(config)

    for i, turn in enumerate(config.turns):
        # Store management
        if config.is_conversational:
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

        messages.append({"role": "user", "content": prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        results.append(_process_result("WITH STORE (+History)", i + 1, turn, response))

    return results


def run_without_store(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """[3] NO Store (Baseline): Rules + chat history only, no explicit belief tracking."""
    results = []
    messages = [{"role": "system", "content": BASELINE_SYSTEM_PROMPT}]
    initial_belief_lines = [f"{k} = {v}" for k, v in config.initial_beliefs.items()]

    for i, turn in enumerate(config.turns):
        # Only new beliefs for this turn (relying on chat history for prior context)
        if i == 0:
            belief_lines = initial_belief_lines
        else:
            belief_lines = [f"{k} = {v}" for k, v in (turn.get("beliefs") or {}).items()]

        # Build and send prompt as part of chat history
        question = _format_question(turn)
        prompt = _build_baseline_prompt(config.baseline_rules, belief_lines, question)

        messages.append({"role": "user", "content": prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        results.append(_process_result("NO STORE", i + 1, turn, response))

    return results


# ────────────────────────────────────────────────────────────────────
# Evaluation Orchestrators
# ────────────────────────────────────────────────────────────────────

def run_single_eval(config: DomainConfig, model: str = "gemma3:1b") -> None:
    """Run single evaluation: all 3 conditions, print results table."""
    print(f"Connecting to Ollama ({model})...\n")
    llm = OllamaClient(model=model)
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
) -> None:
    """Run evaluation N times in parallel, print summary statistics and export results."""
    print(f"Connecting to Ollama ({model})...\n")
    llm = OllamaClient(model=model)
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
        sc_str = ", ".join(str(x) for x in sc)
        print(f"  {label} | Avg: {avg:.2f}/{n_turns} | Var: {var:.2f} | Scores: [{sc_str}]")

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
    try:
        with open(csv_filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Domain", "Summary_Metric", "With_Store", "Store_History", "No_Store"])

            # Accuracy per domain
            avg0 = (sum(scores[0]) / n) / n_turns if n_turns > 0 else 0
            avg1 = (sum(scores[1]) / n) / n_turns if n_turns > 0 else 0
            avg2 = (sum(scores[2]) / n) / n_turns if n_turns > 0 else 0
            writer.writerow([config.name, "Average_Accuracy", f"{avg0:.4f}", f"{avg1:.4f}", f"{avg2:.4f}"])

            # Variance in raw score
            var0 = statistics.variance(scores[0]) if n > 1 else 0.0
            var1 = statistics.variance(scores[1]) if n > 1 else 0.0
            var2 = statistics.variance(scores[2]) if n > 1 else 0.0
            writer.writerow([config.name, "Variance_Raw_Score", f"{var0:.4f}", f"{var1:.4f}", f"{var2:.4f}"])

        print(f"Results exported to {csv_filename}")
    except Exception as e:
        print(f"Failed to write CSV: {e}")
