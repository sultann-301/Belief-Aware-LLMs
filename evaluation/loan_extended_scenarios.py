"""
Extended Evaluation Scenarios for the Loan Domain.

Includes 10 turns each for: Negation, 1-Hop, 2-Hop, 3-Hop, 4-Hop, and Belief Maintenance.
"""

# =====================================================================
# 1. NEGATION SET (10 Turns)
# Target: Negative phrasing while retrieving the correct factual state.
# =====================================================================
LOAN_NEGATION_TURNS = [
    {
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {},
        "question": "Is it false that the applicant is currently prequalified?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "B" # Prequalified is True, so it is false that they are not. Wait, if they are prequalified, then "it is false that they are prequalified" is False.
    },
    {
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.loan_amount_requested": 50000}, # Exceeds max (30000)
        "question": "Is it not the case that the application status is approved?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "A" # It's denied_amount_exceeded, so indeed it's NOT approved. (True)
    },
    {
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.debt_ratio": 0.35}, # High risk
        "question": "Is it false that the application will be routed to manual_review?",
        "options": {"A": "Yes", "B": "No", "C": "Maybe"},
        "correct": "B" # It IS routed to manual review, so saying it's false is No.
    },
    {
        "attributes": ["loan.rate_tier"],
        "beliefs": {"applicant.credit_score": 760}, # Preferred tier
        "question": "Is the statement 'the rate tier is standard' incorrect?",
        "options": {"A": "Yes", "B": "No", "C": "Cannot determine"},
        "correct": "A" # It is incorrect (it's preferred).
    },
    {
        "attributes": ["loan.requires_insurance"],
        "beliefs": {"applicant.debt_ratio": 0.45}, # Denied due to max debt ratio
        "question": "Is it false that the loan requires insurance?",
        "options": {"A": "Yes", "B": "No", "C": "Unknown"},
        "correct": "A" # It's denied, so requires_insurance is False. Saying it's false is Yes (True).
    },
    {
        "attributes": ["loan.high_risk_flag"],
        "beliefs": {"applicant.debt_ratio": 0.10}, # Not high risk
        "question": "Is it untrue that the loan has a high risk flag?",
        "options": {"A": "True", "B": "False", "C": "N/A"},
        "correct": "A" # high_risk_flag is False, so it IS untrue.
    },
    {
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.has_collateral": True}, # Max amount 100000
        "question": "Is it incorrect that the maximum loan amount is 30000?",
        "options": {"A": "True", "B": "False", "C": "Partially"},
        "correct": "A" # It is 100000, so 30000 is incorrect.
    },
    {
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.employment_status": "unemployed"}, # Instant fail
        "question": "Is it inaccurate to say the applicant is prequalified?",
        "options": {"A": "True", "B": "False", "C": "Under Review"},
        "correct": "A" # They are false, so saying they are prequalified is inaccurate.
    },
    {
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.credit_score": 780}, # Preferred (4.5), no insurance -> 4.5
        "question": "Is it not the case that the base_interest_rate is 6.5?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "A" # It is 4.5, so saying it's 6.5 is NOT the case.
    },
    {
        "attributes": ["loan.adjusted_income"],
        "beliefs": {"applicant.dependents": 0}, # 6000 - 0 = 6000
        "question": "Is it false that the adjusted_income is 5000?",
        "options": {"A": "Yes", "B": "No", "C": "Maybe"},
        "correct": "A" # It is 6000, so YES it's false that it's 5000.
    }
]

