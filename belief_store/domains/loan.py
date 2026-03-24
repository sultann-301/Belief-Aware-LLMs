"""
Loan domain — deterministic derivation rules for loan eligibility.

Registers four rules matching the spec:
  1. income_check:    income >= min_income → income_eligible
  2. credit_check:    credit >= min_credit → credit_eligible
  3. loan_decision:   both eligible → "approved", else "rejected"
  4. rejection_reason: None if approved, else which check failed
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from belief_store.store import BeliefStore


def setup_loan_domain(store: BeliefStore) -> None:
    """Register all loan-domain derivation rules on the given store."""

    # 1. Income eligibility
    store.add_rule(
        name="income_check",
        inputs=["applicant.income", "loan.min_income"],
        output_key="loan.income_eligible",
        derive_fn=lambda inputs: (
            inputs["applicant.income"] >= inputs["loan.min_income"]
        ),
    )

    # 2. Credit eligibility
    store.add_rule(
        name="credit_check",
        inputs=["applicant.credit_score", "loan.min_credit"],
        output_key="loan.credit_eligible",
        derive_fn=lambda inputs: (
            inputs["applicant.credit_score"] >= inputs["loan.min_credit"]
        ),
    )

    # 3. Loan decision
    store.add_rule(
        name="loan_decision",
        inputs=["loan.income_eligible", "loan.credit_eligible"],
        output_key="loan.status",
        derive_fn=lambda inputs: (
            "approved"
            if inputs["loan.income_eligible"] and inputs["loan.credit_eligible"]
            else "rejected"
        ),
    )

    # 4. Rejection reason
    store.add_rule(
        name="rejection_reason",
        inputs=["loan.income_eligible", "loan.credit_eligible"],
        output_key="loan.rejection_reason",
        derive_fn=lambda inputs: _rejection_reason(inputs),
    )


def _rejection_reason(inputs: dict) -> str | None:
    """Determine rejection reason, or None if approved."""
    income_ok = inputs["loan.income_eligible"]
    credit_ok = inputs["loan.credit_eligible"]

    if income_ok and credit_ok:
        return None

    reasons = []
    if not income_ok:
        reasons.append("income below minimum")
    if not credit_ok:
        reasons.append("credit score below minimum")

    return ", ".join(reasons)
