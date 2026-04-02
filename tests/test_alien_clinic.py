"""
Unit tests for the alien clinic domain rules (domains.md spec Domain 2).

Covers:
  - Specific Rule behaviors (R1 - R10)
  - Full revision walkthrough (t=0 → t=1 from spec)
  - Handling of strict "LETHAL" conditionals and priority lists.
"""

import pytest

from belief_store.store import BeliefStore
from belief_store.domains.alien_clinic import setup_alien_clinic_domain


# ── Helpers ──────────────────────────────────────────────────────────

def _make_clinic_store() -> BeliefStore:
    s = BeliefStore()
    setup_alien_clinic_domain(s)
    return s


def _seed_base_beliefs(store: BeliefStore, overrides: dict | None = None) -> None:
    defaults = {
        "patient.organism_type": "Glerps",
        "atmosphere.ambient_pressure": 3.5,
        "atmosphere.dominant_gas": "methane",
    }
    if overrides:
        defaults.update(overrides)

    for key, value in defaults.items():
        store.add_hypothesis(key, value)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def store():
    return BeliefStore()


@pytest.fixture
def clinic_store():
    return _make_clinic_store()


@pytest.fixture
def resolved_clinic_store():
    s = _make_clinic_store()
    _seed_base_beliefs(s)
    s.resolve_all_dirty()
    return s


# =====================================================================
# R1: Organ Integrity
# =====================================================================

class TestOrganIntegrity:
    def test_stable(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.ambient_pressure": 2.0})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.organ_integrity") == "stable"

    def test_brittle(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.ambient_pressure": 3.1})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.organ_integrity") == "brittle"

    def test_glerps_volatile(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.ambient_pressure": 4.1, "patient.organism_type": "Glerps"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.organ_integrity") == "volatile"

    def test_yorp_volatile(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.ambient_pressure": 5.1, "patient.organism_type": "Yorp"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.organ_integrity") == "volatile"


# =====================================================================
# R2: Molecular Phases
# =====================================================================

