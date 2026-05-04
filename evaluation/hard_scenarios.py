"""
Hard-tier evaluation scenarios for the four belief-aware domains.

These sets are intentionally narrower than the extended tiers, but each turn
is more adversarial: more multi-hop dependencies, threshold edges, masking
effects, and tie-breaker cases that are useful for larger models.
"""


LOAN_HARD_TURNS = [
    {
        "attributes": ["loan.application_status", "loan.base_interest_rate"],
        "beliefs": {
            "applicant.income": 6500,
            "applicant.dependents": 3,
            "applicant.credit_score": 780,
            "applicant.co_signer": True,
        },
        "question": "With higher income, more dependents, and a co-signer, what are the application status and base interest rate?",
        "options": {
            "A": "approved, 4.5",
            "B": "denied_ineligible, None",
            "C": "approved, 6.5",
        },
        "correct": "A",
    },
    {
        "attributes": ["loan.requires_insurance", "loan.review_queue"],
        "beliefs": {
            "applicant.debt_ratio": 0.30,
            "applicant.credit_score": 700,
        },
        "question": "At the high-risk threshold, what are the required insurance status and review queue?",
        "options": {
            "A": "True, manual_review",
            "B": "False, auto_approve",
            "C": "True, auto_approve",
        },
        "correct": "A",
    },
    {
        "attributes": ["loan.application_status", "loan.rate_tier"],
        "beliefs": {
            "applicant.employment_status": "unemployed",
            "applicant.income": 9000,
            "applicant.credit_score": 780,
            "applicant.co_signer": True,
            "applicant.debt_ratio": 0.10,
        },
        "question": "If the applicant loses their job despite strong finances, what are the application status and rate tier?",
        "options": {
            "A": "denied_ineligible, None",
            "B": "approved, preferred",
            "C": "denied_amount_exceeded, standard",
        },
        "correct": "A",
    },
    {
        "attributes": ["loan.applicant_prequalified", "loan.max_amount"],
        "beliefs": {
            "applicant.bankruptcy_history": True,
            "applicant.employment_duration_months": 12,
            "applicant.income": 9000,
            "applicant.credit_score": 780,
            "applicant.co_signer": True,
            "applicant.debt_ratio": 0.10,
        },
        "question": "With a recent bankruptcy and short tenure, what are the prequalified status and max amount?",
        "options": {
            "A": "True, 100000",
            "B": "False, 0",
            "C": "False, 30000",
        },
        "correct": "B",
    },
    {
        "attributes": ["loan.application_status", "loan.base_interest_rate"],
        "beliefs": {
            "applicant.income": 8000,
            "applicant.dependents": 1,
            "applicant.credit_score": 760,
            "applicant.co_signer": False,
            "applicant.debt_ratio": 0.39,
            "applicant.has_collateral": True,
            "applicant.loan_amount_requested": 40000,
        },
        "question": "If collateral is provided and the debt ratio is near the cap, what are the application status and base interest rate?",
        "options": {
            "A": "approved, 5.5",
            "B": "approved, 4.5",
            "C": "denied_amount_exceeded, 5.5",
        },
        "correct": "A",
    },
    {
        "attributes": ["loan.application_status", "loan.review_queue"],
        "beliefs": {
            "applicant.income": 6000,
            "applicant.dependents": 2,
            "applicant.credit_score": 640,
            "applicant.co_signer": False,
            "applicant.debt_ratio": 0.25,
        },
        "question": "If the effective credit score stays below the minimum, what are the application status and review queue?",
        "options": {
            "A": "approved, auto_approve",
            "B": "denied_ineligible, rejected",
            "C": "denied_amount_exceeded, rejected",
        },
        "correct": "B",
    },
    {
        "attributes": ["loan.requires_insurance", "loan.base_interest_rate"],
        "beliefs": {
            "applicant.income": 7000,
            "applicant.dependents": 4,
            "applicant.credit_score": 650,
            "applicant.co_signer": False,
            "applicant.debt_ratio": 0.35,
            "applicant.loan_amount_requested": 20000,
        },
        "question": "With the applicant still eligible but high risk, what are the required insurance status and base interest rate?",
        "options": {
            "A": "True, 7.5",
            "B": "False, 6.5",
            "C": "True, 6.5",
        },
        "correct": "A",
    },
    {
        "attributes": ["loan.application_status", "loan.max_amount"],
        "beliefs": {
            "applicant.income": 5500,
            "applicant.dependents": 0,
            "applicant.credit_score": 720,
            "applicant.co_signer": False,
            "applicant.debt_ratio": 0.41,
        },
        "question": "If the debt ratio is over the limit, what are the application status and max amount?",
        "options": {
            "A": "denied_ineligible, 0",
            "B": "denied_amount_exceeded, 30000",
            "C": "approved, 30000",
        },
        "correct": "A",
    },
]


