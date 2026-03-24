# Belief-Aware LLM — Domain Specifications

This document defines the four handcrafted domains used to evaluate the belief revision system. Each domain uses the KV store + dependency map representation (`entity.attribute = value`). Rules are deterministic `derive_fn` functions.

---

## Domain 1: Loan Eligibility

### Purpose

The **baseline domain**. Threshold-based rules with clear pass/fail outcomes. Validates core architecture: insert, conflict detection, dirty propagation, lazy resolution.

### What It Tests

| Capability | How |
|---|---|
| Basic contradiction detection | Income changes → old value conflicts with new |
| Multi-hop revision | Income → income_eligible → loan_status → rate_tier (3 hops) |
| Conjunctive rules | Eligibility requires ALL conditions in one rule |
| Belief Maintain | Changing credit score should NOT affect employment status |

### Attributes (KV Keys)

| Key | Type | Example | How It Evolves |
|---|---|---|---|
| `applicant.income` | numeric | 3000, 6000 | Raises, job loss |
| `applicant.credit_score` | numeric | 520, 750 | Payments, defaults |
| `applicant.debt_ratio` | float | 0.15, 0.60 | New loans, payoffs |
| `applicant.employment_status` | str | employed, unemployed | Hiring, firing |
| `applicant.employment_duration_months` | numeric | 3, 36 | Time passing |
| `applicant.has_collateral` | bool | true, false | Asset purchase/sale |
| `applicant.loan_amount_requested` | numeric | 10000, 50000 | Applicant changes |
| `applicant.bankruptcy_history` | bool | true, false | Proceedings resolved |
| `applicant.co_signer` | bool | true, false | Co-signer agrees/withdraws |
| `loan.min_income` | numeric | 5000 | Policy |
| `loan.min_credit` | numeric | 650 | Policy |
| `loan.max_debt_ratio` | float | 0.4 | Policy |

### Rules

All conditions are consolidated per output key — no rule priority conflicts.

```
R1: loan.eligible
    inputs: [applicant.income, loan.credit_score_effective, applicant.debt_ratio,
             applicant.employment_status, applicant.bankruptcy_history,
             applicant.employment_duration_months,
             loan.min_income, loan.min_credit, loan.max_debt_ratio]
    logic:
      IF employment_status = "unemployed" → False
      IF bankruptcy_history = True AND employment_duration_months < 24 → False
      IF income >= min_income AND credit_score_effective >= min_credit AND debt_ratio < max_debt_ratio → True
      ELSE → False

R2: loan.credit_score_effective
    inputs: [applicant.credit_score, applicant.co_signer]
    logic:  credit_score + 50 if co_signer = True, else credit_score

R3: loan.rate_tier
    inputs: [loan.eligible, loan.credit_score_effective]
    logic:
      IF NOT eligible → None
      IF credit_score_effective >= 750 → "preferred"
      ELSE → "standard"

R4: loan.max_amount
    inputs: [loan.eligible, applicant.has_collateral]
    logic:
      IF NOT eligible → 0
      IF has_collateral → 100000
      ELSE → 30000

R5: loan.application_status
    inputs: [loan.eligible, applicant.loan_amount_requested, loan.max_amount]
    logic:
      IF NOT eligible → "denied_ineligible"
      IF loan_amount_requested > max_amount → "denied_amount_exceeded"
      ELSE → "approved"

R6: loan.high_risk_flag
    inputs: [applicant.debt_ratio]
    logic:  debt_ratio >= 0.3 → True, else False
```

### Dependency Chain

```
applicant.income ──→ loan.eligible ──→ loan.rate_tier
applicant.credit_score ──→ loan.credit_score_effective ──→ loan.eligible
applicant.co_signer ──→                                ──→ loan.rate_tier
applicant.debt_ratio ──→ loan.eligible
applicant.employment_status ──→
applicant.bankruptcy_history ──→
applicant.debt_ratio ──→ loan.high_risk_flag
                        loan.eligible ──→ loan.max_amount ──→ loan.application_status
```

### Example Revision Scenario

