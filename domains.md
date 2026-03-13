# Belief-Aware LLM — Domain Specifications

This document defines the four handcrafted domains used to evaluate the belief revision system. Each domain is designed to stress-test different aspects of the bipartite inference graph: threshold rules, temporal retraction, deep revision chains, and parametric isolation.

---

## Domain 1: Loan Eligibility

### Purpose

The **baseline domain**. Simple threshold-based rules with clear pass/fail outcomes. Used to validate that the core architecture works: fact insertion, contradiction detection, dirty propagation, and lazy re-derivation.

### What It Tests

| Capability | How |
|---|---|
| Basic contradiction detection | Income changes → old value conflicts with new |
| Single-hop revision | One fact change → one derived belief goes dirty |
| Conjunctive rule firing | Eligibility requires ALL conditions met |
| Belief Maintain | Changing credit score should NOT affect employment status |

### Attributes

| Attribute | Type | Example Values | How It Evolves |
|---|---|---|---|
| `income` | numeric | 3000, 5000, 7500 | Raises, job loss, new employment |
| `credit_score` | numeric | 520, 650, 780 | Payments, defaults, disputes resolved |
| `debt_ratio` | float | 0.15, 0.40, 0.60 | New loans taken, debts paid off |
| `employment_status` | categorical | employed, self_employed, unemployed | Hiring, firing, career changes |
| `employment_duration_months` | numeric | 3, 12, 36 | Time passing |
| `has_collateral` | boolean | true, false | Asset purchase or sale |
| `loan_amount_requested` | numeric | 10000, 50000 | Applicant changes request |
| `existing_loans_count` | numeric | 0, 2, 5 | New loans or payoffs |
| `bankruptcy_history` | boolean | true, false | Legal proceedings resolved |
| `applicant_age` | numeric | 22, 35, 60 | Static but affects some rules |
| `co_signer_available` | boolean | true, false | Co-signer agrees or withdraws |
| `income_source` | categorical | salary, freelance, investments, pension | Career changes |

### Rules

```
R1: income >= 5000 ∧ credit_score >= 650 ∧ debt_ratio < 0.4
    → loan_eligible = true

R2: employment_status = unemployed
    → loan_eligible = false
    (overrides R1 — even if income from investments meets threshold)

R3: loan_eligible = true ∧ credit_score >= 750
    → interest_rate_tier = preferred

R4: loan_eligible = true ∧ credit_score < 750 ∧ credit_score >= 650
    → interest_rate_tier = standard

R5: loan_eligible = true ∧ has_collateral = true
    → max_loan_amount = 100000

R6: loan_eligible = true ∧ has_collateral = false
    → max_loan_amount = 30000

R7: bankruptcy_history = true ∧ employment_duration_months < 24
    → loan_eligible = false

R8: loan_amount_requested > max_loan_amount
    → application_status = denied_amount_exceeded

R9: co_signer_available = true ∧ credit_score < 650
    → credit_score_effective = credit_score + 50
    (co-signer boosts effective score)

R10: existing_loans_count >= 3 ∧ debt_ratio >= 0.3
     → high_risk_flag = true
```

### Example Revision Scenario

```
t=0: income=3000, credit_score=700, debt_ratio=0.3
     → R1 fails (income < 5000) → loan_eligible = false

t=1: User says "I got a new job, income is now 6000"
     → income conflict: 3000 vs 6000 → retract old, insert new
     → loan_eligible goes dirty

t=2: Query loan_eligible → re-derive with income=6000
     → R1: 6000 >= 5000 ✓, 700 >= 650 ✓, 0.3 < 0.4 ✓
     → loan_eligible = true
     → interest_rate_tier goes dirty (depends on loan_eligible)

t=3: Query interest_rate_tier → re-derive
     → R4: credit_score=700, 650 <= 700 < 750 → standard
```

---

## Domain 2: Employee Compliance & Role Eligibility

### Purpose

Tests **temporal belief revision** — beliefs that become invalid due to the passage of time (expiring certifications, overdue training). Also tests multi-prerequisite role eligibility rules.

### What It Tests

| Capability | How |
|---|---|
| Temporal retraction | Certification expires → downstream role eligibility cascades to dirty |
| Multi-hop dependency chains | Cert expires → role ineligible → project assignment invalid |
| Independent belief maintenance | Revoking one certification should NOT affect unrelated clearances |
| Conjunctive rules with 3+ premises | Role eligibility requires training + cert + experience |

### Attributes

