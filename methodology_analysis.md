# Belief-Aware LLM System — Methodology Analysis

## Overview of the Guide

The A4 Extended Guide frames a strong, well-scoped project: build an **external belief management layer** around an LLM so that it can maintain, query, and revise an explicit set of beliefs over time—without retraining the model. The guide wisely limits scope (no full AGM, no multi-agent, no modal logic) and focuses on a controlled domain with simple, testable revision rules.

Your planned architecture aligns well with the guide:

| Guide Recommendation | Your Architecture |
|---|---|
| Beliefs must be explicit and queryable | ✅ Explicit, queryable belief store |
| Belief state must remain external | ✅ LLM integrated via API, store is separate |
| LLM generates conclusions from current belief state | ✅ Prompt injects relevant beliefs into context |
| Simple revision rules | ✅ Lazy belief revision |

---

## Thoughts on the Methodology

### What's Strong

1. **Separation of concerns** — Keeping the LLM as a "reasoning engine" that reads beliefs from an external store is exactly right. The model doesn't need to "know" its beliefs internally; it just reasons over whatever is injected into its prompt.
2. **Controlled domain** — The guide's emphasis on a small domain (loan eligibility, game state, etc.) is critical. You can actually *measure* consistency in a bounded space.
3. **Lazy revision** — This is a pragmatic choice. Full eagerness (revise everything on every new input) is both expensive and unnecessary. Most beliefs won't be affected by any given update.

### Where I'd Push Further

#### 1. Belief Granularity — Knowledge Graph Triples

The guide gives examples like `"Applicant income = 4000"` and `"Loan rejected"`. The chosen representation is **knowledge graph triples**: each belief is a `(subject, relation, object)` tuple.

This resolves the granularity question cleanly:
- `"Loan rejected due to low income"` becomes two triples: `(applicant, loan_status, rejected)` + `(applicant, rejection_reason, low_income)`
- Rules are also triples: `(loan_policy, min_income, 5000)`

Triples should be separated into three **types** for different revision behavior:

| Type | Description | Example |
|---|---|---|
| `factual` | Observable data from external input | `(applicant_1, has_income, 6000)` |
| `derived` | Conclusions inferred by the LLM from other beliefs | `(applicant_1, loan_status, approved)` |
| `rule` | Policies/constraints that govern derivations | `(loan_policy, min_income, 5000)` |

> [!IMPORTANT]
> Contradiction detection becomes a simple query: two active triples with the **same (subject, relation)** but **different object**. This is a trivial graph lookup.

#### 2. Lazy Revision Needs a Trigger Strategy

"Lazy" means you don't revise everything upfront—but you need to define **when** revision happens:

- **On-query lazy**: When a belief is queried, check if any of its dependencies have been invalidated. This is like a cache invalidation pattern.
- **On-conflict lazy**: When new information is inserted, flag directly contradicted beliefs as "dirty" but don't cascade. Cascade only when a dirty belief is accessed.
- **Periodic batch**: Run a sweep at fixed intervals.

> [!TIP]
> **On-conflict lazy** is the sweet spot for your system. It's cheap at insertion time (just flag contradictions), but still ensures any queried belief is up-to-date at read time. Think of it as a "dirty flag" pattern.

#### 3. The Prompt Injection Strategy is the Key Engineering Challenge

The guide's Step 5 says to use "structured prompts," but the quality of this system will live or die by **how you query the belief store and construct the prompt**. Consider:

- **Relevance filtering**: Not all beliefs should be injected. You need a retrieval mechanism (keyword match, semantic similarity, or dependency graph traversal) to select only the beliefs relevant to the current query.
- **Context window budget**: LLMs have token limits. You need to prioritize which beliefs to inject when the store grows large.
- **Prompt template design**: Structure the injected beliefs clearly (e.g., as a labeled list) so the LLM can distinguish them from the user query.

---

## Belief Store: Knowledge Graph with Triples

Beliefs are stored as **(subject, relation, object)** triples in a knowledge graph, with metadata to support lazy revision.

### Triple Schema

Each triple carries metadata beyond the core `(S, R, O)`:

```python
# A single belief triple
("applicant_1", "has_income", 6000, {
    "id": "b001",
    "type": "factual",        # factual | derived | rule
    "status": "active",       # active | dirty | retracted
    "timestamp": "2026-03-07T00:30:00Z",
    "source": "user_input",   # provenance tracking
    "confidence": 1.0          # optional soft weighting
})
```

| Metadata Field | Purpose |
|---|---|
| `id` | Unique triple ID for cross-referencing |
| `type` | Determines revision behavior (factual vs derived vs rule) |
| `status` | `active` / `dirty` / `retracted` — drives lazy revision |
| `timestamp` | Temporal ordering for recency-based conflict resolution |
| `source` | Who/what introduced this belief (user, LLM, system) |
| `confidence` | Optional weight for soft revision scenarios |

