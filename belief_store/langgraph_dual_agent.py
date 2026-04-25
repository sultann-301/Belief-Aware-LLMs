"""Dual-agent reasoning system using LangGraph.

Architecture:
  - Agent 1 (Reasoner): Analyzes the query using relevant beliefs, outputs a canonical conclusion in JSON.
    - Agent 2 (Matcher): Reads Agent 1's conclusion and phrase-matches against options only.

Both agents use the same LLM model for fairness. The workflow decouples semantic reasoning 
from symbol binding.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END

from belief_store.llm_client import LLMClient
from belief_store.text_utils import normalize_for_match
from belief_store.prompts import (
    DUAL_AGENT_PROMPTS,
    DEFAULT_DUAL_AGENT_VERSIONS,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# State Schemas
# ────────────────────────────────────────────────────────────────────

class Agent1State(TypedDict, total=False):
    """State for Agent 1 (Reasoning phase)."""
    relevant_beliefs: str
    query: str
    conclusion: str
    evidence_keys: list[str]
    reasoning: str


class Agent2State(TypedDict, total=False):
    """State for Agent 2 (Decision phase)."""
    options: dict[str, str]
    conclusion: str
    matched_option_text: str
    matcher_rationale: str
    matched_option_label: str
    match_status: str


class DualAgentState(TypedDict, total=False):
    """Combined state flowing through the graph."""
    # Agent 1 inputs
    relevant_beliefs: str
    query: str
    chat_history: list[dict[str, str]]

    # Agent 1 outputs
    conclusion: str
    evidence_keys: list[str]
    reasoning: str

    # Agent 2 inputs (conclusion comes from Agent 1 outputs above)
    options: dict[str, str]

    # Agent 2 outputs
    matched_option_text: str
    matcher_rationale: str
    matched_option_label: str
    match_status: str


# ────────────────────────────────────────────────────────────────────
# Node Functions
# ────────────────────────────────────────────────────────────────────

def agent1_reason(
    state: dict[str, Any],
    llm: LLMClient,
    system_prompt: str,
) -> dict[str, Any]:
    """Agent 1: Compress the belief state into a canonical claim."""
    relevant_beliefs = state.get("relevant_beliefs", "")
    query = state.get("query", "")
    chat_history = state.get("chat_history", [])
    user_prompt = f"""[RELEVANT BELIEFS]\n{relevant_beliefs}\n\n[QUERY]\n{query}"""

    # Build messages list for the LLM
    messages = chat_history.copy() if chat_history else []
    
    # Ensure system prompt is present at the start of the thread
    if not messages or messages[0]["role"] != "system":
        messages.insert(0, {"role": "system", "content": system_prompt})
    
    # Add current turn's prompt
    messages.append({"role": "user", "content": user_prompt})
    
    response = llm.generate_with_history(messages, json_mode=True)

    parsed = _parse_json_object(response)
    if not parsed:
        logger.warning(
            "Agent 1 JSON parse failed. Raw response: %.200s", response
        )
        parsed = {
            "conclusion": "[PARSE FAILURE]",
            "evidence_keys": [],
            "reasoning": "Output was not valid JSON.",
        }

    evidence = parsed.get("evidence_keys", [])
    if not isinstance(evidence, list):
        evidence = []

    return {
        "conclusion": str(parsed.get("conclusion", "")),
        "evidence_keys": [str(item) for item in evidence],
        "reasoning": str(parsed.get("reasoning", "")),
    }


def agent2_decide(
    state: dict[str, Any],
    llm: LLMClient,
    system_prompt: str,
) -> dict[str, Any]:
    """Agent 2: Match Agent 1's conclusion to the correct option phrase."""
    options = state.get("options", {})
    options_text = "\n".join([f"- {phrase}" for phrase in options.values()])

    user_prompt = (
        f"Conclusion: {state.get('conclusion', '')}\n\n"
        f"Options:\n{options_text}\n\n"
        "Return JSON only."
    )

    response = llm.generate(system_prompt, user_prompt, json_mode=True).strip()
    parsed = _parse_json_object(response)

    matched_option_text = ""
    matcher_rationale = ""
    if parsed:
        matched_option_text = str(parsed.get("matched_option_text", "")).strip()
        matcher_rationale = str(parsed.get("matcher_rationale", "")).strip()

    if not matched_option_text:
        recovered = _recover_answer_from_text(response, options)
        matched_option_text = recovered or ""

    matched_option_label, match_status = derive_option_label_from_phrase(
        matched_option_text, options
    )

    return {
        "matched_option_text": matched_option_text,
        "matcher_rationale": matcher_rationale,
        "matched_option_label": matched_option_label or "",
        "match_status": match_status,
    }


