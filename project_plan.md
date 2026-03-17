# Project Timeline

## Methodology Phase (6 Weeks)

### Week 1: BeliefStore Core
**Show professor:** Working `BeliefStore` class with add/update/retract + revision log.

- [ ] Implement `BeliefStore` class: `beliefs`, `dependencies`, `is_derived`, `dirty`, `revision_log`
- [ ] Implement `add_hypothesis(key, value)` with conflict detection + logging
- [ ] Implement `remove_hypothesis(key)` with cascading retraction
- [ ] Implement `_propagate_dirty(key)` — recursive downstream marking
- [ ] Unit tests: insert, update, retract, dirty propagation, cascade retraction
- [ ] JSON serialization: `save(path)` / `load(path)` for persistence

**Demo:** Run a script that inserts beliefs, updates one, shows the revision log and dirty set.

---

### Week 2: Derivation Rules Engine
**Show professor:** Rules that auto-derive beliefs + resolve dirty keys.

- [ ] Implement `add_rule(name, inputs, output_key, derive_fn)`
- [ ] Implement `resolve_all_dirty()` with topological ordering (bottom-up)
- [ ] Implement `_resolve(key)` — find matching rule, run `derive_fn`, log result
- [ ] Hand-code all **Loan domain** rules (R1–R6)
- [ ] Unit tests: dirty → resolve → correct derived values, multi-hop chains
- [ ] Test cascading: change input → dirty propagation → resolve → verify all derived values update

**Demo:** Insert loan hypotheses, resolve, update income, resolve again, show revision log.

---

### Week 3: Prompt Construction + LLM Integration
**Show professor:** Working prompt builder + first LLM call with real beliefs.

- [ ] Implement `get_relevant_beliefs(entity)` — filter by entity prefix
- [ ] Implement `to_prompt(entities)` — assert relevant beliefs clean, serialize
- [ ] Build prompt template: `[SYSTEM]` + `[NEW INFORMATION]` + `[RELEVANT BELIEFS]` + `[QUERY]` + `[OUTPUT FORMAT]`
- [ ] Integrate LLM API (OpenAI / local model) — send prompt, receive response
- [ ] End-to-end test with Loan domain: insert → update → resolve → prompt → LLM explains

**Demo:** Full pipeline — structured input → belief store updates → LLM explains the change.

---

### Week 4: Remaining Domains (Employee + Crime Scene)
**Show professor:** Two more domains working end-to-end.

- [ ] Hand-code all **Employee Compliance** rules (R1–R7)
- [ ] Hand-code all **Crime Scene** rules (R1–R7)
- [ ] Create test scenarios for each domain (from domains.md)
- [ ] Run end-to-end pipeline for both domains
- [ ] Fix any edge cases found (missing dependencies, rule ordering issues)

**Demo:** Crime scene scenario — witness credibility changes → alibi broken → suspect status changes → LLM explains the cascade.

---

### Week 5: Thorncrester Domain + Scenario Scripting
**Show professor:** All 4 domains working + scripted multi-turn scenarios.

- [ ] Hand-code all **Thorncrester** rules (R1–R9)
- [ ] Script multi-turn evaluation scenarios for all 4 domains:
  - Belief Update (BU) scenarios — new info contradicts prior conclusion
  - Belief Maintain (BM) scenarios — new info is irrelevant, system should NOT revise
- [ ] Build scenario runner: reads scenario file → replays turns → collects results
- [ ] Verify all scenarios produce expected outcomes

**Demo:** Scripted scenario playback across all domains.

---

### Week 6: Polish + Robustness
**Show professor:** Stable, testable system ready for evaluation.

- [ ] Edge case handling: missing keys, duplicate rules, circular dependencies
- [ ] Improve prompt template based on LLM response quality from weeks 3–5
- [ ] Clean up codebase: docstrings, README, clear module structure
- [ ] Ensure JSON persistence works for all domains
- [ ] Run all scenarios end-to-end, fix any remaining issues
- [ ] Freeze codebase for evaluation phase

**Demo:** Full system walkthrough — all 4 domains, clean code, stable results.

---

## Results & Evaluation Phase (4 Weeks)

### Week 7: Baseline Setup + Data Collection
**Show professor:** Baseline LLM results (no belief store) for comparison.

- [ ] Build baseline pipeline: same prompts, same scenarios, but no belief store — just raw LLM with conversation history
- [ ] Run all BU (Belief Update) scenarios through baseline
- [ ] Run all BM (Belief Maintain) scenarios through baseline
- [ ] Run same scenarios through belief-aware system
- [ ] Collect raw results: LLM responses, belief store states, revision logs
- [ ] Store results in structured format (JSON/CSV) for analysis

---

### Week 8: Metrics + Quantitative Analysis
**Show professor:** Comparison tables + BREU scores.

- [ ] Define scoring criteria:
  - **BU accuracy:** Did the system correctly revise when it should have?
  - **BM accuracy:** Did the system correctly NOT revise when it shouldn't have?
  - **BREU score:** average(BU accuracy, BM accuracy)
  - **Consistency rate:** contradictions remaining after revision
  - **Revision correctness:** % of derived beliefs with correct values after update
- [ ] Score baseline results
- [ ] Score belief-aware results
- [ ] Build comparison tables (per domain + aggregate)
- [ ] Run multiple trials if using stochastic LLM (temperature > 0)

---

### Week 9: Qualitative Analysis + Visualizations
**Show professor:** Charts, example traces, failure analysis.

- [ ] Create visualizations:
  - Bar charts: BREU scores per domain (baseline vs belief-aware)
  - Table: per-scenario pass/fail comparison
  - Dependency chain diagrams for key revision cascades
- [ ] Qualitative analysis of LLM explanations:
  - Does the LLM correctly reference belief keys?
  - Does it explain cascading changes accurately?
  - Where does it fail? (hallucinations, missing references, wrong reasoning)
- [ ] Document failure cases — what went wrong and why
- [ ] Analyze: which domains show the biggest improvement? Why?

---

### Week 10: Write-Up + Final Results
**Show professor:** Draft results chapter + final evaluation summary.

- [ ] Write results section:
  - Quantitative results (tables, BREU scores)
  - Qualitative analysis (LLM explanation quality)
  - Per-domain discussion
  - Failure analysis
- [ ] Write evaluation methodology section (how scenarios were designed, how scoring works)
- [ ] Compare findings to research questions:
  - Does explicit belief tracking improve consistency?
  - What revision patterns does the system handle well/poorly?
  - How does parametric isolation affect results?
- [ ] Limitations and future work section
- [ ] Final review and cleanup

---

## Summary

| Phase | Weeks | Key Deliverable |
|---|---|---|
| BeliefStore core | 1 | Working store with CRUD + dirty propagation |
| Rules engine | 2 | Deterministic derivation + Loan domain |
| LLM integration | 3 | End-to-end pipeline with prompts |
| Employee + Crime | 4 | 3 domains working |
| Thorncrester + scenarios | 5 | All 4 domains + scripted evaluation |
| Polish | 6 | Stable, frozen codebase |
| Baseline + data | 7 | Raw results collected |
| Quantitative analysis | 8 | BREU scores + comparison tables |
| Qualitative analysis | 9 | Charts, traces, failure analysis |
| Write-up | 10 | Draft results chapter |
