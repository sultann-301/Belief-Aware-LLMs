# Graph Structure Debate: Bipartite Inference Graph vs. KG Triples

## The Question

How should the belief store be structured? Two viable options emerged:

1. **Bipartite Inference Graph** — two node types (beliefs + rules) in a directed graph, where edges represent entailment
2. **KG Triples with Dependency Metadata** — flat `(Subject, Relation, Object)` triples with `derived_from` and `derivation_rule` fields

Both support the same revision behavior (contradiction detection, dirty propagation, lazy re-derivation). The difference is structural.

---

## Option A: Bipartite Inference Graph

Rules are **explicit nodes** in the graph. Edges alternate: `belief → rule → belief`.

### Visualization (Loan Domain)

```mermaid
graph LR
    b001((b001<br/>income = 6000<br/>FACTUAL))
    b002((b002<br/>debt_ratio = 0.3<br/>FACTUAL))
    b003((b003<br/>credit_score = 700<br/>FACTUAL))
    r001[["r001<br/>income ≥ 5000<br/>∧ debt < 0.4<br/>∧ credit ≥ 650"]]
    b004((b004<br/>loan_eligible = true<br/>DERIVED))
    r002[["r002<br/>eligible ∧ credit ≥ 750"]]
    b005((b005<br/>rate_tier = standard<br/>DERIVED))

    b001 --> r001
    b002 --> r001
    b003 --> r001
    r001 --> b004
    b004 --> r002
    b003 --> r002
    r002 --> b005

    style b001 fill:#4a9eff,color:#fff
    style b002 fill:#4a9eff,color:#fff
    style b003 fill:#4a9eff,color:#fff
    style b004 fill:#ff9f43,color:#fff
    style b005 fill:#ff9f43,color:#fff
    style r001 fill:#2d3436,color:#fff
    style r002 fill:#2d3436,color:#fff
```

### With Negation (Crime Domain)

```mermaid
graph LR
    b010((b010<br/>evidence_A = present<br/>FACTUAL))
    b011((b011<br/>alibi_A = confirmed<br/>RETRACTED ✗))
    r005[["r005<br/>evidence ∧ ¬alibi"]]
    b012((b012<br/>suspect_A = prime<br/>DERIVED))

    b010 --> r005
    b011 -.->|NEGATED| r005
    r005 --> b012

    style b010 fill:#4a9eff,color:#fff
    style b011 fill:#e74c3c,color:#fff
    style b012 fill:#ff9f43,color:#fff
    style r005 fill:#2d3436,color:#fff
```

### With Disjunction (Loan Domain)

```mermaid
graph LR
    b020((b020<br/>has_collateral = true<br/>FACTUAL))
    b021((b021<br/>co_signer = true<br/>FACTUAL))
    r003a[["r003a<br/>collateral → mitigated"]]
    r003b[["r003b<br/>co_signer → mitigated"]]
    b022((b022<br/>risk_mitigated = true<br/>DERIVED))

    b020 --> r003a
    r003a --> b022
    b021 --> r003b
    r003b --> b022

    style b020 fill:#4a9eff,color:#fff
    style b021 fill:#4a9eff,color:#fff
    style r003a fill:#2d3436,color:#fff
    style r003b fill:#2d3436,color:#fff
    style b022 fill:#ff9f43,color:#fff
```

### Dirty Propagation

```mermaid
graph LR
    b001((b001<br/>income = 3000→6000<br/>⚡ CHANGED))
    b002((b002<br/>debt_ratio = 0.3))
    b003((b003<br/>credit_score = 700))
    r001[["r001"]]
    b004((b004<br/>loan_eligible = ???<br/>🔴 DIRTY))
    r002[["r002"]]
    b005((b005<br/>rate_tier = ???<br/>🔴 DIRTY))

    b001 ==>|change propagates| r001
    b002 --> r001
    b003 --> r001
    r001 ==>|marks dirty| b004
    b004 ==>|marks dirty| r002
    b003 --> r002
    r002 ==>|marks dirty| b005

    style b001 fill:#e74c3c,color:#fff
    style b004 fill:#f39c12,color:#fff
    style b005 fill:#f39c12,color:#fff
    style r001 fill:#2d3436,color:#fff
    style r002 fill:#2d3436,color:#fff
    style b002 fill:#4a9eff,color:#fff
    style b003 fill:#4a9eff,color:#fff
```

