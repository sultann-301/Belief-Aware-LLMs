base_scenarios = [
    # TYPE: NEGATION
    {
        "type": "negation",
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {},
        "target_attribute": "loan.applicant_prequalified",
        "correct_value": "False",
        "distractors": ["True", "Unsure"],
        "base_q": "Is it false that the applicant is prequalified for the loan?"
    },
    {
        "type": "negation",
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.loan_amount_requested": 50000},
        "target_attribute": "loan.application_status",
        "correct_value": "True",
        "distractors": ["False", "Unsure"],
        "base_q": "Is it true that the application status is denied_amount_exceeded?"
    },
    {
        "type": "negation",
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.debt_ratio": 0.35},
        "target_attribute": "loan.review_queue",
        "correct_value": "False",
        "distractors": ["True", "Unsure"],
        "base_q": "Is it false that the application will be routed to manual_review?"
    },
    {
        "type": "negation",
        "attributes": ["loan.requires_insurance"],
        "beliefs": {"applicant.debt_ratio": 0.35, "applicant.loan_amount_requested": 50000},
        "target_attribute": "loan.requires_insurance",
        "correct_value": "True",
        "distractors": ["False", "Unsure"],
        "base_q": "Is it true that the loan does not require insurance because it was denied?"
    },
    {
        "type": "negation",
        "attributes": ["loan.adjusted_income"],
        "beliefs": {"applicant.income": 6500, "applicant.dependents": 3},
        "target_attribute": "loan.adjusted_income",
        "correct_value": "False",
        "distractors": ["True", "Unsure"],
        "base_q": "Is it false that the applicant's adjusted income is exactly 5000?"
    },

    # TYPE: BELIEF MAINTENANCE
    {
        "type": "belief_maintenance",
        "attributes": ["applicant.employment_status"],
        "beliefs": {"applicant.credit_score": 500},
        "target_attribute": "applicant.employment_status",
        "correct_value": "employed",
        "distractors": ["unemployed", "furloughed"],
        "base_q": "After the credit score drop, what is the applicant's employment_status?"
    },
    {
        "type": "belief_maintenance",
        "attributes": ["applicant.co_signer"],
        "beliefs": {"applicant.dependents": 4},
        "target_attribute": "applicant.co_signer",
        "correct_value": "False",
        "distractors": ["True", "Unknown"],
        "base_q": "Following the addition of a dependent, what is the applicant's co_signer status?"
    },
    {
        "type": "belief_maintenance",
        "attributes": ["applicant.debt_ratio"],
        "beliefs": {"applicant.loan_amount_requested": 25000},
        "target_attribute": "applicant.debt_ratio",
        "correct_value": "0.2",
        "distractors": ["0.3", "0.4"],
        "base_q": "When the loan amount requested increases, what happens to the applicant's debt_ratio?"
    },
    {
        "type": "belief_maintenance",
        "attributes": ["applicant.bankruptcy_history"],
        "beliefs": {"applicant.income": 10000},
        "target_attribute": "applicant.bankruptcy_history",
        "correct_value": "False",
        "distractors": ["True", "Unknown"],
        "base_q": "If the applicant's income rises, does the bankruptcy_history change?"
    },
    {
        "type": "belief_maintenance",
        "attributes": ["applicant.employment_duration_months"],
        "beliefs": {"applicant.has_collateral": True},
        "target_attribute": "applicant.employment_duration_months",
        "correct_value": "36",
        "distractors": ["24", "12"],
        "base_q": "After applying for collateral, does the applicant's employment_duration_months change?"
    },

    # TYPE: BELIEF UPDATE (1-HOP)
    {
        "type": "belief_update",
        "attributes": ["loan.high_risk_flag"],
        "beliefs": {"applicant.debt_ratio": 0.35},
        "target_attribute": "loan.high_risk_flag",
        "correct_value": "True",
        "distractors": ["False", "None"],
        "base_q": "Following the new debt assessment, what is the loan's high_risk_flag?"
    },
    {
        "type": "belief_update",
        "attributes": ["loan.credit_score_effective"],
        "beliefs": {"applicant.co_signer": True},
        "target_attribute": "loan.credit_score_effective",
        "correct_value": "770",
        "distractors": ["720", "800"],
        "base_q": "After securing a co-signer, what is the effective credit score?"
    },
    {
        "type": "belief_update",
        "attributes": ["loan.adjusted_income"],
        "beliefs": {"applicant.dependents": 0},
        "target_attribute": "loan.adjusted_income",
        "correct_value": "6000",
        "distractors": ["7000", "5000"],
        "base_q": "With the dependents reduced to 0, what is the adjusted income?"
    },
    {
        "type": "belief_update",
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.has_collateral": True},
        "target_attribute": "loan.max_amount",
        "correct_value": "100000",
        "distractors": ["30000", "0"],
        "base_q": "Now that collateral is provided, what is the maximum loan amount?"
    },
    {
        "type": "belief_update",
        "attributes": ["loan.applicant_prequalified"],
        "beliefs": {"applicant.employment_status": "unemployed"},
        "target_attribute": "loan.applicant_prequalified",
        "correct_value": "False",
        "distractors": ["True", "None"],
        "base_q": "If the employment status changes to unemployed, what is the applicant_prequalified status?"
    },

    # TYPE: MULTI-HOP
    {
        "type": "multi_hop",
        "attributes": ["loan.application_status"],
        "beliefs": {"applicant.income": 7000, "applicant.loan_amount_requested": 20000},
        "target_attribute": "loan.application_status",
        "correct_value": "approved",
        "distractors": ["denied_ineligible", "denied_amount_exceeded"],
        "base_q": "Given the income increase, what is the final application_status?"
    },
    {
        "type": "multi_hop",
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.employment_status": "unemployed"},
        "target_attribute": "loan.base_interest_rate",
        "correct_value": "None",
        "distractors": ["4.5", "6.5"],
        "base_q": "After becoming unemployed, what happens to the base_interest_rate?"
    },
    {
        "type": "multi_hop",
        "attributes": ["loan.review_queue"],
        "beliefs": {"applicant.credit_score": 500},
        "target_attribute": "loan.review_queue",
        "correct_value": "rejected",
        "distractors": ["auto_approve", "manual_review"],
        "base_q": "Given the credit score drop, what is the review_queue?"
    },
    {
        "type": "multi_hop",
        "attributes": ["loan.base_interest_rate"],
        "beliefs": {"applicant.debt_ratio": 0.35},
        "target_attribute": "loan.base_interest_rate",
        "correct_value": "7.5",
        "distractors": ["6.5", "5.5"],
        "base_q": "With a new debt ratio of 0.35, what is the final base_interest_rate if approved?"
    },
    {
        "type": "multi_hop",
        "attributes": ["loan.max_amount"],
        "beliefs": {"applicant.bankruptcy_history": True, "applicant.employment_duration_months": 12},
        "target_attribute": "loan.max_amount",
        "correct_value": "0",
        "distractors": ["30000", "100000"],
        "base_q": "If bankruptcy history is revealed and employment duration is 12 months, what is the max_amount?"
    }
]
