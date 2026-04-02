"""
MCQ Evaluation — Alien Clinic (Zylosian Xenomedicine) Domain.

Defines the alien clinic scenario (initial beliefs, 10-turn MCQ, baseline rules)
and delegates all evaluation logic to eval_harness.

Usage:
    python3 evaluation/alien_mcq_eval.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.domains.alien_clinic import setup_alien_clinic_domain
from evaluation.eval_harness import DomainConfig, run_single_eval
from evaluation.scenarios import ALIEN_RULES, ALIEN_INITIAL_BELIEFS, ALIEN_TURNS


# ── Config factory ──────────────────────────────────────────────────

def get_config() -> DomainConfig:
    return DomainConfig(
        name="alien_clinic",
        setup_fn=setup_alien_clinic_domain,
        initial_beliefs=ALIEN_INITIAL_BELIEFS,
        turns=ALIEN_TURNS,
        baseline_rules=ALIEN_RULES,
        default_entities="patient",
    )


if __name__ == "__main__":
    run_single_eval(get_config())
