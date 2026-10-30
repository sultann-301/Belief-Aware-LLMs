# LLM + Graph Retrieval Evaluation Baseline

## Purpose

Test whether deterministic rule execution improves answer accuracy beyond
retrieving the relevant rules and facts for an LLM. The experiment covers all
four domains and supplies the same benchmark target attributes to both
graph retrieval and the belief store.

This is a custom dependency-graph RAG baseline using the project's hand-authored
rule topology. It is not an implementation of Microsoft's GraphRAG software.

| Condition | Context selection | Rule execution |
| --- | --- | --- |
| LLM only | Receives the full domain rules and facts | LLM |
| LLM + graph retrieval | Retrieves relevant rules and base facts using supplied targets | LLM |
| LLM + belief store | Selects dependencies and computes derived values | Deterministic Python |

Plain LLM versus graph retrieval measures the effect of context selection.
Graph retrieval versus belief store measures the benefit of supplying computed
values. Results for plain LLM and belief store already exist: run only the new
graph baseline and compare its results with the relevant existing results.
Question-to-attribute matching is a later, separate experiment.

The new graph condition reconstructs the current asserted input state and uses
no assistant chat history. Sequential scenarios accumulate input updates;
independent scenarios reset to their initial facts. The paper batch samples
paraphrases; the single-set smoke command uses canonical questions.
Before comparing with existing results, match the model, generation
settings, scenario subset, prompt profile, and question-selection policy; the
older runner may have sampled paraphrases. Historical results are left intact.
This tests LLM rule execution after input updates, not the cost or correctness
of incremental state maintenance.

Graph retrieval reuses the existing baseline system prompt and format. Record
the prompt version when interpreting results alongside historical evaluations.
Existing evaluation commands retain their original behavior.

## Compatibility Requirement

The existing evaluation workflow must remain unchanged by default:

- Existing commands continue to work.
- `run_with_store()` and `run_without_store()` retain their behavior.
- Existing CSV schemas and result files are not modified initially.
- Graph retrieval is introduced as an opt-in condition with a separate results file.
- Existing tests must continue to pass.

## Information Boundaries

The controlled graph baseline may use:

- The natural-language question.
- Current asserted facts and belief updates.
- Explicit scenario assertions on normally derived attributes are allowed.
  For example, Alien Clinic directly asserts a prescription in two temporal
  turns. These are input facts, not values computed by the deterministic store.
  Retrieval stops at an asserted key and omits its producing rule. This follows
  assertion precedence; it does not reproduce the store's dirty-flag behavior.
- Domain definitions and human-readable rules.
- `turn["attributes"]` as supplied retrieval targets, just as the store does.
- Answer options when constructing the final LLM prompt.

Graph retrieval must not use:

- `turn["correct"]`, which is the answer key.
- Precomputed values produced by the deterministic belief store.
- Evaluation scenarios or correct answers as indexed documents.

The evaluator uses `correct` only after generation. Supplied attributes are
benchmark context filters, not necessarily literal question targets. Do not
use them uncritically as matcher ground truth in the later end-to-end experiment.

## Current Progress: Read-Only Loan Graph

The first isolated component is implemented in `evaluation/graphrag/`.

It provides:

- An immutable snapshot of the existing loan rules and asserted facts.
- Human-readable, non-executable rule nodes.
- Backward traversal from an explicitly supplied attribute.
- A dependency slice containing upstream rules and connected base facts.
- No execution of `derive_fn` and no generation of derived values.

For example, requesting `loan.application_status` returns the rules and base
facts needed to reason about that attribute, but does not calculate its value.

The implementation is covered by focused tests. At the time it was added, the
complete repository suite passed with 152 tests.

## Later Experiment: Natural-Language Attribute Matching

After the controlled comparison works, a separate component can translate a
question into one or more likely attributes without the supplied target hint:

```text
Question
  -> attribute matching
  -> selected graph attributes
  -> backward graph traversal
  -> retrieved rules and facts
```

Example:

```text
"What is the current application status?"
  -> loan.application_status
```

Questions may contain multiple targets:

```text
"What is the application status and review queue?"
  -> loan.application_status
  -> loan.review_queue
```

### Option A: Lexical and Alias Matching

Each attribute has a canonical phrase and a small set of aliases:

```text
loan.application_status
  - application status
  - loan status
  - approval status

loan.max_amount
  - maximum loan amount
  - borrowing limit
  - loan limit
```

Matching can combine exact phrases, aliases, and token overlap. This approach
is fast, deterministic, transparent, and easy to test. It may struggle when a
paraphrase shares few words with the stored descriptions.

### Option B: Embedding Matching

For embedding retrieval, create one searchable document per derived attribute:

