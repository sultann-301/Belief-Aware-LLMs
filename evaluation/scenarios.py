"""
Evaluation Scenarios for Belief-Aware LLMs.

Contains the predefined scenarios for each domain, including:
  - Baseline deterministic rules [RULES]
  - Initial beliefs
  - Sequential MCQ evaluation turns
"""

# =====================================================================
# LOAN DOMAIN
# =====================================================================

LOAN_RULES = """\
[RULES]
1. loan.adjusted_income = applicant.income - (applicant.dependents * 500)
2. loan.credit_score_effective = applicant.credit_score + (50 if applicant.co_signer else 0)
3. loan.high_risk_flag = True if applicant.debt_ratio >= 0.3 else False
4. loan.applicant_prequalified = True ONLY IF loan.adjusted_income >= loan.min_income AND loan.credit_score_effective >= loan.min_credit AND applicant.debt_ratio < loan.max_debt_ratio AND applicant.employment_status != 'unemployed' AND NOT (applicant.bankruptcy_history == True AND applicant.employment_duration_months < 24)
5. loan.rate_tier = "preferred" if loan.credit_score_effective >= 750 else "standard" (None if not loan.applicant_prequalified)
6. loan.max_amount = 100000 if applicant.has_collateral else 30000 (0 if not loan.applicant_prequalified)
7. loan.application_status = "approved" if loan.applicant_prequalified and applicant.loan_amount_requested <= loan.max_amount. Otherwise "denied_amount_exceeded" or "denied_ineligible"
8. loan.requires_insurance = True if loan.high_risk_flag AND loan.application_status == "approved" else False
9. loan.review_queue = "manual_review" if loan.high_risk_flag else "auto_approve" ("rejected" if denied)
10. loan.base_interest_rate = 4.5 if loan.rate_tier == "preferred" else 6.5. Add +1.0 if loan.requires_insurance. (None if not loan.applicant_prequalified)
"""

LOAN_INITIAL_BELIEFS = {
    "applicant.income": 6000,
    "applicant.credit_score": 720,
    "applicant.co_signer": False,
    "applicant.debt_ratio": 0.20,
    "applicant.employment_status": "employed",
    "applicant.bankruptcy_history": False,
    "applicant.employment_duration_months": 36,
    "applicant.has_collateral": False,
    "applicant.loan_amount_requested": 10_000,
    "applicant.dependents": 2,
    "loan.min_income": 5000,
    "loan.min_credit": 650,
    "loan.max_debt_ratio": 0.4,
}

LOAN_TURNS = [
    {
        "entities": "loan",
        "beliefs": {},
        "question": "What is the application status and review queue?",
        "options": {
            "A": "denied_ineligible, rejected",
            "B": "approved, auto_approve",
            "C": "approved, manual_review",
        },
        "correct": "B",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.debt_ratio": 0.35},
        "question": "What is the required insurance status and review queue?",
        "options": {
            "A": "requires_insurance = True, review_queue = manual_review",
            "B": "requires_insurance = False, review_queue = auto_approve",
            "C": "requires_insurance = True, review_queue = auto_approve",
        },
        "correct": "A",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.credit_score": 740},
        "question": "What is the current application status?",
        "options": {
            "A": "preferred_approved",
            "B": "denied",
            "C": "approved",
        },
        "correct": "C",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.co_signer": True},
        "question": "What is the new base interest rate?",
        "options": {
            "A": "5.5",
            "B": "7.5",
            "C": "4.5",
        },
        "correct": "A",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.has_collateral": True},
        "question": "What are the final application status and base interest rate?",
        "options": {
            "A": "approved, 5.5",
            "B": "pending_manager_approval, 5.5",
            "C": "approved, 4.5",
        },
        "correct": "A",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.employment_status": "unemployed"},
        "question": "What is the application status and base interest rate?",
        "options": {
            "A": "approved, 5.5",
            "B": "denied_ineligible, None",
            "C": "denied_ineligible, 6.5",
        },
        "correct": "B",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.employment_status": "employed"},
        "question": "What is the maximum loan amount and application status?",
        "options": {
            "A": "100000, approved",
            "B": "30000, approved",
            "C": "100000, denied_amount_exceeded",
        },
        "correct": "A",
    },
    {
        "entities": "applicant, loan",
        "beliefs": {"applicant.dependents": 3},
        "question": "What is the adjusted income and application status?",
        "options": {
            "A": "5000, approved",
            "B": "4500, denied_ineligible",
            "C": "3000, denied_ineligible",
        },
        "correct": "B",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.loan_amount_requested": 20_000},
        "question": "What is the application status?",
        "options": {
            "A": "approved",
            "B": "denied_amount_exceeded",
            "C": "denied_ineligible",
        },
        "correct": "C",
    },
    {
        "entities": "loan",
        "beliefs": {"applicant.income": 7000},
        "question": "What is the application status?",
        "options": {
            "A": "approved",
            "B": "denied_amount_exceeded",
            "C": "denied_ineligible",
        },
        "correct": "A",
    },
]


