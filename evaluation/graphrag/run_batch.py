"""Run the paper's graph-only batch; dry-run validates all sampled contexts."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import replace
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import random
import shutil
import tempfile

from belief_store.llm_client import OllamaClient
from evaluation.eval_common import DomainConfig
from evaluation.graphrag.condition import (
    CONDITION, RETRIEVER_VERSION, build_graph_prompt, fact_snapshots, retrieve_slices,
    run_with_graph_retrieval, snapshot_config,
)
from evaluation.graphrag.run_evals import DOMAINS
from evaluation.prompting import build_baseline_system_prompt
from evaluation.run_evals import DOMAIN_REGISTRY


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configs/thesis_graphrag_batch.json"


def load_config(path: Path) -> dict:
    return validate_config(json.loads(path.read_text()))


def validate_config(config: dict) -> dict:
    for key in ("models", "domains"):
        values = config.get(key)
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v for v in values):
            raise ValueError(f"{key} must be a nonempty list of strings")
        if len(set(values)) != len(values):
            raise ValueError(f"{key} contains duplicates")
    if set(config["domains"]) - set(DOMAINS):
        raise ValueError("Only belief_maintenance, absurd, absurd_temporal and grounding are supported")
    for key in ("runs_per_config", "workers"):
        if type(config.get(key)) is not int or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if config.get("think") is not False:
        raise ValueError("This baseline requires think=false, including for qwen3:4b")
    if any("qwen3-nothink" in model for model in config["models"]):
        raise ValueError("Use qwen3:4b with think=false instead of the removed modified Qwen model")
    if config.get("question_policy") not in ("canonical", "sampled_paraphrases"):
        raise ValueError("Unknown question_policy")
    if type(config.get("scenario_seed")) is not int:
        raise ValueError("scenario_seed must be an integer")
    if type(config.get("temperature")) not in (int, float) or not 0 <= config["temperature"] <= 2:
        raise ValueError("temperature must be between 0 and 2")
    options = config.get("ollama", {})
    allowed = {"num_predict", "num_ctx", "repeat_penalty", "repeat_last_n", "top_k", "top_p", "keep_alive"}
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError("Unsupported Ollama options")
    for key in ("num_predict", "num_ctx"):
        if type(options.get(key)) is not int or options[key] < 1:
            raise ValueError(f"ollama.{key} must be a positive integer")
    if not isinstance(config.get("csv_out"), str) or not config["csv_out"]:
        raise ValueError("csv_out must be a nonempty path")
    build_baseline_system_prompt(config["baseline_prompt_version"])
    return config


def prepare_runs(config: dict) -> list[tuple[int, DomainConfig]]:
    """Sample once per domain/run, then share those questions across models.

    Use the existing paraphrase selector and restore the caller's RNG state.
    The saved manifest records exact questions; this seed is not an LLM seed.
    """
    previous_state = random.getstate()
    random.seed(config["scenario_seed"])
    prepared = []
    try:
        for domain in config["domains"]:
            original = DOMAIN_REGISTRY[domain]
            for run in range(1, config["runs_per_config"] + 1):
                turns = original.turns
                if config["question_policy"] == "sampled_paraphrases" and original.seed_fn:
                    turns = original.seed_fn()
                current = snapshot_config(original, turns)
                retrieve_slices(current)
                prepared.append((run, current))
    finally:
        random.setstate(previous_state)
    return prepared


def restore_runs(manifest: dict) -> list[tuple[int, DomainConfig]]:
    """Restore saved questions and inputs, never sample again during resume."""
    config = validate_config(manifest["config"])
    prepared = []
    seen = set()
    for saved in manifest["runs"]:
        key = (saved["domain"], saved["run"])
        if key in seen:
            raise ValueError(f"Duplicate run in manifest: {key}")
        seen.add(key)
        current = replace(
            DOMAIN_REGISTRY[saved["domain"]], turns=saved["turns"],
            initial_beliefs=saved["initial_beliefs"], is_conversational=False,
            accumulate_prior_beliefs=saved["accumulate_prior_beliefs"], seed_fn=None,
        )
        retrieve_slices(current)
        prepared.append((saved["run"], current))
    expected = {(domain, run) for domain in config["domains"]
                for run in range(1, config["runs_per_config"] + 1)}
    if seen != expected or any(not current.turns for _, current in prepared):
        raise ValueError("Manifest does not contain the configured run matrix")
    return prepared


def csv_values(row):
    return {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
            for key, value in row.items()}


def read_checkpoint(path: Path, config: dict, prepared):
    """Validate saved rows and identify complete runs; tolerate a torn final row.

    Incomplete runs are excluded from the recovered CSV and rerun as a unit.
    This function is read-only, including when the original runner is active.
    """
    expected = {}
    system_prompt = build_baseline_system_prompt(config["baseline_prompt_version"])
    for run, current in prepared:
        for index, (turn, facts, graph_slice) in enumerate(zip(
            current.turns, fact_snapshots(current), retrieve_slices(current)
        ), start=1):
            expected[(current.name, run, index)] = {
                "question": turn["question"], "options": turn["options"],
                "correct": turn["correct"], "current_inputs": facts,
                "supplied_attributes": turn["attributes"],
                "prompt": build_graph_prompt(graph_slice, turn), "system_prompt": system_prompt,
            }
    rows = []
    fields = None
    torn_tail = False
    if path.exists() and path.stat().st_size:
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source, strict=True)
            fields = reader.fieldnames
            required = {"model", "domain", "run", "turn", "response", "hit", "condition", "retriever_version"}
            if not fields or not required.issubset(fields):
                raise ValueError("Unrecognized graph results CSV header")
            while True:
                try:
                    row = next(reader)
                except StopIteration:
                    break
                except csv.Error:
                    # A killed writer can leave the last quoted prompt unfinished.
                    if source.read():
                        raise ValueError("Malformed CSV before end of file; results left untouched")
                    torn_tail = True
                    break
                if None in row or any(value is None for value in row.values()):
                    if source.read():
                        raise ValueError("Incomplete CSV row before end of file; results left untouched")
                    torn_tail = True
                    break
                rows.append(row)
    groups = {}
    for row in rows:
        key = (row["model"], row["domain"], int(row["run"]))
        index = int(row["turn"])
        target = expected.get((key[1], key[2], index))
        if key[0] not in config["models"] or target is None:
            raise ValueError(f"Saved result is outside the manifest: {key}, turn {index}")
        metadata = {
            **target, "condition": CONDITION, "retriever_version": RETRIEVER_VERSION,
            "temperature": config["temperature"], "think": False,
            "baseline_prompt_version": config["baseline_prompt_version"],
            "ollama_options": config["ollama"], "history_mode": "snapshot",
            "response_cache": False, "question_policy": config["question_policy"],
            "scenario_seed": config["scenario_seed"],
        }
        for field, value in csv_values(metadata).items():
            if row.get(field) != str(value):
                raise ValueError(f"Saved {field} differs from this evaluation for {key}; refusing to mix results")
        turns = groups.setdefault(key, set())
        if index in turns:
            raise ValueError(f"Duplicate saved turn for {key}: {index}")
        turns.add(index)
    lengths = {(current.name, run): len(current.turns) for run, current in prepared}
    complete = {key for key, turns in groups.items()
                if turns == set(range(1, lengths[(key[1], key[2])] + 1))}
    retained = [row for row in rows if (row["model"], row["domain"], int(row["run"])) in complete]
    return fields, retained, complete, torn_tail or len(retained) != len(rows)


def recover_checkpoint(path: Path, fields, rows) -> None:
    """Back up interrupted output, then atomically retain only complete runs."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.before-resume-{stamp}.bak")
    shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8",
                                     dir=path.parent, delete=False) as temporary:
        writer = csv.DictWriter(temporary, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        temporary.flush()
        os.fsync(temporary.fileno())
    os.replace(temporary.name, path)
    print(f"Preserved interrupted output in {backup}; incomplete runs will repeat")


def evaluate_run(model, run, current, config):
    llm = OllamaClient(model=model, temperature=config["temperature"], think=False,
                       cache_enabled=False, **config["ollama"])
    records = run_with_graph_retrieval(
        llm, current, baseline_prompt_version=config["baseline_prompt_version"],
        debug_logs_enabled=False,
    )
    rows = []
    for turn, facts, record in zip(current.turns, fact_snapshots(current), records):
        rows.append({
            "domain": current.name, "run": run, "condition": CONDITION,
            "model": model, "temperature": config["temperature"], "think": False,
            "baseline_prompt_version": config["baseline_prompt_version"],
            "ollama_options": config["ollama"], "history_mode": "snapshot",
            "response_cache": False, "question_policy": config["question_policy"],
            "scenario_seed": config["scenario_seed"],
            "question": turn["question"], "options": turn["options"],
            "supplied_attributes": turn["attributes"], "current_inputs": facts,
            **record,
        })
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--csv-out", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Reuse the saved manifest and skip complete runs. Stop the old process first.")
    args = parser.parse_args(argv)
    config = load_config(args.config or DEFAULT_CONFIG)
    output_path = args.csv_out or Path(config["csv_out"])
    manifest_path = output_path.with_suffix(".manifest.json")
    if args.resume:
        manifest = json.loads(manifest_path.read_text())
        saved_config = validate_config(manifest["config"])
        if args.config:
            ignored = {"workers", "csv_out"}
            if {k: v for k, v in config.items() if k not in ignored} != {
                k: v for k, v in saved_config.items() if k not in ignored
            }:
                raise ValueError("Requested config differs from the saved batch; cannot resume with changed settings")
            saved_config = {**saved_config, "workers": config["workers"]}
        config = saved_config
        prepared = restore_runs(manifest)
    else:
        prepared = prepare_runs(config)
    count = len(config["models"]) * sum(len(current.turns) for _, current in prepared)
    print(f"Graph baseline only: {len(config['models'])} models × {len(config['domains'])} scenario sets "
          f"× {config['runs_per_config']} runs = {count} model calls")
    print(f"Models: {', '.join(config['models'])}; think=false; temperature={config['temperature']}")
    print(f"Scenarios: {', '.join(config['domains'])}")
    if args.dry_run:
        if args.resume:
            _, _, completed, _ = read_checkpoint(output_path, config, prepared)
            remaining = sum(len(current.turns) for model in config["models"]
                            for run, current in prepared if (model, current.name, run) not in completed)
            print(f"Resume: {len(completed)} complete runs saved; {remaining} model calls remaining")
        print("All sampled graph contexts validated. No model calls made.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # A separate lock survives atomic CSV recovery. Old pre-resume versions do
    # not hold this lock: their process must exit before --resume is used.
    with output_path.with_suffix(output_path.suffix + ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another batch is writing this results file; do not start a second runner") from None
        run_jobs(output_path, manifest_path, config, prepared, resume=args.resume)


def run_jobs(output_path, manifest_path, config, prepared, *, resume):
    fields = None
    completed = set()
    if resume:
        fields, retained, completed, needs_recovery = read_checkpoint(output_path, config, prepared)
        if needs_recovery:
            recover_checkpoint(output_path, fields, retained)
        print(f"Resuming: skipping {len(completed)} complete runs", flush=True)
    elif output_path.exists() or manifest_path.exists():
        raise FileExistsError("Choose a fresh --csv-out path; results and manifests are never overwritten")
    else:
        with manifest_path.open("x", encoding="utf-8") as manifest:
            json.dump({"config": config, "runs": [
                {"domain": current.name, "run": run, "turns": current.turns,
                 "initial_beliefs": current.initial_beliefs,
                 "accumulate_prior_beliefs": current.accumulate_prior_beliefs}
                for run, current in prepared
            ]}, manifest, indent=2)
    with output_path.open("a" if resume else "x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields) if fields else None
        # Finish one model before loading another to limit GPU model switching.
        for model in config["models"]:
            with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
                futures = {pool.submit(evaluate_run, model, run, current, config): (run, current.name)
                           for run, current in prepared if (model, current.name, run) not in completed}
                try:
                    for future in as_completed(futures):
                        rows = future.result()
                        if writer is None:
                            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
                            writer.writeheader()
                        for row in rows:
                            writer.writerow(csv_values(row))
                        output.flush()
                        os.fsync(output.fileno())
                        run, domain = futures[future]
                        print(f"{model} {domain} run {run}: {sum(row['hit'] for row in rows)}/{len(rows)}", flush=True)
                except BaseException:
                    for pending in futures:
                        pending.cancel()
                    raise
    print(f"Saved graph baseline results to {output_path}")


if __name__ == "__main__":
    main()