```
t=0: applicant.income = 3000, applicant.credit_score = 700, applicant.debt_ratio = 0.3
     → R1: 3000 < 5000 → loan.eligible = False
     → R3: not eligible → loan.rate_tier = None
     → R5: → loan.application_status = "denied_ineligible"

t=1: applicant.income updated to 6000
     → dirty: {loan.eligible, loan.rate_tier, loan.max_amount, loan.application_status}

t=2: resolve_all_dirty():
     → R1: 6000 >= 5000 ✓, credit_score_effective=700 >= 650 ✓, 0.3 < 0.4 ✓ → loan.eligible = True
     → R3: eligible, credit_score_effective=700 < 750 → loan.rate_tier = "standard"
     → R4: eligible, no collateral → loan.max_amount = 30000
     → R5: eligible, 10000 <= 30000 → loan.application_status = "approved"
```

---

## Domain 2: Employee Compliance & Role Eligibility

### Purpose

Tests **multi-prerequisite rules** and **cascading chains** from certification/training status changes. Temporal changes (cert expiry, training overdue) are simulated by the test harness directly updating the relevant keys.

### What It Tests

| Capability | How |
|---|---|
| Multi-hop chains | Cert expires → can_operate = false → project suspended |
| Independent belief maintenance | Revoking one cert should NOT affect unrelated clearances |
| Conjunctive rules with 3+ inputs | Role eligibility requires training + cert + experience |
| Simulated temporal changes | Test harness updates cert/training status to simulate time |

### Attributes (KV Keys)

| Key | Type | Example | How It Evolves |
|---|---|---|---|
| `employee.certification_safety` | str | valid, expired | Test harness simulates expiry |
| `employee.certification_cpa` | str | valid, expired | Test harness simulates expiry |
| `employee.training_hazmat` | str | completed, not_completed | Test harness simulates overdue |
| `employee.training_ethics` | str | completed, not_completed | Annual cycle |
| `employee.training_compliance` | str | completed, not_completed | Annual cycle |
| `employee.clearance_level` | str | none, basic, confidential, secret | Background checks |
| `employee.years_experience` | numeric | 1, 5 | Role changes |
| `employee.performance_rating` | str | exceeds, meets, below | Annual review |
| `employee.disciplinary_action` | bool | true, false | Incidents |
| `employee.background_check` | str | passed, pending, failed | Investigation results |
| `employee.department` | str | engineering, finance | Transfers |
| `employee.manager_approval_remote` | bool | true, false | Manager grants/revokes |

### Rules

```
R1: employee.can_operate_heavy_machinery
    inputs: [employee.certification_safety, employee.training_hazmat]
    logic:  certification_safety = "valid" AND training_hazmat = "completed"

R2: employee.project_factory_floor
    inputs: [employee.can_operate_heavy_machinery]
    logic:  "assigned" if can_operate = True, else "suspended"

R3: employee.eligible_senior_analyst
    inputs: [employee.clearance_level, employee.years_experience,
             employee.background_check]
    logic:  clearance_level in ("confidential", "secret")
            AND years_experience >= 3 AND background_check = "passed"

R4: employee.compliance_status
    inputs: [employee.training_ethics, employee.training_compliance]
    logic:  "compliant" if both = "completed", else "non_compliant"

R5: employee.promotion_eligible
    inputs: [employee.compliance_status, employee.performance_rating,
             employee.disciplinary_action]
    logic:  compliance_status = "compliant"
            AND performance_rating != "below"
            AND disciplinary_action = False

R6: employee.eligible_financial_auditor
    inputs: [employee.department, employee.certification_cpa]
    logic:  department = "finance" AND certification_cpa = "valid"

R7: employee.remote_work_approved
    inputs: [employee.manager_approval_remote, employee.performance_rating]
    logic:  manager_approval_remote = True AND performance_rating = "exceeds"
```

### Dependency Chain

```
employee.certification_safety ──→ employee.can_operate_heavy_machinery ──→ employee.project_factory_floor
employee.training_hazmat ──→

employee.training_ethics ──→ employee.compliance_status ──→ employee.promotion_eligible
employee.training_compliance ──→
employee.performance_rating ──→
employee.disciplinary_action ──→
```

### Example Revision Scenario

