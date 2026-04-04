"""
Domain rules for Domain 4: Thorncrester Taxonomy (Ecological Masking)
Evaluates non-monotonic inheritance and latent beliefs via phenotypic masking.
"""

from typing import Any
from belief_store.store import BeliefStore

def setup_thorncrester_domain(store: BeliefStore) -> None:
    """Register all Thorncrester derivation rules with the belief store."""

    # ── BLOCK 1: THE ENVIRONMENTAL STRESS LAYER ───────────────

    def derive_ecological_stress(deps: dict[str, Any]) -> Any:
        weather = deps.get("environment.weather_pattern")
        scarcity = deps.get("environment.food_scarcity")

        if weather == "drought" and scarcity is True:
            return "high"
        if weather == "flood":
            return "high"
        return "nominal"

    store.add_rule(
        name="ecological_stress",
        inputs=["environment.weather_pattern", "environment.food_scarcity"],
        output_key="thorncrester.ecological_stress",
        derive_fn=derive_ecological_stress
    )

    # ── BLOCK 2: PHENOTYPIC PLASTICITY (The Masking Layer) ────

    def derive_expressed_diet(deps: dict[str, Any]) -> Any:
        genetic_diet = deps.get("thorncrester.genetic_diet")
        stress = deps.get("thorncrester.ecological_stress")

        if stress == "high":
            return "scavenger"
        return genetic_diet

    store.add_rule(
        name="expressed_diet",
        inputs=["thorncrester.genetic_diet", "thorncrester.ecological_stress"],
        output_key="thorncrester.expressed_diet",
        derive_fn=derive_expressed_diet
    )


    def derive_expressed_plumage(deps: dict[str, Any]) -> Any:
        genetic_plumage = deps.get("thorncrester.genetic_plumage")
        expressed_diet = deps.get("thorncrester.expressed_diet")

        if expressed_diet == "scavenger":
            return "dull_grey"
        return genetic_plumage

    store.add_rule(
        name="expressed_plumage",
        inputs=["thorncrester.genetic_plumage", "thorncrester.expressed_diet"],
        output_key="thorncrester.expressed_plumage",
        derive_fn=derive_expressed_plumage
    )

    # ── BLOCK 3: BEHAVIORAL CASCADES ──────────────────────────

    def derive_primary_forage(deps: dict[str, Any]) -> Any:
        expressed_diet = deps.get("thorncrester.expressed_diet")

        if expressed_diet == "frugivore":
            return "verath_berries"
        if expressed_diet == "insectivore":
            return "thorn_beetles"
        if expressed_diet == "scavenger":
            return "carrion"
        return "unknown"

    store.add_rule(
        name="primary_forage",
        inputs=["thorncrester.expressed_diet"],
        output_key="thorncrester.primary_forage",
        derive_fn=derive_primary_forage
    )


    def derive_mating_viability(deps: dict[str, Any]) -> Any:
        expressed_plumage = deps.get("thorncrester.expressed_plumage")
        stress = deps.get("thorncrester.ecological_stress")

        if expressed_plumage == "dull_grey" or stress == "high":
            return False
        return True

    store.add_rule(
        name="mating_viability",
        inputs=["thorncrester.expressed_plumage", "thorncrester.ecological_stress"],
        output_key="thorncrester.mating_viability",
        derive_fn=derive_mating_viability
    )

    # ── BLOCK 4: POPULATION & CONSERVATION ────────────────────

    def derive_population_trend(deps: dict[str, Any]) -> Any:
        viability = deps.get("thorncrester.mating_viability")
        scarcity = deps.get("environment.food_scarcity")

        if viability is False and scarcity is True:
            return "crashing"
        if viability is False and scarcity is False:
            return "declining"
        return "growing"

    store.add_rule(
        name="population_trend",
        inputs=["thorncrester.mating_viability", "environment.food_scarcity"],
        output_key="thorncrester.population_trend",
        derive_fn=derive_population_trend
    )


    def derive_conservation_status(deps: dict[str, Any]) -> Any:
        trend = deps.get("thorncrester.population_trend")

        if trend == "crashing":
            return "critical"
        if trend == "declining":
            return "vulnerable"
        return "safe"

    store.add_rule(
        name="conservation_status",
        inputs=["thorncrester.population_trend"],
        output_key="thorncrester.conservation_status",
        derive_fn=derive_conservation_status
    )


    def derive_intervention_plan(deps: dict[str, Any]) -> Any:
        status = deps.get("thorncrester.conservation_status")
        expressed_diet = deps.get("thorncrester.expressed_diet")

        if status == "critical" and expressed_diet == "scavenger":
            return "supplemental_carrion_drops"
        if status == "critical":
            return "captive_breeding"
        if status == "vulnerable":
            return "habitat_protection"
        return "none"

    store.add_rule(
        name="intervention_plan",
        inputs=["thorncrester.conservation_status", "thorncrester.expressed_diet"],
        output_key="thorncrester.intervention_plan",
        derive_fn=derive_intervention_plan
    )