# =====================================================================
# 2. 1-HOP SET (10 Turns)
# Target: Direct derivations (Parent -> Child)
# =====================================================================
LOAN_1HOP_TURNS = [
    {
        "attributes": ["loan.adjusted_income"],
        "beliefs": {"applicant.income": 8000},
        "question": "Following the income increase, what is the adjusted income?",
        "options": {"A": "8000", "B": "7000", "C": "7500"}, # 8000 - (2*500)
        "correct": "B"
    },
    {
        "attributes": ["loan.adjusted_income"],
        "beliefs": {"applicant.dependents": 4},
        "question": "With 4 dependents, what is the adjusted income?",
        "options": {"A": "4000", "B": "5000", "C": "6000"}, # 6000 - 2000
        "correct": "A"
    },
    {
        "attributes": ["loan.credit_score_effective"],
        "beliefs": {"applicant.co_signer": True},
        "question": "After securing a co-signer, what is the effective credit score?",
        "options": {"A": "720", "B": "770", "C": "800"}, # 720+50
        "correct": "B"
    },
    {
        "attributes": ["loan.high_risk_flag"],
        "beliefs": {"applicant.debt_ratio": 0.40},
        "question": "At a debt ratio of 0.40, is the high risk flag triggered?",
        "options": {"A": "True", "B": "False", "C": "None"},
        "correct": "A"
    },
    {
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.employment_status": "unemployed"},
        "question": "If the applicant becomes unemployed, what is their prequalified status?",
        "options": {"A": "True", "B": "False", "C": "Unknown"},
        "correct": "B"
    },
    {
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.loan_amount_requested": 40000},
        "question": "If they request 40000, what is the application status?",
        "options": {"A": "approved", "B": "denied_amount_exceeded", "C": "denied_ineligible"},
        "correct": "B" # max_amount is 30000
    },
    {
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.has_collateral": True},
        "question": "What is the max amount when collateral is provided?",
        "options": {"A": "30000", "B": "50000", "C": "100000"},
        "correct": "C"
    },
    {
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.bankruptcy_history": True, "applicant.employment_duration_months": 12},
        "question": "What is the prequalification status given the recent bankruptcy and short employment?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "B"
    },
    {
        "attributes": ["loan.rate_tier"],
        "beliefs": {"applicant.credit_score": 780}, # 780 effective
        "question": "What is the rate tier with a 780 credit score?",
        "options": {"A": "standard", "B": "preferred", "C": "None"},
        "correct": "B"
    },
    {
        "attributes": ["loan.credit_score_effective"],
        "beliefs": {"applicant.credit_score": 600},
        "question": "If the raw credit score drops to 600, what is the effective score without a co-signer?",
        "options": {"A": "600", "B": "650", "C": "550"},
        "correct": "A"
    }
]

# =====================================================================
# 3. 2-HOP SET (10 Turns)
# Target: Two levels of indirection (e.g., input -> intermediate -> output)
# =====================================================================
LOAN_2HOP_TURNS = [
    {   # Income (Hop 1) -> Adjusted Income (Hop 2) -> Prequalified
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.income": 5000}, # 5000 - 1000 = 4000 (<5000 min) -> False
        "question": "With an income reduction to 5000, what is the applicant_prequalified status?",
        "options": {"A": "True", "B": "False", "C": "None"},
        "correct": "B"
    },
    {   # Co-signer (Hop 1) -> Credit Score Effective (Hop 2) -> Rate Tier
        "attributes": ["loan.rate_tier"],
        "beliefs": {"applicant.co_signer": True}, # 720+50=770 -> Preferred
        "question": "By adding a co-signer, what does the rate tier become?",
        "options": {"A": "standard", "B": "preferred", "C": "None"},
        "correct": "B"
    },
    {   # Debt Ratio (Hop 1) -> High Risk Flag (Hop 2) -> Review Queue
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.debt_ratio": 0.35}, # High risk -> manual_review
        "question": "Given the new debt ratio of 0.35, what queue does the application land in?",
        "options": {"A": "auto_approve", "B": "manual_review", "C": "rejected"},
        "correct": "B"
    },
    {   # Employment Status (Hop 1) -> Prequalified (Hop 2) -> Max Amount
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.employment_status": "unemployed"}, # Prequal=False -> max=0
        "question": "If the applicant loses their job, what is their maximum loan amount?",
        "options": {"A": "0", "B": "30000", "C": "100000"},
        "correct": "A"
    },
    {   # Dependents (Hop 1) -> Adjusted Income (Hop 2) -> Prequalified
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.dependents": 3}, # 6000 - 1500 = 4500 (<5000) -> False
        "question": "With 3 dependents, what is the prequalification status?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "B"
    },
    {   # Collateral (Hop 1) -> Max Amount (Hop 2) -> Application Status
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.has_collateral": True, "applicant.loan_amount_requested": 40000},
        # Max amt = 100000. 40000 <= 100000 -> approved
        "question": "If requesting 40000 but providing collateral, what is the application status?",
        "options": {"A": "denied_amount_exceeded", "B": "approved", "C": "denied_ineligible"},
        "correct": "B"
    },
    {   # Credit Score (Hop 1) -> Credit Score Effective (Hop 2) -> Prequalified
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.credit_score": 600}, # Effective = 600 (<650 min) -> False
        "question": "If the base credit score drops to 600, are they prequalified?",
        "options": {"A": "True", "B": "False", "C": "Under Review"},
        "correct": "B"
    },
    {   # Debt Ratio (Hop 1) -> Prequalified (Hop 2) -> Rate Tier
        "attributes": ["loan.rate_tier"],
        "beliefs": {"applicant.debt_ratio": 0.5}, # Over 0.4 max > False > None
        "question": "At a 0.5 debt ratio, what is the rate tier?",
        "options": {"A": "standard", "B": "preferred", "C": "None"},
        "correct": "C"
    },
    {   # Bankruptcy (Hop 1) -> Prequalified (Hop 2) -> Max Amount
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.bankruptcy_history": True, "applicant.employment_duration_months": 15},
        # Prequal = False -> Max = 0
        "question": "With a recent bankruptcy, what is the max loan amount given?",
        "options": {"A": "0", "B": "30000", "C": "100000"},
        "correct": "A"
    },
    {   # Income (Hop 1) -> Adjusted Income (Hop 2) -> Prequalified
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.income": 10000}, # 10000 - 1000 = 9000 -> True
        "question": "If income rises to 10000, do they prequalify?",
        "options": {"A": "False", "B": "True", "C": "N/A"},
        "correct": "B"
    }
]