```
t=0: certification_safety = "valid", training_hazmat = "completed"
     → R1: can_operate = True
     → R2: project_factory_floor = "assigned"

t=1: Test harness simulates cert expiry:
     employee.certification_safety = "expired"
     → dirty: {can_operate_heavy_machinery, project_factory_floor}

t=2: resolve_all_dirty():
     → R1: expired ≠ valid → can_operate = False
     → R2: can_operate = False → project = "suspended"

t=3: Employee renews cert:
     employee.certification_safety = "valid"
     → dirty again → resolve → can_operate = True → project = "assigned"
```

---

## Domain 3: Crime Scene Investigation

### Purpose

Tests **deep revision chains** and **cascading retraction**. All facts are fictional — the LLM has **zero parametric knowledge** and must rely entirely on the belief store.

### What It Tests

| Capability | How |
|---|---|
| Deep revision chains (3-4 hops) | Witness unreliable → alibi broken → suspect status → case theory |
| Complete parametric isolation | Crime is fictional — LLM can't cheat |
| Cascading retraction | Clearing a suspect retracts all downstream derivations |
| Evidence overriding testimony | CCTV (hard evidence) overrides witness (soft evidence) |

### Attributes (KV Keys)

| Key | Type | Example | How It Evolves |
|---|---|---|---|
| `suspect_a.alibi` | str | confirmed, unconfirmed, broken | Witnesses change |
| `suspect_a.alibi_source` | str | witness_jones, cctv | Source tracking |
| `suspect_a.evidence_at_scene` | str | present, absent | Forensics arrive |
| `suspect_a.motive` | str | financial, personal, none | Background investigation |
| `suspect_a.access_to_weapon` | bool | true, false | Investigation findings |
| `suspect_a.physical_evidence_match` | bool | true, false | Lab results |
| `suspect_b.alibi` | str | confirmed, broken | Same as above |
| `suspect_b.evidence_at_scene` | str | present, absent | |
| `suspect_b.motive` | str | revenge, none | |
| `case.time_of_death` | str | 10pm, 9pm | Autopsy updates |
| `case.cause_of_death` | str | blunt_force, poison | Forensics refinement |
| `case.cctv_available` | bool | true, false | Footage discovered |
| `case.toxicology_result` | str | positive_X, negative, pending | Lab processing |
| `witness_jones.credibility` | str | reliable, unreliable | Cross-examination |

### Rules

```
R1: suspect_a.status
    inputs: [suspect_a.evidence_at_scene, suspect_a.alibi,
             suspect_a.motive, suspect_a.access_to_weapon]
    logic:
      IF alibi = "confirmed" → "cleared"
      IF evidence_at_scene = "present" AND alibi = "broken" → "prime_suspect"
      IF motive != "none" AND alibi = "broken" → "person_of_interest"
      ELSE → "under_investigation"

R2: suspect_a.alibi (derived override)
    inputs: [suspect_a.alibi_source, witness_jones.credibility]
    logic:
      IF alibi_source = "witness_jones" AND credibility = "unreliable"
        → "broken"
      IF alibi_source = "cctv" → "confirmed"  (hard evidence, always holds)
      ELSE → keep current value

R3: suspect_a.cleared_by_weapon
    inputs: [case.cause_of_death, suspect_a.access_to_weapon]
    logic:
      IF cause_of_death = "poison" AND access_to_weapon = False
        → True (suspect cleared for this reason)
      ELSE → False

R4: case.theory
    inputs: [suspect_a.status, suspect_a.motive]
    logic:
      IF status = "prime_suspect" AND motive = "financial"
        → "suspect_a committed crime for financial gain"
      IF status = "prime_suspect"
        → "suspect_a is primary suspect, motive under investigation"
      ELSE → "no confirmed theory"

R5: case.cause_of_death (derived override)
    inputs: [case.toxicology_result]
    logic:
      IF toxicology_result = "positive_X" → "poison"
      ELSE → keep current value

R6: suspect_b.status
    inputs: [suspect_b.evidence_at_scene, suspect_b.alibi, suspect_b.motive]
    logic:  (same pattern as R1 for suspect_b)

R7: suspect_a.alibi (CCTV override)
    inputs: [case.cctv_available, suspect_a.alibi_source]
    logic:
      IF cctv_available = True AND alibi_source = "cctv"
        → "confirmed"
```

