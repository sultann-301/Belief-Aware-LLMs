"""run_evals.py — CLI for running MCQ evaluations across domains and scenarios.

Supports:
  - Full domains (basic 5-turn scenarios)
  - Extended domains (60 turns: negation, 1-hop, 2-hop, 3-hop, 4-hop, belief_maintenance)
  - Individual scenario subsets (e.g., loan_negation for just negation questions)

Architecture:
  - _SUBSET_MAP: Defines each domain's config and all its scenario sets
  - auto-generates extended turn arrays and subset configurations
"""

import argparse
from sys import path
from os.path import join, dirname

path.insert(0, join(dirname(__file__), ".."))

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
    LOAN_NEGATION_TURNS, LOAN_1HOP_TURNS, LOAN_2HOP_TURNS, LOAN_3HOP_TURNS,
    LOAN_4HOP_TURNS, LOAN_BELIEF_MAINTENANCE_TURNS
)
from evaluation.alien_clinic_extended_scenarios import (
    ALIEN_NEGATION_TURNS, ALIEN_1HOP_TURNS, ALIEN_2HOP_TURNS, ALIEN_3HOP_TURNS,
    ALIEN_4HOP_TURNS, ALIEN_BELIEF_MAINTENANCE_TURNS
)
from evaluation.crime_scene_extended_scenarios import (
    CRIME_NEGATION_TURNS, CRIME_1HOP_TURNS, CRIME_2HOP_TURNS, CRIME_3HOP_TURNS,
    CRIME_4HOP_TURNS, CRIME_BELIEF_MAINTENANCE_TURNS
)
from evaluation.thorncrester_extended_scenarios import (
    THORNCRESTER_NEGATION_TURNS, THORNCRESTER_1HOP_TURNS, THORNCRESTER_2HOP_TURNS,
    THORNCRESTER_3HOP_TURNS, THORNCRESTER_4HOP_TURNS, THORNCRESTER_BELIEF_MAINTENANCE_TURNS
)
from evaluation.belief_awareness_scenarios import (
    LOAN_COUNTERFACTUAL_TURNS, LOAN_GROUNDING_TURNS,
    ALIEN_COUNTERFACTUAL_TURNS, ALIEN_GROUNDING_TURNS,
    CRIME_COUNTERFACTUAL_TURNS, CRIME_GROUNDING_TURNS,
    THORNCRESTER_COUNTERFACTUAL_TURNS, THORNCRESTER_GROUNDING_TURNS,
)
from evaluation.prompting import get_eval_prompt_version

# ────────────────────────────────────────────────────────────────────
# Domain Configuration Map
# ────────────────────────────────────────────────────────────────────
# Each domain maps to:
#   - setup_fn: Registers rules in BeliefStore
#   - initial_beliefs: Starting state for all evaluations
#   - baseline_rules: Text rules for NO STORE condition
#   - default_entities: Fallback for entity-level filtering
#   - subsets: Named scenario groups (negation, 1hop, 2hop, etc.)

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

# ────────────────────────────────────────────────────────────────────
# Build Evaluation Registry
# ────────────────────────────────────────────────────────────────────

DOMAIN_REGISTRY = {}

# Map of base domain names to their basic turns
_BASIC_TURNS_MAP = {
    "loan": LOAN_TURNS,
    "alien_clinic": ALIEN_TURNS_BASIC,
    "crime_scene": CRIME_TURNS,
    "thorncrester": THORNCRESTER_TURNS,
}

for domain_name, domain_config in _SUBSET_MAP.items():
    # Full basic domain (5 turns)
    DOMAIN_REGISTRY[domain_name] = DomainConfig(
        name=domain_name,
        setup_fn=domain_config["setup_fn"],
        initial_beliefs=domain_config["initial_beliefs"],
        turns=_BASIC_TURNS_MAP[domain_name],
        baseline_rules=domain_config["baseline_rules"],
        default_entities=domain_config["default_entities"],
    )

    # Extended domain (concatenate all subsets: 60 turns)
    extended_turns = sum(
        (turns for turns in domain_config["subsets"].values()),
        []  # start with empty list
    )
    DOMAIN_REGISTRY[f"{domain_name}_extended"] = DomainConfig(
        name=f"{domain_name}_extended",
        setup_fn=domain_config["setup_fn"],
        initial_beliefs=domain_config["initial_beliefs"],
        turns=extended_turns,
        baseline_rules=domain_config["baseline_rules"],
        default_entities=domain_config["default_entities"],
        is_conversational=False,
        accumulate_prior_beliefs=True,
    )

    # Individual subsets (e.g., loan_negation, loan_1hop, etc.)
    for subset_name, turns in domain_config["subsets"].items():
        full_name = f"{domain_name}_{subset_name}"
        DOMAIN_REGISTRY[full_name] = DomainConfig(
            name=full_name,
            setup_fn=domain_config["setup_fn"],
            initial_beliefs=domain_config["initial_beliefs"],
            turns=turns,
            baseline_rules=domain_config["baseline_rules"],
            default_entities=domain_config["default_entities"],
            is_conversational=False,
            # NOTE: belief_maintenance tests accumulation + retrieval of old beliefs
            # Beliefs accumulate, but queries ask about UNAFFECTED attributes
            accumulate_prior_beliefs=(subset_name == "belief_maintenance"),
        )

