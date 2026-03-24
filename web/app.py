"""
Flask backend for the Belief-Aware LLM web UI.

Serves a single-page app and exposes REST endpoints for:
  - Viewing / adding / removing beliefs
  - Querying the LLM via ReasoningEngine
  - Viewing the revision log
  - Resetting the store
"""

from __future__ import annotations

import json
import sys
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add project root to path so belief_store is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain
from belief_store.engine import ReasoningEngine
from belief_store.llm_client import OllamaClient, LLMClient


# ── App setup ────────────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# Global state
store: BeliefStore = BeliefStore()
setup_loan_domain(store)

# Try to connect to Ollama; fall back to a stub if unavailable
try:
    llm: LLMClient = OllamaClient()
except Exception:
    llm = None  # type: ignore

engine: ReasoningEngine = ReasoningEngine(store, llm)  # type: ignore


def _reset_store() -> None:
    """Re-initialise the global store and engine."""
    global store, engine
    store = BeliefStore()
    setup_loan_domain(store)
    engine = ReasoningEngine(store, llm)  # type: ignore


# ── Serve SPA ────────────────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── API: Beliefs ─────────────────────────────────────────────────────


@app.route("/api/beliefs", methods=["GET"])
def get_beliefs():
    """Return all beliefs grouped by entity prefix."""
    grouped: dict[str, list[dict]] = {}
    for key, value in store.beliefs.items():
        entity = key.split(".")[0]
        entry = {
            "key": key,
            "attribute": key.split(".", 1)[1] if "." in key else key,
            "value": value,
            "is_derived": store.is_derived.get(key, False),
            "is_dirty": key in store.dirty,
        }
        grouped.setdefault(entity, []).append(entry)
    return jsonify(grouped)


@app.route("/api/beliefs", methods=["POST"])
def add_belief():
    """Add or update a hypothesis belief."""
    data = request.get_json(force=True)
    key = data.get("key", "").strip()
    raw_value = data.get("value")

    if not key:
        return jsonify({"error": "key is required"}), 400

    # Auto-cast value
    value = _parse_value(raw_value)

    store.add_hypothesis(key, value)
    return jsonify({"ok": True, "key": key, "value": value})


@app.route("/api/beliefs/<path:key>", methods=["DELETE"])
def remove_belief(key: str):
    """Retract a hypothesis belief."""
    store.remove_hypothesis(key)
    return jsonify({"ok": True, "key": key})


# ── API: Query ───────────────────────────────────────────────────────


@app.route("/api/query", methods=["POST"])
def query():
    """Send a question to the ReasoningEngine → LLM."""
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    entities = data.get("entities", ["applicant", "loan"])

    if not question:
        return jsonify({"error": "question is required"}), 400

    if llm is None:
        return jsonify({
            "error": "Ollama is not available. Start it with: ollama serve",
        }), 503

    try:
        response = engine.query(question, entities)
        return jsonify({"response": response})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── API: Revision log ────────────────────────────────────────────────


@app.route("/api/log", methods=["GET"])
def get_log():
    """Return the full revision log."""
    return jsonify(store.revision_log)


# ── API: Reset ───────────────────────────────────────────────────────


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset the store to a fresh state."""
    _reset_store()
    return jsonify({"ok": True})


# ── API: Resolve ─────────────────────────────────────────────────────


@app.route("/api/resolve", methods=["POST"])
def resolve():
    """Manually resolve all dirty beliefs."""
    store.resolve_all_dirty()
    return jsonify({"ok": True})


# ── Helpers ──────────────────────────────────────────────────────────


def _parse_value(raw):
    """Best-effort parse of user-provided string values."""
    if isinstance(raw, (int, float, bool)):
        return raw
    if raw is None:
        return None
    s = str(raw).strip()
    # booleans
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() == "none":
        return None
    # numbers
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass
    return s


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5001)