### Dependency Chain (4-hop)

```
witness_jones.credibility ──→ suspect_a.alibi ──→ suspect_a.status ──→ case.theory
suspect_a.evidence_at_scene ──→                                           │
suspect_a.motive ──────────────────────────────────────────────────────────┘

case.toxicology_result ──→ case.cause_of_death ──→ suspect_a.cleared_by_weapon
```

### Example Revision Scenario

```
t=0: witness_jones says suspect_a was at bar at 10pm
     → suspect_a.alibi = "confirmed", alibi_source = "witness_jones"
     → R1: alibi confirmed → suspect_a.status = "cleared"

t=1: Cross-examination reveals jones has prior relationship with suspect_a
     → witness_jones.credibility = "unreliable"
     → dirty: {suspect_a.alibi, suspect_a.status, case.theory}

t=2: resolve_all_dirty():
     → R2: alibi_source = jones, credibility = unreliable → alibi = "broken"
     → R1: evidence = present, alibi = broken → status = "prime_suspect"
     → R4: prime_suspect, motive = financial → theory updated

t=3: Forensics: suspect_a.evidence_at_scene = "present"
     (already present — no change, no cascade)

t=4: Toxicology: case.toxicology_result = "positive_X"
     → dirty: {case.cause_of_death, suspect_a.cleared_by_weapon}
     → R5: cause_of_death = "poison"
     → R3: poison + access_to_weapon = False → cleared_by_weapon = True
```

---

## Domain 4: Thorncrester Taxonomy (Fictional Bird Species)

### Purpose

Tests belief revision with **complete parametric isolation**. The Thorncrester is fictional — the LLM has zero prior knowledge. Also tests classification revision from evolving field observations.

### What It Tests

| Capability | How |
|---|---|
| Zero parametric leakage | Fictional species — LLM cannot rely on training data |
| Classification revision | Diet reclassification cascades to prey + conservation |
| Seasonal lifecycle changes | Season change triggers behavioral and habitat updates |
| Extensibility | Easy to add new observations over time |

### Species Background

The **Thorncrester** (*Spinocristatus fictus*) is a fictional bird native to the Verath Archipelago. Two subspecies: **Coastal** and **Highland**.

### Attributes (KV Keys)

| Key | Type | Example | How It Evolves |
|---|---|---|---|
| `thorncrester.diet` | str | carnivore, omnivore, herbivore | Field reclassification |
| `thorncrester.can_fly` | bool | true, false | Life stage |
| `thorncrester.habitat` | str | coastal, highland, wetland | Migration, destruction |
| `thorncrester.subspecies` | str | coastal, highland | Identification |
| `thorncrester.life_stage` | str | juvenile, adult, elder | Maturation |
| `thorncrester.season` | str | mating, nesting, migration, dormant | Calendar |
| `thorncrester.plumage_color` | str | crimson, blue, moulted | Seasonal moult |
| `thorncrester.threat_level` | str | safe, endangered, critical | Population surveys |
| `thorncrester.population_count` | numeric | 50, 500 | Census |
| `thorncrester.nesting_behavior` | str | ground, cliff, tree | Research findings |
| `thorncrester.social_structure` | str | solitary, pair, flock | Season + context |

### Rules