| Attribute | Type | Example Values | How It Evolves |
|---|---|---|---|
| `certification(X)` | categorical | valid, expired, revoked | Certifications expire annually |
| `cert_expiry_date(X)` | date | 2026-06-01 | Set on certification |
| `training(X)` | categorical | completed, not_completed, overdue | Annual re-training cycles |
| `training_completion_date(X)` | date | 2025-09-15 | On completion |
| `clearance_level` | categorical | none, basic, confidential, secret | Background checks |
| `years_experience` | numeric | 1, 3, 7 | Time / role changes |
| `department` | categorical | engineering, finance, operations | Transfers |
| `performance_rating` | categorical | exceeds, meets, below | Annual review |
| `disciplinary_action` | boolean | true, false | Incidents |
| `background_check_status` | categorical | passed, pending, failed | Investigation results |
| `manager_approval(X)` | boolean | true, false | Manager grants/revokes |
| `project_assignment(X)` | categorical | assigned, unassigned, suspended | Based on eligibility |
| `overtime_eligible` | boolean | true, false | Employment classification |
| `remote_work_approved` | boolean | true, false | Policy changes |

### Rules

```
R1: certification(safety) = valid ∧ training(hazmat) = completed
    → can_operate(heavy_machinery) = true

R2: clearance_level >= confidential ∧ years_experience >= 3
      ∧ background_check_status = passed
    → eligible_for(senior_analyst) = true

R3: certification(safety) = expired
    → can_operate(heavy_machinery) = false
    → project_assignment(factory_floor) = suspended

R4: training(ethics) = completed ∧ training(compliance) = completed
    → compliance_status = compliant

R5: compliance_status = compliant ∧ performance_rating != below
    → promotion_eligible = true

R6: disciplinary_action = true
    → promotion_eligible = false
    → clearance_level = under_review

R7: training(X) = overdue (> 12 months since completion)
    → training(X) = not_completed (auto-retraction)

R8: manager_approval(remote_work) = true ∧ performance_rating = exceeds
    → remote_work_approved = true

R9: department = finance ∧ certification(cpa) = valid
    → eligible_for(financial_auditor) = true

R10: eligible_for(senior_analyst) = true ∧ manager_approval(promotion) = true
     → promotion_status = recommended
```

### Example Revision Scenario

```
t=0: certification(safety) = valid, training(hazmat) = completed
     → R1 fires → can_operate(heavy_machinery) = true
     → project_assignment(factory_floor) = assigned

t=1: certification(safety) expires → status changes to expired
     → can_operate(heavy_machinery) goes dirty
     → project_assignment(factory_floor) goes dirty

t=2: Query can_operate → re-derive → R3 fires → false
     → project_assignment → re-derive → suspended

t=3: Employee renews certification → certification(safety) = valid
     → can_operate goes dirty again → re-derive → true
     → project_assignment → re-derive → assigned
```

---

## Domain 3: Crime Scene Investigation

### Purpose

Tests **deep retraction chains and abductive reasoning**. Evidence gets contradicted, alibis collapse, and suspect assessments cascade through revision. The facts of the crime are invented, so the **LLM has zero parametric knowledge** and must rely entirely on the belief store.

### What It Tests

| Capability | How |
|---|---|
| Deep revision chains (3-4 hops) | Witness unreliable → alibi broken → suspect status → case theory |
| Complete parametric isolation | Crime is fictional — LLM can't cheat |
| Retraction of derived beliefs | Clearing a suspect retracts all accusations derived from that status |
| Process of elimination reasoning | All-but-one suspects cleared → last one becomes prime suspect |
| Source reliability weighting | Witness credibility affects downstream belief confidence |

### Attributes

| Attribute | Type | Example Values | How It Evolves |
|---|---|---|---|
| `suspect_alibi(X)` | categorical | confirmed, unconfirmed, broken | Witness statements change |
| `alibi_source(X)` | string | witness_jones, cctv_footage | Source tracking |
| `evidence_at_scene(X)` | categorical | present, absent, contaminated | Forensics results arrive |
| `evidence_type(X)` | categorical | fingerprint, dna, weapon, fiber | Collection over time |
| `motive(X)` | categorical | financial, personal, revenge, none | Background investigation |
| `time_of_death` | string | 10pm, 11pm, 9pm-10pm_window | Autopsy updates |
| `cause_of_death` | categorical | blunt_force, poison, gunshot | Forensics refinement |
| `suspect_location(X, time)` | string | at_scene, at_bar, at_home | Tracking / phone records |
| `witness_credibility(X)` | categorical | reliable, unreliable, unknown | Cross-examination |
| `witness_statement(X)` | string | "saw suspect A at bar at 10pm" | Testimonies |
| `relationship_to_victim(X)` | categorical | spouse, colleague, stranger, rival | Background research |
| `suspect_status(X)` | categorical | cleared, person_of_interest, prime_suspect | Ongoing investigation |
| `physical_evidence_match(X)` | boolean | true, false | Lab results |
| `access_to_weapon(X)` | boolean | true, false | Investigation findings |
| `case_theory` | string | "suspect_A committed crime for financial gain" | Evolving conclusion |
| `cctv_available` | boolean | true, false | Footage discovered/corrupted |
| `toxicology_result` | categorical | positive(X), negative, pending | Lab processing |

