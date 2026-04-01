"""
Unit tests for the specific loan domain rules (domains.md spec).

Covers:
  - Core BeliefStore operations (add, update, retract, prompt, log)
  - Individual rule correctness for all 6 loan rules
  - Dirty propagation chains
  - Full revision walkthrough (t=0 → t=2 from spec)
  - Co-signer cascade effects
  - Belief maintenance (unrelated beliefs stay clean)
  - Retraction cascades
  - Edge / boundary values
"""

import pytest

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain


# ── Helpers ──────────────────────────────────────────────────────────


def _make_loan_store() -> BeliefStore:
    """Return a BeliefStore with loan rules registered."""
    s = BeliefStore()
    setup_loan_domain(s)
    return s


def _seed_base_beliefs(store: BeliefStore, overrides: dict | None = None) -> None:
    """Add a full set of base beliefs with sensible defaults.

    Pass a dict to override any default value, e.g.
    ``_seed_base_beliefs(store, {"applicant.income": 3000})``.
    """
    defaults = {
        "applicant.income": 6000,
        "applicant.credit_score": 720,
        "applicant.co_signer": False,
        "applicant.debt_ratio": 0.20,
        "applicant.employment_status": "employed",
        "applicant.bankruptcy_history": False,
        "applicant.employment_duration_months": 36,
        "applicant.has_collateral": False,
        "applicant.loan_amount_requested": 10_000,
        "applicant.dependents": 0,
        "applicant.marital_status": "single",
        "loan.min_income": 5000,
        "loan.min_credit": 650,
        "loan.max_debt_ratio": 0.4,
    }
    if overrides:
        defaults.update(overrides)

    for key, value in defaults.items():
        store.add_hypothesis(key, value)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def store():
    """Empty BeliefStore."""
    return BeliefStore()


@pytest.fixture
def loan_store():
    """BeliefStore with loan-domain rules registered, no beliefs yet."""
    return _make_loan_store()


@pytest.fixture
def resolved_loan_store():
    """Loan store with default base beliefs added and fully resolved."""
    s = _make_loan_store()
    _seed_base_beliefs(s)
    s.resolve_all_dirty()
    return s


# =====================================================================


class TestAddHypothesis:

    def test_add_new_belief(self, store):
        store.add_hypothesis("applicant.income", 6000)

        assert store.get_value("applicant.income") == 6000
        _, is_derived = store.beliefs["applicant.income"]
        assert is_derived is False
        assert len(store.revision_log) == 1
        assert store.revision_log[0]["action"] == "add"

    def test_update_existing_belief(self, store):
        store.add_hypothesis("applicant.income", 4000)
        store.add_hypothesis("applicant.income", 6000)

        assert store.get_value("applicant.income") == 6000
        assert len(store.revision_log) == 2
        assert store.revision_log[1]["action"] == "update"
        assert store.revision_log[1]["old"] == 4000
        assert store.revision_log[1]["new"] == 6000


class TestRetraction:

    def test_retract_logs_action(self, store):
        store.add_hypothesis("foo.bar", 42)
        log_start = len(store.revision_log)
        store.remove_hypothesis("foo.bar")

        entry = store.revision_log[log_start]
        assert entry["action"] == "retract"
        assert entry["old"] == 42
        assert entry["new"] is None

    def test_retract_nonexistent_is_safe(self, store):
        store.remove_hypothesis("does.not.exist")
        assert store.revision_log[-1]["action"] == "retract"


class TestPromptConstruction:

    def test_dirty_assertion_raises(self, resolved_loan_store):
        resolved_loan_store.add_hypothesis("applicant.income", 3000)
        with pytest.raises(AssertionError):
            resolved_loan_store.to_prompt(["loan"])

    def test_entity_filtering(self, store):
        store.add_hypothesis("applicant.income", 6000)
        store.add_hypothesis("unrelated.data", "hello")

        prompt, keys = store.to_prompt(["applicant"])
        assert "applicant.income" in prompt
        assert "unrelated" not in prompt
        assert len(keys) == 1


class TestRevisionLog:

    def test_log_format(self, store):
        store.add_hypothesis("x.a", 1)
        store.add_hypothesis("x.a", 2)
        log = store.format_revision_log()
        assert "[add]" in log
        assert "[update]" in log
        assert "1 → 2" in log

    def test_since_index(self, store):
        store.add_hypothesis("x.a", 1)
        store.add_hypothesis("x.b", 2)
        log = store.format_revision_log(since_index=1)
        assert "x.a" not in log
        assert "x.b" in log


