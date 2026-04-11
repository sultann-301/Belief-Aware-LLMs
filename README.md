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

## 🏗️ Technical Stack
- **Graph Evaluation / Base Logic:** Pure modular Python, topological sorts handled at query-time via dynamic lambda tracking.
- **LLM Interaction Structure:** Uses local model inference (defaulting to Ollama `gemma3:1b`) natively decoupled from deterministic logic paths to avoid token noise.
- **UI Visualization Components:** Vanilla JS logic paired with native visual edge-drawing, avoiding monolithic frameworks while guaranteeing smooth tracking transitions.
