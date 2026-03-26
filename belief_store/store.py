"""BeliefStore — belief store with deterministic derivation rules."""

from __future__ import annotations

from typing import Any, Callable


class BeliefStore:

    def __init__(self) -> None:
        # beliefs maps key → (value, is_derived)
        self.beliefs: dict[str, tuple[Any, bool]] = {}
        self.dependencies: dict[str, list[str]] = {}
        self.dirty: set[str] = set()
        self.revision_log: list[dict[str, Any]] = []
        self.derivation_rules: list[dict[str, Any]] = []

    def entity_of(self, key: str) -> str:
        """Extract the entity name from a belief key."""
        return key.split(".")[0]

    def get_value(self, key: str) -> Any:
        """Return the current value for a belief key."""
        entry = self.beliefs.get(key)
        return entry[0] if entry is not None else None

    def add_hypothesis(self, key: str, value: Any) -> None:
        """Add or update a hypothesis belief and propagate dirty flags."""
        old_belief_entry = self.beliefs.get(key)
        old_value = old_belief_entry[0] if old_belief_entry is not None else None

        if old_value is not None:
            self.revision_log.append({
                "action": "update", "key": key, "old": old_value, "new": value,
            })
        else:
            self.revision_log.append({
                "action": "add", "key": key, "old": None, "new": value,
            })

        self.beliefs[key] = (value, False)
        self._propagate_dirty(key)

    def remove_hypothesis(self, key: str) -> None:
        """Retract a hypothesis and cascade to unsupported derivations."""
        old_belief_entry = self.beliefs.pop(key, None)
        old_value = old_belief_entry[0] if old_belief_entry is not None else None
        self.dirty.discard(key)

        self.revision_log.append({
            "action": "retract", "key": key, "old": old_value, "new": None,
        })
        for dep_key, dep_sources in list(self.dependencies.items()):
            if key in dep_sources:
                if not all(s in self.beliefs for s in dep_sources):
                    self.remove_hypothesis(dep_key)

    def add_rule(
        self,
        name: str,
        inputs: list[str],
        output_key: str,
        derive_fn: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a derivation rule and wire up the dependency graph."""
        self.derivation_rules.append({
            "name": name,
            "inputs": inputs,
            "output_key": output_key,
            "derive_fn": derive_fn,
        })
        self.dependencies[output_key] = inputs

    def _propagate_dirty(self, key: str) -> None:
        """Recursively mark all downstream dependents as dirty."""
        for dep_key, dep_sources in self.dependencies.items():
            if key in dep_sources and dep_key not in self.dirty:
                self.dirty.add(dep_key)
                self._propagate_dirty(dep_key)

    def resolve_all_dirty(self) -> None:
        """Resolve ALL dirty beliefs. Convenience alias."""
        entities = list({self.entity_of(k) for k in self.dirty})
        self.resolve_dirty(entities)

    def resolve_dirty(self, entities: list[str]) -> None:
        """Resolve only dirty beliefs belonging to the given entities."""
        resolved: set[str] = set()

        def resolve(key: str) -> None:
            if key in resolved or key not in self.dirty:
                return
            # Always resolve upstream deps (may belong to other entities)
            for dep in self.dependencies.get(key, []):
                if dep in self.dirty:
                    resolve(dep)
            for rule in self.derivation_rules:
                if rule["output_key"] == key:
                    input_values = {k: self.beliefs[k][0] for k in rule["inputs"]}
                    old_belief_entry = self.beliefs.get(key)
                    old_value = old_belief_entry[0] if old_belief_entry is not None else None
                    new_value = rule["derive_fn"](input_values)
                    self.beliefs[key] = (new_value, True)
                    self.dirty.discard(key)
                    resolved.add(key)
                    self.revision_log.append({
                        "action": "derived",
                        "key": key,
                        "old": old_value,
                        "new": new_value,
                        "reason": f"rule: {rule['name']}",
                    })
                    return

        # Only resolve dirty keys that belong to the requested entities
        for key in list(self.dirty):
            if self.entity_of(key) in entities:
                resolve(key)

    def to_prompt(self, entities: list[str]) -> tuple[str, list[str]]:
        """Serialize clean beliefs for the given entities into a prompt."""
        lines: list[str] = []
        prompt_keys: list[str] = []

        for key, (value, is_derived) in self.beliefs.items():
            entity = self.entity_of(key)
            if entity in entities:
                assert key not in self.dirty, (
                    f"Relevant belief {key} is still dirty"
                )
                tag = "derived" if is_derived else "base"
                lines.append(f"[{tag}] {key} = {value}")
                prompt_keys.append(key)

        return "\n".join(lines), prompt_keys

    def format_revision_log(self, since_index: int = 0) -> str:
        """Format the revision log from ``since_index`` onward."""
        lines: list[str] = []
        for entry in self.revision_log[since_index:]:
            action = entry["action"]
            key = entry["key"]
            old_value = entry.get("old")
            new_value = entry.get("new")

            if action == "add":
                lines.append(f"[add]     {key}: {new_value}")
            elif action == "update":
                lines.append(f"[update]  {key}: {old_value} → {new_value}")
            elif action == "derived":
                reason = entry.get("reason", "")
                lines.append(f"[derived] {key}: {old_value} → {new_value}    ({reason})")
            elif action == "retract":
                lines.append(f"[retract] {key}: {old_value} → None")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"BeliefStore(beliefs={len(self.beliefs)}, "
            f"dirty={len(self.dirty)}, rules={len(self.derivation_rules)})"
        )
