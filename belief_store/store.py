"""
BeliefStore — External persistent belief store for belief-aware LLMs.

The store manages structured beliefs (key-value pairs), deterministic
derivation rules, dirty-flag propagation, and a full audit trail.
The LLM never writes to this store; it only reads clean, resolved beliefs.
"""

from __future__ import annotations

from typing import Any, Callable


class BeliefStore:
    """External belief store with deterministic derivation rules.

    Attributes:
        beliefs:          key → value  (e.g. "applicant.income" → 6000)
        dependencies:     key → [keys it depends on]
        is_derived:       key → bool (True = derived via rule, False = hypothesis)
        dirty:            set of keys needing re-derivation
        revision_log:     audit trail of every mutation
        derivation_rules: list of deterministic rule dicts
    """

    def __init__(self) -> None:
        self.beliefs: dict[str, Any] = {}
        self.dependencies: dict[str, list[str]] = {}
        self.is_derived: dict[str, bool] = {}
        self.dirty: set[str] = set()
        self.revision_log: list[dict[str, Any]] = []
        self.derivation_rules: list[dict[str, Any]] = []

    # ================================================================
    # Hypothesis management
    # ================================================================

    def add_hypothesis(self, key: str, value: Any) -> None:
        """Add or update a user-provided hypothesis belief.

        - Logs the action (add or update).
        - Stores the value and marks it as non-derived.
        - Propagates dirty flags to all downstream dependents.
        """
        old = self.beliefs.get(key)

        # Log
        if old is not None:
            self.revision_log.append({
                "action": "update", "key": key, "old": old, "new": value,
            })
        else:
            self.revision_log.append({
                "action": "add", "key": key, "old": None, "new": value,
            })

        # Store
        self.beliefs[key] = value
        self.is_derived[key] = False

        # Mark all downstream dependents dirty (recursive)
        self._propagate_dirty(key)

    def remove_hypothesis(self, key: str) -> None:
        """Retract a hypothesis and cascade to unsupported derivations.

        Removing a belief causes any derived belief that depended on it
        (and now has a missing premise) to also be retracted, recursively.
        """
        old = self.beliefs.pop(key, None)
        self.is_derived.pop(key, None)
        self.dirty.discard(key)

        self.revision_log.append({
            "action": "retract", "key": key, "old": old, "new": None,
        })

        # Cascade: retract derived beliefs missing a premise
        for dep_key, dep_sources in list(self.dependencies.items()):
            if key in dep_sources:
                if not all(s in self.beliefs for s in dep_sources):
                    self.remove_hypothesis(dep_key)

    # ================================================================
    # Rules & derivation
    # ================================================================

    def add_rule(
        self,
        name: str,
        inputs: list[str],
        output_key: str,
        derive_fn: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a deterministic derivation rule.

        Automatically wires up the dependency graph so that changes to
        any input key will mark the output key as dirty.
        """
        self.derivation_rules.append({
            "name": name,
            "inputs": inputs,
            "output_key": output_key,
            "derive_fn": derive_fn,
        })
        # Wire up dependencies
        self.dependencies[output_key] = inputs
        self.is_derived[output_key] = True

    def _propagate_dirty(self, key: str) -> None:
        """Recursively mark all downstream dependents as dirty."""
        for dep_key, dep_sources in self.dependencies.items():
            if key in dep_sources and dep_key not in self.dirty:
                self.dirty.add(dep_key)
                self._propagate_dirty(dep_key)

    def resolve_all_dirty(self) -> None:
        """Resolve ALL dirty beliefs via derive_fn rules. No LLM.

        Resolution is bottom-up: dependencies are resolved before their
        dependents via recursive descent.
        """
        resolved: set[str] = set()

        def resolve(key: str) -> None:
            if key in resolved or key not in self.dirty:
                return
            # Resolve upstream first
            for dep in self.dependencies.get(key, []):
                if dep in self.dirty:
                    resolve(dep)

            # Find matching rule
            for rule in self.derivation_rules:
                if rule["output_key"] == key:
                    inputs = {k: self.beliefs[k] for k in rule["inputs"]}
                    old = self.beliefs.get(key)
                    new = rule["derive_fn"](inputs)
                    self.beliefs[key] = new
                    self.dirty.discard(key)
                    resolved.add(key)
                    self.revision_log.append({
                        "action": "derived",
                        "key": key,
                        "old": old,
                        "new": new,
                        "reason": f"rule: {rule['name']}",
                    })
                    return

        for key in list(self.dirty):
            resolve(key)

    # ================================================================
    # Prompt construction
    # ================================================================

    def to_prompt(self, entities: list[str]) -> tuple[str, list[str]]:
        """Serialize relevant beliefs into a structured prompt.

        Only beliefs whose entity prefix (before the first dot) is in
        ``entities`` are included. Those beliefs must all be clean;
        an ``AssertionError`` is raised if any relevant belief is dirty.

        Returns:
            (prompt_text, list_of_included_keys)
        """
        lines: list[str] = []
        prompt_keys: list[str] = []

        for key, value in self.beliefs.items():
            entity = key.split(".")[0]
            if entity in entities:
                assert key not in self.dirty, (
                    f"Relevant belief {key} is still dirty"
                )
                tag = "derived" if self.is_derived.get(key) else "base"
                lines.append(f"[{tag}] {key} = {value}")
                prompt_keys.append(key)

        return "\n".join(lines), prompt_keys

    # ================================================================
    # Audit
    # ================================================================

    def format_revision_log(self, since_index: int = 0) -> str:
        """Format the revision log as human-readable text.

        Args:
            since_index: only include entries from this index onward.

        Returns:
            Formatted string with one line per log entry.
        """
        lines: list[str] = []
        for entry in self.revision_log[since_index:]:
            action = entry["action"]
            key = entry["key"]
            old = entry.get("old")
            new = entry.get("new")

            if action == "add":
                lines.append(f"[add]     {key}: {new}")
            elif action == "update":
                lines.append(f"[update]  {key}: {old} → {new}")
            elif action == "derived":
                reason = entry.get("reason", "")
                lines.append(f"[derived] {key}: {old} → {new}    ({reason})")
            elif action == "retract":
                lines.append(f"[retract] {key}: {old} → None")

        return "\n".join(lines)

    # ================================================================
    # Introspection helpers
    # ================================================================

    def get_relevant_beliefs(self, entity: str) -> dict[str, Any]:
        """Return all beliefs belonging to a given entity prefix."""
        return {
            k: v for k, v in self.beliefs.items()
            if k.split(".")[0] == entity
        }

    def __repr__(self) -> str:
        n_beliefs = len(self.beliefs)
        n_dirty = len(self.dirty)
        n_rules = len(self.derivation_rules)
        return (
            f"BeliefStore(beliefs={n_beliefs}, "
            f"dirty={n_dirty}, rules={n_rules})"
        )
