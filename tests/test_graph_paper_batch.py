"""Validate the paper matrix, cross-domain retrieval and Ollama thinking flag."""

import csv
import json
from types import SimpleNamespace

import pytest

from belief_store.llm_client import OllamaClient
from belief_store.store import BeliefStore
from evaluation.graphrag import run_batch
from evaluation.graphrag.condition import CONDITION, retrieve_slices
from evaluation.graphrag.run_evals import DOMAINS
from evaluation.run_evals import DOMAIN_REGISTRY


def test_paper_matrix_matches_original_models_except_qwen():
    config = run_batch.load_config(run_batch.DEFAULT_CONFIG)
    original = json.loads((run_batch.DEFAULT_CONFIG.parent / "thesis_standard_batch.json").read_text())
    assert config["models"] == ["qwen3:4b" if "qwen3-nothink" in name else name for name in original["models"]]
    assert set(config["domains"]) == set(DOMAINS)
    assert len(config["domains"]) == 16
    assert config["runs_per_config"] == original["runs_per_config"] == 10
    assert config["temperature"] == original["temperatures"][0] == 0.0
    assert config["workers"] == original["workers"]
    assert config["think"] is False
    for key in ("num_predict", "num_ctx", "keep_alive"):
        assert config["ollama"][key] == original["ollama"][key]


def test_every_sampled_paper_context_builds_without_rule_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Retrieval executed a derivation")

    original = BeliefStore.add_rule

    def register(self, *args, **kwargs):
        kwargs["derive_fn"] = forbidden
        return original(self, *args, **kwargs)

    monkeypatch.setattr(BeliefStore, "add_rule", register)
    monkeypatch.setattr(BeliefStore, "resolve_dirty_for_attributes", forbidden)
    monkeypatch.setattr(BeliefStore, "resolve_dirty", forbidden)
    config = run_batch.load_config(run_batch.DEFAULT_CONFIG)
    prepared = run_batch.prepare_runs(config)
    assert len(prepared) == 160
    assert sum(len(current.turns) for _, current in prepared) == 1600
    repeated = run_batch.prepare_runs(config)
    assert [current.turns for _, current in prepared] == [current.turns for _, current in repeated]


def test_explicit_prescription_assertion_is_retrieved_as_input():
    config = DOMAIN_REGISTRY["alien_clinic_absurd_temporal"]
    slices = retrieve_slices(config)
    # Turn 6 explicitly supplies snevox; it is not computed by this retriever.
    assert slices[5].facts["treatment.active_prescription"] == "snevox"
    assert "treatment.active_prescription" not in {rule.output for rule in slices[5].rules}
    assert "medical.staff_requirement" in {rule.output for rule in slices[5].rules}


def test_qwen_request_disables_thinking_at_api_level(monkeypatch):
    requests = []

    class Backend:
        def __init__(self, **kwargs):
            pass

        def chat(self, **kwargs):
            requests.append(kwargs)
            return SimpleNamespace(message=SimpleNamespace(content="ANSWER: [test]"), logprobs=None)

    monkeypatch.setattr("belief_store.llm_client._ollama.Client", Backend)
    client = OllamaClient(model="qwen3:4b", think=False)
    client.generate_with_history_and_logprobs([{"role": "user", "content": "test"}])
    assert requests[0]["model"] == "qwen3:4b"
    assert requests[0]["think"] is False


def test_batch_only_generates_graph_rows_and_preserves_manifest(tmp_path, monkeypatch, capsys):
    from evaluation import eval_conditions

    def forbidden(*args, **kwargs):
        raise AssertionError("Existing baseline was rerun")

    monkeypatch.setattr(eval_conditions, "run_with_store", forbidden)
    monkeypatch.setattr(eval_conditions, "run_without_store", forbidden)
    config = run_batch.load_config(run_batch.DEFAULT_CONFIG)
    config.update(models=["qwen3:4b", "gemma3:1b"], domains=["loan_grounding"], runs_per_config=2)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    out = tmp_path / "results.csv"
    monkeypatch.setattr(run_batch, "OllamaClient", forbidden)
    run_batch.main(["--config", str(path), "--dry-run", "--csv-out", str(out)])
    assert "40 model calls" in capsys.readouterr().out
    assert not out.exists()
    calls = []

    class FakeLLM:
        def __init__(self, **kwargs):
            assert kwargs["think"] is False
            assert kwargs["cache_enabled"] is False
            self.model = kwargs["model"]

        def generate_with_history_and_logprobs(self, messages):
            calls.append((self.model, messages))
            return "ANSWER: [test]", None

    monkeypatch.setattr(run_batch, "OllamaClient", FakeLLM)
    run_batch.main(["--config", str(path), "--csv-out", str(out)])
    with out.open() as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == len(calls) == 40
    assert {row["condition"] for row in rows} == {CONDITION}
    assert {row["model"] for row in rows} == set(config["models"])
    assert all(row["think"] == "False" for row in rows)
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    assert len(manifest["runs"]) == 2
    for run in ("1", "2"):
        first = sorted((row["turn"], row["question"]) for row in rows if row["run"] == run and row["model"] == "qwen3:4b")
        second = sorted((row["turn"], row["question"]) for row in rows if row["run"] == run and row["model"] == "gemma3:1b")
        assert first == second


@pytest.mark.parametrize("field,value", [
    ("think", True), ("models", ["hoangquan456/qwen3-nothink:4b"]),
    ("domains", ["loan_hard"]), ("runs_per_config", 0),
])
def test_rejects_out_of_scope_batch_settings(tmp_path, field, value):
    config = run_batch.load_config(run_batch.DEFAULT_CONFIG)
    config[field] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        run_batch.load_config(path)
