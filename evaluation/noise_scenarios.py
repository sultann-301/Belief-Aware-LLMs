"""Noise-augmented scenario turns derived from absurd_temporal base sets."""

from __future__ import annotations

from itertools import cycle
from typing import Dict, Iterable, List

from evaluation.belief_awareness_scenarios import (
    ALIEN_ABSURD_TEMPORAL_TURNS,
    CRIME_ABSURD_TEMPORAL_TURNS,
    LOAN_ABSURD_TEMPORAL_TURNS,
    THORNCRESTER_ABSURD_TEMPORAL_TURNS,
)

NoiseSentences = List[str]
Turn = Dict[str, object]


NOISE_SENTENCES: NoiseSentences = [
    "Also, my cat knocked over a glass of water earlier today.",
    "By the way, I had oatmeal for breakfast this morning.",
    "Also, the bus was a few minutes late on my commute.",
    "By the way, I watered the plants before leaving home.",
    "Also, I heard a dog barking outside for a while.",
    "By the way, I picked up a package from the front desk.",
    "Also, I left my umbrella in the car by mistake.",
    "By the way, the coffee shop was out of muffins today.",
    "Also, I need to remember to call my dentist later.",
    "By the way, I noticed the sky looked unusually bright today.",
]


def _add_noise_sentence(question: str, noise_sentence: str) -> str:
    question = str(question).strip()
    if not question.endswith((".", "?", "!")):
        question = f"{question}?"
    return f"{question} {noise_sentence}"


def build_noisy_turns(turns: Iterable[Turn], noise_sentences: NoiseSentences) -> List[Turn]:
    noisy_turns: List[Turn] = []
    noise_iter = cycle(noise_sentences)

    for turn in turns:
        noise_sentence = next(noise_iter)
        noisy_turns.append(
            {
                "attributes": list(turn.get("attributes", [])),
                "beliefs": dict(turn.get("beliefs", {})),
                "question": _add_noise_sentence(turn.get("question", ""), noise_sentence),
                "options": dict(turn.get("options", {})),
                "correct": turn.get("correct"),
                "noise_sentence": noise_sentence,
            }
        )

    return noisy_turns


LOAN_ABSURD_TEMPORAL_NOISE_TURNS = build_noisy_turns(
    LOAN_ABSURD_TEMPORAL_TURNS,
    NOISE_SENTENCES,
)

ALIEN_ABSURD_TEMPORAL_NOISE_TURNS = build_noisy_turns(
    ALIEN_ABSURD_TEMPORAL_TURNS,
    NOISE_SENTENCES,
)

CRIME_ABSURD_TEMPORAL_NOISE_TURNS = build_noisy_turns(
    CRIME_ABSURD_TEMPORAL_TURNS,
    NOISE_SENTENCES,
)

THORNCRESTER_ABSURD_TEMPORAL_NOISE_TURNS = build_noisy_turns(
    THORNCRESTER_ABSURD_TEMPORAL_TURNS,
    NOISE_SENTENCES,
)


NOISE_SCENARIO_TURNS = {
    "loan_absurd_temporal": LOAN_ABSURD_TEMPORAL_NOISE_TURNS,
    "alien_clinic_absurd_temporal": ALIEN_ABSURD_TEMPORAL_NOISE_TURNS,
    "crime_scene_absurd_temporal": CRIME_ABSURD_TEMPORAL_NOISE_TURNS,
    "thorncrester_absurd_temporal": THORNCRESTER_ABSURD_TEMPORAL_NOISE_TURNS,
}