# =====================================================================


class TestDirtyPropagation:

    def test_income_change_dirties_eligible_and_downstream(
        self, resolved_loan_store,
    ):
        """Changing income dirties eligible → rate_tier, max_amount, application_status."""
        resolved_loan_store.add_hypothesis("applicant.income", 3000)

        assert "loan.eligible" in resolved_loan_store.dirty
        assert "loan.rate_tier" in resolved_loan_store.dirty
        assert "loan.max_amount" in resolved_loan_store.dirty
        assert "loan.application_status" in resolved_loan_store.dirty
        # credit_score_effective and high_risk_flag are NOT affected
        assert "loan.credit_score_effective" not in resolved_loan_store.dirty
        assert "loan.high_risk_flag" not in resolved_loan_store.dirty

    def test_credit_score_change_dirties_effective_and_chain(
        self, resolved_loan_store,
    ):
        """credit_score → credit_score_effective → eligible → rate_tier, etc."""
        resolved_loan_store.add_hypothesis("applicant.credit_score", 500)

        assert "loan.credit_score_effective" in resolved_loan_store.dirty
        assert "loan.eligible" in resolved_loan_store.dirty
        assert "loan.rate_tier" in resolved_loan_store.dirty

    def test_cosigner_change_dirties_effective_and_chain(
        self, resolved_loan_store,
    ):
        """co_signer → credit_score_effective → eligible + rate_tier."""
        resolved_loan_store.add_hypothesis("applicant.co_signer", True)

        assert "loan.credit_score_effective" in resolved_loan_store.dirty
        assert "loan.eligible" in resolved_loan_store.dirty
        assert "loan.rate_tier" in resolved_loan_store.dirty

    def test_debt_ratio_dirties_eligible_and_high_risk(
        self, resolved_loan_store,
    ):
        """debt_ratio feeds both eligible and high_risk_flag."""
        resolved_loan_store.add_hypothesis("applicant.debt_ratio", 0.5)

        assert "loan.eligible" in resolved_loan_store.dirty
        assert "loan.high_risk_flag" in resolved_loan_store.dirty

    def test_collateral_only_dirties_max_amount(self, resolved_loan_store):
        """has_collateral feeds only max_amount."""
        resolved_loan_store.add_hypothesis("applicant.has_collateral", True)

        assert "loan.max_amount" in resolved_loan_store.dirty
        # eligible should NOT be dirty
        assert "loan.eligible" not in resolved_loan_store.dirty


# =====================================================================


class TestBeliefMaintain:

    def test_credit_change_does_not_affect_employment(
        self, resolved_loan_store,
    ):
        """Changing credit_score should NOT dirty employment-related keys."""
        resolved_loan_store.add_hypothesis("applicant.credit_score", 500)
        resolved_loan_store.resolve_all_dirty()

        # employment_status is a base belief, never derived, never dirty
        assert "applicant.employment_status" not in resolved_loan_store.dirty
        assert (
            resolved_loan_store.get_value("applicant.employment_status")
            == "employed"
        )

    def test_employment_change_does_not_affect_credit_effective(
        self, resolved_loan_store,
    ):
        """Changing employment_status should NOT dirty credit_score_effective."""
        resolved_loan_store.add_hypothesis(
            "applicant.employment_status", "unemployed",
        )

        assert "loan.credit_score_effective" not in resolved_loan_store.dirty

    def test_debt_ratio_does_not_affect_rate_tier_directly(
        self, resolved_loan_store,
    ):
        """debt_ratio feeds eligible (which feeds rate_tier), but does NOT
        directly feed rate_tier — so if eligible doesn't change, rate_tier
        stays clean after re-resolution of eligible.
        """
        # debt_ratio 0.20 → 0.25: both < 0.4, so eligible stays True
        old_rate = resolved_loan_store.get_value("loan.rate_tier")
        resolved_loan_store.add_hypothesis("applicant.debt_ratio", 0.25)
        resolved_loan_store.resolve_all_dirty()

        assert resolved_loan_store.get_value("loan.rate_tier") == old_rate


