"""
Domain rules for Domain 4: Thorncrester Taxonomy (Ecosystem Trap)
Evaluates multi-layered masking (Adult, Social, Juvenile) and parasitic cascades.
"""

from typing import Any
from belief_store.store import BeliefStore

def setup_thorncrester_domain(store: BeliefStore) -> None:
    """Register all Thorncrester derivation rules with the belief store."""

    # ── BLOCK 1: THE ADULT MASKING LAYER ────────────────────

    def derive_ecological_stress(deps: dict[str, Any]) -> str:
        weather = deps.get("environment.weather_pattern")
        scarcity = deps.get("environment.food_scarcity")
        if weather == "drought" and scarcity is True:
            return "high"
        return "nominal"

    store.add_rule(
        name="ecological_stress",
        inputs=["environment.weather_pattern", "environment.food_scarcity"],
        output_key="adult_thorncrester.ecological_stress",
        derive_fn=derive_ecological_stress
    )

    def derive_expressed_diet(deps: dict[str, Any]) -> str:
        genetic_diet = deps.get("adult_thorncrester.genetic_diet")
        stress = deps.get("adult_thorncrester.ecological_stress")
        if stress == "high":
            return "scavenger"
        return genetic_diet

    store.add_rule(
        name="expressed_diet",
        inputs=["adult_thorncrester.genetic_diet", "adult_thorncrester.ecological_stress"],
        output_key="adult_thorncrester.expressed_diet",
        derive_fn=derive_expressed_diet
    )

    def derive_plumage_color(deps: dict[str, Any]) -> str:
        diet = deps.get("adult_thorncrester.expressed_diet")
        if diet == "scavenger":
            return "dull_grey"
        return "crimson"

    store.add_rule(
        name="plumage_color",
        inputs=["adult_thorncrester.expressed_diet"],
        output_key="adult_thorncrester.plumage_color",
        derive_fn=derive_plumage_color
    )

    # ── BLOCK 2: THE MACRO-SOCIAL MASKING LAYER ──────────────

    def derive_expressed_structure(deps: dict[str, Any]) -> str:
        genetic_struct = deps.get("thorncrester_flock.genetic_structure")
        stress = deps.get("adult_thorncrester.ecological_stress")
        if stress == "high":
            return "survival_swarm"
        return genetic_struct

    store.add_rule(
        name="expressed_structure",
        inputs=["thorncrester_flock.genetic_structure", "adult_thorncrester.ecological_stress"],
        output_key="thorncrester_flock.expressed_structure",
        derive_fn=derive_expressed_structure
    )

    def derive_territory_behavior(deps: dict[str, Any]) -> str:
        struct = deps.get("thorncrester_flock.expressed_structure")
        scarcity = deps.get("environment.food_scarcity")
        if struct == "survival_swarm" and scarcity is True:
            return "hyper_aggressive"
        return "peaceful"

    store.add_rule(
        name="territory_behavior",
        inputs=["thorncrester_flock.expressed_structure", "environment.food_scarcity"],
        output_key="thorncrester_flock.territory_behavior",
        derive_fn=derive_territory_behavior
    )

    # ── BLOCK 3: THE JUVENILE DEPENDENCY TRAP ────────────────

    def derive_metabolic_state(deps: dict[str, Any]) -> str:
        enzyme = deps.get("juvenile_thorncrester.digestive_enzyme")
        adult_diet = deps.get("adult_thorncrester.expressed_diet")
        if enzyme == "fructose_processor" and adult_diet != "frugivore":
            return "starving"
        return "thriving"

    store.add_rule(
        name="metabolic_state",
        inputs=["juvenile_thorncrester.digestive_enzyme", "adult_thorncrester.expressed_diet"],
        output_key="juvenile_thorncrester.metabolic_state",
        derive_fn=derive_metabolic_state
    )

    def derive_development(deps: dict[str, Any]) -> str:
        state = deps.get("juvenile_thorncrester.metabolic_state")
        if state == "starving":
            return "arrested"
        return "maturing"

    store.add_rule(
        name="development",
        inputs=["juvenile_thorncrester.metabolic_state"],
        output_key="juvenile_thorncrester.development",
        derive_fn=derive_development
    )

    # ── BLOCK 4: THE PARASITIC LAYER ─────────────────────────

    def derive_bloom_status(deps: dict[str, Any]) -> str:
        plumage = deps.get("adult_thorncrester.plumage_color")
        weather = deps.get("environment.weather_pattern")
        if plumage == "dull_grey" and weather == "drought":
            return "active_bloom"
        return "dormant"

    store.add_rule(
        name="bloom_status",
        inputs=["adult_thorncrester.plumage_color", "environment.weather_pattern"],
        output_key="feather_mite.bloom_status",
        derive_fn=derive_bloom_status
    )

    def derive_parasitic_load(deps: dict[str, Any]) -> str:
        bloom = deps.get("feather_mite.bloom_status")
        if bloom == "active_bloom":
            return "lethal"
        return "harmless"

    store.add_rule(
        name="parasitic_load",
        inputs=["feather_mite.bloom_status"],
        output_key="feather_mite.parasitic_load",
        derive_fn=derive_parasitic_load
    )

    # ── BLOCK 5: THE FINAL OUTCOME ───────────────────────────

    def derive_mortality_risk(deps: dict[str, Any]) -> str:
        parasites = deps.get("feather_mite.parasitic_load")
        territory = deps.get("thorncrester_flock.territory_behavior")
        if parasites == "lethal" or territory == "hyper_aggressive":
            return "critical"
        return "low"

    store.add_rule(
        name="mortality_risk",
        inputs=["feather_mite.parasitic_load", "thorncrester_flock.territory_behavior"],
        output_key="adult_thorncrester.mortality_risk",
        derive_fn=derive_mortality_risk
    )