ALIEN_HARD_TURNS = [
    {
        "attributes": ["treatment.active_prescription", "clinic.billing_tier"],
        "beliefs": {},
        "question": "At the starting atmospheric state, what are the active prescription and billing tier?",
        "options": {
            "A": "snevox, class_omega",
            "B": "zyxostin, class_standard",
            "C": "none, class_omega",
        },
        "correct": "A",
    },
    {
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {"atmosphere.ambient_pressure": 4.5},
        "question": "If pressure spikes for the same Glerps patient, what are the active prescription and recovery prospect?",
        "options": {
            "A": "zyxostin, miraculous",
            "B": "snevox, excellent",
            "C": "filinan, guarded",
        },
        "correct": "A",
    },
    {
        "attributes": ["treatment.active_prescription", "medical.staff_requirement"],
        "beliefs": {
            "patient.organism_type": "Yorp",
            "patient.symptoms": ["acid_sweat"],
            "atmosphere.ambient_pressure": 5.5,
            "atmosphere.dominant_gas": "methane",
        },
        "question": "For a volatile Yorp patient with acid sweat, what are the active prescription and staff requirement?",
        "options": {
            "A": "filinan, hazmat_team",
            "B": "snevox, psionic_handler",
            "C": "zyxostin, standard_medic",
        },
        "correct": "A",
    },
    {
        "attributes": ["treatment.active_prescription", "clinic.billing_tier"],
        "beliefs": {
            "patient.organism_type": "Qwerl",
            "atmosphere.ambient_pressure": 5.5,
            "atmosphere.dominant_gas": "chlorine",
        },
        "question": "Under chlorine with a Qwerl patient, what are the active prescription and billing tier?",
        "options": {
            "A": "zyxostin, class_delta",
            "B": "snevox, class_omega",
            "C": "filinan, class_standard",
        },
        "correct": "A",
    },
    {
        "attributes": ["treatment.active_prescription", "medical.staff_requirement"],
        "beliefs": {
            "patient.organism_type": "Glerps",
            "patient.symptoms": ["fever", "spasms"],
            "atmosphere.ambient_pressure": 1.0,
            "atmosphere.dominant_gas": "chlorine",
        },
        "question": "If the Glerps patient presents fever and spasms at low pressure, what are the active prescription and staff requirement?",
        "options": {
            "A": "snevox, psionic_handler",
            "B": "zyxostin, hazmat_team",
            "C": "filinan, standard_medic",
        },
        "correct": "A",
    },
    {
        "attributes": ["treatment.active_prescription", "clinic.billing_tier"],
        "beliefs": {
            "patient.organism_type": "Yorp",
            "patient.symptoms": ["acid_sweat"],
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "xenon",
        },
        "question": "For an acid-sweat Yorp in xenon, which prescription wins and what billing tier follows?",
        "options": {
            "A": "snevox, class_omega",
            "B": "zyxostin, class_standard",
            "C": "filinan, class_delta",
        },
        "correct": "A",
    },
    {
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "patient.organism_type": "Qwerl",
            "patient.symptoms": ["fever", "spasms"],
            "atmosphere.ambient_pressure": 2.0,
            "atmosphere.dominant_gas": "methane",
        },
        "question": "When the Qwerl patient is stable enough to avoid the hard-stop hazards, what are the active prescription and recovery prospect?",
        "options": {
            "A": "zyxostin, excellent",
            "B": "snevox, excellent",
            "C": "zyxostin, miraculous",
        },
        "correct": "A",
    },
    {
        "attributes": ["treatment.active_prescription", "patient.recovery_prospect"],
        "beliefs": {
            "patient.organism_type": "Yorp",
            "atmosphere.ambient_pressure": 5.5,
            "atmosphere.dominant_gas": "chlorine",
        },
        "question": "At the volatile Yorp threshold, what are the active prescription and recovery prospect?",
        "options": {
            "A": "filinan, miraculous",
            "B": "snevox, excellent",
            "C": "zyxostin, terminal",
        },
        "correct": "A",
    },
]


