"""Immutable graph views for retrieval-only evaluation code.

These classes deliberately contain no rule functions.  They expose graph
structure, human-readable rule text, and asserted facts, but they cannot run
the deterministic belief-store derivations.
"""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RuleNode:
    """A non-executable rule in a domain dependency graph."""

    name: str
    inputs: tuple[str, ...]
    output: str
    text: str


@dataclass(frozen=True)
class GraphSlice:
    """The rules and asserted facts upstream of one or more attributes."""

    targets: tuple[str, ...]
    rules: tuple[RuleNode, ...]
    facts: Mapping[str, Any]


class DomainGraph:
    """A read-only snapshot of one implemented domain.

    ``subgraph_for`` currently accepts explicit attributes.  Natural-language
    query matching will be a separate layer so this adapter stays small and
    independently testable.
    """

    def __init__(
        self,
        *,
        domain: str,
        rules: Sequence[RuleNode],
        facts: Mapping[str, Any],
    ) -> None:
        rules_tuple = tuple(rules)
        rules_by_output = {rule.output: rule for rule in rules_tuple}
        if len(rules_by_output) != len(rules_tuple):
            raise ValueError("Each graph rule must have a unique output attribute.")

        self._domain = domain
        self._rules = rules_tuple
        self._rules_by_output = MappingProxyType(rules_by_output)
        # Copy before wrapping so later caller mutations cannot change the graph.
        self._facts = MappingProxyType(deepcopy(dict(facts)))

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def rules(self) -> tuple[RuleNode, ...]:
        return self._rules

    @property
    def facts(self) -> Mapping[str, Any]:
        return self._facts

    def rule_for(self, output: str) -> RuleNode | None:
        """Return the rule that produces ``output``, if one exists."""
        return self._rules_by_output.get(output)

    def subgraph_for(self, targets: Sequence[str]) -> GraphSlice:
        """Return the complete upstream dependency slice for ``targets``.

        Rules are ordered with upstream dependencies first.  Facts contain
        only asserted values that are actually connected to the slice. An
        explicit scenario assertion takes precedence over a rule for that key.
        No rule is executed while constructing the result.
        """
        ordered_rules: list[RuleNode] = []
        selected_facts: dict[str, Any] = {}
        visited_rules: set[str] = set()
        visiting: set[str] = set()

        def visit(attribute: str) -> None:
            if attribute in self._facts:
                selected_facts[attribute] = self._facts[attribute]
                return
            rule = self._rules_by_output.get(attribute)
            if rule is None:
                return

            if rule.output in visited_rules:
                return
            if rule.output in visiting:
                raise ValueError(f"Cycle detected while traversing {rule.output!r}.")

            visiting.add(rule.output)
            for input_attribute in rule.inputs:
                visit(input_attribute)
            visiting.remove(rule.output)
            visited_rules.add(rule.output)
            ordered_rules.append(rule)

        target_tuple = tuple(targets)
        for target in target_tuple:
            visit(target)

        return GraphSlice(
            targets=target_tuple,
            rules=tuple(ordered_rules),
            facts=MappingProxyType(selected_facts),
        )
