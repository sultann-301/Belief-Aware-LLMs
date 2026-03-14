# Belief-Aware LLM System — Methodology

## Architecture Overview

The system externalizes belief state into a managed graph and uses the LLM as a modular reasoning engine — not a knowledge store. The LLM never "knows" its beliefs internally; it reasons over whatever is injected into its prompt from the belief store.

```
Structured Input → Belief Store (Bipartite Inference Graph)
                        ↓
               Contradiction Detector
                        ↓
              Dirty Propagation (BFS)
                        ↓
        On Query: Lazy Re-derivation via LLM
```

> [!IMPORTANT]
> All belief inputs are **structured** (not natural language). The LLM is never used for NL-to-belief extraction — its sole role is **reasoning over injected beliefs** to derive conclusions. This avoids the NL parsing reliability problem entirely.

**Key architectural decisions:**

| Decision | Choice | Rationale |
|---|---|---|
| Belief representation | Bipartite inference graph | Handles conjunctive entailment structurally |
| Graph library | NetworkX | BFS built-in, JSON-serializable, lightweight |
| Revision strategy | On-conflict lazy (dirty flags) | Cheap insertion, correct on read |
| Contradiction detection | Hash-map attribute clash | Simple and sufficient for controlled domains |
| LLM role | Reasoning / re-derivation only | No NL-to-belief extraction (structured inputs) |
| Evaluation framework | Belief-R / BREU | Tractable within timeline |
| TMS implementation | The graph IS the TMS | No separate library needed |

---

## Bipartite Inference Graph

Two types of nodes in a single directed graph:

- **Belief nodes** — propositions that can be true, false, or unknown
- **Rule nodes** — inference rules that connect premises to conclusions

Edges alternate between types: `belief → rule` (premise) and `rule → belief` (conclusion). This enforces a bipartite structure where beliefs never connect directly to beliefs.

### Why Bipartite (Not KG Triples)

Knowledge graph triples `(subject, predicate, object)` encode relationships between entities. Our problem requires entailment between propositions — a fundamentally different abstraction. The bipartite graph encodes entailment structurally:

- **Conjunction** is a natural consequence of multiple premise edges feeding into one rule node
- **Implication** is the rule node itself — it IS the "if...then"
- **Entailment** is the directed edge from rule to conclusion

### Belief Node Schema

```python
{
    "id": "b001",
    "node_type": "belief",
    "proposition": "income(applicant_1) = 6000",
    "belief_type": "factual",       # factual | derived
    "status": "active",             # active | dirty | retracted
    "timestamp": "2026-03-12T04:00:00Z",
    "source": "user_input"          # user_input | llm_derivation | system
}
```

| Field | Purpose |
|---|---|
| `belief_type` | `factual` = external input, `derived` = inferred by a rule |
| `status` | `active` / `dirty` / `retracted` — drives lazy revision |
| `source` | Provenance tracking for audit |

### Rule Node Schema

```python
{
    "id": "r001",
    "node_type": "rule",
    "description": "If income >= min_income AND debt < threshold, then eligible",
    "rule_type": "conjunction",     # conjunction | disjunction
    "formal": "income >= min_income ∧ debt_ratio < 0.4 → eligible = true"
}
```

### Premise Edge Schema

```python
graph.add_edge("b001", "r001", **{
    "role": "premise",
    "negated": False,               # True = premise must NOT hold
    "operator": ">=",               # for threshold comparisons
    "threshold_value": 5000         # if applicable
})
```

### Graph Visualization

```
  (income = 6000) ───→  ┌───────────────────┐  ───→  (eligible = true)
                         │  R1: conjunction   │
  (debt_ratio = 0.3) →  │  income >= 5000    │
                         │  ∧ debt < 0.4     │
  (credit = 700) ────→  │  ∧ credit >= 650   │
                         └───────────────────┘

  Belief → Rule = "this belief is a premise of this rule"
  Rule → Belief = "this rule produces this conclusion"
```

---

## Supported Logical Operations

The bipartite graph encodes three logical connectives through its structure:

### Conjunction (∧)

Multiple belief nodes feed into the same rule node. **All** incoming premises must hold for the rule to fire.

```
  (A) ──→ [Rule: A ∧ B → C] ──→ (C)
  (B) ──→ [                ]
```

This is the default — a rule node with multiple incoming premise edges is an AND-junction.

### Disjunction (∨)

Multiple **separate rule nodes** point to the **same conclusion**. If **any** rule fires, the conclusion is active.

```
  (A) ──→ [R1: A → C] ──→ (C)

  (B) ──→ [R2: B → C] ──→ (C)
```

The conclusion C is active if R1 fires OR R2 fires. During dirty propagation, if A changes and R1 no longer fires, the system checks whether any other rule (R2) still sustains C before retracting it.

### Negation (¬)

A `negated` flag on the premise edge. When checking if a rule fires, a negated premise must be `retracted`, `false`, or absent for the rule to be satisfied.

```
  (alibi_A = confirmed) ──[negated=True]──→ [R: ¬alibi ∧ evidence → suspect]
  (evidence_A = present) ──[negated=False]─→ [                               ] ──→ (suspect_A = true)
```

Rule fires only when `alibi_A` is NOT active AND `evidence_A` IS active.

### Modus Tollens

Not a separate mechanism — it falls out of the graph structure. If B was derived from A via rule R, and B is observed to be false, the system can trace back through R to identify A as questionable. This can be encoded as explicit contrapositive rule nodes when needed.

---

## Lazy Revision Algorithm

On-conflict lazy revision: flag contradictions at insertion time, resolve at query time.