# =====================================================================
# ALIEN CLINIC DOMAIN
# =====================================================================

ALIEN_RULES = """\
[RULES]
1. patient.organ_integrity = "volatile" if ambient_pressure > 5.0 and organism_type == "Yorp". "volatile" if ambient_pressure > 4.0 and organism_type == "Glerps". "brittle" if ambient_pressure > 3.0. Otherwise "stable".
2. treatment.zyxostin_phase = "plasma" IF dominant_gas == "methane" ELSE "crystalline". treatment.filinan_phase = "vapor" IF dominant_gas == "xenon" ELSE "plasma". treatment.snevox_phase = "liquid" IF dominant_gas == "chlorine" ELSE "vapor".
3. hazards: If organism_type + compound has explode constraint (Glerps+zyxostin, Yorp+filinan, Qwerl+snevox), then if organ_integrity is "volatile", hazard is "symbiotic" (Biological Singularity). Else hazard is "LETHAL". If phase="plasma" and filinan -> "LETHAL". If phase="vapor" and snevox and Qwerl -> "LETHAL". If organ_integrity="volatile" -> "LETHAL". Else "safe". (hazards are treatment.{compound}_hazard)
4. treatment.active_prescription = MIRACLE OVERRIDE: If any hazard is "symbiotic", pick it immediately ignoring priority. SYMPTOM PRIORITIES: Glerps: if "fever" and "spasms" in symptoms (snevox -> zyxostin -> filinan), if "fever" in symptoms (zyxostin -> snevox -> filinan), else (filinan -> zyxostin -> snevox). Yorp: if "acid_sweat" in symptoms (filinan -> snevox -> zyxostin), else (zyxostin -> snevox -> filinan). Qwerl: (snevox -> zyxostin -> filinan). Select highest priority safe. Else none.
5. patient.sensory_status = "telepathic" if active_prescription == "snevox", else "normal".
6. patient.quarantine_required = True if (dominant_gas == "chlorine" AND organism_type == "Qwerl") or (dominant_gas == "methane" AND organism_type == "Yorp"), else False.
7. treatment.duration_cycles = 12 if active_prescription == "snevox" and organ_integrity == "volatile". 0 if active_prescription == "none". Otherwise 5.
8. medical.staff_requirement = "hazmat_team" if quarantine_required == True. "psionic_handler" if sensory_status == "telepathic". Else "standard_medic". (Quarantine overrides Psionic).
9. patient.recovery_prospect = "miraculous" if hazard is "symbiotic". "guarded" if duration_cycles > 10 and staff_requirement == "hazmat_team". "terminal" if duration_cycles == 0. Else "excellent". (hazards are treatment.{compound}_hazard)
10. clinic.billing_tier = "class_omega" if staff_requirement == "psionic_handler" or active_prescription == "snevox". "class_delta" if staff_requirement == "hazmat_team". Otherwise "class_standard".
"""

