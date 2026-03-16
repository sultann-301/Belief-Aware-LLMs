# Belief-Aware LLM System — Methodology

## Architecture Overview

The system externalizes belief state into a structured store and uses the LLM as a reasoning engine. Responsibilities are split:

- **System** — stores beliefs, detects contradictions, tracks dependencies, retrieves relevant beliefs for prompts
- **LLM** — generates conclusions, re-derives affected beliefs, explains reasoning, proposes updates via structured prompts

```
Structured Input → System: Insert belief → System: Contradiction check
                                                    │
                                          ┌─────────┴──────────┐
                                          │ Conflict            │ No conflict
                                          ▼                     ▼
                              System: Flag affected       Done (belief stored)
                              beliefs via dependencies
                                          │
                                          ▼
                              System: Build structured prompt
                              (current beliefs + new info + rules)
                                          │
                                          ▼
                              LLM: Reason over beliefs
                              → Derive updated conclusions
                              → Explain reasoning
                                          │
                                          ▼
                              System: Apply LLM's updates
                              to belief store + log revision
```

> [!IMPORTANT]
> All belief inputs are **structured** (not natural language). The LLM is never used for NL-to-belief extraction — it receives structured prompts and reasons over injected beliefs.

**Key decisions:**

| Decision | Choice | Rationale |
|---|---|---|
| Belief representation | Structured belief store with dependency metadata | Simple, queryable, serializable |
| Contradiction detection | System-side attribute-clash check | Deterministic, cheap, no LLM call needed |
| Dependency tracking | `derived_from` field on derived beliefs | Tells the system which beliefs are affected by a change |
| Reasoning & re-derivation | LLM via structured prompts | LLM applies rules, handles judgment, explains changes |
| Evaluation | Belief-R / BREU style | Tractable, measures update + maintain accuracy |
| TMS connection | Dependency tracking IS a simplified TMS | Cite Doyle (1979), no separate library needed |

---

## Responsibility Split

### What the System Does (Deterministic)

| Task | How |
|---|---|
| **Store beliefs** | Dict/DB of beliefs with ID, subject, attribute, value, status, metadata |
| **Detect contradictions** | On insert: check if an active belief exists with same (subject, attribute) but different value |
| **Track dependencies** | Each derived belief has `derived_from: [list of belief IDs]` |
| **Flag affected beliefs** | When a belief changes, find all beliefs whose `derived_from` includes it → mark them for re-derivation |
| **Build prompts** | Serialize relevant beliefs + applicable rules into structured prompt for LLM |
| **Apply updates** | Parse LLM output → update belief store → log revision |
| **Maintain revision log** | Record what changed, when, why, which turn |

### What the LLM Does (Reasoning)

| Task | How |
|---|---|
| **Generate conclusions** | Given beliefs + rules in prompt → derive outcome |
| **Re-derive affected beliefs** | When flagged beliefs are presented → produce updated values |
| **Explain reasoning** | Step-by-step trace referencing belief IDs |
| **Handle judgment calls** | When rules require interpretation (e.g., "strong evidence") |

---

## Belief Store Schema

```python
beliefs = {
    "b001": {
        "subject": "applicant_1",
        "attribute": "income",
        "value": 6000,
        "type": "factual",           # factual | derived
        "status": "active",          # active | revised | retracted
        "source": "structured_input",
        "timestamp": "2026-03-16T03:00:00Z"
    },
    "b003": {
        "subject": "applicant_1",
        "attribute": "loan_status",
        "value": "approved",
        "type": "derived",
        "status": "active",
        "derived_from": ["b001", "b002"],
        "derivation_rule": "r001",
        "derivation_reason": "income 6000 >= min 5000",
        "source": "llm_derivation"
    }
}
```

Rules are stored separately:

```python
rules = {
    "r001": {
        "description": "If income >= min_income, loan eligible",
        "formal": "income >= min_income → loan_eligible = true",
        "domain": "loan"
    }
}
```

Revision history:

```python
revision_log = [
    {
        "turn": 2,
        "trigger": "income updated from 4000 to 6000",
        "beliefs_changed": ["b001", "b003"],
        "reason": "b001 updated → b003 depended on b001 → LLM re-derived"
    }
]
```

---

## Contradiction Detection (System-Side)

Simple attribute-clash check — no LLM needed:

