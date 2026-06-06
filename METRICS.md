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

The evaluation pipeline obtains the model’s predicted answer and a confidence score derived from the model’s output probabilities. Each prediction is paired with a binary correctness label ($o = 1$ if correct, $o = 0$ if wrong), and we then compute accuracy, Brier score, expected calibration error (ECE), and Macro Calibration Error (MacroCE) over the full set of examples. Accuracy measures answer correctness, while Brier score, ECE, and MacroCE measure whether the model’s confidence is aligned with correctness, with MacroCE giving a balanced view across correct and incorrect predictions.

#### Brier Score

**What it is:** The average of $(p - o)^2$ over all items, where $p$ is the model's confidence and $o$ is the actual correctness.

**What it tells you:** Measures the "mean squared error" of the model's self-assessment. A lower score indicates the model's confidence is more predictive of its actual success.

#### Log Loss

**What it is:** The mean negative log-likelihood of the outcomes given the model's probabilities.

**What it tells you:** Penalizes "confident wrong" answers heavily. If the model is 99% sure but incorrect, Log Loss will be very high.

#### Expected Calibration Error (ECE)

**What it is:** Predictions are grouped into bins by confidence, and we compare the average confidence in each bin to the actual accuracy of that bin.

**What it tells you:** The "gold standard" for calibration. It tells you exactly how much the model's probability deviates from its true accuracy rate on average.

#### Macro Calibration Error (MacroCE)

**What it is:** A balanced version of the calibration error. It calculates the mean absolute error for correct predictions ($ICE_{pos}$) and incorrect predictions ($ICE_{neg}$) separately, then averages them: `0.5 * (ICE_pos + ICE_neg)`.

**What it tells you:** Prevents calibration results from being dominated by high accuracy. If a model is 99% accurate, standard ECE mostly reflects correct cases. MacroCE forces an equal look at how "arrogant" the model is when it is wrong versus how "timid" it is when it is right.

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

### End-to-End Accuracy (Dual-Agent)

**What it is:** In the dual-agent system, did the final answer (after Agent 2 matched it to an MCQ
option) match the correct answer label?

**What it tells you:** The overall accuracy of the dual-agent pipeline. Compare to BBR to
diagnose where failures happen.

---

---

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

---

## Quick Reference Table

| Acronym                | Full Name                        | One Line                                            | Category          |
| ---------------------- | -------------------------------- | --------------------------------------------------- | ----------------- |
| **Accuracy**           | Accuracy                         | Fraction of correct answers                         | Core              |
| **Var/Std**            | Variance & StdDev of Raw Score   | Statistical spread across N runs                    | Stability         |
| **Evidence Precision** | Evidence Precision               | Fraction of cited keys that were relevant           | Reasoning Quality |
| **Evidence Recall**    | Evidence Recall                  | Fraction of relevant keys that were cited           | Reasoning Quality |
| **Evidence F1**        | Evidence F1                      | Harmonic mean of precision and recall               | Reasoning Quality |
| **E2E Acc (DA)**       | End-to-End Accuracy (Dual-Agent) | Final answer accuracy after dual-agent pipeline     | Dual-Agent        |
| **AFR**                | Answer Flip Rate                 | How often does same question get different answers? | Stability         |
| **EFR**                | Extraction Failure Rate          | Fraction of responses with no extractable answer    | Failure Modes     |
| **EMD**                | Extraction Method Distribution   | Breakdown of which extraction methods were used     | Failure Modes     |
| **BS**                 | Brier Score                      | Mean squared error of predicted probability         | Calibration       |
| **LL**                 | Log Loss                         | Penalty for confident wrong answers                 | Calibration       |
| **ECE**                | Expected Calibration Error       | Bin-weighted deviation of confidence from accuracy  | Calibration       |
| **MacroCE**            | Macro Calibration Error          | Balanced calibration error across correct/incorrect | Calibration       |
