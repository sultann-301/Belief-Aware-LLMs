"""BeliefStore — belief store with deterministic derivation rules."""

from __future__ import annotations

from typing import Any, Callable
from .belief_lookup import BELIEF_DESCRIPTIONS


class BeliefStore:

    def __init__(self) -> None:
        # beliefs maps key → (value, is_derived)
        self.beliefs: dict[str, tuple[Any, bool]] = {}
        self.dependencies: dict[str, list[str]] = {}
        self.dirty: set[str] = set()
        self.removed: set[str] = set()  # tombstone set — lazy retraction
        self.revision_log: list[dict[str, Any]] = []
        self.rule_index: dict[str, dict[str, Any]] = {}  # output_key → rule
        self._entity_cache: dict[str, str] = {}  # key → entity name cache

    def entity_of(self, key: str) -> str:
        """Extract the entity name from a belief key (cached)."""
        entity = self._entity_cache.get(key)
        if entity is None:
            entity = key.split(".")[0]
            self._entity_cache[key] = entity
        return entity

    def get_value(self, key: str) -> Any:
        """Return the current value, or None if absent or tombstoned."""
        if key in self.removed:
            self.beliefs.pop(key, None)  # flush on access
            return None
        entry = self.beliefs.get(key)
        return entry[0] if entry is not None else None

    def add_hypothesis(self, key: str, value: Any) -> None:
        """Add or update a hypothesis belief and propagate dirty flags.

        Un-tombstones the key if it was previously retracted.
        """
        self.removed.discard(key)  # un-tombstone if being re-added
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
        """Lazily retract a hypothesis.

        The belief is tombstoned in ``self.removed`` immediately but the actual
        deletion from ``beliefs`` and cascade to derived dependents are deferred:
        - ``get_value`` flushes the entry on the next read.
        - ``resolve_dirty`` cascades the tombstone when it encounters a removed
          input, flushing each derived belief at that point.
        """
        if key in self.removed:
            return  # already tombstoned
        old_entry = self.beliefs.get(key)
        old_value = old_entry[0] if old_entry is not None else None
        self.removed.add(key)
        self.dirty.discard(key)
        self.revision_log.append({
            "action": "retract", "key": key, "old": old_value, "new": None,
        })
        # Mark downstream derived beliefs dirty so resolve_dirty can lazily
        # cascade the removal when it next processes them.
        self._propagate_dirty(key)

    def add_rule(
        self,
        name: str,
        inputs: list[str],
        output_key: str,
        derive_fn: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a derivation rule and wire up the dependency graph."""
        self.rule_index[output_key] = {
            "name": name,
            "inputs": inputs,
            "derive_fn": derive_fn,
        }
        self.dependencies[output_key] = inputs

    def _propagate_dirty(self, key: str) -> None:
        """Recursively mark all downstream dependents as dirty."""
        for dep_key, dep_sources in self.dependencies.items():
            if key in dep_sources and dep_key not in self.dirty:
                self.dirty.add(dep_key)
                self._propagate_dirty(dep_key)

    def resolve_all_dirty(self) -> None:
        """Resolve ALL dirty beliefs. Convenience alias."""
        entity_set = {self.entity_of(k) for k in self.dirty}
        self._resolve_dirty_set(entity_set)

    def resolve_dirty(self, entities: list[str]) -> None:
        """Resolve only dirty beliefs belonging to the given entities."""
        self._resolve_dirty_set(set(entities))

    def _resolve_dirty_set(self, entity_set: set[str]) -> None:
        """Internal resolver — operates on a pre-built entity set."""
        resolved: set[str] = set()

        def resolve(key: str) -> None:
            if key in resolved or key not in self.dirty:
                return
            # Always resolve upstream deps (may belong to other entities)
            for dep in self.dependencies.get(key, []):
                if dep in self.dirty:
                    resolve(dep)
            rule = self.rule_index.get(key)
            if rule:
                # Lazy cascade: if any input was tombstoned, tombstone this
                # derived belief too and flush it rather than re-deriving.
                if any(inp in self.removed for inp in rule["inputs"]):
                    old_entry = self.beliefs.get(key)
                    old_value = old_entry[0] if old_entry is not None else None
                    self.removed.add(key)
                    self.beliefs.pop(key, None)  # flush from live beliefs
                    self.dirty.discard(key)
                    resolved.add(key)
                    self.revision_log.append({
                        "action": "retract", "key": key,
                        "old": old_value, "new": None,
                    })
                    return
                # Build input_values dict only for inputs that exist in beliefs.
                # This allows derive_fn to use dict.get(default) for missing keys.
                input_values: dict[str, Any] = {}
                for k in rule["inputs"]:
                    if k in self.beliefs:
                        input_values[k] = self.beliefs[k][0]
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
            if self.entity_of(key) in entity_set:
                resolve(key)

    def to_prompt(self, entities: list[str]) -> tuple[str, list[str]]:
        """Serialize clean beliefs for the given entities into a prompt."""
        lines: list[str] = []
        prompt_keys: list[str] = []

        entity_set = set(entities)
        for key, (value, is_derived) in self.beliefs.items():
            if key in self.removed:
                continue  # skip tombstoned beliefs
            entity = self.entity_of(key)
            if entity in entity_set:
                assert key not in self.dirty, (
                    f"Relevant belief {key} is still dirty"
                )
                tag = "derived" if is_derived else "base"
                # Append an inline description when available so the LLM
                # understands the role or relationship of this attribute.
                desc = BELIEF_DESCRIPTIONS.get(key)
                line = f"[{tag}] {key} = {value}"
                if desc:
                    line = f"{line}  # {desc}"
                lines.append(line)
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
            f"dirty={len(self.dirty)}, removed={len(self.removed)}, "
            f"rules={len(self.rule_index)})"
        )