# Special alternate belief state for alien_clinic counterfactual
DOMAIN_REGISTRY["alien_clinic_cf"] = DomainConfig(
    name="alien_clinic_cf",
    setup_fn=setup_alien_clinic_domain,
    initial_beliefs=ALIEN_INITIAL_BELIEFS_CF,
    turns=ALIEN_TURNS_CF,
    baseline_rules=ALIEN_RULES,
    default_entities="patient",
)

# ────────────────────────────────────────────────────────────────────
# Belief-Awareness Evaluation Configs
# ────────────────────────────────────────────────────────────────────
# Two dimensions: counterfactual (prior suppression) and grounding
# (hallucination resistance).  Non-conversational, no accumulation.

_BELIEF_AWARENESS_MAP = {
    "loan": {
        "counterfactual": LOAN_COUNTERFACTUAL_TURNS,
        "grounding": LOAN_GROUNDING_TURNS,
    },
    "alien_clinic": {
        "counterfactual": ALIEN_COUNTERFACTUAL_TURNS,
        "grounding": ALIEN_GROUNDING_TURNS,
    },
    "crime_scene": {
        "counterfactual": CRIME_COUNTERFACTUAL_TURNS,
        "grounding": CRIME_GROUNDING_TURNS,
    },
    "thorncrester": {
        "counterfactual": THORNCRESTER_COUNTERFACTUAL_TURNS,
        "grounding": THORNCRESTER_GROUNDING_TURNS,
    },
}

for domain_name, ba_subsets in _BELIEF_AWARENESS_MAP.items():
    domain_config = _SUBSET_MAP[domain_name]

    # Individual subsets: e.g. loan_counterfactual, loan_grounding
    for subset_name, turns in ba_subsets.items():
        full_name = f"{domain_name}_{subset_name}"
        DOMAIN_REGISTRY[full_name] = DomainConfig(
            name=full_name,
            setup_fn=domain_config["setup_fn"],
            initial_beliefs=domain_config["initial_beliefs"],
            turns=turns,
            baseline_rules=domain_config["baseline_rules"],
            default_entities=domain_config["default_entities"],
            is_conversational=False,
            accumulate_prior_beliefs=False,
        )

    # Combined: e.g. loan_belief_awareness (20 turns)
    combined_name = f"{domain_name}_belief_awareness"
    combined_turns = ba_subsets["counterfactual"] + ba_subsets["grounding"]
    DOMAIN_REGISTRY[combined_name] = DomainConfig(
        name=combined_name,
        setup_fn=domain_config["setup_fn"],
        initial_beliefs=domain_config["initial_beliefs"],
        turns=combined_turns,
        baseline_rules=domain_config["baseline_rules"],
        default_entities=domain_config["default_entities"],
        is_conversational=False,
        accumulate_prior_beliefs=False,
    )


# ────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run MCQ evaluations across domains and scenario types.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python3 evaluation/run_evals.py --domain loan
    → Run full loan domain (5 turns)

  python3 evaluation/run_evals.py --domain loan_extended
    → Run extended loan evaluation (60 turns: all scenario types)

  python3 evaluation/run_evals.py --domain loan_negation --runs 20
    → Run just negation questions (10 turns) for 20 iterations

  python3 evaluation/run_evals.py --domain crime_scene_2hop --model llama2
    → Run crime scene 2-hop scenarios with a different model
        """
    )

    parser.add_argument(
        "--domain",
        choices=sorted(DOMAIN_REGISTRY.keys()),
        default="loan",
        help="Domain or scenario subset to evaluate (default: loan)"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of evaluation runs (default: 10)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel worker threads (default: 4)"
    )
    parser.add_argument(
        "--model",
        default="gemma3:1b",
        help="Ollama model name (default: gemma3:1b)"
    )
    parser.add_argument(
        "--eval-prompt-version",
        default=None,
        help=(
            "Base belief-store prompt profile for WITH STORE evals "
            "(e.g., v5, v12). Defaults to EVAL_BASE_PROMPT_VERSION or v5."
        ),
    )

    args = parser.parse_args()

    config = DOMAIN_REGISTRY[args.domain]
    if args.eval_prompt_version:
        config.eval_prompt_version = args.eval_prompt_version
    resolved_eval_prompt_version = get_eval_prompt_version(config.eval_prompt_version)
    print(f"\n{'='*75}")
    print(f"Domain: {config.name} ({len(config.turns)} turns)")
    print(
        f"Model: {args.model} | Runs: {args.runs} | Workers: {args.workers} "
        f"| Eval Prompt: {resolved_eval_prompt_version}"
    )
    print(f"{'='*75}\n")

    run_multi_eval(
        config,
        runs=args.runs,
        workers=args.workers,
        model=args.model
    )


if __name__ == "__main__":
    main()
