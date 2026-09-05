"""
Hard-tier evaluation scenarios for the four belief-aware domains.

These sets focus on Hard Belief Revision (Masking, Shadowing, and Unmasking).
Each scenario is a 10-turn temporal sequence (`accumulate_prior_beliefs=True`)
that tests whether the model understands the hierarchical dominance of rules across time.
"""

# =====================================================================
# LOAN DOMAIN - HARD BELIEF REVISION
# Masking Variable: bankruptcy_history (Forces Prequalified = False -> Max Amount = 0)
# Shadow Updates: We improve income, collateral, credit score.
# =====================================================================
LOAN_HARD_TURNS = [
    {
        # T1 - Baseline Success
        "attributes": ["loan.application_status", "loan.rate_tier"],
        "beliefs": {
            "applicant.income": 8000,
            "applicant.dependents": 0,
            "applicant.credit_score": 750,
            "applicant.co_signer": False,
            "applicant.debt_ratio": 0.20,
            "applicant.employment_status": "employed",
            "applicant.employment_duration_months": 36,
            "applicant.bankruptcy_history": False,
            "applicant.has_collateral": False,
            "applicant.loan_amount_requested": 25000,
        },
        "question": "What is the application status and rate tier for this strong applicant?",
        "options": {"A": "approved, preferred", "B": "denied_ineligible, standard", "C": "approved, standard"},
        "correct": "A",
    },
    {
        # T2 - Minor degradation
        "attributes": ["loan.requires_insurance", "loan.review_queue"],
        "beliefs": {
            "applicant.debt_ratio": 0.35, # Pushes high_risk_flag = True -> manual_review
        },
        "question": "Debt ratio increases to 0.35. Does the loan require insurance and what is the review queue?",
        "options": {"A": "True, manual_review", "B": "False, auto_approve", "C": "False, manual_review"},
        "correct": "A",
    },
    {
        # T3 - The Mask (Bankruptcy)
        "attributes": ["loan.applicant_prequalified", "loan.application_status"],
        "beliefs": {
            "applicant.bankruptcy_history": True,
        },
        "question": "A past bankruptcy is discovered. What are the prequalified status and application status now?",
        "options": {"A": "False, denied_ineligible", "B": "True, manual_review", "C": "False, denied_amount_exceeded"},
        "correct": "A",
    },
    {
        # T4 - Shadow Update 1 (Collateral added)
        "attributes": ["loan.max_amount", "loan.application_status"],
        "beliefs": {
            "applicant.has_collateral": True, # Should normally boost max_amount to 100k, but bankruptcy masks it.
        },
        "question": "The applicant secures collateral. Does this change the max loan amount and application status?",
        "options": {"A": "100000, approved", "B": "0, denied_ineligible", "C": "30000, manual_review"},
        "correct": "B",
    },
    {
        # T5 - Shadow Update 2 (Income massive boost)
        "attributes": ["loan.applicant_prequalified", "loan.application_status"],
        "beliefs": {
            "applicant.income": 20000, # Massive income, but prequal still fails due to bankruptcy.
        },
        "question": "The applicant's income surges to 20,000. What is their prequalified status and application status?",
        "options": {"A": "True, approved", "B": "False, denied_ineligible", "C": "True, manual_review"},
        "correct": "B",
    },
    {
        # T6 - Shadow Update 3 (Co-signer added)
        "attributes": ["loan.base_interest_rate", "loan.application_status"],
        "beliefs": {
            "applicant.co_signer": True, # Boosts credit score, but loan is still denied (rate=None).
        },
        "question": "A co-signer is added. What is the base interest rate and application status?",
        "options": {"A": "4.5, approved", "B": "None, denied_ineligible", "C": "6.5, denied_ineligible"},
        "correct": "B",
    },
    {
        # T7 - The Unmask (Bankruptcy drops off)
        "attributes": ["loan.application_status", "loan.max_amount"],
        "beliefs": {
            "applicant.bankruptcy_history": False,
        },
        "question": "The bankruptcy falls off the record. Considering the high income and collateral added previously, what are the application status and max amount?",
        "options": {"A": "approved, 100000", "B": "denied_ineligible, 0", "C": "approved, 30000"},
        "correct": "A",
    },
    {
        # T8 - Unmasked State Verification
        "attributes": ["loan.review_queue", "loan.requires_insurance"],
        "beliefs": {
            "applicant.debt_ratio": 0.20, # Drops high risk flag
        },
        "question": "The debt ratio improves back to 0.20. What is the review queue and insurance requirement?",
        "options": {"A": "auto_approve, False", "B": "manual_review, True", "C": "auto_approve, True"},
        "correct": "A",
    },
    {
        # T9 - A New Mask (Unemployed)
        "attributes": ["loan.applicant_prequalified", "loan.application_status"],
        "beliefs": {
            "applicant.employment_status": "unemployed",
        },
        "question": "The applicant suddenly becomes unemployed. What happens to prequalification and application status?",
        "options": {"A": "True, approved", "B": "False, denied_ineligible", "C": "False, denied_amount_exceeded"},
        "correct": "B",
    },
    {
        # T10 - Shadow Update under new mask
        "attributes": ["loan.max_amount", "loan.application_status"],
        "beliefs": {
            "applicant.loan_amount_requested": 5000, # Dropping request doesn't help if unemployed.
        },
        "question": "They lower their request to just 5,000. Does this fix the max amount and application status?",
        "options": {"A": "100000, approved", "B": "0, denied_ineligible", "C": "30000, approved"},
        "correct": "B",
    }
]

