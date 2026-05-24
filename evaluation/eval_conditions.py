"""eval_conditions.py — Evaluation condition runners.

Provides the actual evaluation execution functions that run turns against the LLM:
  - run_with_store: [1] WITH Store (stateless, no chat history)
  - run_with_store_with_history: [2] WITH Store + chat history
  - run_without_store: [3] NO Store baseline
  - run_with_store_dual_agent: [4] Dual-agent condition
  - _run_standard_eval_task: Thread-pool task wrapper (standard)
  - _run_dual_agent_eval_task: Thread-pool task wrapper (dual-agent)
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from belief_store.store import BeliefStore
from belief_store.llm_client import OllamaClient
from belief_store.langgraph_dual_agent import run_dual_agent, build_dual_agent_graph
from evaluation.prompting import (
    build_baseline_system_prompt,
    build_baseline_prompt as _build_baseline_prompt,
    build_store_prompt as _build_store_prompt,
)
from evaluation.answer_extraction import _enforce_exact_phrase_output
from evaluation.eval_metrics import (
    _get_reasoning_metrics,
    _build_dual_agent_response,
    _compute_dual_agent_metrics,
)
from evaluation.eval_common import (
    DomainConfig,
    _init_store,
    _accumulate_prior_beliefs,
    _get_filter_spec,
    _resolve_and_serialize,
    _format_question,
    _resolve_eval_system_prompt,
    _create_ollama_client,
    _process_result,
)


# ────────────────────────────────────────────────────────────────────
# Standard Conditions
# ────────────────────────────────────────────────────────────────────

def run_with_store(llm: OllamaClient, config: DomainConfig, turns: list[dict] | None = None) -> list[dict]:
    """[1] WITH Store (Stateless): Fresh store per turn, no chat history."""
    results = []
    eval_system_prompt = _resolve_eval_system_prompt(config)
    t_list = turns if turns is not None else config.turns

    for i, turn in enumerate(t_list):
        store = _init_store(config)

        # Accumulate prior turn beliefs if configured
        if config.is_conversational or config.accumulate_prior_beliefs:
            accumulated = _accumulate_prior_beliefs(config, i)
            for key, value in accumulated.items():
                store.add_hypothesis(key, value)

        # Add current turn beliefs
        if turn.get("beliefs"):
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)

        # Serialize beliefs for the prompt
        filter_spec, is_attr = _get_filter_spec(turn, config.default_entities)
        beliefs_text = _resolve_and_serialize(store, filter_spec, is_attr)

        # Build and send prompt
        question = _format_question(turn)
        prompt = _build_store_prompt(beliefs_text, question)

        raw_response, logprobs_data = llm.generate_with_logprobs(eval_system_prompt, prompt)
        response = _enforce_exact_phrase_output(turn, raw_response)

        reasoning = _get_reasoning_metrics(store, filter_spec, is_attr, raw_response,
                                           beliefs_text=beliefs_text)
        results.append(_process_result("WITH STORE", i + 1, turn, response,
                                       extra_fields=reasoning or None,
                                       logprobs_data=logprobs_data))

    return results


def run_with_store_with_history(llm: OllamaClient, config: DomainConfig, turns: list[dict] | None = None) -> list[dict]:
    """[2] WITH Store + Chat History: Store-derived beliefs + conversational context."""
    results = []
    t_list = turns if turns is not None else config.turns
    eval_system_prompt = _resolve_eval_system_prompt(config)

    # Base messages tracking
    base_messages = [{"role": "system", "content": eval_system_prompt}]
    messages = base_messages.copy()

    # For conversational: maintain one store across all turns
    store: BeliefStore | None = _init_store(config) if config.is_conversational else None

    for i, turn in enumerate(config.turns):
        # Store management
        if config.is_conversational:
            assert store is not None
            # Add turn beliefs to persistent store
            if turn.get("beliefs"):
                for key, value in turn["beliefs"].items():
                    store.add_hypothesis(key, value)
            current_store = store
        else:
            # Snapshot mode: fresh store per turn
            current_store = _init_store(config)

            # Optionally accumulate prior beliefs
            if config.accumulate_prior_beliefs:
                accumulated = _accumulate_prior_beliefs(config, i)
                for key, value in accumulated.items():
                    current_store.add_hypothesis(key, value)

            # Add current turn beliefs
            if turn.get("beliefs"):
                for key, value in turn["beliefs"].items():
                    current_store.add_hypothesis(key, value)

        # Serialize beliefs for the prompt
        filter_spec, is_attr = _get_filter_spec(turn, config.default_entities)
        beliefs_text = _resolve_and_serialize(current_store, filter_spec, is_attr)

        # Build and send prompt as part of chat history
        question = _format_question(turn)
        prompt = _build_store_prompt(beliefs_text, question)

        if not config.is_conversational:
            # Snapshot mode: start from a fresh chat history each turn
            messages = base_messages.copy()

        messages.append({"role": "user", "content": prompt})
        raw_response, logprobs_data = llm.generate_with_history_and_logprobs(messages)
        response = _enforce_exact_phrase_output(turn, raw_response)
        messages.append({"role": "assistant", "content": response})

        reasoning = _get_reasoning_metrics(current_store, filter_spec, is_attr, raw_response,
                                           beliefs_text=beliefs_text)
        results.append(_process_result("WITH STORE (+History)", i + 1, turn, response,
                                       extra_fields=reasoning or None,
                                       logprobs_data=logprobs_data))

    return results


def run_without_store(
    llm: OllamaClient,
    config: DomainConfig,
    turns: list[dict] | None = None,
    baseline_prompt_version: str | None = None,
) -> list[dict]:
    """[3] NO Store (Baseline): Rules + chat history only, no explicit belief tracking."""
    results = []
    t_list = turns if turns is not None else config.turns
    system_prompt = build_baseline_system_prompt(baseline_prompt_version)
    base_messages = [{"role": "system", "content": system_prompt}]
    messages = base_messages.copy()
    initial_belief_lines = [f"{k} = {v}" for k, v in config.initial_beliefs.items()]

    for i, turn in enumerate(t_list):
        if config.is_conversational:
            # Conversational mode: relying on chat history for prior context
            if i == 0:
                belief_lines = initial_belief_lines
            else:
                belief_lines = [f"{k} = {v}" for k, v in (turn.get("beliefs") or {}).items()]
        else:
            # Snapshot mode: start from fresh history and reconstruct full belief state
            messages = base_messages.copy()
            belief_state = config.initial_beliefs.copy()

            if config.accumulate_prior_beliefs:
                accumulated = _accumulate_prior_beliefs(config, i)
                belief_state.update(accumulated)

            if turn.get("beliefs"):
                belief_state.update(turn["beliefs"])

            belief_lines = [f"{k} = {v}" for k, v in belief_state.items()]

        # Build and send prompt as part of chat history
        question = _format_question(turn)
        prompt = _build_baseline_prompt(config.baseline_rules, belief_lines, question)

        messages.append({"role": "user", "content": prompt})
        raw_response, logprobs_data = llm.generate_with_history_and_logprobs(messages)
        response = _enforce_exact_phrase_output(turn, raw_response)
        messages.append({"role": "assistant", "content": response})

        results.append(_process_result("NO STORE", i + 1, turn, response,
                                       logprobs_data=logprobs_data))

    return results


# ────────────────────────────────────────────────────────────────────
# Dual-Agent Condition
# ────────────────────────────────────────────────────────────────────

def run_with_store_dual_agent(
    llm: OllamaClient,
    config: DomainConfig,
    reasoner_model: str | None = None,
    matcher_model: str | None = None,
    turns: list[dict] | None = None,
) -> list[dict]:
    """[4] WITH Store (Dual-Agent): Fresh store per turn, decoupled reasoning+decision, no chat history."""
    results = []
    t_list = turns if turns is not None else config.turns
    # Pre-compile graph once for all turns
    graph = build_dual_agent_graph(llm, reasoner_model=reasoner_model, matcher_model=matcher_model)

    for i, turn in enumerate(t_list):
        store = _init_store(config)

        # Accumulate prior turn beliefs if configured
        if config.is_conversational or config.accumulate_prior_beliefs:
            accumulated = _accumulate_prior_beliefs(config, i)
            for key, value in accumulated.items():
                store.add_hypothesis(key, value)

        # Add current turn beliefs
        if turn.get("beliefs"):
            for key, value in turn["beliefs"].items():
                store.add_hypothesis(key, value)

        # Serialize beliefs for the prompt
        filter_spec, is_attr = _get_filter_spec(turn, config.default_entities)
        beliefs_text = _resolve_and_serialize(store, filter_spec, is_attr)

        # Run dual-agent system
        dual_agent_result = run_dual_agent(
            llm=llm,
            relevant_beliefs=beliefs_text,
            query=turn["question"],
            options=turn.get("options", {}),
            compiled_graph=graph,
        )

        # Build a response string for logging and extraction compatibility
        response = _build_dual_agent_response(dual_agent_result)

        # Enforce exact phrase output format for compatibility with extraction logic
        response = _enforce_exact_phrase_output(turn, response)
        split_metrics = _compute_dual_agent_metrics(turn, dual_agent_result)

        cited_override = set(dual_agent_result.get("agent1_evidence_keys", []))
        reasoning = _get_reasoning_metrics(
            store, filter_spec, is_attr, response,
            cited_keys_override=cited_override,
            beliefs_text=beliefs_text,
        )
        split_metrics.update(reasoning)

        results.append(
            _process_result(
                "WITH STORE (Dual-Agent)",
                i + 1,
                turn,
                response,
                extra_fields=split_metrics,
            )
        )

    return results


# ────────────────────────────────────────────────────────────────────
# Thread-Pool Task Wrappers
# ────────────────────────────────────────────────────────────────────

def _run_standard_eval_task(
    condition: int,
    config: DomainConfig,
    model: str,
    temperature: float,
    ollama_options: dict[str, object] | None,
    cache_path: str | None,
    cache_enabled: bool,
    baseline_prompt_version: str | None = None,
    turns: list[dict] | None = None,
) -> list[dict]:
    """Run one standard eval task with its own Ollama client instance."""
    llm = _create_ollama_client(model, temperature, ollama_options, cache_path, cache_enabled)
    t_list = turns if turns is not None else config.turns
    if condition == 0:
        return run_with_store(llm, config, turns=t_list)
    return run_without_store(llm, config, turns=t_list, baseline_prompt_version=baseline_prompt_version)


def _run_dual_agent_eval_task(
    config: DomainConfig,
    model: str,
    temperature: float,
    reasoner_model: str,
    matcher_model: str,
    ollama_options: dict[str, object] | None,
    cache_path: str | None,
    cache_enabled: bool,
    turns: list[dict] | None = None,
) -> list[dict]:
    """Run one dual-agent eval task with its own Ollama client instance."""
    llm = _create_ollama_client(model, temperature, ollama_options, cache_path, cache_enabled)
    t_list = turns if turns is not None else config.turns
    return run_with_store_dual_agent(llm, config, reasoner_model, matcher_model, turns=t_list)
