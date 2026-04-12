"""
Extended Evaluation Scenarios for the Thorncrester Domain.

Includes 10 turns each for: Negation, 1-Hop, 2-Hop, 3-Hop, 4-Hop, and Belief Maintenance.
"""

# =====================================================================
# 1. NEGATION SET (10 Turns)
# Target: Negative phrasing while retrieving the correct factual state.
# =====================================================================
THORNCRESTER_NEGATION_TURNS = [
    {
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {},
        "question": "Is it false that the ecological stress is nominal?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "B" # Stress is nominal, so false that it is nominal is 'False'.
    },
    {
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # High stress -> diet=scavenger -> plumage=dull_grey
        "question": "Is it inaccurate to say the plumage color is crimson?",
        "options": {"A": "Yes", "B": "No", "C": "Maybe"},
        "correct": "A" # It's dull_grey. So crimson is inaccurate.
    },
    {
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # High stress -> structure=survival_swarm + scarcity-> hyper_aggressive
        "question": "Is it untrue that the territory behavior is peaceful?",
        "options": {"A": "True", "B": "False", "C": "None"},
        "correct": "A" # It is hyper_aggressive, so saying it's peaceful is untrue.
    },
    {
        "attributes": ["juvenile_thorncrester.metabolic_state"],
        "beliefs": {"adult_thorncrester.genetic_diet": "insectivore"},
        # stable -> diet=insectivore. Juv=fructose -> starving
        "question": "Is the assertion 'the juvenile is thriving' incorrect?",
        "options": {"A": "Yes", "B": "No", "C": "Partially"},
        "correct": "A" # They are starving.
    },
    {
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # hyper_aggressive + lethal mites -> critical
        "question": "Is it false that the mortality risk is low for the affected flock?",
        "options": {"A": "Yes", "B": "No", "C": "Unknown"},
        "correct": "A"
    },
    {
        "attributes": ["feather_mite.bloom_status"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # drought + dull_grey -> active_bloom
        "question": "Is it not the case that the parasite bloom is dormant?",
        "options": {"A": "True", "B": "False", "C": "Maybe"},
        "correct": "A"
    },
    {
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"juvenile_thorncrester.digestive_enzyme": "general_processor"},
        # thriving -> maturing
        "question": "Is it incorrect to claim the development is arrested?",
        "options": {"A": "Yes", "B": "No", "C": "Unsure"},
        "correct": "A" # It is maturing.
    },
    {
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # active_bloom -> lethal
        "question": "Is it false that the parasitic load is harmless?",
        "options": {"A": "Yes", "B": "No", "C": "Depending"},
        "correct": "A" # It is lethal.
    },
    {
        "attributes": ["adult_thorncrester.expressed_diet"],
        "beliefs": {"environment.weather_pattern": "stable"},
        "question": "Is it untrue that the expressed diet is a scavenger?",
        "options": {"A": "True", "B": "False", "C": "Missing"},
        "correct": "A" # It is frugivore. 
    },
    {
        "attributes": ["thorncrester_flock.expressed_structure"],
        "beliefs": {"environment.weather_pattern": "stable"},
        "question": "Is it incorrect to say the structure is survival_swarm?",
        "options": {"A": "Yes", "B": "No", "C": "N/A"},
        "correct": "A"
    }
]

