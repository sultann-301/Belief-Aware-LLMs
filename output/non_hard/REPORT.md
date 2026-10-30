# Non-Hard analysis handoff — 2026-10-07

Project: `/Users/mws/Documents/GitHub/Belief-Aware-LLMs`.

**Hard scenarios are excluded from the reported benchmark.** All current notebooks report only loan, alien_clinic, crime_scene and thorncrester × belief_maintenance, absurd, absurd_temporal and grounding. Noise and bare-domain experiments are also outside these 16 combinations. Source CSVs were not modified. No model evaluations were run. No LaTeX or conference-paper workspace was accessed.

## Files and fallback copies

Updated files (relative to the project root):

- `graphrag_single_agent_comparison.ipynb`
- `final_single_agent_analysis.ipynb`
- `eval_results_analysis.ipynb`
- `dual_agent_analysis.ipynb`
- `final_dual_agent_analysis.ipynb`
- `scripts/analysis_reporting.py`
- `scripts/execute_analysis_notebooks.py`
- `tests/test_non_hard_reporting.py`
- `README.md`

All five original `.ipynb` files are preserved byte-for-byte in `backups/before_non_hard_standardization_2026-10-07/`, with `sha256.json`. The pre-existing `final_single_agent_analysis.ipynb.bak` was also copied there. The obsolete root `hard_scenario_average_accuracy_by_model.png` was moved into that backup folder so it is not mistaken for a current benchmark chart. Existing unrelated README edits, baseline planning files and source data were preserved.

The comparison notebook retains its analysis structure. The two historical single-agent notebooks now render checked exports from that notebook, replacing stale, out-of-order and inconsistently labeled calculations. The two dual-agent notebooks retain a separate experiment, use the existing legacy-column repair, and split prompt cohorts. Their old mixed-condition/mixed-family and missing-as-zero views were replaced. No raw normalization or evaluation scripts were changed.

## Coverage and accuracy audit

All five models have **16/16 combinations in GraphRAG v1, With Store v15, With Store v16, No Store v1 and No Store v2**. No missing accuracy combinations; 80 matched model/combination cells, 240 reported system/cell accuracy values. GraphRAG has 8,000 turns (five models × 16 combinations × 10 runs × 10 turns).

The table's “before” columns describe broader historical single-agent summaries that included Hard where available. The previous comparison notebook's matched primary accuracy already used the same 16 combinations, so its primary accuracy values do not change. Historical small models had no Hard rows; larger models had four additional Hard combinations.

| Model | Historical combinations before → after | With Store accuracy before → after | No Store accuracy before → after | GraphRAG accuracy (unchanged) |
| --- | --- | --- | --- | --- |
| gemma3:1b | 16 → 16 | 0.56125 → 0.56125 | 0.3696875 → 0.3696875 | 0.270625 |
| gemma4:e2b | 20 → 16 | 0.77875 → 0.8396875 | 0.509 → 0.5528125 | 0.754375 |
| llama3.2:1b | 16 → 16 | 0.3884375 → 0.3884375 | 0.1746875 → 0.1746875 | 0.26375 |
| ministral-3:3b | 20 → 16 | 0.8175 → 0.885 | 0.57125 → 0.601875 | 0.701875 |
| Qwen3:4b, no thinking | 20 → 16 | 0.8265 → 0.896875 | 0.58 → 0.62375 | 0.385 |

All five expected With Store means were reproduced from data, including a separate verification against the wide `eval_results.csv`. They are not hard-coded in reporting or checks. Overall equal-cell accuracies: GraphRAG **0.475125**, With Store **0.71425**, No Store **0.4645625**. GraphRAG minus With Store is **−23.9125 pp**; GraphRAG minus No Store is **+1.05625 pp**. These are descriptive differences.

## Exports and charts

All paths below are relative to `output/non_hard/`:

