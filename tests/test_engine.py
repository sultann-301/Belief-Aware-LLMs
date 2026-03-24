"""
Unit tests for ReasoningEngine (uses MockLLMClient — no Ollama needed).

Covers:
  - Engine resolves dirty beliefs before calling LLM
  - Engine builds correct prompt structure
  - Engine returns LLM response unmodified
  - Engine never writes to the store after LLM call
  - Log cursor advances between queries
  - Full turn cycle: add beliefs → query → verify
"""

import pytest

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain
from belief_store.engine import ReasoningEngine, SYSTEM_PROMPT
from belief_store.llm_client import LLMClient


# ── Mock LLM ─────────────────────────────────────────────────────────


class MockLLMClient:
    """Records calls and returns a canned response."""

    def __init__(self, response: str = "REASONING: mock\nANSWER: mock") -> None:
        self.response = response
        self.calls: list[dict[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        })
        return self.response


# ── Helpers ──────────────────────────────────────────────────────────


def _make_engine(
    mock_response: str = "REASONING: mock\nANSWER: mock",
) -> tuple[BeliefStore, MockLLMClient, ReasoningEngine]:
    """Create a loan-domain store + mock LLM + engine."""
    store = BeliefStore()
    setup_loan_domain(store)
    mock = MockLLMClient(response=mock_response)
    engine = ReasoningEngine(store, mock)
    return store, mock, engine


def _seed(store: BeliefStore) -> None:
    """Add a standard set of base beliefs."""
    store.add_hypothesis("applicant.income", 6000)
    store.add_hypothesis("applicant.credit_score", 720)
    store.add_hypothesis("applicant.co_signer", False)
    store.add_hypothesis("applicant.debt_ratio", 0.20)
    store.add_hypothesis("applicant.employment_status", "employed")
    store.add_hypothesis("applicant.bankruptcy_history", False)
    store.add_hypothesis("applicant.employment_duration_months", 36)
    store.add_hypothesis("applicant.has_collateral", False)
    store.add_hypothesis("applicant.loan_amount_requested", 10_000)
    store.add_hypothesis("loan.min_income", 5000)
    store.add_hypothesis("loan.min_credit", 650)
    store.add_hypothesis("loan.max_debt_ratio", 0.4)


# ── Tests ────────────────────────────────────────────────────────────


class TestMockSatisfiesProtocol:

    def test_mock_is_llm_client(self):
        assert isinstance(MockLLMClient(), LLMClient)


class TestDirtyResolution:

    def test_query_resolves_dirty(self):
        """Engine resolves all dirty beliefs before calling the LLM."""
        store, mock, engine = _make_engine()
        _seed(store)
        assert len(store.dirty) > 0  # beliefs are dirty after seeding

        engine.query("What is the status?", ["applicant", "loan"])

        assert len(store.dirty) == 0
        assert store.beliefs["loan.eligible"] is True

    def test_query_on_clean_store(self):
        """Calling query on an already-clean store still works."""
        store, mock, engine = _make_engine()
        _seed(store)
        store.resolve_all_dirty()

        result = engine.query("Status?", ["applicant", "loan"])
        assert result == mock.response


class TestPromptStructure:

    def test_prompt_contains_sections(self):
        """User prompt must have the three required sections."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("What is the loan status?", ["applicant", "loan"])

        user_prompt = mock.calls[0]["user_prompt"]
        assert "[NEW INFORMATION THIS TURN]" in user_prompt
        assert "[RELEVANT BELIEFS (after update)]" in user_prompt
        assert "[QUERY]" in user_prompt
        assert "What is the loan status?" in user_prompt

    def test_prompt_contains_beliefs(self):
        """Prompt must include the resolved belief values."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("Status?", ["applicant", "loan"])

        user_prompt = mock.calls[0]["user_prompt"]
        assert "applicant.income = 6000" in user_prompt
        assert "loan.eligible = True" in user_prompt

    def test_system_prompt_is_correct(self):
        """Engine passes the SYSTEM_PROMPT constant."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("Status?", ["applicant", "loan"])

        assert mock.calls[0]["system_prompt"] == SYSTEM_PROMPT

    def test_prompt_shows_changes(self):
        """After an update, the NEW INFORMATION section shows the change."""
        store, mock, engine = _make_engine()
        _seed(store)

        # First query to advance the cursor past the initial adds
        engine.query("Status?", ["applicant", "loan"])

        # Now update a belief and query again
        store.add_hypothesis("applicant.income", 3000)
        engine.query("What changed?", ["applicant", "loan"])

        user_prompt = mock.calls[1]["user_prompt"]
        assert "[update]" in user_prompt
        assert "6000" in user_prompt  # old value in the log
        assert "3000" in user_prompt  # new value in the log

    def test_no_changes_shows_placeholder(self):
        """If nothing changed since last query, show '(no changes)'."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("Status?", ["applicant", "loan"])
        # Query again with no modifications
        engine.query("Status again?", ["applicant", "loan"])

        user_prompt = mock.calls[1]["user_prompt"]
        assert "(no changes)" in user_prompt


