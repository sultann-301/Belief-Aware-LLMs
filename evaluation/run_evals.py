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
    CRIME_RULES, CRIME_INITIAL_BELIEFS, CRIME_TURNS,
    THORNCRESTER_RULES, THORNCRESTER_INITIAL_BELIEFS, THORNCRESTER_TURNS
)
from belief_store.domains.loan import setup_loan_domain
from belief_store.domains.alien_clinic import setup_alien_clinic_domain
from belief_store.domains.crime_scene import setup_crime_scene_domain
from belief_store.domains.thorncrester import setup_thorncrester_domain

from evaluation.loan_extended_scenarios import (
    LOAN_NEGATION_TURNS, LOAN_1HOP_TURNS, LOAN_2HOP_TURNS, LOAN_3HOP_TURNS, LOAN_4HOP_TURNS, LOAN_BELIEF_MAINTENANCE_TURNS
)
from evaluation.alien_clinic_extended_scenarios import (
    ALIEN_NEGATION_TURNS, ALIEN_1HOP_TURNS, ALIEN_2HOP_TURNS, ALIEN_3HOP_TURNS, ALIEN_4HOP_TURNS, ALIEN_BELIEF_MAINTENANCE_TURNS
)
from evaluation.crime_scene_extended_scenarios import (
    CRIME_NEGATION_TURNS, CRIME_1HOP_TURNS, CRIME_2HOP_TURNS, CRIME_3HOP_TURNS, CRIME_4HOP_TURNS, CRIME_BELIEF_MAINTENANCE_TURNS
)
from evaluation.thorncrester_extended_scenarios import (
    THORNCRESTER_NEGATION_TURNS, THORNCRESTER_1HOP_TURNS, THORNCRESTER_2HOP_TURNS, THORNCRESTER_3HOP_TURNS, THORNCRESTER_4HOP_TURNS, THORNCRESTER_BELIEF_MAINTENANCE_TURNS
)

LOAN_EXTENDED_TURNS = LOAN_NEGATION_TURNS + LOAN_1HOP_TURNS + LOAN_2HOP_TURNS + LOAN_3HOP_TURNS + LOAN_4HOP_TURNS + LOAN_BELIEF_MAINTENANCE_TURNS
ALIEN_EXTENDED_TURNS = ALIEN_NEGATION_TURNS + ALIEN_1HOP_TURNS + ALIEN_2HOP_TURNS + ALIEN_3HOP_TURNS + ALIEN_4HOP_TURNS + ALIEN_BELIEF_MAINTENANCE_TURNS
CRIME_EXTENDED_TURNS = CRIME_NEGATION_TURNS + CRIME_1HOP_TURNS + CRIME_2HOP_TURNS + CRIME_3HOP_TURNS + CRIME_4HOP_TURNS + CRIME_BELIEF_MAINTENANCE_TURNS
THORNCRESTER_EXTENDED_TURNS = THORNCRESTER_NEGATION_TURNS + THORNCRESTER_1HOP_TURNS + THORNCRESTER_2HOP_TURNS + THORNCRESTER_3HOP_TURNS + THORNCRESTER_4HOP_TURNS + THORNCRESTER_BELIEF_MAINTENANCE_TURNS