- `accuracy_cells.csv`, `accuracy_prompt_cells.csv`: full-precision observations, including separately labeled prompt variants.
- `accuracy_by_model.csv`, `accuracy_by_scenario.csv`, `accuracy_by_family.csv`, `accuracy_by_combination.csv`, `accuracy_by_model_scenario.csv`, `accuracy_by_overall.csv`: means, sample SDs and observation counts.
- `before_after_accuracy.csv`, `source_selection.csv`: scope audit and before/after scores.
- `metric_cells.csv`, `metric_summaries.csv`: all metric cells plus available-case and matched-support summaries, labeled by prompt, aggregation dimension and support policy.
- `metric_coverage.csv`, `missing_metric_values.csv`, `missing_accuracy_combinations.csv`: explicit expected/available/missing support, including structurally unavailable metrics.
- `raw_score_variability_cells.csv`, `graphrag_run_scores.csv`, `graphrag_run_stats_by_combination.csv`, `graphrag_run_accuracy_spread.csv`: appropriate underlying run or cell observations; raw-score SDs are not averaged.
- `confidence_coverage.csv`, `graphrag_diagnostics.csv`, `accuracy_deltas.csv`, `accuracy_cell_outcomes.csv`: diagnostics and comparison detail.
- `supplemental_cells.csv`, `supplemental_metric_coverage.csv`, `supplemental_missing_metric_values.csv`, `supplemental_shared_summary.csv`: separate v16_one_shot experiment, filtered to the same 16 combinations.
- `undefined_word_means_audit.csv`, `undefined_afr_audit.csv`: original historical zero placeholders marked undefined because the relevant response group is empty.
- `definitions.json`, `metric_definitions.csv`: aggregation definitions, metric direction, prompt mapping, source-file SHA-256 hashes and experimental limitations.
- `charts/`: 15 comparison figures, each PNG and SVG, with numerical CSV sidecars.
- `final_single_agent_analysis/`, `eval_results_analysis/`: each notebook's charts, sidecars and detailed single-agent summaries.
- `dual_agent_analysis/`, `final_dual_agent_analysis/`: each notebook's separate dual-agent charts, summary CSVs, metric coverage and source/aggregation definitions.
- `chart_manifest.json`: complete chart inventory, CSV data associations and artifact hashes.
- `checks.json`, `execution.json`, `validation.json`: executed checks and notebook provenance.

Total: **79 figures**, each exported as PNG and SVG, across all five refreshed notebooks.

## Aggregation and variability

Accuracy: average With Store v15/v16 equally within each model/combination; average No Store v1/v2 equally within the same combination; then average the 16 combinations equally. Both variants are required. GraphRAG contributes v1 once. The existing normalizer maps evaluation v15 → baseline v2 and evaluation v16 → baseline v1; this mapping is verified against code, but is inferred historical metadata rather than independent run metadata.

Other primary metrics compare GraphRAG v1 / With Store v16 / No Store v1 on each metric's complete shared support. Separate prompt and available-case summaries are also exported. Missing values are never filled with zero. Evidence/fidelity/EMD condition labels are repaired in memory using the existing evaluator semantics.

Accuracy SD is recomputed with ddof=1 after prompt averaging: 16 combination accuracies per model, 20 model/combination accuracies per scenario type, and 80 overall. This measures task/model heterogeneity, not run uncertainty, a standard error, or a paired confidence interval. Other metric SDs describe the retained per-combination metric summaries. GraphRAG run variability is recomputed from individual runs; its pooled 160 scenario/run observations per model mix task difficulty and run variability. Historical per-combination raw-score SDs are available. A pooled run-accuracy SD has not been reconstructed; deriving it from the saved means, variances and run counts would require confirmed historical turns per run. Stored raw-score variances/SDs remain per combination and prompt; no standard deviations are averaged into a replacement SD.

## Remaining data limitations