# ────────────────────────────────────────────────────────────────────
# Parsing Helpers
# ────────────────────────────────────────────────────────────────────

def _parse_json_object(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from model output."""
    if not text:
        return {}

    block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    candidate = block_match.group(1) if block_match else text

    candidate = candidate.strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    start = candidate.find("{")
    while start != -1:
        depth = 0
        for idx in range(start, len(candidate)):
            char = candidate[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    snippet = candidate[start : idx + 1]
                    try:
                        parsed = json.loads(snippet)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break
        start = candidate.find("{", start + 1)

    return {}


def _recover_answer_from_text(text: str, options: dict[str, str]) -> str | None:
    """Conservatively recover an option phrase from free-form output."""
    if not text or not options:
        return None

    cleaned_text = text.replace("[]", "").replace("[ ]", "").strip()

    if cleaned_text in options.values():
        return cleaned_text

    exact_hits = [phrase for phrase in options.values() if phrase in cleaned_text]
    unique_exact_hits = list(dict.fromkeys(exact_hits))

    if len(unique_exact_hits) == 1:
        return unique_exact_hits[0]

    norm_text = normalize_for_match(cleaned_text)
    for phrase in options.values():
        if norm_text == normalize_for_match(phrase):
            return phrase
            
    normalized_hits: list[str] = []
    for phrase in options.values():
        norm_phrase = normalize_for_match(phrase)
        if len(norm_phrase) >= 5 and norm_phrase in norm_text:
            normalized_hits.append(phrase)

    unique_norm_hits = list(dict.fromkeys(normalized_hits))
    if len(unique_norm_hits) == 1:
        return unique_norm_hits[0]

    return None


def derive_option_label_from_phrase(
    matched_option_text: str,
    options: dict[str, str],
) -> tuple[str | None, str]:
    """Derive option label deterministically from phrase text.

    Returns:
      (label, status) where status is one of:
        - "matched"
        - "phrase-not-found"
        - "ambiguous-match"
    """
    if not matched_option_text or not options:
        return None, "phrase-not-found"

    # 1. Try exact match first (highest confidence)
    exact_matches = [label for label, phrase in options.items() if phrase == matched_option_text]
    if len(exact_matches) == 1:
        return exact_matches[0], "matched"
    if len(exact_matches) > 1:
        return None, "ambiguous-match"

    # 2. Try normalized match as fallback
    normalized_target = normalize_for_match(matched_option_text)
    normalized_matches = [
        label
        for label, phrase in options.items()
        if normalize_for_match(phrase) == normalized_target
    ]
    if len(normalized_matches) > 1:
        return None, "ambiguous-match"
    if len(normalized_matches) == 1:
        return normalized_matches[0], "matched"

    # 3. Try substring match as final fallback (for truncated model outputs)
    substring_matches = []
    for label, phrase in options.items():
        norm_phrase = normalize_for_match(phrase)
        if len(normalized_target) >= 5 and (normalized_target in norm_phrase or norm_phrase in normalized_target):
            substring_matches.append(label)
    
    unique_substring_matches = list(dict.fromkeys(substring_matches))
    if len(unique_substring_matches) == 1:
        return unique_substring_matches[0], "matched"
    if len(unique_substring_matches) > 1:
        return None, "ambiguous-match"

    return None, "phrase-not-found"


def _coerce_state_dict(state: Any) -> dict[str, Any]:
    """Convert LangGraph node state objects to a plain dictionary."""
    if isinstance(state, dict):
        return state

    model_dump = getattr(state, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped

    to_dict = getattr(state, "dict", None)
    if callable(to_dict):
        dumped = to_dict()
        if isinstance(dumped, dict):
            return dumped

    raise TypeError(
        f"Cannot coerce state of type {type(state).__name__} to dict. "
        "Expected a dict, Pydantic model, or object with .dict()/.model_dump()."
    )


# ────────────────────────────────────────────────────────────────────
# Prompt Resolution
# ────────────────────────────────────────────────────────────────────

def _resolve_prompt(version: str) -> str:
    """Resolve a dual-agent prompt version to its text."""
    prompt = DUAL_AGENT_PROMPTS.get(version)
    if prompt is None:
        available = ", ".join(sorted(DUAL_AGENT_PROMPTS))
        raise ValueError(
            f"Unknown dual-agent prompt version: {version}. "
            f"Available: {available}"
        )
    return prompt


# ────────────────────────────────────────────────────────────────────
# Graph Construction
# ────────────────────────────────────────────────────────────────────

def build_dual_agent_graph(
    llm: LLMClient,
    reasoner_prompt_version: str | None = None,
    matcher_prompt_version: str | None = None,
) -> Any:
    """Construct the dual-agent reasoning graph.
    
    Args:
        llm: The LLM client to use for both agents.
        reasoner_prompt_version: Registry key for Agent 1 prompt.
            Defaults to DEFAULT_DUAL_AGENT_VERSIONS["reasoner"].
        matcher_prompt_version: Registry key for Agent 2 prompt.
            Defaults to DEFAULT_DUAL_AGENT_VERSIONS["matcher"].
    
    Returns:
        A compiled LangGraph state graph.
    """
    reasoner_prompt = _resolve_prompt(
        reasoner_prompt_version or DEFAULT_DUAL_AGENT_VERSIONS["reasoner"]
    )
    matcher_prompt = _resolve_prompt(
        matcher_prompt_version or DEFAULT_DUAL_AGENT_VERSIONS["matcher"]
    )

    graph_builder = StateGraph(DualAgentState)
    graph_builder.add_node(
        "agent1",
        lambda state: agent1_reason(_coerce_state_dict(state), llm, reasoner_prompt),
    )
    graph_builder.add_node(
        "agent2",
        lambda state: agent2_decide(_coerce_state_dict(state), llm, matcher_prompt),
    )
    graph_builder.add_edge(START, "agent1")
    graph_builder.add_edge("agent1", "agent2")
    graph_builder.add_edge("agent2", END)
    return graph_builder.compile()


# ────────────────────────────────────────────────────────────────────
# Public Interface
# ────────────────────────────────────────────────────────────────────

def run_dual_agent(
    llm: LLMClient,
    relevant_beliefs: str,
    query: str,
    options: dict[str, str],
    *,
    chat_history: list[dict[str, str]] | None = None,
    compiled_graph: Any | None = None,
    reasoner_prompt_version: str | None = None,
    matcher_prompt_version: str | None = None,
) -> dict[str, Any]:
    """Run the dual-agent system on a single turn.

    Args:
        llm: The LLM client.
        relevant_beliefs: Serialized belief text for Agent 1.
        query: The user query / question text.
        options: Mapping of option labels (A/B/C) to phrase texts.
        compiled_graph: Optional pre-compiled graph to reuse.
            If None, a new graph is compiled (slower for loops).
        reasoner_prompt_version: Registry key for Agent 1 prompt.
        matcher_prompt_version: Registry key for Agent 2 prompt.

    Returns:
        Dict with agent1_* and agent2_* fields, plus full_response.
    """
    if compiled_graph is not None:
        graph = compiled_graph
    else:
        graph = build_dual_agent_graph(
            llm,
            reasoner_prompt_version=reasoner_prompt_version,
            matcher_prompt_version=matcher_prompt_version,
        )

    initial_state: DualAgentState = {
        "relevant_beliefs": relevant_beliefs,
        "query": query,
        "options": options,
        "chat_history": chat_history or [],
    }

    final_state = graph.invoke(initial_state)

    return {
        "agent1_conclusion": final_state.get("conclusion", ""),
        "agent1_evidence_keys": final_state.get("evidence_keys", []),
        "agent1_reasoning": final_state.get("reasoning", ""),
        "agent2_matched_option_text": final_state.get("matched_option_text", ""),
        "agent2_matcher_rationale": final_state.get("matcher_rationale", ""),
        "agent2_matched_option_label": final_state.get("matched_option_label", ""),
        "agent2_match_status": final_state.get("match_status", "phrase-not-found"),
        # Backward-compatible alias while downstream migrates.
        "agent2_answer": final_state.get("matched_option_text", ""),
        "full_response": dict(final_state),
    }
