"""
Loan domain — deterministic derivation rules (R1–R6).

R2 is registered first because R1 and R3 depend on its output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from belief_store.store import BeliefStore


def setup_loan_domain(store: BeliefStore) -> None:
    """Register all loan-domain derivation rules on the given store."""

    store.add_rule(
        name="credit_score_effective",
        inputs=["applicant.credit_score", "applicant.co_signer"],
        output_key="loan.credit_score_effective",
        derive_fn=_credit_score_effective,
    )

    store.add_rule(
        name="applicant_prequalified",
        inputs=[
            "loan.adjusted_income",
            "loan.credit_score_effective",
            "applicant.debt_ratio",
            "applicant.employment_status",
            "applicant.bankruptcy_history",
            "applicant.employment_duration_months",
            "loan.min_income",
            "loan.min_credit",
            "loan.max_debt_ratio",
        ],
        output_key="loan.applicant_prequalified",
        derive_fn=_applicant_prequalified,
    )

    store.add_rule(
        name="rate_tier",
        inputs=["loan.applicant_prequalified", "loan.credit_score_effective"],
        output_key="loan.rate_tier",
        derive_fn=_rate_tier,
    )

    store.add_rule(
        name="max_amount",
        inputs=["loan.applicant_prequalified", "applicant.has_collateral"],
        output_key="loan.max_amount",
        derive_fn=_max_amount,
    )

    store.add_rule(
        name="application_status",
        inputs=[
            "loan.applicant_prequalified",
            "applicant.loan_amount_requested",
            "loan.max_amount",
        ],
        output_key="loan.application_status",
        derive_fn=_application_status,
    )

    store.add_rule(
        name="high_risk_flag",
        inputs=["applicant.debt_ratio"],
        output_key="loan.high_risk_flag",
        derive_fn=_high_risk_flag,
    )

    store.add_rule(
        name="adjusted_income",
        inputs=["applicant.income", "applicant.dependents"],
        output_key="loan.adjusted_income",
        derive_fn=_adjusted_income,
    )

    store.add_rule(
        name="requires_insurance",
        inputs=["loan.high_risk_flag", "loan.application_status"],
        output_key="loan.requires_insurance",
        derive_fn=_requires_insurance,
    )

    store.add_rule(
        name="review_queue",
        inputs=["loan.application_status", "loan.high_risk_flag"],
        output_key="loan.review_queue",
        derive_fn=_review_queue,
    )

    store.add_rule(
        name="base_interest_rate",
        inputs=["loan.rate_tier", "loan.requires_insurance"],
        output_key="loan.base_interest_rate",
        derive_fn=_base_interest_rate,
    )


def _credit_score_effective(inputs: dict[str, Any]) -> int:
    score = inputs["applicant.credit_score"]
    return score + 50 if inputs["applicant.co_signer"] else score


def _applicant_prequalified(inputs: dict[str, Any]) -> bool:
    if inputs["applicant.employment_status"] == "unemployed":
        return False
    if (
        inputs["applicant.bankruptcy_history"] is True
        and inputs["applicant.employment_duration_months"] < 24
    ):
        return False
    return (
        inputs["loan.adjusted_income"] >= inputs["loan.min_income"]
        and inputs["loan.credit_score_effective"] >= inputs["loan.min_credit"]
        and inputs["applicant.debt_ratio"] < inputs["loan.max_debt_ratio"]
    )


def _rate_tier(inputs: dict[str, Any]) -> str | None:
    if not inputs["loan.applicant_prequalified"]:
        return None
    return "preferred" if inputs["loan.credit_score_effective"] >= 750 else "standard"


def _max_amount(inputs: dict[str, Any]) -> int:
    if not inputs["loan.applicant_prequalified"]:
        return 0
    return 100_000 if inputs["applicant.has_collateral"] else 30_000


def _application_status(inputs: dict[str, Any]) -> str:
    if not inputs["loan.applicant_prequalified"]:
        return "denied_ineligible"
    if inputs["applicant.loan_amount_requested"] > inputs["loan.max_amount"]:
        return "denied_amount_exceeded"
    return "approved"


def _high_risk_flag(inputs: dict[str, Any]) -> bool:
    return inputs["applicant.debt_ratio"] >= 0.3


def _adjusted_income(inputs: dict[str, Any]) -> float:
    return inputs["applicant.income"] - (inputs.get("applicant.dependents", 0) * 500)


def _requires_insurance(inputs: dict[str, Any]) -> bool:
    return bool(inputs["loan.high_risk_flag"] and inputs["loan.application_status"] == "approved")


def _review_queue(inputs: dict[str, Any]) -> str:
    if inputs["loan.application_status"] == "approved":
        return "manual_review" if inputs["loan.high_risk_flag"] else "auto_approve"
    return "rejected"


def _base_interest_rate(inputs: dict[str, Any]) -> float | None:
    tier = inputs.get("loan.rate_tier")
    if tier is None:
        return None
    base = 4.5 if tier == "preferred" else 6.5
    return base + 1.0 if inputs.get("loan.requires_insurance") else base
