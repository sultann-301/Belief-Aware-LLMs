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
        "beliefs": {},
        "question": "Is it false that the patient's organ integrity is stable?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "A" # It is 'brittle', so it IS false that it is stable.
    },
    {
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"patient.symptoms": ["acid_sweat"]},
        # Glerps: no 'acid_sweat' specific priority. Falls back to filinan -> zyxostin -> snevox
        # Hazards stay the same: filinan=fatal, zyxostin=fatal, snevox=safe. Prescription = snevox
        "question": "Is it inaccurate to say the active prescription is filinan?",
        "options": {"A": "Yes", "B": "No", "C": "Maybe"},
        "correct": "A" # It's snevox, so saying it's filinan is inaccurate (Yes).
    },
    {
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine"},
        # Chlorine: snevox_phase = liquid, zyxostin_phase=crystalline, filinan_phase=plasma
        # None of the Glerps hazards trigger for liquid/crystalline. 
        # Zyxostin: Glerps explode -> fatal. 
        # filinan: plasma -> fatal. 
        # snevox: liquid -> safe. 
        # Prescription -> snevox -> telepathic -> psionic_handler
        "question": "Is it untrue that the medical staff requirement is standard_medic?",
        "options": {"A": "True", "B": "False", "C": "Cannot determine"},
        "correct": "A" # It is psionic_handler, so it is untrue that it is standard_medic.
    },
    {
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Yorp"},
        # Yorp + 3.5 press -> brittle. 
        # Methane + Yorp -> Quarantine=True
        # Yorp + Methane -> Z(plasma, safe), F(plasma, fatal), S(vapor, safe)
        # Yorp F->S->Z. F is fatal. S is safe -> active = snevox.
        # Quarantine overrides Psionic -> hazmat_team
        # hazmat_team -> class_delta 
        # (Wait, R10: psionic_handler OR snevox -> class_omega. It's snevox! class_omega!)
        "question": "Is the statement 'the clinic billing tier is class_standard' incorrect?",
        "options": {"A": "True", "B": "False", "C": "Partially"},
        "correct": "A" # It is class_omega. So standard is incorrect (True).
    },
    {
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        # Xenon -> Z(crystalline), F(vapor), S(vapor)
        "question": "Is it false that zyxostin is in a plasma phase?",
        "options": {"A": "Yes", "B": "No", "C": "None"},
        "correct": "A" # It is crystalline, so Yes, it's false it's plasma.
    },
    {
        "attributes": ["patient.sensory_status"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0},
        # Pressure 2.0 -> stable. Glerps+methane still means snevox -> telepathic
        "question": "Is it not the case that the patient has normal sensory status?",
        "options": {"A": "True", "B": "False", "C": "Maybe"},
        "correct": "A" # They are telepathic, so they do NOT have normal.
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"patient.organism_type": "Qwerl"},
        # Qwerl + methane (3.5=brittle) 
        # Z(plasma)-safe, F(plasma)-fatal, S(vapor)-fatal (vapor+S+Qwerl=fatal).
        # Qwerl priority: S->Z->F. S is fatal. Z is safe -> zyxostin.
        # Duration: 5. Staff: standard. Prospect: excellent.
        "question": "Is it incorrect to state the recovery prospect is terminal?",
        "options": {"A": "Yes", "B": "No", "C": "Unknown"},
        "correct": "A" # It is excellent. Saying terminal is incorrect.
    },
    {
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        # 4.5 + Glerps -> volatile. Glerps+Zyxostin+volatile -> symbiotic!
        # Prescription -> zyxostin. Duration cycles -> 5
        "question": "Is it false that the treatment will last exactly 12 cycles?",
        "options": {"A": "True", "B": "False", "C": "N/A"},
        "correct": "A" # It lasts 5 cycles. So false.
    },
    {
        "attributes": ["patient.quarantine_required"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Qwerl"},
        # Chlorine + Qwerl -> True quarantine
        "question": "Is it untrue that quarantine is bypassed?",
        "options": {"A": "True", "B": "False", "C": "Sometimes"},
        "correct": "A" # Quarantine is required. So asserting it's bypassed is untrue.
    },
    {
        "attributes": ["treatment.snevox_danger_level"],
        "beliefs": {"patient.organ_integrity": "volatile", "atmosphere.dominant_gas": "chlorine"},
        # Chlorine -> snevox=liquid. Glerps + volatile + snevox(liquid) -> No explode, but volatile -> fatal_to_patient.
        "question": "Is it false that the snevox danger level is considered safe?",
        "options": {"A": "Yes", "B": "No", "C": "None"},
        "correct": "A" # It is fatal_to_patient.
    }
]

