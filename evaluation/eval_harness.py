"""
eval_harness.py — Shared evaluation framework for all MCQ domain evaluations.

Provides:
  - DomainConfig: dataclass describing a domain's setup, beliefs, turns, rules.
  - run_with_store / run_with_store_with_history / run_without_store: 3 conditions.
  - run_single_eval: runs all 3 conditions and prints a results table.
  - run_multi_eval: parallel N-run benchmark with summary statistics.
"""

from __future__ import annotations

import os
import re
import sys
import time
import concurrent.futures
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.engine import SYSTEM_PROMPT
from belief_store.llm_client import OllamaClient


# ── Shared prompts ───────────────────────────────────────────────────

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


# ── Domain config ────────────────────────────────────────────────────

@dataclass
class DomainConfig:
    """Everything a domain evaluation needs beyond the shared harness logic."""

    name: str
    setup_fn: Callable[[BeliefStore], None]
    initial_beliefs: dict[str, Any]
    turns: list[dict]
    baseline_rules: str
    default_entities: str = "applicant, loan"


# ── Answer extraction & logging ──────────────────────────────────────

def extract_answer(response: str) -> str | None:
    """Pull the letter (A/B/C) from the LLM response."""
    m = re.search(r"ANSWER[:\s]+.*?([A-C])\b", response, re.DOTALL)
    if m:
        return m.group(1)
    m = re.findall(r"\b([A-C])\b", response)
    return m[-1] if m else None


def log_none_answer(condition: str, turn: int, response: str) -> None:
    """Log the raw LLM response when answer extraction fails."""
    log_file = os.path.join(os.path.dirname(__file__), "failed_extractions.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}]\n{response}\n{'-'*40}\n")


def log_incorrect_answer(
    condition: str, turn: int, question: str, actual: str, expected: str, response: str,
) -> None:
    """Log the question and full LLM reasoning when it outputs the wrong letter."""
    log_file = os.path.join(os.path.dirname(__file__), "incorrect_answers.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}] LLM chose {actual}, Correct was {expected}\n")
        f.write(f"QUESTION: {question}\n")
        f.write(f"{response}\n{'-'*40}\n")


# ── Prompt construction ─────────────────────────────────────────────

def _get_filter(turn: dict, default: str) -> tuple[list[str], bool]:
    """Return (filter_items, is_attribute_mode) from a turn definition.

    If the turn has an ``attributes`` key, use attribute-level filtering
    (HopWalker path).  Otherwise fall back to entity-level.
    """
    if "attributes" in turn:
        return list(turn["attributes"]), True
    ents = turn.get("entities", default).split(", ")
    return [e.strip() for e in ents], False


def _resolve_and_prompt(
    store: BeliefStore, filter_items: list[str], is_attribute_mode: bool,
) -> str:
    """Resolve dirty beliefs and serialize to prompt text."""
    if is_attribute_mode:
        store.resolve_dirty_for_attributes(filter_items)
        beliefs_text, _ = store.to_prompt_attributes(filter_items)
    else:
        store.resolve_dirty(filter_items)
        beliefs_text, _ = store.to_prompt(filter_items)
    return beliefs_text


def _format_question(turn: dict) -> str:
    q = turn["question"] + "\n\nChoose exactly one:\n"
    for letter, text in turn["options"].items():
        q += f"  {letter}) {text}\n"
    q += "\nRespond with REASONING then ANSWER: [Letter]"
    return q


def _build_prompt(
    filter_items: list[str],
    new_beliefs_lines: list[str],
    beliefs_text: str | None,
    turn: dict,
) -> str:
    parts = [f"[ENTITY]\n{', '.join(filter_items)}"]
    if new_beliefs_lines:
        parts.append("[NEW BELIEF]\n" + "\n".join(new_beliefs_lines))
    if beliefs_text:
        parts.append("[RELEVANT BELIEFS]\n" + beliefs_text)
    parts.append(f"[QUERY]\n{_format_question(turn)}")
    return "\n\n".join(parts)


