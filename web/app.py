"""Flask backend for the Belief-Aware LLM web UI."""

from __future__ import annotations

import sys
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain
from belief_store.domains.alien_clinic import setup_alien_clinic_domain
from belief_store.domains.crime_scene import setup_crime_scene_domain
from belief_store.domains.thorncrester import setup_thorncrester_domain
from belief_store.engine import ReasoningEngine, SYSTEM_PROMPT
from belief_store.llm_client import OllamaClient, LLMClient

from evaluation.scenarios import (
    LOAN_RULES, LOAN_INITIAL_BELIEFS, LOAN_TURNS,
    ALIEN_RULES, ALIEN_INITIAL_BELIEFS, ALIEN_TURNS_BASIC,
    CRIME_RULES, CRIME_INITIAL_BELIEFS, CRIME_TURNS,
    THORNCRESTER_RULES, THORNCRESTER_INITIAL_BELIEFS, THORNCRESTER_TURNS,
)
from evaluation.eval_harness import (
    DomainConfig, EVAL_SYSTEM_PROMPT, BASELINE_SYSTEM_PROMPT,
    extract_answer, _get_entities, _format_question, _build_prompt,
    _build_baseline_prompt,
)

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# ── Chat-specific prompts (no MCQ instructions) ─────────────────────

BASELINE_CHAT_SYSTEM_PROMPT = """\
You are a reasoning assistant. You reason over a set of rules and fact updates.
You do NOT have access to a belief store — you must track all facts yourself.

Rules:
- Carefully apply the rules below to the facts you have been given.
- When a fact is updated, re-derive any conclusions that depend on it.
- Reference specific rule numbers and fact keys in your reasoning.

Output format:
REASONING: <step-by-step explanation>
ANSWER: <direct answer to the query>
"""

# ── Domain registry ──────────────────────────────────────────────────

DOMAIN_REGISTRY = {
    "loan": {
        "label": "Loan Eligibility",
        "setup_fn": setup_loan_domain,
        "initial_beliefs": LOAN_INITIAL_BELIEFS,
        "turns": LOAN_TURNS,
        "baseline_rules": LOAN_RULES,
        "default_entities": "applicant, loan",
    },
    "alien_clinic": {
        "label": "Alien Clinic",
        "setup_fn": setup_alien_clinic_domain,
        "initial_beliefs": ALIEN_INITIAL_BELIEFS,
        "turns": ALIEN_TURNS_BASIC,
        "baseline_rules": ALIEN_RULES,
        "default_entities": "patient, atmosphere, zyxostin, filinan, snevox, treatment, medical, clinic",
    },
    "crime_scene": {
        "label": "Crime Scene",
        "setup_fn": setup_crime_scene_domain,
        "initial_beliefs": CRIME_INITIAL_BELIEFS,
        "turns": CRIME_TURNS,
        "baseline_rules": CRIME_RULES,
        "default_entities": "case, suspect_a, suspect_b, officer_smith",
    },
    "thorncrester": {
        "label": "Thorncrester",
        "setup_fn": setup_thorncrester_domain,
        "initial_beliefs": THORNCRESTER_INITIAL_BELIEFS,
        "turns": THORNCRESTER_TURNS,
        "baseline_rules": THORNCRESTER_RULES,
        "default_entities": "environment, adult_thorncrester, thorncrester_flock, juvenile_thorncrester, feather_mite",
    },
}

try:
    llm: LLMClient = OllamaClient()
except Exception:
    llm = None  # type: ignore


def _reset_store(domain_key: str | None = None) -> None:
    global store, engine, current_domain_key, chat_messages
    if domain_key:
        current_domain_key = domain_key
    store = BeliefStore()
    cfg = DOMAIN_REGISTRY[current_domain_key]
    cfg["setup_fn"](store)
    # Seed initial beliefs to prevent KeyError during resolution
    for k, v in cfg["initial_beliefs"].items():
        store.add_hypothesis(k, v)
    engine = ReasoningEngine(store, llm)  # type: ignore
    # Reset chat history on domain switch / store reset
    chat_messages = []


# ── Global state ─────────────────────────────────────────────────────

current_domain_key = "loan"
store: BeliefStore = BeliefStore()
chat_messages: list[dict] = []   # for store_history / baseline chat
_reset_store(current_domain_key)

