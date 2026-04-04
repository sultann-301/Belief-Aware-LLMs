"""
Unit tests for the specific crime scene domain rules (domains.md spec).

Covers:
  - Core BeliefStore operations (add, update, prompt, log)
  - Individual rule correctness for all 10 crime scene rules
  - Dirty propagation chains
  - Full revision walkthrough (t=0 → t=1 procedural cascade from spec)
  - Edge / boundary values like digital evidence overrides
"""

import pytest

from belief_store.store import BeliefStore
from belief_store.domains.crime_scene import setup_crime_scene_domain


# ── Helpers ──────────────────────────────────────────────────────────


def _make_crime_store() -> BeliefStore:
    """Return a BeliefStore with crime scene rules registered."""
    s = BeliefStore()
    setup_crime_scene_domain(s)
    return s


def _seed_base_beliefs(store: BeliefStore, overrides: dict | None = None) -> None:
    """Add a full set of base beliefs with sensible defaults."""
    defaults = {
        "officer_smith.status": "active",
        "case.warrant_status": False,
        "case.cctv_status": "corrupted",
        "case.cctv_subject": "none",
        "suspect_a.home_evidence": "gun",
        "suspect_a.evidence_logger": "officer_smith",
        "suspect_a.financial_records": "clean",
        "suspect_b.relation_to_victim": "stranger",
        "suspect_b.alibi_partner": "suspect_a",
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
def crime_store():
    """BeliefStore with crime scene-domain rules registered, no beliefs yet."""
    return _make_crime_store()


@pytest.fixture
def resolved_crime_store():
    """Crime scene store with default base beliefs added and fully resolved."""
    s = _make_crime_store()
    _seed_base_beliefs(s)
    s.resolve_all_dirty()
    return s


# =====================================================================
# BLOCKS 1 & 2: Base Rules
# =====================================================================


class TestPhysicalEvidence:

    def test_active_officer(self, crime_store):
        """Active officer passes the home evidence through as admissible."""
        _seed_base_beliefs(crime_store, {"officer_smith.status": "active", "suspect_a.home_evidence": "gun"})
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_a.admissible_evidence") == "gun"

    def test_suspended_officer(self, crime_store):
        """Suspended officer suppresses the physical evidence to none."""
        _seed_base_beliefs(crime_store, {"officer_smith.status": "suspended", "suspect_a.home_evidence": "gun"})
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_a.admissible_evidence") == "none"

    def test_different_logger_ignores_smith(self, crime_store):
        """If someone else logged it, Smith's suspension doesn't matter."""
        _seed_base_beliefs(crime_store, {
            "officer_smith.status": "suspended",
            "suspect_a.evidence_logger": "officer_jones",
            "suspect_a.home_evidence": "gun"
        })
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_a.admissible_evidence") == "gun"


class TestSuspectStatus:

    def test_admissible_evidence_makes_prime(self, crime_store):
        """Any valid evidence string != "none" sets prime_suspect."""
        _seed_base_beliefs(crime_store, {"suspect_a.home_evidence": "gun", "officer_smith.status": "active"})
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_a.status") == "prime_suspect"

    def test_no_admissible_evidence_clears(self, crime_store):
        """If admissible is none, suspect is cleared."""
        _seed_base_beliefs(crime_store, {"suspect_a.home_evidence": "none"})
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_a.status") == "cleared"


# =====================================================================
# ALIBI HIERARCHY
# =====================================================================


class TestAlibis:

    def test_broken_testimonial(self, crime_store):
        """If B points to A, and A is prime, testimonial alibi breaks."""
        _seed_base_beliefs(crime_store, {"suspect_a.home_evidence": "gun", "suspect_b.alibi_partner": "suspect_a"})
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_b.testimonial_alibi") == "broken"
        assert crime_store.get_value("suspect_b.status") == "prime_suspect"

    def test_confirmed_digital(self, crime_store):
        """Active camera pointing at B confirms the digital alibi."""
        _seed_base_beliefs(crime_store, {"case.cctv_status": "active", "case.cctv_subject": "suspect_b"})
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_b.digital_alibi") == "confirmed"

    def test_digital_overrides_testimonial(self, crime_store):
        """Testimonial is broken, but digital is confirmed -> Final is confirmed -> Cleared."""
        _seed_base_beliefs(crime_store, {
            "suspect_a.home_evidence": "gun",
            "suspect_b.alibi_partner": "suspect_a",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b"
        })
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("suspect_b.testimonial_alibi") == "broken"
        assert crime_store.get_value("suspect_b.digital_alibi") == "confirmed"
        assert crime_store.get_value("suspect_b.final_alibi") == "confirmed"
        assert crime_store.get_value("suspect_b.status") == "cleared"


# =====================================================================
# THEORY AND LEAD SUSPECT
# =====================================================================


class TestTheoryAndLead:

    def test_solo_perpetrator(self, crime_store):
        """A is prime, B is cleared -> Solo Perpetrator -> A is lead."""
        _seed_base_beliefs(crime_store, {
            "suspect_a.home_evidence": "gun",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b"
        })
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("case.theory") == "solo_perpetrator"
        assert crime_store.get_value("case.lead_suspect") == "suspect_a"

    def test_collusion_both_motives(self, crime_store):
        """Both prime, both have verified motives -> Collusion -> both lead."""
        _seed_base_beliefs(crime_store, {
            "suspect_a.home_evidence": "gun",
            "suspect_b.alibi_partner": "suspect_a",
            "case.cctv_status": "corrupted",
            "case.warrant_status": True,
            "suspect_a.financial_records": "debt",
            "suspect_b.relation_to_victim": "enemy",
        })
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("case.theory") == "collusion"
        assert crime_store.get_value("case.lead_suspect") == "both"

    def test_collusion_mastermind_b(self, crime_store):
        """Both prime, but only B has a verified motive -> B is the mastermind / lead."""
        _seed_base_beliefs(crime_store, {
            "suspect_a.home_evidence": "gun",
            "case.warrant_status": False,
            "suspect_a.financial_records": "debt",  # But warrant is false, so no motive
            "suspect_b.relation_to_victim": "enemy",
        })
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("case.theory") == "collusion"
        assert crime_store.get_value("suspect_a.motive_verified") is False
        assert crime_store.get_value("suspect_b.motive_verified") is True
        assert crime_store.get_value("case.lead_suspect") == "suspect_b"

    def test_unsolved(self, crime_store):
        """Both cleared -> unsolved -> no lead."""
        _seed_base_beliefs(crime_store, {
            "suspect_a.home_evidence": "none",
            "case.cctv_status": "active",
            "case.cctv_subject": "suspect_b"
        })
        crime_store.resolve_all_dirty()
        assert crime_store.get_value("case.theory") == "unsolved"
        assert crime_store.get_value("case.lead_suspect") == "none"


# =====================================================================
# Full spec walkthrough (domains.md t=0 → t=1)
# =====================================================================


class TestSpecWalkthrough:

    def test_full_scenario(self, crime_store):
        """Reproduce the exact cascade example from domains.md."""
        store = crime_store

        # ── t=0: The Setup ──────────────
        _seed_base_beliefs(store, {
            "officer_smith.status": "active",
            "suspect_a.home_evidence": "gun",
            "suspect_a.evidence_logger": "officer_smith",
            "suspect_b.alibi_partner": "suspect_a",
            "case.cctv_status": "corrupted",
            "case.warrant_status": False,
            "suspect_a.financial_records": "clean",
            "suspect_b.relation_to_victim": "stranger"
        })
        store.resolve_all_dirty()

        # R1: officer is active → suspect_a.admissible_evidence = "gun"
        assert store.get_value("suspect_a.admissible_evidence") == "gun"
        # R2: gun is admissible → suspect_a.status = "prime_suspect"
        assert store.get_value("suspect_a.status") == "prime_suspect"
        # R3: partner is a prime suspect → suspect_b.testimonial_alibi = "broken"
        assert store.get_value("suspect_b.testimonial_alibi") == "broken"
        # R5: final alibi broken
        assert store.get_value("suspect_b.final_alibi") == "broken"
        # R6: alibi is broken → suspect_b.status = "prime_suspect"
        assert store.get_value("suspect_b.status") == "prime_suspect"
        # R9: both are prime suspects → case.theory = "collusion"
        assert store.get_value("case.theory") == "collusion"

        # ── t=1: The Procedural Plot Twist ─────────────────────────────
        log_before = len(store.revision_log)
        store.add_hypothesis("officer_smith.status", "suspended")

        # Check dirty propagation: changing smith affects evidence which bubbles all the way up to theory and lead
        assert "suspect_a.admissible_evidence" in store.dirty
        assert "suspect_a.status" in store.dirty
        assert "suspect_b.testimonial_alibi" in store.dirty
        assert "suspect_b.final_alibi" in store.dirty
        assert "suspect_b.status" in store.dirty
        assert "case.theory" in store.dirty
        assert "case.lead_suspect" in store.dirty

        store.resolve_all_dirty()

        # R1: officer is suspended → suspect_a.admissible_evidence = "none"
        assert store.get_value("suspect_a.admissible_evidence") == "none"
        # R2: no admissible evidence → suspect_a.status = "cleared"
        assert store.get_value("suspect_a.status") == "cleared"
        # R3: partner is cleared → suspect_b.testimonial_alibi = "confirmed"
        assert store.get_value("suspect_b.testimonial_alibi") == "confirmed"
        # R5: final alibi confirmed
        assert store.get_value("suspect_b.final_alibi") == "confirmed"
        # R6: alibi is confirmed → suspect_b.status = "cleared"
        assert store.get_value("suspect_b.status") == "cleared"
        # R9: both suspects cleared → case.theory = "unsolved"
        assert store.get_value("case.theory") == "unsolved"

        assert len(store.dirty) == 0

        # Verify audit trail captured it
        log_t1 = store.format_revision_log(since_index=log_before)
        assert "[update]" in log_t1
        assert "[derived]" in log_t1
