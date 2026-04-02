"""
run_evals.py — Run any domain's MCQ evaluation N times and average the results.

Usage:
    python3 evaluation/run_evals.py                    # defaults to loan
    python3 evaluation/run_evals.py --domain loan
    python3 evaluation/run_evals.py --domain alien_clinic
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation.eval_harness import run_multi_eval


DOMAIN_REGISTRY = {
    "loan": "evaluation.mcq_eval",
    "alien_clinic": "evaluation.alien_mcq_eval",
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

    # Dynamically import the selected domain module and get its config
    import importlib
    module = importlib.import_module(DOMAIN_REGISTRY[args.domain])
    config = module.get_config()

    print(f"Domain: {config.name} ({len(config.turns)} turns)\n")
    run_multi_eval(config, runs=args.runs, workers=args.workers, model=args.model)


if __name__ == "__main__":
    main()