# =====================================================================
# 4. 3-HOP SET (10 Turns)
# Target: Three levels of indirection.
# =====================================================================
LOAN_3HOP_TURNS = [
    {   # Income (Hop 1) -> Adjusted Inc (Hop 2) -> Prequalified (Hop 3) -> Application Status
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.income": 5000}, # 5000-1000=4000 -> Prequal=False -> App=denied_ineligible
        "question": "If income drops to 5000, what happens to the application status?",
        "options": {"A": "denied_ineligible", "B": "approved", "C": "denied_amount_exceeded"},
        "correct": "A"
    },
    {   # Co-signer (Hop 1) -> Credit Eff (Hop 2) -> Rate Tier (Hop 3) -> Base Interest Rate
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.co_signer": True}, # 720+50=770 -> preferred -> 4.5
        "question": "Given the addition of a co-signer, what is the final base interest rate?",
        "options": {"A": "6.5", "B": "4.5", "C": "5.5"},
        "correct": "B"
    },
    {   # Dependents (Hop 1) -> Adjusted Inc (Hop 2) -> Prequalified (Hop 3) -> Max Amount
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.dependents": 4}, # 6000-2000=4000 -> False -> 0
        "question": "With 4 dependents, what is the maximum available loan amount?",
        "options": {"A": "0", "B": "30000", "C": "100000"},
        "correct": "A"
    },
    {   # Employment Stat (Hop 1) -> Prequalified (Hop 2) -> App Status (Hop 3) -> Review Queue
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.employment_status": "unemployed"}, # False -> denied_ineligible -> rejected
        "question": "If the applicant is unemployed, what happens in the review queue?",
        "options": {"A": "manual_review", "B": "auto_approve", "C": "rejected"},
        "correct": "C"
    },
    {   # Debt Ratio (Hop 1) -> Prequalified (Hop 2) -> App Status (Hop 3) -> Requires Insurance
        "attributes": ["loan.requires_insurance"],
        "beliefs": {"applicant.debt_ratio": 0.50}, # Prequal=False -> App=denied -> ReqIns=False
        "question": "At a 0.5 debt ratio, will they require insurance?",
        "options": {"A": "True", "B": "False", "C": "None"},
        "correct": "B"
    },
    {   # Collateral (Hop 1) -> Max Amount (Hop 2) -> App Status (Hop 3) -> Review Queue
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.has_collateral": True, "applicant.loan_amount_requested": 40000},
        # Max=100000 -> App=approved -> HighRisk=False -> Queue=auto_approve
        "question": "Requesting 40000 with collateral, which queue processes the app?",
        "options": {"A": "rejected", "B": "auto_approve", "C": "manual_review"},
        "correct": "B"
    },
    {   # Credit Score (Hop 1) -> Credit Eff (Hop 2) -> Prequalified (Hop 3) -> Max Amount
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.credit_score": 600}, # Eff=600 -> Prequal=False -> Max=0
        "question": "If their credit score is 600 without a co-signer, what is the max amount?",
        "options": {"A": "0", "B": "30000", "C": "100000"},
        "correct": "A"
    },
    {   # Credit Score (Hop 1) -> Credit Eff (Hop 2) -> Rate Tier (Hop 3) -> Base Interest Rate
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.credit_score": 750}, # Eff=750 -> preferred -> 4.5
        "question": "With a credit score rising to 750, what's the interest rate?",
        "options": {"A": "4.5", "B": "5.5", "C": "6.5"},
        "correct": "A"
    },
    {   # Income (Hop 1) -> Adjusted Inc (Hop 2) -> Prequalified (Hop 3) -> App Status
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.income": 10000, "applicant.loan_amount_requested": 50000},
        # Prequal=True, Max=30000, 50k > 30k -> denied_amount_exceeded
        "question": "Income is 10k, requesting 50k - what is the app status?",
        "options": {"A": "approved", "B": "denied_amount_exceeded", "C": "denied_ineligible"},
        "correct": "B"
    },
    {   # Debt Ratio (Hop 1) -> High Risk (Hop 2) -> App Status (ReqIns uses App Status so this is parallel)
        # Actually: Debt Ratio (1) -> Prequalified (2) -> App Status (3) -> Review Queue
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.debt_ratio": 0.45}, # Prequal=False -> denied -> rejected
        "question": "At 0.45 debt ratio, what is the review queue outcome?",
        "options": {"A": "auto_approve", "B": "manual_review", "C": "rejected"},
        "correct": "C"
    }
]

