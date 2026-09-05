"""
Extended Evaluation Scenarios for the Alien Clinic Domain.

Includes 10 turns each for: Negation, 1-Hop, 2-Hop, 3-Hop, 4-Hop, and Belief Maintenance.
"""

# =====================================================================
# 1. NEGATION SET (10 Turns)
# Target: Negative phrasing while retrieving the correct factual state.
# =====================================================================
ALIEN_NEGATION_TURNS = [
    {
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 1.0, "patient.organism_type": "Glerps"},
        "question": "Is it false that the patient's organ integrity is stable?",
        "options": {"A": "False", "B": "True", "C": "Unsure"},
        "correct": "A" # At 1.0 pressure, organ integrity IS stable
    },
    {
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"patient.symptoms": ["acid_sweat"], "patient.organism_type": "Yorp", "atmosphere.dominant_gas": "methane"},
        "question": "Is it inaccurate to say the active prescription is filinan?",
        "options": {"A": "No", "B": "Maybe", "C": "Yes"},
        "correct": "C"
    },
    {
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Qwerl"},
        "question": "Is it untrue that the medical staff requirement is standard_medic?",
        "options": {"A": "False", "B": "True", "C": "Cannot determine"},
        "correct": "B"
    },
    {
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Yorp", "patient.symptoms": [], "atmosphere.dominant_gas": "methane"},
        "question": "Is the statement 'the clinic billing tier is class_standard' incorrect?",
        "options": {"A": "True", "B": "False", "C": "Partially"},
        "correct": "A"
    },
    {
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "Is it false that zyxostin is in a plasma phase?",
        "options": {"A": "No", "B": "None", "C": "Yes"},
        "correct": "C"
    },
    {
        "attributes": ["patient.sensory_status"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0, "patient.organism_type": "Glerps", "patient.symptoms": []},
        "question": "Is it not the case that the patient has normal sensory status?",
        "options": {"A": "False", "B": "True", "C": "Maybe"},
        "correct": "B"
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"patient.organism_type": "Qwerl"},
        "question": "Is it incorrect to state the recovery prospect is terminal?",
        "options": {"A": "No", "B": "Yes", "C": "Unknown"},
        "correct": "B"
    },
    {
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        "question": "Is it false that the treatment will last exactly 12 cycles?",
        "options": {"A": "False", "B": "N/A", "C": "True"},
        "correct": "C"
    },
    {
        "attributes": ["patient.quarantine_required"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Qwerl"},
        "question": "Is it untrue that quarantine is bypassed?",
        "options": {"A": "True", "B": "False", "C": "Sometimes"},
        "correct": "A"
    },
    {
        "attributes": ["treatment.snevox_danger_level"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "atmosphere.dominant_gas": "chlorine"},
        "question": "Is it false that the snevox danger level is considered safe?",
        "options": {"A": "No", "B": "Yes", "C": "None"},
        "correct": "B"
    }
]

# =====================================================================
# 2. 1-HOP SET (10 Turns)
# Target: Direct derivations (Parent -> Child)
# =====================================================================
ALIEN_1HOP_TURNS = [
    {
        "attributes": ["patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 1.0,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "When pressure drops to 1.0, what is the organ integrity?",
        "options": {"A": "brittle", "B": "stable", "C": "volatile"},
        "correct": "B"
    },
    {
        "attributes": ["treatment.filinan_phase"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "In a xenon atmosphere, what phase is filinan in?",
        "options": {"A": "plasma", "B": "liquid", "C": "vapor"},
        "correct": "C"
    },
    {
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "chlorine",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "In a chlorine atmosphere, what is the zyxostin phase?",
        "options": {"A": "plasma", "B": "crystalline", "C": "vapor"},
        "correct": "B"
    },
    {
        "attributes": ["patient.quarantine_required"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Yorp",
            "patient.symptoms": [],
        },
        "question": "For this case, is quarantine required?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "A"
    },
    {
        "attributes": ["patient.sensory_status"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "What is the patient's sensory status?",
        "options": {"A": "telepathic", "B": "blind", "C": "normal"},
        "correct": "A"
    },
    {
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": ["fever", "spasms"],
        },
        "question": "Which staff type is required for this patient?",
        "options": {"A": "standard_medic", "B": "psionic_handler", "C": "hazmat_team"},
        "correct": "B"
    },
    {
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Yorp",
            "patient.symptoms": [],
        },
        "question": "What is the billing tier for this case?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "A"
    },
    {
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": ["acid_sweat"],
        },
        "question": "How many treatment cycles are required?",
        "options": {"A": "5", "B": "0", "C": "12"},
        "correct": "A"
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": ["spasms"],
        },
        "question": "What is the recovery prospect for this patient?",
        "options": {"A": "excellent", "B": "guarded", "C": "terminal"},
        "correct": "A"
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "At this pressure and case setup, what is the recovery prospect?",
        "options": {"A": "guarded", "B": "miraculous", "C": "excellent"},
        "correct": "B"
    }
]

