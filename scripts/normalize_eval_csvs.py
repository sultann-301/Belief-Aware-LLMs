#!/usr/bin/env python3
"""Normalize eval CSVs into corrected long-format outputs.

Writes new CSVs and keeps originals untouched.
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import Iterable

STANDARD_DEFAULT_IN = "eval_results.csv"
STANDARD_DEFAULT_OUT = "eval_results_normalized.csv"
DUAL_DEFAULT_IN = "eval_results_dual_agent.csv"
DUAL_DEFAULT_OUT = "eval_results_dual_agent_normalized.csv"

STANDARD_HEADER = [
    "Timestamp",
    "Domain",
    "Model",
    "Temp",
    "Eval_Prompt_Ver",
    "Baseline_Prompt_Ver",
    "Runs",
    "Condition",
    "Summary_Metric",
    "Value",
    "Class_Label",
]

DUAL_HEADER = [
    "Timestamp",
    "Domain",
    "Model",
    "Reasoner_Model",
    "Matcher_Model",
    "Temp",
    "Eval_Prompt_Ver",
    "Baseline_Prompt_Ver",
    "Runs",
    "Condition",
    "Metric_Family",
    "Summary_Metric",
    "Value",
    "Class_Label",
]


def _read_rows(path: str) -> Iterable[dict[str, str]]:
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def _write_rows(path: str, header: list[str], rows: Iterable[dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _baseline_from_eval_prompt(eval_prompt_ver: str) -> str:
    if eval_prompt_ver == "v15":
        return "v2"
    if eval_prompt_ver == "v16":
        return "v2"
    return ""


def normalize_standard(in_path: str, out_path: str) -> int:
    def _rows() -> Iterable[dict[str, str]]:
        for row in _read_rows(in_path):
            eval_prompt_ver = (row.get("Prompt_Ver") or "").strip()
            baseline_prompt_ver = _baseline_from_eval_prompt(eval_prompt_ver)

            base = {
                "Timestamp": row.get("Timestamp", ""),
                "Domain": row.get("Domain", ""),
                "Model": row.get("Model", ""),
                "Temp": row.get("Temp", ""),
                "Eval_Prompt_Ver": eval_prompt_ver,
                "Baseline_Prompt_Ver": baseline_prompt_ver,
                "Runs": row.get("Runs", ""),
                "Summary_Metric": row.get("Summary_Metric", ""),
                "Class_Label": row.get("Class_Label", ""),
            }

            with_store_val = (row.get("With_Store") or "").strip()
            if with_store_val != "":
                out_row = dict(base)
                out_row.update({
                    "Condition": "With_Store",
                    "Value": with_store_val,
                })
                yield out_row

            no_store_val = (row.get("No_Store") or "").strip()
            if no_store_val != "":
                out_row = dict(base)
                out_row.update({
                    "Condition": "No_Store",
                    "Value": no_store_val,
                })
                yield out_row

    rows = list(_rows())
    _write_rows(out_path, STANDARD_HEADER, rows)
    return len(rows)


def normalize_dual(in_path: str, out_path: str) -> int:
    def _rows() -> Iterable[dict[str, str]]:
        for row in _read_rows(in_path):
            eval_prompt_ver = (row.get("Prompt_Ver") or "").strip()
            baseline_prompt_ver = _baseline_from_eval_prompt(eval_prompt_ver)

            value = (row.get("Dual_Agent_Store") or "").strip()
            if value == "":
                continue

            yield {
                "Timestamp": row.get("Timestamp", ""),
                "Domain": row.get("Domain", ""),
                "Model": row.get("Model", ""),
                "Reasoner_Model": row.get("Reasoner_Model", ""),
                "Matcher_Model": row.get("Matcher_Model", ""),
                "Temp": row.get("Temp", ""),
                "Eval_Prompt_Ver": eval_prompt_ver,
                "Baseline_Prompt_Ver": baseline_prompt_ver,
                "Runs": row.get("Runs", ""),
                "Condition": "Dual_Agent_Store",
                "Metric_Family": row.get("Metric_Family", ""),
                "Summary_Metric": row.get("Summary_Metric", ""),
                "Value": value,
                "Class_Label": row.get("Class_Label", ""),
            }

    rows = list(_rows())
    _write_rows(out_path, DUAL_HEADER, rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize eval CSVs into corrected long-format outputs."
    )
    parser.add_argument(
        "--standard-in",
        default=STANDARD_DEFAULT_IN,
        help=f"Input standard CSV (default: {STANDARD_DEFAULT_IN})",
    )
    parser.add_argument(
        "--standard-out",
        default=STANDARD_DEFAULT_OUT,
        help=f"Output standard CSV (default: {STANDARD_DEFAULT_OUT})",
    )
    parser.add_argument(
        "--dual-in",
        default=DUAL_DEFAULT_IN,
        help=f"Input dual-agent CSV (default: {DUAL_DEFAULT_IN})",
    )
    parser.add_argument(
        "--dual-out",
        default=DUAL_DEFAULT_OUT,
        help=f"Output dual-agent CSV (default: {DUAL_DEFAULT_OUT})",
    )
    parser.add_argument(
        "--skip-standard",
        action="store_true",
        help="Skip standard CSV normalization",
    )
    parser.add_argument(
        "--skip-dual",
        action="store_true",
        help="Skip dual-agent CSV normalization",
    )

    args = parser.parse_args()

    if not args.skip_standard:
        if not os.path.exists(args.standard_in):
            raise FileNotFoundError(f"Missing standard CSV: {args.standard_in}")
        count = normalize_standard(args.standard_in, args.standard_out)
        print(f"Wrote {count} rows to {args.standard_out}")

    if not args.skip_dual:
        if not os.path.exists(args.dual_in):
            raise FileNotFoundError(f"Missing dual-agent CSV: {args.dual_in}")
        count = normalize_dual(args.dual_in, args.dual_out)
        print(f"Wrote {count} rows to {args.dual_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