DOMAIN_REGISTRY = {
    "loan": DomainConfig(
        name="loan",
        setup_fn=setup_loan_domain,
        initial_beliefs=LOAN_INITIAL_BELIEFS,
        turns=LOAN_TURNS,
        baseline_rules=LOAN_RULES,
        default_entities="applicant, loan",
    ),
    "loan_extended": DomainConfig(
        name="loan_extended",
        setup_fn=setup_loan_domain,
        initial_beliefs=LOAN_INITIAL_BELIEFS,
        turns=LOAN_EXTENDED_TURNS,
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
    "alien_clinic_extended": DomainConfig(
        name="alien_clinic_extended",
        setup_fn=setup_alien_clinic_domain,
        initial_beliefs=ALIEN_INITIAL_BELIEFS,
        turns=ALIEN_EXTENDED_TURNS,
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
    "crime_scene_extended": DomainConfig(
        name="crime_scene_extended",
        setup_fn=setup_crime_scene_domain,
        initial_beliefs=CRIME_INITIAL_BELIEFS,
        turns=CRIME_EXTENDED_TURNS,
        baseline_rules=CRIME_RULES,
        default_entities="case, suspect_a, suspect_b, officer_smith",
    ),
    "thorncrester": DomainConfig(
        name="thorncrester",
        setup_fn=setup_thorncrester_domain,
        initial_beliefs=THORNCRESTER_INITIAL_BELIEFS,
        turns=THORNCRESTER_TURNS,
        baseline_rules=THORNCRESTER_RULES,
        default_entities="environment, adult_thorncrester, thorncrester_flock, juvenile_thorncrester, feather_mite",
    ),
    "thorncrester_extended": DomainConfig(
        name="thorncrester_extended",
        setup_fn=setup_thorncrester_domain,
        initial_beliefs=THORNCRESTER_INITIAL_BELIEFS,
        turns=THORNCRESTER_EXTENDED_TURNS,
        baseline_rules=THORNCRESTER_RULES,
        default_entities="environment, adult_thorncrester, thorncrester_flock, juvenile_thorncrester, feather_mite",
    ),
}

# --- Add Isolated Subsets ---
_SUBSET_MAP = {
    "loan": {
        "setup_fn": setup_loan_domain,
        "initial_beliefs": LOAN_INITIAL_BELIEFS,
        "baseline_rules": LOAN_RULES,
        "default_entities": "applicant, loan",
        "subsets": {
            "negation": LOAN_NEGATION_TURNS,
            "1hop": LOAN_1HOP_TURNS,
            "2hop": LOAN_2HOP_TURNS,
            "3hop": LOAN_3HOP_TURNS,
            "4hop": LOAN_4HOP_TURNS,
            "belief_maintenance": LOAN_BELIEF_MAINTENANCE_TURNS,
        }
    },
    "alien_clinic": {
        "setup_fn": setup_alien_clinic_domain,
        "initial_beliefs": ALIEN_INITIAL_BELIEFS,
        "baseline_rules": ALIEN_RULES,
        "default_entities": "patient",
        "subsets": {
            "negation": ALIEN_NEGATION_TURNS,
            "1hop": ALIEN_1HOP_TURNS,
            "2hop": ALIEN_2HOP_TURNS,
            "3hop": ALIEN_3HOP_TURNS,
            "4hop": ALIEN_4HOP_TURNS,
            "belief_maintenance": ALIEN_BELIEF_MAINTENANCE_TURNS,
        }
    },
    "crime_scene": {
        "setup_fn": setup_crime_scene_domain,
        "initial_beliefs": CRIME_INITIAL_BELIEFS,
        "baseline_rules": CRIME_RULES,
        "default_entities": "case, suspect_a, suspect_b, officer_smith",
        "subsets": {
            "negation": CRIME_NEGATION_TURNS,
            "1hop": CRIME_1HOP_TURNS,
            "2hop": CRIME_2HOP_TURNS,
            "3hop": CRIME_3HOP_TURNS,
            "4hop": CRIME_4HOP_TURNS,
            "belief_maintenance": CRIME_BELIEF_MAINTENANCE_TURNS,
        }
    },
    "thorncrester": {
        "setup_fn": setup_thorncrester_domain,
        "initial_beliefs": THORNCRESTER_INITIAL_BELIEFS,
        "baseline_rules": THORNCRESTER_RULES,
        "default_entities": "environment, adult_thorncrester, thorncrester_flock, juvenile_thorncrester, feather_mite",
        "subsets": {
            "negation": THORNCRESTER_NEGATION_TURNS,
            "1hop": THORNCRESTER_1HOP_TURNS,
            "2hop": THORNCRESTER_2HOP_TURNS,
            "3hop": THORNCRESTER_3HOP_TURNS,
            "4hop": THORNCRESTER_4HOP_TURNS,
            "belief_maintenance": THORNCRESTER_BELIEF_MAINTENANCE_TURNS,
        }
    }
}

for base_name, config_data in _SUBSET_MAP.items():
    for subset_name, turns in config_data["subsets"].items():
        full_name = f"{base_name}_{subset_name}"
        DOMAIN_REGISTRY[full_name] = DomainConfig(
            name=full_name,
            setup_fn=config_data["setup_fn"],
            initial_beliefs=config_data["initial_beliefs"],
            turns=turns,
            baseline_rules=config_data["baseline_rules"],
            default_entities=config_data["default_entities"],
        )

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
