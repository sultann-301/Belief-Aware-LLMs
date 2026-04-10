"""
Alien Clinic (Zylosian Xenomedicine) domain — deterministic derivation rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from belief_store.store import BeliefStore


def setup_alien_clinic_domain(store: BeliefStore) -> None:
    """Register all alien clinic domain rules on the given store."""

    # R1: organ_integrity
    store.add_rule(
        name="organ_integrity",
        inputs=["atmosphere.ambient_pressure", "patient.organism_type"],
        output_key="patient.organ_integrity",
        derive_fn=_organ_integrity,
    )

    # R2: molecular phases per compound (under treatment entity)
    store.add_rule(
        name="zyxostin_phase",
        inputs=["atmosphere.dominant_gas"],
        output_key="treatment.zyxostin_phase",
        derive_fn=_zyxostin_phase,
    )
    store.add_rule(
        name="filinan_phase",
        inputs=["atmosphere.dominant_gas"],
        output_key="treatment.filinan_phase",
        derive_fn=_filinan_phase,
    )
    store.add_rule(
        name="snevox_phase",
        inputs=["atmosphere.dominant_gas"],
        output_key="treatment.snevox_phase",
        derive_fn=_snevox_phase,
    )

    # R3: danger_levels per compound
    store.add_rule(
        name="zyxostin_danger_level",
        inputs=["patient.organism_type", "treatment.zyxostin_phase", "patient.organ_integrity"],
        output_key="treatment.zyxostin_danger_level",
        derive_fn=_zyxostin_danger_level,
    )
    store.add_rule(
        name="filinan_danger_level",
        inputs=["patient.organism_type", "treatment.filinan_phase", "patient.organ_integrity"],
        output_key="treatment.filinan_danger_level",
        derive_fn=_filinan_danger_level,
    )
    store.add_rule(
        name="snevox_danger_level",
        inputs=["patient.organism_type", "treatment.snevox_phase", "patient.organ_integrity"],
        output_key="treatment.snevox_danger_level",
        derive_fn=_snevox_danger_level,
    )

    # R4
    store.add_rule(
        name="active_prescription",
        inputs=[
            "patient.organism_type",
            "patient.symptoms",
            "treatment.zyxostin_danger_level",
            "treatment.filinan_danger_level",
            "treatment.snevox_danger_level",
        ],
        output_key="treatment.active_prescription",
        derive_fn=_active_prescription,
    )

    # R5
    store.add_rule(
        name="sensory_status",
        inputs=["treatment.active_prescription"],
        output_key="patient.sensory_status",
        derive_fn=_sensory_status,
    )

    # R6
    store.add_rule(
        name="quarantine_required",
        inputs=["atmosphere.dominant_gas", "patient.organism_type"],
        output_key="patient.quarantine_required",
        derive_fn=_quarantine_required,
    )

    # R7
    store.add_rule(
        name="duration_cycles",
        inputs=["treatment.active_prescription", "patient.organ_integrity"],
        output_key="treatment.duration_cycles",
        derive_fn=_duration_cycles,
    )

    # R8
    store.add_rule(
        name="staff_requirement",
        inputs=["patient.quarantine_required", "patient.sensory_status"],
        output_key="medical.staff_requirement",
        derive_fn=_staff_requirement,
    )

    # R9
    store.add_rule(
        name="recovery_prospect",
        inputs=[
            "treatment.active_prescription",
            "treatment.zyxostin_danger_level",
            "treatment.filinan_danger_level",
            "treatment.snevox_danger_level",
            "treatment.duration_cycles",
            "medical.staff_requirement"
        ],
        output_key="patient.recovery_prospect",
        derive_fn=_recovery_prospect,
    )

    # R10
    store.add_rule(
        name="billing_tier",
        inputs=["treatment.active_prescription", "medical.staff_requirement"],
        output_key="clinic.billing_tier",
        derive_fn=_billing_tier,
    )


# --- R1: organ_integrity ---
def _organ_integrity(inputs: dict[str, Any]) -> str:
    pressure = inputs["atmosphere.ambient_pressure"]
    organism = inputs["patient.organism_type"]

    if pressure > 5.0 and organism == "Yorp":
        return "volatile"
    if pressure > 4.0 and organism == "Glerps":
        return "volatile"
    if pressure > 3.0:
        return "brittle"
    return "stable"


# --- R2: phases ---
def _zyxostin_phase(inputs: dict[str, Any]) -> str:
    return "plasma" if inputs["atmosphere.dominant_gas"] == "methane" else "crystalline"


def _filinan_phase(inputs: dict[str, Any]) -> str:
    return "vapor" if inputs["atmosphere.dominant_gas"] == "xenon" else "plasma"


def _snevox_phase(inputs: dict[str, Any]) -> str:
    return "liquid" if inputs["atmosphere.dominant_gas"] == "chlorine" else "vapor"


# --- R3: danger_levels ---
def _evaluate_danger_level(
    compound: str,
    organism: str,
    phase: str,
    integrity: str,
) -> str:
    # 1. EXPLODE CONSTRAINTS & SINGULARITY
    is_explode = False
    if organism == "Glerps" and compound == "zyxostin":
        is_explode = True
    elif organism == "Yorp" and compound == "filinan":
        is_explode = True
    elif organism == "Qwerl" and compound == "snevox":
        is_explode = True
        
    if is_explode:
        if integrity == "volatile":
            return "symbiotic"
        return "fatal_to_patient"
    
    # 2. State-Based
    if phase == "plasma" and compound == "filinan":
        return "fatal_to_patient"
    if phase == "vapor" and compound == "snevox" and organism == "Qwerl":
        return "fatal_to_patient"
    
    # 3. Condition-Based
    if integrity == "volatile":
        return "fatal_to_patient"
    
    return "safe"


def _zyxostin_danger_level(inputs: dict[str, Any]) -> str:
    return _evaluate_danger_level(
        "zyxostin",
        inputs["patient.organism_type"],
        inputs["treatment.zyxostin_phase"],
        inputs["patient.organ_integrity"],
    )


def _filinan_danger_level(inputs: dict[str, Any]) -> str:
    return _evaluate_danger_level(
        "filinan",
        inputs["patient.organism_type"],
        inputs["treatment.filinan_phase"],
        inputs["patient.organ_integrity"],
    )


def _snevox_danger_level(inputs: dict[str, Any]) -> str:
    return _evaluate_danger_level(
        "snevox",
        inputs["patient.organism_type"],
        inputs["treatment.snevox_phase"],
        inputs["patient.organ_integrity"],
    )


# --- R4: active_prescription ---
def _active_prescription(inputs: dict[str, Any]) -> str:
    organism = inputs["patient.organism_type"]
    symptoms = inputs.get("patient.symptoms", [])
    danger_levels = {
        "zyxostin": inputs["treatment.zyxostin_danger_level"],
        "filinan": inputs["treatment.filinan_danger_level"],
        "snevox": inputs["treatment.snevox_danger_level"],
    }
    
    # 1. MIRACLE OVERRIDE
    if danger_levels["filinan"] == "symbiotic":
        return "filinan"
    if danger_levels["zyxostin"] == "symbiotic":
        return "zyxostin"
    if danger_levels["snevox"] == "symbiotic":
        return "snevox"
        
    # 2. SYMPTOM PRIORITIES
    if organism == "Glerps":
        if "fever" in symptoms and "spasms" in symptoms:
            priority = ["snevox", "zyxostin", "filinan"]
        elif "fever" in symptoms:
            priority = ["zyxostin", "snevox", "filinan"]
        else:
            priority = ["filinan", "zyxostin", "snevox"]
    elif organism == "Yorp":
        if "acid_sweat" in symptoms:
            priority = ["filinan", "snevox", "zyxostin"]
        else:
            priority = ["zyxostin", "snevox", "filinan"]
    elif organism == "Qwerl":
        priority = ["snevox", "zyxostin", "filinan"]
    else:
        priority = []
        
    for option in priority:
        if danger_levels[option] == "safe":
            return option
            
    return "none"


# --- R5: sensory_status ---
def _sensory_status(inputs: dict[str, Any]) -> str:
    if inputs["treatment.active_prescription"] == "snevox":
        return "telepathic"
    return "normal"


# --- R6: quarantine_required ---
def _quarantine_required(inputs: dict[str, Any]) -> bool:
    gas = inputs["atmosphere.dominant_gas"]
    organism = inputs["patient.organism_type"]
    
    if gas == "chlorine" and organism == "Qwerl":
        return True
    if gas == "methane" and organism == "Yorp":
        return True
    return False


# --- R7: duration_cycles ---
def _duration_cycles(inputs: dict[str, Any]) -> int:
    prescription = inputs["treatment.active_prescription"]
    integrity = inputs["patient.organ_integrity"]
    
    if prescription == "snevox" and integrity == "volatile":
        return 12
    if prescription == "none":
        return 0
    return 5


# --- R8: staff_requirement ---
def _staff_requirement(inputs: dict[str, Any]) -> str:
    if inputs["patient.quarantine_required"]:
        return "hazmat_team"
    if inputs["patient.sensory_status"] == "telepathic":
        return "psionic_handler"
    return "standard_medic"


# --- R9: recovery_prospect ---
def _recovery_prospect(inputs: dict[str, Any]) -> str:
    prescription = inputs["treatment.active_prescription"]
    duration = inputs["treatment.duration_cycles"]
    staff = inputs["medical.staff_requirement"]
    
    # 1. MIRACLE CHECK
    if prescription != "none":
        danger_level_key = f"treatment.{prescription}_danger_level"
        if inputs.get(danger_level_key) == "symbiotic":
            return "miraculous"
            
    # 2. STANDARD CHECK
    if duration > 10 and staff == "hazmat_team":
        return "guarded"
    if duration == 0:
        return "terminal"
    return "excellent"


# --- R10: billing_tier ---
def _billing_tier(inputs: dict[str, Any]) -> str:
    prescription = inputs["treatment.active_prescription"]
    staff = inputs["medical.staff_requirement"]
    
    if staff == "psionic_handler" or prescription == "snevox":
        return "class_omega"
    if staff == "hazmat_team":
        return "class_delta"
    return "class_standard"
