"""
Loan domain — deterministic derivation rules for loan eligibility.

Registers six rules matching the domains.md spec (R1–R6):
  R2: credit_score_effective  (co-signer boost)
  R1: eligible                (unemployment, bankruptcy, threshold checks)
  R3: rate_tier               (preferred vs. standard)
  R4: max_amount              (collateral gate)
  R5: application_status      (final decision)
  R6: high_risk_flag          (debt ratio warning)

R2 is registered first because R1 and R3 depend on its output
(loan.credit_score_effective).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from belief_store.store import BeliefStore


def setup_loan_domain(store: BeliefStore) -> None:
    """Register all loan-domain derivation rules on the given store."""

    # ── R2: Credit score effective (must come before R1 & R3) ────────
    store.add_rule(
        name="credit_score_effective",
        inputs=["applicant.credit_score", "applicant.co_signer"],
        output_key="loan.credit_score_effective",
        derive_fn=_credit_score_effective,
    )

    # ── R1: Loan eligibility ─────────────────────────────────────────
    store.add_rule(
        name="eligible",
        inputs=[
            "applicant.income",
            "loan.credit_score_effective",
            "applicant.debt_ratio",
            "applicant.employment_status",
            "applicant.bankruptcy_history",
            "applicant.employment_duration_months",
            "loan.min_income",
            "loan.min_credit",
            "loan.max_debt_ratio",
        ],
        output_key="loan.eligible",
        derive_fn=_eligible,
    )

    # ── R3: Rate tier ────────────────────────────────────────────────
    store.add_rule(
        name="rate_tier",
        inputs=["loan.eligible", "loan.credit_score_effective"],
        output_key="loan.rate_tier",
        derive_fn=_rate_tier,
    )

    # ── R4: Max loan amount ──────────────────────────────────────────
    store.add_rule(
        name="max_amount",
        inputs=["loan.eligible", "applicant.has_collateral"],
        output_key="loan.max_amount",
        derive_fn=_max_amount,
    )

    # ── R5: Application status ───────────────────────────────────────
    store.add_rule(
        name="application_status",
        inputs=[
            "loan.eligible",
            "applicant.loan_amount_requested",
            "loan.max_amount",
        ],
        output_key="loan.application_status",
        derive_fn=_application_status,
    )

    # ── R6: High risk flag ───────────────────────────────────────────
    store.add_rule(
        name="high_risk_flag",
        inputs=["applicant.debt_ratio"],
        output_key="loan.high_risk_flag",
        derive_fn=_high_risk_flag,
    )


# ── Private derive functions ─────────────────────────────────────────


def _credit_score_effective(inputs: dict[str, Any]) -> int:
    """R2: credit_score + 50 if co_signer, else credit_score."""
    score = inputs["applicant.credit_score"]
    co_signer = inputs["applicant.co_signer"]
    return score + 50 if co_signer else score


def _eligible(inputs: dict[str, Any]) -> bool:
    """R1: Multi-condition eligibility check."""
    if inputs["applicant.employment_status"] == "unemployed":
        return False

    if (
        inputs["applicant.bankruptcy_history"] is True
        and inputs["applicant.employment_duration_months"] < 24
    ):
        return False

    return (
        inputs["applicant.income"] >= inputs["loan.min_income"]
        and inputs["loan.credit_score_effective"] >= inputs["loan.min_credit"]
        and inputs["applicant.debt_ratio"] < inputs["loan.max_debt_ratio"]
    )


def _rate_tier(inputs: dict[str, Any]) -> str | None:
    """R3: Preferred if effective score >= 750, else standard."""
    if not inputs["loan.eligible"]:
        return None
    return (
        "preferred"
        if inputs["loan.credit_score_effective"] >= 750
        else "standard"
    )


def _max_amount(inputs: dict[str, Any]) -> int:
    """R4: Collateral gate for max loan amount."""
    if not inputs["loan.eligible"]:
        return 0
    return 100_000 if inputs["applicant.has_collateral"] else 30_000


def _application_status(inputs: dict[str, Any]) -> str:
    """R5: Final application decision."""
    if not inputs["loan.eligible"]:
        return "denied_ineligible"
    if inputs["applicant.loan_amount_requested"] > inputs["loan.max_amount"]:
        return "denied_amount_exceeded"
    return "approved"


def _high_risk_flag(inputs: dict[str, Any]) -> bool:
    """R6: Debt ratio warning."""
    return inputs["applicant.debt_ratio"] >= 0.3