def _build_baseline_prompt(
    rules_text: str,
    new_beliefs_lines: list[str],
    turn: dict,
) -> str:
    parts = [rules_text]
    if new_beliefs_lines:
        parts.append("[NEW BELIEF]\n" + "\n".join(new_beliefs_lines))
    parts.append(f"[QUERY]\n{_format_question(turn)}")
    return "\n\n".join(parts)


# ── Result processing ───────────────────────────────────────────────

def _log_and_print(condition: str, turn_idx: int, turn: dict, response: str) -> dict:
    answer = extract_answer(response)
    if answer is None:
        log_none_answer(condition, turn_idx, response)

    correct = turn["correct"]
    hit = answer == correct

    if answer is not None and not hit:
        log_incorrect_answer(condition, turn_idx, turn["question"], answer, correct, response)

    print(f"  Turn {turn_idx}: LLM={answer}  correct={correct}  {'✓' if hit else '✗'}")

    return {
        "turn": turn_idx,
        "answer": answer,
        "correct": correct,
        "hit": hit,
        "response": response,
    }


# ── Condition runners ────────────────────────────────────────────────

def run_with_store(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """Run all turns WITH the belief store (stateless per-turn rebuild)."""
    results = []
    initial_lines = [f"{k} = {v}" for k, v in config.initial_beliefs.items()]

    for i, turn in enumerate(config.turns):
        store = BeliefStore()
        config.setup_fn(store)

        for k, v in config.initial_beliefs.items():
            store.add_hypothesis(k, v)
        for prev_idx in range(i + 1):
            prev_turn = config.turns[prev_idx]
            if prev_turn["beliefs"]:
                for k, v in prev_turn["beliefs"].items():
                    store.add_hypothesis(k, v)

        filter_items, is_attr = _get_filter(turn, config.default_entities)
        beliefs_text = _resolve_and_prompt(store, filter_items, is_attr)

        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_prompt(filter_items, new_lines, beliefs_text, turn)

        response = llm.generate(EVAL_SYSTEM_PROMPT, full_prompt)
        results.append(_log_and_print("WITH STORE", i + 1, turn, response))

    return results


def run_with_store_with_history(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """Run all turns WITH the belief store AND multi-turn chat history."""
    store = BeliefStore()
    config.setup_fn(store)

    for k, v in config.initial_beliefs.items():
        store.add_hypothesis(k, v)

    results = []
    messages = [{"role": "system", "content": EVAL_SYSTEM_PROMPT}]
    initial_lines = [f"{k} = {v}" for k, v in config.initial_beliefs.items()]

    for i, turn in enumerate(config.turns):
        filter_items, is_attr = _get_filter(turn, config.default_entities)
        if turn["beliefs"]:
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)

        beliefs_text = _resolve_and_prompt(store, filter_items, is_attr)

        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_prompt(filter_items, new_lines, beliefs_text, turn)

        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        results.append(_log_and_print("WITH STORE (+History)", i + 1, turn, response))

    return results


def run_without_store(llm: OllamaClient, config: DomainConfig) -> list[dict]:
    """Run all turns WITHOUT the belief store (baseline LLM + chat history)."""
    results = []
    messages = [{"role": "system", "content": BASELINE_SYSTEM_PROMPT}]
    initial_lines = [f"{k} = {v}" for k, v in config.initial_beliefs.items()]

    for i, turn in enumerate(config.turns):
        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_baseline_prompt(config.baseline_rules, new_lines, turn)

        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        results.append(_log_and_print("NO STORE", i + 1, turn, response))

    return results


# ── High-level orchestrators ────────────────────────────────────────

def run_single_eval(config: DomainConfig, model: str = "gemma3:1b") -> None:
    """Run one complete eval (all 3 conditions) and print the results table."""
    print(f"Connecting to Ollama ({model})...\n")
    llm = OllamaClient(model=model)
    n_turns = len(config.turns)

    print("=" * 60)
    print("CONDITION 1: WITH Store (Stateless)")
    print("=" * 60)
    with_store = run_with_store(llm, config)
    score_with = sum(r["hit"] for r in with_store)

    print()
    print("=" * 60)
    print("CONDITION 2: WITH Store (+Chat History)")
    print("=" * 60)
    with_history = run_with_store_with_history(llm, config)
    score_with_history = sum(r["hit"] for r in with_history)

    print()
    print("=" * 60)
    print("CONDITION 3: NO Store (+Chat History)")
    print("=" * 60)
    no_store = run_without_store(llm, config)
    score_no_store = sum(r["hit"] for r in no_store)

    # Results table
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print()
    print(f"  {'Turn':<6} {'Store':<12} {'Store+Hist':<12} {'No Store':<12}")
    print(f"  {'─'*6} {'─'*12} {'─'*12} {'─'*12}")
    for r1, r2, r3 in zip(with_store, with_history, no_store):
        t = r1["turn"]
        s1 = "✓" if r1["hit"] else f"✗ ({r1['answer']})"
        s2 = "✓" if r2["hit"] else f"✗ ({r2['answer']})"
        s3 = "✓" if r3["hit"] else f"✗ ({r3['answer']})"
        print(f"  {t:<6} {s1:<12} {s2:<12} {s3:<12}")

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
    """Run the evaluation N times in parallel and print summary statistics."""
    print(f"Connecting to Ollama ({model})...\n")
    llm = OllamaClient(model=model)
    n_turns = len(config.turns)

    print(f"Launching {runs} runs ({runs * 3} total tasks in flat parallel pool of {workers})\n")
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
            hits = 0
            for r in res:
                if r["hit"]:
                    hits += 1
                    hits_per_turn[condition_idx][r["turn"] - 1] += 1

            run_results[run_idx][condition_idx] = hits
            scores[condition_idx].append(hits)

            if all(v is not None for v in run_results[run_idx]):
                s1, s2, s3 = run_results[run_idx]
                print(f"✓ Run {run_idx:>2}: [1] {s1}/{n_turns} | [2] {s2}/{n_turns} | [3] {s3}/{n_turns}")

    elapsed = time.time() - start
    n = len(scores[0])

    print("\n" + "=" * 65)
    print(f"SUMMARY OVER {n} RUNS")
    print("=" * 65)
    for label, sc in zip(
        ["[1] WITH STORE            ", "[2] WITH STORE (+History) ", "[3] NO STORE              "],
        scores,
    ):
        avg = sum(sc) / n
        var = statistics.variance(sc) if n > 1 else 0.0
        sc_str = ", ".join(str(x) for x in sc)
        print(f"  {label} | Avg: {avg:.2f}/{n_turns} | Var: {var:.2f} | Scores: [{sc_str}]")
    
    print("\n  PER-TURN ACCURACY:")
    print(f"    {'Turn':<4} | {'[1] WITH STORE':<20} | {'[2] STORE (+Hist)':<20} | {'[3] NO STORE':<20}")
    print(f"    {'─'*4} | {'─'*20} | {'─'*20} | {'─'*20}")
    for t in range(n_turns):
        acc1, acc2, acc3 = hits_per_turn[0][t], hits_per_turn[1][t], hits_per_turn[2][t]
        s1 = f"{acc1:>2}/{n} ({acc1 * 100 // n:>3}%)"
        s2 = f"{acc2:>2}/{n} ({acc2 * 100 // n:>3}%)"
        s3 = f"{acc3:>2}/{n} ({acc3 * 100 // n:>3}%)"
        print(f"    {t+1:>4} | {s1:<20} | {s2:<20} | {s3:<20}")
        
    print("=" * 65)
    print(f"Total wall-clock time: {elapsed:.1f}s\n")
