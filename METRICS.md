# Evaluation Metrics Reference

This document explains every metric used (or planned) in the belief-aware LLM evaluation system.
Written so you can come back to this in 3 months and understand exactly what each thing measures
without having to reverse-engineer the code.

---

## ⚠️ First — What NOT to Trust

The evaluator uses objective, code-derived uncertainty signals. Useful measures include Answer Flip
Rate (AFR), Determinism Score (DS), and Extraction Failure Rate (EFR).

---

## Currently Implemented Metrics

### Calibration & Uncertainty Metrics

The evaluation pipeline obtains the model’s predicted answer and a confidence score derived from the model’s output probabilities. Each prediction is paired with a binary correctness label ($o = 1$ if correct, $o = 0$ if wrong), and we then compute accuracy, Brier score, and expected calibration error (ECE) over the full set of examples. Accuracy measures answer correctness, while Brier score and ECE measure whether the model’s confidence is aligned with correctness.

#### Brier Score

**What it is:** The average of $(p - o)^2$ over all items, where $p$ is the model's confidence and $o$ is the actual correctness.

**What it tells you:** Measures the "mean squared error" of the model's self-assessment. A lower score indicates the model's confidence is more predictive of its actual success.

#### Log Loss

**What it is:** The mean negative log-likelihood of the outcomes given the model's probabilities.

**What it tells you:** Penalizes "confident wrong" answers heavily. If the model is 99% sure but incorrect, Log Loss will be very high.

#### Expected Calibration Error (ECE)

**What it is:** Predictions are grouped into bins by confidence, and we compare the average confidence in each bin to the actual accuracy of that bin.

**What it tells you:** The "gold standard" for calibration. It tells you exactly how much the model's probability deviates from its true accuracy rate on average.

---

### Accuracy

**What it is:** Fraction of turns where the model's extracted answer matches the correct answer label.

```
Accuracy = correct_hits / total_turns
```

**What it tells you:** The baseline. Does the model get the right answer? Reported separately for:

- `WITH_STORE` — model sees serialized belief store in the prompt
- `NO_STORE` — model only sees natural-language rules (the baseline)
- `WITH_STORE + HISTORY` — model sees the store AND prior conversation turns

**Good score:** Higher is better. But accuracy alone doesn't tell you _why_ the model is right.

---

### Variance & StdDev of Raw Score

**What it is:** Statistical spread of accuracy across N repeated runs.

```
Variance = spread of [hits_per_run_1, hits_per_run_2, ..., hits_per_run_N]
```

**What it tells you:** A model that scores 7/10 on every single run is far more trustworthy than
one that scores 3/10 one time and 10/10 the next. High variance = the model is unstable and
results aren't reproducible.

**Good score:** Low variance. Ideally 0 at temperature=0.

---

### Evidence Precision

**What it is:** Of all the belief-store keys the model cited in its reasoning (e.g. `applicant.credit_score`),
what fraction were actually relevant to the question?

```
Evidence Precision = relevant keys cited / all keys cited
```

**What it tells you:** High precision = the model cited exactly the right evidence. Low precision =
the model is citing irrelevant beliefs as justification (reasoning slop / hallucinated citations).

**Good score:** High. 1.0 = every cited key was relevant.

---

### Evidence Recall

**What it is:** Of all the belief-store keys that _should_ have been cited to answer the question,
what fraction did the model actually mention?

```
Evidence Recall = relevant keys cited / all relevant keys that exist
```

**What it tells you:** High recall = the model didn't miss any important evidence. Low recall =
the model ignored relevant information in the store.

**Good score:** High. 1.0 = the model mentioned every relevant belief key.

---

### Evidence F1

**What it is:** The harmonic mean of Evidence Precision and Recall. A single combined score.