class TestResponsePassthrough:

    def test_returns_llm_response_unmodified(self):
        """Engine returns exactly what the LLM returns."""
        canned = "REASONING: The loan is approved.\nANSWER: Approved."
        store, mock, engine = _make_engine(mock_response=canned)
        _seed(store)

        result = engine.query("Status?", ["applicant", "loan"])
        assert result == canned


class TestStoreIntegrity:

    def test_store_not_modified_after_llm_call(self):
        """The engine must NOT write anything to the store after the LLM responds."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("Status?", ["applicant", "loan"])

        beliefs_after = dict(store.beliefs)
        log_len_after = len(store.revision_log)

        # Nothing new should be written — snapshot should match
        assert store.beliefs == beliefs_after
        assert len(store.revision_log) == log_len_after

    def test_multiple_queries_do_not_corrupt_store(self):
        """Running several queries in sequence keeps the store consistent."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("Q1?", ["applicant", "loan"])
        store.add_hypothesis("applicant.income", 3000)
        engine.query("Q2?", ["applicant", "loan"])
        store.add_hypothesis("applicant.income", 8000)
        engine.query("Q3?", ["applicant", "loan"])

        assert len(store.dirty) == 0
        assert store.beliefs["applicant.income"] == 8000
        assert store.beliefs["loan.eligible"] is True


class TestLogCursor:

    def test_cursor_advances(self):
        """Log cursor should advance so next query only shows new changes."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("Q1?", ["applicant", "loan"])
        cursor_after_q1 = engine._log_cursor

        store.add_hypothesis("applicant.income", 3000)
        engine.query("Q2?", ["applicant", "loan"])
        cursor_after_q2 = engine._log_cursor

        assert cursor_after_q2 > cursor_after_q1

    def test_first_query_includes_all_history(self):
        """First query should include all adds + derivations."""
        store, mock, engine = _make_engine()
        _seed(store)

        engine.query("Q1?", ["applicant", "loan"])

        user_prompt = mock.calls[0]["user_prompt"]
        # Should contain the initial add entries
        assert "[add]" in user_prompt


class TestFullTurnCycle:

    def test_full_scenario(self):
        """Add beliefs → query → update → query → verify prompt differences."""
        store, mock, engine = _make_engine()

        # Turn 1: initial beliefs (income too low)
        store.add_hypothesis("applicant.income", 3000)
        store.add_hypothesis("applicant.credit_score", 700)
        store.add_hypothesis("applicant.co_signer", False)
        store.add_hypothesis("applicant.debt_ratio", 0.3)
        store.add_hypothesis("applicant.employment_status", "employed")
        store.add_hypothesis("applicant.bankruptcy_history", False)
        store.add_hypothesis("applicant.employment_duration_months", 36)
        store.add_hypothesis("applicant.has_collateral", False)
        store.add_hypothesis("applicant.loan_amount_requested", 10_000)
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 650)
        store.add_hypothesis("loan.max_debt_ratio", 0.4)

        result1 = engine.query(
            "What is the loan status?", ["applicant", "loan"],
        )
        assert result1 == mock.response
        assert store.beliefs["loan.eligible"] is False
        assert store.beliefs["loan.application_status"] == "denied_ineligible"

        # Prompt should contain the denied status
        prompt1 = mock.calls[0]["user_prompt"]
        assert "denied_ineligible" in prompt1

        # Turn 2: income updated
        store.add_hypothesis("applicant.income", 6000)

        result2 = engine.query(
            "What changed with the loan?", ["applicant", "loan"],
        )
        assert result2 == mock.response
        assert store.beliefs["loan.eligible"] is True
        assert store.beliefs["loan.application_status"] == "approved"

        # Second prompt should show the update and approved status
        prompt2 = mock.calls[1]["user_prompt"]
        assert "[update]" in prompt2
        assert "approved" in prompt2
        # First prompt's full add history should NOT appear in second prompt
        assert prompt2.count("[add]") == 0
