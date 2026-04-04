"""
Crime Scene Investigation domain — deterministic derivation rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from belief_store.store import BeliefStore


def setup_crime_scene_domain(store: BeliefStore) -> None:
    """Register all crime scene domain rules on the given store."""

    # R1: suspect_a.admissible_evidence
    store.add_rule(
        name="admissible_evidence",
        inputs=["suspect_a.home_evidence", "suspect_a.evidence_logger", "officer_smith.status"],
        output_key="suspect_a.admissible_evidence",
        derive_fn=_admissible_evidence,
    )

    # R2: suspect_a.status
    store.add_rule(
        name="status_a",
        inputs=["suspect_a.admissible_evidence"],
        output_key="suspect_a.status",
        derive_fn=_status_a,
    )

    # R3: suspect_b.testimonial_alibi
    store.add_rule(
        name="testimonial_alibi",
        inputs=["suspect_b.alibi_partner", "suspect_a.status"],
        output_key="suspect_b.testimonial_alibi",
        derive_fn=_testimonial_alibi,
    )

    # R4: suspect_b.digital_alibi
    store.add_rule(
        name="digital_alibi",
        inputs=["case.cctv_status", "case.cctv_subject"],
        output_key="suspect_b.digital_alibi",
        derive_fn=_digital_alibi,
    )

    # R5: suspect_b.final_alibi
    store.add_rule(
        name="final_alibi",
        inputs=["suspect_b.testimonial_alibi", "suspect_b.digital_alibi"],
        output_key="suspect_b.final_alibi",
        derive_fn=_final_alibi,
    )

    # R6: suspect_b.status
    store.add_rule(
        name="status_b",
        inputs=["suspect_b.final_alibi"],
        output_key="suspect_b.status",
        derive_fn=_status_b,
    )

    # R7: suspect_a.motive_verified
    store.add_rule(
        name="motive_verified_a",
        inputs=["suspect_a.financial_records", "case.warrant_status"],
        output_key="suspect_a.motive_verified",
        derive_fn=_motive_verified_a,
    )

    # R8: suspect_b.motive_verified
    store.add_rule(
        name="motive_verified_b",
        inputs=["suspect_b.relation_to_victim"],
        output_key="suspect_b.motive_verified",
        derive_fn=_motive_verified_b,
    )

    # R9: case.theory
    store.add_rule(
        name="theory",
        inputs=["suspect_a.status", "suspect_b.status"],
        output_key="case.theory",
        derive_fn=_theory,
    )

    # R10: case.lead_suspect
    store.add_rule(
        name="lead_suspect",
        inputs=[
            "case.theory",
            "suspect_a.status",
            "suspect_b.status",
            "suspect_a.motive_verified",
            "suspect_b.motive_verified"
        ],
        output_key="case.lead_suspect",
        derive_fn=_lead_suspect,
    )


# --- Derivation Functions ---

def _admissible_evidence(inputs: dict[str, Any]) -> str:
    home_evidence = inputs["suspect_a.home_evidence"]
    logger = inputs["suspect_a.evidence_logger"]
    smith_status = inputs["officer_smith.status"]
    
    if logger == "officer_smith" and smith_status == "suspended":
        return "none"
    return home_evidence


def _status_a(inputs: dict[str, Any]) -> str:
    if inputs["suspect_a.admissible_evidence"] != "none":
        return "prime_suspect"
    return "cleared"


def _testimonial_alibi(inputs: dict[str, Any]) -> str:
    partner = inputs["suspect_b.alibi_partner"]
    status_a = inputs["suspect_a.status"]
    
    if partner == "suspect_a" and status_a == "prime_suspect":
        return "broken"
    return "confirmed"


def _digital_alibi(inputs: dict[str, Any]) -> str:
    if inputs["case.cctv_status"] == "active" and inputs["case.cctv_subject"] == "suspect_b":
        return "confirmed"
    return "none"


def _final_alibi(inputs: dict[str, Any]) -> str:
    digital = inputs["suspect_b.digital_alibi"]
    testimonial = inputs["suspect_b.testimonial_alibi"]
    
    if digital == "confirmed":
        return "confirmed"
    return testimonial


def _status_b(inputs: dict[str, Any]) -> str:
    if inputs["suspect_b.final_alibi"] == "broken":
        return "prime_suspect"
    return "cleared"


def _motive_verified_a(inputs: dict[str, Any]) -> bool:
    records = inputs["suspect_a.financial_records"]
    warrant = inputs["case.warrant_status"]
    
    if records == "debt" and warrant is True:
        return True
    return False


def _motive_verified_b(inputs: dict[str, Any]) -> bool:
    return inputs["suspect_b.relation_to_victim"] == "enemy"


def _theory(inputs: dict[str, Any]) -> str:
    status_a = inputs["suspect_a.status"]
    status_b = inputs["suspect_b.status"]
    
    if status_a == "prime_suspect" and status_b == "prime_suspect":
        return "collusion"
    if status_a == "prime_suspect" or status_b == "prime_suspect":
        return "solo_perpetrator"
    return "unsolved"


def _lead_suspect(inputs: dict[str, Any]) -> str:
    theory = inputs["case.theory"]
    status_a = inputs["suspect_a.status"]
    status_b = inputs["suspect_b.status"]
    motive_a = inputs["suspect_a.motive_verified"]
    motive_b = inputs["suspect_b.motive_verified"]
    
    if theory == "unsolved":
        return "none"
    if theory == "solo_perpetrator":
        if status_a == "prime_suspect":
            return "suspect_a"
        if status_b == "prime_suspect":
            return "suspect_b"
            
    if theory == "collusion":
        if motive_a is True and motive_b is False:
            return "suspect_a"
        if motive_b is True and motive_a is False:
            return "suspect_b"
        return "both"
        
    return "none"
