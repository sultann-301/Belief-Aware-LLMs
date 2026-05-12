# Expanded Evaluation Plan: Calibration & Robustness

This document outlines the scope, schedule, and metrics for the final week of evaluation. The goal is to provide additive evidence for the thesis by testing model performance under stress (paraphrasing, noise, temperature) and architecture variations (dual-agent).

---

## 1. Scope Calculation

### Paraphrasing Runs
- **Source Data**: 5 scenario types × 4 domains × 10 turns = 200 turns to paraphrase.
- **Evaluation**: Run 5 LLMs × 2 conditions (With_Store, No_Store) = 10 full runs on the paraphrased set.

### Temperature Runs (Focused)
- **Scope**: 2 temps (T=0.5, T=0.9) × 2 samples.
- **Target**: Run only on **Absurd Compliance** and **Temporal** turns.
- **Goal**: Measure "hidden stochasticity" and flip rates where model logic is most strained.

### Noise Scenarios
- **Source Data**: 10 turns × 4 domains = 40 new turns.
- **Method**: Append irrelevant real-world "noise" to the question (e.g., "...Also my cat drank milk today.").
- **Metric**: Robustness to noise (correctness and confidence stability).

### Dual-Agent Architecture
- **Configuration**: 10 agent pairs (Reasoning Agent + Answer Agent).
- **Evaluation**: 5 scenario types × 4 domains × 2 conditions = 400 total runs.
- **Priority**: Representative subset of 5 pairs if time is constrained.

### "Hard Mode" (Hard Belief Revision)
- **Target**: Larger models only (`gemma4:e2b`, `hoangquan/qwen3-nothink:4b`).
- **Concept**: Temporal rule hierarchies testing state memory and logic under "masking."
- **Scenario Components**:
    - **Masking**: A dominant belief (e.g., "Global Freeze") overrides all variables.
    - **Shadow Updates**: Variables are updated while masked; the model must ignore them for the final decision but remember them.
    - **Unmasking**: The mask expires, forcing a "state spring-back" where the model must calculate the result based on all accumulated shadow updates.
- **Scope**: 5 complex multi-turn scenarios per domain.

---

## 2. Day-by-Day Schedule

### Day 1 — Paraphrasing + Noise + Hard Mode Setup
- **Morning**: Run paraphraser on 200 turns. Perform manual quality audit.
- **Afternoon**: Author 40 noise turns AND the **Hard Belief Revision** suite (5/domain).
    - These require complex temporal logic chains (Mask → Shadow Updates → Unmask).

### Day 2 — Stress Test Evaluations
- **Task**: Run Paraphrased suite, Noise suite, and **Hard Mode** suite in parallel.
- **Models for Hard Mode**: Strictly larger models (4b+).
- **Setup**: Prepare dual-agent pipeline logic.

### Day 3 — Dual-Agent Setup + First Runs
- **Morning**: Finalize dual-agent pipeline. Perform end-to-end test on one domain.
- **Afternoon**: Start dual-agent runs. Prioritize diverse model sizes:
  - `gemma3:1b` + `ministral-3:3b` (Small + Small)
  - `gemma4:e2b` + `llama3.2:1b` (Strong + Weak)
  - `qwen3-nothink:4b` + `gemma4:e2b` (Strong + Strong)

### Day 4 — Dual-Agent Finalization + Temperature
- **Morning**: Complete remaining dual-agent pair runs.
- **Afternoon**: Run Temperature suite (T=0.5, T=0.9) on Absurd/Temporal turns.

### Day 5 — Analysis + Thesis Integration
- **Metrics**: Compute Brier, ECE, and MacroCE across all new conditions.
- **Writeup**: Integrate findings into the "Results and Evaluation" chapter.

---

## 3. Key Metrics & Analysis

| Metric | Formula / Calculation | Interpretation |
| :--- | :--- | :--- |
| **Paraphrase Sensitivity** | `|Brier_orig - Brier_para|` | High delta suggests model relies on surface patterns, not beliefs. |
| **Noise Sensitivity** | `|prob_clean - prob_noisy|` | Measures how much irrelevant context bleeds into the decision process. |
| **Dual-Agent Delta** | `ECE_single - ECE_dual` | Quantifies the benefit of separating reasoning from decision-making. |
| **Temperature Flip Rate** | `P(Ans_T > 0 != Ans_T = 0)` | Measures logical stability in the face of stochasticity. |

---

## 4. Contingency Plan (What to cut)

If the schedule slips, prioritize based on thesis value:
1. **First Cut**: Reduce temperature runs to a single T=0.7 × 2 samples.
2. **Second Cut**: Reduce Dual-Agent evaluation to the top 3 most interesting model pairs.
3. **Third Cut**: Reduce Noise Scenarios to only 2 domains instead of 4.

**Focus**: The core "With_Store vs No_Store" finding is already strong. These evaluations are "hardness tests" to prove the robustness of the architecture.
