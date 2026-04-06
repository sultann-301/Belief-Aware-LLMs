"""Lookup of brief descriptions for belief keys.

Keep compact, neutral descriptions that explain the relationship or role
of each attribute. `BELIEF_DESCRIPTIONS` is imported by `store.to_prompt`
to inject inline hints for the LLM when serializing beliefs.
"""
from __future__ import annotations

from typing import Dict

# A concise mapping: key -> short description used inline in prompts.
BELIEF_DESCRIPTIONS: Dict[str, str] = {
    # Loan domain (derived keys only)
    "loan.adjusted_income": "derived_from: applicant.income, applicant.dependents",
    "loan.credit_score_effective": "derived_from: applicant.credit_score, applicant.co_signer",
    "loan.applicant_prequalified": "derived_from: loan.adjusted_income, loan.credit_score_effective, applicant.debt_ratio, applicant.employment_status, applicant.bankruptcy_history, applicant.employment_duration_months, loan.min_income, loan.min_credit, loan.max_debt_ratio",
    "loan.rate_tier": "derived_from: loan.applicant_prequalified, loan.credit_score_effective",
    "loan.max_amount": "derived_from: loan.applicant_prequalified, applicant.has_collateral",
    "loan.application_status": "derived_from: loan.applicant_prequalified, applicant.loan_amount_requested, loan.max_amount",
    "loan.high_risk_flag": "derived_from: applicant.debt_ratio",
    "loan.requires_insurance": "derived_from: loan.high_risk_flag, loan.application_status",
    "loan.review_queue": "derived_from: loan.application_status, loan.high_risk_flag",
    "loan.base_interest_rate": "derived_from: loan.rate_tier, loan.requires_insurance",

    # Alien clinic (derived keys only)
    "patient.organ_integrity": "derived_from: atmosphere.ambient_pressure, patient.organism_type",
    "treatment.zyxostin_phase": "derived_from: atmosphere.dominant_gas (treatment compound)",
    "treatment.filinan_phase": "derived_from: atmosphere.dominant_gas (treatment compound)",
    "treatment.snevox_phase": "derived_from: atmosphere.dominant_gas (treatment compound)",
    "treatment.zyxostin_hazard": "derived_from: patient.organism_type, treatment.zyxostin_phase, patient.organ_integrity",
    "treatment.filinan_hazard": "derived_from: patient.organism_type, treatment.filinan_phase, patient.organ_integrity",
    "treatment.snevox_hazard": "derived_from: patient.organism_type, treatment.snevox_phase, patient.organ_integrity",
    "treatment.active_prescription": "derived_from: patient.organism_type, patient.symptoms, treatment.zyxostin_hazard, treatment.filinan_hazard, treatment.snevox_hazard",
    "patient.sensory_status": "derived_from: treatment.active_prescription",
    "patient.quarantine_required": "derived_from: atmosphere.dominant_gas, patient.organism_type",
    "treatment.duration_cycles": "derived_from: treatment.active_prescription, patient.organ_integrity",
    "medical.staff_requirement": "derived_from: patient.quarantine_required, patient.sensory_status",
    "patient.recovery_prospect": "derived_from: treatment.active_prescription, treatment.zyxostin_hazard, treatment.filinan_hazard, treatment.snevox_hazard, treatment.duration_cycles, medical.staff_requirement",
    "clinic.billing_tier": "derived_from: treatment.active_prescription, medical.staff_requirement",

    # Crime scene (derived keys only)
    "suspect_a.admissible_evidence": "derived_from: suspect_a.home_evidence, suspect_a.evidence_logger, officer_smith.status",
    "suspect_a.status": "derived_from: suspect_a.admissible_evidence",
    "suspect_b.testimonial_alibi": "derived_from: suspect_b.alibi_partner, suspect_a.status",
    "suspect_b.digital_alibi": "derived_from: case.cctv_status, case.cctv_subject",
    "suspect_b.final_alibi": "derived_from: suspect_b.testimonial_alibi, suspect_b.digital_alibi",
    "suspect_b.status": "derived_from: suspect_b.final_alibi",
    "suspect_a.motive_verified": "derived_from: suspect_a.financial_records, case.warrant_status",
    "suspect_b.motive_verified": "derived_from: suspect_b.relation_to_victim",
    "case.theory": "derived_from: suspect_a.status, suspect_b.status",
    "case.lead_suspect": "derived_from: case.theory, suspect_a.status, suspect_b.status, suspect_a.motive_verified, suspect_b.motive_verified",

    # Thorncrester taxonomy (derived keys only)
    "adult_thorncrester.ecological_stress": "derived_from: environment.weather_pattern, environment.food_scarcity",
    "adult_thorncrester.expressed_diet": "derived_from: adult_thorncrester.genetic_diet, adult_thorncrester.ecological_stress",
    "adult_thorncrester.plumage_color": "derived_from: adult_thorncrester.expressed_diet",
    "thorncrester_flock.expressed_structure": "derived_from: thorncrester_flock.genetic_structure, adult_thorncrester.ecological_stress",
    "thorncrester_flock.territory_behavior": "derived_from: thorncrester_flock.expressed_structure, environment.food_scarcity",
    "juvenile_thorncrester.metabolic_state": "derived_from: juvenile_thorncrester.digestive_enzyme, adult_thorncrester.expressed_diet",
    "juvenile_thorncrester.development": "derived_from: juvenile_thorncrester.metabolic_state",
    "feather_mite.bloom_status": "derived_from: adult_thorncrester.plumage_color, environment.weather_pattern",
    "feather_mite.parasitic_load": "derived_from: feather_mite.bloom_status",
    "adult_thorncrester.mortality_risk": "derived_from: feather_mite.parasitic_load, thorncrester_flock.territory_behavior",
}

__all__ = ["BELIEF_DESCRIPTIONS"]