### Graph Structure

Dependencies between triples are captured as **edges** in the graph. A special `derived_from` relation links derived beliefs to their upstream facts/rules:

```
┌─────────────────────────────────┐
│ (applicant_1, has_income, 6000) │  [factual, b001]
└──────────────┬──────────────────┘
               │ derived_from
               ▼
┌─────────────────────────────────────┐
│ (applicant_1, loan_status, approved)│  [derived, b003]
└──────────────▲──────────────────────┘
               │ derived_from
┌─────────────────────────────────────┐
│ (loan_policy, min_income, 5000)     │  [rule, b002]
└─────────────────────────────────────┘
```

When `b001` changes, a graph traversal along `derived_from` edges immediately identifies `b003` as needing re-evaluation.

### Implementation: NetworkX (Recommended)

| Option | Pros | Cons |
|---|---|---|
| **NetworkX** (in-memory graph) | Easy, fast prototyping, BFS/DFS built in, JSON serializable | Not persistent by default |
| **RDFLib** | Standards-compliant (RDF/SPARQL), built for triples | Heavier, SPARQL learning curve |
| **Neo4j** | Powerful queries, scalable, visualization tools | Overkill for a controlled domain |
| **Custom dict + JSON** | Simplest, full control | Manual traversal code |

> [!TIP]
> **Start with NetworkX** — it gives you real graph traversal (find all downstream dependents = one BFS call) while staying lightweight. Persist the graph to a JSON file between sessions. Migrate to RDFLib or Neo4j only if you outgrow it.

---

## Lazy Revision: A Concrete Algorithm

Using the KG triple structure, here's how "on-conflict lazy" revision works:

```
ON NEW TRIPLE (subject, relation, object):
  1. CONFLICT CHECK:
     → Find active triples where (subject, relation) match but object differs

  2. For each conflicting triple:
     a. Set old_triple.status = "retracted"
     b. Insert new triple with status = "active"
     c. DIRTY PROPAGATION (graph traversal):
        → Follow derived_from edges to find all downstream triples
        → Set each downstream triple's status = "dirty"

ON QUERY (subject, relation):
  1. Find matching active/dirty triple
  2. If status == "dirty":
     a. Recursively resolve any dirty upstream dependencies first
     b. Re-prompt LLM with current active upstream triples
     c. Update object value, set status = "active"
  3. Return triple
```

This gives you:
- **O(1) insertion cost** — just flag dirty via edge traversal, don't cascade reasoning
- **O(k) query cost** — where k = depth of the dependency chain (only re-derive what's needed)
- **Natural auditability** — every triple has a visible status (`active`, `dirty`, `retracted`)
- **Graph-native** — dirty propagation is a simple BFS on `derived_from` edges in NetworkX

---

## Prompt Construction Strategy

When the system needs the LLM to reason, structure the prompt like this:

```
SYSTEM: You are a reasoning assistant. You must base your conclusions
ONLY on the knowledge graph triples provided below. Explain your
reasoning step by step, referencing triple IDs.

ACTIVE BELIEFS (subject, relation, object):
- [b001] (applicant_1, has_income, 6000)        — factual, 2026-03-07
- [b002] (loan_policy, min_income, 5000)         — rule
- [b003] (applicant_1, loan_status, ???)          — derived, DIRTY

RETRACTED (for context):
- [b001_old] (applicant_1, has_income, 4000)     — retracted

TASK: Re-derive the value of b003 (applicant_1, loan_status, ???)
based on the active triples above. State your conclusion as a
(subject, relation, object) triple.
```

Key design decisions:
- **Label each triple with its ID** so the LLM's output can reference specific beliefs for traceability.
- **Present beliefs in triple format** — the LLM sees the same structure the system uses internally, reducing translation errors.
- **Show retracted triples for context** so the LLM understands *what changed* and can explain the revision.
- **Ask for output as a triple** so the result can be directly inserted back into the KG.
- **Constrain the LLM** ("ONLY on the triples provided") to prevent hallucination from parametric knowledge.

---

## Summary of Recommendations

| Aspect | Recommendation |
|---|---|
| Belief representation | Knowledge graph triples `(subject, relation, object)` with metadata |
| Belief types | Separate into `factual`, `derived`, `rule` |
| Graph library | NetworkX (in-memory, JSON-serializable, BFS built in) |
| Dependencies | `derived_from` edges in the graph |
| Lazy revision | On-conflict: flag dirty via graph traversal, re-derive on query |
| Prompt injection | Serialize relevant triples into prompt, ask LLM to output triples |
| Contradiction detection | Same `(subject, relation)` with different `object` |
| Evaluation | Compare with/without belief tracking on consistency & contradiction rate |
