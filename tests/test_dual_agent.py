"""Deterministic tests for the dual-agent reasoning pipeline."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.langgraph_dual_agent import (  # noqa: E402
    build_dual_agent_graph,
    derive_option_label_from_phrase,
    run_dual_agent,
)
from evaluation.eval_harness import DomainConfig, run_with_store_dual_agent  # noqa: E402
from evaluation.scenarios import LOAN_INITIAL_BELIEFS, LOAN_RULES  # noqa: E402
from belief_store.domains.loan import setup_loan_domain  # noqa: E402


class SequenceMockLLM:
    """Mock LLM that returns scripted responses and records prompts."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls: list[dict[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str, model: str | None = None, json_mode: bool = False) -> str:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        if not self._responses:
            raise AssertionError("No scripted response left for generate().")
        return self._responses.pop(0)

    def generate_with_history(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        raise AssertionError("generate_with_history should not be used in dual-agent tests.")


def _single_turn_config(*, include_reasoning_gold: bool = True) -> DomainConfig:
    turn = {
        "attributes": ["loan.application_status"],
        "beliefs": {},
        "question": "What is the current application status?",
        "options": {
            "A": "approved",
            "B": "denied_ineligible",
            "C": "denied_amount_exceeded",
        },
        "correct": "A",
    }
    if include_reasoning_gold:
        turn["reasoning_gold"] = "approved"

    return DomainConfig(
        name="loan_dual_agent_test",
        setup_fn=setup_loan_domain,
        initial_beliefs=LOAN_INITIAL_BELIEFS,
        turns=[turn],
        baseline_rules=LOAN_RULES,
        default_entities="applicant, loan",
        is_conversational=False,
        accumulate_prior_beliefs=False,
    )


def test_run_dual_agent_returns_canonical_fields() -> None:
    llm = SequenceMockLLM(
        responses=[
            '{"conclusion":"approved","evidence_keys":["loan.application_status"],"reasoning":"all checks pass"}',
            '{"matched_option_text":"approved","matcher_rationale":"exact semantic match"}',
        ]
    )

    result = run_dual_agent(
        llm=llm,
        relevant_beliefs="loan.application_status = approved",
        query="What is the current application status?",
        options={"A": "approved", "B": "denied_ineligible"},
    )

    assert result["agent1_conclusion"] == "approved"
    assert result["agent1_evidence_keys"] == ["loan.application_status"]
    assert result["agent1_reasoning"] == "all checks pass"
    assert result["agent2_matched_option_text"] == "approved"
    assert result["agent2_matcher_rationale"] == "exact semantic match"
    assert result["agent2_matched_option_label"] == "A"
    assert result["agent2_match_status"] == "matched"


def test_deterministic_label_derivation() -> None:
    options = {
        "A": "approved",
        "B": "denied_ineligible",
        "C": "denied amount exceeded",
        "D": "Denied Amount Exceeded",
    }

    label, status = derive_option_label_from_phrase("approved", options)
    assert (label, status) == ("A", "matched")

    label, status = derive_option_label_from_phrase("  denied_ineligible  ", options)
    assert (label, status) == ("B", "matched")

    label, status = derive_option_label_from_phrase("denied amount exceeded", options)
    assert (label, status) == ("C", "matched")  # exact match wins over normalized ambiguity

    label, status = derive_option_label_from_phrase("manual_review", options)
    assert (label, status) == (None, "phrase-not-found")


def test_agent2_prompt_isolation_from_beliefs() -> None:
    llm = SequenceMockLLM(
        responses=[
            '{"conclusion":"approved","evidence_keys":["loan.application_status"],"reasoning":"derived from beliefs"}',
            '{"matched_option_text":"approved","matcher_rationale":"best phrase match"}',
        ]
    )

    config = _single_turn_config(include_reasoning_gold=True)
    run_with_store_dual_agent(llm, config)

    assert len(llm.calls) == 2
    agent1_prompt = llm.calls[0]["user_prompt"]
    agent2_prompt = llm.calls[1]["user_prompt"]

    assert "[RELEVANT BELIEFS]" in agent1_prompt
    assert "applicant.loan_amount_requested" in agent1_prompt

    assert "Conclusion:" in agent2_prompt
    assert "Options:" in agent2_prompt
    assert "Query:" not in agent2_prompt
    assert "applicant.loan_amount_requested" not in agent2_prompt
    assert "[RELEVANT BELIEFS]" not in agent2_prompt


def test_dual_agent_split_metrics_are_reported() -> None:
    llm = SequenceMockLLM(
        responses=[
            '{"conclusion":"approved","evidence_keys":["loan.application_status"],"reasoning":"gold aligns"}',
            '{"matched_option_text":"approved","matcher_rationale":"exact option phrase"}',
        ]
    )

    config = _single_turn_config(include_reasoning_gold=True)
    results = run_with_store_dual_agent(llm, config)

    assert len(results) == 1
    row = results[0]

    assert row["reasoning_scored"] is True
    assert row["reasoning_correct"] is True
    assert row["binding_scored"] is True
    assert row["binding_correct"] is True
    assert row["end_to_end_correct"] is True


def test_reasoning_metric_not_scored_without_gold() -> None:
    llm = SequenceMockLLM(
        responses=[
            '{"conclusion":"approved","evidence_keys":[],"reasoning":"no gold provided"}',
            '{"matched_option_text":"approved","matcher_rationale":"exact option phrase"}',
        ]
    )

    config = _single_turn_config(include_reasoning_gold=False)
    results = run_with_store_dual_agent(llm, config)

    assert len(results) == 1
    row = results[0]

    assert row["reasoning_scored"] is False
    assert row["reasoning_status"] == "not-scored-missing-gold"
    assert row["binding_scored"] is True
    assert row["end_to_end_correct"] is True
