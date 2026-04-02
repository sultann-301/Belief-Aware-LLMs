"""
Alien Clinic MCQ Evaluation — Belief-Store LLM vs Bare LLM.

Runs 10 turns where beliefs change across turns. Each turn asks an MCQ:
  A) correct (based on current resolved beliefs)
  B) stale (based on a PREVIOUS belief value)
  C) irrelevant nonsense

Usage:
    python3 evaluation/alien_mcq_eval.py
"""

from __future__ import annotations

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.domains.alien_clinic import setup_alien_clinic_domain
from belief_store.engine import SYSTEM_PROMPT
from belief_store.llm_client import OllamaClient


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

# The compressed alien rules for the bare LLM
ALIEN_RULES = """\
[RULES]
1. patient.organ_integrity = "volatile" if ambient_pressure > 5.0 and organism_type == "Yorp". "volatile" if ambient_pressure > 4.0 and organism_type == "Glerps". "brittle" if ambient_pressure > 3.0. Otherwise "stable".
2. zyxostin.phase = "plasma" IF dominant_gas == "methane" ELSE "crystalline". filinan.phase = "vapor" IF dominant_gas == "xenon" ELSE "plasma". snevox.phase = "liquid" IF dominant_gas == "chlorine" ELSE "vapor".
3. LETHAL hazards: organism/compound explode combinations (Glerps+zyxostin, Yorp+filinan, Qwerl+snevox). State-based (plasma+filinan, Snevox+vapor for Qwerl). Condition-based (organ_integrity is "volatile" makes all LETHAL). Otherwise compound hazard is "safe".
4. treatment.active_prescription = Highest priority safe compound. Priorities: Glerps (filinan -> zyxostin -> snevox). Yorp (zyxostin -> snevox -> filinan). Qwerl (snevox -> zyxostin -> filinan). If no safe options, return "none".
5. patient.sensory_status = "telepathic" if active_prescription == "snevox", else "normal".
6. patient.quarantine_required = True if (dominant_gas == "chlorine" AND organism_type == "Qwerl") or (dominant_gas == "methane" AND organism_type == "Yorp"), else False.
7. treatment.duration_cycles = 12 if active_prescription == "snevox" and organ_integrity == "volatile". 0 if active_prescription == "none". Otherwise 5.
8. medical.staff_requirement = "hazmat_team" if quarantine_required == True. "psionic_handler" if sensory_status == "telepathic". Else "standard_medic". (Quarantine overrides Psionic).
9. patient.recovery_prospect = "guarded" if duration_cycles > 10 and staff_requirement == "hazmat_team". "terminal" if duration_cycles == 0. Else "excellent".
10. clinic.billing_tier = "class_omega" if staff_requirement == "psionic_handler" or active_prescription == "snevox". "class_delta" if staff_requirement == "hazmat_team". Otherwise "class_standard".
"""

# Base beliefs
INITIAL_BELIEFS = {
    "patient.organism_type": "Glerps",
    "atmosphere.ambient_pressure": 3.5,
    "atmosphere.dominant_gas": "methane",
}

# The 10 Eval Turns
TURNS = [
    {
        "entities": "treatment, clinic",
        "beliefs": {},
        "question": "What is the active prescription and billing tier?",
        "options": {
            "A": "snevox, class_omega",        # Correct (t=0)
            "B": "filinan, class_standard",    # Wrong fallback
            "C": "none, class_omega",          # Nonsense
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 5.0},
        "question": "What are the new duration cycles and recovery prospect?",
        "options": {
            "A": "5, excellent",               # Stale t=0
            "B": "12, guarded",                # Volatile trap
            "C": "0, terminal",                # Correct (t=1: volatile -> none)
        },
        "correct": "C",
    },
    {
        "entities": "medical, clinic",
        "beliefs": {"patient.organism_type": "Yorp"},
        "question": "What is the required staff requirement and billing tier?",
        "options": {
            "A": "standard_medic, class_standard",  # Stale t=1
            "B": "hazmat_team, class_delta",        # Correct (t=2: yorp+methane -> quarantine -> hazmat -> delta)
            "C": "psionic_handler, class_omega",    # Stale t=0
        },
        "correct": "B",
    },
    {
        "entities": "treatment, medical",
        "beliefs": {"atmosphere.ambient_pressure": 2.0},
        "question": "What is the active prescription and staff requirement?",
        "options": {
            "A": "zyxostin, hazmat_team",      # Correct (t=3: stable. yorp likes zyxostin. methane+yorp=hazmat)
            "B": "none, hazmat_team",          # Stale t=2
            "C": "snevox, psionic_handler",    # Stale t=0
        },
        "correct": "A",
    },
    {
        "entities": "medical, clinic",
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "What is the staff requirement and billing tier?",
        "options": {
            "A": "hazmat_team, class_delta",           # Stale t=3
            "B": "standard_medic, class_standard",     # Correct (t=4: no quarantine in xenon for Yorp)
            "C": "psionic_handler, class_omega",       # Nonsense
        },
        "correct": "B",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.organism_type": "Qwerl"},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "none, terminal",
            "B": "zyxostin, excellent",                # Correct (t=5: Qwerl -> snevox lethal, falls back to zyxostin)
            "C": "snevox, guarded",                    # Trap: Qwerl prefers snevox but it explodes
        },
        "correct": "B",
    },
    {
        "entities": "treatment, clinic",
        "beliefs": {"atmosphere.dominant_gas": "chlorine"},
        "question": "What is the active prescription and billing tier?",
        "options": {
            "A": "zyxostin, class_standard",           # Stale t=5
            "B": "zyxostin, class_delta",              # Correct (t=6: chlorine+Qwerl -> hazmat -> delta)
            "C": "snevox, class_omega",                # Logic failure
        },
        "correct": "B",
    },
    {
        "entities": "patient, treatment",
        "beliefs": {"atmosphere.ambient_pressure": 6.0},
        "question": "What is the organ integrity and active prescription?",
        "options": {
            "A": "volatile, none",                     # Trap (Qwerl has no volatile threshold)
            "B": "brittle, zyxostin",                  # Correct (t=7: Qwerl becomes brittle, but not volatile. zyxostin safe)
            "C": "stable, zyxostin",                   # Stale t=6
        },
        "correct": "B",
    },
    {
        "entities": "patient, treatment",
        "beliefs": {"patient.organism_type": "Glerps"},
        "question": "What is the organ integrity and active prescription?",
        "options": {
            "A": "volatile, none",                     # Correct (t=8: Glerps > 4.0 -> volatile -> all lethal -> none)
            "B": "brittle, snevox",                    # Stale logic
            "C": "volatile, zyxostin",                 # Volatile logic failure
        },
        "correct": "A",
    },
    {
        "entities": "treatment",
        "beliefs": {"atmosphere.ambient_pressure": 3.0},
        "question": "What is the active prescription?",
        "options": {
            "A": "none",
            "B": "filinan",                            # Trap (It's preferred by Glerps, but is plasma so Lethal)
            "C": "snevox",                             # Correct (t=9: filinan and zyxostin lethal, snevox safe)
        },
        "correct": "C",
    },
]