# Simulation state
sim_state: dict = {
    "domain": None,
    "condition": None,
    "turn_index": 0,
    "store": None,
    "messages": [],
    "results": [],
}

# ── Routes ───────────────────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/models", methods=["GET"])
def get_models():
    """List available Ollama models."""
    try:
        if llm and hasattr(llm, "_client"):
            # Use the existing client if possible
            models_info = llm._client.list()
        else:
            import ollama
            models_info = ollama.list()
        
        # Accessing models based on the ollama python library structure
        models = [m.model for m in models_info.models]
        return jsonify({"models": models})
    except Exception as exc:
        return jsonify({"models": ["qwen3:4b", "gemma3:1b"], "error": str(exc)})


# ── Domain management ────────────────────────────────────────────────


@app.route("/api/domains", methods=["GET"])
def get_domains():
    result = {}
    for key, cfg in DOMAIN_REGISTRY.items():
        result[key] = {
            "label": cfg["label"],
            "entities": [e.strip() for e in cfg["default_entities"].split(",")],
            "num_turns": len(cfg["turns"]),
        }
    return jsonify({"domains": result, "current": current_domain_key})


@app.route("/api/domain", methods=["POST"])
def set_domain():
    data = request.get_json(force=True)
    domain_key = data.get("domain", "").strip()
    if domain_key not in DOMAIN_REGISTRY:
        return jsonify({"error": f"Unknown domain: {domain_key}"}), 400
    _reset_store(domain_key)
    return jsonify({"ok": True, "domain": domain_key})


# ── Beliefs ──────────────────────────────────────────────────────────


@app.route("/api/beliefs", methods=["GET"])
def get_beliefs():
    grouped: dict[str, list[dict]] = {}
    for key, (value, is_derived) in store.beliefs.items():
        if key in store.removed:
            continue
        entity = key.split(".")[0]
        grouped.setdefault(entity, []).append({
            "key": key,
            "attribute": key.split(".", 1)[1] if "." in key else key,
            "value": value,
            "is_derived": is_derived,
            "is_dirty": key in store.dirty,
        })
    return jsonify(grouped)


@app.route("/api/beliefs", methods=["POST"])
def add_belief():
    data = request.get_json(force=True)
    key = data.get("key", "").strip()
    raw_value = data.get("value")
    if not key:
        return jsonify({"error": "key is required"}), 400
    value = _parse_value(raw_value)
    store.add_hypothesis(key, value)
    return jsonify({"ok": True, "key": key, "value": value})


@app.route("/api/beliefs/<path:key>", methods=["DELETE"])
def remove_belief(key: str):
    store.remove_hypothesis(key)
    return jsonify({"ok": True, "key": key})


# ── Dependency graph ─────────────────────────────────────────────────


@app.route("/api/graph", methods=["GET"])
def get_graph():
    """Return the dependency graph as nodes + edges for visualization."""
    nodes = []
    edges = []
    seen_keys = set()

    # Add all belief keys as nodes
    for key, (value, is_derived) in store.beliefs.items():
        if key in store.removed:
            continue
        seen_keys.add(key)
        nodes.append({
            "id": key,
            "entity": store.entity_of(key),
            "value": value,
            "is_derived": is_derived,
            "is_dirty": key in store.dirty,
        })

    # Add rule output keys that may not have values yet
    for output_key, rule in store.rule_index.items():
        if output_key not in seen_keys:
            nodes.append({
                "id": output_key,
                "entity": store.entity_of(output_key),
                "value": None,
                "is_derived": True,
                "is_dirty": output_key in store.dirty,
            })
            seen_keys.add(output_key)

        # Add input keys that aren't in beliefs yet
        for inp in rule["inputs"]:
            if inp not in seen_keys:
                nodes.append({
                    "id": inp,
                    "entity": store.entity_of(inp),
                    "value": None,
                    "is_derived": False,
                    "is_dirty": inp in store.dirty,
                })
                seen_keys.add(inp)

    # Build edges from rule dependencies
    for output_key, inputs in store.dependencies.items():
        for inp in inputs:
            edges.append({"source": inp, "target": output_key})

    return jsonify({"nodes": nodes, "edges": edges})


# ── Query (chat) ─────────────────────────────────────────────────────


