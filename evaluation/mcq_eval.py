"""
MCQ Evaluation — Belief-Store LLM vs Bare LLM.

Runs 10 turns where beliefs change across turns. Each turn asks an MCQ:
  A) correct (based on current resolved beliefs)
  B) stale (based on a PREVIOUS belief value)
  C) irrelevant nonsense

Condition 1 (WITH store):  beliefs are resolved and injected as [RELEVANT BELIEFS]
Condition 2 (NO store):    [RELEVANT BELIEFS] is empty — LLM has no state across turns

Usage:
    python3 evaluation/mcq_eval.py
"""

from __future__ import annotations

import re
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain
from belief_store.engine import ReasoningEngine, SYSTEM_PROMPT
from belief_store.llm_client import OllamaClient


# Eval-specific system prompt — forces letter-only answers
EVAL_SYSTEM_PROMPT = SYSTEM_PROMPT.rstrip() + """

IMPORTANT: For multiple-choice questions, you MUST end your response with
exactly one letter: A, B, or C. Example: ANSWER: A
Do not write anything after the letter.
"""


# ── 10-Turn scenario ─────────────────────────────────────────────────

# Each turn: (new_beliefs_dict, question, options, correct_letter)
# Beliefs accumulate across turns in the store condition.

INITIAL_BELIEFS = {
    "applicant.income": 6000,
    "applicant.credit_score": 720,
    "applicant.co_signer": False,
    "applicant.debt_ratio": 0.20,
    "applicant.employment_status": "employed",
    "applicant.bankruptcy_history": False,
    "applicant.employment_duration_months": 36,
    "applicant.has_collateral": False,
    "applicant.loan_amount_requested": 10_000,
    "loan.min_income": 5000,
    "loan.min_credit": 650,
    "loan.max_debt_ratio": 0.4,
}

TURNS = [
    # Turn 1: baseline — approved
    {
        "beliefs": {},  # no changes, just the initial state
        "question": "What is the current application status?",
        "options": {
            "A": "approved",
            "B": "denied_ineligible",
            "C": "pending_review",
        },
        "correct": "A",
    },
    # Turn 2: income drops → denied
    {
        "beliefs": {"applicant.income": 3000},
        "question": "After the income change, what is the application status?",
        "options": {
            "A": "denied_ineligible",
            "B": "approved (the previous status)",
            "C": "referred_to_manager",
        },
        "correct": "A",
    },
    # Turn 3: income recovers → approved again
    {
        "beliefs": {"applicant.income": 7000},
        "question": "What is the applicant's eligibility now?",
        "options": {
            "A": "Eligible (True)",
            "B": "Ineligible (it was denied last turn)",
            "C": "Eligible only with manager approval",
        },
        "correct": "A",
    },
    # Turn 4: co-signer added → credit_score_effective goes up
    {
        "beliefs": {"applicant.co_signer": True},
        "question": "What is the effective credit score now?",
        "options": {
            "A": "770 (720 + 50 co-signer boost)",
            "B": "720 (same as raw credit score)",
            "C": "650 (the minimum threshold)",
        },
        "correct": "A",
    },
    # Turn 5: effective score 770 → preferred rate
    {
        "beliefs": {},  # no change, just asking about rate
        "question": "What rate tier does the applicant qualify for?",
        "options": {
            "A": "preferred (effective score 770 ≥ 750)",
            "B": "standard (effective score below 750)",
            "C": "subprime",
        },
        "correct": "A",
    },
    # Turn 6: co-signer removed → effective drops back, rate changes
    {
        "beliefs": {"applicant.co_signer": False},
        "question": "After removing the co-signer, what is the rate tier?",
        "options": {
            "A": "standard (effective score 720 < 750)",
            "B": "preferred (it was preferred last turn)",
            "C": "variable_rate",
        },
        "correct": "A",
    },
    # Turn 7: collateral added → max_amount goes up
    {
        "beliefs": {"applicant.has_collateral": True},
        "question": "What is the maximum loan amount now?",
        "options": {
            "A": "100,000 (has collateral)",
            "B": "30,000 (the previous max without collateral)",
            "C": "500,000",
        },
        "correct": "A",
    },
    # Turn 8: debt ratio spikes → high risk + ineligible
    {
        "beliefs": {"applicant.debt_ratio": 0.45},
        "question": "What is the high risk flag and eligibility status?",
        "options": {
            "A": "high_risk_flag = True, eligible = False (debt_ratio 0.45 ≥ max 0.4)",
            "B": "high_risk_flag = True, eligible = True (it was eligible before)",
            "C": "high_risk_flag = False, eligible = True",
        },
        "correct": "A",
    },
    # Turn 9: debt ratio fixed → eligible again, still has collateral
    {
        "beliefs": {"applicant.debt_ratio": 0.15},
        "question": "After fixing the debt ratio, what is the application status and max amount?",
        "options": {
            "A": "approved, max_amount = 100,000",
            "B": "denied_ineligible, max_amount = 0 (it was denied last turn)",
            "C": "approved, max_amount = 50,000",
        },
        "correct": "A",
    },
    # Turn 10: loan request exceeds max → denied_amount_exceeded
    {
        "beliefs": {"applicant.loan_amount_requested": 150_000},
        "question": "The applicant now requests 150,000. What is the application status?",
        "options": {
            "A": "denied_amount_exceeded (150,000 > max 100,000)",
            "B": "approved (it was approved last turn)",
            "C": "denied_credit_score",
        },
        "correct": "A",
    },
]


