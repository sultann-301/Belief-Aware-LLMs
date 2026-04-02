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

ALIEN_RULES = """\
[RULES]
1. patient.organ_integrity = "volatile" if ambient_pressure > 5.0 and organism_type == "Yorp". "volatile" if ambient_pressure > 4.0 and organism_type == "Glerps". "brittle" if ambient_pressure > 3.0. Otherwise "stable".
2. zyxostin.phase = "plasma" IF dominant_gas == "methane" ELSE "crystalline". filinan.phase = "vapor" IF dominant_gas == "xenon" ELSE "plasma". snevox.phase = "liquid" IF dominant_gas == "chlorine" ELSE "vapor".
3. hazards: If organism_type + compound has explode constraint (Glerps+zyxostin, Yorp+filinan, Qwerl+snevox), then if organ_integrity is "volatile", hazard is "symbiotic" (Biological Singularity). Else hazard is "LETHAL". If phase="plasma" and filinan -> "LETHAL". If phase="vapor" and snevox and Qwerl -> "LETHAL". If organ_integrity="volatile" -> "LETHAL". Else "safe".
4. treatment.active_prescription = MIRACLE OVERRIDE: If any hazard is "symbiotic", pick it immediately ignoring priority. SYMPTOM PRIORITIES: Glerps: if "fever" and "spasms" in symptoms (snevox -> zyxostin -> filinan), if "fever" in symptoms (zyxostin -> snevox -> filinan), else (filinan -> zyxostin -> snevox). Yorp: if "acid_sweat" in symptoms (filinan -> snevox -> zyxostin), else (zyxostin -> snevox -> filinan). Qwerl: (snevox -> zyxostin -> filinan). Select highest priority safe. Else none.
5. patient.sensory_status = "telepathic" if active_prescription == "snevox", else "normal".
6. patient.quarantine_required = True if (dominant_gas == "chlorine" AND organism_type == "Qwerl") or (dominant_gas == "methane" AND organism_type == "Yorp"), else False.
7. treatment.duration_cycles = 12 if active_prescription == "snevox" and organ_integrity == "volatile". 0 if active_prescription == "none". Otherwise 5.
8. medical.staff_requirement = "hazmat_team" if quarantine_required == True. "psionic_handler" if sensory_status == "telepathic". Else "standard_medic". (Quarantine overrides Psionic).
9. patient.recovery_prospect = "miraculous" if hazard is "symbiotic". "guarded" if duration_cycles > 10 and staff_requirement == "hazmat_team". "terminal" if duration_cycles == 0. Else "excellent".
10. clinic.billing_tier = "class_omega" if staff_requirement == "psionic_handler" or active_prescription == "snevox". "class_delta" if staff_requirement == "hazmat_team". Otherwise "class_standard".
"""

INITIAL_BELIEFS = {
    "patient.organism_type": "Glerps",
    "patient.symptoms": [],
    "atmosphere.ambient_pressure": 3.5,
    "atmosphere.dominant_gas": "methane",
}

TURNS = [
    {
        "entities": "treatment, clinic",
        "beliefs": {},
        "question": "What is the active prescription and billing tier?",
        "options": {
            "A": "snevox, class_omega",        
            "B": "filinan, class_standard",    
            "C": "none, class_omega",          
        },
        "correct": "A",
    },
    {
        "entities": "treatment, clinic",
        "beliefs": {"patient.symptoms": ["fever", "spasms"]},
        "question": "What is the new active prescription and billing tier?",
        "options": {
            "A": "snevox, class_omega",               
            "B": "zyxostin, class_standard",                
            "C": "none, class_standard",                
        },
        "correct": "A",
    },
    {
        "entities": "treatment, clinic",
        "beliefs": {"patient.symptoms": ["fever"]},
        "question": "What is the active prescription?",
        "options": {
            "A": "snevox",  
            "B": "zyxostin",        
            "C": "filinan",    
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "zyxostin, miraculous",      
            "B": "none, terminal",          
            "C": "snevox, excellent",    
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.symptoms": []},
        "question": "What is the recovery prospect?",
        "options": {
            "A": "miraculous",           
            "B": "excellent",     
            "C": "terminal",       
        },
        "correct": "A",
    },
    {
        "entities": "treatment, medical",
        "beliefs": {"patient.organism_type": "Yorp"},
        "question": "What is the active prescription and staff requirement?",
        "options": {
            "A": "none, hazmat_team",
            "B": "zyxostin, hazmat_team",                
            "C": "zyxostin, standard_medic",                    
        },
        "correct": "B",
    },
    {
        "entities": "treatment, medical",
        "beliefs": {"patient.symptoms": ["acid_sweat"]},
        "question": "What is the new prescription and staff requirement?",
        "options": {
            "A": "snevox, hazmat_team",           
            "B": "snevox, psionic_handler",              
            "C": "filinan, hazmat_team",                
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 5.5},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "none, terminal",                     
            "B": "filinan, miraculous",                  
            "C": "snevox, terminal",                   
        },
        "correct": "B",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "filinan, miraculous",                     
            "B": "zyxostin, excellent",                    
            "C": "snevox, guarded",                 
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.organism_type": "Qwerl"},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "zyxostin, excellent",
            "B": "filinan, miraculous",                            
            "C": "none, terminal",                             
        },
        "correct": "A",
    },
]


def extract_answer(response: str) -> str | None:
    m = re.search(r"ANSWER[:\s]+.*?([A-C])\b", response, re.DOTALL)
    if m:
        return m.group(1)
    m = re.findall(r"\b([A-C])\b", response)
    return m[-1] if m else None


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
    print("Connecting to Ollama (gemma3:1b)...")
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
