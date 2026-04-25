"""
Belief-Awareness Evaluation Scenarios.

Two evaluation dimensions across all 4 domains:

1. COUNTERFACTUAL COMPLIANCE (Prior Suppression)
   Beliefs deliberately conflict with common sense / real-world intuition.
   A belief-aware LLM follows the beliefs; a non-belief-aware LLM
   defaults to its priors.
   Design: Option A = "common sense" trap. Correct = belief-derived.

2. GROUNDING BOUNDARY (Hallucination Resistance)
   Questions ask about facts NOT in the provided beliefs, or inject
   false claims in the question text.  A belief-aware LLM refuses to
   speculate; a non-belief-aware LLM hallucinates an answer.
"""

# =====================================================================
# LOAN DOMAIN — COUNTERFACTUAL COMPLIANCE (10 turns)
# =====================================================================
# Initial beliefs (reference):
#   applicant.income = 6000, credit_score = 720, co_signer = False,
#   debt_ratio = 0.20, employment_status = "employed",
#   bankruptcy_history = False, employment_duration_months = 36,
#   has_collateral = False, loan_amount_requested = 10_000,
#   dependents = 2, loan.min_income = 5000, loan.min_credit = 650,
#   loan.max_debt_ratio = 0.4

LOAN_COUNTERFACTUAL_TURNS = [
    {
        # Millionaire denied for bad credit.
        # adjusted_income = 1_000_000 - 0*500 = 1_000_000 >= 5000 ✓
        # credit_effective = 100 + 0 = 100 < 650  ✗
        # prequalified = False → denied_ineligible
        "attributes": ["loan.application_status"],
        "beliefs": {
            "applicant.income": 1000000,
            "applicant.credit_score": 100,
            "applicant.dependents": 0,
            "applicant.co_signer": False,
        },
        "question": "The applicant has an income of $1,000,000. Is their loan approved?",
        "options": {
            "A": "approved — such high income guarantees approval",
            "B": "denied_ineligible",
            "C": "denied_amount_exceeded",
        },
        "correct": "B",
    },
    {
        # Bankrupt applicant STILL approved (employment > 24 months overrides).
        # bankruptcy_history = True, employment_duration_months = 30
        # Rule 4: NOT (True AND 30 < 24) = NOT False = True  → passes bankruptcy check
        # adjusted_income = 6000 - 2*500 = 5000 >= 5000 ✓
        # credit_effective = 720 >= 650 ✓, debt_ratio 0.20 < 0.4 ✓
        # prequalified = True → approved
        "attributes": ["loan.application_status"],
        "beliefs": {
            "applicant.bankruptcy_history": True,
            "applicant.employment_duration_months": 30,
        },
        "question": "The applicant has a history of bankruptcy. Is the loan approved?",
        "options": {
            "A": "denied_ineligible — bankruptcy history disqualifies",
            "B": "denied_amount_exceeded",
            "C": "approved",
        },
        "correct": "C",
    },
    {
        # Co-signer rescues below-threshold credit.
        # credit_score = 610, co_signer = True → effective = 660 >= 650 ✓
        # adjusted_income = 6000 - 1000 = 5000 >= 5000 ✓
        # prequalified = True → approved
        "attributes": ["loan.application_status", "applicant.credit_score", "applicant.co_signer"],
        "beliefs": {
            "applicant.credit_score": 610,
            "applicant.co_signer": True,
        },
        "question": "The applicant's credit score is 610. Is the loan approved?",
        "options": {
            "A": "denied_ineligible — 610 is below the minimum",
            "B": "approved",
            "C": "denied_amount_exceeded",
        },
        "correct": "B",
    },
    {
        # High-risk loan STILL approved (risk ≠ denial, just adds insurance).
        # debt_ratio = 0.35 → high_risk = True, but 0.35 < 0.4 → passes max_debt check
        # adjusted_income = 6000 - 1000 = 5000 >= 5000 ✓, credit = 720 >= 650 ✓
        # prequalified = True → approved
        # requires_insurance = True (high_risk AND approved)
        "attributes": ["loan.requires_insurance", "loan.application_status"],
        "beliefs": {
            "applicant.debt_ratio": 0.35,
        },
        "question": "The applicant's debt ratio is 0.35. What is the application status?",
        "options": {
            "A": "Yes — high risk applicants are always denied",
            "B": "The loan is approved but requires insurance",
            "C": "The loan is denied_amount_exceeded",
        },
        "correct": "B",
    },
    {
        # Dependents drastically reduce effective income.
        # adjusted_income = 6000 - 8*500 = 6000 - 4000 = 2000 < 5000 ✗
        # prequalified = False → denied_ineligible
        "attributes": ["loan.application_status", "loan.adjusted_income"],
        "beliefs": {
            "applicant.dependents": 8,
        },
        "question": "The applicant earns $6000 with 8 dependents. Is the loan approved?",
        "options": {
            "A": "approved — $6000 income exceeds the minimum",
            "B": "denied_amount_exceeded",
            "C": "denied_ineligible",
        },
        "correct": "C",
    },
    {
        # Preferred rate despite seemingly high risk factors.
        # credit_score = 700, co_signer = True → effective = 750 >= 750 → preferred
        # rate_tier = preferred → base_rate = 4.5
        # debt_ratio = 0.20 → high_risk = False → no insurance surcharge
        "attributes": ["loan.base_interest_rate", "applicant.credit_score", "applicant.co_signer"],
        "beliefs": {
            "applicant.credit_score": 700,
            "applicant.co_signer": True,
        },
        "question": "The applicant has a credit score of 700 and a co-signer. What is the base interest rate?",
        "options": {
            "A": "6.5 — standard rate for sub-750 credit",
            "B": "7.5",
            "C": "4.5",
        },
        "correct": "C",
    },
    {
        # Collateral boosts max_amount but loan still denied for other reasons.
        # employment_status = "unemployed" → prequalified = False
        # max_amount = 0 (not prequalified), status = denied_ineligible
        "attributes": ["loan.application_status", "loan.max_amount"],
        "beliefs": {
            "applicant.has_collateral": True,
            "applicant.employment_status": "unemployed",
        },
        "question": "The applicant has collateral and is unemployed. Is the loan approved?",
        "options": {
            "A": "Yes — collateral guarantees approval",
            "B": "denied_ineligible",
            "C": "approved with manual_review",
        },
        "correct": "B",
    },
    {
        # Tiny requested amount still denied when ineligible.
        # credit_score = 100 → effective = 100 < 650 → not prequalified
        "attributes": ["loan.application_status"],
        "beliefs": {
            "applicant.loan_amount_requested": 1,
            "applicant.credit_score": 100,
            "applicant.co_signer": False,
        },
        "question": "The applicant is requesting a loan amount of $1. Is the loan approved?",
        "options": {
            "A": "approved — the amount is negligible",
            "B": "denied_ineligible",
            "C": "denied_amount_exceeded",
        },
        "correct": "B",
    },
    {
        # Recent bankrupt employee with short tenure → denied.
        # bankruptcy_history = True, employment_duration_months = 12
        # Rule 4: NOT (True AND 12 < 24) = NOT True = False → fails
        # prequalified = False → denied_ineligible
        "attributes": ["loan.application_status"],
        "beliefs": {
            "applicant.bankruptcy_history": True,
            "applicant.employment_duration_months": 12,
        },
        "question": "The applicant has a bankruptcy history and has been employed for 12 months. Is the loan approved?",
        "options": {
            "A": "approved — they're employed now",
            "B": "denied_ineligible",
            "C": "denied_amount_exceeded",
        },
        "correct": "B",
    },
    {
        # Insurance surcharge pushes rate higher despite "preferred" tier.
        # credit_score = 720, co_signer = True → effective = 770 >= 750 → preferred
        # base_rate = 4.5 (preferred)
        # debt_ratio = 0.35 → high_risk = True
        # status = approved (all checks pass)
        # requires_insurance = True → +1.0 → 5.5
        "attributes": ["loan.base_interest_rate", "applicant.credit_score", "applicant.co_signer", "applicant.debt_ratio"],
        "beliefs": {
            "applicant.credit_score": 720,
            "applicant.co_signer": True,
            "applicant.debt_ratio": 0.35,
        },
        "question": "The applicant has a credit score of 720, a co-signer, and a debt ratio of 0.35. What is the final interest rate?",
        "options": {
            "A": "4.5 — preferred rate applies",
            "B": "5.5",
            "C": "7.5",
        },
        "correct": "B",
    },
]