@app.route("/api/query", methods=["POST"])
def query():
    global chat_messages
    data = request.get_json(force=True)
    structured_input = data.get("input", "").strip()
    condition = data.get("condition", "store")  # store, store_history, baseline
    model = data.get("model")  # optional override
    prompt_version = data.get("prompt_version", "v1")  # v1 or v2
    if not structured_input:
        return jsonify({"error": "input is required"}), 400
    if llm is None:
        return jsonify({"error": "Ollama is not available. Start it with: ollama serve"}), 503
    try:
        if condition == "baseline":
            # Baseline: no belief injection, rules always prepended, no MCQ
            cfg = DOMAIN_REGISTRY[current_domain_key]
            prompt = cfg["baseline_rules"] + "\n\n" + structured_input
            if not chat_messages:
                chat_messages = [{"role": "system", "content": BASELINE_CHAT_SYSTEM_PROMPT}]
            chat_messages.append({"role": "user", "content": prompt})
            response = llm.generate_with_history(chat_messages, model=model)
            chat_messages.append({"role": "assistant", "content": response})

        elif condition == "store_history":
            # Store + History: belief-aware + conversation memory
            sys_prompt, user_prompt = engine.build_prompt(structured_input, prompt_version)
            if not chat_messages:
                chat_messages = [{"role": "system", "content": sys_prompt}]
            chat_messages.append({"role": "user", "content": user_prompt})
            response = llm.generate_with_history(chat_messages, model=model)
            chat_messages.append({"role": "assistant", "content": response})

        else:
            # Store (stateless): normal belief-aware query, no history
            chat_messages = []  # reset history when switching to stateless
            response = engine.query(structured_input, model=model, prompt_version=prompt_version)

        return jsonify({"response": response})
    except (ValueError, Exception) as exc:
        return jsonify({"error": str(exc)}), 500


# ── Simulation ───────────────────────────────────────────────────────


@app.route("/api/simulate/start", methods=["POST"])
def simulate_start():
    """Initialize a simulation for a domain + condition."""
    data = request.get_json(force=True)
    domain_key = data.get("domain", "loan")
    condition = data.get("condition", "store")  # store, store_history, baseline
    model = data.get("model")

    if domain_key not in DOMAIN_REGISTRY:
        return jsonify({"error": f"Unknown domain: {domain_key}"}), 400

    cfg = DOMAIN_REGISTRY[domain_key]

    sim_state["domain"] = domain_key
    sim_state["condition"] = condition
    sim_state["model"] = model
    sim_state["turn_index"] = 0
    sim_state["results"] = []

    # Set up the persistent store for store_history condition
    sim_store = BeliefStore()
    cfg["setup_fn"](sim_store)
    for k, v in cfg["initial_beliefs"].items():
        sim_store.add_hypothesis(k, v)
    sim_state["store"] = sim_store

    # Set up message history for history / baseline conditions
    if condition == "store_history":
        sim_state["messages"] = [{"role": "system", "content": EVAL_SYSTEM_PROMPT}]
    elif condition == "baseline":
        sim_state["messages"] = [{"role": "system", "content": BASELINE_SYSTEM_PROMPT}]
    else:
        sim_state["messages"] = []

    return jsonify({
        "ok": True,
        "domain": domain_key,
        "condition": condition,
        "total_turns": len(cfg["turns"]),
    })