# =====================================================================
# 3. 2-HOP SET (10 Turns)
# Target: Two levels of indirection.
# =====================================================================
ALIEN_2HOP_TURNS = [
    {   # Gas(1) -> Phase(2) -> Hazard(3)
        "attributes": ["treatment.filinan_danger_level"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # Xenon -> filinan_phase=vapor. Vapor filinan -> safe (brittle)
        "question": "In a xenon atmosphere, what is the filinan danger level?",
        "options": {"A": "fatal_to_patient", "B": "safe", "C": "symbiotic"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3)
        "attributes": ["treatment.snevox_danger_level"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "chlorine",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # Chlorine -> snevox_phase=liquid. Liquid snevox -> safe
        "question": "In a chlorine environment, what is the snevox danger level?",
        "options": {"A": "fatal_to_patient", "B": "symbiotic", "C": "safe"},
        "correct": "C"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3)
        "attributes": ["treatment.snevox_danger_level"],
        "beliefs": {
            "atmosphere.ambient_pressure": 5.0,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # 5.0 + Glerps -> volatile. Volatile + snevox(vapor) -> fatal_to_patient.
        "question": "When pressure hits 5.0, what happens to the snevox danger level?",
        "options": {"A": "fatal_to_patient", "B": "safe", "C": "symbiotic"},
        "correct": "A"
    },
    {   # Prescription(1) -> Sensory(2)
        "attributes": ["patient.sensory_status"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "What is the sensory status for this case?",
        "options": {"A": "telepathic", "B": "normal", "C": "blind"},
        "correct": "A"
    },
    {   # Species(1) -> Quarantine(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Yorp",
            "patient.symptoms": [],
        },
        # Yorp+Methane -> Quar=True -> hazmat_team
        "question": "For a Yorp patient, what medical staff is required by protocol?",
        "options": {"A": "psionic_handler", "B": "standard_medic", "C": "hazmat_team"},
        "correct": "C"
    },
    {   # Gas(1) -> Quarantine(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "chlorine",
            "patient.organism_type": "Qwerl",
            "patient.symptoms": [],
        },
        # Chlorine+Qwerl -> Quar=True -> hazmat_team
        "question": "If a Qwerl is brought in under a chlorine atmosphere, who must staff them?",
        "options": {"A": "standard_medic", "B": "hazmat_team", "C": "psionic_handler"},
        "correct": "B"
    },
    {   # Sensory(1) -> Staff(2) -> Billing(3)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "What billing tier results from this case?",
        "options": {"A": "class_standard", "B": "class_omega", "C": "class_delta"},
        "correct": "B"
    },
    {
        # Integrity(1) -> Hazard(2) -> Prescription(3) -> Recovery(4)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # 4.5 -> volatile -> symbiotic(zyxostin) -> excellent
        "question": "Given this pressure and patient profile, what is the recovery prospect?",
        "options": {"A": "guarded", "B": "miraculous", "C": "terminal"},
        "correct": "B"
    },
    {   # Prescription(1) -> Sensory(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": ["fever"],
        },
        "question": "Who is required to staff this case?",
        "options": {"A": "hazmat_team", "B": "standard_medic", "C": "psionic_handler"},
        "correct": "C"
    },
    {   # Prescription(1) -> Duration(2) -> Recovery(3)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "argon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [99999],
        },
        "question": "What is the recovery prospect for this case?",
        "options": {"A": "terminal", "B": "excellent", "C": "guarded"},
        "correct": "B"
    }
]

