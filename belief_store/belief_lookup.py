"""Lookup of brief descriptions for belief keys.

Keep compact, neutral descriptions that explain the relationship or role
of each attribute. `BELIEF_DESCRIPTIONS` is imported by `store.to_prompt`
to inject inline hints for the LLM when serializing beliefs.
"""
from __future__ import annotations

from typing import Dict

# Semantic descriptions for derived keys only.
BELIEF_DESCRIPTIONS: Dict[str, str] = {
    # Loan domain
    "loan.adjusted_income": "income after dependents deduction",
    "loan.credit_score_effective": "credit score after co-signer boost",
    "loan.applicant_prequalified": "meets income/credit/debt/employment gates",
    "loan.rate_tier": "rate category from eligibility + credit",
    "loan.max_amount": "maximum loan cap from eligibility + collateral",
    "loan.application_status": "approval/denial from eligibility + amount",
    "loan.high_risk_flag": "high-risk flag from debt ratio",
    "loan.requires_insurance": "insurance required for approved high-risk",
    "loan.review_queue": "review queue from status + risk",
    "loan.base_interest_rate": "base rate from tier + insurance",

    # Alien clinic
    "patient.organ_integrity": "organ stability from pressure + species",
    "treatment.zyxostin_phase": "zyxostin compound phase from atmosphere",
    "treatment.filinan_phase": "filinan compound phase from atmosphere",
    "treatment.snevox_phase": "snevox compound phase from atmosphere",
    "treatment.zyxostin_danger_level": "zyxostin danger level for patient",
    "treatment.filinan_danger_level": "filinan danger level for patient",
    "treatment.snevox_danger_level": "snevox danger level for patient",
    "treatment.active_prescription": "selected compound from symptoms + safety",
    "patient.sensory_status": "sensory side-effect from prescription",
    "patient.quarantine_required": "quarantine required from atmosphere + species",
    "treatment.duration_cycles": "treatment length from prescription + integrity",
    "medical.staff_requirement": "staffing from quarantine + sensory status",
    "patient.recovery_prospect": "recovery outlook from treatment safety + duration",
    "clinic.billing_tier": "billing class from prescription + staffing",

    # Crime scene
    "suspect_a.admissible_evidence": "evidence after custody integrity gate",
    "suspect_a.status": "A's status from admissible evidence",
    "suspect_b.testimonial_alibi": "human alibi affected by suspect A status",
    "suspect_b.digital_alibi": "CCTV-based alibi",
    "suspect_b.final_alibi": "final alibi with digital override",
    "suspect_b.status": "B's status from final alibi",
    "suspect_a.motive_verified": "A's motive verified with warrant",
    "suspect_b.motive_verified": "B's motive from relation",
    "case.theory": "case theory from suspect statuses",
    "case.lead_suspect": "lead suspect from theory + motives",

    # Thorncrester taxonomy
    "adult_thorncrester.ecological_stress": "stress level from weather + scarcity",
    "adult_thorncrester.expressed_diet": "expressed diet masked by stress",
    "adult_thorncrester.plumage_color": "plumage from expressed diet",
    "thorncrester_flock.expressed_structure": "social structure masked by stress",
    "thorncrester_flock.territory_behavior": "territory behavior from structure + scarcity",
    "juvenile_thorncrester.metabolic_state": "juvenile metabolism from enzyme + adult diet",
    "juvenile_thorncrester.development": "development from metabolic state",
    "feather_mite.bloom_status": "mite bloom from plumage + weather",
    "feather_mite.parasitic_load": "parasite load from bloom status",
    "adult_thorncrester.mortality_risk": "mortality risk from parasites + territory",
}

__all__ = ["BELIEF_DESCRIPTIONS"]
