"""
Unit tests for BeliefStore with the loan domain (domains.md spec).

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


def _seed_base_beliefs(store: BeliefStore, **overrides) -> None:
    """Add a full set of base beliefs with sensible defaults.

    Pass keyword arguments to override any default value, e.g.
    ``_seed_base_beliefs(store, income=3000, co_signer=True)``.
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
        "loan.min_income": 5000,
        "loan.min_credit": 650,
        "loan.max_debt_ratio": 0.4,
    }
    # Allow short-hand keys: income → applicant.income
    shorthand = {
        "income": "applicant.income",
        "credit_score": "applicant.credit_score",
        "co_signer": "applicant.co_signer",
        "debt_ratio": "applicant.debt_ratio",
        "employment_status": "applicant.employment_status",
        "bankruptcy_history": "applicant.bankruptcy_history",
        "employment_duration_months": "applicant.employment_duration_months",
        "has_collateral": "applicant.has_collateral",
        "loan_amount_requested": "applicant.loan_amount_requested",
        "min_income": "loan.min_income",
        "min_credit": "loan.min_credit",
        "max_debt_ratio": "loan.max_debt_ratio",
    }
    for k, v in overrides.items():
        full_key = shorthand.get(k, k)
        defaults[full_key] = v

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
# Core BeliefStore operations (generic, domain-independent)
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
# R2: loan.credit_score_effective
# =====================================================================


class TestR2CreditScoreEffective:

    def test_no_cosigner(self, loan_store):
        _seed_base_beliefs(loan_store, co_signer=False, credit_score=700)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 700

    def test_with_cosigner(self, loan_store):
        _seed_base_beliefs(loan_store, co_signer=True, credit_score=700)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 750

    def test_cosigner_boost_is_exactly_50(self, loan_store):
        _seed_base_beliefs(loan_store, co_signer=True, credit_score=600)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 650


# =====================================================================
# R1: loan.eligible
# =====================================================================