CRIME_HARD_TURNS = [
    {
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "suspect_a.evidence_logger": "officer_jones",
            "case.warrant_status": True,
            "suspect_a.financial_records": "debt",
            "suspect_b.relation_to_victim": "stranger",
            "case.cctv_status": "corrupted",
        },
        "question": "With admissible evidence intact and only one verified motive, what are the case theory and lead suspect?",
        "options": {
            "A": "collusion, suspect_a",
            "B": "solo_perpetrator, suspect_b",
            "C": "collusion, both",
        },
        "correct": "A",
    },
    {
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "suspect_a.evidence_logger": "officer_jones",
            "case.warrant_status": True,
            "suspect_a.financial_records": "clean",
            "suspect_b.relation_to_victim": "enemy",
            "case.cctv_status": "corrupted",
        },
        "question": "If both suspects remain prime but only one motive is verified, what are the case theory and lead suspect?",
        "options": {
            "A": "collusion, suspect_b",
            "B": "solo_perpetrator, suspect_a",
            "C": "collusion, both",
        },
        "correct": "A",
    },
    {
        "attributes": ["suspect_a.status", "case.theory"],
        "beliefs": {
            "officer_smith.status": "suspended",
            "case.warrant_status": True,
            "suspect_a.financial_records": "debt",
            "suspect_b.relation_to_victim": "enemy",
            "case.cctv_status": "corrupted",
        },
        "question": "Once the logging officer is suspended, what are Suspect A's status and the case theory?",
        "options": {
            "A": "cleared, unsolved",
            "B": "prime_suspect, solo_perpetrator",
            "C": "cleared, collusion",
        },
        "correct": "A",
    },
    {
        "attributes": ["suspect_b.final_alibi", "case.lead_suspect"],
        "beliefs": {
            "officer_smith.status": "active",
            "suspect_a.home_evidence": "none",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b",
            "case.warrant_status": True,
            "suspect_a.financial_records": "debt",
            "suspect_b.relation_to_victim": "enemy",
        },
        "question": "If CCTV now confirms Suspect B while Suspect A has no admissible evidence, what are Suspect B's final alibi and the lead suspect?",
        "options": {
            "A": "confirmed, none",
            "B": "broken, suspect_a",
            "C": "confirmed, suspect_b",
        },
        "correct": "A",
    },
    {
        "attributes": ["case.theory", "case.lead_suspect"],
        "beliefs": {
            "suspect_a.evidence_logger": "officer_jones",
            "case.warrant_status": True,
            "suspect_a.financial_records": "debt",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b",
            "suspect_b.relation_to_victim": "enemy",
        },
        "question": "When CCTV clears Suspect B but Suspect A remains prime, what are the case theory and lead suspect?",
        "options": {
            "A": "solo_perpetrator, suspect_a",
            "B": "collusion, both",
            "C": "unsolved, none",
        },
        "correct": "A",
    },
    {
        "attributes": ["suspect_a.motive_verified", "case.lead_suspect"],
        "beliefs": {
            "suspect_a.evidence_logger": "officer_jones",
            "case.warrant_status": False,
            "suspect_a.financial_records": "debt",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b",
            "suspect_b.relation_to_victim": "enemy",
        },
        "question": "If the warrant is rejected but Suspect A is still the only prime suspect, what are Suspect A's motive status and the lead suspect?",
        "options": {
            "A": "False, suspect_a",
            "B": "True, suspect_b",
            "C": "False, none",
        },
        "correct": "A",
    },
    {
        "attributes": ["suspect_b.status", "case.theory"],
        "beliefs": {
            "officer_smith.status": "suspended",
            "suspect_a.home_evidence": "none",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b",
            "case.warrant_status": True,
            "suspect_a.financial_records": "debt",
            "suspect_b.relation_to_victim": "enemy",
        },
        "question": "When the CCTV survives but the physical evidence is gone, what are Suspect B's status and the case theory?",
        "options": {
            "A": "cleared, unsolved",
            "B": "prime_suspect, collusion",
            "C": "cleared, solo_perpetrator",
        },
        "correct": "A",
    },
    {
        "attributes": ["case.lead_suspect", "case.theory"],
        "beliefs": {
            "suspect_a.evidence_logger": "officer_jones",
            "case.warrant_status": False,
            "suspect_a.financial_records": "debt",
            "suspect_b.relation_to_victim": "enemy",
            "case.cctv_status": "corrupted",
        },
        "question": "With both suspects prime again but only Suspect B's motive verified, what are the lead suspect and the case theory?",
        "options": {
            "A": "suspect_b, collusion",
            "B": "suspect_a, solo_perpetrator",
            "C": "both, collusion",
        },
        "correct": "A",
    },
]


