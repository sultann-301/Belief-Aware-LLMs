# Reproducibility and cleanup checklist

Review date: 2026-10-14. Tests: **183 passed, 1 failed**. The repo needs the fixes below before reviewer release.

**Keep:** shared reporting helpers, scenario filtering, prompt weighting, missing-data checks, source hashes, and the notebook runner.

**Trim:** duplicate notebooks, backups already preserved in Git, duplicated exports, runtime lock files, and speculative GraphRAG planning sections.

## Actions, in priority order

- [ ] **Fix reproducibility.** `graphrag_single_agent_comparison.ipynb` recreates 62 incorrect zero placeholders instead of the undefined values in saved tables.
- [ ] **Refresh validation.** Forty chart files fail their recorded hashes. Regenerate outputs after the first fix, then rerun checks.
- [ ] **Fix the execution check.** `tests/test_non_hard_reporting.py` requires execution counts even for an empty code cell; remove that cell or skip empty cells.
- [ ] **Document installation.** Add tested dependency versions, Python/Ollama versions, and model identifiers/digests; there is currently no dependency manifest.
- [ ] **Package exact inputs.** Publish a versioned CSV bundle with checksums and download instructions; remove dependencies on unrelated CSVs and local backups.
- [ ] **Align reproduction configs.** The standard config runs only v15/v1, while reporting requires v15/v16 and v1/v2. Document commands for both required cohorts.
- [ ] **Consolidate notebooks.** The dual-agent pair differs only by output folder; the single-agent pair is almost identical. Keep one of each plus the GraphRAG comparison.
- [ ] **Trim artifacts.** Archive backups and historical charts outside paper outputs; ignore the runtime `.lock` file. Keep canonical figures and their underlying tables.
- [ ] **Update stale documentation.** The report says 79 figures; there are 105. Its prompt splits and exclusions also differ from current notebook behavior.
- [ ] **Publish the reviewed state.** Commit required helpers, tests, outputs, and documentation, then tag the paper's exact version.

## Review limits

Live model reruns, Drive contents, and paper-to-result agreement were not checked. Historical checkpoint/settings differences still limit experimental comparability.

Raw data and source code stayed unchanged during review. Generated CSVs touched during checking had their corrected values and coverage restored from existing audit records.
