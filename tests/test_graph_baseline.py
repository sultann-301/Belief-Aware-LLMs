"""Protect state parity and the no-computation boundary of graph retrieval."""

import copy
import csv
import json
from dataclasses import replace

import pytest

from belief_store.domains.loan import setup_loan_domain
from belief_store.store import BeliefStore
from evaluation.eval_common import DomainConfig
from evaluation.graphrag import run_evals
from evaluation.graphrag.condition import (
    CONDITION, fact_snapshots, retrieve_slices, run_with_graph_retrieval,
)
from evaluation.scenario_sets.base import LOAN_INITIAL_BELIEFS, LOAN_RULES


class RecordingLLM:
    def __init__(self, **kwargs):
        self.messages = []

    def generate_with_history_and_logprobs(self, messages):
        self.messages.append(copy.deepcopy(messages))
        return "ANSWER: [5000]", None

    def generate_with_logprobs(self, system_prompt, user_prompt):
        return self.generate_with_history_and_logprobs([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])


@pytest.fixture
def config():
    turn = {
        "attributes": ["loan.adjusted_income"],
        "beliefs": {},
        "question": "What is the adjusted income?",
        "options": {"A": "5000", "B": "9000"},
        "correct": "A",
    }
    return DomainConfig(
        name="loan", setup_fn=setup_loan_domain,
        initial_beliefs=dict(LOAN_INITIAL_BELIEFS), baseline_rules=LOAN_RULES,
        turns=[copy.deepcopy(turn), copy.deepcopy(turn)], is_conversational=False,
    )


def test_graph_never_executes_rules_or_resolves_store(config, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Graph retrieval attempted deterministic computation")

    original_add_rule = BeliefStore.add_rule

    def register_non_executable_rule(self, *args, **kwargs):
        kwargs["derive_fn"] = forbidden
        return original_add_rule(self, *args, **kwargs)

    monkeypatch.setattr(BeliefStore, "add_rule", register_non_executable_rule)
    monkeypatch.setattr(BeliefStore, "resolve_dirty_for_attributes", forbidden)
    monkeypatch.setattr(BeliefStore, "resolve_dirty", forbidden)
    llm = RecordingLLM()
    results = run_with_graph_retrieval(llm, config, debug_logs_enabled=False)
    assert all(result["hit"] for result in results)
    assert results[0]["retrieved_facts"] == {"applicant.income": 6000, "applicant.dependents": 2}
    assert results[0]["retrieved_rules"] == ["loan.adjusted_income"]
    assert "loan.adjusted_income = applicant.income" in results[0]["prompt"]
    assert "loan.adjusted_income = 5000" not in results[0]["prompt"]
    assert all(len(messages) == 2 for messages in llm.messages)


@pytest.mark.parametrize("conversational,accumulate,expected", [
    (False, False, 6000), (False, True, 10000), (True, False, 10000),
])
def test_updates_accumulate_only_when_configured(config, conversational, accumulate, expected):
    config.is_conversational = conversational
    config.accumulate_prior_beliefs = accumulate
    config.turns[0]["beliefs"] = {"applicant.income": 10000}
    config.turns[1]["beliefs"] = {"applicant.dependents": 3}
    before = copy.deepcopy(config)
    snapshots = fact_snapshots(config)
    results = run_with_graph_retrieval(RecordingLLM(), config, debug_logs_enabled=False)
    assert snapshots[0]["applicant.income"] == 10000
    assert results[1]["retrieved_facts"] == {"applicant.income": expected, "applicant.dependents": 3}
    assert config == before


def test_alternate_turn_sequence_controls_history(config):
    config.accumulate_prior_beliefs = True
    config.turns[0]["beliefs"] = {"applicant.income": 1}
    turns = copy.deepcopy(config.turns)
    turns[0]["beliefs"] = {"applicant.income": 10000}
    results = run_with_graph_retrieval(RecordingLLM(), config, turns=turns, debug_logs_enabled=False)
    assert results[1]["retrieved_facts"]["applicant.income"] == 10000


def test_answer_key_does_not_change_prompt(config):
    first = RecordingLLM()
    run_with_graph_retrieval(first, config, debug_logs_enabled=False)
    config.turns[0]["correct"] = "B"
    second = RecordingLLM()
    run_with_graph_retrieval(second, config, debug_logs_enabled=False)
    assert first.messages == second.messages


@pytest.mark.parametrize("bad_input", ["missing_targets", "unknown_target", "domain"])
def test_invalid_inputs_fail_before_generation(config, bad_input):
    if bad_input == "missing_targets":
        del config.turns[1]["attributes"]
    elif bad_input == "unknown_target":
        config.turns[1]["attributes"] = ["loan.nonexistent"]
    else:
        config = replace(config, baseline_rules="different rules")
    llm = RecordingLLM()
    with pytest.raises(ValueError):
        run_with_graph_retrieval(llm, config, debug_logs_enabled=False)
    assert llm.messages == []


def test_baseline_uses_updated_inputs_without_computing_outputs(config):
    config.is_conversational = True
    config.turns[0]["beliefs"] = {"applicant.income": 10000}
    llm = RecordingLLM()
    results = run_with_graph_retrieval(llm, config, debug_logs_enabled=False)
    assert len(results) == len(config.turns)
    assert len(llm.messages) == 2
    for messages in llm.messages:
        assert len(messages) == 2
        assert "applicant.income = 10000" in messages[1]["content"]
        assert config.turns[0]["question"] in messages[1]["content"]
        assert "loan.adjusted_income = 9000" not in messages[1]["content"]


def test_all_cli_scenarios_have_valid_retrieval_inputs():
    for domain in run_evals.DOMAINS:
        config = run_evals.DOMAIN_REGISTRY[domain]
        assert len(retrieve_slices(config)) == len(config.turns)


def test_cli_runs_only_graph_baseline_and_dry_run_needs_no_llm(config, tmp_path, monkeypatch, capsys):
    from evaluation import eval_conditions

    monkeypatch.setitem(run_evals.DOMAIN_REGISTRY, "loan_belief_maintenance", config)

    def no_old_conditions(*args, **kwargs):
        raise AssertionError("Graph baseline reran an existing condition")

    monkeypatch.setattr(eval_conditions, "run_with_store", no_old_conditions)
    monkeypatch.setattr(eval_conditions, "run_without_store", no_old_conditions)

    def no_llm(**kwargs):
        raise AssertionError("Dry run constructed an LLM client")

    monkeypatch.setattr(run_evals, "OllamaClient", no_llm)
    path = tmp_path / "graph_baseline.csv"
    run_evals.main(["--dry-run", "--csv-out", str(path)])
    assert not path.exists()
    assert "[RULES]" in capsys.readouterr().out

    llm = RecordingLLM()
    monkeypatch.setattr(run_evals, "OllamaClient", lambda **kwargs: llm)
    run_evals.main(["--runs", "2", "--csv-out", str(path)])
    with path.open() as output:
        rows = list(csv.DictReader(output))
    assert len(rows) == 4
    assert len(llm.messages) == 4
    assert {row["condition"] for row in rows} == {CONDITION}
    assert {row["run"] for row in rows} == {"1", "2"}
    graph_row = next(row for row in rows if row["condition"] == CONDITION)
    assert json.loads(graph_row["retrieved_facts"]) == {"applicant.income": 6000, "applicant.dependents": 2}
    assert all(row["response_cache"] == "False" for row in rows)
    with pytest.raises(FileExistsError):
        run_evals.main(["--csv-out", str(path)])
