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
        "beliefs": {"atmosphere.ambient_pressure": 1.0, "patient.organism_type": "Glerps"},
        "question": "When pressure drops to 1.0, what is the organ integrity?",
        "options": {"A": "brittle", "B": "stable", "C": "volatile"},
        "correct": "B"
    },
    {
        "attributes": ["treatment.filinan_phase"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "In a xenon atmosphere, what phase is filinan in?",
        "options": {"A": "plasma", "B": "liquid", "C": "vapor"},
        "correct": "C"
    },
    {
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine"},
        "question": "In a chlorine atmosphere, what is the zyxostin phase?",
        "options": {"A": "plasma", "B": "crystalline", "C": "vapor"},
        "correct": "B"
    },
    {
        "attributes": ["patient.quarantine_required"],
        "beliefs": {"patient.organism_type": "Yorp", "atmosphere.dominant_gas": "methane"},
        "question": "If the patient is a Yorp, what is their quarantine required status?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "A"
    },
    {
        "attributes": ["patient.sensory_status"],
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": [], "atmosphere.dominant_gas": "methane"},
        "question": "If filinan is prescribed, what is the sensory status?",
        "options": {"A": "telepathic", "B": "blind", "C": "normal"},
        "correct": "C"
    },
    {
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "patient.organism_type": "Glerps", "patient.symptoms": ["fever", "spasms"]},
        "question": "If snevox is prescribed under xenon, what staff is required?",
        "options": {"A": "standard_medic", "B": "psionic_handler", "C": "hazmat_team"},
        "correct": "B"
    },
    {
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"atmosphere.dominant_gas": "methane", "patient.organism_type": "Yorp", "patient.symptoms": []},
        "question": "If snevox is active for a Yorp under methane, what is the billing tier?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "B"
    },
    {
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": ["severe_toxin"], "atmosphere.dominant_gas": "argon"},
        "question": "If no prescription can be safely administered, how many duration cycles?",
        "options": {"A": "5", "B": "0", "C": "12"},
        "correct": "B"
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.dominant_gas": "methane", "patient.organism_type": "Glerps", "patient.symptoms": ["severe_toxin"]},
        "question": "If no prescription is active for a Glerp under methane, what is the recovery prospect?",
        "options": {"A": "excellent", "B": "guarded", "C": "terminal"},
        "correct": "C"
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        "question": "If zyxostin is active at 4.5 pressure, what is the recovery prospect?",
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
        "beliefs": {"atmosphere.dominant_gas": "xenon"}, 
        # Xenon -> filinan_phase=vapor. Vapor filinan -> safe (brittle)
        "question": "In a xenon atmosphere, what is the filinan danger level?",
        "options": {"A": "fatal_to_patient", "B": "safe", "C": "symbiotic"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3)
        "attributes": ["treatment.snevox_danger_level"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine"},
        # Chlorine -> snevox_phase=liquid. Liquid snevox -> safe
        "question": "In a chlorine environment, what is the snevox danger level?",
        "options": {"A": "fatal_to_patient", "B": "symbiotic", "C": "safe"},
        "correct": "C"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3)
        "attributes": ["treatment.snevox_danger_level"],
        "beliefs": {"atmosphere.ambient_pressure": 5.0},
        # 5.0 + Glerps -> volatile. Volatile + snevox(vapor) -> fatal_to_patient.
        "question": "When pressure hits 5.0, what happens to the snevox danger level?",
        "options": {"A": "fatal_to_patient", "B": "safe", "C": "symbiotic"},
        "correct": "A"
    },
    {   # Prescription(1) -> Sensory(2)
        "attributes": ["patient.sensory_status"],
        "beliefs": {"treatment.active_prescription": "filinan"},
        # filinan -> normal
        "question": "If filinan is prescribed, what is the sensory status?",
        "options": {"A": "telepathic", "B": "normal", "C": "blind"},
        "correct": "B"
    },
    {   # Species(1) -> Quarantine(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"patient.organism_type": "Yorp"},
        # Yorp+Methane -> Quar=True -> hazmat_team
        "question": "For a Yorp patient, what medical staff is required by protocol?",
        "options": {"A": "psionic_handler", "B": "standard_medic", "C": "hazmat_team"},
        "correct": "C"
    },
    {   # Gas(1) -> Quarantine(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Qwerl"},
        # Chlorine+Qwerl -> Quar=True -> hazmat_team
        "question": "If a Qwerl is brought in under a chlorine atmosphere, who must staff them?",
        "options": {"A": "standard_medic", "B": "hazmat_team", "C": "psionic_handler"},
        "correct": "B"
    },
    {   # Sensory(1) -> Staff(2) -> Billing(3)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": [], "atmosphere.dominant_gas": "methane"},
        # filinan -> normal -> standard_medic -> class_standard
        "question": "If filinan leads to normal sensory status, what is the billing tier?",
        "options": {"A": "class_standard", "B": "class_omega", "C": "class_delta"},
        "correct": "A"
    },
    {
        # Integrity(1) -> Hazard(2) -> Prescription(3) -> Recovery(4)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # 4.5 -> volatile -> symbiotic(zyxostin) -> excellent
        "question": "With volatile integrity from pressure, what is the recovery prospect?",
        "options": {"A": "guarded", "B": "terminal", "C": "excellent"},
        "correct": "C"
    },
    {   # Prescription(1) -> Sensory(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": ["fever"], "atmosphere.dominant_gas": "methane"},
        # fever -> zyxostin priority -> normal sensory -> staff determination
        "question": "If zyxostin is preferred based on symptoms, who staffs the ward?",
        "options": {"A": "hazmat_team", "B": "standard_medic", "C": "psionic_handler"},
        "correct": "B"
    },
    {   # Prescription(1) -> Duration(2) -> Recovery(3)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": [99999], "atmosphere.dominant_gas": "argon"},
        # incompatible symptoms/atmosphere combo -> none -> duration=0 -> terminal
        "question": "If no prescription is analyzable, what is the recovery prospect?",
        "options": {"A": "terminal", "B": "excellent", "C": "guarded"},
        "correct": "A"
    }
]

