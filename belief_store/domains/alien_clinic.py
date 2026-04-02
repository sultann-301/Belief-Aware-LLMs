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

    # R2: molecular phases per compound
    store.add_rule(
        name="zyxostin_phase",
        inputs=["atmosphere.dominant_gas"],
        output_key="zyxostin.phase",
        derive_fn=_zyxostin_phase,
    )
    store.add_rule(
        name="filinan_phase",
        inputs=["atmosphere.dominant_gas"],
        output_key="filinan.phase",
        derive_fn=_filinan_phase,
    )
    store.add_rule(
        name="snevox_phase",
        inputs=["atmosphere.dominant_gas"],
        output_key="snevox.phase",
        derive_fn=_snevox_phase,
    )

    # R3: hazards per compound
    store.add_rule(
        name="zyxostin_hazard",
        inputs=["patient.organism_type", "zyxostin.phase", "patient.organ_integrity"],
        output_key="zyxostin.hazard",
        derive_fn=_zyxostin_hazard,
    )
    store.add_rule(
        name="filinan_hazard",
        inputs=["patient.organism_type", "filinan.phase", "patient.organ_integrity"],
        output_key="filinan.hazard",
        derive_fn=_filinan_hazard,
    )
    store.add_rule(
        name="snevox_hazard",
        inputs=["patient.organism_type", "snevox.phase", "patient.organ_integrity"],
        output_key="snevox.hazard",
        derive_fn=_snevox_hazard,
    )

    # R4
    store.add_rule(
        name="active_prescription",
        inputs=[
            "patient.organism_type",
            "patient.symptoms",
            "zyxostin.hazard",
            "filinan.hazard",
            "snevox.hazard",
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
            "zyxostin.hazard",
            "filinan.hazard",
            "snevox.hazard",
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


# --- R3: hazards ---
def _evaluate_hazard(
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
        return "LETHAL"
    
    # 2. State-Based
    if phase == "plasma" and compound == "filinan":
        return "LETHAL"
    if phase == "vapor" and compound == "snevox" and organism == "Qwerl":
        return "LETHAL"
    
    # 3. Condition-Based
    if integrity == "volatile":
        return "LETHAL"
    
    return "safe"


def _zyxostin_hazard(inputs: dict[str, Any]) -> str:
    return _evaluate_hazard(
        "zyxostin",
        inputs["patient.organism_type"],
        inputs["zyxostin.phase"],
        inputs["patient.organ_integrity"],
    )


def _filinan_hazard(inputs: dict[str, Any]) -> str:
    return _evaluate_hazard(
        "filinan",
        inputs["patient.organism_type"],
        inputs["filinan.phase"],
        inputs["patient.organ_integrity"],
    )


def _snevox_hazard(inputs: dict[str, Any]) -> str:
    return _evaluate_hazard(
        "snevox",
        inputs["patient.organism_type"],
        inputs["snevox.phase"],
        inputs["patient.organ_integrity"],
    )


# --- R4: active_prescription ---
def _active_prescription(inputs: dict[str, Any]) -> str:
    organism = inputs["patient.organism_type"]
    symptoms = inputs.get("patient.symptoms", [])
    hazards = {
        "zyxostin": inputs["zyxostin.hazard"],
        "filinan": inputs["filinan.hazard"],
        "snevox": inputs["snevox.hazard"],
    }
    
    # 1. MIRACLE OVERRIDE
    if hazards["filinan"] == "symbiotic":
        return "filinan"
    if hazards["zyxostin"] == "symbiotic":
        return "zyxostin"
    if hazards["snevox"] == "symbiotic":
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
        if hazards[option] == "safe":
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
        hazard_key = f"{prescription}.hazard"
        if inputs.get(hazard_key) == "symbiotic":
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
