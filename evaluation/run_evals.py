"""
run_evals.py — Run any domain's MCQ evaluation N times and average the results.

Usage:
    python3 evaluation/run_evals.py                    # defaults to loan
    python3 evaluation/run_evals.py --domain loan
    python3 evaluation/run_evals.py --domain alien_clinic
    python3 evaluation/run_evals.py --domain alien_clinic_cf
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation.eval_harness import run_multi_eval, DomainConfig
from evaluation.scenarios import (
    LOAN_RULES, LOAN_INITIAL_BELIEFS, LOAN_TURNS,
    ALIEN_RULES, ALIEN_INITIAL_BELIEFS, ALIEN_TURNS_BASIC,
    ALIEN_INITIAL_BELIEFS_CF, ALIEN_TURNS_CF,
    CRIME_RULES, CRIME_INITIAL_BELIEFS, CRIME_TURNS
)
from belief_store.domains.loan import setup_loan_domain
from belief_store.domains.alien_clinic import setup_alien_clinic_domain
from belief_store.domains.crime_scene import setup_crime_scene_domain

DOMAIN_REGISTRY = {
    "loan": DomainConfig(
        name="loan",
        setup_fn=setup_loan_domain,
        initial_beliefs=LOAN_INITIAL_BELIEFS,
        turns=LOAN_TURNS,
        baseline_rules=LOAN_RULES,
        default_entities="applicant, loan",
    ),
    "alien_clinic": DomainConfig(
        name="alien_clinic",
        setup_fn=setup_alien_clinic_domain,
        initial_beliefs=ALIEN_INITIAL_BELIEFS,
        turns=ALIEN_TURNS_BASIC,
        baseline_rules=ALIEN_RULES,
        default_entities="patient",
    ),
    "alien_clinic_cf": DomainConfig(
        name="alien_clinic_cf",
        setup_fn=setup_alien_clinic_domain,
        initial_beliefs=ALIEN_INITIAL_BELIEFS_CF,
        turns=ALIEN_TURNS_CF,
        baseline_rules=ALIEN_RULES,
        default_entities="patient",
    ),
    "crime_scene": DomainConfig(
        name="crime_scene",
        setup_fn=setup_crime_scene_domain,
        initial_beliefs=CRIME_INITIAL_BELIEFS,
        turns=CRIME_TURNS,
        baseline_rules=CRIME_RULES,
        default_entities="case, suspect_a, suspect_b, officer_smith",
    ),
}

def main():
    parser = argparse.ArgumentParser(description="Run MCQ evaluations for a domain.")
    parser.add_argument(
        "--domain",
        choices=list(DOMAIN_REGISTRY.keys()),
        default="loan",
        help="Domain to evaluate (default: loan)",
    )
    parser.add_argument("--runs", type=int, default=10, help="Number of runs (default: 10)")
    parser.add_argument("--workers", type=int, default=4, help="Thread pool size (default: 4)")
    parser.add_argument("--model", default="gemma3:1b", help="Ollama model (default: gemma3:1b)")
    args = parser.parse_args()

    config = DOMAIN_REGISTRY[args.domain]
    print(f"Domain: {config.name} ({len(config.turns)} turns)\n")
    run_multi_eval(config, runs=args.runs, workers=args.workers, model=args.model)

if __name__ == "__main__":
    main()
