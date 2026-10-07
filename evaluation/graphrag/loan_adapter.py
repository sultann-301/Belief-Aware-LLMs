"""Read-only adapter for the existing loan-domain implementation."""

from __future__ import annotations

import re
from typing import Any, Mapping

from belief_store.domains.loan import setup_loan_domain
from belief_store.store import BeliefStore
from evaluation.graphrag.graph import DomainGraph, RuleNode
from evaluation.scenario_sets.base import LOAN_INITIAL_BELIEFS, LOAN_RULES


_RULE_LINE = re.compile(r"^\s*\d+\.\s+([A-Za-z_][\w.]+)\s*=\s*(.+?)\s*$")


def _loan_rule_text_by_output() -> dict[str, str]:
    """Extract each loan rule's output key and readable text."""
    rule_text: dict[str, str] = {}
    for line in LOAN_RULES.splitlines():
        match = _RULE_LINE.match(line)
        if match:
            output = match.group(1)
            rule_text[output] = line.split(". ", 1)[1].strip()
    return rule_text


def build_loan_graph(facts: Mapping[str, Any] | None = None) -> DomainGraph:
    """Build an immutable, non-executable view of the current loan graph.

    The topology is read from ``setup_loan_domain`` so it remains aligned with
    the real belief-store implementation.  Human-readable rule text and the
    default asserted facts come from the existing evaluation scenario data.
    """
    store = BeliefStore()
    setup_loan_domain(store)

    text_by_output = _loan_rule_text_by_output()
    graph_outputs = set(store.rule_index)
    text_outputs = set(text_by_output)
    if graph_outputs != text_outputs:
        missing_text = sorted(graph_outputs - text_outputs)
        missing_graph = sorted(text_outputs - graph_outputs)
        raise ValueError(
            "Loan rule definitions are out of sync: "
            f"missing text={missing_text}, missing graph rules={missing_graph}."
        )

    rules = [
        RuleNode(
            name=rule["name"],
            inputs=tuple(rule["inputs"]),
            output=output,
            text=text_by_output[output],
        )
        for output, rule in store.rule_index.items()
    ]

    current_facts = LOAN_INITIAL_BELIEFS if facts is None else facts
    return DomainGraph(domain="loan", rules=rules, facts=current_facts)