# =====================================================================
# 2. 1-HOP SET (10 Turns)
# Target: Direct derivations (Parent -> Child)
# =====================================================================
THORNCRESTER_1HOP_TURNS = [
    {
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        "question": "With a drought and food scarcity officially starting, what is the stress level?",
        "options": {"A": "high", "B": "nominal", "C": "critical"},
        "correct": "A"
    },
    {
        "attributes": ["adult_thorncrester.expressed_diet"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high"},
        "question": "If ecological stress hits high, what does the expressed diet instantly become?",
        "options": {"A": "scavenger", "B": "frugivore", "C": "insectivore"},
        "correct": "A"
    },
    {
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {"adult_thorncrester.expressed_diet": "scavenger"},
        "question": "If they are forced to scavenge, what happens to their plumage?",
        "options": {"A": "dull_grey", "B": "crimson", "C": "molting"},
        "correct": "A"
    },
    {
        "attributes": ["thorncrester_flock.expressed_structure"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high"},
        "question": "High stress alters the flock setup. What is the new expressed structure?",
        "options": {"A": "survival_swarm", "B": "matriarchal_pairs", "C": "solitary"},
        "correct": "A"
    },
    {
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {"thorncrester_flock.expressed_structure": "survival_swarm", "environment.food_scarcity": True},
        "question": "With a survival swarm active during scarcity, what is the territory behavior?",
        "options": {"A": "hyper_aggressive", "B": "peaceful", "C": "defensive"},
        "correct": "A"
    },
    {
        "attributes": ["juvenile_thorncrester.metabolic_state"],
        "beliefs": {"adult_thorncrester.expressed_diet": "scavenger"},
        "question": "If adults scavenge but young process fructose, what is the juvenile state?",
        "options": {"A": "starving", "B": "thriving", "C": "stable"},
        "correct": "A"
    },
    {
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"juvenile_thorncrester.metabolic_state": "starving"},
        "question": "A starving juvenile has what development prospect?",
        "options": {"A": "arrested", "B": "maturing", "C": "unknown"},
        "correct": "A"
    },
    {
        "attributes": ["feather_mite.bloom_status"],
        "beliefs": {"adult_thorncrester.plumage_color": "dull_grey", "environment.weather_pattern": "drought"},
        "question": "Drought conditions with dull_grey plumage - what is the mite bloom status?",
        "options": {"A": "active_bloom", "B": "dormant", "C": "lethal"},
        "correct": "A"
    },
    {
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {"feather_mite.bloom_status": "active_bloom"},
        "question": "An active bloom creates what parasitic load on the hosts?",
        "options": {"A": "lethal", "B": "harmless", "C": "moderate"},
        "correct": "A"
    },
    {
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"feather_mite.parasitic_load": "lethal"},
        "question": "When the parasitic load is lethal, what is the adult mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "high"},
        "correct": "A"
    }
]

# =====================================================================
# 3. 2-HOP SET (10 Turns)
# Target: Two levels of indirection.
# =====================================================================
THORNCRESTER_2HOP_TURNS = [
    {   # Weather+Scarcity(1) -> Stress(2) -> ExpDiet / ExpStruct
        "attributes": ["adult_thorncrester.expressed_diet"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        "question": "With a drought hitting alongside food scarcity, what is the expressed diet?",
        "options": {"A": "scavenger", "B": "frugivore", "C": "omnivore"},
        "correct": "A"
    },
    {   # GenDiet(1) -> ExpDiet(2) -> Plumage
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {"adult_thorncrester.genetic_diet": "scavenger"},
        # stress=nominal -> exp=scavenger -> grey
        "question": "If a variant has a genetic diet of scavenger by default, what is their plumage?",
        "options": {"A": "dull_grey", "B": "crimson", "C": "azure"},
        "correct": "A"
    },
    {   # GenStruct(1) -> ExpStruct(2) -> Territory
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {"thorncrester_flock.genetic_structure": "survival_swarm", "environment.food_scarcity": True},
        # stress=nominal -> exp=survival_swarm. swarm+scarcity -> aggressive
        "question": "Genetic swarmers paired with food scarcity display what territory behavior?",
        "options": {"A": "hyper_aggressive", "B": "peaceful", "C": "defensive"},
        "correct": "A"
    },
    {   # ExpDiet(1) -> Metabolism(2) -> Development
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"adult_thorncrester.expressed_diet": "scavenger"},
        # scav + fructose -> starving -> arrested
        "question": "If adults shift to scavengers, what happens to youth development?",
        "options": {"A": "arrested", "B": "maturing", "C": "accelerated"},
        "correct": "A"
    },
    {   # Plumage(1) -> Bloom(2) -> Load
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {"adult_thorncrester.plumage_color": "dull_grey", "environment.weather_pattern": "drought"},
        # active_bloom -> lethal
        "question": "Dull_grey birds in a drought trigger a bloom. What is the parasitic load?",
        "options": {"A": "lethal", "B": "harmless", "C": "low"},
        "correct": "A"
    },
    {   # Bloom(1) -> Load(2) -> Mortality
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"feather_mite.bloom_status": "active_bloom"},
        # lethal -> critical
        "question": "An active bloom is present. What is the mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "moderate"},
        "correct": "A"
    },
    {   # Territory(1) -> Mortality(2)  Wait, Territory is 1 hop from Mortality.
        # How about ExpStruct(1) -> Territory(2) -> Mortality(3)  <- 3 hop
        # Stress(1) -> ExpStruct(2) -> Territory
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high", "environment.food_scarcity": True},
        # high obj -> swarm -> aggressive
        "question": "Forced into high stress and scarcity, how does the flock act?",
        "options": {"A": "hyper_aggressive", "B": "peaceful", "C": "fearful"},
        "correct": "A"
    },
    {   # Enzmye(1) -> Metabolism(2) -> Development
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"juvenile_thorncrester.digestive_enzyme": "fructose_processor", "adult_thorncrester.expressed_diet": "scavenger"},
        # fructose processor + scavenger diet -> starving -> arrested
        "question": "A juvenile needs fructose but adults shifted to scavenging. Growth status?",
        "options": {"A": "arrested", "B": "maturing", "C": "thriving"},
        "correct": "A"
    },
    {   # Stress(1) -> ExpDiet(2) -> Plumage
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high"},
        "question": "High stress masks the diet. What color is the plumage?",
        "options": {"A": "dull_grey", "B": "crimson", "C": "mixed"},
        "correct": "A"
    },
    {   # GenDiet(1) -> ExpDiet(2) -> Metabolism
        "attributes": ["juvenile_thorncrester.metabolic_state"],
        "beliefs": {"adult_thorncrester.genetic_diet": "scavenger"},
        # stress=nom -> exp=scavenger -> Juv(fructose) -> starving
        "question": "A scavenger genetic lineage trying to feed fructose youths causes what metabolic state?",
        "options": {"A": "starving", "B": "thriving", "C": "arrested"},
        "correct": "A"
    }
]

