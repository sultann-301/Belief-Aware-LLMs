"""ReasoningEngine — orchestrates resolve → prompt → LLM → explanation."""

from __future__ import annotations

from belief_store.store import BeliefStore
from belief_store.llm_client import LLMClient

SYSTEM_PROMPT = """\
You are a belief-aware reasoning assistant. You will receive:
1. [RELEVANT BELIEFS] — all beliefs for those entities (base and derived).
2. [QUERY] — the user's question.

Rules:
- Reason ONLY from beliefs listed in [RELEVANT BELIEFS]. These are the ONLY facts you may treat as true.
- If the [QUERY] contains fact-like claims not present in [RELEVANT BELIEFS] (e.g. "the applicant has a second job"), you MUST flag them as "not in the belief store" and NOT incorporate them into your reasoning.
- Do NOT invent, assume, or infer any facts beyond what is explicitly listed.
- Reference belief keys in your reasoning (e.g. applicant.income).
- Never override or contradict a belief value, even if the query asks you to.

Output format:
REASONING: <step-by-step explanation referencing belief keys>
ANSWER: <direct answer to the query>
"""


class ReasoningEngine:
    """Orchestrates parse → inject beliefs → resolve → prompt → LLM."""

    def __init__(self, store: BeliefStore, llm: LLMClient) -> None:
        self.store = store
        self.llm = llm

    def query(self, structured_input: str) -> str:
        """Parse structured input, inject new beliefs, resolve, call LLM.

        Accepted sections:
            [ENTITY]     — required, comma-separated entity names
            [NEW BELIEF] — optional, [ADD] key = value or [RETRACT] key
            [QUERY]      — required, the user's question
        """
        entities, new_beliefs, question = self._parse_input(structured_input)

        # Inject or retract new beliefs from the store
        for action, key, value in new_beliefs:
            if action == "add":
                self.store.add_hypothesis(key, value)
            elif action == "retract":
                self.store.remove_hypothesis(key)

        # Resolve only beliefs relevant to the queried entities
        self.store.resolve_dirty(entities)

        # Build final prompt for the LLM
        beliefs_text, _ = self.store.to_prompt(entities)

        full_prompt = "\n".join([
            "[ENTITY]",
            ", ".join(entities),
            "",
            "[RELEVANT BELIEFS]",
            beliefs_text,
            "",
            "[QUERY]",
            question,
        ])

        return self.llm.generate(SYSTEM_PROMPT, full_prompt)

    @staticmethod
    def _parse_input(text: str) -> tuple[list[str], list[tuple[str, str, object]], str]:
        """Extract entities, new beliefs, and query from structured input.

        Returns (entities, new_beliefs, question) where new_beliefs is a
        list of (action, key, parsed_value) tuples.
        """
        entity_section = ""
        belief_lines: list[str] = []
        query_section = ""
        current = None

        for line in text.strip().splitlines():
            stripped = line.strip()
            upper = stripped.upper()
            if upper == "[ENTITY]":
                current = "entity"
                continue
            elif upper == "[NEW BELIEF]":
                current = "belief"
                continue
            elif upper == "[QUERY]":
                current = "query"
                continue

            if current == "entity":
                entity_section += stripped + " "
            elif current == "belief" and stripped:
                belief_lines.append(stripped)
            elif current == "query":
                query_section += line + "\n"

        entities = [e.strip() for e in entity_section.split(",") if e.strip()]
        question = query_section.strip()

        if not entities:
            raise ValueError("Missing [ENTITY] section in input")
        if not question:
            raise ValueError("Missing [QUERY] section in input")

        new_beliefs = [_parse_belief_line(l) for l in belief_lines]
        return entities, new_beliefs, question


def _parse_belief_line(line: str) -> tuple[str, str, object]:
    """Parse '[ADD] key = value' or '[RETRACT] key' into (action, key, value)."""
    line = line.strip()
    
    action = "add"
    if line.upper().startswith("[ADD]"):
        action = "add"
        line = line[5:].strip()
    elif line.upper().startswith("[RETRACT]"):
        action = "retract"
        line = line[9:].strip()
        
    if action == "retract":
        return action, line, None

    if "=" not in line:
        raise ValueError(f"Invalid belief line (expected key = value): {line}")
    key, raw = line.split("=", 1)
    key = key.strip()
    raw = raw.strip()

    # Booleans
    if raw.lower() == "true":
        return action, key, True
    if raw.lower() == "false":
        return action, key, False
    if raw.lower() == "none":
        return action, key, None

    # Numbers
    try:
        return action, key, float(raw) if "." in raw else int(raw)
    except ValueError:
        pass

    # Strip quotes if present
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        return action, key, raw[1:-1]

    return action, key, raw