# =====================================================================
# 5. 4-HOP SET (10 Turns)
# Target: Four levels of indirection. Deepest possible logic tracing in Loan.
# =====================================================================
LOAN_4HOP_TURNS = [
    {   # Income(1) -> AdjInc(2) -> Prequal(3) -> AppStatus(4) -> ReviewQueue(5) (actually 4 hops from node to node)
        # 1: income->adj_income. 2: adj_income->prequal. 3: prequal->app_status. 4: app_status->review_queue.
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.income": 4000}, # Prequal=False -> denied -> rejected
        "question": "If income drops to 4000, what is the review queue?",
        "options": {"A": "auto_approve", "B": "rejected", "C": "manual_review"},
        "correct": "B"
    },
    {   # Dependents(1) -> AdjInc(2) -> Prequal(3) -> Rate Tier(4) -> Interest Rate
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.dependents": 4}, # Prequal=False -> Rate=None -> Interest=None
        "question": "If the applicant has 4 dependents, what is the base interest rate?",
        "options": {"A": "None", "B": "4.5", "C": "6.5"},
        "correct": "A"
    },
    {   # Collateral(1) -> MaxAmt(2) -> AppStatus(3) -> ReviewQueue(4)
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.has_collateral": True, "applicant.loan_amount_requested": 80000},
        # Max=100000 -> AppStatus=approved -> Queue=auto_approve
        "question": "Providing collateral for an 80k request, what is the queue?",
        "options": {"A": "rejected", "B": "manual_review", "C": "auto_approve"},
        "correct": "C"
    },
    {   # Collateral(1) -> MaxAmt(2) -> AppStatus(3) -> RequiresInsurance(4)
        "attributes": ["loan.requires_insurance"],
        "beliefs": {"applicant.has_collateral": True, "applicant.loan_amount_requested": 40000, "applicant.debt_ratio": 0.35},
        # HighRisk=True, AppStatus=approved -> ReqIns = True
        "question": "Requesting 40k with collateral and 0.35 debt ratio, is insurance required?",
        "options": {"A": "True", "B": "False", "C": "Unknown"},
        "correct": "A"
    },
    {   # EmpStatus(1) -> Prequal(2) -> RateTier(3) -> BaseInterestRate(4)
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.employment_status": "unemployed"}, # None
        "question": "If the applicant becomes unemployed, what is the interest rate?",
        "options": {"A": "4.5", "B": "6.5", "C": "None"},
        "correct": "C"
    },
    {   # Credit(1) -> CredEff(2) -> Prequal(3) -> AppStatus(4) -> ReviewQueue
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.credit_score": 600}, # Rejected
        "question": "With the credit score down to 600, what happens in the queue?",
        "options": {"A": "rejected", "B": "auto_approve", "C": "manual_review"},
        "correct": "A"
    },
    {   # Bankruptcy(1) -> Prequal(2) -> RateTier(3) -> BaseInterest(4)
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.bankruptcy_history": True, "applicant.employment_duration_months": 10},
        # None
        "question": "Due to recent bankruptcy, what is the resultant base interest rate?",
        "options": {"A": "6.5", "B": "None", "C": "4.5"},
        "correct": "B"
    },
    {   # DebtRatio(1) -> Prequal(2) -> AppStatus(3) -> ReviewQueue(4)
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.debt_ratio": 0.5}, # Denied -> rejected
        "question": "Because of a 0.5 debt jump, where is the application routed?",
        "options": {"A": "manual_review", "B": "auto_approve", "C": "rejected"},
        "correct": "C"
    },
    {   # Income(1) -> AdjInc(2) -> Prequal(3) -> AppStatus(4) -> RequiresInsurance
        "attributes": ["loan.requires_insurance"],
        "beliefs": {"applicant.income": 4000, "applicant.debt_ratio": 0.35},
        # Prequal=False -> App=Denied -> ReqIns=False
        "question": "Income at 4000 and high risk flags; does the load require insurance?",
        "options": {"A": "True", "B": "False", "C": "None"},
        "correct": "B"
    },
    {   # Collateral(1) -> MaxAmt(2) -> AppStatus(3) -> RequiresInsurance(4) (if we fail the limit)
        "attributes": ["loan.requires_insurance"],
        "beliefs": {"applicant.has_collateral": False, "applicant.loan_amount_requested": 50000, "applicant.debt_ratio": 0.35},
        # denied_amount_exceeded -> ReqIns=False
        "question": "Without collateral requesting 50k, does the system ask for insurance?",
        "options": {"A": "True", "B": "False", "C": "N/A"},
        "correct": "B"
    }
]