### Rules

```
R1: evidence_at_scene(fingerprints_A) = present ∧ suspect_alibi(A) = broken
    → suspect_status(A) = prime_suspect

R2: suspect_alibi(A) = confirmed ∧ witness_credibility(source) = reliable
    → suspect_status(A) = cleared

R3: witness_credibility(W) = unreliable ∧ alibi_source(A) = W
    → suspect_alibi(A) = broken
    (alibi collapses because its source is discredited)

R4: time_of_death = T ∧ suspect_location(A, T) = at_scene
    → suspect_status(A) = prime_suspect

R5: suspect_status(A) = cleared ∧ suspect_status(B) = cleared
      ∧ suspect_count = 3
    → suspect_status(C) = person_of_interest
    (process of elimination)

R6: physical_evidence_match(A) = true ∧ motive(A) != none
    → suspect_status(A) = prime_suspect

R7: cause_of_death = poison ∧ access_to_weapon(A) = false
    → suspect_status(A) != prime_suspect
    (can't be prime suspect without access to the weapon type)

R8: suspect_status(A) = prime_suspect ∧ motive(A) = financial
    → case_theory = "suspect_A committed crime for financial gain"

R9: cctv_available = true ∧ suspect_location(A, T) != at_scene
    → suspect_alibi(A) = confirmed
    (hard evidence overrides witness testimony)

R10: toxicology_result = positive(substance_X)
     → cause_of_death = poison (may override earlier forensic conclusion)
```

### Example Revision Scenario

```
t=0: Witness Jones says Suspect A was at the bar at 10pm
     → alibi_source(A) = witness_jones
     → suspect_alibi(A) = confirmed
     → R2 fires → suspect_status(A) = cleared

t=1: Cross-examination: Jones has a prior relationship with A
     → witness_credibility(jones) = unreliable

t=2: R3 fires: alibi_source(A) = jones ∧ jones = unreliable
     → suspect_alibi(A) = broken
     → suspect_status(A) goes dirty

t=3: Forensic lab returns: fingerprints_A present at scene
     → evidence_at_scene(fingerprints_A) = present

t=4: Re-derive suspect_status(A):
     → R1: fingerprints present ∧ alibi broken → prime_suspect

t=5: case_theory goes dirty → re-derive with motive(A) = financial
     → "suspect_A committed crime for financial gain"
```

---

## Domain 4: Thorncrester Taxonomy (Fictional Bird Species)

### Purpose

Tests belief revision with **complete parametric isolation**. The Thorncrester is a fictional bird-like species — the LLM has absolutely no prior knowledge of it and MUST reason exclusively from the belief store. Also tests naturally evolving scientific knowledge (field observations update classifications over time).

### What It Tests

| Capability | How |
|---|---|
| Zero parametric leakage | Fictional species — LLM cannot rely on training data |
| Classification revision | Diet reclassification cascades to prey, habitat strategy, conservation |
| Seasonal / lifecycle belief changes | Plumage, behavior, and abilities change with seasons and maturity |
| Extensibility | Easy to add subspecies, regional variants, new observations |
| Multi-hop scientific reasoning | Trait → classification → behavior → conservation action |

### Species Background

The **Thorncrester** (*Spinocristatus fictus*) is a fictional medium-sized bird native to the fictional Verath Archipelago. It has several unusual characteristics:
- Its crest changes color seasonally
- Juveniles cannot fly; adults can
- Its diet shifts based on habitat
- It has two known subspecies: the **Coastal Thorncrester** and the **Highland Thorncrester**

### Attributes