# =====================================================================
# 4. 3-HOP SET (10 Turns)
# Target: Three levels of indirection.
# =====================================================================
THORNCRESTER_3HOP_TURNS = [
    {   # Weather(1) -> Stress(2) -> ExpDiet(3) -> Plumage Phase
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        "question": "Drought and scarcity strike together. What color are their feathers?",
        "options": {"A": "dull_grey", "B": "crimson", "C": "azure"},
        "correct": "A"
    },
    {   # Weather(1) -> Stress(2) -> ExpStruct(3) -> Territory
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # hyper aggressive
        "question": "Under drought and scarcity, what happens to their flock territory behavior?",
        "options": {"A": "hyper_aggressive", "B": "peaceful", "C": "scattered"},
        "correct": "A"
    },
    {   # Stress(1) -> ExpDiet(2) -> Metabolism(3) -> Development
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high"},
        # scav -> starving -> arrested
        "question": "With stress levels flagged high, what is the developmental outcome of the young?",
        "options": {"A": "arrested", "B": "maturing", "C": "stunted"},
        "correct": "A"
    },
    {   # ExpDiet(1) -> Plumage(2) -> Bloom(3) -> Load
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {"adult_thorncrester.expressed_diet": "scavenger", "environment.weather_pattern": "drought"},
        # dull_grey -> active_bloom -> lethal
        "question": "Scavenging in a drought triggers feather mites. What is the parasitic load?",
        "options": {"A": "lethal", "B": "harmless", "C": "dormant"},
        "correct": "A"
    },
    {   # Plumage(1) -> Bloom(2) -> Load(3) -> Mortality
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"adult_thorncrester.plumage_color": "dull_grey", "environment.weather_pattern": "drought"},
        # active -> lethal -> critical
        "question": "Dull_grey plumage in drought conditions leads to what mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "moderate"},
        "correct": "A"
    },
    {   # Stress(1) -> ExpStruct(2) -> Territory(3) -> Mortality
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high", "environment.food_scarcity": True},
        # swarm -> aggressive -> critical
        "question": "High stress combined with scarcity brings what level of mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "moderate"},
        "correct": "A"
    },
    {   # GenDiet(1) -> ExpDiet(2) -> Metabolism(3) -> Development
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"adult_thorncrester.genetic_diet": "insectivore"},
        # insect -> starving -> arrested
        "question": "If their genetic diet is insectivore, how do the fructose-youths develop?",
        "options": {"A": "arrested", "B": "maturing", "C": "normal"},
        "correct": "A"
    },
    {   # GenStruct(1) -> ExpStruct(2) -> Territory(3) -> Mortality
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"thorncrester_flock.genetic_structure": "survival_swarm", "environment.food_scarcity": True},
        # swarm + scarcity -> aggressive -> critical
        "question": "A genetic survival swarm deals with food loss. The resulting mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "high"},
        "correct": "A"
    },
    {   # Weather(1) -> Stress(2) -> ExpDiet(3) -> Metabolism
        "attributes": ["juvenile_thorncrester.metabolic_state"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # scav -> starving
        "question": "A harsh drought hits with scarcity. How does this affect juvenile metabolism?",
        "options": {"A": "starving", "B": "thriving", "C": "dead"},
        "correct": "A"
    },
    {   # ExpStruct(1) -> Territory(2) -> Mortality(3)  Let's do Enzmye(1) -> Metabolism(2) -> Development(3) -> X? No, Dev is leaf.
        # How about: Weather(1) -> Stress(2) -> ExpDiet(3) -> Plumage
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": False},
        # Stress=nominal! Exp=frugivore. Plumage=crimson
        "question": "Drought but NO scarcity. What is the plumage color?",
        "options": {"A": "crimson", "B": "dull_grey", "C": "black"},
        "correct": "A"
    }
]

