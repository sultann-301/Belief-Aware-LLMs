"""Controlled graph-retrieval baseline with benchmark-supplied targets.

Only the LLM executes rules. The adapter reads the store's rule topology but
never resolves beliefs. This is custom dependency-graph RAG, not Microsoft
GraphRAG. Retrieval sees attributes and asserted facts, never the answer key.
"""

from __future__ import annotations

from dataclasses import replace

from belief_store.llm_client import LLMClient
from evaluation.answer_extraction import _enforce_exact_phrase_output
from evaluation.eval_common import DomainConfig, _format_question, _process_result
from evaluation.graphrag.graph import GraphSlice
from evaluation.graphrag.domain_adapter import build_domain_graph
from evaluation.prompting import build_baseline_prompt, build_baseline_system_prompt


CONDITION = "GRAPH RETRIEVAL (SUPPLIED TARGETS)"
RETRIEVER_VERSION = "domain-dependency-v2"


def snapshot_config(config: DomainConfig, turns: list[dict] | None = None) -> DomainConfig:
    """Use the actual evaluated turn sequence and disable assistant history.

    Conversational source scenarios still accumulate input updates. Replacing
    config.turns also makes the existing runners accumulate from this sequence.
    """
    return replace(
        config,
        turns=list(config.turns if turns is None else turns),
        is_conversational=False,
        accumulate_prior_beliefs=config.is_conversational or config.accumulate_prior_beliefs,
        seed_fn=None,
    )


def fact_snapshots(config: DomainConfig) -> list[dict]:
    """Materialize current asserted inputs without running any derivations."""
    current = dict(config.initial_beliefs)
    snapshots = []
    for turn in config.turns:
        if not (config.is_conversational or config.accumulate_prior_beliefs):
            current = dict(config.initial_beliefs)
        current.update(turn.get("beliefs") or {})
        snapshots.append(dict(current))
    return snapshots


def retrieve_slices(config: DomainConfig) -> list[GraphSlice]:
    """Validate and retrieve all turns before spending any generation calls."""
    slices = []
    for turn, facts in zip(config.turns, fact_snapshots(config)):
        targets = turn.get("attributes")
        if not isinstance(targets, (list, tuple)) or not targets:
            raise ValueError("Controlled graph retrieval requires supplied target attributes.")
        if any(not isinstance(target, str) for target in targets):
            raise ValueError("Target attributes must be strings.")
        graph = build_domain_graph(config.setup_fn, config.baseline_rules, facts)
        outputs = {rule.output for rule in graph.rules}
        unknown = set(targets) - outputs - facts.keys()
        if unknown:
            raise ValueError(f"Unknown supplied targets: {sorted(unknown)}")
        slices.append(graph.subgraph_for(targets))
    return slices


def serialize_slice(graph_slice: GraphSlice) -> tuple[str, list[str]]:
    """Return rule text and asserted fact assignments as separate sections."""
    derived_keys = {rule.output for rule in graph_slice.rules}
    if derived_keys & graph_slice.facts.keys():
        raise ValueError("Retrieved facts must not include computed values.")
    rules = "[RULES]\n" + "\n".join(rule.text for rule in graph_slice.rules)
    facts = [f"{key} = {value}" for key, value in sorted(graph_slice.facts.items())]
    return rules, facts


def build_graph_prompt(graph_slice: GraphSlice, turn: dict) -> str:
    rules, facts = serialize_slice(graph_slice)
    return build_baseline_prompt(rules, facts, _format_question(turn))


def run_with_graph_retrieval(
    llm: LLMClient,
    config: DomainConfig,
    turns: list[dict] | None = None,
    baseline_prompt_version: str | None = None,
    debug_log_dir: str | None = None,
    debug_logs_enabled: bool = True,
) -> list[dict]:
    """Use the plain baseline's prompt format, with only retrieved context.

    Each call has fresh messages. Retrieval metrics record actual rules/facts;
    the store's text-key coverage metrics are intentionally not used here.
    """
    config = snapshot_config(config, turns)
    slices = retrieve_slices(config)
    system_prompt = build_baseline_system_prompt(baseline_prompt_version)
    results = []
    for index, (turn, graph_slice) in enumerate(zip(config.turns, slices), start=1):
        prompt = build_graph_prompt(graph_slice, turn)
        raw_response, logprobs = llm.generate_with_history_and_logprobs([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ])
        response = _enforce_exact_phrase_output(turn, raw_response)
        rules, facts = serialize_slice(graph_slice)
        result = _process_result(
            CONDITION, index, turn, response,
            logprobs_data=logprobs,
            debug_log_dir=debug_log_dir,
            debug_logs_enabled=debug_logs_enabled,
            extra_fields={
                "retriever_version": RETRIEVER_VERSION,
                "target_mode": "supplied",
                "selected_targets": list(graph_slice.targets),
                "retrieved_rules": [rule.output for rule in graph_slice.rules],
                "retrieved_facts": dict(graph_slice.facts),
                "retrieved_rule_count": len(graph_slice.rules),
                "retrieved_fact_count": len(graph_slice.facts),
                "context_chars": len(rules) + len("\n".join(facts)),
                "system_prompt": system_prompt,
                "prompt": prompt,
            },
        )
        results.append(result)
    return results