# =====================================================================
# 4. 3-HOP SET (10 Turns)
# Target: Three levels of indirection.
# =====================================================================
ALIEN_3HOP_TURNS = [
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "What compound is prescribed in this case?",
        "options": {"A": "snevox", "B": "zyxostin", "C": "none"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "What is prescribed in this case?",
        "options": {"A": "snevox", "B": "zyxostin", "C": "filinan"},
        "correct": "C"
    },
    {   # Species(1) -> Quarantine(2) -> Staff(3) -> Billing(4)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "chlorine",
            "patient.organism_type": "Qwerl",
            "patient.symptoms": [],
        },
        "question": "What billing tier applies to this case?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "A"
    },
    {   # Same chain but avoiding snevox override
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Yorp",
            "patient.symptoms": ["acid_sweat"],
        },
        "question": "What billing tier applies to this case?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "B"
    },
    {   # Pressure/Hazard(1) -> Prescription(2) -> Sensory(3) -> Staff(4)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 1.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # All hazards safe at low pressure -> filinan -> normal -> standard_medic
        "question": "Who is required to staff this case?",
        "options": {"A": "psionic_handler", "B": "hazmat_team", "C": "standard_medic"},
        "correct": "A"
    },
    {   # Pressure/Integrity -> Hazards all fatal -> Prescription -> Recovery
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 5.5, "atmosphere.dominant_gas": "argon", "patient.organism_type": "Yorp", "patient.symptoms": []},
        # All compounds have lethal interactions at high pressure for Yorp -> none -> duration 0 -> terminal
        "question": "What is the recovery prospect for this case?",
        "options": {"A": "excellent", "B": "terminal", "C": "miraculous"},
        "correct": "C"
    },
    {   # Species(1) -> Hazard(2) -> Prescription(3) -> Sensory(4)
        "attributes": ["patient.sensory_status"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "patient.organism_type": "Qwerl",
            "atmosphere.dominant_gas": "methane",
            "patient.symptoms": [],
        },
        # Qwerl+Methane. S(vapor)-fatal, Z(plasma)-safe, F(plasma)-fatal. S->Z->F. Z is safe -> zyxostin -> normal.
        "question": "What is the sensory status in this case?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"
    },
    {   # Pressure(1) -> Integrity(2) -> Duration(3) -> Recovery(4)  (actually Prescription(4) if symbiotic)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # 4.5 -> volatile -> symbiotic(zyxostin) -> miraculous
        "question": "What is the recovery prospect in this case?",
        "options": {"A": "terminal", "B": "excellent", "C": "miraculous"},
        "correct": "C"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "chlorine",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # Chlorine -> S=liquid, Z=crystalline, F=plasma.
        # Glerps F=fatal(plasma). Z=fatal(explode). S=safe(liquid). F->Z->S -> Snevox
        "question": "Which prescription is active in this case?",
        "options": {"A": "zyxostin", "B": "snevox", "C": "filinan"},
        "correct": "B"
    },
    {   # Symptoms(1) -> Prescription(2) -> Sensory(3) -> Staff(4)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "patient.organism_type": "Yorp",
            "patient.symptoms": ["acid_sweat"],
            "atmosphere.dominant_gas": "xenon",
        },
        "question": "Who is required to staff this case?",
        "options": {"A": "standard_medic", "B": "hazmat_team", "C": "psionic_handler"},
        "correct": "C"
    }
]