---

## Option B: KG Triples with Dependency Metadata

Rules are **metadata on derived triples**, not graph nodes. The store is a flat dictionary of triples.

### Visualization (Loan Domain)

```mermaid
graph TD
    subgraph "Flat Triple Store"
        direction TB
        b001["b001: (applicant_1, income, 6000)<br/>type: factual | status: active"]
        b002["b002: (applicant_1, debt_ratio, 0.3)<br/>type: factual | status: active"]
        b003["b003: (applicant_1, credit_score, 700)<br/>type: factual | status: active"]
        b004["b004: (applicant_1, loan_eligible, true)<br/>type: derived | status: active<br/>derived_from: [b001, b002, b003]<br/>rule: r001"]
        b005["b005: (applicant_1, rate_tier, standard)<br/>type: derived | status: active<br/>derived_from: [b003, b004]<br/>rule: r002"]
    end

    subgraph "Rules Store (separate dict)"
        r001["r001: income ≥ 5000 ∧ debt < 0.4 ∧ credit ≥ 650"]
        r002["r002: eligible ∧ credit ≥ 750 → preferred"]
    end

    b001 -.->|derived_from| b004
    b002 -.->|derived_from| b004
    b003 -.->|derived_from| b004
    b003 -.->|derived_from| b005
    b004 -.->|derived_from| b005

    style b001 fill:#4a9eff,color:#fff
    style b002 fill:#4a9eff,color:#fff
    style b003 fill:#4a9eff,color:#fff
    style b004 fill:#ff9f43,color:#fff
    style b005 fill:#ff9f43,color:#fff
    style r001 fill:#2d3436,color:#fff
    style r002 fill:#2d3436,color:#fff
```

### Dirty Propagation (via reverse index)

```mermaid
graph TD
    subgraph "Reverse Dependency Index"
        direction TB
        idx["reverse_deps = {<br/>  b001: [b004],<br/>  b002: [b004],<br/>  b003: [b004, b005],<br/>  b004: [b005]<br/>}"]
    end

    subgraph "Propagation on b001 change"
        step1["1. b001 changes → lookup reverse_deps[b001]"]
        step2["2. Found: [b004] → mark b004 dirty"]
        step3["3. Recurse: reverse_deps[b004] → [b005]"]
        step4["4. Mark b005 dirty"]
    end

    step1 --> step2 --> step3 --> step4

    style idx fill:#2d3436,color:#fff
    style step1 fill:#e74c3c,color:#fff
    style step2 fill:#f39c12,color:#fff
    style step3 fill:#f39c12,color:#fff
    style step4 fill:#f39c12,color:#fff
```

---

## Side-by-Side Comparison

| Aspect | Bipartite Graph | KG Triples + derived_from |
|---|---|---|
| **Data structure** | NetworkX directed graph | Dict of triples + dict of rules |
| **Nodes** | Beliefs + Rules (2 types) | Beliefs only |
| **Where rules live** | Explicit graph nodes | Metadata on derived triples + separate rules dict |
| **Conjunction** | Multiple edges into a rule node | `derived_from: [b001, b002, b003]` |
| **Disjunction** | Multiple rule nodes → same belief | Multiple rules listed, check if any fires |
| **Negation** | `negated` flag on edge | `negated_premises: [b011]` in metadata |
| **Dirty propagation** | BFS on graph edges | Reverse index lookup + recursion |
| **Forward traversal** | Follow edges naturally | Requires building reverse index |
| **Backward traversal** | Follow edges in reverse | Direct — `derived_from` field |
| **Serialization** | Walk graph, format nodes/edges | Dump relevant triples as text |
| **Code complexity** | ~400+ lines | ~200 lines |
| **Bipartite invariant** | Must enforce (no belief→belief) | Not applicable |
| **Academic framing** | Inference graph / TMS (stronger) | Knowledge base with dependency tracking |
| **Implementation speed** | Slower | Faster |
| **Revision behavior** | Identical | Identical |

## The Decision Criterion

> **If your professor requires entailment-as-edges** (the graph structure itself is a deliverable) → **Bipartite Graph**
>
> **If your professor cares about revision behavior** (contradiction detection, dirty propagation, lazy re-derivation) → **KG Triples** (faster to build, same behavior)
>
> Ask: *"Is the graph structure itself a deliverable, or is the revision behavior what matters?"*
