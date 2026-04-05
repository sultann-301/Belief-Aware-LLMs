"""
Unit tests for the Revised Thorncrester Taxonomy Domain (Ecosystem Trap)
Tests adult/social masking, juvenile dependency traps, and parasitic mortality cascades.
"""

import pytest
from belief_store.store import BeliefStore
from belief_store.domains.thorncrester import setup_thorncrester_domain

def _make_store() -> BeliefStore:
    s = BeliefStore()
    setup_thorncrester_domain(s)
    return s

def _seed_base(store: BeliefStore) -> None:
    defaults = {
        "environment.weather_pattern": "stable",
        "environment.food_scarcity": False,
        "adult_thorncrester.genetic_diet": "frugivore",
        "thorncrester_flock.genetic_structure": "matriarchal_pairs",
        "juvenile_thorncrester.digestive_enzyme": "fructose_processor",
    }
    for k, v in defaults.items():
        store.add_hypothesis(k, v)

def test_nominal_state():
    store = _make_store()
    _seed_base(store)
    store.resolve_all_dirty()
    
    assert store.get_value("adult_thorncrester.ecological_stress") == "nominal"
    assert store.get_value("adult_thorncrester.expressed_diet") == "frugivore"
    assert store.get_value("adult_thorncrester.plumage_color") == "crimson"
    assert store.get_value("thorncrester_flock.expressed_structure") == "matriarchal_pairs"
    assert store.get_value("thorncrester_flock.territory_behavior") == "peaceful"
    assert store.get_value("juvenile_thorncrester.metabolic_state") == "thriving"
    assert store.get_value("juvenile_thorncrester.development") == "maturing"
    assert store.get_value("feather_mite.bloom_status") == "dormant"
    assert store.get_value("adult_thorncrester.mortality_risk") == "low"

def test_ecosystem_trap_cascade():
    store = _make_store()
    _seed_base(store)
    store.resolve_all_dirty()
    
    # Trigger: Drought + Scarcity
    store.add_hypothesis("environment.weather_pattern", "drought")
    store.add_hypothesis("environment.food_scarcity", True)
    store.resolve_all_dirty()
    
    # Block 1: Adult Masking
    assert store.get_value("adult_thorncrester.ecological_stress") == "high"
    assert store.get_value("adult_thorncrester.expressed_diet") == "scavenger"
    assert store.get_value("adult_thorncrester.plumage_color") == "dull_grey"
    
    # Block 2: Social Masking
    assert store.get_value("thorncrester_flock.expressed_structure") == "survival_swarm"
    assert store.get_value("thorncrester_flock.territory_behavior") == "hyper_aggressive"
    
    # Block 3: Juvenile Starvation Trap (Parents eat scavenger, kids need fruit)
    assert store.get_value("juvenile_thorncrester.metabolic_state") == "starving"
    assert store.get_value("juvenile_thorncrester.development") == "arrested"
    
    # Block 4: Parasite Bloom (Drought + Dull Grey)
    assert store.get_value("feather_mite.bloom_status") == "active_bloom"
    assert store.get_value("feather_mite.parasitic_load") == "lethal"
    
    # Block 5: Mortality Risk
    assert store.get_value("adult_thorncrester.mortality_risk") == "critical"

def test_partial_stress_recovery():
    store = _make_store()
    _seed_base(store)
    store.add_hypothesis("environment.weather_pattern", "drought")
    store.add_hypothesis("environment.food_scarcity", True)
    store.resolve_all_dirty()
    assert store.get_value("adult_thorncrester.mortality_risk") == "critical"
    
    # Drought ends, but scarcity remains (maybe recovery takes time)
    # stress becomes nominal because R1 requires drought AND scarcity
    store.add_hypothesis("environment.weather_pattern", "stable")
    store.resolve_all_dirty()
    
    assert store.get_value("adult_thorncrester.ecological_stress") == "nominal"
    assert store.get_value("adult_thorncrester.expressed_diet") == "frugivore"
    assert store.get_value("adult_thorncrester.plumage_color") == "crimson"
    assert store.get_value("juvenile_thorncrester.metabolic_state") == "thriving"
    assert store.get_value("feather_mite.bloom_status") == "dormant"
    assert store.get_value("adult_thorncrester.mortality_risk") == "low"
    
    # Note: territory behavior is still hyper_aggressive? 
    # R5: expressed_structure("matriarchal_pairs") + scarcity(True) -> "peaceful"
    assert store.get_value("thorncrester_flock.territory_behavior") == "peaceful"