@app.route("/api/simulate/step", methods=["POST"])
def simulate_step():
    """Execute one turn of the simulation."""
    if sim_state["domain"] is None:
        return jsonify({"error": "No simulation started. Call /api/simulate/start first."}), 400

    domain_key = sim_state["domain"]
    condition = sim_state["condition"]
    turn_idx = sim_state["turn_index"]
    cfg = DOMAIN_REGISTRY[domain_key]
    turns = cfg["turns"]

    if turn_idx >= len(turns):
        return jsonify({"error": "Simulation complete. No more turns.", "done": True}), 200

    turn = turns[turn_idx]
    initial_lines = [f"{k} = {v}" for k, v in cfg["initial_beliefs"].items()]
    entities = _get_entities(turn, cfg["default_entities"])

    llm_answer = None
    llm_response = ""
    correct = turn["correct"]
    hit = False
    beliefs_snapshot = {}

    if llm is None:
        llm_response = "(Ollama not available — showing belief state only)"
    else:
        try:
            if condition == "store":
                # Stateless per-turn rebuild
                turn_store = BeliefStore()
                cfg["setup_fn"](turn_store)
                for k, v in cfg["initial_beliefs"].items():
                    turn_store.add_hypothesis(k, v)
                for prev_idx in range(turn_idx):
                    prev = turns[prev_idx]
                    if prev["beliefs"]:
                        for k, v in prev["beliefs"].items():
                            turn_store.add_hypothesis(k, v)
                turn_store.resolve_all_dirty()
                
                # Now track updates for CURRENT turn
                log_start_idx = len(turn_store.revision_log)
                if turn["beliefs"]:
                    for k, v in turn["beliefs"].items():
                        turn_store.add_hypothesis(k, v)
                turn_store.resolve_dirty(entities)
                
                updated_keys = list({entry["key"] for entry in turn_store.revision_log[log_start_idx:]})
                beliefs_text, _ = turn_store.to_prompt(entities)
                new_lines = initial_lines if turn_idx == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
                prompt = _build_prompt(entities, new_lines, beliefs_text, turn)
                llm_response = llm.generate(EVAL_SYSTEM_PROMPT, prompt, model=sim_state.get("model"))

                # Snapshot beliefs
                for key, (value, is_derived) in turn_store.beliefs.items():
                    if key not in turn_store.removed:
                        beliefs_snapshot[key] = {"value": value, "is_derived": is_derived}

            elif condition == "store_history":
                sim_store = sim_state["store"]
                log_start_idx = len(sim_store.revision_log)
                if turn["beliefs"]:
                    for k, v in turn["beliefs"].items():
                        sim_store.add_hypothesis(k, v)
                sim_store.resolve_dirty(entities)
                updated_keys = list({entry["key"] for entry in sim_store.revision_log[log_start_idx:]})
                
                beliefs_text, _ = sim_store.to_prompt(entities)
                new_lines = initial_lines if turn_idx == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
                prompt = _build_prompt(entities, new_lines, beliefs_text, turn)
                sim_state["messages"].append({"role": "user", "content": prompt})
                llm_response = llm.generate_with_history(sim_state["messages"], model=sim_state.get("model"))
                sim_state["messages"].append({"role": "assistant", "content": llm_response})

                for key, (value, is_derived) in sim_store.beliefs.items():
                    if key not in sim_store.removed:
                        beliefs_snapshot[key] = {"value": value, "is_derived": is_derived}

            elif condition == "baseline":
                updated_keys = []
                new_lines = initial_lines if turn_idx == 0 else [f"{k} = {v}" for k, v in (turn["beliefs"] or {}).items()]
                prompt = _build_baseline_prompt(cfg["baseline_rules"], new_lines, turn)
                sim_state["messages"].append({"role": "user", "content": prompt})
                llm_response = llm.generate_with_history(sim_state["messages"], model=sim_state.get("model"))
                sim_state["messages"].append({"role": "assistant", "content": llm_response})

            llm_answer = extract_answer(llm_response)
            hit = llm_answer == correct
        except Exception as exc:
            llm_response = f"Error: {exc}"

    result = {
        "turn": turn_idx + 1,
        "total": len(turns),
        "question": turn["question"],
        "options": turn["options"],
        "injected_beliefs": turn["beliefs"],
        "correct": correct,
        "llm_answer": llm_answer,
        "hit": hit,
        "llm_response": llm_response,
        "beliefs_snapshot": beliefs_snapshot,
        "updated_keys": updated_keys,
        "done": turn_idx + 1 >= len(turns),
    }

    sim_state["results"].append(result)
    sim_state["turn_index"] += 1
    return jsonify(result)


# ── Utility endpoints ────────────────────────────────────────────────


@app.route("/api/log", methods=["GET"])
def get_log():
    return jsonify(store.revision_log)


@app.route("/api/reset", methods=["POST"])
def reset():
    _reset_store()
    return jsonify({"ok": True})


@app.route("/api/resolve", methods=["POST"])
def resolve():
    store.resolve_all_dirty()
    return jsonify({"ok": True})


def _parse_value(raw):
    """Best-effort parse of user-provided string values."""
    if isinstance(raw, (int, float, bool)):
        return raw
    if raw is None:
        return None
    s = str(raw).strip()
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() == "none":
        return None
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return s


if __name__ == "__main__":
    app.run(debug=True, port=5001)