# ── Run evaluation ───────────────────────────────────────────────────


def build_mcq_query(turn: dict, entities: str = "applicant, loan") -> str:
    """Build the structured prompt for one MCQ turn."""
    parts = [f"[ENTITY]\n{entities}"]

    # NEW BELIEF section (if any changes this turn)
    if turn["beliefs"]:
        lines = [f"{k} = {v}" for k, v in turn["beliefs"].items()]
        parts.append("[NEW BELIEF]\n" + "\n".join(lines))

    # QUERY section with MCQ
    q = turn["question"] + "\n\nChoose exactly one:\n"
    for letter, text in turn["options"].items():
        q += f"  {letter}) {text}\n"
    q += "\nRespond with REASONING then ANSWER: <letter>"

    parts.append(f"[QUERY]\n{q}")
    return "\n\n".join(parts)


def extract_answer(response: str) -> str | None:
    """Pull the letter (A/B/C) from the LLM response."""
    m = re.search(r"ANSWER[:\s]+([A-C])", response, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Fallback: last standalone letter
    m = re.findall(r"\b([A-C])\b", response)
    return m[-1].upper() if m else None


def run_with_store(llm: OllamaClient, turns: list[dict]) -> list[dict]:
    """Run all 10 turns WITH the belief store."""
    import belief_store.engine as engine_mod
    orig_prompt = engine_mod.SYSTEM_PROMPT
    engine_mod.SYSTEM_PROMPT = EVAL_SYSTEM_PROMPT

    store = BeliefStore()
    setup_loan_domain(store)

    # Seed initial beliefs
    for k, v in INITIAL_BELIEFS.items():
        store.add_hypothesis(k, v)

    engine = ReasoningEngine(store, llm)
    results = []

    for i, turn in enumerate(turns):
        query_text = build_mcq_query(turn)
        response = engine.query(query_text)
        answer = extract_answer(response)
        correct = turn["correct"]
        results.append({
            "turn": i + 1,
            "answer": answer,
            "correct": correct,
            "hit": answer == correct,
            "response": response,
        })
        print(f"  Turn {i+1}: LLM={answer}  correct={correct}  {'✓' if answer == correct else '✗'}")

    engine_mod.SYSTEM_PROMPT = orig_prompt
    return results


def run_with_store_with_history(llm: OllamaClient, turns: list[dict]) -> list[dict]:
    """Run all 10 turns WITH the belief store AND WITH chat history."""
    store = BeliefStore()
    setup_loan_domain(store)

    for k, v in INITIAL_BELIEFS.items():
        store.add_hypothesis(k, v)

    results = []
    messages = [{"role": "system", "content": EVAL_SYSTEM_PROMPT}]
    initial_lines = [f"{k} = {v}" for k, v in INITIAL_BELIEFS.items()]

    for i, turn in enumerate(turns):
        entities = ["applicant", "loan"]

        # 1. Update store
        if turn["beliefs"]:
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)
        
        store.resolve_dirty(entities)
        beliefs_text, _ = store.to_prompt(entities)

        # 2. Build explicit prompt
        parts = ["[ENTITY]\napplicant, loan"]

        if i == 0:
            parts.append("[NEW BELIEF]\n" + "\n".join(initial_lines))
        elif turn["beliefs"]:
            lines = [f"{k} = {v}" for k, v in turn["beliefs"].items()]
            parts.append("[NEW BELIEF]\n" + "\n".join(lines))

        parts.append("[RELEVANT BELIEFS]\n" + beliefs_text)

        q = turn["question"] + "\n\nChoose exactly one:\n"
        for letter, text in turn["options"].items():
            q += f"  {letter}) {text}\n"
        q += "\nRespond with REASONING then ANSWER: <letter>"
        parts.append(f"[QUERY]\n{q}")

        full_prompt = "\n\n".join(parts)
        
        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        answer = extract_answer(response)
        correct = turn["correct"]
        results.append({
            "turn": i + 1,
            "answer": answer,
            "correct": correct,
            "hit": answer == correct,
            "response": response,
        })
        print(f"  Turn {i+1}: LLM={answer}  correct={correct}  {'✓' if answer == correct else '✗'}")

    return results


