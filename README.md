# Belief-Aware LLMs

An LLM-based system that utilizes belief revision and a deterministic belief graph to improve reasoning. By grounding standard Large Language Models with a strictly evaluated, dependency-driven belief store, the system successfully bridges LLM reasoning gaps handling tasks like complex multi-hop rule traces, counterfactual branching, and negated phrasing.

## 🌟 Core Features

- **Deterministic Belief Store**: A reactive topological graph that manages factual state, derivation rules, and automatic cascading variable updates with rigid determinism.
See [Implementation.md](Implementation.md) for the core mechanics of the belief store.
- **Real-Time Visualizer (Web App)**: A dynamic front-end that allows developers to converse alongside the LLM while immediately observing topological graph updates, logic nodes, and branching edge activations.
- **Automated Evaluator Harness**: A robust, multi-threaded MCQ benchmarking harness running 60+ scenarios isolated by inference hops to analyze LLM reasoning baseline against the store. See [METRICS.md](METRICS.md) for evaluation metrics definitions.
- **Intricate Logic Domains**: Ships with specialized domains to tax varying forms of structural logic (see [domains.md](domains.md) for detailed logic reference):
  - 🏠 **Loan Application**: Tests sequential hierarchies, multi-tiered prerequisites, and financial status routing.
  - 👽 **Alien Clinic**: Tests multivariate symptom combinations, variable phasing structures, and compound hazard exclusions.
  - 🔍 **Crime Scene**: Tests evidence chains, interlocking suspect alibis, and transitive motive verification.
  - 🦅 **Thorncrester Taxonomy**: Tests deep phenotypic cascades and cyclic ecological development derivations.

---

## 🚀 Getting Started

### 1. Interactive Visualizer Web App

The simplest way to understand the system is to run the visual dashboard, where conversations push state changes into the visual map.

**To run the system locally:**

```bash
python3 web/app.py
```

Open your browser and navigate to `http://localhost:5001` to select a domain context and begin a conversation.

### 2. Running Automated Evaluations

The built-in evaluation suite contains deterministic, carefully mapped multi-hop scenario sets plus paraphrased variants. Paraphrase selection is intentionally random during evaluation to sample a broader answer distribution.

For a single evaluation run, use `evaluation/run_evals.py`:

```bash
# General Domain Usage
python3 evaluation/run_evals.py \
  --domain loan_belief_maintenance \
  --runs 10 \
  --workers 4 \
  --model gemma3:1b \
  --eval-prompt-version v15 \
  --baseline-prompt-version v1
```

For thesis-style batches, use the config-driven runner:

```bash
# Inspect the planned standard batch without running models
python3 evaluation/run_batch.py \
  --config evaluation/configs/thesis_standard_batch.json \
  --dry-run

# Inspect the planned dual-agent batch without running models
python3 evaluation/run_batch.py \
  --config evaluation/configs/thesis_dual_agent_batch.json \
  --dry-run
```

`run_batch.py` validates its JSON config before launching model calls. Batch configs define the mode, domains, models, model pairs, prompt versions, run counts, worker count, Ollama options, cache settings, result CSV path, and debug-log behavior.

By default, evaluation results are appended to `eval_results.csv`, `eval_results_with_store.csv`, or `eval_results_dual_agent.csv` depending on mode. Use `--csv-out` to route a run somewhere else, and use `--log-dir` or `--no-debug-logs` to redirect or disable failed-extraction and incorrect-answer logs:

```bash
python3 evaluation/run_evals.py \
  --domain loan \
  --runs 1 \
  --model gemma3:1b \
  --csv-out /tmp/belief-aware-smoke.csv \
  --no-debug-logs
```

**Valid domains and scenario subsets:**
The repository ships with base structures (`loan`, `alien_clinic`, `crime_scene`, `thorncrester`) and larger logic suites (`loan_extended`, `alien_clinic_extended`, etc.).

If you want to isolate a specific structural issue, target the subsets individually using these suffixes on any domain name:

- `_negation` (e.g. `loan_negation`)
- `_1hop` (e.g. `alien_clinic_1hop`)
- `_2hop`
- `_3hop`
- `_4hop`
- `_belief_maintenance` (e.g. `crime_scene_belief_maintenance`)
- `_hard`
- `_absurd`
- `_absurd_temporal`
- `_absurd_temporal_noise`
- `_belief_awareness`
- `_grounding`

### Graph-retrieval baseline for the paper

This command runs only graph retrieval + LLM and saves new baseline results for
comparison with your existing plain-LLM and belief-store results. It retrieves
rules and current input facts using the benchmark's supplied target attributes,
then lets the LLM calculate the answer. It uses no assistant chat history.
This is custom dependency-graph RAG, not Microsoft's GraphRAG implementation.

```bash
# Validate the full paper batch without calling models
python3 -m evaluation.graphrag.run_batch --dry-run

# Run the paper batch (graph baseline only)
python3 -m evaluation.graphrag.run_batch

# Inspect retrieved rules and facts for one scenario set
python3 -m evaluation.graphrag.run_evals --domain loan_absurd --dry-run

# Run one model and scenario set as a small smoke test
python3 -m evaluation.graphrag.run_evals \
  --domain loan_absurd --model qwen3:4b --runs 1 \
  --csv-out graphrag_smoke.csv
```