# =====================================================================
# ALIEN CLINIC DOMAIN - HARD BELIEF REVISION
# Masking Variable: atmosphere.ambient_pressure (volatile organ_integrity)
# Shadow Updates: We change gases and symptoms, but symbiotic overrides everything.
# =====================================================================
ALIEN_HARD_TURNS = [
    {
        # T1 - Baseline Success (Safe snevox)
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "patient.organism_type": "Glerps",
            "atmosphere.ambient_pressure": 3.5, # brittle
            "atmosphere.dominant_gas": "methane",
            "patient.symptoms": ["fever"],
            "patient.quarantine_required": False,
            "patient.sensory_status": "normal",
        },
        "question": "With a brittle Glerps in methane, what are the active prescription and recovery prospect?",
        "options": {"A": "snevox, excellent", "B": "zyxostin, excellent", "C": "filinan, guarded"},
        "correct": "A",
    },
    {
        # T2 - The Mask (Pressure spikes -> volatile)
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5, # volatile -> zyxostin becomes symbiotic
        },
        "question": "Pressure spikes to 4.5, making organs volatile. What are the prescription and recovery prospect now?",
        "options": {"A": "zyxostin, miraculous", "B": "snevox, excellent", "C": "filinan, terminal"},
        "correct": "A",
    },
    {
        # T3 - Shadow Update 1 (Symptoms clear)
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "patient.symptoms": [], # Normally changes priority, but symbiotic zyxostin overrides symptom priority.
        },
        "question": "The fever clears up. Does this change the active prescription and recovery prospect?",
        "options": {"A": "zyxostin, miraculous", "B": "filinan, excellent", "C": "snevox, excellent"},
        "correct": "A",
    },
    {
        # T4 - Shadow Update 2 (Gas changes)
        "attributes": ["treatment.active_prescription", "clinic.billing_tier"],
        "beliefs": {
            "atmosphere.dominant_gas": "xenon", # Normally snevox phase = unknown, filinan = vapor. But zyxostin is symbiotic.
        },
        "question": "The gas shifts to xenon. What is the active prescription and resulting billing tier?",
        "options": {"A": "zyxostin, class_standard", "B": "filinan, class_standard", "C": "snevox, class_omega"},
        "correct": "A",
    },
    {
        # T5 - Shadow Update 3 (Quarantine required)
        "attributes": ["medical.staff_requirement", "clinic.billing_tier"],
        "beliefs": {
            "patient.quarantine_required": True, # Hazmat team -> billing class_omega
        },
        "question": "Quarantine is now required. How does this affect staff requirements and the billing tier for the zyxostin treatment?",
        "options": {"A": "hazmat_team, class_omega", "B": "standard_medic, class_standard", "C": "psionic_handler, class_omega"},
        "correct": "A",
    },
    {
        # T6 - The Unmask (Pressure drops)
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 2.5, # Back to brittle. Symbiotic override is gone.
        },
        "question": "Pressure drops back to 2.5, removing the volatility. What is the prescription and recovery prospect now?",
        "options": {"A": "filinan, guarded", "B": "zyxostin, miraculous", "C": "snevox, guarded"},
        # Explanation: brittle Glerps in xenon. No symptoms. Priority is filinan. filinan is safe.
        "correct": "A",
    },
    {
        # T7 - Secondary Mask (Organism Type shifts to Yorp)
        "attributes": ["treatment.active_prescription", "medical.staff_requirement"],
        "beliefs": {
            "patient.organism_type": "Yorp",
            "patient.symptoms": ["acid_sweat"], # Yorp priority: snevox -> zyxostin -> filinan
        },
        "question": "The organism mutates into a Yorp with acid sweat. What is the prescription and staff requirement?",
        "options": {"A": "snevox, hazmat_team", "B": "filinan, hazmat_team", "C": "zyxostin, standard_medic"},
        "correct": "A",
    },
    {
        # T8 - Shadow Update under Yorp (Gas change to chlorine)
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.dominant_gas": "chlorine", # Yorp + chlorine = snevox is fatal.
        },
        "question": "Gas changes to chlorine. Does the prescription change, and what is the recovery prospect?",
        "options": {"A": "zyxostin, excellent", "B": "snevox, terminal", "C": "filinan, excellent"},
        # snevox is fatal, so it falls back to zyxostin.
        "correct": "A",
    },
    {
        # T9 - The Terminal Mask (Pressure spikes for Yorp)
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "atmosphere.ambient_pressure": 5.5, # Yorp + volatile = zyxostin is fatal!
        },
        "question": "Pressure spikes, making the Yorp volatile. What happens to the prescription and recovery prospect?",
        "options": {"A": "filinan, excellent", "B": "zyxostin, terminal", "C": "none, terminal"},
        # snevox fatal (chlorine), zyxostin fatal (volatile). Only filinan is left, it's safe.
        "correct": "A",
    },
    {
        # T10 - Ultimate Failure (Sensory becomes telepathic)
        "attributes": ["medical.staff_requirement", "clinic.billing_tier"],
        "beliefs": {
            "patient.sensory_status": "telepathic",
        },
        "question": "The Yorp becomes telepathic. Who treats them and what is the billing tier?",
        "options": {"A": "psionic_handler, class_omega", "B": "hazmat_team, class_omega", "C": "standard_medic, class_standard"},
        # Quarantine (from T5) means hazmat_team, but telepathic means psionic_handler. Psionic overrides all.
        "correct": "A",
    }
]