# =====================================================================
# 4. 3-HOP SET (10 Turns)
# Target: Three levels of indirection.
# =====================================================================
ALIEN_3HOP_TURNS = [
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # 4.5+Glerps -> volatile. Volatile+Zyxostin+Glerps -> symbiotic hazard. Active -> zyxostin.
        "question": "When pressure rises to 4.5, what compound is ultimately prescribed?",
        "options": {"A": "snevox", "B": "zyxostin", "C": "none"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "patient.organism_type": "Glerps", "patient.symptoms": []},
        # Xenon -> F(vapor, safe), Z(crystalline, safe), S(vapor, safe). Glerps priority: F->Z->S. -> filinan
        "question": "In a xenon atmosphere with no symptoms, what is prescribed?",
        "options": {"A": "snevox", "B": "zyxostin", "C": "filinan"},
        "correct": "C"
    },
    {   # Species(1) -> Quarantine(2) -> Staff(3) -> Billing(4)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Qwerl", "atmosphere.dominant_gas": "chlorine"},
        # Q+Chlorine -> Quar=True -> hazmat -> class_delta 
        # (Wait, Qwerl+Chlorine snevox=liquid(safe). Prescription=snevox. snevox -> class_omega overrules!). Let's change snevox priority or prescription.
        "question": "For a Qwerl patient in a chlorine environment where snevox is active, what is the tier?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "B"
    },
    {   # Same chain but avoiding snevox override
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Yorp", "patient.symptoms": ["acid_sweat"], "atmosphere.dominant_gas": "methane"},
        # Yorp+Methane+acid_sweat -> Quar=True -> hazmat. filinan -> normal. Staff=hazmat -> class_delta.
        "question": "If a Yorp with acid sweat goes through symptom-based prescription, what billing tier?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "A"
    },
    {   # Pressure/Hazard(1) -> Prescription(2) -> Sensory(3) -> Staff(4)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"atmosphere.ambient_pressure": 1.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # All hazards safe at low pressure -> filinan -> normal -> standard_medic
        "question": "At low pressure where all compounds are safe, who staffs the room?",
        "options": {"A": "psionic_handler", "B": "hazmat_team", "C": "standard_medic"},
        "correct": "C"
    },
    {   # Pressure/Integrity -> Hazards all fatal -> Prescription -> Recovery
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 5.5, "atmosphere.dominant_gas": "argon", "patient.organism_type": "Yorp", "patient.symptoms": []},
        # All compounds have lethal interactions at high pressure for Yorp -> none -> duration 0 -> terminal
        "question": "At extreme pressure where all compounds become lethal, what is the prospect?",
        "options": {"A": "excellent", "B": "terminal", "C": "guarded"},
        "correct": "B"
    },
    {   # Species(1) -> Hazard(2) -> Prescription(3) -> Sensory(4)
        "attributes": ["patient.sensory_status"],
        "beliefs": {"patient.organism_type": "Qwerl", "atmosphere.dominant_gas": "methane", "patient.symptoms": []},
        # Qwerl+Methane. S(vapor)-fatal, Z(plasma)-safe, F(plasma)-fatal. S->Z->F. Z is safe -> zyxostin -> normal.
        "question": "A Qwerl checks in under methane with no reported symptoms. What sensory status post-medication?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"
    },
    {   # Pressure(1) -> Integrity(2) -> Duration(3) -> Recovery(4)  (actually Prescription(4) if symbiotic)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # 4.5 -> volatile -> symbiotic(zyxostin) -> miraculous
        "question": "Under 4.5 pressure, a biological singularity occurs. What is the prospect?",
        "options": {"A": "terminal", "B": "excellent", "C": "miraculous"},
        "correct": "C"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Glerps"},
        # Chlorine -> S=liquid, Z=crystalline, F=plasma. 
        # Glerps F=fatal(plasma). Z=fatal(explode). S=safe(liquid). F->Z->S -> Snevox
        "question": "Under a chlorine atmosphere, which prescription does the Glerp receive?",
        "options": {"A": "zyxostin", "B": "snevox", "C": "filinan"},
        "correct": "B"
    },
    {   # Symptoms(1) -> Prescription(2) -> Sensory(3) -> Staff(4)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"patient.organism_type": "Yorp", "patient.symptoms": ["acid_sweat"], "atmosphere.dominant_gas": "xenon"},
        # Xenon -> F=vapor(safe). Yorp + acid_sweat -> F->S->Z. F is safe -> filinan -> normal -> hazmat (Yorp+methane? No, Xenon! Yorp+Xenon -> no quar -> standard_medic)
        "question": "A Yorp with acid sweat in Xenon. Who staffs them?",
        "options": {"A": "standard_medic", "B": "hazmat_team", "C": "psionic_handler"},
        "correct": "A"
    }
]

