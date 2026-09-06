#!/usr/bin/env python3
"""Run configured evaluation batches.

This script intentionally keeps experiment choices in JSON config files instead
of editing Python globals for each thesis run.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from os.path import dirname, join
from typing import Any

sys.path.insert(0, join(dirname(__file__), ".."))

DEFAULT_CONFIG_PATH = "evaluation/configs/thesis_dual_agent_batch.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "standard",
    "eval_prompt_versions": ["v15"],
    "baseline_prompt_version": "v1",
    "models": ["gemma3:1b"],
    "hard_scenario_excluded_models": [],
    "dual_agent_pairs": [["gemma3:1b", "gemma3:1b"]],
    "temperatures": [0.0],
    "domains": ["loan"],
    "phase1_domains": [],
    "phase2_domains": [],
    "runs_per_config": 10,
    "phase1_runs": 10,
    "phase2_runs": 5,
    "workers": 4,
    "fast_eval": False,
    "cooldown_seconds": 0,
    "state_file": None,
    "log_file": None,
    "csv_out": None,
    "debug_log_dir": None,
    "debug_logs_enabled": True,
    "ollama": {
        "num_predict": None,
        "num_ctx": None,
        "repeat_penalty": None,
        "repeat_last_n": None,
        "top_k": None,
        "top_p": None,
        "keep_alive": None,
    },
    "cache": {
        "enabled": False,
        "dir": ".cache/ollama_eval",
    },
}

VALID_MODES = {"standard", "dual-agent", "sequential"}
CONFIG_KEYS = set(DEFAULT_CONFIG)
OLLAMA_KEYS = set(DEFAULT_CONFIG["ollama"])
CACHE_KEYS = set(DEFAULT_CONFIG["cache"])


class ConfigError(ValueError):
    """Raised when a batch config is invalid."""


def _deep_update(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_update(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_str_list(
    config: Mapping[str, Any],
    key: str,
    errors: list[str],
    *,
    non_empty: bool = False,
) -> list[str]:
    value = config.get(key)
    if not isinstance(value, list):
        errors.append(f"'{key}' must be a list of strings.")
        return []
    if non_empty and not value:
        errors.append(f"'{key}' must contain at least one value.")
    invalid = [item for item in value if not isinstance(item, str) or not item]
    if invalid:
        errors.append(f"'{key}' must contain only non-empty strings.")
    return [item for item in value if isinstance(item, str)]


def _validate_number_list(
    config: Mapping[str, Any],
    key: str,
    errors: list[str],
    *,
    non_empty: bool = False,
) -> list[int | float]:
    value = config.get(key)
    if not isinstance(value, list):
        errors.append(f"'{key}' must be a list of numbers.")
        return []
    if non_empty and not value:
        errors.append(f"'{key}' must contain at least one value.")
    invalid = [item for item in value if not _is_number(item)]
    if invalid:
        errors.append(f"'{key}' must contain only numeric values.")
    return [item for item in value if _is_number(item)]


def _validate_optional_path(config: Mapping[str, Any], key: str, errors: list[str]) -> None:
    value = config.get(key)
    if value is not None and (not isinstance(value, str) or not value):
        errors.append(f"'{key}' must be a non-empty string when provided.")


def _validate_positive_int(config: Mapping[str, Any], key: str, errors: list[str]) -> None:
    if not _is_positive_int(config.get(key)):
        errors.append(f"'{key}' must be a positive integer.")


def _validate_non_negative_int(config: Mapping[str, Any], key: str, errors: list[str]) -> None:
    if not _is_non_negative_int(config.get(key)):
        errors.append(f"'{key}' must be a non-negative integer.")


def _available_domains() -> set[str]:
    from evaluation.run_evals import DOMAIN_REGISTRY

    return set(DOMAIN_REGISTRY)


def _validate_domains(domain_names: list[str], key: str, errors: list[str]) -> None:
    valid_domains = _available_domains()
    unknown = sorted(set(domain_names) - valid_domains)
    if unknown:
        errors.append(
            f"'{key}' contains unknown domain(s): {', '.join(unknown)}. "
            f"Use one of: {', '.join(sorted(valid_domains))}."
        )


def _validate_prompt_versions(eval_prompts: list[str], baseline_prompt: Any, errors: list[str]) -> None:
    from evaluation.prompting import build_baseline_system_prompt, build_eval_system_prompt

    for prompt in eval_prompts:
        try:
            build_eval_system_prompt(prompt)
        except ValueError as exc:
            errors.append(str(exc))

    if not isinstance(baseline_prompt, str) or not baseline_prompt:
        errors.append("'baseline_prompt_version' must be a non-empty string.")
        return

    try:
        build_baseline_system_prompt(baseline_prompt)
    except ValueError as exc:
        errors.append(str(exc))


def _validate_dual_agent_pairs(config: Mapping[str, Any], errors: list[str]) -> list[list[str]]:
    pairs = config.get("dual_agent_pairs")
    if not isinstance(pairs, list):
        errors.append("'dual_agent_pairs' must be a list of [reasoner_model, matcher_model] pairs.")
        return []
    if not pairs:
        errors.append("'dual_agent_pairs' must contain at least one pair.")

    valid_pairs = []
    for index, pair in enumerate(pairs):
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or not all(isinstance(model, str) and model for model in pair)
        ):
            errors.append(
                f"'dual_agent_pairs[{index}]' must be [reasoner_model, matcher_model] "
                "with two non-empty strings."
            )
            continue
        valid_pairs.append(pair)
    return valid_pairs


def _validate_ollama_config(config: Mapping[str, Any], errors: list[str]) -> None:
    ollama = config.get("ollama")
    if not isinstance(ollama, Mapping):
        errors.append("'ollama' must be an object.")
        return

    unknown = sorted(set(ollama) - OLLAMA_KEYS)
    if unknown:
        errors.append(f"'ollama' contains unknown key(s): {', '.join(unknown)}.")

    for key in ["num_predict", "num_ctx", "repeat_last_n", "top_k"]:
        value = ollama.get(key)
        if value is not None and not _is_positive_int(value):
            errors.append(f"'ollama.{key}' must be a positive integer when provided.")

    for key in ["repeat_penalty", "top_p"]:
        value = ollama.get(key)
        if value is not None and not _is_number(value):
            errors.append(f"'ollama.{key}' must be numeric when provided.")

    top_p = ollama.get("top_p")
    if _is_number(top_p) and not 0 <= top_p <= 1:
        errors.append("'ollama.top_p' must be between 0 and 1 when provided.")

    keep_alive = ollama.get("keep_alive")
    if keep_alive is not None and (not isinstance(keep_alive, str) or not keep_alive):
        errors.append("'ollama.keep_alive' must be a non-empty string when provided.")


def _validate_cache_config(config: Mapping[str, Any], errors: list[str]) -> None:
    cache = config.get("cache")
    if not isinstance(cache, Mapping):
        errors.append("'cache' must be an object.")
        return

    unknown = sorted(set(cache) - CACHE_KEYS)
    if unknown:
        errors.append(f"'cache' contains unknown key(s): {', '.join(unknown)}.")

    if not isinstance(cache.get("enabled"), bool):
        errors.append("'cache.enabled' must be true or false.")

    cache_dir = cache.get("dir")
    if not isinstance(cache_dir, str) or not cache_dir:
        errors.append("'cache.dir' must be a non-empty string.")


def validate_config(config: Mapping[str, Any]) -> None:
    """Validate a loaded batch config before any long-running subprocesses start."""
    errors: list[str] = []

    unknown = sorted(set(config) - CONFIG_KEYS)
    if unknown:
        errors.append(f"Unknown config key(s): {', '.join(unknown)}.")

    mode = config.get("mode")
    if mode not in VALID_MODES:
        errors.append(f"'mode' must be one of: {', '.join(sorted(VALID_MODES))}.")

    eval_prompts = _validate_str_list(config, "eval_prompt_versions", errors, non_empty=True)
    _validate_prompt_versions(eval_prompts, config.get("baseline_prompt_version"), errors)
    _validate_number_list(config, "temperatures", errors, non_empty=True)

    for key in ["runs_per_config", "phase1_runs", "phase2_runs", "workers"]:
        _validate_positive_int(config, key, errors)
    _validate_non_negative_int(config, "cooldown_seconds", errors)

    for key in ["fast_eval", "debug_logs_enabled"]:
        if not isinstance(config.get(key), bool):
            errors.append(f"'{key}' must be true or false.")

    for key in ["state_file", "log_file", "csv_out", "debug_log_dir"]:
        _validate_optional_path(config, key, errors)

    _validate_ollama_config(config, errors)
    _validate_cache_config(config, errors)

    if mode in {"standard", "sequential"}:
        _validate_str_list(config, "models", errors, non_empty=True)
    else:
        _validate_str_list(config, "models", errors)

    _validate_str_list(config, "hard_scenario_excluded_models", errors)
    _validate_dual_agent_pairs(config, errors)

    domains = _validate_str_list(
        config,
        "domains",
        errors,
        non_empty=(mode in {"standard", "dual-agent"}),
    )
    phase1_domains = _validate_str_list(
        config,
        "phase1_domains",
        errors,
        non_empty=(mode == "sequential"),
    )
    phase2_domains = _validate_str_list(config, "phase2_domains", errors)

    _validate_domains(domains, "domains", errors)
    _validate_domains(phase1_domains, "phase1_domains", errors)
    _validate_domains(phase2_domains, "phase2_domains", errors)

    if errors:
        details = "\n  - ".join(errors)
        raise ConfigError(f"Invalid batch config:\n  - {details}")


def load_config(path: str | None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if path:
        with open(path, "r", encoding="utf-8") as f:
            config = _deep_update(config, json.load(f))
    return config


def _as_list(config: Mapping[str, Any], key: str) -> list[Any]:
    value = config.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"Config key '{key}' must be a list")
    return value


def _state_file(config: Mapping[str, Any], mode: str) -> str:
    configured = config.get("state_file")
    if configured:
        return str(configured)
    return f"evaluation/batch_state_{mode}.json"


def _log_file(config: Mapping[str, Any], mode: str) -> str:
    configured = config.get("log_file")
    if configured:
        return str(configured)
    return f"evaluation/batch_progress_{mode}.log"


def print_progress(current: int, total: int) -> None:
    if total <= 0:
        return
    percent = 100 * (current / total)
    bar_length = 40
    filled_length = int(bar_length * current // total)
    bar = "#" * filled_length + "-" * (bar_length - filled_length)
    sys.stdout.write(f"\rProgress: |{bar}| {percent:.1f}% ({current}/{total})")
    sys.stdout.flush()


def log(msg: str, log_file: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def load_state(state_file: str) -> dict[str, list[str]]:
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                return {"completed": []}
        completed = state.get("completed", [])
        return {"completed": completed if isinstance(completed, list) else []}
    return {"completed": []}


def save_state(state: Mapping[str, Any], state_file: str) -> None:
    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _append_ollama_options(cmd: list[str], config: Mapping[str, Any]) -> None:
    if config.get("fast_eval"):
        cmd.append("--fast-eval")

    ollama = config.get("ollama", {})
    if not isinstance(ollama, Mapping):
        raise TypeError("Config key 'ollama' must be an object")

    option_flags = {
        "num_predict": "--num-predict",
        "num_ctx": "--num-ctx",
        "repeat_penalty": "--repeat-penalty",
        "repeat_last_n": "--repeat-last-n",
        "top_k": "--top-k",
        "top_p": "--top-p",
        "keep_alive": "--keep-alive",
    }
    for key, flag in option_flags.items():
        value = ollama.get(key)
        if value is not None:
            cmd += [flag, str(value)]

    cache = config.get("cache", {})
    if not isinstance(cache, Mapping):
        raise TypeError("Config key 'cache' must be an object")
    if cache.get("enabled"):
        cmd += ["--cache", "--cache-dir", str(cache.get("dir", ".cache/ollama_eval"))]

    if config.get("csv_out"):
        cmd += ["--csv-out", str(config["csv_out"])]
    if config.get("debug_log_dir"):
        cmd += ["--log-dir", str(config["debug_log_dir"])]
    if not config.get("debug_logs_enabled", True):
        cmd.append("--no-debug-logs")


def _standard_cmd(
    config: Mapping[str, Any],
    model: str,
    prompt: str,
    temperature: float,
    domain: str,
    runs: int,
) -> list[str]:
    cmd = [
        sys.executable,
        "evaluation/run_evals.py",
        "--domain",
        domain,
        "--model",
        model,
        "--eval-prompt-version",
        prompt,
        "--baseline-prompt-version",
        str(config["baseline_prompt_version"]),
        "--runs",
        str(runs),
        "--workers",
        str(config["workers"]),
        "--temperature",
        str(temperature),
    ]
    _append_ollama_options(cmd, config)
    return cmd


def _dual_agent_cmd(
    config: Mapping[str, Any],
    reasoner_model: str,
    matcher_model: str,
    prompt: str,
    temperature: float,
    domain: str,
    runs: int,
) -> list[str]:
    cmd = [
        sys.executable,
        "evaluation/run_evals.py",
        "--domain",
        domain,
        "--dual-agent",
        "--reasoner-model",
        reasoner_model,
        "--matcher-model",
        matcher_model,
        "--eval-prompt-version",
        prompt,
        "--baseline-prompt-version",
        str(config["baseline_prompt_version"]),
        "--runs",
        str(runs),
        "--workers",
        str(config["workers"]),
        "--temperature",
        str(temperature),
    ]
    _append_ollama_options(cmd, config)
    return cmd


def _run_command(
    config_id: str,
    cmd: list[str],
    state: dict[str, list[str]],
    state_file: str,
    log_file: str,
    dry_run: bool,
) -> None:
    if dry_run:
        log(f"DRY RUN: {config_id}\nCommand: {' '.join(cmd)}", log_file)
        return

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        log(f"SUCCESS: {config_id}", log_file)
        state.setdefault("completed", []).append(config_id)
        save_state(state, state_file)
        return

    stderr = result.stderr.strip()
    stdout = result.stdout.strip()
    details = stderr or stdout or "(no output)"
    log(f"FAILURE: {config_id}\nError: {details}", log_file)


def _cooldown(seconds: int, log_file: str, dry_run: bool) -> None:
    if dry_run or seconds <= 0:
        return
    log(f"Cooldown: Sleeping for {seconds} seconds...", log_file)
    for remaining in range(seconds, 0, -1):
        sys.stdout.write(f"\rCooling down... {remaining}s remaining   ")
        sys.stdout.flush()
        time.sleep(1)
    print()


def run_standard_batch(
    config: Mapping[str, Any],
    state: dict[str, list[str]],
    state_file: str,
    log_file: str,
    dry_run: bool,
) -> None:
    configs = []
    excluded = set(_as_list(config, "hard_scenario_excluded_models"))
    for model in _as_list(config, "models"):
        for prompt in _as_list(config, "eval_prompt_versions"):
            for temperature in _as_list(config, "temperatures"):
                for domain in _as_list(config, "domains"):
                    if str(domain).endswith("_hard") and model in excluded:
                        continue
                    configs.append(("std", model, prompt, temperature, domain))

    log(f"Starting STANDARD Batch Eval: {len(configs)} total configurations planned.", log_file)
    log(f"Already completed: {len(state.get('completed', []))}", log_file)

    for i, (prefix, model, prompt, temperature, domain) in enumerate(configs):
        config_id = f"{prefix}|{model}|{prompt}|{temperature}|{domain}"
        if config_id in state.get("completed", []):
            continue

        print_progress(i, len(configs))
        print()
        runs = int(config["runs_per_config"])
        log(f"RUNNING: {domain} | Model: {model} | Prompt: {prompt} | Temp: {temperature} | Runs: {runs}", log_file)
        cmd = _standard_cmd(config, str(model), str(prompt), float(temperature), str(domain), runs)
        try:
            _run_command(config_id, cmd, state, state_file, log_file, dry_run)
            _cooldown(int(config["cooldown_seconds"]), log_file, dry_run)
        except Exception as exc:
            log(f"CRITICAL ERROR running {config_id}: {exc}", log_file)

    print_progress(len(configs), len(configs))
    print()
    log("Standard Batch Evaluation Complete!", log_file)


def run_dual_agent_batch(
    config: Mapping[str, Any],
    state: dict[str, list[str]],
    state_file: str,
    log_file: str,
    dry_run: bool,
) -> None:
    configs = []
    for pair in _as_list(config, "dual_agent_pairs"):
        if not isinstance(pair, list | tuple) or len(pair) != 2:
            raise TypeError("Each dual_agent_pairs item must be [reasoner_model, matcher_model]")
        reasoner_model, matcher_model = pair
        for prompt in _as_list(config, "eval_prompt_versions"):
            for temperature in _as_list(config, "temperatures"):
                for domain in _as_list(config, "domains"):
                    configs.append(("da", reasoner_model, matcher_model, prompt, temperature, domain))

    log(f"Starting DUAL-AGENT Batch Eval: {len(configs)} total configurations planned.", log_file)
    log(f"Already completed: {len(state.get('completed', []))}", log_file)
    log(f"Model pairs: {_as_list(config, 'dual_agent_pairs')}", log_file)
    log(f"Domains: {_as_list(config, 'domains')}", log_file)
    log(f"Temperatures: {_as_list(config, 'temperatures')}", log_file)

    for i, (prefix, reasoner_model, matcher_model, prompt, temperature, domain) in enumerate(configs):
        config_id = f"{prefix}|{reasoner_model}|{matcher_model}|{prompt}|{temperature}|{domain}"
        if config_id in state.get("completed", []):
            continue

        print_progress(i, len(configs))
        print()
        runs = int(config["phase2_runs"])
        log(
            f"RUNNING: {domain} | Reasoner: {reasoner_model} | Matcher: {matcher_model} "
            f"| Prompt: {prompt} | Temp: {temperature} | Runs: {runs}",
            log_file,
        )
        cmd = _dual_agent_cmd(config, str(reasoner_model), str(matcher_model), str(prompt), float(temperature), str(domain), runs)
        try:
            _run_command(config_id, cmd, state, state_file, log_file, dry_run)
            _cooldown(int(config["cooldown_seconds"]), log_file, dry_run)
        except Exception as exc:
            log(f"CRITICAL ERROR running {config_id}: {exc}", log_file)

    print_progress(len(configs), len(configs))
    print()
    log("Dual-Agent Batch Evaluation Complete!", log_file)


def run_sequential_batch(
    config: Mapping[str, Any],
    state: dict[str, list[str]],
    state_file: str,
    log_file: str,
    dry_run: bool,
) -> None:
    phase1_domains = _as_list(config, "phase1_domains")
    phase2_domains = _as_list(config, "phase2_domains") or phase1_domains

    phase1_configs = []
    for model in _as_list(config, "models"):
        for prompt in _as_list(config, "eval_prompt_versions"):
            for temperature in _as_list(config, "temperatures"):
                for domain in phase1_domains:
                    phase1_configs.append(("std", model, prompt, temperature, domain))

    log(f"Starting SEQUENTIAL Phase A (single-agent): {len(phase1_configs)} configurations planned.", log_file)
    for i, (prefix, model, prompt, temperature, domain) in enumerate(phase1_configs):
        config_id = f"{prefix}|{model}|{prompt}|{temperature}|{domain}"
        if config_id in state.get("completed", []):
            continue

        print_progress(i, len(phase1_configs))
        print()
        runs = int(config["phase1_runs"])
        log(f"PHASE A RUNNING: {domain} | Model: {model} | Prompt: {prompt} | Temp: {temperature} | Runs: {runs}", log_file)
        cmd = _standard_cmd(config, str(model), str(prompt), float(temperature), str(domain), runs)
        try:
            _run_command(config_id, cmd, state, state_file, log_file, dry_run)
            _cooldown(int(config["cooldown_seconds"]), log_file, dry_run)
        except Exception as exc:
            log(f"CRITICAL ERROR running {config_id}: {exc}", log_file)

    print_progress(len(phase1_configs), len(phase1_configs))
    print()
    log("Phase A Complete; starting Phase B (dual-agent)", log_file)

    phase2_configs = []
    for pair in _as_list(config, "dual_agent_pairs"):
        if not isinstance(pair, list | tuple) or len(pair) != 2:
            raise TypeError("Each dual_agent_pairs item must be [reasoner_model, matcher_model]")
        reasoner_model, matcher_model = pair
        for prompt in _as_list(config, "eval_prompt_versions"):
            for temperature in _as_list(config, "temperatures"):
                for domain in phase2_domains:
                    phase2_configs.append(("da", reasoner_model, matcher_model, prompt, temperature, domain))

    log(f"Starting SEQUENTIAL Phase B (dual-agent): {len(phase2_configs)} configurations planned.", log_file)
    for i, (prefix, reasoner_model, matcher_model, prompt, temperature, domain) in enumerate(phase2_configs):
        config_id = f"{prefix}|{reasoner_model}|{matcher_model}|{prompt}|{temperature}|{domain}"
        if config_id in state.get("completed", []):
            continue

        print_progress(i, len(phase2_configs))
        print()
        runs = int(config["phase2_runs"])
        log(
            f"PHASE B RUNNING: {domain} | Reasoner: {reasoner_model} | Matcher: {matcher_model} "
            f"| Prompt: {prompt} | Temp: {temperature} | Runs: {runs}",
            log_file,
        )
        cmd = _dual_agent_cmd(config, str(reasoner_model), str(matcher_model), str(prompt), float(temperature), str(domain), runs)
        try:
            _run_command(config_id, cmd, state, state_file, log_file, dry_run)
            _cooldown(int(config["cooldown_seconds"]), log_file, dry_run)
        except Exception as exc:
            log(f"CRITICAL ERROR running {config_id}: {exc}", log_file)

    print_progress(len(phase2_configs), len(phase2_configs))
    print()
    log("Sequential Batch Evaluation Complete!", log_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run configured evaluation batches.")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Batch config JSON path (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--mode",
        choices=["standard", "dual-agent", "sequential"],
        default=None,
        help="Override the mode from the config file.",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Override the resume-state JSON path.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Override the batch progress log path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands without running evaluations or updating state.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
        if args.mode:
            config["mode"] = args.mode
        if args.state_file:
            config["state_file"] = args.state_file
        if args.log_file:
            config["log_file"] = args.log_file
        validate_config(config)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    mode = str(config["mode"])
    state_file = _state_file(config, mode)
    log_file = _log_file(config, mode)
    state = load_state(state_file)

    log(f"Using batch config: {args.config}", log_file)
    log(f"Mode: {mode}", log_file)
    log(f"State file: {state_file}", log_file)

    if mode == "standard":
        run_standard_batch(config, state, state_file, log_file, args.dry_run)
    elif mode == "dual-agent":
        run_dual_agent_batch(config, state, state_file, log_file, args.dry_run)
    elif mode == "sequential":
        run_sequential_batch(config, state, state_file, log_file, args.dry_run)
    else:
        raise ValueError(f"Unknown mode '{mode}'. Use standard, dual-agent, or sequential.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