# =====================================================================
# CRIME SCENE DOMAIN - HARD BELIEF REVISION
# Masking Variable: case.warrant_status (Invalidates suspect_a evidence)
# Shadow Updates: We add home evidence for A, loggers change.
# =====================================================================
CRIME_HARD_TURNS = [
    {
        # T1 - Baseline (A is prime, B is stranger)
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "suspect_a.financial_records": "debt",
            "suspect_a.home_evidence": "none",
            "suspect_a.evidence_logger": "officer_jones",
            "suspect_b.relation_to_victim": "stranger",
            "suspect_b.final_alibi": "unverified",
            "case.cctv_status": "corrupted",
            "case.cctv_subject": "none",
            "case.warrant_status": True,
            "officer_smith.status": "active",
        },
        "question": "With a valid warrant, Suspect A in debt, and Suspect B a stranger, what is the theory and lead suspect?",
        "options": {"A": "solo_perpetrator, suspect_a", "B": "unsolved, none", "C": "solo_perpetrator, suspect_b"},
        "correct": "A",
    },
    {
        # T2 - B gains motive
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "suspect_b.relation_to_victim": "enemy",
        },
        "question": "Suspect B is found to be an enemy. What is the case theory and lead suspect?",
        "options": {"A": "collusion, both", "B": "solo_perpetrator, suspect_a", "C": "unsolved, none"},
        "correct": "A",
    },
    {
        # T3 - The Mask (Warrant Rejected)
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "case.warrant_status": False,
        },
        "question": "The warrant is suddenly rejected. How does this affect the case theory and lead suspect?",
        "options": {"A": "solo_perpetrator, suspect_b", "B": "unsolved, none", "C": "collusion, both"},
        # Without warrant, A's financial_records are inadmissible, motive=False, status=cleared.
        "correct": "A",
    },
    {
        # T4 - Shadow Update 1 (A's home evidence)
        "attributes": ["suspect_a.status", "case.theory"],
        "beliefs": {
            "suspect_a.home_evidence": "weapon",
        },
        "question": "A weapon is found in Suspect A's home. What is Suspect A's status and the case theory?",
        "options": {"A": "cleared, solo_perpetrator", "B": "prime_suspect, collusion", "C": "prime_suspect, solo_perpetrator"},
        # Weapon is inadmissible without a warrant. Status remains cleared.
        "correct": "A",
    },
    {
        # T5 - Shadow Update 2 (Officer changes to smith)
        "attributes": ["suspect_a.status", "case.lead_suspect"],
        "beliefs": {
            "suspect_a.evidence_logger": "officer_smith",
        },
        "question": "Officer Smith takes over logging Suspect A's evidence. Does Suspect A become the lead suspect?",
        "options": {"A": "cleared, suspect_b", "B": "prime_suspect, suspect_a", "C": "prime_suspect, both"},
        "correct": "A",
    },
    {
        # T6 - The Unmask (Warrant Approved)
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "case.warrant_status": True,
        },
        "question": "A judge finally approves the warrant. Considering the weapon and Smith logging, what is the theory?",
        "options": {"A": "collusion, both", "B": "solo_perpetrator, suspect_a", "C": "solo_perpetrator, suspect_b"},
        # A's motive (debt) and weapon are now admissible. A is prime. B is prime (enemy).
        "correct": "A",
    },
    {
        # T7 - A New Mask (CCTV confirms B)
        "attributes": ["suspect_b.final_alibi", "case.theory"],
        "beliefs": {
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b",
        },
        "question": "CCTV is restored and confirms Suspect B was elsewhere. What is B's alibi and the case theory?",
        "options": {"A": "confirmed, solo_perpetrator", "B": "broken, collusion", "C": "confirmed, unsolved"},
        # B is cleared. Theory goes back to A alone.
        "correct": "A",
    },
    {
        # T8 - Shadow Update (B becomes beneficiary)
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "suspect_b.relation_to_victim": "beneficiary",
        },
        "question": "Suspect B is revealed as the sole beneficiary of the victim's will. Does this change the lead suspect?",
        "options": {"A": "solo_perpetrator, suspect_a", "B": "collusion, both", "C": "solo_perpetrator, suspect_b"},
        # Alibi mask overrides motive. B remains cleared.
        "correct": "A",
    },
    {
        # T9 - The Final Mask (Smith Suspended)
        "attributes": ["suspect_a.status", "case.theory"],
        "beliefs": {
            "officer_smith.status": "suspended",
        },
        "question": "Officer Smith is suspended for corruption. What happens to Suspect A's status and the case theory?",
        "options": {"A": "cleared, unsolved", "B": "prime_suspect, solo_perpetrator", "C": "cleared, solo_perpetrator"},
        # Smith logged A's evidence. Evidence becomes inadmissible. A is cleared. Case unsolved.
        "correct": "A",
    },
    {
        # T10 - Shadow Update under Unsolved
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "suspect_a.financial_records": "clean",
        },
        "question": "Suspect A's financial records are proven clean. Does this affect the current case theory?",
        "options": {"A": "unsolved, none", "B": "solo_perpetrator, suspect_a", "C": "solo_perpetrator, suspect_b"},
        # Already unsolved. No change.
        "correct": "A",
    }
]

