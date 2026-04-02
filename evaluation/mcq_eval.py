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
the word ANSWER: followed by exactly one capital letter (A, B, or C).
Do not write anything after the letter.
"""

# Lean system prompt for the baseline — rules are injected per-turn instead.
BASELINE_SYSTEM_PROMPT = """\
You are a reasoning assistant evaluating facts over a conversation.
You will receive [NEW BELIEF] updates. You MUST remember all previous facts across the conversation.

IMPORTANT: For multiple-choice questions, you MUST end your response with
the word ANSWER: followed by exactly one capital letter (A, B, or C).
Do not write anything after the letter.
"""

# The 10 deterministic loan-domain rules injected into every baseline prompt.
LOAN_RULES = """\
[RULES]
1. loan.adjusted_income = applicant.income - (applicant.dependents * 500)
2. loan.credit_score_effective = applicant.credit_score + (50 if applicant.co_signer else 0)
3. loan.high_risk_flag = True if applicant.debt_ratio >= 0.3 else False
4. loan.eligible = True ONLY IF loan.adjusted_income >= loan.min_income AND loan.credit_score_effective >= loan.min_credit AND applicant.debt_ratio < loan.max_debt_ratio AND applicant.employment_status != 'unemployed' AND NOT (applicant.bankruptcy_history == True AND applicant.employment_duration_months < 24)
5. loan.rate_tier = "preferred" if loan.credit_score_effective >= 750 else "standard" (None if not loan.eligible)
6. loan.max_amount = 100000 if applicant.has_collateral else 30000 (0 if not loan.eligible)
7. loan.application_status = "approved" if loan.eligible and applicant.loan_amount_requested <= loan.max_amount. Otherwise "denied_amount_exceeded" or "denied_ineligible"
8. loan.requires_insurance = True if loan.high_risk_flag AND loan.application_status == "approved" else False
9. loan.review_queue = "manual_review" if loan.high_risk_flag else "auto_approve" ("rejected" if denied)
10. loan.base_interest_rate = 4.5 if loan.rate_tier == "preferred" else 6.5. Add +1.0 if loan.requires_insurance. (None if not loan.eligible)
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
    "applicant.dependents": 2,
    "loan.min_income": 5000,
    "loan.min_credit": 650,
    "loan.max_debt_ratio": 0.4,
}