```text
Attribute: loan.max_amount
Meaning: Maximum amount an applicant is permitted to borrow.
Related terms: borrowing limit, maximum loan, loan limit.
Rule: Depends on applicant eligibility and collateral.
```

The implementation would:

1. Embed all attribute documents once.
2. Embed the question.
3. Compare the question vector with attribute vectors using cosine similarity.
4. Select the top attributes above a confidence threshold.
5. Retrieve their dependency slices from the graph adapter.

The existing Ollama Python client supports embedding requests, so this does not
require LangChain or a vector database.

Embeddings improve synonym and paraphrase matching, but introduce another model,
configuration, caching, and possible GPU model-switching costs.

### Recommended Matching Strategy

Start with lexical and alias matching. Audit target annotations and reserve
held-out scenario/paraphrase families before tuning. Measure recall against
question targets separately from the evidence needed to assess answer options.
Add embeddings only if lexical matching has a meaningful retrieval gap.

If embeddings are added, use them as a fallback:

```text
Confident lexical match?
  yes -> use lexical result
  no  -> use embedding similarity
```

This keeps common direct questions fast and makes the more expensive semantic
matching available for difficult paraphrases.

## Embedding Performance

Embedding retrieval adds one small model operation per unique question, but the
cost can be controlled through caching.

Cache:

- Attribute-document embeddings by document hash and embedding model.
- Question embeddings by normalized question text and embedding model.

The evaluation suite repeats the same scenarios across runs. For 60 scenarios
evaluated 20 times, caching reduces up to 1,200 question embedding requests to
approximately 60 requests followed by cache hits.

The main remaining performance risk is model switching when the generation and
embedding models compete for limited GPU memory. A lexical-first strategy avoids
that cost for straightforward questions.

## Staged Implementation Plan

1. **Read-only loan graph adapter — complete**
   - Represent loan rule topology and asserted facts without executing rules.
   - Test immutability, graph coverage, and dependency traversal.

2. **Four-domain runner and serializer — implemented**
   - `evaluation/graphrag/condition.py` retrieves supplied target slices.
   - Reconstruct current input facts without executing rules.
   - Reject unsupported domain configurations; include only scenario assertions
     as facts, never values computed by the store.
   - Reuse baseline prompts, answer extraction, and grading.
   - Record actual retrieved rules/facts rather than counting key mentions in text.

3. **Standalone graph-baseline command — implemented**
   - `python3 -m evaluation.graphrag.run_evals --domain loan_absurd --dry-run`
     previews graph prompts without model calls.
   - Remove `--dry-run` and supply `--model` to run only graph retrieval + LLM.
     The plain LLM and belief-store conditions are not rerun.
   - `--csv-out` defaults to `eval_results_graphrag.csv`; existing files are never
     overwritten or appended to. Choose a new output path for each experiment.
   - Single-set runs use canonical questions. The paper batch uses the existing
     paraphrase selector, with a saved manifest shared across models.
   - Disable response caching. Record current inputs,
     question/options, model, temperature, prompt versions, and graph context.
   - Repeated runs sample generation variability; they do not add independent
     scenarios. Generation seeds are not yet exposed by the existing client.

4. **Paper batch — configured, real-model execution pending**
   - `python3 -m evaluation.graphrag.run_batch --dry-run` validates all contexts.
   - Remove `--dry-run` to run the batch in
     `evaluation/configs/thesis_graphrag_batch.json`.
   - Models: gemma3:1b, llama3.2:1b, ministral-3:3b, qwen3:4b, gemma4:e2b.
   - Explicit `think=false`; the removed modified Qwen is not used.
   - Only belief_maintenance, absurd, absurd_temporal and grounding, across
     loan, alien clinic, crime scene and Thorncrester.
   - Original settings: 10 runs, temperature 0.0, 4 workers, num_predict=768,
     num_ctx=8162, keep_alive=10m. Total: 8,000 generation calls.
   - Complete one model before starting the next to reduce model switching.
   - `--resume` reuses the saved manifest and skips completed runs, including
     results written by the original runner. Stop the original process first.
   - Incomplete runs repeat; partial CSV tails are backed up before recovery.
     `--resume --dry-run` checks progress without modifying results.
   - Inspect a few retrieved contexts, then run one small loan graph baseline.
   - Check grading and prompt sizes before scaling up run counts or model sizes.
   - Report answer accuracy by condition and subset, including extraction failures.
   - Model output is required before claiming an accuracy improvement.

5. **Broader evaluation — later**
   - Audit natural-language rule fidelity, scenario labels, and context limits.
   - Add generation seed support, timing/token measurements,
     and analysis of repeated runs.
   - Add question-driven retrieval as a separate experiment with audited labels,
     held-out tuning, and defined behavior for unknown/ambiguous queries.