# =====================================================================
# THORNCRESTER DOMAIN - HARD BELIEF REVISION
# Masking Variable: environment.weather_pattern (Drought forces scavenger)
# Shadow Updates: We shift digestion and behavior while drought is active.
# =====================================================================
THORNCRESTER_HARD_TURNS = [
    {
        # T1 - Baseline (Stable, Frugivore)
        "attributes": ["adult_thorncrester.expressed_diet", "juvenile_thorncrester.development"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": False,
            "thorncrester_flock.predator_presence": False,
            "juvenile_thorncrester.digestive_enzyme": "fructose_processor",
        },
        "question": "In a stable, plentiful environment, what is the adult diet and juvenile development?",
        "options": {"A": "frugivore, maturing", "B": "scavenger, arrested", "C": "frugivore, arrested"},
        "correct": "A",
    },
    {
        # T2 - Minor shift (Scarcity)
        "attributes": ["thorncrester_flock.expressed_structure", "adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.food_scarcity": True,
        },
        "question": "Food becomes scarce, but weather is stable. What is the flock structure and mortality risk?",
        "options": {"A": "survival_swarm, low", "B": "matriarchal_pairs, critical", "C": "survival_swarm, critical"},
        # Stable + Scarcity -> structure=survival_swarm, but diet is still frugivore, risk=low
        "correct": "A",
    },
    {
        # T3 - The Mask (Drought)
        "attributes": ["adult_thorncrester.expressed_diet", "adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.weather_pattern": "drought",
        },
        "question": "A severe drought hits. How does this mask the diet and affect mortality risk?",
        "options": {"A": "scavenger, critical", "B": "frugivore, low", "C": "scavenger, low"},
        # Drought forces scavenger. Scavenger + Scarcity = critical mortality risk.
        "correct": "A",
    },
    {
        # T4 - Shadow Update 1 (Juvenile gets general processor)
        "attributes": ["juvenile_thorncrester.metabolic_state", "juvenile_thorncrester.development"],
        "beliefs": {
            "juvenile_thorncrester.digestive_enzyme": "general_processor",
        },
        "question": "The juveniles mutate a general processor enzyme. What is their metabolic state and development?",
        "options": {"A": "thriving, arrested", "B": "starving, arrested", "C": "thriving, maturing"},
        # General processor allows digestion of scavenger diet -> thriving. BUT adults have critical mortality -> arrested.
        "correct": "A",
    },
    {
        # T5 - Shadow Update 2 (Food becomes plentiful)
        "attributes": ["adult_thorncrester.expressed_diet", "adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.food_scarcity": False,
        },
        "question": "Food is no longer scarce, but the drought persists. What is the adult diet and mortality risk?",
        "options": {"A": "scavenger, critical", "B": "frugivore, low", "C": "scavenger, low"},
        # Wait, drought forces scavenger. But scavenger + NO scarcity = critical?
        # Actually, rule is: if scavenger, mortality is critical regardless of scarcity.
        "correct": "A",
    },
    {
        # T6 - The Unmask (Weather stabilizes)
        "attributes": ["adult_thorncrester.expressed_diet", "adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.weather_pattern": "stable",
        },
        "question": "The weather finally stabilizes. Given the plentiful food, what is the diet and mortality risk?",
        "options": {"A": "frugivore, low", "B": "scavenger, critical", "C": "frugivore, critical"},
        # Stable -> frugivore. No scarcity -> low risk.
        "correct": "A",
    },
    {
        # T7 - Unmasked Validation (Juvenile development)
        "attributes": ["juvenile_thorncrester.development", "thorncrester_flock.expressed_structure"],
        "beliefs": {
            "thorncrester_flock.predator_presence": True,
        },
        "question": "With low mortality risk restored, predators arrive. What is the juvenile development and flock structure?",
        "options": {"A": "maturing, defensive_ring", "B": "arrested, survival_swarm", "C": "maturing, matriarchal_pairs"},
        "correct": "A",
    },
    {
        # T8 - A New Mask (Mite Bloom)
        "attributes": ["adult_thorncrester.plumage_color", "thorncrester_flock.territory_behavior"],
        "beliefs": {
            "feather_mite.bloom_status": "active_bloom",
        },
        "question": "An active mite bloom occurs. How does this mask plumage color and territory behavior?",
        "options": {"A": "dull_grey, hyper_aggressive", "B": "crimson, peaceful", "C": "dull_grey, peaceful"},
        "correct": "A",
    },
    {
        # T9 - Shadow Update under Mites (No predators)
        "attributes": ["thorncrester_flock.expressed_structure", "thorncrester_flock.territory_behavior"],
        "beliefs": {
            "thorncrester_flock.predator_presence": False,
        },
        "question": "The predators leave. Does this calm the flock's structure and territory behavior?",
        "options": {"A": "matriarchal_pairs, hyper_aggressive", "B": "defensive_ring, peaceful", "C": "matriarchal_pairs, peaceful"},
        # Structure drops defensive ring, but mites force hyper_aggressive behavior.
        "correct": "A",
    },
    {
        # T10 - Final Verification
        "attributes": ["adult_thorncrester.mortality_risk", "juvenile_thorncrester.development"],
        "beliefs": {
            "environment.food_scarcity": True,
        },
        "question": "Scarcity returns while mites are active. What is the mortality risk and juvenile development?",
        "options": {"A": "low, maturing", "B": "critical, arrested", "C": "low, arrested"},
        # Frugivore + Scarcity = low risk. So juveniles mature. Mites don't affect mortality directly.
        "correct": "A",
    }
]
