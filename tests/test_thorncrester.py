"""
Unit tests for the Thorncrester Taxonomy Domain (Ecological Masking)
Tests the 10-turn unmasking trace, phenotypic plasticity, and non-monotonic cascade rules.
"""

import pytest

from belief_store.store import BeliefStore
from belief_store.domains.thorncrester import setup_thorncrester_domain


def _make_store() -> BeliefStore:
    s = BeliefStore()
    setup_thorncrester_domain(s)
    return s


def _seed_base(store: BeliefStore, overrides: dict = None) -> None:
    defaults = {
        "environment.weather_pattern": "stable",
        "environment.food_scarcity": False,
        "thorncrester.genetic_diet": "frugivore",
        "thorncrester.genetic_plumage": "crimson",
    }
    if overrides:
        defaults.update(overrides)

    for k, v in defaults.items():
        store.add_hypothesis(k, v)


# =====================================================================
# INDIVIDUAL RULE BLOCKS
# =====================================================================


class TestStressLayer:
    def test_nominal(self):
        store = _make_store()
        _seed_base(store, {"environment.weather_pattern": "stable", "environment.food_scarcity": False})
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.ecological_stress") == "nominal"

    def test_drought_without_scarcity(self):
        store = _make_store()
        _seed_base(store, {"environment.weather_pattern": "drought", "environment.food_scarcity": False})
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.ecological_stress") == "nominal"
        
    def test_drought_with_scarcity(self):
        store = _make_store()
        _seed_base(store, {"environment.weather_pattern": "drought", "environment.food_scarcity": True})
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.ecological_stress") == "high"

    def test_flood_automatic(self):
        store = _make_store()
        _seed_base(store, {"environment.weather_pattern": "flood", "environment.food_scarcity": False})
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.ecological_stress") == "high"


class TestPhenotypicMasking:
    def test_no_masking(self):
        store = _make_store()
        _seed_base(store, {"thorncrester.genetic_diet": "insectivore"})
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.expressed_diet") == "insectivore"
        
    def test_high_stress_masking(self):
        store = _make_store()
        _seed_base(store, {"thorncrester.genetic_diet": "frugivore", "environment.weather_pattern": "flood"})
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.expressed_diet") == "scavenger"
        assert store.get_value("thorncrester.expressed_plumage") == "dull_grey"

    def test_plumage_follows_diet(self):
        store = _make_store()
        _seed_base(store, {"thorncrester.genetic_plumage": "azure", "environment.weather_pattern": "flood"})
        store.resolve_all_dirty()
        # Stress -> Scavenger -> Dull Grey. It masks the Azure.
        assert store.get_value("thorncrester.expressed_plumage") == "dull_grey"


class TestCascades:
    def test_safe_growing(self):
        store = _make_store()
        _seed_base(store)
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.mating_viability") is True
        assert store.get_value("thorncrester.population_trend") == "growing"
        assert store.get_value("thorncrester.conservation_status") == "safe"
        assert store.get_value("thorncrester.intervention_plan") == "none"

    def test_critical_scavenger_intervention(self):
        store = _make_store()
        # High stress = Scavenger -> Dull Grey -> Extinct
        _seed_base(store, {"environment.weather_pattern": "drought", "environment.food_scarcity": True})
        store.resolve_all_dirty()
        
        assert store.get_value("thorncrester.mating_viability") is False
        assert store.get_value("thorncrester.population_trend") == "crashing"
        assert store.get_value("thorncrester.conservation_status") == "critical"
        assert store.get_value("thorncrester.intervention_plan") == "supplemental_carrion_drops"

    def test_declining_vulnerable(self):
         store = _make_store()
         # Stable weather + false scarcity = nominal stress... BUT if plumage is somehow grey
         _seed_base(store, {"thorncrester.genetic_plumage": "dull_grey", "environment.weather_pattern": "stable"})
         store.resolve_all_dirty()
         
         assert store.get_value("thorncrester.mating_viability") is False
         # Scarcity is false, so trend is just declining, not crashing
         assert store.get_value("thorncrester.population_trend") == "declining"
         assert store.get_value("thorncrester.conservation_status") == "vulnerable"
         assert store.get_value("thorncrester.intervention_plan") == "habitat_protection"


# =====================================================================
# FULL WALKTHROUGH AND REVISIONS
# =====================================================================

class TestWalkthrough:
    def test_masking_unmasking_cycle(self):
        store = _make_store()
        
        # t=0: Nominal Base
        _seed_base(store)
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.ecological_stress") == "nominal"
        assert store.get_value("thorncrester.expressed_diet") == "frugivore"
        assert store.get_value("thorncrester.expressed_plumage") == "crimson"
        assert store.get_value("thorncrester.intervention_plan") == "none"
        
        # t=1: Masking Event (Drought + Scarcity)
        store.add_hypothesis("environment.weather_pattern", "drought")
        store.add_hypothesis("environment.food_scarcity", True)
        
        assert "thorncrester.ecological_stress" in store.dirty
        
        store.resolve_all_dirty()
        assert store.get_value("thorncrester.ecological_stress") == "high"
        assert store.get_value("thorncrester.expressed_diet") == "scavenger"
        assert store.get_value("thorncrester.expressed_plumage") == "dull_grey"
        assert store.get_value("thorncrester.intervention_plan") == "supplemental_carrion_drops"
        
        # t=2: Unmasking (Rains return, but still scarcity temporarily)
        store.add_hypothesis("environment.weather_pattern", "stable")
        store.resolve_all_dirty()
        
        # stress = nominal because drought is gone
        assert store.get_value("thorncrester.ecological_stress") == "nominal"
        # genotype unmasks
        assert store.get_value("thorncrester.expressed_diet") == "frugivore" 
        assert store.get_value("thorncrester.expressed_plumage") == "crimson"
        # Mating viable again!
        assert store.get_value("thorncrester.mating_viability") is True
        # Since viability=True, population trend ignores scarcity and defaults to growing
        assert store.get_value("thorncrester.population_trend") == "growing"
        assert store.get_value("thorncrester.intervention_plan") == "none"