```
ON NEW BELIEF (subject, attribute, value):
  1. CONFLICT CHECK:
     → Find active beliefs where (subject, attribute) match but value differs

  2. For each conflicting belief:
     a. Set old_belief.status = "retracted"
     b. Insert new belief with status = "active"
     c. DIRTY PROPAGATION (BFS):
        → Find all rule nodes R where old_belief → R
        → For each R, find all output beliefs C where R → C
        → Set each C.status = "dirty"
        → Recurse: treat each dirty C as a changed belief

ON QUERY (subject, attribute):
  1. Find matching active/dirty belief
  2. If status == "dirty":
     a. Find the rule node R where R → this belief
     b. Find all premise beliefs for R
     c. Recursively resolve any dirty premises first
     d. Check rule firing conditions:
        - For conjunction: ALL premises must be active (respecting negation flags)
        - For disjunction: check all rules pointing to this conclusion
     e. Re-prompt LLM with active premises to re-derive value
     f. Update value, set status = "active"
  3. Return belief
```

**Complexity:**
- Insertion: O(d) where d = number of direct downstream dependents (BFS to flag dirty)
- Query: O(k) where k = depth of dependency chain (only re-derive what's needed)

---

## LLM Integration

The LLM is used **only for reasoning** — specifically, re-deriving dirty beliefs when queried. All belief inputs (facts, rules) are inserted into the graph as structured data, never parsed from natural language.

### Prompt Construction (Belief Injection)

When a dirty belief is queried and needs re-derivation, the system serializes the relevant subgraph into the prompt:

```
SYSTEM: You are a reasoning assistant. Base your conclusions
ONLY on the beliefs provided below. Reference belief IDs.

ACTIVE BELIEFS:
- [b001] income(applicant_1) = 6000           — factual
- [b002] min_income(loan_policy) = 5000        — factual
- [b003] loan_eligible(applicant_1) = ???      — derived, DIRTY

APPLICABLE RULE:
- [r001] IF income >= min_income ∧ debt_ratio < 0.4 ∧ credit_score >= 650
         THEN loan_eligible = true

RETRACTED (for context):
- [b001_old] income(applicant_1) = 4000        — retracted

TASK: Re-derive b003. Output as: {"subject": ..., "attribute": ..., "value": ...}
```

**Design principles:**
- Label each belief with its ID for traceability
- Show retracted beliefs so the LLM understands what changed
- Include the applicable rule explicitly
- Constrain output to structured schema
- Constrain reasoning to provided beliefs only (prevent parametric hallucination)

---

## Contradiction Detection

Contradiction = two active beliefs with the same `(subject, attribute)` but different `value`. This is a hash-map lookup, not a satisfiability problem.

```python
def detect_contradiction(graph, new_belief):
    key = (new_belief.subject, new_belief.attribute)
    for node_id, data in graph.nodes(data=True):
        if (data.get("node_type") == "belief"
            and data.get("status") == "active"
            and (data["subject"], data["attribute"]) == key
            and data["value"] != new_belief.value):
            return node_id  # conflicting belief found
    return None
```

---

## The Graph as TMS

The bipartite inference graph with dirty-flag propagation **is** a simplified Justification-Based Truth Maintenance System (JTMS):

| TMS concept | Graph equivalent |
|---|---|
| Node labels (IN/OUT) | Belief status (active/dirty/retracted) |
| Justifications | Rule nodes connecting premises to conclusions |
| Dependency recording | Directed edges (belief → rule → belief) |
| Label propagation | BFS dirty propagation on belief change |
| Assumption retraction | Setting a factual belief to retracted, cascading dirty flags |

No separate TMS library is needed. Cite Doyle (1979) and De Kleer (1986) to anchor the theoretical connection in the write-up.

---

## Evaluation: Belief-R / BREU

Performance is measured using a Belief-R style framework with two scenario types:

| Scenario Type | Test | Expected Behavior |
|---|---|---|
| **Belief Update (BU)** | New info contradicts prior conclusion | System must revise the conclusion |
| **Belief Maintain (BM)** | New info is irrelevant to prior conclusion | System must retain the conclusion unchanged |

**BREU score** = average of BU accuracy and BM accuracy.

The evaluation compares:
1. **Belief-aware system** (with the graph store and revision engine)
2. **Baseline** (same LLM, raw prompting with conversation history, no belief store)

Metrics: BREU score, contradiction rate, revision cascade correctness, false retraction rate.

---

## Domains

Four handcrafted domains, documented in detail in [domains.md](file:///Users/mws/Documents/GitHub/Belief-Aware-LLMs/domains.md):

| Domain | Tests | Parametric Isolation |
|---|---|---|
| **Loan Eligibility** | Threshold rules, basic contradiction, conjunctive logic | Low |
| **Employee Compliance** | Temporal expiry, cert revocation, multi-hop chains | Low |
| **Crime Scene** | Deep retraction chains, process of elimination, negation | Total |
| **Thorncrester Taxonomy** | Classification revision, seasonal changes, extensibility | Total |

Crime Scene and Thorncrester are the strongest evaluation domains because the LLM has zero prior knowledge — every correct conclusion must come from the belief store.

---

## Summary

| Aspect | Decision |
|---|---|
| Graph structure | Bipartite inference graph (belief nodes + rule nodes) |
| Logical operators | Conjunction (multi-premise), disjunction (multi-rule), negation (edge flag) |
| Graph library | NetworkX (in-memory, JSON persistence, BFS built-in) |
| Entailment encoding | Directed edges: belief → rule → belief |
| Revision strategy | On-conflict lazy: dirty-flag at insertion, re-derive on query |
| Contradiction detection | Attribute-clash hash-map lookup |
| TMS | The graph itself (no separate library) |
| LLM output validation | Pydantic schemas with retry |
| Evaluation | Belief-R / BREU (update accuracy + maintain accuracy) |
| Domains | Loan, Employee, Crime Scene, Thorncrester |