TURNS = [
    {
        "entities": "loan",
        "beliefs": {},
        "question": "What is the application status and review queue?",
        "options": {
            "A": "denied_ineligible, rejected",
            "B": "approved, auto_approve",
            "C": "approved, manual_review",
        },
        "correct": "B",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.debt_ratio": 0.35},
        "question": "What is the required insurance status and review queue?",
        "options": {
            "A": "requires_insurance = True, review_queue = manual_review",
            "B": "requires_insurance = False, review_queue = auto_approve",
            "C": "requires_insurance = True, review_queue = auto_approve",
        },
        "correct": "A",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.credit_score": 740},
        "question": "What is the current application status?",
        "options": {
            "A": "preferred_approved",
            "B": "denied",
            "C": "approved",
        },
        "correct": "C",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.co_signer": True},
        "question": "What is the new base interest rate?",
        "options": {
            "A": "5.5", 
            "B": "7.5", 
            "C": "4.5", 
        },
        "correct": "A",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.has_collateral": True},
        "question": "What are the final application status and base interest rate?",
        "options": {
            "A": "approved, 5.5",
            "B": "pending_manager_approval, 5.5",
            "C": "approved, 4.5",
        },
        "correct": "A",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.employment_status": "unemployed"},
        "question": "What is the application status and base interest rate?",
        "options": {
            "A": "approved, 5.5",
            "B": "denied_ineligible, None",
            "C": "denied_ineligible, 6.5", 
        },
        "correct": "B",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.employment_status": "employed"},
        "question": "What is the maximum loan amount and application status?",
        "options": {
            "A": "100000, approved",
            "B": "30000, approved",
            "C": "100000, denied_amount_exceeded",
        },
        "correct": "A",
    },
    {
        "entities": "applicant, loan",
        "beliefs": {"applicant.dependents": 3},
        "question": "What is the adjusted income and application status?",
        "options": {
            "A": "5000, approved",
            "B": "4500, denied_ineligible",
            "C": "3000, denied_ineligible",
        },
        "correct": "B",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.loan_amount_requested": 20_000},
        "question": "What is the application status?",
        "options": {
            "A": "approved",
            "B": "denied_amount_exceeded",
            "C": "denied_ineligible",
        },
        "correct": "C",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.income": 7000},
        "question": "What is the application status?",
        "options": {
            "A": "approved",
            "B": "denied_amount_exceeded",
            "C": "denied_ineligible",
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
    q += "\nRespond with REASONING then ANSWER: [Letter]"

    parts.append(f"[QUERY]\n{q}")
    return "\n\n".join(parts)


def log_none_answer(condition: str, turn: int, response: str) -> None:
    """Log the raw LLM response when answer extraction fails (returns None)."""
    log_file = os.path.join(os.path.dirname(__file__), "failed_extractions.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}]\n{response}\n{'-'*40}\n")


def log_incorrect_answer(condition: str, turn: int, question: str, actual: str, expected: str, response: str) -> None:
    """Log the question and full LLM reasoning when it outputs the wrong letter."""
    log_file = os.path.join(os.path.dirname(__file__), "incorrect_answers.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}] LLM chose {actual}, Correct was {expected}\n")
        f.write(f"QUESTION: {question}\n")
        f.write(f"{response}\n{'-'*40}\n")


def extract_answer(response: str) -> str | None:
    """Pull the letter (A/B/C) from the LLM response."""
    # Scan for a standalone capital A, B, or C after the ANSWER: block
    m = re.search(r"ANSWER[:\s]+.*?([A-C])\b", response, re.DOTALL)
    if m:
        return m.group(1)
    # Fallback: last standalone capital A, B, or C anywhere
    m = re.findall(r"\b([A-C])\b", response)
    return m[-1] if m else None


# ── Helpers ─────────────────────────────────────────────────────────

def _get_entities(turn: dict) -> list[str]:
    """Helper to parse the entities list from a turn."""
    ents = turn.get("entities", "applicant, loan").split(", ")
    return [e.strip() for e in ents]


def _build_prompt(entities: list[str], new_beliefs_lines: list[str], beliefs_text: str | None, turn: dict) -> str:
    """Helper to construct the structured evaluation prompt."""
    parts = [f"[ENTITY]\n{', '.join(entities)}"]
    
    if new_beliefs_lines:
        parts.append("[NEW BELIEF]\n" + "\n".join(new_beliefs_lines))
    
    if beliefs_text:
        parts.append("[RELEVANT BELIEFS]\n" + beliefs_text)

    q = turn["question"] + "\n\nChoose exactly one:\n"
    for letter, text in turn["options"].items():
        q += f"  {letter}) {text}\n"
    q += "\nRespond with REASONING then ANSWER: [Letter]"
    parts.append(f"[QUERY]\n{q}")
    
    return "\n\n".join(parts)


def _log_and_print(condition: str, turn_idx: int, turn: dict, response: str) -> dict:
    """Extract answer, log errors, and return result dict."""
    answer = extract_answer(response)
    if answer is None:
        log_none_answer(condition, turn_idx, response)
    
    correct = turn["correct"]
    hit = (answer == correct)
    
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


def run_with_store(llm: OllamaClient, turns: list[dict]) -> list[dict]:
    """Run all 10 turns WITH the belief store. Stateless (store is re-derived each turn)."""
    results = []
    initial_lines = [f"{k} = {v}" for k, v in INITIAL_BELIEFS.items()]

    for i, turn in enumerate(turns):
        # 1. Setup fresh store and resolve
        store = BeliefStore()
        setup_loan_domain(store)
        
        # Hydrate with initial + all cumulative beliefs up to now
        for k, v in INITIAL_BELIEFS.items():
            store.add_hypothesis(k, v)
        for prev_idx in range(i + 1):
            prev_turn = turns[prev_idx]
            if prev_turn["beliefs"]:
                for k, v in prev_turn["beliefs"].items():
                    store.add_hypothesis(k, v)

        entities = _get_entities(turn)
        store.resolve_dirty(entities)
        beliefs_text, _ = store.to_prompt(entities)

        # 2. Build prompt
        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_prompt(entities, new_lines, beliefs_text, turn)
        
        # 3. Generate
        response = llm.generate(EVAL_SYSTEM_PROMPT, full_prompt)

        # 4. Result
        res = _log_and_print("WITH STORE", i + 1, turn, response)
        results.append(res)

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
        entities = _get_entities(turn)
        
        # 1. Update store
        if turn["beliefs"]:
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)
        
        store.resolve_dirty(entities)
        beliefs_text, _ = store.to_prompt(entities)

        # 2. Build prompt
        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_prompt(entities, new_lines, beliefs_text, turn)
        
        # 3. Chat
        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        # 4. Result
        res = _log_and_print("WITH STORE (+History)", i + 1, turn, response)
        results.append(res)

    return results


def _build_baseline_prompt(entities: list[str], new_beliefs_lines: list[str], turn: dict) -> str:
    """Build the baseline prompt with the loan rules injected directly into each turn."""
    parts = [LOAN_RULES]

    if new_beliefs_lines:
        parts.append("[NEW BELIEF]\n" + "\n".join(new_beliefs_lines))

    q = turn["question"] + "\n\nChoose exactly one:\n"
    for letter, text in turn["options"].items():
        q += f"  {letter}) {text}\n"
    q += "\nRespond with REASONING then ANSWER: [Letter]"
    parts.append(f"[QUERY]\n{q}")

    return "\n\n".join(parts)


def run_without_store(llm: OllamaClient, turns: list[dict]) -> list[dict]:
    """Run all 10 turns WITHOUT the belief store, but WITH chat history.
    
    The loan-domain rules are injected directly into every user-turn prompt
    rather than being hidden in the system prompt, making this a fairer
    in-context reasoning baseline.
    """
    results = []
    messages = [{"role": "system", "content": BASELINE_SYSTEM_PROMPT}]
    initial_lines = [f"{k} = {v}" for k, v in INITIAL_BELIEFS.items()]

    for i, turn in enumerate(turns):
        entities = ["applicant", "loan"]

        # 1. Build prompt — rules are included in every turn via _build_baseline_prompt
        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_baseline_prompt(entities, new_lines, turn)

        # 2. Chat
        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        # 3. Result
        res = _log_and_print("NO STORE", i + 1, turn, response)
        results.append(res)

    return results


# ── Main ─────────────────────────────────────────────────────────────


def main():
    print("Connecting to Ollama (gemma3:1b)...\n")
    llm = OllamaClient(model="gemma3:1b")

    print("=" * 60)
    print("CONDITION 1: WITH Store (Stateless)")
    print("=" * 60)
    with_store = run_with_store(llm, TURNS)
    score_with = sum(r["hit"] for r in with_store)

    print()
    print("=" * 60)
    print("CONDITION 2: WITH Store (+Chat History)")
    print("=" * 60)
    with_history = run_with_store_with_history(llm, TURNS)
    score_with_history = sum(r["hit"] for r in with_history)

    print()
    print("=" * 60)
    print("CONDITION 3: NO Store (+Chat History)")
    print("=" * 60)
    no_store = run_without_store(llm, TURNS)
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