# =====================================================================
# 2. 1-HOP SET (10 Turns)
# Target: Direct derivations (Parent -> Child)
# =====================================================================
ALIEN_1HOP_TURNS = [
    {
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 1.0},
        "question": "When pressure drops to 1.0, what is the organ integrity?",
        "options": {"A": "stable", "B": "brittle", "C": "volatile"},
        "correct": "A"
    },
    {
        "attributes": ["treatment.filinan_phase"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "In a xenon atmosphere, what phase is filinan in?",
        "options": {"A": "vapor", "B": "plasma", "C": "liquid"},
        "correct": "A"
    },
    {
        "attributes": ["treatment.zyxostin_phase"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine"},
        "question": "In a chlorine atmosphere, what is the zyxostin phase?",
        "options": {"A": "crystalline", "B": "plasma", "C": "vapor"}, # methane=plasma, else=crystalline
        "correct": "A"
    },
    {
        "attributes": ["patient.quarantine_required"],
        "beliefs": {"patient.organism_type": "Yorp"},
        "question": "If the patient is a Yorp, what is their quarantine required status?",
        "options": {"A": "True", "B": "False", "C": "Pending"}, # Yorp + Methane (default) = True
        "correct": "A"
    },
    {
        "attributes": ["patient.sensory_status"],
        "beliefs": {"treatment.active_prescription": "filinan"},
        "question": "If filinan is somehow prescribed, what is the sensory status?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"}, # Only snevox -> telepathic
        "correct": "A"
    },
    {
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"patient.sensory_status": "telepathic"},
        "question": "If they become explicitly telepathic, what staff is required?",
        "options": {"A": "standard_medic", "B": "psionic_handler", "C": "hazmat_team"},
        "correct": "B"
    },
    {
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"medical.staff_requirement": "hazmat_team", "treatment.active_prescription": "filinan"},
        "question": "If the staff requirement is hazmat_team and filinan is prescribed, what is the billing tier?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "A" # hazmat_team -> class_delta (filinan doesn't override)
    },
    {
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {"treatment.active_prescription": "none"},
        "question": "If no prescription is active, how many duration cycles?",
        "options": {"A": "0", "B": "5", "C": "12"},
        "correct": "A"
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"treatment.duration_cycles": 0},
        "question": "If the duration cycles are forced to 0, what is the recovery prospect?",
        "options": {"A": "terminal", "B": "guarded", "C": "excellent"},
        "correct": "A"
    },
    {
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"treatment.duration_cycles": 0},
        "question": "If the duration cycles are forced to 0, what is the recovery prospect?",
        "options": {"A": "terminal", "B": "guarded", "C": "excellent"},
        "correct": "A"
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
        "options": {"A": "safe", "B": "fatal_to_patient", "C": "symbiotic"},
        "correct": "A"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3)
        "attributes": ["treatment.snevox_danger_level"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine"},
        # Chlorine -> snevox_phase=liquid. Liquid snevox -> safe
        "question": "In a chlorine environment, what is the snevox danger level?",
        "options": {"A": "safe", "B": "fatal_to_patient", "C": "symbiotic"},
        "correct": "A"
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
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"
    },
    {   # Species(1) -> Quarantine(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"patient.organism_type": "Yorp"},
        # Yorp+Methane -> Quar=True -> hazmat_team
        "question": "For a Yorp patient, what medical staff is required by protocol?",
        "options": {"A": "hazmat_team", "B": "psionic_handler", "C": "standard_medic"},
        "correct": "A" # Quarantine overrides Psionic Handler
    },
    {   # Gas(1) -> Quarantine(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Qwerl"},
        # Chlorine+Qwerl -> Quar=True -> hazmat_team
        "question": "If a Qwerl is brought in under a chlorine atmosphere, who must staff them?",
        "options": {"A": "hazmat_team", "B": "standard_medic", "C": "psionic_handler"},
        "correct": "A"
    },
    {   # Sensory(1) -> Staff(2) -> Billing(3)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.sensory_status": "normal", "treatment.active_prescription": "filinan"},
        # staff -> standard_medic. billing -> class_standard
        "question": "If sensory status is normal and filinan is active, what is the billing tier?",
        "options": {"A": "class_standard", "B": "class_omega", "C": "class_delta"},
        "correct": "A"
    },
    {
        # Integrity(1) -> Duration(2) -> Recovery(3)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"treatment.active_prescription": "snevox", "patient.organ_integrity": "volatile"},
        # active=snevox + volatile -> duration=12. staff=psionic (bc snevox=telepathic). 
        # Duration>10 AND staff=hazmat -> guarded. But staff is psionic -> excellent.
        "question": "With a volatile integrity and active snevox, what is the recovery prospect?",
        "options": {"A": "excellent", "B": "guarded", "C": "terminal"},
        "correct": "A"
    },
    {   # Prescription(1) -> Sensory(2) -> Staff(3)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"treatment.active_prescription": "zyxostin", "patient.organism_type": "Glerps"},
        # zyxostin -> normal -> standard_medic
        "question": "If zyxostin is prescribed manually, who staffs the ward?",
        "options": {"A": "standard_medic", "B": "hazmat_team", "C": "psionic_handler"},
        "correct": "A"
    },
    {   # Prescription(1) -> Duration(2) -> Recovery(3)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"treatment.active_prescription": "none"},
        # none -> duration=0 -> terminal
        "question": "If no prescription can be found (active = none), what is the recovery prospect?",
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
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        # 4.5+Glerps -> volatile. Volatile+Zyxostin+Glerps -> symbiotic hazard. Active -> zyxostin.
        "question": "When pressure rises to 4.5, what compound is ultimately prescribed?",
        "options": {"A": "zyxostin", "B": "snevox", "C": "none"},
        "correct": "A"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"atmosphere.dominant_gas": "xenon", "patient.organ_integrity": "stable"},
        # Xenon -> F(vapor, safe), Z(crystalline, safe), S(vapor, safe). Glerps priority: F->Z->S. -> filinan
        "question": "In a xenon atmosphere with stable integrity, what is prescribed?",
        "options": {"A": "filinan", "B": "snevox", "C": "zyxostin"},
        "correct": "A"
    },
    {   # Species(1) -> Quarantine(2) -> Staff(3) -> Billing(4)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Qwerl", "atmosphere.dominant_gas": "chlorine"},
        # Q+Chlorine -> Quar=True -> hazmat -> class_delta 
        # (Wait, Qwerl+Chlorine snevox=liquid(safe). Prescription=snevox. snevox -> class_omega overrules!). Let's change snevox priority or prescription.
        "question": "For a Qwerl patient in a chlorine environment where snevox is active, what is the tier?",
        "options": {"A": "class_omega", "B": "class_delta", "C": "class_standard"},
        "correct": "A"
    },
    {   # Same chain but avoiding snevox override
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Yorp", "treatment.active_prescription": "filinan"},
        # Yorp+Methane -> Quar=True -> hazmat. active=filinan -> normal. Staff=hazmat -> class_delta.
        "question": "If a Yorp is forced onto filinan, what does their billing class become?",
        "options": {"A": "class_delta", "B": "class_omega", "C": "class_standard"},
        "correct": "A"
    },
    {   # Hazard(1) -> Prescription(2) -> Sensory(3) -> Staff(4)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"treatment.filinan_hazard": "safe"},
        # Glerps F is safe -> filinan -> normal -> standard_medic
        "question": "If filinan hazard is declared safe, who staffs the room?",
        "options": {"A": "standard_medic", "B": "psionic_handler", "C": "hazmat_team"},
        "correct": "A"
    },
    {   # Hazard(1) -> Prescription(2) -> Duration(3) -> Recovery(4)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"treatment.snevox_hazard": "fatal_to_patient", "treatment.zyxostin_hazard": "fatal_to_patient", "treatment.filinan_hazard": "fatal_to_patient"},
        # all fatal -> none -> duration 0 -> terminal
        "question": "If all hazards are deemed fatal_to_patient, what is the patient's prospect?",
        "options": {"A": "terminal", "B": "excellent", "C": "guarded"},
        "correct": "A"
    },
    {   # Species(1) -> Hazard(2) -> Prescription(3) -> Sensory(4)
        "attributes": ["patient.sensory_status"],
        "beliefs": {"patient.organism_type": "Qwerl"},
        # Qwerl+Methane. S(vapor)-fatal, Z(plasma)-safe, F(plasma)-fatal. S->Z->F. Z is safe -> zyxostin -> normal.
        "question": "A Qwerl checks in under methane. What sensory status will they exhibit post-medication?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"
    },
    {   # Pressure(1) -> Integrity(2) -> Duration(3) -> Recovery(4)  (actually Prescription(4) if symbiotic)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        # 4.5 -> volatile -> symbiotic(zyxostin) -> miraculous
        "question": "Under 4.5 pressure, a biological singularity occurs. What is the prospect?",
        "options": {"A": "miraculous", "B": "terminal", "C": "excellent"},
        "correct": "A"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4)
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Glerps"},
        # Chlorine -> S=liquid, Z=crystalline, F=plasma. 
        # Glerps F=fatal(plasma). Z=fatal(explode). S=safe(liquid). F->Z->S -> Snevox
        "question": "Under a chlorine atmosphere, which prescription does the Glerp receive?",
        "options": {"A": "snevox", "B": "zyxostin", "C": "filinan"},
        "correct": "A"
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
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        # 4.5 -> volatile -> symbiotic(zyxostin) -> zyxostin -> normal
        "question": "At 4.5 ambient pressure causing extreme volatility, what is their sensory status?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Sensory(5)
        "attributes": ["patient.sensory_status"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        # Xenon -> F(vapor,safe) -> filinan -> normal
        "question": "When xenon floods the room, what sensory side effect is caused by the new meds?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Duration(5)
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        # 4.5 -> volatile -> symbiotic -> zyxostin -> duration 5
        "question": "At 4.5 pressure, how many cycles does the symbiotic reaction take?",
        "options": {"A": "5", "B": "12", "C": "0"},
        "correct": "A"
    },
    {   # Gas(1) -> Phase(2) -> Hazard(3) -> Prescription(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        # xen -> filinan -> class_standard
        "question": "Xenon causes a shift in prescription. What does the final bill look like?",
        "options": {"A": "class_standard", "B": "class_omega", "C": "class_delta"},
        "correct": "A"
    },
    {   # Species(1) -> Hazard(2) -> Prescription(3) -> Sensory(4) -> Staff(5)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {"patient.organism_type": "Qwerl"},
        # Qwerl+Methane -> Z(plasma,safe) -> zyxostin -> normal -> standard
        "question": "A Qwerl walks in. Which team handles them under default methane pressure?",
        "options": {"A": "standard_medic", "B": "hazmat_team", "C": "psionic_handler"},
        "correct": "A"
    },
    {   # Pressure(1) -> Integrity(2) -> Hazard(3) -> Prescription(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        # 4.5 -> zyxostin -> class_standard
        "question": "If pressure forces a biological singularity using zyxostin, how is it billed?",
        "options": {"A": "class_standard", "B": "class_omega", "C": "class_delta"},
        "correct": "A"
    },
    {   # Symptoms(1) -> Prescription(2) -> Sensory(3) -> Staff(4) -> Billing(5)
        "attributes": ["clinic.billing_tier"],
        "beliefs": {"patient.organism_type": "Yorp", "patient.symptoms": ["acid_sweat"], "atmosphere.dominant_gas": "xenon"},
        # Yorp+Xenon+acid_sweat -> filinan -> standard -> class_standard
        "question": "A Yorp with acid sweat under Xenon. What is their final billing class?",
        "options": {"A": "class_standard", "B": "class_delta", "C": "class_omega"},
        "correct": "A"
    },
    {   # Gas(1) -> Quarantine(2) -> Staff(3) -> Recovery(4) [Actually Duration+Staff->Recovery]
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.dominant_gas": "methane", "patient.organism_type": "Yorp", "treatment.duration_cycles": 15},
        # Methane+Yorp -> Quar=True -> hazmat. Dur>10 + hazmat -> guarded
        "question": "A Yorp on a 15-cycle treatment in Methane. What is the prospect?",
        "options": {"A": "guarded", "B": "excellent", "C": "miraculous"},
        "correct": "A"
    },
    {   # Pressure(1) -> Integrity(2) -> Duration(3) ...  let's do:
        # Pressure(1)->Integrity(2)->Hazard(3)->Prescription(4)->Recovery(5)
        "attributes": ["patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 4.1, "patient.organism_type": "Glerps"},
        # 4.1+Glerps -> volatile -> symbiotic(zyxostin) -> miraculous
        "question": "At 4.1 pressure for a Glerp, what is the recovery prospect?",
        "options": {"A": "miraculous", "B": "excellent", "C": "terminal"},
        "correct": "A"
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
        "options": {"A": "brittle", "B": "stable", "C": "volatile"},
        "correct": "B"  # 2.0 -> stable
    },
    {   # Add symptoms (unrelated input) -> organ_integrity should stay same
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0, "patient.symptoms": ["fever"]},
        "question": "After adding symptoms, what is organ integrity?",
        "options": {"A": "brittle", "B": "stable", "C": "volatile"},
        "correct": "B"  # Maintained: symptoms don't affect organ_integrity
    },
    {   # Query: active_prescription with just pressure
        "attributes": ["treatment.active_prescription"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0},
        "question": "At 2.0 pressure, what prescription is active?",
        "options": {"A": "filinan", "B": "snevox", "C": "zyxostin"},
        "correct": "A"  # Glerps default: filinan
    },
    {   # Add organism type (different input) -> pressure-derived integral should stay same
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 2.0, "patient.organism_type": "Yorp"},
        "question": "With Yorp organism type added, what is organ integrity?",
        "options": {"A": "brittle", "B": "stable", "C": "volatile"},
        "correct": "B"  # Maintained: 2.0 pressure is stable regardless of organism
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
        "options": {"A": "crystalline", "B": "plasma", "C": "vapor"},
        "correct": "A"  # Maintained: phase depends on gas only, not pressure
    },
    {   # Query: sensory_status from prescription
        "attributes": ["patient.sensory_status"],
        "beliefs": {"treatment.active_prescription": "filinan"},
        "question": "With filinan prescribed, what is sensory status?",
        "options": {"A": "normal", "B": "telepathic", "C": "blind"},
        "correct": "A"  # Only snevox -> telepathic
    },
    {   # Add organism info (different chain) -> sensory should unchanged
        "attributes": ["patient.sensory_status"],
        "beliefs": {"treatment.active_prescription": "filinan", "patient.organism_type": "Glerps"},
        "question": "After specifying organism, what is sensory status?",
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
        "options": {"A": "True", "B": "False", "C": "Changed"},
        "correct": "B"  # Maintained: quarantine depends on gas+organism pair only
    }
]