```
Evidence F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**What it tells you:** A balanced score. A model that achieves F1 = 1.0 cited exactly the right
evidence and nothing else. F1 penalizes both over-citing (noise) and under-citing (missing evidence).

**Good score:** High. This is the most useful single number for reasoning quality.

---

### Belief Binding Rate (BBR)

**What it is:** In the dual-agent system, Agent 1 reasons and produces a raw conclusion (e.g. "Approved").
BBR measures how often Agent 1's conclusion matches what the correct answer implies.

```
BBR = turns where Agent1_conclusion matches expected_conclusion / total turns
```

**What it tells you:** BBR isolates the _reasoning_ step from the _answer formatting_ step. It
tells you whether the reasoner itself is correct, independent of whether Agent 2 (the matcher)
correctly maps that conclusion to a multiple-choice option.

**Good score:** High BBR with lower End-to-End accuracy = the problem is in Agent 2 (matching).
Low BBR = the core reasoning is broken.

---

### End-to-End Accuracy (Dual-Agent)

**What it is:** In the dual-agent system, did the final answer (after Agent 2 matched it to an MCQ
option) match the correct answer label?

**What it tells you:** The overall accuracy of the dual-agent pipeline. Compare to BBR to
diagnose where failures happen.

---

---

## Planned / Proposed Metrics

The following metrics are not yet implemented but are documented here for future reference.

---

## 📦 Category 1: Belief Store Dependency Metrics

_Does the store actually change what the model outputs?_

---

### SDD — Store Dependency Delta

**What it is:** The accuracy improvement from having the belief store, compared to the no-store baseline.

```
SDD = Accuracy(WITH_STORE) − Accuracy(NO_STORE)
```

**What it tells you:** This is the core scientific claim of the whole system. If SDD is near 0,
the belief store isn't adding any information the model didn't already know from its training
data. If SDD is negative, the store is actually making things worse (prompt bloat or distraction).

**Planned variants:**

- **SDD by hop depth:** Does SDD increase with reasoning chain depth? It should — the store
  should help most on 4-hop questions that are too complex for parametric memory.
- **SDD by domain:** Which domains benefit most from the store?
- **SDD by scenario type:** How much does the store help on negation vs. grounding vs. absurd turns?

**Good score:** Positive. The bigger, the better. The key result.

---

### BSR — Belief Suppression Rate

**What it is:** On `absurd` scenario turns — where the belief store contains counterfactual or
impossible information (e.g., gravity is reversed, a patient has an impossible physiology) — what
fraction of the time does the model correctly follow the store instead of its real-world training?

```
BSR = correct answers on absurd turns / total absurd turns
```

**What it tells you:** A model that ignores the store and answers from real-world knowledge will
fail these turns. BSR directly tests whether the model actually grounds to the store or just
pattern-matches to what it "knows" is true in the real world.

**Example:** If the store says `loan.interest_rate = 0%` (an absurd but valid belief), and the
model says "that's not possible, interest rates can't be 0%" — it failed the BSR test.

**Good score:** High. If BSR is low, the model isn't truly belief-aware.

---

### CWCR — Closed-World Compliance Rate

**What it is:** On `grounding` scenario turns — where the answer to the question is genuinely not
in the belief store — what fraction of the time does the model correctly say "Cannot Answer"
instead of hallucinating an answer?

```
CWCR = correct "Cannot Answer" responses / total grounding turns
```

**What it tells you:** Tests epistemic restraint. The model should know the limits of what the
store tells it. A model that always guesses will fail these turns. A model that truly respects the
closed-world assumption of the store will abstain when the information isn't there.

**Good score:** High. Low CWCR = the model hallucinates freely and doesn't respect the store's
epistemic boundaries.

---

---

## 🧠 Category 2: Reasoning Chain Integrity Metrics

_Is the reasoning process actually correct, not just the final answer?_

---

### HDDC — Hop-Depth Degradation Curve

**What it is:** Accuracy at each level of reasoning chain depth: 1-hop, 2-hop, 3-hop, 4-hop.
A "hop" is one inference step (e.g., `credit_score → risk_level` is 1-hop;
`credit_score → risk_level → interest_rate → monthly_payment` is 4-hop).

```
HDDC = [Acc(1-hop), Acc(2-hop), Acc(3-hop), Acc(4-hop)]
```

**What it tells you:** You'd expect accuracy to decrease with hop depth — multi-step reasoning
is harder. But the _shape_ matters:

- Smooth monotonic decline = systematic reasoning degradation (expected and explainable)
- Erratic / non-monotonic = the model is not actually reasoning, it's guessing

This is one of the most important ablation results for any paper or report on this system.

**Good score:** Graceful degradation. Not a cliff from 1-hop to 2-hop.

---

### OC — Overcitation Rate

**What it is:** What fraction of the keys the model cited were _not_ relevant?

```
OC = 1 − Evidence_Precision = irrelevant keys cited / all keys cited
```

**What it tells you:** Identical to `1 − Evidence_Precision` — just a more intuitive framing.
If 40% of cited keys are irrelevant, the model is reasoning sloppily, citing everything it sees
rather than the specific evidence needed.

**Good score:** Low. Ideally 0.

---

### RAC — Reasoning-Answer Consistency

**What it is:** Do the evidence keys the model cited actually _lead to_ the answer it gave, when
run through the belief store's rules engine?

Steps:

1. Extract which belief keys the model cited
2. Feed _only those keys_ into `BeliefStore` and run `resolve_dirty_for_attributes()`
3. Check what answer the store's rules would produce
4. Compare to what the model actually output

```
RAC = turns where derived_answer(cited_keys) == model_output / total turns
```

**What it tells you:** This is the most rigorous metric. A model that gets the right answer
for the wrong reasons (lucky guess, parametric recall, random sampling) will have:

- High Accuracy
- Low RAC

A model that is genuinely using the store's reasoning chain will have RAC ≈ Accuracy.

**RAC < Accuracy** is the danger sign — it means the model is right but not for the stated reasons.

**Good score:** High, and close to Accuracy. Requires the most engineering to implement.

---

### NCR — Negation Comprehension Rate

**What it is:** Accuracy specifically on `negation` scenario turns — questions where the belief
involves a negated fact (e.g., "the patient does NOT have condition X").

```
NCR = correct answers on negation turns / total negation turns
```

**What it tells you:** Negation is one of the most well-documented failure modes of LLMs. A
model that scores 80% overall but 40% on negation turns is fundamentally unreliable — it's
confusing "does not have" with "has". Negation turns are a stress test for attention to detail.

**Good score:** High. Should be close to overall accuracy. A large gap = serious reasoning problem.

---

---

## 🎲 Category 3: Behavioral Consistency & Stability Metrics

_Is the model reliably consistent, or is it noisy?_

---

### PTC Variance — Per-Turn Consistency Variance

**What it is:** For each question (turn), compute the fraction of runs that got it right. Then
compute the variance of _that distribution_ across all questions.

```
PTC[t] = hits_for_turn_t / N_runs   (for each turn t)
PTC_variance = Var([PTC[1], PTC[2], ..., PTC[T]])
```

**What it tells you:** A model with PTC_variance ≈ 0 is uniformly reliable across all questions
(always right or always wrong on each one). High PTC_variance means the model is wildly
inconsistent — some questions it always gets right, others it always fails. For a reasoning system,
this is a red flag: questions should have similar difficulty if the reasoning process is systematic.

**Good score:** Low. High variance across turns suggests the model is not doing principled reasoning.

---

### AFR — Answer Flip Rate

**What it is:** Across N runs on the same turn (same prompt, same beliefs, same question), how
often does the model give a different answer?

```
AFR[t] = (N − count_of_most_common_answer[t]) / N   per turn
mean_AFR = avg(AFR[t] for all turns)
```

**What it tells you:** This is an **objective, code-derived uncertainty measure**. If the model
truly understands the question and is reasoning systematically, it should almost always give the
same answer to the same question. High AFR means the model is sampling from a noisy distribution,
not performing deterministic reasoning.

**Key comparison:**

- `AFR(WITH_STORE)` vs `AFR(NO_STORE)` — Does the belief store _stabilize_ outputs?
  If WITH_STORE has lower AFR, that's evidence the store is providing genuine grounding.

**Good score:** Low. At temperature=0, AFR should be near 0. At temperature=0.7, some variance
is expected — but high AFR even on simple 1-hop turns is a red flag.

---

### DS — Determinism Score

**What it is:** At temperature=0.0, what fraction of turns produce the _same answer_ across all N runs?

```
DS = turns where all N runs returned the same answer / total turns  (at temp=0 only)
```

**What it tells you:** Temperature=0 _should_ be fully deterministic (same input → same output).
In practice, Ollama/vLLM can have non-determinism from parallel sampling, quantization noise,
or hardware differences. DS < 1.0 at temp=0 is a data quality issue — it means your "deterministic
baseline" is actually stochastic, which undermines the scientific validity of those results.

**Good score:** 1.0 at temperature=0. Anything less needs investigation.

---

---

## 🔴 Category 4: Failure Mode Analysis Metrics

_How does the model fail, not just how often?_

---

### EFR — Extraction Failure Rate

**What it is:** What fraction of model responses produced no extractable answer at all?

```
EFR = count(answer == None) / total_turns
```

The code tries multiple strategies to extract an answer (`bracketed_exact` → `bracketed_normalized`
→ `unbracketed_substring`). If all fail, the result is `None`.

**What it tells you:** This is a **validity threat** for all other metrics. If EFR = 20%, your
accuracy metric is computed over only the 80% of responses where extraction succeeded — and those
responses may not be a random sample (the model might fail extraction more often when it's
confused, biasing accuracy upward).

Currently, failures are logged to `failed_extractions.log` but never surfaced as a metric.
That needs to change.

**Good score:** Near 0. Above 5% is a serious problem. Above 10% means prompt format is broken.

---

### EMD — Extraction Method Distribution

**What it is:** Of the responses where extraction _did_ succeed, what method was used?

```
EMD = {
    "bracketed_exact":      X%,   ← Gold standard: model output exactly "[Option text]"
    "bracketed_normalized": X%,   ← Minor formatting difference but still bracketed
    "bracketed_substring":  X%,   ← Fuzzy match inside brackets
    "unbracketed_normalized": X%, ← Model ignored the brackets instruction entirely
    "unbracketed_substring":  X%, ← Most fragile: substring match without brackets
}
```

**What it tells you:** Your accuracy number is only as clean as your extraction. If 40% of
extractions are `unbracketed_substring`, those answers were found by fuzzy matching — they could
be wrong extractions reported as correct. You need to know this to assess how much to trust
the overall accuracy number.

Ideally, `bracketed_exact` should be > 90%.

**Good score:** Mostly `bracketed_exact`. Lots of `unbracketed_*` = prompt format is failing.

---

### SEP — Systematic Error Patterns (Confusion Matrix)

**What it is:** When the model is wrong, what does it choose instead?

```
SEP[correct_label][predicted_label] = count of times the model predicted `predicted_label`
                                       when the correct answer was `correct_label`
