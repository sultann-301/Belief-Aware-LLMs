"""
Unit tests for the alien clinic domain rules (domains.md spec Domain 2).

Covers:
  - Specific Rule behaviors (R1 - R10)
  - Full revision walkthrough (t=0 → t=1 from spec)
  - Handling of strict "fatal_to_patient" conditionals and priority lists.
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
        "patient.symptoms": [],
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
        assert clinic_store.get_value("treatment.zyxostin_phase") == "plasma"
        assert clinic_store.get_value("treatment.filinan_phase") == "plasma"
        assert clinic_store.get_value("treatment.snevox_phase") == "vapor"

    def test_xenon(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.dominant_gas": "xenon"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("treatment.zyxostin_phase") == "crystalline"
        assert clinic_store.get_value("treatment.filinan_phase") == "vapor"
        assert clinic_store.get_value("treatment.snevox_phase") == "vapor"

    def test_chlorine(self, clinic_store):
        _seed_base_beliefs(clinic_store, {"atmosphere.dominant_gas": "chlorine"})
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("treatment.zyxostin_phase") == "crystalline"
        assert clinic_store.get_value("treatment.filinan_phase") == "plasma"
        assert clinic_store.get_value("treatment.snevox_phase") == "liquid"


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
        assert clinic_store.get_value("treatment.zyxostin_danger_level") == "fatal_to_patient" # Glerps + Zyxostin
        assert clinic_store.get_value("treatment.filinan_danger_level") == "fatal_to_patient" # Plasma + Filinan
        assert clinic_store.get_value("treatment.snevox_danger_level") == "safe"
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
        assert clinic_store.get_value("treatment.filinan_danger_level") == "fatal_to_patient" # Yorp + Filinan
        assert clinic_store.get_value("treatment.zyxostin_danger_level") == "safe"
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
        assert clinic_store.get_value("treatment.snevox_danger_level") == "fatal_to_patient"
        assert clinic_store.get_value("treatment.filinan_danger_level") == "fatal_to_patient" 
        assert clinic_store.get_value("treatment.zyxostin_danger_level") == "safe"
        assert clinic_store.get_value("treatment.active_prescription") == "zyxostin"

    def test_volatile_condition(self, clinic_store):
        # High pressure -> volatile -> all lethal. We use Yorp + methane so 
        # Zyxostin doesn't explode for Yorp, Snevox doesn't explode for Yorp.
        # But Filinan explodes for Yorp. 
        # Wait, if Filinan explodes for Yorp, it will be Symbiotic! Let's test the Singularity!
        _seed_base_beliefs(clinic_store, {
            "atmosphere.ambient_pressure": 5.5,
            "patient.organism_type": "Yorp"
        })
        clinic_store.resolve_all_dirty()
        assert clinic_store.get_value("patient.organ_integrity") == "volatile"
        assert clinic_store.get_value("treatment.zyxostin_danger_level") == "fatal_to_patient" # Condition-based
        assert clinic_store.get_value("treatment.filinan_danger_level") == "symbiotic" # Singularity! Yorp + filinan + volatile
        assert clinic_store.get_value("treatment.snevox_danger_level") == "fatal_to_patient" # Condition-based
        assert clinic_store.get_value("treatment.active_prescription") == "filinan"
        assert clinic_store.get_value("patient.recovery_prospect") == "miraculous"

    def test_symptoms_priority_override(self, clinic_store):
        _seed_base_beliefs(clinic_store, {
            "patient.organism_type": "Glerps",
            "patient.symptoms": ["fever", "spasms"],
            "atmosphere.ambient_pressure": 3.5,
            "atmosphere.dominant_gas": "xenon" 
            # xenon -> zyxostin=crystalline (safe), filinan=vapor (safe), snevox=vapor (safe)
        })
        clinic_store.resolve_all_dirty()
        # Normal Glerps priority is filinan -> zyxostin -> snevox
        # With fever and spasms it is snevox -> zyxostin -> filinan
        assert clinic_store.get_value("treatment.active_prescription") == "snevox"


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
        store.add_hypothesis("patient.symptoms", [])
        store.add_hypothesis("atmosphere.ambient_pressure", 3.5)
        store.add_hypothesis("atmosphere.dominant_gas", "methane")
        store.resolve_all_dirty()

        # R1: 3.5 > 3.0 -> brittle
        assert store.get_value("patient.organ_integrity") == "brittle"
        # R3: danger_levels
        assert store.get_value("treatment.zyxostin_danger_level") == "fatal_to_patient"
        assert store.get_value("treatment.filinan_danger_level") == "fatal_to_patient"
        assert store.get_value("treatment.snevox_danger_level") == "safe"
        # R4: prescription
        assert store.get_value("treatment.active_prescription") == "snevox"
        assert store.get_value("clinic.billing_tier") == "class_omega"

        # ── t=1: Inject symptoms ──────────────
        store.add_hypothesis("patient.symptoms", ["fever", "spasms"])
        store.resolve_all_dirty()
        
        # Priority shifts to snevox, which is safe, so active prescription remains "snevox"
        assert store.get_value("treatment.active_prescription") == "snevox"

        # ── t=2: Pressure spike ─────────────────────────────
        store.add_hypothesis("atmosphere.ambient_pressure", 4.5)
        # Should propagate to a bunch of things
        store.resolve_all_dirty()

        # R1 -> volatile
        assert store.get_value("patient.organ_integrity") == "volatile"
        # R3 -> Singularity on zyxostin!
        assert store.get_value("treatment.zyxostin_danger_level") == "symbiotic"
        assert store.get_value("treatment.filinan_danger_level") == "fatal_to_patient"
        assert store.get_value("treatment.snevox_danger_level") == "fatal_to_patient"
        # R4 -> Singularity override
        assert store.get_value("treatment.active_prescription") == "zyxostin"
        # R9 -> miraculous
        assert store.get_value("patient.recovery_prospect") == "miraculous"
        # R10 -> standard tier
        assert store.get_value("clinic.billing_tier") == "class_standard"