ALIEN_INITIAL_BELIEFS = {
    "patient.organism_type": "Glerps",
    "patient.symptoms": [],
    "atmosphere.ambient_pressure": 3.5,
    "atmosphere.dominant_gas": "methane",
}

ALIEN_INITIAL_BELIEFS_CF = {
    "patient.organism_type": "Qwerl",
    "atmosphere.dominant_gas": "xenon",
    "atmosphere.ambient_pressure": 5.5,
    "patient.symptoms": ["acid_sweat"],
}

# --- Alien Clinic: Turns ---
ALIEN_TURNS_BASIC = [
    {
        "entities": "treatment, clinic",
        "beliefs": {},
        "question": "What is the active prescription and billing tier?",
        "options": {
            "A": "snevox, class_omega",
            "B": "filinan, class_standard",
            "C": "none, class_omega",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, clinic",
        "beliefs": {"patient.symptoms": ["fever", "spasms"]},
        "question": "What is the new active prescription and billing tier?",
        "options": {
            "A": "snevox, class_omega",
            "B": "zyxostin, class_standard",
            "C": "none, class_standard",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, clinic",
        "beliefs": {"patient.symptoms": ["fever"]},
        "question": "What is the active prescription?",
        "options": {
            "A": "snevox",
            "B": "zyxostin",
            "C": "filinan",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "zyxostin, miraculous",
            "B": "none, terminal",
            "C": "snevox, excellent",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.symptoms": []},
        "question": "What is the recovery prospect?",
        "options": {
            "A": "miraculous",
            "B": "excellent",
            "C": "terminal",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, medical",
        "beliefs": {"patient.organism_type": "Yorp"},
        "question": "What is the active prescription and staff requirement?",
        "options": {
            "A": "none, hazmat_team",
            "B": "zyxostin, hazmat_team",
            "C": "zyxostin, standard_medic",
        },
        "correct": "B",
    },
    {
        "entities": "treatment, medical",
        "beliefs": {"patient.symptoms": ["acid_sweat"]},
        "question": "What is the new prescription and staff requirement?",
        "options": {
            "A": "snevox, hazmat_team",
            "B": "snevox, psionic_handler",
            "C": "filinan, hazmat_team",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 5.5},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "none, terminal",
            "B": "filinan, miraculous",
            "C": "snevox, terminal",
        },
        "correct": "B",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.dominant_gas": "xenon"},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "filinan, miraculous",
            "B": "zyxostin, excellent",
            "C": "snevox, guarded",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.organism_type": "Qwerl"},
        "question": "What is the active prescription and recovery prospect?",
        "options": {
            "A": "zyxostin, excellent",
            "B": "filinan, miraculous",
            "C": "none, terminal",
        },
        "correct": "A",
    },
]

ALIEN_TURNS_CF = [
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 2.0},
        "question": "Under the latest pressure condition, what is the organ integrity?",
        "options": {
            "A": "stable",
            "B": "brittle",
            "C": "volatile",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.organism_type": "Glerps", "patient.symptoms": []},
        "question": "Given the patient species and symptom clearance in the latest belief update, what is the active prescription at this low pressure?",
        "options": {
            "A": "filinan",
            "B": "snevox",
            "C": "zyxostin",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.dominant_gas": "methane"},
        "question": "Under the latest atmospheric gas, what is treatment.zyxostin_phase?",
        "options": {
            "A": "plasma",
            "B": "vapor",
            "C": "crystalline",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 4.1},
        "question": "At the current pressure and gas, is treatment.zyxostin_hazard symbiotic?",
        "options": {
            "A": "Yes",
            "B": "No, it is LETHAL",
            "C": "No, it is safe",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, clinic",
        "beliefs": {"patient.symptoms": ["fever", "spasms"]},
        "question": "Given the current symptoms and resulting medication, what is the billing tier?",
        "options": {
            "A": "class_standard",
            "B": "class_delta",
            "C": "class_omega",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.organism_type": "Qwerl"},
        "question": "Given the species transformation in the latest update, what is the active prescription?",
        "options": {
            "A": "snevox",
            "B": "zyxostin",
            "C": "filinan",
        },
        "correct": "B",
    },
    {
        "entities": "treatment, medical",
        "beliefs": {"atmosphere.dominant_gas": "chlorine"},
        "question": "Does the current gas and species combination necessitate specialized hazmat staffing?",
        "options": {
            "A": "Yes",
            "B": "No, psionic_handler only",
            "C": "No, standard_medic only",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, clinic",
        "beliefs": {"patient.symptoms": []},
        "question": "After clearing all symptoms, has the billing tier returned to the standard class?",
        "options": {
            "A": "Yes, class_standard",
            "B": "No, it stayed class_delta",
            "C": "No, it is class_omega",
        },
        "correct": "B",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"atmosphere.ambient_pressure": 5.5},
        "question": "At the highest pressure recorded so far, what is the recovery prospect for the current species?",
        "options": {
            "A": "excellent",
            "B": "miraculous",
            "C": "terminal",
        },
        "correct": "A",
    },
    {
        "entities": "treatment, patient",
        "beliefs": {"patient.organism_type": "Glerps"},
        "question": "Given the substitution in the latest update, what is the recovery prospect?",
        "options": {
            "A": "excellent",
            "B": "miraculous",
            "C": "terminal",
        },
        "correct": "B",
    },
]

ALIEN_TURNS = ALIEN_TURNS_BASIC + ALIEN_TURNS_CF


# =====================================================================
# CRIME SCENE DOMAIN
# =====================================================================

CRIME_RULES = """\
[RULES]
1. suspect_a.admissible_evidence = "none" if suspect_a.evidence_logger == "officer_smith" and officer_smith.status == "suspended" else suspect_a.home_evidence.
2. suspect_a.status = "prime_suspect" if suspect_a.admissible_evidence != "none" else "cleared".
3. suspect_b.testimonial_alibi = "broken" if suspect_b.alibi_partner == "suspect_a" and suspect_a.status == "prime_suspect" else "confirmed".
4. suspect_b.digital_alibi = "confirmed" if case.cctv_status == "active" and case.cctv_subject == "suspect_b" else "none".
5. suspect_b.final_alibi = "confirmed" if suspect_b.digital_alibi == "confirmed" else suspect_b.testimonial_alibi.
6. suspect_b.status = "prime_suspect" if suspect_b.final_alibi == "broken" else "cleared".
7. suspect_a.motive_verified = True if suspect_a.financial_records == "debt" and case.warrant_status == True else False.
8. suspect_b.motive_verified = True if suspect_b.relation_to_victim == "enemy" else False.
9. case.theory = "collusion" if suspect_a.status == "prime_suspect" and suspect_b.status == "prime_suspect" else ("solo_perpetrator" if suspect_a.status == "prime_suspect" or suspect_b.status == "prime_suspect" else "unsolved").
10. case.lead_suspect = "none" if case.theory == "unsolved" else ("suspect_a" if case.theory == "solo_perpetrator" and suspect_a.status == "prime_suspect" else ("suspect_b" if case.theory == "solo_perpetrator" and suspect_b.status == "prime_suspect" else ("suspect_a" if suspect_a.motive_verified == True and suspect_b.motive_verified == False else ("suspect_b" if suspect_b.motive_verified == True and suspect_a.motive_verified == False else "both")))).
"""

CRIME_INITIAL_BELIEFS = {
    "officer_smith.status": "active",
    "suspect_a.home_evidence": "gun",
    "suspect_a.evidence_logger": "officer_smith",
    "suspect_a.financial_records": "clean",
    "suspect_b.relation_to_victim": "stranger",
    "suspect_b.alibi_partner": "suspect_a",
    "case.warrant_status": False,
    "case.cctv_status": "corrupted",
    "case.cctv_subject": "none",
}

CRIME_TURNS = [
    {
        "entities": "case",
        "beliefs": {},
        "question": "What is the initial case theory and lead suspect?",
        "options": {
            "A": "unsolved, none",
            "B": "collusion, both",
            "C": "solo_perpetrator, suspect_a",
        },
        "correct": "B",
    },
    {
        "entities": "case, suspect_a",
        "beliefs": {"case.warrant_status": True, "suspect_a.financial_records": "debt"},
        "question": "After discovering debt via a warrant, who is the lead suspect?",
        "options": {
            "A": "suspect_a",
            "B": "suspect_b",
            "C": "both",
        },
        "correct": "A",
    },
    {
        "entities": "case",
        "beliefs": {"suspect_b.relation_to_victim": "enemy"},
        "question": "With both motives verified, who is the lead suspect?",
        "options": {
            "A": "suspect_a",
            "B": "suspect_b",
            "C": "both",
        },
        "correct": "C",
    },
    {
        "entities": "suspect_a, suspect_b, case",
        "beliefs": {"officer_smith.status": "suspended"},
        "question": "Officer Smith is suspended. What is Suspect A's status, Case Theory, and Lead Suspect?",
        "options": {
            "A": "cleared, unsolved, none",
            "B": "prime_suspect, collusion, both",
            "C": "cleared, solo_perpetrator, suspect_b",
        },
        "correct": "A",
    },
    {
        "entities": "case",
        "beliefs": {"suspect_a.evidence_logger": "officer_jones"},
        "question": "After logging the evidence with a new active officer, what is the case theory?",
        "options": {
            "A": "unsolved",
            "B": "solo_perpetrator",
            "C": "collusion",
        },
        "correct": "C",
    },
    {
        "entities": "suspect_b, case",
        "beliefs": {"case.cctv_status": "active", "case.cctv_subject": "suspect_b"},
        "question": "Given the new CCTV evidence clearing Suspect B dynamically, what is Suspect B's status and the case theory?",
        "options": {
            "A": "cleared, solo_perpetrator",
            "B": "prime_suspect, collusion",
            "C": "cleared, unsolved",
        },
        "correct": "A",
    },
    {
        "entities": "suspect_b, case",
        "beliefs": {"case.cctv_status": "corrupted"},
        "question": "If the CCTV is discovered to be corrupted, what is the final alibi for Suspect B and the lead suspect?",
        "options": {
            "A": "confirmed, suspect_a",
            "B": "broken, both",
            "C": "broken, suspect_b",
        },
        "correct": "B",
    },
    {
        "entities": "suspect_a, case",
        "beliefs": {"suspect_a.home_evidence": "none"},
        "question": "Without the home evidence, what is Suspect A's status and the case theory?",
        "options": {
            "A": "prime_suspect, collusion",
            "B": "cleared, solo_perpetrator",
            "C": "cleared, unsolved",
        },
        "correct": "C",
    },
    {
        "entities": "case",
        "beliefs": {"suspect_a.home_evidence": "gun"},
        "question": "If the gun is found again, what is the case theory?",
        "options": {
            "A": "unsolved",
            "B": "solo_perpetrator",
            "C": "collusion",
        },
        "correct": "C",
    },
    {
        "entities": "case",
        "beliefs": {"case.warrant_status": False},
        "question": "If the warrant is thrown out, who is the lead suspect?",
        "options": {
            "A": "suspect_b",
            "B": "suspect_a",
            "C": "both",
        },
        "correct": "A",
    },
]

# =====================================================================
# THORNCRESTER TAXONOMY
# =====================================================================

THORNCRESTER_RULES = """[RULES]
R1: ecological_stress -> "high" if drought+scarcity, else "nominal"
R2: expressed_diet -> "scavenger" if stress is high, else genetic_diet
R3: plumage_color -> "dull_grey" if scavenger, else "crimson"
R4: expressed_structure -> "survival_swarm" if stress is high, else genetic_structure
R5: territory_behavior -> "hyper_aggressive" if survival_swarm + scarcity, else "peaceful"
R6: metabolic_state -> "starving" if fructose_processor + adult_diet != frugivore, else "thriving"
R7: development -> "arrested" if starving, else "maturing"
R8: bloom_status -> "active_bloom" if dull_grey + drought, else "dormant"
R9: parasitic_load -> "lethal" if active_bloom, else "harmless"
R10: mortality_risk -> "critical" if lethal OR hyper_aggressive, else "low"
"""

THORNCRESTER_INITIAL_BELIEFS = {
    "environment.weather_pattern": "stable",
    "environment.food_scarcity": False,
    "adult_thorncrester.genetic_diet": "frugivore",
    "thorncrester_flock.genetic_structure": "matriarchal_pairs",
    "juvenile_thorncrester.digestive_enzyme": "fructose_processor",
}

THORNCRESTER_TURNS = [
    {
        "entities": "adult_thorncrester",
        "beliefs": {},
        "question": "Given the stable environment, what is the current plumage color of the adult Thorncrester?",
        "options": {"A": "dull_grey", "B": "crimson", "C": "azure"},
        "correct": "B",
    },
    {
        "entities": "environment, adult_thorncrester",
        "beliefs": {"environment.weather_pattern": "drought"},
        "question": "A drought has begun. If food is still plentiful (no scarcity), what is the ecological stress level?",
        "options": {"A": "nominal", "B": "high", "C": "critical"},
        "correct": "A",
    },
    {
        "entities": "environment, adult_thorncrester",
        "beliefs": {"environment.food_scarcity": True},
        "question": "Food scarcity has hit during the drought. What is the adult's expressed diet now?",
        "options": {"A": "frugivore", "B": "scavenger", "C": "insectivore"},
        "correct": "B",
    },
    {
        "entities": "adult_thorncrester, juvenile_thorncrester",
        "beliefs": {},
        "question": "The adults have shifted to scavenging. What is the metabolic state of the juvenile (fructose processor) offspring?",
        "options": {"A": "thriving", "B": "starving", "C": "dormant"},
        "correct": "B",
    },
    {
        "entities": "adult_thorncrester, feather_mite, environment",
        "beliefs": {},
        "question": "With the plumage turned dull_grey during a drought, what is the status of the feather mite bloom?",
        "options": {"A": "dormant", "B": "active_bloom", "C": "lethal"},
        "correct": "B",
    },
    {
        "entities": "feather_mite, thorncrester_flock, adult_thorncrester",
        "beliefs": {},
        "question": "Between the lethal parasitic load and the social aggression, what is the mortality risk?",
        "options": {"A": "low", "B": "moderate", "C": "critical"},
        "correct": "C",
    },
    {
        "entities": "environment, adult_thorncrester",
        "beliefs": {"environment.weather_pattern": "stable"},
        "question": "The rains have returned (stable). What has happened to the adult's plumage color?",
        "options": {"A": "remains dull_grey", "B": "reverts to crimson", "C": "turns azure"},
        "correct": "B",
    },
    {
        "entities": "environment, adult_thorncrester",
        "beliefs": {"environment.food_scarcity": False},
        "question": "Food is now abundant again. What is the current mortality risk for the adults?",
        "options": {"A": "low", "B": "critical", "C": "moderate"},
        "correct": "A",
    },
    {
        "entities": "juvenile_thorncrester, adult_thorncrester",
        "beliefs": {"juvenile_thorncrester.digestive_enzyme": "general_processor"},
        "question": "A subspecies with a 'general_processor' enzyme is found. If the adults were scavenging, what would this juvenile's development status be?",
        "options": {"A": "arrested", "B": "maturing", "C": "unknown"},
        "correct": "B",
    },
    {
        "entities": "environment, thorncrester_flock, adult_thorncrester",
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        "question": "Stress is high again. What is the currently expressed social structure of the flock?",
        "options": {"A": "matriarchal_pairs", "B": "solitary", "C": "survival_swarm"},
        "correct": "C",
    },
]