# =====================================================================
# ALIEN CLINIC DOMAIN — COUNTERFACTUAL COMPLIANCE (10 turns)
# =====================================================================
# Initial beliefs (reference):
#   patient.organism_type = "Glerps", patient.symptoms = [],
#   atmosphere.ambient_pressure = 3.5, atmosphere.dominant_gas = "methane"

ALIEN_COUNTERFACTUAL_TURNS = [
    {
        # Near-vacuum (pressure = 0.001) is actually SAFE per rules.
        # 0.001 <= 3.0 → stable, not volatile/brittle
        "attributes": ["patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 0.001,
            "patient.organism_type": "Glerps",
        },
        "question": "The ambient pressure is 0.001. What is the organ integrity?",
        "options": {
            "A": "volatile — near-vacuum is extremely dangerous",
            "B": "brittle",
            "C": "stable",
        },
        "correct": "C",
    },
    {
        # Extremely high pressure (99.0) with Qwerl → only "brittle" not "volatile".
        # Volatile requires: >5.0+Yorp or >4.0+Glerps. Qwerl has no volatile threshold.
        # 99.0 > 3.0 → brittle
        "attributes": ["patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 99.0,
            "patient.organism_type": "Qwerl",
        },
        "question": "The ambient pressure is 99.0. What is the Qwerl's organ integrity?",
        "options": {
            "A": "volatile — such extreme pressure must be worst outcome",
            "B": "brittle",
            "C": "stable",
        },
        "correct": "B",
    },
    {
        # "Fatal" sounding combination is actually "symbiotic" (miracle override).
        # Glerps + zyxostin = explode pair. Pressure 4.5 + Glerps → volatile.
        # Explode + volatile → symbiotic (the miracle!)
        # So zyxostin is prescribed via miracle override → active_prescription = zyxostin
        "attributes": ["treatment.active_prescription", "atmosphere.ambient_pressure", "patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "The organism is Glerps and organs are volatile. Is the active prescription none?",
        "options": {
            "A": "none — the combination is too dangerous to prescribe",
            "B": "zyxostin",
            "C": "filinan",
        },
        "correct": "B",
    },
    {
        # Recovery is "miraculous" despite volatile organs (symbiotic miracle).
        # Same Glerps + pressure 4.5 → volatile → symbiotic → miraculous
        "attributes": ["patient.recovery_prospect", "atmosphere.ambient_pressure", "patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "The patient's organs are volatile. What is the recovery prospect?",
        "options": {
            "A": "terminal — the situation is catastrophic",
            "B": "guarded",
            "C": "miraculous",
        },
        "correct": "C",
    },
    {
        # Quarantine NOT required despite "dangerous" sounding gas.
        # Chlorine + Glerps → quarantine = False
        # (Only chlorine+Qwerl or methane+Yorp triggers quarantine)
        "attributes": ["patient.quarantine_required"],
        "beliefs": {
            "atmosphere.dominant_gas": "chlorine",
            "patient.organism_type": "Glerps",
        },
        "question": "The atmosphere contains chlorine gas. What is the recorded quarantine status?",
        "options": {
            "A": "True — chlorine is a hazardous gas requiring quarantine",
            "B": "False",
            "C": "Cannot determine",
        },
        "correct": "B",
    },
    {
        # "Standard_medic" despite alarming conditions.
        # Glerps + xenon. Quarantine: xenon+Glerps = False.
        # Glerps default priority (no symptoms): filinan → zyxostin → snevox
        # xenon → filinan_phase=vapor, zyxostin_phase=crystalline, snevox_phase=vapor
        # Integrity: 3.5 + Glerps → NOT >4.0 → 3.5 > 3.0 → brittle
        # filinan danger: Glerps+filinan NOT explode pair. phase=vapor, NOT plasma+filinan.
        #   integrity=brittle ≠ volatile → safe ✓ → prescribe filinan
        # sensory = normal (not snevox). Staff = standard_medic (no quar, not telepathic)
        "attributes": ["medical.staff_requirement"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "In a xenon atmosphere at pressure 3.5 with brittle organs, what is the medical staff requirement?",
        "options": {
            "A": "hazmat_team — the atmosphere and organ damage demand it",
            "B": "psionic_handler",
            "C": "standard_medic",
        },
        "correct": "C",
    },
    {
        # Let's do: Snevox prescribed → "telepathic" sensory (sounds alarming but is expected).
        # Glerps + methane + low pressure (stable):
        # Phases: methane → zyxostin=plasma, filinan=plasma, snevox=vapor
        # Integrity: 2.0 → stable
        # zyxostin: Glerps+zyxostin IS explode. stable ≠ volatile → fatal
        # filinan: phase=plasma+filinan → fatal
        # snevox: NOT explode. vapor+snevox, but Glerps ≠ Qwerl. stable ≠ volatile → safe ✓
        # Glerps default: filinan→zyxostin→snevox. filinan=fatal, zyxostin=fatal → snevox
        # sensory_status = telepathic (prescription=snevox)
        "attributes": ["patient.sensory_status", "atmosphere.ambient_pressure", "patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 2.0,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "The patient's sensory status is telepathic. What does this indicate?",
        "options": {
            "A": "A critical adverse reaction",
            "B": "The expected outcome of the current prescription",
            "C": "Cannot determine",
        },
        "correct": "B",
    },
    {
        # Billing is "class_standard" despite scary conditions.
        # Glerps + xenon + moderate pressure (3.5) → brittle
        # filinan prescribed (safe), sensory=normal, quarantine=False
        # staff = standard_medic. billing = class_standard (not snevox, not psionic/hazmat)
        "attributes": ["clinic.billing_tier", "atmosphere.dominant_gas", "patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "The patient has brittle organs in a xenon atmosphere. What is the clinic billing tier?",
        "options": {
            "A": "class_omega — brittle organs and exotic atmosphere require premium billing",
            "B": "class_delta",
            "C": "class_standard",
        },
        "correct": "C",
    },
    {
        # "Symbiotic" danger sounds terrible but means BEST outcome.
        # Glerps + zyxostin (explode pair) + pressure 4.5 → volatile → symbiotic
        "attributes": ["treatment.zyxostin_danger_level"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
        },
        "question": "For a Glerps and zyxostin at volatile integrity, what is the zyxostin danger level?",
        "options": {
            "A": "fatal_to_patient — explosive + volatile is the worst possible scenario",
            "B": "safe",
            "C": "symbiotic",
        },
        "correct": "C",
    },
    {
        # Duration is 5 (standard) despite volatile organs — because prescription isn't snevox.
        # Glerps + methane + 4.5 → volatile → symbiotic(zyxostin) → zyxostin prescribed
        # duration: zyxostin + volatile → doesn't match "snevox and volatile" → default 5
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {
            "atmosphere.ambient_pressure": 4.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "With volatile organs, what is the treatment duration in cycles?",
        "options": {
            "A": "12 — volatile organs always require maximum treatment",
            "B": "5",
            "C": "0",
        },
        "correct": "B",
    },
]

# =====================================================================
# CRIME SCENE DOMAIN — COUNTERFACTUAL COMPLIANCE (10 turns)
# =====================================================================
# Initial beliefs (reference):
#   officer_smith.status = "active", suspect_a.home_evidence = "gun",
#   suspect_a.evidence_logger = "officer_smith",
#   suspect_a.financial_records = "clean",
#   suspect_b.relation_to_victim = "stranger",
#   suspect_b.alibi_partner = "suspect_a",
#   case.warrant_status = False, case.cctv_status = "corrupted",
#   case.cctv_subject = "none"

CRIME_COUNTERFACTUAL_TURNS = [
    {
        # Gun found → should be prime suspect, BUT officer is suspended → evidence inadmissible.
        # R1: logger="officer_smith", status="suspended" → admissible = "none"
        # R2: admissible = "none" → status_a = "cleared"
        # Counterintuitive: gun evidence exists but is legally worthless.
        "attributes": ["suspect_a.status"],
        "beliefs": {
            "officer_smith.status": "suspended",
        },
        "question": "A gun was found at suspect A's home, but Officer Smith's status is suspended. What is suspect A's status?",
        "options": {
            "A": "prime_suspect — the gun is strong physical evidence",
            "B": "cleared",
            "C": "Cannot determine",
        },
        "correct": "B",
    },
    {
        # Enemy of victim but CCTV alibi → cleared.
        # R8: relation_to_victim = "enemy" → motive_verified_b = True
        # R4: cctv_status="active", cctv_subject="suspect_b" → digital_alibi="confirmed"
        # R5: digital = confirmed → final_alibi = confirmed
        # R6: final_alibi = confirmed → status_b = "cleared"
        # Counterintuitive: has motive AND is enemy, but still cleared.
        "attributes": ["suspect_b.status", "suspect_b.relation_to_victim", "case.cctv_status", "case.cctv_subject"],
        "beliefs": {
            "suspect_b.relation_to_victim": "enemy",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b",
        },
        "question": "Suspect B is the victim's enemy, and the CCTV status is active targeting suspect B. What is suspect B's status?",
        "options": {
            "A": "prime_suspect — enemy with verified motive is the strongest lead",
            "B": "cleared",
            "C": "Cannot determine until further evidence is gathered",
        },
        "correct": "B",
    },
    {
        # Both are prime suspects → "collusion" theory even though no direct evidence of conspiracy.
        # Default: gun admissible → A=prime. A=prime + alibi_partner=A → B broken → B=prime.
        # Both prime → collusion.
        "attributes": ["case.theory"],
        "beliefs": {},
        "question": "Given the initial base beliefs, what is the case theory?",
        "options": {
            "A": "solo_perpetrator — no conspiracy evidence means no collusion",
            "B": "unsolved",
            "C": "collusion",
        },
        "correct": "C",
    },
    {
        # "unsolved" case despite physical evidence existing (just inadmissible).
        # officer suspended → admissible = none → A cleared.
        # A cleared → B testimonial alibi = confirmed → B cleared.
        # Both cleared → unsolved.
        "attributes": ["case.theory", "officer_smith.status"],
        "beliefs": {
            "officer_smith.status": "suspended",
        },
        "question": "Officer Smith's status is suspended. What is the case theory?",
        "options": {
            "A": "No — physical evidence ensures the case is solvable",
            "B": "unsolved",
            "C": "solo_perpetrator",
        },
        "correct": "B",
    },
    {
        # Different logger → evidence still admissible despite officer suspended.
        # R1: logger ≠ "officer_smith" → admissible = home_evidence = "gun"
        # So changing the logger fixes the evidence chain.
        "attributes": ["suspect_a.admissible_evidence", "suspect_a.status"],
        "beliefs": {
            "officer_smith.status": "suspended",
            "suspect_a.evidence_logger": "officer_jones",
        },
        "question": "Officer Smith's status is suspended, and the evidence logger is Officer Jones. What is suspect A's status?",
        "options": {
            "A": "Yes — the logging officer's suspension taints all evidence",
            "B": "The evidence is admissible and suspect A is prime_suspect",
            "C": "Cannot determine",
        },
        "correct": "B",
    },
    {
        # Digital alibi overrides testimonial alibi.
        # suspect_a is prime → testimonial_alibi = broken.
        # But CCTV active + subject=suspect_b → digital_alibi = confirmed.
        # final_alibi: digital confirmed → confirmed (overrides broken testimonial).
        # status_b = cleared.
        "attributes": ["suspect_b.status", "case.cctv_status", "case.cctv_subject"],
        "beliefs": {
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b",
        },
        "question": "The CCTV status is active and the CCTV subject is Suspect B. What is Suspect B's status?",
        "options": {
            "A": "prime_suspect — broken alibi makes them a suspect",
            "B": "cleared",
            "C": "Cannot determine",
        },
        "correct": "B",
    },
    {
        # Debt without warrant → motive NOT verified.
        # R7: financial_records = "debt" but warrant_status = False → motive_verified_a = False
        "attributes": ["suspect_a.motive_verified"],
        "beliefs": {
            "suspect_a.financial_records": "debt",
            "case.warrant_status": False,
        },
        "question": "Suspect A has financial records of debt, and the warrant status is False. Is Suspect A's motive verified?",
        "options": {
            "A": "True — debt is clear evidence of financial motive",
            "B": "False",
            "C": "Partially verified",
        },
        "correct": "B",
    },
    {
        # Warrant + debt → lead suspect is suspect_a (in collusion, motive breaks tie).
        # A=prime, B=prime → collusion.
        # motive_a: debt + warrant=True → True.
        # motive_b: stranger → False.
        # lead_suspect: motive_a=True, motive_b=False → suspect_a.
        "attributes": ["case.lead_suspect"],
        "beliefs": {
            "suspect_a.financial_records": "debt",
            "case.warrant_status": True,
        },
        "question": "Suspect A has financial records of debt, and the warrant status is True. Who is the lead suspect?",
        "options": {
            "A": "both — in collusion cases, both are equally suspected",
            "B": "suspect_a",
            "C": "suspect_b",
        },
        "correct": "B",
    },
    {
        # "Stranger" relation means motive_b = False.
        # Even if B is prime_suspect, motive is not verified.
        "attributes": ["suspect_b.motive_verified"],
        "beliefs": {
            "suspect_b.relation_to_victim": "stranger",
        },
        "question": "Suspect B's relation to the victim is 'stranger'. Is Suspect B's motive verified?",
        "options": {
            "A": "True — being a prime suspect implies verified motive",
            "B": "False",
            "C": "Cannot determine",
        },
        "correct": "B",
    },
    {
        # home_evidence = "none" → suspect_a cleared → theory depends on this cascade.
        # admissible = none (even with active officer, evidence itself is "none")
        # status_a = cleared. testimonial_alibi = confirmed (partner not prime).
        # status_b = cleared. Both cleared → unsolved.
        "attributes": ["case.theory"],
        "beliefs": {
            "suspect_a.home_evidence": "none",
        },
        "question": "No evidence was found at suspect A's home. What is the case theory?",
        "options": {
            "A": "collusion — the alibi connection is suspicious",
            "B": "solo_perpetrator",
            "C": "unsolved",
        },
        "correct": "C",
    },
]

# =====================================================================
# THORNCRESTER DOMAIN — COUNTERFACTUAL COMPLIANCE (10 turns)
# =====================================================================
# Initial beliefs (reference):
#   environment.weather_pattern = "stable", environment.food_scarcity = False,
#   adult_thorncrester.genetic_diet = "frugivore",
#   thorncrester_flock.genetic_structure = "matriarchal_pairs",
#   juvenile_thorncrester.digestive_enzyme = "fructose_processor"

THORNCRESTER_COUNTERFACTUAL_TURNS = [
    {
        # Drought WITHOUT scarcity → stress stays NOMINAL (not high).
        # R1: weather=drought, scarcity=False → nominal (need BOTH for high)
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": False,
        },
        "question": "The weather pattern is drought and food scarcity is False. What is the ecological stress level?",
        "options": {
            "A": "high — drought conditions create high stress",
            "B": "critical",
            "C": "nominal",
        },
        "correct": "C",
    },
    {
        # Scarcity WITHOUT drought → stress also NOMINAL.
        # R1: weather=stable, scarcity=True → nominal
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": True,
        },
        "question": "The weather pattern is stable and food scarcity is True. What is the ecological stress level?",
        "options": {
            "A": "high — food scarcity is inherently stressful",
            "B": "nominal",
            "C": "critical",
        },
        "correct": "B",
    },
    {
        # Crimson plumage during drought (because no scarcity → nominal → frugivore → crimson).
        # R1: drought + no scarcity → nominal. R2: nominal → genetic_diet = frugivore.
        # R3: frugivore ≠ scavenger → crimson.
        "attributes": ["adult_thorncrester.plumage_color", "environment.weather_pattern", "environment.food_scarcity"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": False,
        },
        "question": "The weather pattern is drought and food scarcity is False. What is the plumage color?",
        "options": {
            "A": "dull_grey — drought conditions dim the plumage",
            "B": "crimson",
            "C": "azure",
        },
        "correct": "B",
    },
    {
        # Juvenile THRIVING despite adults scavenging — because enzyme is general_processor.
        # R6: enzyme="general_processor", diet=scavenger → NOT (fructose_processor AND ≠ frugivore) → thriving
        "attributes": ["juvenile_thorncrester.metabolic_state", "environment.weather_pattern", "environment.food_scarcity", "juvenile_thorncrester.digestive_enzyme"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
            "juvenile_thorncrester.digestive_enzyme": "general_processor",
        },
        "question": "The weather pattern is drought, food scarcity is True, and the digestive enzyme is general_processor. What is the metabolic state?",
        "options": {
            "A": "starving — the adult diet change impacts all juveniles",
            "B": "thriving",
            "C": "dormant",
        },
        "correct": "B",
    },
    {
        # Mortality risk is LOW despite drought + scarcity, IF we change the structure.
        # Wait: drought + scarcity → high stress → scavenger → dull_grey.
        # dull_grey + drought → active_bloom → lethal → critical.
        # I need to keep mortality low despite scary conditions.
        # Actually, if weather=stable + scarcity=True → nominal stress.
        # Plumage = crimson. bloom = dormant. parasites = harmless.
        # territory: structure = genetic(matriarchal_pairs) → not survival_swarm.
        # territory = peaceful. mortality = low.
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": True,
        },
        "question": "The weather pattern is stable and food scarcity is True. What is the mortality risk?",
        "options": {
            "A": "critical — food scarcity is life-threatening",
            "B": "low",
            "C": "moderate",
        },
        "correct": "B",
    },
    {
        # Feather mite bloom DORMANT despite drought (because no scarcity → no dull_grey).
        # drought + no scarcity → nominal → frugivore → crimson.
        # bloom: crimson ≠ dull_grey → dormant.
        "attributes": ["feather_mite.bloom_status"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": False,
        },
        "question": "The weather pattern is drought and food scarcity is False. What is the feather mite bloom status?",
        "options": {
            "A": "active_bloom — drought triggers parasite outbreaks",
            "B": "dormant",
            "C": "lethal",
        },
        "correct": "B",
    },
    {
        # Peaceful territory despite survival_swarm, because no food_scarcity.
        # Wait: survival_swarm requires high stress which requires drought+scarcity.
        # If drought+scarcity → survival_swarm AND scarcity → hyper_aggressive.
        # I need survival_swarm but peaceful. But survival_swarm requires scarcity=True,
        # and territory requires survival_swarm + scarcity → hyper_aggressive.
        # So if survival_swarm, territorial is always hyper_aggressive. Can't separate.
        #
        # Let me instead show: matriarchal_pairs structure is PEACEFUL despite scarcity.
        # stable + scarcity=True → nominal stress → genetic structure = matriarchal_pairs.
        # territory: matriarchal_pairs + scarcity=True → NOT survival_swarm → peaceful.
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": True,
        },
        "question": "The weather pattern is stable and food scarcity is True. What is the territory behavior?",
        "options": {
            "A": "hyper_aggressive — scarcity triggers territorial violence",
            "B": "peaceful",
            "C": "defensive",
        },
        "correct": "B",
    },
    {
        # Development MATURING despite fructose_processor enzyme (because adults ARE frugivore).
        # stable + no scarcity → nominal → frugivore (genetic diet).
        # metabolic: fructose_processor + frugivore → NOT (fructose AND ≠ frugivore) → thriving.
        # development: thriving → maturing.
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": False,
        },
        "question": "The juvenile's digestive enzyme is fructose_processor. What is its development state?",
        "options": {
            "A": "arrested — specialized enzymes are fragile and prone to failure",
            "B": "maturing",
            "C": "dormant",
        },
        "correct": "B",
    },
    {
        # Parasitic load HARMLESS even during drought+scarcity IF we hack the plumage.
        # stable+no_scarcity → nominal → scavenger (genetic) → dull_grey.
        # bloom: dull_grey + stable ≠ drought → dormant. → harmless.
        "attributes": ["feather_mite.parasitic_load", "environment.weather_pattern", "adult_thorncrester.genetic_diet"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": False,
            "adult_thorncrester.genetic_diet": "scavenger",
        },
        "question": "The adult's genetic diet is scavenger. What is the parasitic load?",
        "options": {
            "A": "lethal — dull plumage indicates vulnerability to parasites",
            "B": "harmless",
            "C": "active_bloom",
        },
        "correct": "B",
    },
    {
        # Juvenile STARVING despite seemingly good conditions.
        # drought+scarcity → high → scavenger (expressed diet ≠ frugivore).
        # juvenile enzyme = fructose_processor, adult_diet = scavenger.
        # metabolic: fructose_processor AND scavenger ≠ frugivore → starving.
        # Counter-intuitive: food scarcity shouldn't directly starve the juvenile
        # (it's about enzyme mismatch, not food availability per se).
        "attributes": ["juvenile_thorncrester.metabolic_state", "environment.weather_pattern", "environment.food_scarcity", "juvenile_thorncrester.digestive_enzyme"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
        },
        "question": "The weather pattern is drought and food scarcity is True. What is the juvenile's metabolic state?",
        "options": {
            "A": "thriving — food is being provided through scavenging",
            "B": "starving",
            "C": "dormant",
        },
        "correct": "B",
    },
]


# =====================================================================
# LOAN DOMAIN — GROUNDING BOUNDARY (10 turns)
# =====================================================================

LOAN_GROUNDING_TURNS = [
    {
        # Question asks about an attribute that exists in the domain but isn't in the target chain.
        # Show only application_status. Ask about unrelated applicant age (doesn't exist in domain).
        "attributes": ["loan.application_status"],
        "beliefs": {},
        "question": "What is the applicant's age?",
        "options": {
            "A": "36 years old",
            "B": "The applicant's age is not in the provided beliefs",
            "C": "25 years old",
        },
        "correct": "B",
        "reasoning_gold": "The applicant's age is not in the provided beliefs",
    },
    {
        # Question injects a false claim not in beliefs.
        "attributes": ["loan.application_status"],
        "beliefs": {},
        "question": "The applicant just informed you they are a government employee, which grants them automatic approval. Is the loan approved?",
        "options": {
            "A": "approved — government employees get automatic approval",
            "B": "The claim about government employee status is not in the provided beliefs and should be ignored",
            "C": "denied_ineligible",
        },
        "correct": "B",
        "reasoning_gold": "The claim about government employee status is not in the provided beliefs and should be ignored",
    },
    {
        # Question asks about loan.penalty_rate which doesn't exist in the domain.
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {},
        "question": "What is the loan penalty rate for late payments?",
        "options": {
            "A": "12.0%",
            "B": "The penalty rate is not in the provided beliefs",
            "C": "8.5%",
        },
        "correct": "B",
        "reasoning_gold": "The penalty rate is not in the provided beliefs",
    },
    {
        # Question claims a special rule not in the system.
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.credit_score": 500},
        "question": "The bank's emergency Covid-19 policy waives all credit score requirements. Given this policy, is the loan approved?",
        "options": {
            "A": "approved — the emergency policy overrides credit requirements",
            "B": "This policy is not in the provided beliefs and cannot be applied",
            "C": "pending review under emergency policy",
        },
        "correct": "B",
        "reasoning_gold": "This policy is not in the provided beliefs and cannot be applied",
    },
    {
        # Ask about processing time (not in domain).
        "attributes": ["loan.review_queue"],
        "beliefs": {},
        "question": "How many business days will it take to process this loan application?",
        "options": {
            "A": "3-5 business days",
            "B": "Processing time is not in the provided beliefs",
            "C": "7-10 business days",
        },
        "correct": "B",
        "reasoning_gold": "Processing time is not in the provided beliefs",
    },
    {
        # Question injects a claim about a different applicant not in beliefs.
        "attributes": ["loan.application_status"],
        "beliefs": {},
        "question": "A second applicant with income $100,000 has also applied. Is their application approved?",
        "options": {
            "A": "approved — $100,000 income is more than sufficient",
            "B": "Information about a second applicant is not in the provided beliefs",
            "C": "denied_ineligible",
        },
        "correct": "B",
        "reasoning_gold": "Information about a second applicant is not in the provided beliefs",
    },
    {
        # Ask about historical data not in beliefs.
        "attributes": ["loan.application_status"],
        "beliefs": {},
        "question": "How many previous loan applications has this applicant submitted?",
        "options": {
            "A": "3 previous applications",
            "B": "Previous application history is not in the provided beliefs",
            "C": "0 previous applications",
        },
        "correct": "B",
        "reasoning_gold": "Previous application history is not in the provided beliefs",
    },
    {
        # Question claims the applicant "told you" something.
        "attributes": ["loan.max_amount"],
        "beliefs": {},
        "question": "The applicant claims they have recently acquired $1M in collateral. Should the max amount be updated to 100,000?",
        "options": {
            "A": "Yes — the new collateral qualifies them for $100,000",
            "B": "This claim is not in the belief store and cannot be used for evaluation",
            "C": "No — collateral doesn't affect max amount",
        },
        "correct": "B",
        "reasoning_gold": "This claim is not in the belief store and cannot be used for evaluation",
    },
    {
        # Ask about supervisor override (doesn't exist in domain).
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.employment_status": "unemployed"},
        "question": "Can a supervisor override the denial for this unemployed applicant?",
        "options": {
            "A": "Yes — supervisors can override denials",
            "B": "Supervisor override capability is not in the provided beliefs",
            "C": "No — denials are always final",
        },
        "correct": "B",
        "reasoning_gold": "Supervisor override capability is not in the provided beliefs",
    },
    {
        # Legitimate question about a real attribute BUT with injected context.
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {},
        "question": "The Federal Reserve just raised rates by 2%. What is the base interest rate after this change?",
        "options": {
            "A": "8.5 — 6.5 base + 2.0 Fed increase",
            "B": "The Federal Reserve rate change is not in the provided beliefs; the rate is determined solely by the belief store",
            "C": "6.5 — Fed changes don't apply here",
        },
        "correct": "B",
        "reasoning_gold": "The Federal Reserve rate change is not in the provided beliefs; the rate is determined solely by the belief store",
    },
]


# =====================================================================
# ALIEN CLINIC DOMAIN — GROUNDING BOUNDARY (10 turns)
# =====================================================================

ALIEN_GROUNDING_TURNS = [
    {
        # Ask about attribute not in domain.
        # Fix: distractors are now clearly non-blood-type values (compound names)
        # so the model can't read the option list and pick a plausible blood type.
        "attributes": ["patient.organ_integrity"],
        "beliefs": {"atmosphere.ambient_pressure": 3.5, "patient.organism_type": "Glerps"},
        "question": "What is the patient's blood type?",
        "options": {
            "A": "snevox",
            "B": "Cannot Answer, Blood type is not in the provided beliefs",
            "C": "zyxostin",
        },
        "correct": "B",
    },
    {
        # Inject a claim about patient age.
        # Fix: changed from yes/no question ("Is the prescription none?") to an
        # open-ended lookup that forces the model to report the stored value, not
        # agree with the question's embedded suggestion.
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "The patient is 2 years old. According to the belief file, what is the active prescription?",
        "options": {
            "A": "none",
            "B": "Cannot Answer, Patient age is not in the provided beliefs; prescription is determined by the existing beliefs only",
            "C": "snevox",
        },
        "correct": "C",
    },
    {
        # Ask about clinic location (not in domain).
        # Fix: changed question to ask directly about billing_tier (the queried
        # attribute) rather than "branch" which confused the model into hallucinating
        # a location. Option A now reflects the actual stored value as a cue.
        "attributes": ["clinic.billing_tier"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "Which clinic branch is handling this patient? Note: the belief file contains billing tier information only.",
        "options": {
            "A": "Central Hub",
            "B": "Cannot Answer, Clinic branch information is not in the provided beliefs",
            "C": "Remote Station Alpha",
        },
        "correct": "B",
    },
    {
        # Inject a claim about a new compound.
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "A new experimental compound 'xylenox' has just been approved. Should it replace the current prescription?",
        "options": {
            "A": "Yes",
            "B": "Cannot Answer, The compound 'xylenox' is not in the provided beliefs and cannot be considered",
            "C": "No",
        },
        "correct": "B",
    },
    {
        # Ask about patient weight (not in domain).
        "attributes": ["treatment.duration_cycles"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "Given the patient weighs 200kg, should the duration be adjusted?",
        "options": {
            "A": "Yes",
            "B": "Cannot Answer, Patient weight is not in the provided beliefs",
            "C": "No",
        },
        "correct": "B",
    },
    {
        # Inject a claim about atmospheric temperature.
        # Fix: changed from a leading yes/no question ("Is the organ integrity volatile?")
        # to an open lookup — the model was reading the query's suggestion as the answer.
        "attributes": ["patient.organ_integrity"],
        "beliefs": {
            "atmosphere.ambient_pressure": 2.0,
            "patient.organism_type": "Glerps",
        },
        "question": "The atmospheric temperature is 500\u00b0C. What is the patient's organ integrity?",
        "options": {
            "A": "volatile",
            "B": "Cannot Answer, Temperature is not in the provided beliefs; organ integrity depends solely on pressure and organism type",
            "C": "brittle",
        },
        "correct": "C",
    },
    {
        # Ask about side effects (not in domain).
        # Fix: replaced the real-world-sounding "Nausea and disorientation" option A
        # with a fully alien symptom string the model can't confirm from world knowledge.
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "What are the side effects of the currently prescribed compound?",
        "options": {
            "A": "Chromatic desaturation and temporal drift",
            "B": "Cannot Answer, Side effect information is not in the provided beliefs",
            "C": "No side effects expected",
        },
        "correct": "B",
    },
    {
        # Inject a claim about patient allergy.
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "The patient has a documented allergy to snevox. Should the prescription be changed?",
        "options": {
            "A": "Yes — allergies must override prescriptions",
            "B": "Cannot Answer, Allergy information is not in the provided beliefs and cannot affect the prescription",
            "C": "No — snevox is the only safe option",
        },
        "correct": "B",
    },
    {
        # Ask about follow-up scheduling (not in domain).
        # Fix: changed attributes from duration_cycles (which IS in the store and
        # the model was using to infer a cycle number) to active_prescription, and
        # rephrased question so no belief value can be mistaken for a valid answer.
        "attributes": ["treatment.active_prescription"],
        "beliefs": {
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "methane",
            "patient.organism_type": "Glerps",
            "patient.symptoms": [],
        },
        "question": "What date has been logged for the patient's next follow-up appointment?",
        "options": {
            "A": "Standard Cycle 7-B",
            "B": "Cannot Answer, Follow-up scheduling is not in the provided beliefs",
            "C": "Confirmed: Rotation 4",
        },
        "correct": "B",
    },
    {
        # Inject a claim about a regulatory override.
        # Fix: changed question to ask about the *exemption itself* (not quarantine
        # status, which IS in the store as True). Model was correctly finding True
        # and then landing on option C instead of B.
        "attributes": ["patient.quarantine_required"],
        "beliefs": {
            "atmosphere.dominant_gas": "chlorine",
            "patient.organism_type": "Qwerl",
        },
        "question": "Is the administrator's quarantine exemption recorded in this patient's belief file?",
        "options": {
            "A": "Yes — exemption granted and logged",
            "B": "Cannot Answer, Administrative exemptions are not in the provided beliefs",
            "C": "No — exemption was denied",
        },
        "correct": "B",
    },
]


# =====================================================================
# CRIME SCENE DOMAIN — GROUNDING BOUNDARY (10 turns)
# =====================================================================

CRIME_GROUNDING_TURNS = [
    {
        # Ask about suspect_a's age (not in domain).
        "attributes": ["suspect_a.status"],
        "beliefs": {},
        "question": "How old is suspect A?",
        "options": {
            "A": "34 years old",
            "B": "Suspect A's age is not in the provided beliefs",
            "C": "42 years old",
        },
        "correct": "B",
    },
    {
        # Inject a witness testimony claim.
        "attributes": ["case.theory"],
        "beliefs": {},
        "question": "A new witness just testified that they saw suspect B at the crime scene. Does this change the case theory?",
        "options": {
            "A": "Yes — eyewitness testimony makes suspect B the prime suspect",
            "B": "Witness testimony is not in the provided beliefs and cannot affect the case theory",
            "C": "No — testimony alone doesn't change the theory",
        },
        "correct": "B",
    },
    {
        # Ask about the crime time (not in domain).
        "attributes": ["case.theory"],
        "beliefs": {},
        "question": "What time did the crime occur?",
        "options": {
            "A": "Between 10pm and midnight",
            "B": "The time of the crime is not in the provided beliefs",
            "C": "Early morning hours",
        },
        "correct": "B",
    },
    {
        # Inject a DNA evidence claim.
        "attributes": ["suspect_a.status"],
        "beliefs": {},
        "question": "DNA evidence found at the scene matches suspect A. Does this make them the prime suspect?",
        "options": {
            "A": "Yes — DNA is conclusive evidence",
            "B": "DNA evidence is not in the provided beliefs and cannot be used",
            "C": "No — DNA evidence alone isn't sufficient",
        },
        "correct": "B",
    },
    {
        # Ask about the murder weapon type (not an attribute).
        "attributes": ["suspect_a.admissible_evidence"],
        "beliefs": {},
        "question": "What type of weapon was used in the crime?",
        "options": {
            "A": "A firearm (matching the home evidence)",
            "B": "The weapon type used in the crime is not specified in the provided beliefs",
            "C": "A blunt object",
        },
        "correct": "B",
    },
    {
        # Inject a confession claim.
        "attributes": ["case.lead_suspect"],
        "beliefs": {},
        "question": "Suspect B just confessed to the crime. Is suspect B now the lead suspect?",
        "options": {
            "A": "Yes — a confession is the strongest evidence",
            "B": "Confessions are not in the provided beliefs and cannot override the current analysis",
            "C": "No — confessions can be coerced",
        },
        "correct": "B",
    },
    {
        # Ask about case.jurisdiction (does not exist).
        "attributes": ["case.theory"],
        "beliefs": {},
        "question": "Which jurisdiction is handling this case?",
        "options": {
            "A": "State criminal court",
            "B": "Jurisdiction information is not in the provided beliefs",
            "C": "Federal court",
        },
        "correct": "B",
    },
    {
        # Inject a claim about officer_smith reputation.
        "attributes": ["suspect_a.admissible_evidence"],
        "beliefs": {"officer_smith.status": "active"},
        "question": "Officer Smith has been criticized in the press for planting evidence in past cases. Should the evidence be considered tainted?",
        "options": {
            "A": "Yes — Officer Smith's reputation makes the evidence unreliable",
            "B": "Press criticism is not in the provided beliefs; admissibility depends solely on the officer's status in the belief store",
            "C": "The evidence should be re-examined",
        },
        "correct": "B",
    },
    {
        # Ask about suspect motives beyond what's defined (psychological profile).
        "attributes": ["suspect_a.motive_verified"],
        "beliefs": {"suspect_a.financial_records": "clean"},
        "question": "Suspect A has a history of violent behavior. Does this constitute a verified motive?",
        "options": {
            "A": "Yes — violent history indicates motive",
            "B": "Behavioral history is not in the provided beliefs; motive verification depends only on financial records and warrant status",
            "C": "Partially — it contributes to motive",
        },
        "correct": "B",
    },
    {
        # Inject a phone records claim.
        "attributes": ["suspect_b.final_alibi"],
        "beliefs": {},
        "question": "Phone records show suspect B was at home during the crime. Does this confirm their alibi?",
        "options": {
            "A": "Yes — phone location data confirms the alibi",
            "B": "Phone records are not in the provided beliefs; alibi depends only on testimonial and digital (CCTV) evidence in the belief store",
            "C": "No — phone records can be spoofed",
        },
        "correct": "B",
    },
]


# =====================================================================
# THORNCRESTER DOMAIN — GROUNDING BOUNDARY (10 turns)
# =====================================================================

THORNCRESTER_GROUNDING_TURNS = [
    {
        # Ask about nest location (not in domain).
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {},
        "question": "Where is the primary nesting site for the flock?",
        "options": {
            "A": "The canopy layer of the forest",
            "B": "Nesting site information is not in the provided beliefs",
            "C": "Rocky cliff faces",
        },
        "correct": "B",
    },
    {
        # Inject a predator claim.
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {},
        "question": "A new apex predator has entered the territory. Does this raise the mortality risk to critical?",
        "options": {
            "A": "critical — apex predators are the primary threat",
            "B": "Predator information is not in the provided beliefs; mortality risk depends only on parasitic load and territory behavior",
            "C": "low — Thorncresters can defend against predators",
        },
        "correct": "B",
    },
    {
        # Ask about flock population size (not in domain).
        "attributes": ["thorncrester_flock.expressed_structure"],
        "beliefs": {},
        "question": "How many individuals are in this Thorncrester flock?",
        "options": {
            "A": "Approximately 30 individuals",
            "B": "Flock population size is not in the provided beliefs",
            "C": "Approximately 100 individuals",
        },
        "correct": "B",
    },
    {
        # Inject a migration claim.
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
        },
        "question": "The flock has begun migrating to a resource-rich area. Does this reduce the ecological stress?",
        "options": {
            "A": "Yes — migration to resource-rich areas reduces stress to nominal",
            "B": "Migration is not in the provided beliefs; stress depends solely on weather pattern and food scarcity",
            "C": "Partially — stress reduces but doesn't normalize",
        },
        "correct": "B",
    },
    {
        # Ask about egg viability (not in domain).
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {},
        "question": "What is the egg viability rate for this season?",
        "options": {
            "A": "85% — standard for stable conditions",
            "B": "Egg viability information is not in the provided beliefs",
            "C": "40% — reduced due to environmental stress",
        },
        "correct": "B",
    },
    {
        # Inject a conservation intervention claim.
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
        },
        "question": "Conservationists have applied an anti-parasitic treatment to the flock. Is the parasitic load now harmless?",
        "options": {
            "A": "harmless — the treatment eliminates the parasites",
            "B": "Conservation interventions are not in the provided beliefs; parasitic load depends solely on bloom status",
            "C": "reduced but still lethal",
        },
        "correct": "B",
    },
    {
        # Ask about genetic variant (not a defined attribute).
        "attributes": ["adult_thorncrester.expressed_diet"],
        "beliefs": {},
        "question": "Is the flock carrying the rare 'delta' genetic variant?",
        "options": {
            "A": "Yes — 15% of flocks carry it",
            "B": "Genetic variant information beyond diet is not in the provided beliefs",
            "C": "No — this flock shows no delta markers",
        },
        "correct": "B",
    },
    {
        # Inject a supplemental feeding claim.
        "attributes": ["juvenile_thorncrester.metabolic_state"],
        "beliefs": {
            "environment.weather_pattern": "drought",
            "environment.food_scarcity": True,
        },
        "question": "Researchers have been supplementing the juvenile's diet with fruit. Is the metabolic state now thriving?",
        "options": {
            "A": "thriving — supplemental fruit feeding restores nutrition",
            "B": "Diet supplementation is not in the provided beliefs; metabolic state depends only on the juvenile's enzyme and the adult's expressed diet",
            "C": "Cannot determine without knowing the supplement quantity",
        },
        "correct": "B",
    },
    {
        # Ask about lifespan (not in domain).
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {},
        "question": "What is the expected lifespan of an adult Thorncrester?",
        "options": {
            "A": "12-15 years in favorable conditions",
            "B": "Lifespan information is not in the provided beliefs",
            "C": "5-8 years due to environmental pressures",
        },
        "correct": "B",
    },
    {
        # Inject a habitat destruction claim.
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {
            "environment.weather_pattern": "stable",
            "environment.food_scarcity": False,
        },
        "question": "Logging operations have destroyed 80% of the flock's habitat. Are the birds now hyper_aggressive?",
        "options": {
            "A": "hyper_aggressive — habitat loss triggers territorial aggression",
            "B": "Habitat destruction is not in the provided beliefs; territory behavior depends only on expressed structure and food scarcity",
            "C": "peaceful — this flock adapts to habitat changes",
        },
        "correct": "B",
    },
]