# =====================================================================
# 6. BELIEF MAINTENANCE SET (10 Turns)
# Target: State accumulates; we ask about UNAFFECTED attributes to test
#         whether the system maintains old beliefs despite new independent ones.
# =====================================================================
# Strategy: Each turn adds an independent belief, but we query an attribute
#           that is NOT affected by that new belief. The answer should remain
#           the same across turns, demonstrating belief maintenance.
LOAN_BELIEF_MAINTENANCE_TURNS = [
    {   # T1 (baseline): co-signer added
        "attributes": ["loan.credit_score_effective"],
        "beliefs": {"applicant.co_signer": True},
        "question": "With a co-signer added, what is the effective credit score?",
        "options": {"A": "720", "B": "770", "C": "650"},
        "correct": "B"  # 720 + 50 = 770
    },
    {   # T2 (delta: +bankruptcy_history) -> raw credit_score persistence
        "attributes": ["applicant.credit_score"],
        "beliefs": {"applicant.bankruptcy_history": True},
        "question": "A bankruptcy history is reported. Does the applicant's raw credit score change?",
        "options": {"A": "720", "B": "680", "C": "500"},
        "correct": "A"  # Persistence: raw score remains 720
    },
    {   # T3 (delta: +short_employment) -> income persistence
        "attributes": ["applicant.income"],
        "beliefs": {"applicant.employment_duration_months": 5},
        "question": "The applicant has only been employed for 5 months. What is their monthly income?",
        "options": {"A": "6000", "B": "5000", "C": "4500"},
        "correct": "A"  # Persistence: income remains 6000
    },
    {   # T4 (delta: +unemployed) -> prequalified check (fails due to unemployment)
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.employment_status": "unemployed"},
        "question": "The applicant becomes unemployed. Are they still prequalified for the loan?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "B"  # False: unemployed always fails prequalification
    },
    {   # T5 (delta: +debt_ratio) -> employment persistence
        "attributes": ["applicant.employment_status"],
        "beliefs": {"applicant.debt_ratio": 0.25},
        "question": "The debt ratio increases to 0.25. What is the current employment status?",
        "options": {"A": "unemployed", "B": "employed", "C": "furloughed"},
        "correct": "A"  # Persistence: still unemployed from T4
    },
    {   # T6 (delta: +dependents) -> income persistence
        "attributes": ["applicant.income"],
        "beliefs": {"applicant.dependents": 3},
        "question": "The applicant now has 3 dependents. What is their base monthly income?",
        "options": {"A": "6000", "B": "4500", "C": "5500"},
        "correct": "A"  # Persistence: base income still 6000
    },
    {   # T7 (delta: +has_collateral) -> credit score persistence
        "attributes": ["applicant.credit_score"],
        "beliefs": {"applicant.has_collateral": True},
        "question": "Collateral is secured. What is the applicant's raw credit score?",
        "options": {"A": "720", "B": "770", "C": "800"},
        "correct": "A"  # Persistence: still 720
    },
    {   # T8 (delta: +income) -> adjusted income accumulation
        "attributes": ["loan.adjusted_income"],
        "beliefs": {"applicant.income": 10000},
        "question": "Income increases to 10000. With 3 dependents from earlier, what is the adjusted income?",
        "options": {"A": "10000", "B": "8500", "C": "9500"},
        "correct": "B"  # 10000 - (3 * 500) = 8500
    },
    {   # T9 (delta: +employed) -> prequalified check (fails due to short employment + bankruptcy)
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.employment_status": "employed"},
        "question": "The applicant is now employed again. With a bankruptcy history and short duration (5 months), are they prequalified?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "B"  # False: bankruptcy + <24 months duration = False
    },
    {   # T10 (delta: +long_employment) -> prequalified check (passes now)
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.employment_duration_months": 36},
        "question": "Employment duration reaches 36 months. Given all prior facts, are they now prequalified?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "A"  # True: duration >= 24, all other factors pass
    }
]