- Llama No Store v1 lacks Brier, log loss, ECE and MacroCE in four combinations: `loan_belief_maintenance`, `alien_clinic_absurd_temporal`, `crime_scene_absurd`, `crime_scene_absurd_temporal`. Calibration charts therefore use 76/80 shared cells (12/16 for Llama).
- Llama No Store v1 has six undefined AFR values where EFR=1 (no extracted answers); historical zeros are retained in `undefined_afr_audit.csv`. Primary AFR uses 74/80 shared cells (10/16 for Llama).
- Llama With Store v16 lacks bracketed-exact EMD in six combinations: `loan_belief_maintenance`, `loan_absurd`, `loan_absurd_temporal`, `alien_clinic_absurd_temporal`, `crime_scene_absurd`, `crime_scene_absurd_temporal`.
- GraphRAG has three undefined word-count means: correct-response words for Llama `thorncrester_grounding`; incorrect-response words for Gemma4 `thorncrester_belief_maintenance` and Ministral `crime_scene_belief_maintenance`.
- 56 historical word-count zero placeholders are undefined empty groups (accuracy exactly 0 or 1), now marked missing. The supplemental one-shot experiment has 21 such undefined means. Exact rows and per-prompt counts are exported; these are not zero-length responses.
- Evidence, BCR, SBIR and timing are unavailable for GraphRAG. No Store has no legitimate evidence/fidelity values; timing exported in the store column measures a parallel batch, not a store-only request.
- GraphRAG confidence is missing on 1843 of 8000 turns. The calibration subset may be strongly selected; historical confidence denominators cannot be reconstructed. Confidence coverage by model is in `confidence_coverage.csv`.
- Dual-agent reports are separate: four reasoner/matcher pairs × two prompts × 16 combinations, five runs per combination. All expected metric rows are present after in-memory legacy-header repair; ten incorrect-response word means (five per prompt) are undefined empty groups and are explicitly missing in the dual-agent metric coverage and audits. No Store+History observations are available, and noise is excluded.

## Interpretation for downstream reporting

**Paper exclusions requested by the user:** Do not include `AFR_Answer_Flip_Rate` or `TPCA_Words_Wrong` (average words in incorrect responses). These remain experimental diagnostics only. Use **Qwen3:4b, no thinking** as the shared display name; preserve source identifiers in provenance. Accuracy SD is across scenario combinations, not run-to-run uncertainty.

Historical Qwen uses `hoangquan456/qwen3-nothink:4b`; GraphRAG uses `qwen3:4b` with `think=False`. It is labeled **Qwen3:4b, no thinking**. GraphRAG also uses supplied targets, snapshot history, sampled paraphrases, scenario_seed=0, domain-dependency-v2 retrieval, disabled response caching, num_predict=768 and num_ctx=8162. Historical summaries do not establish identical questions, histories, seeds or generation settings. Temperature and run count match the main comparison; experimental equivalence and causal attribution do not follow.

Downstream text should exclude Hard/noise benchmark claims, replace historical mixed-scope means and SDs, distinguish sample SD across combinations from run uncertainty, retain explicit prompt versions and metric-specific counts, describe TPCA as words rather than tokens, preserve the Qwen checkpoint caveat, and avoid interpreting matching coverage as a controlled causal comparison.

## Validation

Executed from the project root:

```sh
python3 scripts/execute_analysis_notebooks.py
python3 -m tests.test_non_hard_reporting
python3 -m compileall -q scripts/analysis_reporting.py scripts/execute_analysis_notebooks.py tests/test_non_hard_reporting.py
```

All five notebooks executed with fresh kernels and no error outputs. Checks passed for suffix exclusion, exact 5 × 16 accuracy support, duplicate detection, manifest/run completeness, prompt mapping, equal weighting, independent raw-wide accuracy agreement, metric toy cases/missingness, recomputed summary means/SDs, plotted/exported values, chart artifact hashes, valid JSON, and byte-for-byte preservation of source CSVs and original notebook backups. Representative comparison, calibration and dual-agent charts were visually inspected; label/footer overlap was corrected. No applicable AGENTS.md was found in the project or ancestor directories.