# =====================================================================
# 5. 4-HOP SET (10 Turns)
# Target: 4+ levels of indirection. Deepest possible logic tracing.
# =====================================================================
ALIEN_4HOP_TURNS = [
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Sensory(5)
        "attributes": ["patient.sensory_status"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # 4.5 -> volatile -> symbiotic(zyxostin) -> zyxostin -> normal
        "question": "What is the sensory status for this case?",
        "options": {"A": "telepathic", "B": "normal", "C": "blind"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Sensory(5)
        "attributes": ["patient.sensory_status"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # Xenon -> F(vapor,safe) -> filinan -> normal
        "question": "What is the sensory status for this case?",
        "options": {"A": "telepathic", "B": "blind", "C": "normal"},
        "correct": "C"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Duration(5)
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # 4.5 -> volatile -> symbiotic -> zyxostin -> duration 5
        "question": "How many treatment cycles are required in this case?",
        "options": {"A": "12", "B": "5", "C": "0"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # xen -> filinan -> class_standard
        "question": "What is the billing tier for this case?",
        "options": {"A": "class_standard", "B": "class_omega", "C": "class_delta"},
        "correct": "A"
    },
    {   # Species(1) -> Hazard(2) -> Prescription(3) -> Sensory(4) -> Staff(5)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "patient.organism_type": "Qwerl",
            "patient.symptoms": [],
            "atmosphere.dominant_gas": "methane",
        },
        # Qwerl+Methane -> Z(plasma,safe) -> zyxostin -> normal -> standard
        "question": "Who is required to staff this case?",
        "options": {"A": "hazmat_team", "B": "psionic_handler", "C": "standard_medic"},
        "correct": "C"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # 4.5 -> volatile -> symbiotic -> zyxostin -> class_standard
        "question": "What is the billing tier for this case?",
        "options": {"A": "class_omega", "B": "class_standard", "C": "class_delta"},
        "correct": "B"
    },
    {   # Symptoms(1) -> Prescription(2) -> Sensory(3) -> Staff(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "patient.organism_type": "Yorp",
            "patient.symptoms": ["acid_sweat"],
            "atmosphere.dominant_gas": "xenon",
        },
        # Yorp+Xenon+acid_sweat -> filinan -> standard -> class_standard
        "question": "What is the billing tier for this case?",
        "options": {"A": "class_standard", "B": "class_delta", "C": "class_omega"},
        "correct": "C"
    },
    {   # Gas(1) -> Quarantine(2) -> Staff(3) -> Recovery(4)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Yorp",
            "patient.symptoms": [],
        },
        # Methane+Yorp -> Quar=True -> hazmat. None prescribed -> duration=0 -> terminal
        "question": "What is the recovery prospect for this case?",
        "options": {"A": "excellent", "B": "miraculous", "C": "guarded"},
        "correct": "A"
    },
    {   # Pressure(1) -> Integrity(2) -> Duration(3) -> Recovery(4)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.1,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # 4.1+Glerps -> volatile -> symbiotic(zyxostin) -> miraculous
        "question": "What is the recovery prospect for this case?",
        "options": {"A": "excellent", "B": "miraculous", "C": "terminal"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Duration(5)
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        # Xenon -> F(vapor,safe) -> filinan -> duration 5
        "question": "How many treatment cycles are required in this case?",
        "options": {"A": "5", "B": "12", "C": "0"},
        "correct": "A"
    }
]

# =====================================================================
# 6. BELIEF MAINTENANCE SET (10 Turns)
# Target: Adding unrelated input beliefs should NOT affect independently-derived attributes.
# Tests that different dependency chains are orthogonal.
# =====================================================================
ALIEN_BELIEF_MAINTENANCE_TURNS = [
    {   # T1: baseline integrity
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0, "patient.organism_type": "Glerps"},
        "question": "At 2.0 atmospheres, what is the organ integrity of a Glerps patient?",
        "options": {"A": "brittle", "B": "stable", "C": "volatile"},
        "correct": "B"  # stable
    },
    {   # T2: gas delta -> phase (independent of pressure)
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "With xenon as the dominant gas, what is the phase of zyxostin?",
        "options": {"A": "crystalline", "B": "plasma", "C": "liquid"},
        "correct": "A"  # crystalline
    },
    {   # T3: symptoms added -> prescription accumulation
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"patient.symptoms": []},
        "question": "With no symptoms reported for this Glerps patient, what is the prescribed treatment?",
        "options": {"A": "snevox", "B": "zyxostin", "C": "filinan"},
        "correct": "C"  # filinan is safe and highest priority for Glerps no symptoms
    },
    {   # T4: symptom change -> prescription shift
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"patient.symptoms": ["fever"]},
        "question": "Patient develops a fever. What does the prescription change to?",
        "options": {"A": "zyxostin", "B": "snevox", "C": "none"},
        "correct": "B"  # zyxostin explodes (Glerps), so snevox is first safe priority
    },
    {   # T5: no delta -> sensory status (derived from T4 prescription)
        "attributes": ["patient.sensory_status"],
        "beliefs": {},
        "question": "Given the current snevox prescription, what is the patient's sensory status?",
        "options": {"A": "telepathic", "B": "normal", "C": "blinded"},
        "correct": "A"  # snevox -> telepathic
    },
    {   # T6: pressure spike -> integrity change
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        "question": "Pressure spikes to 4.5. What is the Glerps patient's organ integrity now?",
        "options": {"A": "stable", "B": "brittle", "C": "volatile"},
        "correct": "C"  # volatile (>4.0 for Glerps)
    },
    {   # T7: no delta -> zyxostin phase persistence
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {},
        "question": "Despite the pressure spike, what remains the phase of zyxostin in xenon gas?",
        "options": {"A": "plasma", "B": "crystalline", "C": "vapor"},
        "correct": "B"  # crystalline (persistence from T2)
    },
    {   # T8: organism change -> integrity shift
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"patient.organism_type": "Yorp"},
        "question": "The patient is actually a Yorp. At 4.5 atmospheres, what is their organ integrity?",
        "options": {"A": "brittle", "B": "stable", "C": "volatile"},
        "correct": "A"  # brittle (4.5 > 3.0, but only >5.0 is volatile for Yorp)
    },
    {   # T9: no delta -> quarantine check (independence)
        "attributes": ["patient.quarantine_required"],
        "beliefs": {},
        "question": "Is quarantine required for this Yorp in xenon gas?",
        "options": {"A": "Yes", "B": "No", "C": "Maybe"},
        "correct": "B"  # False (quarantine only for chlorine+Qwerl or methane+Yorp)
    },
    {   # T10: gas change -> quarantine trigger
        "attributes": ["patient.quarantine_required"],
        "beliefs": {"atmosphere.dominant_gas": "methane"},
        "question": "Gas shifts to methane. Is quarantine required for the Yorp patient now?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "A"  # True (methane + Yorp)
    }
]