def run_without_store(llm: OllamaClient, turns: list[dict]) -> list[dict]:
    """Run all 10 turns WITHOUT the belief store, but WITH chat history.

    The LLM sees no [RELEVANT BELIEFS] block, but the chat history is
    preserved. It must rely entirely on its context window memory to track
    beliefs across the 10 turns.
    """
    results = []
    messages = [{"role": "system", "content": EVAL_SYSTEM_PROMPT}]

    initial_lines = [f"{k} = {v}" for k, v in INITIAL_BELIEFS.items()]

    for i, turn in enumerate(turns):
        parts = ["[ENTITY]\napplicant, loan"]

        if i == 0:
            parts.append("[NEW BELIEF]\n" + "\n".join(initial_lines))
        elif turn["beliefs"]:
            lines = [f"{k} = {v}" for k, v in turn["beliefs"].items()]
            parts.append("[NEW BELIEF]\n" + "\n".join(lines))

        parts.append("[RELEVANT BELIEFS]\n(no belief store available)")

        q = turn["question"] + "\n\nChoose exactly one:\n"
        for letter, text in turn["options"].items():
            q += f"  {letter}) {text}\n"
        q += "\nRespond with REASONING then ANSWER: <letter>"
        parts.append(f"[QUERY]\n{q}")

        full_prompt = "\n\n".join(parts)
        
        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        answer = extract_answer(response)
        correct = turn["correct"]
        results.append({
            "turn": i + 1,
            "answer": answer,
            "correct": correct,
            "hit": answer == correct,
            "response": response,
        })
        print(f"  Turn {i+1}: LLM={answer}  correct={correct}  {'✓' if answer == correct else '✗'}")

    return results


# ── Main ─────────────────────────────────────────────────────────────


def main():
    print("Connecting to Ollama (gemma3:1b)...\n")
    llm = OllamaClient(model="gemma3:1b")

    # Shuffle MCQ options so the correct answer isn't always A
    shuffled_turns = []
    for turn in TURNS:
        opts = list(turn["options"].values())
        correct_text = turn["options"][turn["correct"]]
        random.shuffle(opts)
        
        new_options = {chr(65+i): opt for i, opt in enumerate(opts)}
        new_correct = next(k for k, v in new_options.items() if v == correct_text)
        
        new_turn = dict(turn)
        new_turn["options"] = new_options
        new_turn["correct"] = new_correct
        shuffled_turns.append(new_turn)

    print("=" * 60)
    print("CONDITION 1: WITH Store (Stateless)")
    print("=" * 60)
    with_store = run_with_store(llm, shuffled_turns)
    score_with = sum(r["hit"] for r in with_store)

    print()
    print("=" * 60)
    print("CONDITION 2: WITH Store (+Chat History)")
    print("=" * 60)
    with_history = run_with_store_with_history(llm, shuffled_turns)
    score_with_history = sum(r["hit"] for r in with_history)

    print()
    print("=" * 60)
    print("CONDITION 3: NO Store (+Chat History)")
    print("=" * 60)
    no_store = run_without_store(llm, shuffled_turns)
    score_no_store = sum(r["hit"] for r in no_store)

    # ── Report ───────────────────────────────────────────────────────
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
    print(f"  [1] WITH STORE:             {score_with}/10  ({score_with * 10}%)")
    print(f"  [2] WITH STORE (+History):  {score_with_history}/10  ({score_with_history * 10}%)")
    print(f"  [3] NO STORE:               {score_no_store}/10  ({score_no_store * 10}%)")
    print()

    if score_with > score_no_store:
        print("  → The belief store improved accuracy.")
    elif score_with == score_no_store:
        print("  → Same score. The MCQ may need harder questions.")
    else:
        print("  → Unexpected: bare LLM outperformed. Check responses.")


if __name__ == "__main__":
    main()