The [paper config](evaluation/configs/thesis_graphrag_batch.json) uses the original
five models, replacing the removed modified Qwen with `qwen3:4b`. Requests explicitly
set `think=false` using [Ollama's thinking control](https://docs.ollama.com/capabilities/thinking).
Only belief maintenance, absurd, absurd temporal, and grounding are run, across
loan, alien clinic, crime scene, and Thorncrester. The original settings are
retained: 10 runs, temperature 0.0, 4 workers, 768 output tokens, and 8162 context
tokens. This is 8,000 model calls. Response caching is disabled.

The batch samples paraphrases using the existing selector, saves the exact turns
to `eval_results_graphrag.manifest.json`, and shares that selection across models.
The scenario seed controls question selection, not model generation. A single-set
smoke test uses canonical questions. The CSV records the policy and generation
settings so comparisons with existing results can account for these differences.

Use `--config` for an alternate batch config and `--csv-out` for a fresh output
path. Completed runs are flushed to CSV as they finish. Once a stopped batch's
process has exited, resume with:

```bash
# Inspect saved progress without making model calls or modifying results
python3 -m evaluation.graphrag.run_batch --resume --dry-run

# Skip completed runs and continue using the exact saved questions/settings
python3 -m evaluation.graphrag.run_batch --resume
```

Include the original `--csv-out` path if you used a custom one. Resume uses the
saved manifest, validates prior rows, and skips complete 10-question runs.
An unfinished run repeats. If interruption left partial rows, the runner backs
up the original CSV before retaining only complete runs. Resuming a finished
batch makes no model calls. New runners lock their output to prevent concurrent
writers. The original pre-resume runner has no lock: **it must exit before you
resume; suspending it with Ctrl+Z is not enough**. Ctrl+C in a running batch may
wait for active workers; wait for the terminal prompt before restarting.

For a temporary terminal suspension use Ctrl+Z, then `fg` in that same terminal
to continue. This only suspends Python, not Ollama requests already in progress,
and does not survive a terminal closure or reboot. See
[the baseline plan](GRAPHRAG_BASELINE_PLAN.md) for the protocol.

### 3. Running Unit Tests

A `pytest` suite is configured to ensure the underlying node graph math triggers perfectly logic pathways independent from LLM injection.

**To run the test suite:**

```bash
pytest -q
```

---

## 📁 Project Structure

For detailed information on domain logic, see [domains.md](domains.md). For evaluation metrics, see [METRICS.md](METRICS.md).
The CSV inputs used by the reporting notebooks are included in the repository: `eval_results.csv`, `eval_results_normalized.csv`, `eval_results_with_store.csv`, `eval_results_dual_agent.csv`, and `eval_results_graphrag.csv` at the project root. The provenance checks also reference `eval_results_dual_agent.legacy.csv`, `eval_results_dual_agent_normalized.csv`, and the empty `evaluation/eval_results_with_store.csv`; these are included unchanged. **Hard scenarios are excluded from the reported benchmark.** Reporting uses the 16 combinations of loan, alien_clinic, crime_scene and thorncrester with belief_maintenance, absurd, absurd_temporal and grounding. The evaluation harness still supports other scenarios; raw CSVs are preserved.

Run `python3 scripts/execute_analysis_notebooks.py`, then `python3 -m tests.test_non_hard_reporting`. The runner executes `graphrag_single_agent_comparison.ipynb` first, followed by the four historical analysis views, without model calls. CSV tables, metric coverage, definitions and source hashes are in [output/non_hard](output/non_hard/). PNG/SVG charts are generated there locally and ignored by Git. See the [reporting report](output/non_hard/REPORT.md) for before/after values and limitations. Original notebooks are preserved in [backups/before_non_hard_standardization_2026-10-07](backups/before_non_hard_standardization_2026-10-07/).

Accuracy averages With Store v15/v16 and No Store v1/v2 equally within each combination, then averages the 16 combinations equally. Other metrics name their prompt versions and support counts. Historical Qwen is `hoangquan456/qwen3-nothink:4b`; GraphRAG uses `qwen3:4b` with thinking disabled. Matching scenario coverage does not make the experiments identical.

```
Belief-Aware-LLMs/
├── belief_store/                    # Core belief store engine
│   ├── __init__.py
│   ├── engine.py                    # Orchestrator (parse input, inject beliefs, resolve, build prompts)
│   ├── store.py                     # Reactive topological graph with derivation rules
│   ├── llm_client.py                # LLM interaction wrapper (Ollama)
│   ├── prompts.py                   # System prompts (v1-v16, dual-agent variants)
│   ├── answer_validation.py         # MCQ answer grading and validation
│   ├── belief_lookup.py             # Relevant belief extraction utilities
│   ├── text_utils.py                # Text processing and normalization
│   └── domains/                     # Domain implementations
│       ├── loan.py                  # Loan application logic (credit, debt, status)
│       ├── alien_clinic.py          # Alien clinic triage (symptoms, organism types)
│       ├── crime_scene.py           # Crime scene investigation (suspects, alibis)
│       └── thorncrester.py          # Ecological taxonomy (species, phenotypes)
│
├── evaluation/                      # Evaluation harness and scenario sets
│   ├── eval_harness.py              # Main evaluation runner (multi-threaded)
│   ├── eval_orchestrator.py         # Orchestrates test execution and result aggregation
│   ├── eval_metrics.py              # Metrics computation (accuracy, precision, F1)
│   ├── eval_conditions.py           # Test condition definitions
│   ├── eval_common.py               # Shared utilities and constants
│   ├── run_evals.py                 # CLI entry point for evaluations
│   ├── run_batch.py                 # Config-driven batch runner
│   ├── prompting.py                 # Query generation and prompt construction
│   ├── answer_extraction.py         # Extract and normalize answers from LLM output
│   ├── configs/                     # Reusable batch-evaluation JSON configs
│   │   ├── thesis_standard_batch.json
│   │   └── thesis_dual_agent_batch.json
│   ├── scenario_sets/               # Scenario data grouped by type and domain
│   │   ├── base.py                  # Base domain rules, initial beliefs, basic turns
│   │   ├── belief_awareness.py      # Absurd, grounding, and trace-selection scenarios
│   │   ├── hard.py                  # Adversarial & edge-case scenarios
│   │   ├── noise.py                 # Noise-augmented scenario variants
│   │   ├── extended/                # Negation, hop-depth, and maintenance scenarios
│   │   ├── paraphrased/             # Generated paraphrase variants
│   │   └── paraphrased_noise/       # Generated noisy paraphrase variants
│   ├── *_scenarios.py               # Compatibility shims for legacy imports
│   ├── eval_results*.csv            # Evaluation results (various runs)
│
├── tests/                           # Unit test suite (pytest)
│   ├── __init__.py
│   ├── test_engine.py               # Belief store graph evaluation tests
│   ├── test_store.py                # Store mutations and state tests
│   ├── test_alien_clinic.py         # Alien clinic domain tests
│   ├── test_crime_scene.py          # Crime scene domain tests
│   ├── test_loan_domain.py          # Loan domain tests
│   ├── test_thorncrester.py         # Thorncrester domain tests
│   └── test_dual_agent.py           # Dual-agent reasoner/matcher tests
│
├── web/                             # Interactive visualization web app
│   ├── app.py                       # Flask server (port 5001)
│   └── static/
│       ├── index.html               # Main UI page
│       ├── style.css                # Styling
│       └── app.js                   # Client-side graph rendering & logic
│
├── scripts/                         # Utility scripts
│   ├── normalize_eval_csvs.py       # CSV normalization and aggregation
│   └── paraphrase_scenarios.py      # Generate paraphrased test variants
│
├── Root configuration files
│   ├── README.md                    # This file
│   ├── pyrightconfig.json           # Pyright type checking configuration
│   ├── domains.md                   # Domain logic reference documentation
│   ├── Implementation.md            # Implementation notes
│   ├── METRICS.md                   # Evaluation metrics definitions
│   ├── LICENSE                      # License file
│
├── Notebooks (Jupyter)
│   ├── final_single_agent_analysis.ipynb  # Analysis of single-agent performance
│   ├── final_dual_agent_analysis.ipynb    # Analysis of dual-agent performance
│   ├── eval_results_analysis.ipynb        # Results visualization & exploration
│   └── dual_agent_analysis.ipynb          # Dual-agent variant comparisons
│
└── eval/ (directory)                # Additional evaluation outputs
```

### Key Components Explained

**belief_store/** — Core deterministic belief engine

- `engine.py`: Orchestrator that parses structured input, injects/retracts beliefs, resolves dirty facts, and constructs prompts for LLM queries. Routes between entity-level and attribute-level (HopWalker) paths.
- `store.py`: Reactive topological graph managing beliefs with deterministic derivation rules. Uses lazy retraction (tombstones), O(edges) dirty propagation via reverse-adjacency maps, post-order DFS resolution, and HopWalker for backward dependency traversal with evidence annotations.
- `prompts.py`: 16 versions of system prompts (single-agent) plus dual-agent reasoner/matcher variants for grounded reasoning.
- `domains/`: Four specialized logic domains, each with distinct rule complexities (hierarchical, multivariate, chained, cascading).

**evaluation/** — Test framework

- `eval_harness.py`: Multi-threaded runner orchestrating scenario execution.
- `run_evals.py`: Runs one domain/scenario subset and writes summary metrics to CSV.
- `run_batch.py`: Runs validated JSON batch configs for standard, dual-agent, or sequential experiments.
- `configs/`: Reusable experiment configurations, including thesis standard and dual-agent batches.
- `scenario_sets/`: Scenario data grouped by type and domain. Legacy `*_scenarios.py` modules remain as compatibility shims, but new imports should target `evaluation.scenario_sets...`.
- Results stored in CSV format for aggregation and analysis.

**tests/** — Unit testing

- Each domain and major component has dedicated tests ensuring logic correctness independent of LLM variance.

**web/** — Visualization dashboard

- Flask server hosting a real-time graph visualizer.
- Users converse with the LLM while observing live belief store updates and topological graph changes.

**scripts/** — Automation utilities

- Normalize and merge evaluation CSV results across runs.
- Generate paraphrased test variants for robustness testing.

---

## 🏗️ Technical Stack

- **Graph Evaluation / Base Logic:** Pure modular Python, topological sorts handled at query-time via dynamic lambda tracking.
- **LLM Interaction Structure:** Uses local model inference (defaulting to Ollama `gemma3:1b`) natively decoupled from deterministic logic paths to avoid token noise.
- **UI Visualization Components:** Vanilla JS logic paired with native visual edge-drawing, avoiding monolithic frameworks while guaranteeing smooth tracking transitions.
