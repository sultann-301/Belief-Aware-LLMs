"""Unit tests for ReasoningEngine (uses MockLLMClient — no Ollama needed)."""

import pytest

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain
from belief_store.engine import ReasoningEngine, SYSTEM_PROMPT
from belief_store.llm_client import LLMClient


class MockLLMClient:

    def __init__(self, response: str = "REASONING: mock\nANSWER: mock") -> None:
        self.response = response
        self.calls: list[dict[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self.response

    def generate_with_history(self, messages: list[dict[str, str]]) -> str:
        self.calls.append({"messages": messages})
        return self.response


def _make_engine(mock_response="REASONING: mock\nANSWER: mock"):
    store = BeliefStore()
    setup_loan_domain(store)
    mock = MockLLMClient(response=mock_response)
    return store, mock, ReasoningEngine(store, mock)


def _seed(store):
    store.add_hypothesis("applicant.income", 6000)
    store.add_hypothesis("applicant.credit_score", 720)
    store.add_hypothesis("applicant.co_signer", False)
    store.add_hypothesis("applicant.debt_ratio", 0.20)
    store.add_hypothesis("applicant.employment_status", "employed")
    store.add_hypothesis("applicant.bankruptcy_history", False)
    store.add_hypothesis("applicant.employment_duration_months", 36)
    store.add_hypothesis("applicant.has_collateral", False)
    store.add_hypothesis("applicant.loan_amount_requested", 10_000)
    store.add_hypothesis("applicant.dependents", 0)
    store.add_hypothesis("applicant.marital_status", "single")
    store.add_hypothesis("loan.min_income", 5000)
    store.add_hypothesis("loan.min_credit", 650)
    store.add_hypothesis("loan.max_debt_ratio", 0.4)


def _structured(entities="applicant, loan", query="Status?", new_beliefs=None):
    parts = [f"[ENTITY]\n{entities}"]
    if new_beliefs:
        parts.append(f"[NEW BELIEF]\n{new_beliefs}")
    parts.append(f"[QUERY]\n{query}")
    return "\n\n".join(parts)


class TestMockSatisfiesProtocol:

    def test_mock_is_llm_client(self):
        assert isinstance(MockLLMClient(), LLMClient)


class TestInputParsing:

    def test_missing_entity_raises(self):
        store, mock, engine = _make_engine()
        _seed(store)
        with pytest.raises(ValueError, match="Missing \\[ENTITY\\]"):
            engine.query("[QUERY]\nHello?")

    def test_missing_query_raises(self):
        store, mock, engine = _make_engine()
        _seed(store)
        with pytest.raises(ValueError, match="Missing \\[QUERY\\]"):
            engine.query("[ENTITY]\napplicant")

    def test_parses_multiple_entities(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured("applicant, loan"))
        prompt = mock.calls[0]["user_prompt"]
        assert "applicant, loan" in prompt


class TestNewBelief:

    def test_injects_belief_into_store(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured(new_beliefs="applicant.income = 9000"))
        assert store.get_value("applicant.income") == 9000

    def test_parses_bool(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured(new_beliefs="applicant.co_signer = true"))
        assert store.get_value("applicant.co_signer") is True

    def test_parses_float(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured(new_beliefs="applicant.debt_ratio = 0.15"))
        assert store.get_value("applicant.debt_ratio") == 0.15

    def test_multiple_beliefs(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured(
            new_beliefs="applicant.income = 9000\napplicant.co_signer = true",
        ))
        assert store.get_value("applicant.income") == 9000
        assert store.get_value("applicant.co_signer") is True

    def test_beliefs_resolved_after_injection(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured(new_beliefs="applicant.income = 2000"))
        assert store.get_value("loan.eligible") is False

    def test_optional_section(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured())  # no [NEW BELIEF]
        assert len(mock.calls) == 1  # still works


class TestDirtyResolution:

    def test_query_resolves_dirty(self):
        store, mock, engine = _make_engine()
        _seed(store)
        assert len(store.dirty) > 0

        engine.query(_structured())
        assert len(store.dirty) == 0
        assert store.get_value("loan.eligible") is True


class TestPromptStructure:

    def test_prompt_contains_sections(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured(query="Is the loan approved?"))

        prompt = mock.calls[0]["user_prompt"]
        assert "[ENTITY]" in prompt
        assert "[RELEVANT BELIEFS]" in prompt
        assert "[QUERY]" in prompt
        assert "Is the loan approved?" in prompt

    def test_prompt_contains_beliefs(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured())

        prompt = mock.calls[0]["user_prompt"]
        assert "applicant.income = 6000" in prompt
        assert "loan.eligible = True" in prompt

    def test_system_prompt_is_correct(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured())
        assert mock.calls[0]["system_prompt"] == SYSTEM_PROMPT


class TestResponsePassthrough:

    def test_returns_llm_response_unmodified(self):
        canned = "REASONING: Approved.\nANSWER: Yes."
        store, mock, engine = _make_engine(mock_response=canned)
        _seed(store)
        assert engine.query(_structured()) == canned


class TestStoreIntegrity:

    def test_store_not_modified_after_llm_call(self):
        store, mock, engine = _make_engine()
        _seed(store)
        engine.query(_structured())

        snapshot = dict(store.beliefs)
        log_len = len(store.revision_log)
        assert store.beliefs == snapshot
        assert len(store.revision_log) == log_len

    def test_multiple_queries_keep_store_consistent(self):
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query(_structured())
        store.add_hypothesis("applicant.income", 3000)
        engine.query(_structured(query="Now?"))
        store.add_hypothesis("applicant.income", 8000)
        engine.query(_structured(query="And now?"))

        assert len(store.dirty) == 0
        assert store.get_value("applicant.income") == 8000
        assert store.get_value("loan.eligible") is True


class TestFullTurnCycle:

    def test_two_turns(self):
        store, mock, engine = _make_engine()

        store.add_hypothesis("applicant.income", 3000)
        store.add_hypothesis("applicant.credit_score", 700)
        store.add_hypothesis("applicant.co_signer", False)
        store.add_hypothesis("applicant.debt_ratio", 0.3)
        store.add_hypothesis("applicant.employment_status", "employed")
        store.add_hypothesis("applicant.bankruptcy_history", False)
        store.add_hypothesis("applicant.employment_duration_months", 36)
        store.add_hypothesis("applicant.has_collateral", False)
        store.add_hypothesis("applicant.loan_amount_requested", 10_000)
        store.add_hypothesis("applicant.dependents", 2)
        store.add_hypothesis("applicant.marital_status", "single")
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 650)
        store.add_hypothesis("loan.max_debt_ratio", 0.4)

        engine.query(_structured(query="Status?"))
        assert store.get_value("loan.eligible") is False
        assert "denied_ineligible" in mock.calls[0]["user_prompt"]

        store.add_hypothesis("applicant.income", 6000)
        engine.query(_structured(query="Now?"))
        assert store.get_value("loan.eligible") is True
        assert "approved" in mock.calls[1]["user_prompt"]