class TestR1Eligible:

    def test_basic_approval(self, loan_store):
        """All conditions met → eligible."""
        _seed_base_beliefs(loan_store)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True

    def test_unemployed_rejected(self, loan_store):
        """Unemployed always ineligible, regardless of other factors."""
        _seed_base_beliefs(loan_store, employment_status="unemployed")
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False

    def test_bankruptcy_with_short_employment(self, loan_store):
        """Bankruptcy + < 24 months employment → ineligible."""
        _seed_base_beliefs(
            loan_store, bankruptcy_history=True,
            employment_duration_months=12,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False

    def test_bankruptcy_with_sufficient_employment(self, loan_store):
        """Bankruptcy + >= 24 months → threshold check proceeds."""
        _seed_base_beliefs(
            loan_store, bankruptcy_history=True,
            employment_duration_months=24,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True

    def test_income_below_minimum(self, loan_store):
        """Income just below threshold → ineligible."""
        _seed_base_beliefs(loan_store, income=4999)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False

    def test_income_at_minimum(self, loan_store):
        """Income exactly at threshold → eligible (>=)."""
        _seed_base_beliefs(loan_store, income=5000)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True

    def test_credit_below_minimum_no_cosigner(self, loan_store):
        """Effective credit below threshold → ineligible."""
        _seed_base_beliefs(loan_store, credit_score=600, co_signer=False)
        loan_store.resolve_all_dirty()
        # effective = 600, min = 650 → ineligible
        assert loan_store.get_value("loan.eligible") is False

    def test_credit_below_minimum_cosigner_saves(self, loan_store):
        """Raw score 610 + co-signer +50 = 660 >= 650 → eligible."""
        _seed_base_beliefs(loan_store, credit_score=610, co_signer=True)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 660
        assert loan_store.get_value("loan.eligible") is True

    def test_debt_ratio_at_max(self, loan_store):
        """Debt ratio exactly at max_debt_ratio → ineligible (strict <)."""
        _seed_base_beliefs(loan_store, debt_ratio=0.4)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False

    def test_debt_ratio_just_below_max(self, loan_store):
        """Debt ratio just below threshold → eligible."""
        _seed_base_beliefs(loan_store, debt_ratio=0.39)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True


# =====================================================================
# R3: loan.rate_tier
# =====================================================================


class TestR3RateTier:

    def test_not_eligible_returns_none(self, loan_store):
        _seed_base_beliefs(loan_store, employment_status="unemployed")
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.rate_tier") is None

    def test_effective_score_750_preferred(self, loan_store):
        """Effective score exactly 750 → preferred."""
        _seed_base_beliefs(loan_store, credit_score=750, co_signer=False)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.rate_tier") == "preferred"

    def test_effective_score_749_standard(self, loan_store):
        """Effective score 749 → standard."""
        _seed_base_beliefs(loan_store, credit_score=749, co_signer=False)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.rate_tier") == "standard"

    def test_cosigner_pushes_to_preferred(self, loan_store):
        """Raw 710 + co-signer +50 = 760 >= 750 → preferred."""
        _seed_base_beliefs(loan_store, credit_score=710, co_signer=True)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 760
        assert loan_store.get_value("loan.rate_tier") == "preferred"


# =====================================================================
# R4: loan.max_amount
# =====================================================================


class TestR4MaxAmount:

    def test_not_eligible_zero(self, loan_store):
        _seed_base_beliefs(loan_store, employment_status="unemployed")
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.max_amount") == 0

    def test_no_collateral_30k(self, loan_store):
        _seed_base_beliefs(loan_store, has_collateral=False)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.max_amount") == 30_000

    def test_with_collateral_100k(self, loan_store):
        _seed_base_beliefs(loan_store, has_collateral=True)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.max_amount") == 100_000


# =====================================================================
# R5: loan.application_status
# =====================================================================


class TestR5ApplicationStatus:

    def test_denied_ineligible(self, loan_store):
        _seed_base_beliefs(loan_store, employment_status="unemployed")
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.application_status") == "denied_ineligible"

    def test_denied_amount_exceeded(self, loan_store):
        """Eligible but requesting more than max_amount."""
        _seed_base_beliefs(
            loan_store, has_collateral=False,
            loan_amount_requested=50_000,  # max without collateral = 30k
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True
        assert loan_store.get_value("loan.max_amount") == 30_000
        assert loan_store.get_value("loan.application_status") == "denied_amount_exceeded"

    def test_approved(self, loan_store):
        _seed_base_beliefs(loan_store, loan_amount_requested=10_000)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.application_status") == "approved"

    def test_amount_exactly_at_max(self, loan_store):
        """Requesting exactly max_amount → approved (not exceeded)."""
        _seed_base_beliefs(
            loan_store, has_collateral=False,
            loan_amount_requested=30_000,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.application_status") == "approved"


# =====================================================================
# R6: loan.high_risk_flag
# =====================================================================


class TestR6HighRiskFlag:

    def test_below_threshold(self, loan_store):
        _seed_base_beliefs(loan_store, debt_ratio=0.29)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.high_risk_flag") is False

    def test_at_threshold(self, loan_store):
        """Debt ratio exactly 0.3 → high risk (>=)."""
        _seed_base_beliefs(loan_store, debt_ratio=0.3)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.high_risk_flag") is True

    def test_above_threshold(self, loan_store):
        _seed_base_beliefs(loan_store, debt_ratio=0.5)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.high_risk_flag") is True


# =====================================================================
# Dirty propagation
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
# Belief maintenance — unrelated beliefs should NOT be affected
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
# Co-signer cascade scenarios
# =====================================================================


class TestCoSignerCascade:

    def test_adding_cosigner_flips_eligibility(self, loan_store):
        """Raw score 610 < 650 → ineligible.
        Add co-signer → 660 >= 650 → eligible."""
        _seed_base_beliefs(loan_store, credit_score=610, co_signer=False)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False

        loan_store.add_hypothesis("applicant.co_signer", True)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 660
        assert loan_store.get_value("loan.eligible") is True

    def test_removing_cosigner_reverts_eligibility(self, loan_store):
        """With co-signer: 610+50=660 → eligible.
        Remove co-signer: 610 < 650 → ineligible."""
        _seed_base_beliefs(loan_store, credit_score=610, co_signer=True)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True

        loan_store.add_hypothesis("applicant.co_signer", False)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 610
        assert loan_store.get_value("loan.eligible") is False

    def test_cosigner_pushes_rate_to_preferred(self, loan_store):
        """Raw 710: standard rate. Add co-signer → 760 → preferred."""
        _seed_base_beliefs(loan_store, credit_score=710, co_signer=False)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.rate_tier") == "standard"

        loan_store.add_hypothesis("applicant.co_signer", True)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.rate_tier") == "preferred"


# =====================================================================
# Retraction cascades
# =====================================================================


class TestRetractionCascade:

    def test_retract_income_cascades(self, resolved_loan_store):
        """Removing income removes eligible and everything downstream."""
        resolved_loan_store.remove_hypothesis("applicant.income")

        assert "applicant.income" not in resolved_loan_store.beliefs
        assert "loan.eligible" not in resolved_loan_store.beliefs
        assert "loan.rate_tier" not in resolved_loan_store.beliefs
        assert "loan.max_amount" not in resolved_loan_store.beliefs
        assert "loan.application_status" not in resolved_loan_store.beliefs

    def test_retract_income_keeps_credit_effective(self, resolved_loan_store):
        """credit_score_effective doesn't depend on income → kept."""
        resolved_loan_store.remove_hypothesis("applicant.income")
        assert "loan.credit_score_effective" in resolved_loan_store.beliefs

    def test_retract_income_keeps_high_risk(self, resolved_loan_store):
        """high_risk_flag depends on debt_ratio, not income → kept."""
        resolved_loan_store.remove_hypothesis("applicant.income")
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


# =====================================================================
# Full spec walkthrough (domains.md t=0 → t=2)
# =====================================================================


class TestSpecWalkthrough:

    def test_full_scenario(self, loan_store):
        """Reproduce the exact example from domains.md."""
        store = loan_store

        # ── t=0: Initial (income too low → ineligible) ──────────────
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

        store.resolve_all_dirty()

        # R2: 700 (no co-signer)
        assert store.get_value("loan.credit_score_effective") == 700
        # R1: 3000 < 5000 → False
        assert store.get_value("loan.eligible") is False
        # R3: not eligible → None
        assert store.get_value("loan.rate_tier") is None
        # R4: not eligible → 0
        assert store.get_value("loan.max_amount") == 0
        # R5: not eligible → denied_ineligible
        assert store.get_value("loan.application_status") == "denied_ineligible"
        # R6: 0.3 >= 0.3 → True
        assert store.get_value("loan.high_risk_flag") is True

        assert len(store.dirty) == 0

        prompt_t0, _ = store.to_prompt(["applicant", "loan"])
        assert "denied_ineligible" in prompt_t0

        # ── t=1: Income updated to 6000 ─────────────────────────────
        log_before = len(store.revision_log)
        store.add_hypothesis("applicant.income", 6000)

        # Dirty set should include eligible and its downstream
        assert "loan.eligible" in store.dirty
        assert "loan.rate_tier" in store.dirty
        assert "loan.max_amount" in store.dirty
        assert "loan.application_status" in store.dirty
        # credit_score_effective should NOT be dirty
        assert "loan.credit_score_effective" not in store.dirty

        # ── t=2: Resolve ─────────────────────────────────────────────
        store.resolve_all_dirty()

        # R1: 6000 >= 5000 ✓, 700 >= 650 ✓, 0.3 < 0.4 ✓ → True
        assert store.get_value("loan.eligible") is True
        # R3: eligible, 700 < 750 → standard
        assert store.get_value("loan.rate_tier") == "standard"
        # R4: eligible, no collateral → 30000
        assert store.get_value("loan.max_amount") == 30_000
        # R5: 10000 <= 30000 → approved
        assert store.get_value("loan.application_status") == "approved"
        # R6: unchanged (debt_ratio unchanged)
        assert store.get_value("loan.high_risk_flag") is True

        assert len(store.dirty) == 0

        prompt_t2, _ = store.to_prompt(["applicant", "loan"])
        assert "approved" in prompt_t2

        # Verify audit trail captured the transition
        log_t2 = store.format_revision_log(since_index=log_before)
        assert "[update]" in log_t2
        assert "[derived]" in log_t2


# =====================================================================
# Edge cases
# =====================================================================


class TestEdgeCases:

    def test_bankruptcy_boundary_23_months(self, loan_store):
        """23 months < 24 → ineligible with bankruptcy."""
        _seed_base_beliefs(
            loan_store, bankruptcy_history=True,
            employment_duration_months=23,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False

    def test_bankruptcy_boundary_24_months(self, loan_store):
        """24 months = 24 → NOT < 24 → proceed to threshold check."""
        _seed_base_beliefs(
            loan_store, bankruptcy_history=True,
            employment_duration_months=24,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True

    def test_no_bankruptcy_short_employment_ok(self, loan_store):
        """Without bankruptcy, short employment is irrelevant."""
        _seed_base_beliefs(
            loan_store, bankruptcy_history=False,
            employment_duration_months=1,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True

    def test_multiple_rapid_updates(self, loan_store):
        """Several updates before resolving — only final state matters."""
        _seed_base_beliefs(loan_store, income=3000)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False

        # Rapid-fire updates
        loan_store.add_hypothesis("applicant.income", 4000)
        loan_store.add_hypothesis("applicant.income", 5000)
        loan_store.add_hypothesis("applicant.income", 6000)

        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is True
        assert loan_store.get_value("applicant.income") == 6000

    def test_loan_request_exactly_one_over_max(self, loan_store):
        """Requesting max_amount + 1 → denied."""
        _seed_base_beliefs(
            loan_store, has_collateral=False,
            loan_amount_requested=30_001,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.application_status") == "denied_amount_exceeded"

    def test_cosigner_boundary_at_min_credit(self, loan_store):
        """Raw 600 + co-signer 50 = 650 = min_credit → eligible."""
        _seed_base_beliefs(loan_store, credit_score=600, co_signer=True)
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.credit_score_effective") == 650
        assert loan_store.get_value("loan.eligible") is True

    def test_all_failing_conditions(self, loan_store):
        """Unemployed, bankrupt, broke — still gets consistent results."""
        _seed_base_beliefs(
            loan_store,
            employment_status="unemployed",
            bankruptcy_history=True,
            employment_duration_months=1,
            income=1000,
            credit_score=300,
            debt_ratio=0.9,
        )
        loan_store.resolve_all_dirty()
        assert loan_store.get_value("loan.eligible") is False
        assert loan_store.get_value("loan.rate_tier") is None
        assert loan_store.get_value("loan.max_amount") == 0
        assert loan_store.get_value("loan.application_status") == "denied_ineligible"
        assert loan_store.get_value("loan.high_risk_flag") is True

    def test_clean_prompt_includes_all_keys(self, resolved_loan_store):
        """A fully resolved store should produce a clean prompt
        with all base + derived beliefs for 'applicant' and 'loan'."""
        prompt, keys = resolved_loan_store.to_prompt(["applicant", "loan"])

        # 12 base beliefs + 6 derived = 18
        assert len(keys) == 18
        assert "[derived] loan.eligible = True" in prompt
        assert "[base] applicant.income = 6000" in prompt