```
R1: thorncrester.primary_prey
    inputs: [thorncrester.diet, thorncrester.habitat]
    logic:
      IF diet = "carnivore" AND habitat = "coastal" → "fish"
      IF diet = "carnivore" AND habitat = "highland" → "small_rodents"
      IF diet = "herbivore" → None  (herbivores don't have prey)
      IF diet = "omnivore" AND habitat = "coastal" → "mixed_fish_berries"
      IF diet = "insectivore" → "beetles"
      ELSE → "unknown"

R2: thorncrester.can_fly
    inputs: [thorncrester.life_stage]
    logic:
      IF life_stage = "juvenile" → False
      IF life_stage = "adult" OR life_stage = "elder" → True

R3: thorncrester.habitat (default from subspecies)
    inputs: [thorncrester.subspecies, thorncrester.season]
    logic:
      IF season = "migration" AND subspecies = "coastal" → "wetland"
      IF subspecies = "coastal" → "coastal"
      IF subspecies = "highland" → "highland"
    NOTE: season change away from migration automatically reverts habitat

R4: thorncrester.territorial_behavior
    inputs: [thorncrester.plumage_color, thorncrester.season]
    logic:  plumage_color = "crimson" AND season = "mating" → True, else False

R5: thorncrester.threat_level
    inputs: [thorncrester.population_count]
    logic:
      IF population_count < 100 → "critical"
      IF population_count < 500 → "endangered"
      ELSE → "safe"

R6: thorncrester.conservation_action
    inputs: [thorncrester.threat_level, thorncrester.habitat]
    logic:
      IF threat_level = "critical" AND habitat = "coastal" → "breeding_program"
      IF threat_level = "critical" → "emergency_monitoring"
      IF threat_level = "endangered" → "monitoring"
      ELSE → "none"

R7: thorncrester.predation_risk
    inputs: [thorncrester.nesting_behavior, thorncrester.threat_level]
    logic:
      IF nesting_behavior = "ground" AND threat_level in ("endangered", "critical")
        → "high"
      ELSE → "low"

R8: thorncrester.clutch_size
    inputs: [thorncrester.season, thorncrester.threat_level]
    logic:
      IF season = "nesting" AND threat_level in ("endangered", "critical") → 4
      IF season = "nesting" → 2
      ELSE → 0  (not nesting season)

R9: thorncrester.social_structure
    inputs: [thorncrester.territorial_behavior, thorncrester.season]
    logic:
      IF territorial_behavior = True → "pair"
      IF season = "migration" → "flock"
      ELSE → "solitary"
```

### Dependency Chain

```
thorncrester.diet ──→ thorncrester.primary_prey
thorncrester.habitat ──→

thorncrester.population_count ──→ thorncrester.threat_level ──→ thorncrester.conservation_action
                                                              ──→ thorncrester.predation_risk
                                                              ──→ thorncrester.clutch_size

thorncrester.season ──→ thorncrester.habitat ──→ thorncrester.primary_prey
                     ──→ thorncrester.territorial_behavior ──→ thorncrester.social_structure
                     ──→ thorncrester.clutch_size
```

### Example Revision Scenario

```
t=0: diet = "carnivore", habitat = "coastal", population_count = 800
     → R1: primary_prey = "fish"
     → R5: threat_level = "safe"
     → R6: conservation_action = "none"

t=1: Field observation: diet reclassified to "omnivore"
     → dirty: {primary_prey}
     → resolve: R1 → primary_prey = "mixed_fish_berries"

t=2: Census: population_count = 80
     → dirty: {threat_level, conservation_action, predation_risk, clutch_size}
     → resolve:
       R5 → threat_level = "critical"
       R6 → critical + coastal → conservation_action = "breeding_program"
       R7 → nesting=ground + critical → predation_risk = "high"

t=3: Season changes to "migration"
     → dirty: {habitat, territorial_behavior, social_structure, clutch_size}
     → resolve:
       R3 → migration + coastal → habitat = "wetland"
       → habitat changed → primary_prey dirty → R1 re-derives
       R4 → not mating season → territorial = False
       R9 → migration → social_structure = "flock"

t=4: Season changes to "dormant"
     → dirty: {habitat, territorial_behavior, social_structure, clutch_size}
     → resolve:
       R3 → not migration, coastal → habitat = "coastal" (reverts automatically)
       R9 → not territorial, not migration → social_structure = "solitary"
```

---

## Cross-Domain Comparison

| Property | Loan | Employee | Crime Scene | Thorncrester |
|---|---|---|---|---|
| **Max dependency depth** | 3 hops | 2 hops | 4 hops | 3 hops |
| **Number of rules** | 6 | 7 | 7 | 9 |
| **Number of attributes** | ~12 | ~12 | ~14 | ~11 |
| **Parametric isolation** | Low | Low | **Total** | **Total** |
| **Belief Maintain test** | ✓ credit ↛ employment | ✓ cert_safety ↛ cpa | ✓ suspect_a ↛ suspect_b | ✓ diet ↛ population |
| **Key revision pattern** | Threshold change | Prerequisite expiry | Evidence cascade | Classification shift |