# =====================================================================
# 5. 4-HOP SET (10 Turns)
# Target: 4+ levels of indirection. Deepest possible logic tracing in Thorncrester.
# =====================================================================
THORNCRESTER_4HOP_TURNS = [
    {   # Weather(1) -> Stress(2) -> ExpDiet(3) -> Plumage(4) -> Bloom(5)
        "attributes": ["feather_mite.bloom_status"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # active
        "question": "Full drought and scarcity set in. What happens to the feather mites?",
        "options": {"A": "active_bloom", "B": "dormant", "C": "extinct"},
        "correct": "A"
    },
    {   # Weather(1) -> Stress(2) -> ExpDiet(3) -> Metabolism(4) -> Development(5)
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        "question": "With the full stress cascading, what is the development state of the young?",
        "options": {"A": "arrested", "B": "maturing", "C": "thriving"},
        "correct": "A"
    },
    {   # Weather(1) -> Stress(2) -> ExpStruct(3) -> Territory(4) -> Mortality(5)
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # critical
        "question": "From weather to social collapse, what is the ultimate adult mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "moderate"},
        "correct": "A"
    },
    {   # GenDiet(1) -> ExpDiet(2) -> Plumage(3) -> Bloom(4) -> Load(5) 
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {"adult_thorncrester.genetic_diet": "scavenger", "environment.weather_pattern": "drought"},
        # scav -> grey -> active -> lethal
        "question": "A genetic scavenger encounters a drought. What is the parasitic load?",
        "options": {"A": "lethal", "B": "harmless", "C": "minor"},
        "correct": "A"
    },
    {   # Stress(1) -> ExpDiet(2) -> Plumage(3) -> Bloom(4) -> Load(5) -> Mortality(6)
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high", "environment.weather_pattern": "drought"},
        # high -> scav -> grey -> active -> lethal -> critical
        "question": "High stress is forced during a drought. What is the adult mortality?",
        "options": {"A": "critical", "B": "low", "C": "medium"},
        "correct": "A"
    },
    {   # Weather(1) -> Stress(2) -> ExpDiet(3) -> Plumage(4) -> Bloom(5) -> Load(6)  Wait, Weather to Bloom is direct, but via plumage it's long.
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": True},
        # active -> lethal
        "question": "Given strict drought and scarcity, what is the parasitic load?",
        "options": {"A": "lethal", "B": "harmless", "C": "high"},
        "correct": "A"
    },
    {   # GenDiet(1) -> ExpDiet(2) -> Metabolism(3) -> Development(4) -- max is 4
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"adult_thorncrester.genetic_diet": "insectivore"},
        # arrested
        "question": "If adults genetically shift to insects, evaluate the juvenile development.",
        "options": {"A": "arrested", "B": "maturing", "C": "thriving"},
        "correct": "A"
    },
    {   # ExpDiet(1) -> Plumage(2) -> Bloom(3) -> Load(4) -> Mortality(5)
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"adult_thorncrester.expressed_diet": "scavenger", "environment.weather_pattern": "drought"},
        "question": "Scavenging in a drought drives plumage changes. Final mortality impact?",
        "options": {"A": "critical", "B": "low", "C": "high"},
        "correct": "A"
    },
    {   # Stress(1) -> ExpStruct(2) -> Territory(3) -> Mortality(4)
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"adult_thorncrester.ecological_stress": "high", "environment.food_scarcity": True},
        "question": "High stress alters flock formation amidst scarcity. Mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "moderate"},
        "correct": "A"
    },
    {   # Weather(1) -> Stress(2) -> ExpDiet(3) -> Plumage(4) -> Bloom(5) (negative check)
        "attributes": ["feather_mite.bloom_status"],
        "beliefs": {"environment.weather_pattern": "drought", "environment.food_scarcity": False},
        # Stress=nominal -> frugivore -> crimson -> dormant
        "question": "Drought but NO scarcity. How are the feather mites affected?",
        "options": {"A": "dormant", "B": "active_bloom", "C": "lethal"},
        "correct": "A"
    }
]