```

This forms a confusion matrix across MCQ options.

**What it tells you:** Random errors would spread uniformly across wrong options. Systematic
errors cluster — e.g. the model always picks "Cannot Answer" when the correct answer is a
specific value, or always picks the "more lenient" option in loan decisions. These patterns
reveal directional biases that accuracy alone hides.

**Good score:** Off-diagonal entries should be roughly uniform (random errors). Clustered
off-diagonal entries = systematic bias.

---

---

## 🔍 Category 5: Retrieval Fidelity Metrics

_Is the right information making it into the model's prompt?_

---

### BCR — Belief Coverage Rate

**What it is:** Of all the belief-store keys that are _relevant_ to a question (the canonical set),
what fraction actually appear in the text that was sent to the model?

```
BCR = |canonical_keys ∩ keys_serialized_to_prompt| / |canonical_keys|
```

**What it tells you:** This is upstream of reasoning. If BCR < 1.0, the store's filtering or
serialization pipeline is _dropping_ required information before the model even sees it. In that
case, accuracy failures are not the model's fault — your retrieval is broken. BCR should be 1.0
by design, but measuring it verifies that assumption isn't violated in practice.

**Good score:** 1.0 always. Anything less is a bug in retrieval.

---

### SBIR — Spurious Belief Injection Rate

**What it is:** Of all the belief-store keys sent to the model in the prompt, what fraction are
_not_ relevant to the current question?

```
SBIR = |keys_in_prompt − canonical_keys| / |keys_in_prompt|
```

**What it tells you:** The complement of BCR — this measures noise injection. If the prompt
contains many irrelevant beliefs, the model has to figure out which ones matter. High SBIR with
low Evidence Precision is a clear signal: the retrieval is injecting noise, and the model is
getting confused by it.

**Good score:** Low. Ideally 0 (only relevant beliefs in the prompt).

---

---

## ⚖️ Category 6: Comparative / Contrastive Metrics

_Does adding complexity actually help?_

---

### HBS — History Benefit Score

**What it is:** Does providing chat history to the model improve accuracy over the stateless version?

```
HBS = Accuracy(WITH_STORE + HISTORY) − Accuracy(WITH_STORE, stateless)
```

**What it tells you:** Justifies (or questions) the complexity of maintaining conversation history.

- `HBS > 0` → History helps. The model uses prior turns to reason better.
- `HBS ≈ 0` → History has no effect. The store alone is sufficient.
- `HBS < 0` → History hurts. The model gets confused by prior context, or prompt length
  causes attention degradation.

**Good score:** Positive, but the magnitude matters. Even a small positive HBS justifies history.

---

### DABS — Dual-Agent Benefit Score

**What it is:** Does the dual-agent architecture (separate Reasoner + Matcher) outperform a
single model doing everything in one shot?

```
DABS = Accuracy(DUAL_AGENT) − Accuracy(SINGLE_AGENT, WITH_STORE)
```

Ideally computed on the same domain, prompt version, temperature, and model.

**What it tells you:** The core justification for building a two-agent system. If DABS is near
zero or negative, the added engineering complexity is not paying off. If DABS is consistently
positive — especially on harder multi-hop turns — you have strong evidence for the architecture.

**Good score:** Positive. Critical metric for any paper arguing for the dual-agent design.

---

---

## ⏱️ Category 7: Latency & Efficiency Metrics

_What does the store cost in wall-clock time?_

---

### TPCA — Tokens Per Correct Answer (proxy: words)

**What it is:** Average length of model response for correct answers vs. incorrect answers.

```
TPCA_correct = avg(len(response.split()) for correct answers)
TPCA_wrong   = avg(len(response.split()) for wrong answers)
```

**What it tells you:** When a model hallucinates or is confused, it tends to generate longer,
more verbose responses as it "tries to explain itself." If `TPCA_wrong > TPCA_correct`, the
model is using more words when it's wrong — a reliable signal of confabulation. This can also
help you detect if a model is padding its response without reasoning.

**Good score:** `TPCA_wrong` should not be dramatically larger than `TPCA_correct`. A big gap
suggests verbosity-when-confused.

---

### WCT — Wall-Clock Time Per Turn

**What it is:** The total elapsed evaluation time divided by the number of turns × runs.

```
WCT = elapsed_seconds / (N_runs × N_turns)
```

**What it tells you:** The overhead cost of the belief store pipeline per query. At scale, even
a 200ms overhead per turn compounds significantly. Compare:

- `WCT(WITH_STORE)` vs `WCT(NO_STORE)` — How much does the store add?
- `WCT` by domain — Are some domains significantly slower (due to belief graph complexity)?

**Good score:** As low as possible. High WCT needs justification from SDD (store must add value
proportional to its cost).

---

---

## Quick Reference Table

| Acronym     | Full Name                      | One Line                                             | Category            |
| ----------- | ------------------------------ | ---------------------------------------------------- | ------------------- |
| **SDD**     | Store Dependency Delta         | Accuracy lift from having the store                  | Belief Dependency   |
| **BSR**     | Belief Suppression Rate        | Does model follow store over real-world knowledge?   | Belief Dependency   |
| **CWCR**    | Closed-World Compliance Rate   | Does model correctly say "I don't know"?             | Belief Dependency   |
| **HDDC**    | Hop-Depth Degradation Curve    | Accuracy vs. reasoning chain depth                   | Reasoning Integrity |
| **OC**      | Overcitation Rate              | Fraction of cited keys that were irrelevant          | Reasoning Integrity |
| **RAC**     | Reasoning-Answer Consistency   | Do cited keys actually lead to the stated answer?    | Reasoning Integrity |
| **NCR**     | Negation Comprehension Rate    | Accuracy specifically on negation questions          | Reasoning Integrity |
| **PTC Var** | Per-Turn Consistency Variance  | Variance in per-question reliability across runs     | Stability           |
| **AFR**     | Answer Flip Rate               | How often does same question get different answers?  | Stability           |
| **DS**      | Determinism Score              | At temp=0, how often are outputs identical?          | Stability           |
| **EFR**     | Extraction Failure Rate        | Fraction of responses with no extractable answer     | Failure Modes       |
| **EMD**     | Extraction Method Distribution | Are accuracy numbers from clean or fuzzy extraction? | Failure Modes       |
| **SEP**     | Systematic Error Patterns      | Which wrong answers get chosen? (confusion matrix)   | Failure Modes       |
| **BCR**     | Belief Coverage Rate           | Are all needed beliefs making it into the prompt?    | Retrieval Fidelity  |
| **SBIR**    | Spurious Belief Injection Rate | Are irrelevant beliefs cluttering the prompt?        | Retrieval Fidelity  |
| **HBS**     | History Benefit Score          | Does chat history help or hurt?                      | Comparative         |
| **DABS**    | Dual-Agent Benefit Score       | Does the 2-agent system beat single-agent?           | Comparative         |
| **TPCA**    | Tokens Per Correct Answer      | Are wrong answers longer? (verbosity = confusion)    | Efficiency          |
| **WCT**     | Wall-Clock Time Per Turn       | Overhead cost of the store pipeline per query        | Efficiency          |
| **BS**      | Brier Score                    | Mean squared error of predicted probability          | Calibration         |
| **LL**      | Log Loss                       | Penalty for confident wrong answers                  | Calibration         |
| **ECE**     | Expected Calibration Error     | Bin-weighted deviation of confidence from accuracy   | Calibration         |
| **BBR**     | Belief Binding Rate            | Does Agent 1 (reasoner) reach the right conclusion?  | Existing            |
