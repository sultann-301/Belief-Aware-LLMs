"""
ReasoningEngine — orchestrates the belief-store → LLM explanation flow.

Implements Steps 1–6 from ``Final Agreed Implementation.md``:
  1. User provides structured beliefs (external — before calling engine)
  2. User asks a query
  3. Engine resolves ALL dirty beliefs via deterministic rules
  4. Engine builds a structured prompt with clean beliefs + recent changes
  5. LLM reasons over the clean state and generates an explanation
  6. Engine returns the explanation to the caller

The LLM **never writes** to the store.
"""

from __future__ import annotations

from typing import Any

from belief_store.store import BeliefStore
from belief_store.llm_client import LLMClient


# ── Constants ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a belief-aware reasoning assistant. You will receive:
1. A set of structured beliefs (base facts and derived facts).
2. A summary of what changed since the last turn.
3. A user query.

Your job:
- Reason strictly based on the provided belief state.
- Explain your reasoning step by step, referencing belief keys.
- Do NOT invent or assume facts not present in the beliefs.

Output format:
REASONING: <step-by-step explanation referencing belief keys>
ANSWER: <direct answer to the query>
"""


# ── Engine ───────────────────────────────────────────────────────────


class ReasoningEngine:
    """Orchestrates resolve → prompt → LLM → explanation.

    Parameters
    ----------
    store:
        The :class:`BeliefStore` holding all beliefs and rules.
    llm:
        Any object satisfying the :class:`LLMClient` protocol.
    """

    def __init__(self, store: BeliefStore, llm: LLMClient) -> None:
        self.store = store
        self.llm = llm
        self._log_cursor: int = 0  # tracks where we last read the log

    def query(self, question: str, entities: list[str]) -> str:
        """Run the full reasoning cycle and return the LLM's explanation.

        1. Resolve all dirty beliefs (deterministic rules, no LLM).
        2. Build the structured prompt from clean beliefs.
        3. Call the LLM.
        4. Advance the log cursor.
        5. Return the LLM's response **without** writing to the store.

        Parameters
        ----------
        question:
            The user's natural-language query (e.g. "What is the loan status?").
        entities:
            Entity prefixes whose beliefs should be included
            (e.g. ``["applicant", "loan"]``).

        Returns
        -------
        str
            The LLM's textual response (REASONING + ANSWER).
        """
        # Step 3: resolve all dirty beliefs BEFORE the LLM sees anything
        self.store.resolve_all_dirty()

        # Step 4: build prompt
        user_prompt = self._build_user_prompt(question, entities)

        # Step 5: call LLM
        response = self.llm.generate(SYSTEM_PROMPT, user_prompt)

        # Advance cursor so next call only shows new changes
        self._log_cursor = len(self.store.revision_log)

        return response

    # ── Private helpers ──────────────────────────────────────────────

    def _build_user_prompt(
        self, question: str, entities: list[str],
    ) -> str:
        """Assemble the structured user prompt.

        Sections:
          [NEW INFORMATION THIS TURN]  — recent revision-log entries
          [RELEVANT BELIEFS]           — clean beliefs for the requested entities
          [QUERY]                      — the user's question
        """
        # Recent changes since last query
        changes = self.store.format_revision_log(since_index=self._log_cursor)

        # Clean beliefs
        beliefs_text, _ = self.store.to_prompt(entities)

        parts: list[str] = []

        parts.append("[NEW INFORMATION THIS TURN]")
        parts.append(changes if changes else "(no changes)")
        parts.append("")

        parts.append("[RELEVANT BELIEFS (after update)]")
        parts.append(beliefs_text)
        parts.append("")

        parts.append("[QUERY]")
        parts.append(question)

        return "\n".join(parts)