# =====================================================================
# 6. BELIEF MAINTENANCE SET (10 Turns)
# Target: Different attributes should maintain independence; adding unrelated beliefs
# should not affect derived attributes. Tests that belief queries are orthogonal.
# =====================================================================
THORNCRESTER_BELIEF_MAINTENANCE_TURNS = [
    {   # Query 1: Stress (baseline)
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False},
        "question": "In a stable environment with no scarcity, what is the ecological stress?",
        "options": {"A": "high", "B": "nominal", "C": "critical"},
        "correct": "B"  # nominal
    },
    {   # Query 2: Plumage (independent path from stress)
        "attributes": ["adult_thorncrester.plumage_color"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False},
        "question": "With no stress, what is the plumage color?",
        "options": {"A": "dull_grey", "B": "crimson", "C": "azure"},
        "correct": "B"  # crimson (stress -> nom -> frugivore -> crimson)
    },
    {   # Query 3: Territory behavior (independent branch)
        "attributes": ["thorncrester_flock.territory_behavior"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False},
        "question": "With stable weather and no scarcity, what territory behavior emerges?",
        "options": {"A": "hyper_aggressive", "B": "peaceful", "C": "defensive"},
        "correct": "B"  # peaceful (stress=nom -> matriarchal -> peaceful)
    },
    {   # Query 4: Add genetic diet variation, requery stress (should be independent)
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False, "adult_thorncrester.genetic_diet": "scavenger"},
        "question": "With genetic diet changed but weather stable, what is stress?",
        "options": {"A": "high", "B": "nominal", "C": "variable"},
        "correct": "B"  # Maintained: stress depends on weather+scarcity, not genetic_diet
    },
    {   # Query 5: Add flock structure variation, requery stress (still independent)
        "attributes": ["adult_thorncrester.ecological_stress"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False, "adult_thorncrester.genetic_diet": "scavenger", "thorncrester_flock.genetic_structure": "survival_swarm"},
        "question": "Despite structure variation, what is ecological stress?",
        "options": {"A": "high", "B": "nominal", "C": "unknown"},
        "correct": "B"  # Maintained: still nominal (weather+scarcity are stable)
    },
    {   # Query 6: Query mortality in stable conditions (should be low)
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False, "adult_thorncrester.genetic_diet": "scavenger", "thorncrester_flock.genetic_structure": "survival_swarm"},
        "question": "In stability despite structural changes, what mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "moderate"},
        "correct": "B"  # low (stress=nom -> exp_struct=swarm (no override), food=no -> territory=peaceful, mites=dormant -> load=harmless -> low)
    },
    {   # Query 7: Add juvenile enzyme info, requery mortality (independent)
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False, "adult_thorncrester.genetic_diet": "scavenger", "thorncrester_flock.genetic_structure": "survival_swarm", "juvenile_thorncrester.digestive_enzyme": "fructose_processor"},
        "question": "With juvenile enzyme added to beliefs, what mortality risk?",
        "options": {"A": "critical", "B": "low", "C": "high"},
        "correct": "B"  # Maintained: mortality independent from juvenile enzyme
    },
    {   # Query 8: Query juvenile development (separate attribute, stable conditions)
        "attributes": ["juvenile_thorncrester.development"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False, "adult_thorncrester.genetic_diet": "frugivore", "juvenile_thorncrester.digestive_enzyme": "fructose_processor"},
        "question": "With frugivore diet and fructose juveniles, what development?",
        "options": {"A": "arrested", "B": "maturing", "C": "stunted"},
        "correct": "B"  # maturing (frugivore matches enzyme)
    },
    {   # Query 9: Keep prior beliefs, query parasitic load (independent from juvenile dev)
        "attributes": ["feather_mite.parasitic_load"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False, "adult_thorncrester.genetic_diet": "frugivore", "juvenile_thorncrester.digestive_enzyme": "fructose_processor"},
        "question": "With stable weather, what is the parasitic load?",
        "options": {"A": "lethal", "B": "harmless", "C": "moderate"},
        "correct": "B"  # harmless (weather=stable -> plumage=crimson, no dull_grey -> no bloom -> dormant -> harmless)
    },
    {   # Query 10: Final maintenance - requery mortality with all prior beliefs (ultimate test)
        "attributes": ["adult_thorncrester.mortality_risk"],
        "beliefs": {"environment.weather_pattern": "stable", "environment.food_scarcity": False, "adult_thorncrester.genetic_diet": "frugivore", "juvenile_thorncrester.digestive_enzyme": "fructose_processor", "thorncrester_flock.genetic_structure": "matriarchal_pairs"},
        "question": "With all stable baseline beliefs, what mortality risk holds?",
        "options": {"A": "critical", "B": "low", "C": "variable"},
        "correct": "B"  # Fully maintained: low (peaceful territory + harmless load = low)
    }
]