THORNCRESTER_HARD_TURNS = [
    {
        "attributes": ["adult_thorncrester.mortality_risk", "juvenile_thorncrester.development"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
        },
        "question": "When the environment flips into drought with scarcity, what are the adult mortality risk and juvenile development states?",
        "options": {
            "A": "critical, arrested",
            "B": "low, maturing",
            "C": "critical, maturing",
        },
        "correct": "A",
    },
    {
        "attributes": ["adult_thorncrester.expressed_diet", "adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": False,
        },
        "question": "If drought begins but food is still plentiful, what are the adult expressed diet and mortality risk?",
        "options": {
            "A": "frugivore, low",
            "B": "scavenger, critical",
            "C": "frugivore, critical",
        },
        "correct": "A",
    },
    {
        "attributes": ["thorncrester_flock.expressed_structure", "adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": True,
        },
        "question": "If scarcity appears without drought, what are the flock structure and mortality risk?",
        "options": {
            "A": "matriarchal_pairs, low",
            "B": "survival_swarm, critical",
            "C": "matriarchal_pairs, critical",
        },
        "correct": "A",
    },
    {
        "attributes": ["juvenile_thorncrester.metabolic_state", "juvenile_thorncrester.development"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
            "juvenile_thorncrester.digestive_enzyme": "general_processor",
        },
        "question": "If the adults are masked into scavenging but the juvenile can digest broadly, what are the juvenile metabolic state and development?",
        "options": {
            "A": "thriving, maturing",
            "B": "starving, arrested",
            "C": "thriving, arrested",
        },
        "correct": "A",
    },
    {
        "attributes": ["feather_mite.bloom_status", "adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
        },
        "question": "Under the full drought-and-scarcity mask, what are the mite bloom status and the adult mortality risk?",
        "options": {
            "A": "active_bloom, critical",
            "B": "dormant, low",
            "C": "active_bloom, low",
        },
        "correct": "A",
    },
    {
        "attributes": ["adult_thorncrester.plumage_color", "thorncrester_flock.territory_behavior"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": False,
        },
        "question": "Once the weather normalizes and scarcity vanishes, what are the adult plumage color and territory behavior?",
        "options": {
            "A": "crimson, peaceful",
            "B": "dull_grey, hyper_aggressive",
            "C": "crimson, hyper_aggressive",
        },
        "correct": "A",
    },
    {
        "attributes": ["adult_thorncrester.expressed_diet", "juvenile_thorncrester.development"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
            "juvenile_thorncrester.digestive_enzyme": "fructose_processor",
        },
        "question": "When the ecological mask is active and the juvenile still depends on fruit, what are the expressed diet and development states?",
        "options": {
            "A": "scavenger, arrested",
            "B": "frugivore, maturing",
            "C": "scavenger, maturing",
        },
        "correct": "A",
    },
    {
        "attributes": ["adult_thorncrester.mortality_risk", "thorncrester_flock.territory_behavior"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
            "juvenile_thorncrester.digestive_enzyme": "fructose_processor",
        },
        "question": "With the flock under stress and the parasites active, what are the adult mortality risk and territory behavior?",
        "options": {
            "A": "critical, hyper_aggressive",
            "B": "low, peaceful",
            "C": "critical, peaceful",
        },
        "correct": "A",
    },
]
