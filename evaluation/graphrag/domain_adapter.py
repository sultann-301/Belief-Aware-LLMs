"""Read existing domain rule text and topology without executing derivations."""

from __future__ import annotations

import re
from typing import Any, Mapping

from belief_store.domains.alien_clinic import setup_alien_clinic_domain
from belief_store.domains.crime_scene import setup_crime_scene_domain
from belief_store.domains.loan import setup_loan_domain
from belief_store.domains.thorncrester import setup_thorncrester_domain
from belief_store.store import BeliefStore
from evaluation.graphrag.graph import DomainGraph, RuleNode
from evaluation.graphrag.loan_adapter import build_loan_graph
from evaluation.scenario_sets.base import ALIEN_RULES, CRIME_RULES, LOAN_RULES, THORNCRESTER_RULES


DOMAIN_SOURCES = {
    setup_loan_domain: ("loan", LOAN_RULES),
    setup_alien_clinic_domain: ("alien_clinic", ALIEN_RULES),
    setup_crime_scene_domain: ("crime_scene", CRIME_RULES),
    setup_thorncrester_domain: ("thorncrester", THORNCRESTER_RULES),
}


def build_domain_graph(setup_fn, rule_text: str, facts: Mapping[str, Any]) -> DomainGraph:
    source = DOMAIN_SOURCES.get(setup_fn)
    if source is None or source[1] != rule_text:
        raise ValueError("Unsupported domain setup or modified rule text.")
    domain = source[0]
    if domain == "loan":
        return build_loan_graph(facts)

    store = BeliefStore()
    setup_fn(store)  # Registers topology only; no values are resolved.
    text_by_output = {}
    for line in rule_text.splitlines():
        match = re.match(r"^\d+\.\s+([\w.]+)\s*=\s*(.*)$", line)
        if match:
            text_by_output[match[1]] = line.split(". ", 1)[1]

    if domain == "alien_clinic":
        # One source line defines all three phases; another defines the shared
        # danger rule. Attach only the relevant phase and instantiate its name.
        lines = {int(m[1]): m[2] for line in rule_text.splitlines()
                 if (m := re.match(r"^(\d+)\.\s+(.*)$", line))}
        for clause in re.split(r"\. (?=treatment\.)", lines[2]):
            output = clause.split(" =", 1)[0]
            text_by_output[output] = clause
        for compound in ("zyxostin", "filinan", "snevox"):
            output = f"treatment.{compound}_danger_level"
            text_by_output[output] = f"{output} (compound = {compound}): {lines[3]}"
    elif domain == "thorncrester":
        for line in rule_text.splitlines():
            match = re.match(r"^R\d+: (\w+) -> (.*)$", line)
            if match:
                outputs = [key for key in store.rule_index if key.rsplit(".", 1)[-1] == match[1]]
                if len(outputs) != 1:
                    raise ValueError(f"Ambiguous Thorncrester rule: {line}")
                text_by_output[outputs[0]] = f"{outputs[0]} -> {match[2]}"

    if set(text_by_output) != set(store.rule_index):
        raise ValueError(f"{domain} rule text and topology are out of sync.")
    rules = [RuleNode(
        name=rule["name"], inputs=tuple(rule["inputs"]), output=output,
        text=f"{text_by_output[output]}\nInput keys: {', '.join(rule['inputs'])}",
    ) for output, rule in store.rule_index.items()]
    return DomainGraph(domain=domain, rules=rules, facts=facts)