class TestMolecularPhases:
    def test_methane(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.dominant_gas": "methane"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("zyxostin.phase") == "plasma"
        assert clinic_store.get_value("filinan.phase") == "plasma"
        assert clinic_store.get_value("snevox.phase") == "vapor"

    def test_xenon(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.dominant_gas": "xenon"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("zyxostin.phase") == "crystalline"
        assert clinic_store.get_value("filinan.phase") == "vapor"
        assert clinic_store.get_value("snevox.phase") == "vapor"

    def test_chlorine(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.dominant_gas": "chlorine"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("zyxostin.phase") == "crystalline"
        assert clinic_store.get_value("filinan.phase") == "plasma"
        assert clinic_store.get_value("snevox.phase") == "liquid"


# =====================================================================
# R3 & R4: Hazards & Prescription
# =====================================================================

class TestHazardsAndPrescription:
    def test_glerps_explode_constraint(self, clinic_store):
        # Glerps + Zyxostin -> Lethal. Filinan is normally preferred, but methane -> Filinan=plasma -> Lethal.
        # So Snevox is chosen.
        _seed_base_beliefs(clinic_store, {
            "patient.organism_type": "Glerps",
            "atmosphere.dominant_gas": "methane",
            "atmosphere.ambient_pressure": 3.5  # brittle (safe)
        })
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("zyxostin.hazard") == "LETHAL" # Glerps + Zyxostin
        assert clinic_store.get_value("filinan.hazard") == "LETHAL" # Plasma + Filinan
        assert clinic_store.get_value("snevox.hazard") == "safe"
        assert clinic_store.get_value("treatment.active_prescription") == "snevox"

    def test_yorp_explode_constraint(self, clinic_store):
        # Yorp + Filinan -> Lethal. Priority: Zyxostin -> Snevox -> Filinan.
        # Gas: xenon -> Zyxostin=crystalline, Filinan=vapor, Snevox=vapor.
        _seed_base_beliefs(clinic_store, {
            "patient.organism_type": "Yorp",
            "atmosphere.dominant_gas": "xenon",
            "atmosphere.ambient_pressure": 2.0
        })
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("filinan.hazard") == "LETHAL" # Yorp + Filinan
        assert clinic_store.get_value("zyxostin.hazard") == "safe"
        assert clinic_store.get_value("treatment.active_prescription") == "zyxostin"

    def test_qwerl_vapor_constraint(self, clinic_store):
        # Qwerl + Snevox -> Lethal. 
        # Gas: xenon -> Snevox=vapor -> Lethal for Qwerl anyway, but the Qwerl+Snevox rule also explodes.
        # Gas: methane -> Snevox=vapor -> Lethal for Qwerl. Phase=plasma -> Filinan=Lethal.
        # Priority for Qwerl: Snevox -> Zyxostin -> Filinan.
        _seed_base_beliefs(clinic_store, {
            "patient.organism_type": "Qwerl",
            "atmosphere.dominant_gas": "methane",
            "atmosphere.ambient_pressure": 2.0
        })
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("snevox.hazard") == "LETHAL"
        assert clinic_store.get_value("filinan.hazard") == "LETHAL" 
        assert clinic_store.get_value("zyxostin.hazard") == "safe"
        assert clinic_store.get_value("treatment.active_prescription") == "zyxostin"

    def test_volatile_condition(self, clinic_store):
        # High pressure -> volatile -> all lethal
        _seed_base_beliefs(clinic_store, {
            "atmosphere.ambient_pressure": 5.5,
            "patient.organism_type": "Yorp"
        })
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.organ_integrity") == "volatile"
        assert clinic_store.get_value("zyxostin.hazard") == "LETHAL"
        assert clinic_store.get_value("filinan.hazard") == "LETHAL"
        assert clinic_store.get_value("snevox.hazard") == "LETHAL"
        assert clinic_store.get_value("treatment.active_prescription") == "none"


# =====================================================================
# R5 - R10: Late Stage Derivations
# =====================================================================

class TestLateStageDerivations:
    def test_quarantine_required(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.dominant_gas": "chlorine", "patient.organism_type": "Qwerl"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.quarantine_required") is True

        _seed_base_beliefs(clinic_store, {"atmosphere.dominant_gas": "methane", "patient.organism_type": "Yorp"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.quarantine_required") is True

    def test_billing_tier(self, clinic_store):
        # Snevox prescription triggers telepathic -> psionic_handler -> class_omega
        _seed_base_beliefs(clinic_store, {
            "patient.organism_type": "Glerps",
            "atmosphere.dominant_gas": "methane",
            "atmosphere.ambient_pressure": 3.5
        })
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("treatment.active_prescription") == "snevox"
        assert clinic_store.get_value("patient.sensory_status") == "telepathic"
        assert clinic_store.get_value("medical.staff_requirement") == "psionic_handler"
        assert clinic_store.get_value("clinic.billing_tier") == "class_omega"


# =====================================================================
# Full spec walkthrough (domains.md t=0 → t=1)
# =====================================================================

class TestSpecWalkthrough:
    def test_full_scenario(self, clinic_store):
        """Reproduce the exact example from domains.md."""
        store = clinic_store

        # ── t=0: Initial ──────────────
        store.add_hypothesis("patient.organism_type", "Glerps")
        store.add_hypothesis("atmosphere.ambient_pressure", 3.5)
        store.add_hypothesis("atmosphere.dominant_gas", "methane")
        store.resolve_all_dirty()

        # R1: 3.5 > 3.0 -> brittle
        assert store.get_value("patient.organ_integrity") == "brittle"
        # R2: phases
        assert store.get_value("zyxostin.phase") == "plasma"
        assert store.get_value("filinan.phase") == "plasma"
        assert store.get_value("snevox.phase") == "vapor"
        # R3: hazards
        assert store.get_value("zyxostin.hazard") == "LETHAL"
        assert store.get_value("filinan.hazard") == "LETHAL"
        assert store.get_value("snevox.hazard") == "safe"
        # R4: prescription
        assert store.get_value("treatment.active_prescription") == "snevox"
        # R5: sensory
        assert store.get_value("patient.sensory_status") == "telepathic"
        # R8: staff
        assert store.get_value("medical.staff_requirement") == "psionic_handler"
        # R10: billing
        assert store.get_value("clinic.billing_tier") == "class_omega"

        # ── t=1: Pressure spike ─────────────────────────────
        store.add_hypothesis("atmosphere.ambient_pressure", 4.5)
        # Should propagate to a bunch of things
        store.resolve_all_dirty()

        # R1 -> volatile
        assert store.get_value("patient.organ_integrity") == "volatile"
        # R3 -> ALL LETHAL
        assert store.get_value("zyxostin.hazard") == "LETHAL"
        assert store.get_value("filinan.hazard") == "LETHAL"
        assert store.get_value("snevox.hazard") == "LETHAL"
        # R4 -> none
        assert store.get_value("treatment.active_prescription") == "none"
        # R7 -> duration = 0
        assert store.get_value("treatment.duration_cycles") == 0
        # R9 -> terminal
        assert store.get_value("patient.recovery_prospect") == "terminal"