| Attribute | Type | Example Values | How It Evolves |
|---|---|---|---|
| `diet` | categorical | carnivore, omnivore, herbivore, insectivore | Field observation reclassification |
| `can_fly` | boolean | true, false | Life stage (juvenile → adult) |
| `habitat` | categorical | coastal, highland, forest, wetland | Migration, habitat destruction |
| `plumage_color` | categorical | crimson, blue, moulted, iridescent | Seasonal moult cycle |
| `season` | categorical | mating, nesting, migration, dormant | Calendar progression |
| `life_stage` | categorical | hatchling, juvenile, adult, elder | Maturation |
| `threat_level` | categorical | safe, vulnerable, endangered, critical | Population surveys |
| `population_count` | numeric | 50, 500, 2000 | Census data |
| `nesting_behavior` | categorical | ground, tree, cliff, burrow | New research findings |
| `subspecies` | categorical | coastal, highland | Identification |
| `primary_prey` | categorical | fish, insects, berries, crustaceans | Derived from diet + habitat |
| `predation_risk` | categorical | low, moderate, high | Derived from nesting + threat level |
| `territorial_behavior` | boolean | true, false | Derived from season + plumage |
| `conservation_action` | categorical | none, monitoring, relocation, breeding_program | Derived from threat + habitat |
| `migration_pattern` | categorical | sedentary, short_range, long_range | Seasonal + subspecies |
| `vocalization_type` | categorical | song, alarm_call, mating_call, silent | Season + context |
| `clutch_size` | numeric | 1, 2, 4 | Subspecies + threat level |
| `wing_span_cm` | numeric | 30, 60, 85 | Life stage |
| `social_structure` | categorical | solitary, pair, flock | Season + habitat |
| `crest_pattern` | categorical | raised, flat, display | Behavioral state |

### Rules

```
R1: diet = carnivore ∧ habitat = coastal
    → primary_prey = fish

R2: diet = carnivore ∧ habitat = highland
    → primary_prey = small_rodents

R3: diet = insectivore ∧ habitat = forest
    → primary_prey = beetles

R4: can_fly = false ∧ habitat = forest
    → locomotion = ground_foraging

R5: plumage_color = crimson ∧ season = mating
    → territorial_behavior = true
    → crest_pattern = display

R6: threat_level = critical ∧ habitat = coastal
    → conservation_action = breeding_program

R7: threat_level = endangered ∧ nesting_behavior = ground
    → predation_risk = high

R8: life_stage = juvenile → can_fly = false
    life_stage = adult → can_fly = true

R9: subspecies = coastal → habitat = coastal (default, can be overridden)
    subspecies = highland → habitat = highland (default)

R10: population_count < 100
     → threat_level = critical

R11: population_count >= 100 ∧ population_count < 500
     → threat_level = endangered

R12: season = migration ∧ subspecies = coastal
     → migration_pattern = long_range
     → habitat = wetland (temporary override)

R13: season = nesting ∧ threat_level >= endangered
     → clutch_size = clutch_size + 1 (stress response)

R14: territorial_behavior = true ∧ social_structure = flock
     → social_structure = pair (territoriality breaks flocks)

R15: diet = herbivore → primary_prey = retracted
     → foraging_target = berries
```

### Example Revision Scenario

```
t=0: Initial observation of Coastal Thorncrester
     → subspecies = coastal, diet = carnivore, habitat = coastal
     → R1 fires → primary_prey = fish
     → R9 fires → habitat confirmed coastal

t=1: Field researcher observes specimens eating berries and insects
     → diet update: carnivore → omnivore
     → primary_prey goes dirty (was derived from diet = carnivore)

t=2: Query primary_prey → re-derive with diet = omnivore ∧ habitat = coastal
     → No exact rule match → LLM reasons: "mixed diet of fish and berries"

t=3: Population census: only 80 individuals counted
     → population_count = 80
     → R10 fires → threat_level = critical
     → conservation_action goes dirty

t=4: Query conservation_action → R6: critical ∧ coastal → breeding_program

t=5: Season changes to mating → plumage = crimson observed
     → R5 fires → territorial_behavior = true
     → R14 fires → social_structure changes from flock → pair
```

---

## Cross-Domain Comparison

| Property | Loan | Employee | Crime Scene | Thorncrester |
|---|---|---|---|---|
| **Rule complexity** | Simple thresholds | Multi-prerequisite | Abductive / elimination | Classification chains |
| **Revision depth** | 1-2 hops | 2-3 hops | 3-4 hops | 2-4 hops |
| **Temporal dynamics** | Moderate | Strong (expiry) | Event-driven | Seasonal cycles |
| **Parametric isolation** | Low | Low | **Total** | **Total** |
| **Belief Maintain test** | ✓ Unrelated attributes | ✓ Unrelated certs | ✓ Unrelated suspects | ✓ Unrelated traits |
| **Conjunctive rules** | 3-way AND | 3-4 way AND | 2-3 way AND | 2-way AND |
| **Process of elimination** | No | No | **Yes** | No |
| **Real-world relatability** | Very high | High | High | Moderate (fictional) |
| **Demo engagement** | Low (dry) | Medium | **High** | **High** (novelty) |
| **Estimated belief nodes** | 12-15 | 15-20 | 15-25 | 20-30 |
| **Estimated rule nodes** | 8-10 | 8-10 | 8-10 | 12-15 |
