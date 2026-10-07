"""Run only the graph-retrieval baseline, with supplied targets.

Example: python3 -m evaluation.graphrag.run_evals --domain loan_absurd --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from belief_store.llm_client import OllamaClient
from evaluation.graphrag.condition import (
    CONDITION, build_graph_prompt, fact_snapshots, retrieve_slices,
    run_with_graph_retrieval, snapshot_config,
)
from evaluation.run_evals import DOMAIN_REGISTRY


SCENARIOS = ("belief_maintenance", "absurd", "absurd_temporal", "grounding")
DOMAINS = tuple(f"{domain}_{scenario}" for domain in
                ("loan", "alien_clinic", "crime_scene", "thorncrester")
                for scenario in SCENARIOS)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=DOMAINS, default="loan_belief_maintenance")
    parser.add_argument("--model", default="gemma3:1b")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--num-predict", type=int, default=768)
    parser.add_argument("--num-ctx", type=int, default=8162)
    parser.add_argument("--baseline-prompt-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--csv-out", type=Path, default=Path("eval_results_graphrag.csv"))
    parser.add_argument("--dry-run", action="store_true", help="Print retrieved prompts without calling Ollama.")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    config = snapshot_config(DOMAIN_REGISTRY[args.domain])
    slices = retrieve_slices(config)
    if args.dry_run:
        for index, (turn, graph_slice) in enumerate(zip(config.turns, slices), start=1):
            print(f"\nTurn {index}: {', '.join(graph_slice.targets)}")
            print(build_graph_prompt(graph_slice, turn))
        return

    # Keep this separate from historical CSVs and avoid accidental overwrites.
    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_out.open("x", newline="", encoding="utf-8") as output:
        llm = OllamaClient(model=args.model, temperature=args.temperature, think=False,
                           num_predict=args.num_predict, num_ctx=args.num_ctx, cache_enabled=False)
        writer = None
        snapshots = fact_snapshots(config)
        for run in range(1, args.runs + 1):
            print(f"Run {run}/{args.runs}: {args.domain}; supplied targets; no chat history")
            records = run_with_graph_retrieval(
                llm, config, baseline_prompt_version=args.baseline_prompt_version,
                debug_logs_enabled=False,
            )
            rows = []
            for turn, facts, record in zip(config.turns, snapshots, records):
                rows.append({
                    "domain": args.domain, "run": run, "condition": CONDITION,
                    "model": args.model, "temperature": args.temperature,
                    "think": False, "num_predict": args.num_predict, "num_ctx": args.num_ctx,
                    "question_policy": "canonical",
                    "baseline_prompt_version": args.baseline_prompt_version,
                    "history_mode": "snapshot", "response_cache": False,
                    "question": turn["question"], "options": turn["options"],
                    "supplied_attributes": turn["attributes"], "current_inputs": facts,
                    **record,
                })
            hits = sum(record["hit"] for record in records)
            print(f"  {CONDITION}: {hits}/{len(records)}")
            if writer is None:
                fields = list(dict.fromkeys(key for row in rows for key in row))
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
            for row in rows:
                writer.writerow({
                    key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                    for key, value in row.items()
                })
            output.flush()
    print(f"Saved graph baseline results to {args.csv_out}")


if __name__ == "__main__":
    main()
