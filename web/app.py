"""Flask backend for the Belief-Aware LLM web UI."""

from __future__ import annotations

import sys
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain
from belief_store.engine import ReasoningEngine
from belief_store.llm_client import OllamaClient, LLMClient

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

store: BeliefStore = BeliefStore()
setup_loan_domain(store)

try:
    llm: LLMClient = OllamaClient()
except Exception:
    llm = None  # type: ignore

engine: ReasoningEngine = ReasoningEngine(store, llm)  # type: ignore


def _reset_store() -> None:
    global store, engine
    store = BeliefStore()
    setup_loan_domain(store)
    engine = ReasoningEngine(store, llm)  # type: ignore


# ── Routes ───────────────────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/beliefs", methods=["GET"])
def get_beliefs():
    grouped: dict[str, list[dict]] = {}
    for key, value in store.beliefs.items():
        entity = key.split(".")[0]
        grouped.setdefault(entity, []).append({
            "key": key,
            "attribute": key.split(".", 1)[1] if "." in key else key,
            "value": value,
            "is_derived": store.is_derived.get(key, False),
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


@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json(force=True)
    structured_input = data.get("input", "").strip()
    if not structured_input:
        return jsonify({"error": "input is required"}), 400
    if llm is None:
        return jsonify({"error": "Ollama is not available. Start it with: ollama serve"}), 503
    try:
        response = engine.query(structured_input)
        return jsonify({"response": response})
    except (ValueError, Exception) as exc:
        return jsonify({"error": str(exc)}), 500


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
