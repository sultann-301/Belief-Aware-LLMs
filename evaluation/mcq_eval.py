"""
MCQ Evaluation — Loan Domain.

Defines the loan-domain scenario (initial beliefs, 10-turn MCQ, baseline rules)
and delegates all evaluation logic to eval_harness.

Usage:
    python3 evaluation/mcq_eval.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.domains.loan import setup_loan_domain
from evaluation.eval_harness import DomainConfig, run_single_eval
from evaluation.scenarios import LOAN_RULES, LOAN_INITIAL_BELIEFS, LOAN_TURNS


# ── Config factory ──────────────────────────────────────────────────

def get_config() -> DomainConfig:
    return DomainConfig(
        name="loan",
        setup_fn=setup_loan_domain,
        initial_beliefs=LOAN_INITIAL_BELIEFS,
        turns=LOAN_TURNS,
        baseline_rules=LOAN_RULES,
        default_entities="applicant, loan",
    )


if __name__ == "__main__":
    run_single_eval(get_config())