```python
def detect_contradiction(beliefs, new_belief):
    for bid, b in beliefs.items():
        if (b["status"] == "active"
            and b["subject"] == new_belief["subject"]
            and b["attribute"] == new_belief["attribute"]
            and b["value"] != new_belief["value"]):
            return bid  # conflicting belief
    return None
```

---

## Dependency Tracking (System-Side)

When a belief changes, find all beliefs that depend on it:

```python
def find_affected(beliefs, changed_id):
    affected = []
    for bid, b in beliefs.items():
        if changed_id in b.get("derived_from", []):
            affected.append(bid)
    return affected
```

This is the simplified TMS: beliefs have justifications (`derived_from`), and when a justification is invalidated, the dependent belief needs re-derivation.

---

## Structured Prompts

### Prompt for Re-derivation

When the system detects that a belief's dependency has changed:

```
SYSTEM: You are a belief-aware reasoning assistant. You maintain
an explicit set of beliefs. A belief dependency has changed and
you must re-derive the affected conclusion.

CURRENT BELIEFS:
- [b001] applicant_1.income = 6000  (UPDATED — was 4000)
- [b002] policy.min_income = 5000   (unchanged)

APPLICABLE RULE:
- [r001] IF income >= min_income THEN loan_eligible = true
         IF income < min_income THEN loan_eligible = false

BELIEF TO RE-DERIVE:
- [b003] applicant_1.loan_status = ???  (was: rejected)

TASK:
1. Evaluate the rule against current beliefs
2. State the revised value for b003
3. Explain your reasoning, referencing belief IDs

Respond in this format:
EVALUATION: <step-by-step check>
RESULT: b003 = <value>
REASON: <explanation>
```

### Prompt for Initial Derivation

When new facts are inserted and the system needs the LLM to derive conclusions:

```
SYSTEM: You are a belief-aware reasoning assistant. Given the
following facts and rules, derive any applicable conclusions.

FACTS:
- [b001] applicant_1.income = 6000
- [b002] policy.min_income = 5000
- [b010] applicant_1.credit_score = 700
- [b011] policy.min_credit = 650

RULES:
- [r001] IF income >= min_income AND credit_score >= min_credit
         THEN loan_eligible = true

TASK: What conclusions can you derive? State each as a belief
with subject, attribute, and value. Explain your reasoning.
```

### Prompt for Explanation

When the system needs the LLM to explain why a belief holds:

```
SYSTEM: Explain why the following belief is held.

BELIEF IN QUESTION:
- [b003] applicant_1.loan_status = approved

SUPPORTING BELIEFS:
- [b001] applicant_1.income = 6000
- [b002] policy.min_income = 5000

RULE USED:
- [r001] IF income >= min_income THEN loan_eligible = true

TASK: Trace the reasoning chain from supporting beliefs
through the rule to the conclusion. Reference all IDs.
```

---

## Evaluation: Belief-R / BREU

Two scenario types across all four domains:

| Type | Test | Expected |
|---|---|---|
| **Belief Update (BU)** | New info contradicts prior conclusion | System must revise |
| **Belief Maintain (BM)** | New info is irrelevant to prior conclusion | System must NOT revise |

**BREU score** = average(BU accuracy, BM accuracy)

Compare:
1. **With belief tracking** — structured belief store + revision
2. **Without belief tracking** — same LLM, raw prompting with conversation history

---

## Domains

Four handcrafted domains documented in [domains.md](file:///Users/mws/Documents/GitHub/Belief-Aware-LLMs/domains.md):

| Domain | Primary Test | Parametric Isolation |
|---|---|---|
| Loan Eligibility | Threshold rules, basic contradiction | Low |
| Employee Compliance | Temporal expiry, multi-hop dependencies | Low |
| Crime Scene | Deep revision chains, process of elimination | Total |
| Thorncrester Taxonomy | Classification revision, evolving observations | Total |

---

## Summary

| Aspect | Decision |
|---|---|
| Belief store | Dict with structured metadata + `derived_from` tracking |
| Contradiction detection | System-side attribute-clash check (deterministic) |
| Dependency tracking | `derived_from` field on derived beliefs |
| Flagging affected beliefs | System traverses `derived_from` references |
| Reasoning & derivation | LLM via structured prompts |
| Revision strategy | System flags conflicts → LLM re-derives → system applies updates |
| Evaluation | Belief-R / BREU (update accuracy + maintain accuracy) |
| Domains | Loan, Employee, Crime Scene, Thorncrester |