# =====================================================================
# 5. 4-HOP SET (10 Turns)
# Target: 4+ levels of indirection. Deepest possible logic tracing.
# =====================================================================
ALIEN_4HOP_TURNS = [
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Sensory(5)
        "attributes": ["patient.sensory_status"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # 4.5 -> volatile -> symbiotic(zyxostin) -> zyxostin -> normal
        "question": "At 4.5 ambient pressure causing extreme volatility, what is their sensory status?",
        "options": {"A": "telepathic", "B": "normal", "C": "blind"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Sensory(5)
        "attributes": ["patient.sensory_status"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "patient.organism_type": "Glerps", "patient.symptoms": []},
        # Xenon -> F(vapor,safe) -> filinan -> normal
        "question": "When xenon floods the room, what sensory side effect is caused by the new meds?",
        "options": {"A": "telepathic", "B": "blind", "C": "normal"},
        "correct": "C"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Duration(5)
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # 4.5 -> volatile -> symbiotic -> zyxostin -> duration 5
        "question": "At 4.5 pressure, how many cycles does the symbiotic reaction take?",
        "options": {"A": "12", "B": "5", "C": "0"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "patient.organism_type": "Glerps", "patient.symptoms": []},
        # xen -> filinan -> class_standard
        "question": "Xenon causes a shift in prescription. What does the final bill look like?",
        "options": {"A": "class_standard", "B": "class_omega", "C": "class_delta"},
        "correct": "A"
    },
    {   # Species(1) -> Hazard(2) -> Prescription(3) -> Sensory(4) -> Staff(5)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"patient.organism_type": "Qwerl", "patient.symptoms": [], "atmosphere.dominant_gas": "methane"},
        # Qwerl+Methane -> Z(plasma,safe) -> zyxostin -> normal -> standard
        "question": "A Qwerl walks in under methane. Which team handles them?",
        "options": {"A": "hazmat_team", "B": "psionic_handler", "C": "standard_medic"},
        "correct": "C"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # 4.5 -> volatile -> symbiotic -> zyxostin -> class_standard
        "question": "If pressure forces a biological singularity using zyxostin, how is it billed?",
        "options": {"A": "class_omega", "B": "class_standard", "C": "class_delta"},
        "correct": "B"
    },
    {   # Symptoms(1) -> Prescription(2) -> Sensory(3) -> Staff(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Yorp", "patient.symptoms": ["acid_sweat"], "atmosphere.dominant_gas": "xenon"},
        # Yorp+Xenon+acid_sweat -> filinan -> standard -> class_standard
        "question": "A Yorp with acid sweat under Xenon. What is their final billing class?",
        "options": {"A": "class_standard", "B": "class_delta", "C": "class_omega"},
        "correct": "A"
    },
    {   # Gas(1) -> Quarantine(2) -> Staff(3) -> Recovery(4)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.dominant_gas": "methane", "patient.organism_type": "Yorp", "patient.symptoms": []},
        # Methane+Yorp -> Quar=True -> hazmat. None prescribed -> duration=0 -> terminal
        "question": "A Yorp in Methane with no treatment options. What is the prospect?",
        "options": {"A": "excellent", "B": "miraculous", "C": "guarded"},
        "correct": "C"
    },
    {   # Pressure(1) -> Integrity(2) -> Duration(3) -> Recovery(4)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 4.1, "patient.organism_type": "Glerps", "patient.symptoms": []},
        # 4.1+Glerps -> volatile -> symbiotic(zyxostin) -> miraculous
        "question": "At 4.1 pressure for a Glerp with no symptoms, what is the recovery prospect?",
        "options": {"A": "excellent", "B": "miraculous", "C": "terminal"},
        "correct": "B"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Duration(5)
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        # Xenon -> F(vapor,safe) -> filinan -> duration 5
        "question": "Under xenon, what are the treatment duration cycles?",
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
    {   # Query: organ_integrity with just pressure
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0},
        "question": "At 2.0 pressure, what is the organ integrity?",
        "options": {"A": "brittle", "B": "volatile", "C": "stable"},
        "correct": "C"  # 2.0 -> stable
    },
    {   # Add symptoms (unrelated input) -> organ_integrity should stay same
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0, "patient.symptoms": ["fever"]},
        "question": "After adding symptoms, what is organ integrity?",
        "options": {"A": "stable", "B": "brittle", "C": "volatile"},
        "correct": "A"  # Maintained: symptoms don't affect organ_integrity
    },
    {   # Query: active_prescription with just pressure
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0, "patient.organism_type": "Glerps", "patient.symptoms": []},
        "question": "At 2.0 pressure, what prescription is active?",
        "options": {"A": "snevox", "B": "filinan", "C": "zyxostin"},
        "correct": "B"  # Glerps default: filinan
    },
    {   # Add organism type (different input) -> pressure-derived integral should stay same
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0, "patient.organism_type": "Yorp"},
        "question": "With Yorp organism type added, what is organ integrity?",
        "options": {"A": "brittle", "B": "volatile", "C": "stable"},
        "correct": "C"  # Maintained: 2.0 pressure is stable regardless of organism
    },
    {   # Query: zyxostin_phase with just gas
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "In xenon atmosphere, what is the zyxostin phase?",
        "options": {"A": "crystalline", "B": "plasma", "C": "vapor"},
        "correct": "A"  # xenon -> crystalline
    },
    {   # Add pressure (different input) -> phase should stay same
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "atmosphere.ambient_pressure": 3.5},
        "question": "After adding pressure, what is zyxostin phase?",
        "options": {"A": "plasma", "B": "crystalline", "C": "vapor"},
        "correct": "B"  # Maintained: phase depends on gas only, not pressure
    },
    {   # Query: sensory_status from prescription
        "attributes": ["patient.sensory_status"],
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": [], "atmosphere.dominant_gas": "methane"},
        "question": "With filinan prescribed (from defaults), what is sensory status?",
        "options": {"A": "telepathic", "B": "blind", "C": "normal"},
        "correct": "C"  # Only snevox -> telepathic
    },
    {   # Add organism info (different chain) -> sensory should unchanged
        "attributes": ["patient.sensory_status"],
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": [], "atmosphere.dominant_gas": "methane"},
        "question": "After specifying organism (still filinan), what is sensory status?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"  # Maintained: sensory depends on prescription only
    },
    {   # Query: quarantine_required with gas+organism
        "attributes": ["patient.quarantine_required"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "patient.organism_type": "Yorp"},
        "question": "Xenon + Yorp: is quarantine required?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "B"  # Xenon+Yorp doesn't trigger quarantine
    },
    {   # Add symptoms + pressure (different inputs) -> quarantine should stay false
        "attributes": ["patient.quarantine_required"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "patient.organism_type": "Yorp", "patient.symptoms": ["fever"], "atmosphere.ambient_pressure": 4.0},
        "question": "With symptoms and pressure added, is quarantine still required?",
        "options": {"A": "True", "B": "Changed", "C": "False"},
        "correct": "C"  # Maintained: quarantine depends on gas+organism pair only
    }
]