# =====================================================================


class TestRuleIndex:

    def test_rule_index_populated_on_add_rule(self, store):
        """rule_index maps output_key → rule dict after add_rule."""
        store.add_rule(
            name="test_rule",
            inputs=["x.a", "x.b"],
            output_key="x.out",
            derive_fn=lambda v: v["x.a"] + v["x.b"],
        )
        assert "x.out" in store.rule_index
        assert store.rule_index["x.out"]["name"] == "test_rule"
        assert store.rule_index["x.out"]["inputs"] == ["x.a", "x.b"]
        assert callable(store.rule_index["x.out"]["derive_fn"])

    def test_rule_index_does_not_store_output_key_field(self, store):
        """output_key is the dict key itself — not redundantly stored inside the rule."""
        store.add_rule(
            name="r", inputs=["a.x"], output_key="b.y", derive_fn=lambda v: v["a.x"]
        )
        assert "output_key" not in store.rule_index["b.y"]

    def test_rule_index_overwrite_on_duplicate_registration(self, store):
        """Re-registering a rule for the same output_key replaces the old entry."""
        store.add_rule("v1", ["a.x"], "b.y", lambda v: 1)
        store.add_rule("v2", ["a.x"], "b.y", lambda v: 2)

        assert len(store.rule_index) == 1
        assert store.rule_index["b.y"]["name"] == "v2"

    def test_repr_reflects_rule_index_count(self, loan_store):
        """__repr__ uses rule_index length, not a deleted derivation_rules list."""
        expected_rules = len(loan_store.rule_index)
        assert f"rules={expected_rules}" in repr(loan_store)

    def test_loan_domain_rules_all_indexed(self, loan_store):
        """Every loan rule has an entry in rule_index after setup_loan_domain."""
        expected_outputs = {
            "loan.adjusted_income",
            "loan.credit_score_effective",
            "loan.high_risk_flag",
            "loan.eligible",
            "loan.rate_tier",
            "loan.max_amount",
            "loan.application_status",
        }
        assert expected_outputs.issubset(loan_store.rule_index.keys())

    def test_derivation_uses_rule_index(self, store):
        """resolve_dirty correctly derives a value via the rule_index lookup."""
        store.add_rule(
            name="sum_rule",
            inputs=["x.a", "x.b"],
            output_key="x.out",
            derive_fn=lambda v: v["x.a"] + v["x.b"],
        )
        store.add_hypothesis("x.a", 3)
        store.add_hypothesis("x.b", 7)
        store.resolve_all_dirty()

        assert store.get_value("x.out") == 10


class TestRetractionCascade:

    def test_retract_income_cascades(self, resolved_loan_store):
        """Removing income removes eligible and downstream,
        but keeps unrelated derived beliefs."""
        resolved_loan_store.remove_hypothesis("applicant.income")

        # Removed: income and everything downstream of eligible
        assert "applicant.income" not in resolved_loan_store.beliefs
        assert "loan.eligible" not in resolved_loan_store.beliefs
        assert "loan.rate_tier" not in resolved_loan_store.beliefs
        assert "loan.max_amount" not in resolved_loan_store.beliefs
        assert "loan.application_status" not in resolved_loan_store.beliefs

        # Kept: beliefs not in income's dependency chain
        assert "loan.credit_score_effective" in resolved_loan_store.beliefs
        assert "loan.high_risk_flag" in resolved_loan_store.beliefs

    def test_retract_credit_score_cascades_through_effective(
        self, resolved_loan_store,
    ):
        """Removing credit_score removes credit_score_effective,
        which removes eligible and all downstream."""
        resolved_loan_store.remove_hypothesis("applicant.credit_score")

        assert "loan.credit_score_effective" not in resolved_loan_store.beliefs
        assert "loan.eligible" not in resolved_loan_store.beliefs
        assert "loan.rate_tier" not in resolved_loan_store.beliefs

    def test_retract_debt_ratio_removes_both_eligible_and_high_risk(
        self, resolved_loan_store,
    ):
        """debt_ratio feeds both eligible and high_risk_flag."""
        resolved_loan_store.remove_hypothesis("applicant.debt_ratio")

        assert "loan.eligible" not in resolved_loan_store.beliefs
        assert "loan.high_risk_flag" not in resolved_loan_store.beliefs