def extract_answer(response: str) -> str | None:
    m = re.search(r"ANSWER[:\s]+.*?([A-C])\b", response, re.DOTALL)
    if m:
        return m.group(1)
    m = re.findall(r"\b([A-C])\b", response)
    return m[-1] if m else None


# ── Internal Evaluator functions identical to mcq_eval ──

def log_none_answer(condition: str, turn: int, response: str) -> None:
    log_file = os.path.join(os.path.dirname(__file__), "failed_extractions.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}]\n{response}\n{'-'*40}\n")


def log_incorrect_answer(condition: str, turn: int, question: str, actual: str, expected: str, response: str) -> None:
    log_file = os.path.join(os.path.dirname(__file__), "incorrect_answers.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{condition} - Turn {turn}] LLM chose {actual}, Correct was {expected}\n")
        f.write(f"QUESTION: {question}\n")
        f.write(f"{response}\n{'-'*40}\n")


def _get_entities(turn: dict) -> list[str]:
    ents = turn.get("entities", "patient").split(", ")
    return [e.strip() for e in ents]


def _build_prompt(entities: list[str], new_beliefs_lines: list[str], beliefs_text: str | None, turn: dict) -> str:
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
    results = []
    initial_lines = [f"{k} = {v}" for k, v in INITIAL_BELIEFS.items()]

    for i, turn in enumerate(turns):
        store = BeliefStore()
        setup_alien_clinic_domain(store)
        
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

        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_prompt(entities, new_lines, beliefs_text, turn)
        
        response = llm.generate(EVAL_SYSTEM_PROMPT, full_prompt)
        res = _log_and_print("WITH STORE", i + 1, turn, response)
        results.append(res)
    return results


def run_with_store_with_history(llm: OllamaClient, turns: list[dict]) -> list[dict]:
    store = BeliefStore()
    setup_alien_clinic_domain(store)

    for k, v in INITIAL_BELIEFS.items():
        store.add_hypothesis(k, v)

    results = []
    messages = [{"role": "system", "content": EVAL_SYSTEM_PROMPT}]
    initial_lines = [f"{k} = {v}" for k, v in INITIAL_BELIEFS.items()]

    for i, turn in enumerate(turns):
        entities = _get_entities(turn)
        if turn["beliefs"]:
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)
        
        store.resolve_dirty(entities)
        beliefs_text, _ = store.to_prompt(entities)

        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_prompt(entities, new_lines, beliefs_text, turn)
        
        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        res = _log_and_print("WITH STORE (+History)", i + 1, turn, response)
        results.append(res)
    return results


def _build_baseline_prompt(entities: list[str], new_beliefs_lines: list[str], turn: dict) -> str:
    parts = [ALIEN_RULES]
    parts.append(f"[ENTITY]\n{', '.join(entities)}")

    if new_beliefs_lines:
        parts.append("[NEW BELIEF]\n" + "\n".join(new_beliefs_lines))

    q = turn["question"] + "\n\nChoose exactly one:\n"
    for letter, text in turn["options"].items():
        q += f"  {letter}) {text}\n"
    q += "\nRespond with REASONING then ANSWER: [Letter]"
    parts.append(f"[QUERY]\n{q}")

    return "\n\n".join(parts)


def run_without_store(llm: OllamaClient, turns: list[dict]) -> list[dict]:
    results = []
    messages = [{"role": "system", "content": BASELINE_SYSTEM_PROMPT}]
    initial_lines = [f"{k} = {v}" for k, v in INITIAL_BELIEFS.items()]

    for i, turn in enumerate(turns):
        entities = _get_entities(turn)
        new_lines = initial_lines if i == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
        full_prompt = _build_baseline_prompt(entities, new_lines, turn)

        messages.append({"role": "user", "content": full_prompt})
        response = llm.generate_with_history(messages)
        messages.append({"role": "assistant", "content": response})

        res = _log_and_print("NO STORE", i + 1, turn, response)
        results.append(res)
    return results


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

if __name__ == "__main__":
    main()
