# Belief-Aware LLMs

An LLM-based system that utilizes belief revision and a deterministic belief graph to drastically improve reasoning. By grounding standard Large Language Models with a strictly evaluated, dependency-driven belief store, the system successfully bridges LLM reasoning gaps handling tasks like complex multi-hop rule traces, counterfactual branching, and negated phrasing.

## 🌟 Core Features

- **Deterministic Belief Store**: A reactive topological graph that manages factual state, derivation rules, and automatic cascading variable updates with rigid determinism.
- **Real-Time Visualizer (Web App)**: A dynamic front-end that allows developers to converse alongside the LLM while immediately observing topological graph updates, logic nodes, and branching edge activations.
- **Automated Evaluator Harness**: A robust, multi-threaded MCQ benchmarking harness running 60+ scenarios isolated by inference hops to analyze LLM reasoning baseline against the store.
- **Intricate Logic Domains**: Ships with specialized domains to tax varying forms of structural logic:
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

Open your browser and navigate to `http://localhost:5000` to select a domain context and begin a conversation.

### 2. Running Automated Evaluations

The built-in evaluation suite contains hundreds of deterministic and carefully mapped multi-hop scenarios. You can run gauntlets on different domains targeting logic tests by running the script:

```bash
# General Domain Usage
python3 evaluation/run_evals.py --domain [domain_name] --runs 10 --workers 4 --model gemma3:1b
```

**Valid Domains:**
The repository ships with base structures (`loan`, `alien_clinic`, `crime_scene`, `thorncrester`) and massive 60-turn logic suites (`loan_extended`, `alien_clinic_extended`, etc.).

If you want to isolate a specific structural issue, target the subsets individually using these suffixes on any domain name:

- `_negation` (e.g. `loan_negation`)
- `_1hop` (e.g. `alien_clinic_1hop`)
- `_2hop`
- `_3hop`
- `_4hop`
- `_belief_maintenance` (e.g. `crime_scene_belief_maintenance`)

### 3. Running Unit Tests

A `pytest` suite is configured to ensure the underlying node graph math triggers perfectly logic pathways independent from LLM injection.

**To run the test suite:**

```bash
pytest tests/
```

---

## 📁 Project Structure

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
├── evaluation/                      # Evaluation harness and test scenarios
│   ├── eval_harness.py              # Main evaluation runner (multi-threaded)
│   ├── eval_orchestrator.py         # Orchestrates test execution and result aggregation
│   ├── eval_metrics.py              # Metrics computation (accuracy, precision, F1)
│   ├── eval_conditions.py           # Test condition definitions
│   ├── eval_common.py               # Shared utilities and constants
│   ├── run_evals.py                 # CLI entry point for evaluations
│   ├── run_batch.py                 # Batch test runner (for scaling)
│   ├── prompting.py                 # Query generation and prompt construction
│   ├── answer_extraction.py         # Extract and normalize answers from LLM output
│   ├── scenarios.py                 # Base scenario definitions
│   ├── hard_scenarios.py            # Adversarial & edge-case scenarios
│   ├── noise_scenarios.py           # Paraphrasing & noisy input scenarios
│   ├── *_scenarios.py               # Domain-specific scenario files:
│       ├── alien_clinic_*_scenarios.py
│       ├── crime_scene_*_scenarios.py
│       ├── loan_*_scenarios.py
│       └── thorncrester_*_scenarios.py
│   ├── batch_state_*.json           # Cached batch execution states
│   ├── eval_results*.csv            # Evaluation results (various runs)
│   └── test_logprobs.py             # Token probability analysis tools
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
│   ├── app.py                       # Flask server (port 5000)
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
- Scenarios are grouped by domain and complexity (base, extended, paraphrased, with noise).
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
