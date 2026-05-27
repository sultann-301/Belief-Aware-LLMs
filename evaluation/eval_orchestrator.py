"""eval_orchestrator.py — Multi-run orchestrators and CSV export.

Provides:
  - run_single_eval: single-run comparison
  - run_multi_eval: multi-run parallel standard eval + CSV export
  - run_multi_eval_dual_agent: multi-run parallel dual-agent eval + CSV export
"""

from __future__ import annotations

import concurrent.futures
import csv
import os
import random
import statistics
import time
from collections import Counter

from belief_store.llm_client import OllamaClient
from evaluation.prompting import get_eval_prompt_version
from evaluation.eval_common import DomainConfig, _ensure_csv_header, _build_cache_path
from evaluation.eval_metrics import (
    brier_score,
    expected_calibration_error,
    log_loss_score,
    macro_calibration_error,
    _compute_reasoner_metrics,
)
from evaluation.eval_conditions import (
    run_with_store,
    run_without_store,
    _run_standard_eval_task,
    _run_dual_agent_eval_task,
)

def run_single_eval(
    config: DomainConfig,
    model: str = "gemma3:1b",
    temperature: float = 0.0,
    baseline_prompt_version: str | None = None,
) -> None:
    """Run single evaluation: Store vs No Store, print results table."""
    print(f"Connecting to Ollama ({model}) with temperature {temperature}...\n")
    llm = OllamaClient(model=model, temperature=temperature)
    n_turns = len(config.turns)

    print("=" * 75)
    print("[1] WITH Store (Stateless, no chat history)")
    print("=" * 75)
    with_store = run_with_store(llm, config)
    score_with = sum(r["hit"] for r in with_store)

    print()
    print("=" * 75)
    print("[2] NO Store (Baseline: rules + chat history only)")
    print("=" * 75)
    no_store = run_without_store(llm, config, baseline_prompt_version=baseline_prompt_version)
    score_no_store = sum(r["hit"] for r in no_store)

    # Results table
    print()
    print("=" * 75)
    print("RESULTS SUMMARY")
    print("=" * 75)
    print()
    print(f"  {'Turn':<6} {'[1] Store':<18} {'[2] NO Store':<18}")
    print(f"  {'─'*6} {'─'*18} {'─'*18}")
    for r1, r2 in zip(with_store, no_store):
        t = r1["turn"]
        s1 = "✓" if r1["hit"] else f"✗ ({r1['answer']})"
        s2 = "✓" if r2["hit"] else f"✗ ({r2['answer']})"
        print(f"  {t:<6} {s1:<18} {s2:<18}")

    print()
    print(f"  [1] WITH STORE:  {score_with}/{n_turns}  ({score_with * 100 // n_turns}%)")
    print(f"  [2] NO STORE:    {score_no_store}/{n_turns}  ({score_no_store * 100 // n_turns}%)")
    print()


def run_multi_eval(
    config: DomainConfig,
    runs: int = 10,
    workers: int = 4,
    model: str = "gemma3:1b",
    temperature: float = 0.7,
    model_alias: str | None = None,
    ollama_options: dict[str, object] | None = None,
    cache_dir: str | None = None,
    cache_enabled: bool = False,
    cache_namespace: str = "eval",
    shuffle_options: bool = False,
    baseline_prompt_version: str | None = None,
    only_with_store: bool = False,
    csv_out: str | None = None,
) -> None:
    """Run evaluation N times in parallel, print summary statistics and export results."""
    print(f"Connecting to Ollama ({model})...\n")
    n_turns = len(config.turns)

    cache_path = _build_cache_path(cache_dir, cache_namespace)

    total_tasks = runs * (1 if only_with_store else 2)
    print(f"Launching {runs} runs ({total_tasks} total tasks) in pool of {workers} workers\n", flush=True)
    start = time.time()

    scores: list[list[int]] = [[], []]
    hits_per_turn: list[list[int]] = [[0] * n_turns for _ in range(2)]
    
    # Reasoning evidence metrics (WITH STORE only — index 0)
    reasoning_scores: dict[str, list[float]] = {
        "evidence_precision": [],
        "evidence_recall": [],
        "evidence_f1": [],
        "evidence_cited_count": [],
        "evidence_canonical_count": [],
    }
    
    # ── New metric trackers ───────────────────────────────────────────────
    answers_per_turn: list[list[list]] = [[[] for _ in range(n_turns)] for _ in range(2)]
    efr_counts: list[list[int]] = [[], []]
    emds: list[Counter] = [Counter(), Counter()]
    tpca_correct: list[list[int]] = [[], []]
    tpca_wrong: list[list[int]] = [[], []]
    retrieval_scores: dict[str, list[float]] = {"bcr": [], "sbir": []}
    calibration_preds: list[list[tuple[float, int]]] = [[] for _ in range(2)]


    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_task: dict[concurrent.futures.Future, tuple[int, int]] = {}
        for i in range(runs):
            run_idx = i + 1
            
            # Prepare turns (potentially seeded/shuffled) for this run
            run_turns = config.seed_fn() if config.seed_fn else config.turns
            if shuffle_options:
                shuffled_turns = []
                for turn in run_turns:
                    t_copy = turn.copy()
                    if "options" in t_copy:
                        labels = list(t_copy["options"].keys())
                        phrases = list(t_copy["options"].values())
                        correct_phrase = t_copy["options"].get(t_copy["correct"])
                        random.shuffle(phrases)
                        new_options = dict(zip(labels, phrases))
                        new_correct = next(l for l, p in new_options.items() if p == correct_phrase)
                        t_copy["options"] = new_options
                        t_copy["correct"] = new_correct
                    shuffled_turns.append(t_copy)
                run_turns = shuffled_turns

            # [1] WITH STORE
            future_to_task[
                pool.submit(
                    _run_standard_eval_task,
                    0, config, model, temperature, ollama_options, cache_path, cache_enabled,
                    baseline_prompt_version, run_turns
                )
            ] = (run_idx, 0)
            
            # [2] NO STORE
            if not only_with_store:
                future_to_task[
                    pool.submit(
                        _run_standard_eval_task,
                        1, config, model, temperature, ollama_options, cache_path, cache_enabled,
                        baseline_prompt_version, run_turns
                    )
                ] = (run_idx, 1)

        num_conds = 1 if only_with_store else 2
        run_results: dict[int, list[int | None]] = {i + 1: [None] * num_conds for i in range(runs)}

        for future in concurrent.futures.as_completed(future_to_task):
            run_idx, condition_idx = future_to_task[future]
            res = future.result()
            hits = sum(r["hit"] for r in res)

            for r in res:
                t_idx = r["turn"] - 1
                if r["hit"]:
                    hits_per_turn[condition_idx][t_idx] += 1
                
                answers_per_turn[condition_idx][t_idx].append(r.get("answer"))
                
                resp_len = len((r.get("response") or "").split())
                (tpca_correct if r["hit"] else tpca_wrong)[condition_idx].append(resp_len)
                
                method = r.get("extraction_method")
                if method:
                    emds[condition_idx][method] += 1
                
                p_val = r.get("decision_prob") or r.get("mean_answer_prob")
                if p_val is not None:
                    calibration_preds[condition_idx].append((p_val, 1 if r["hit"] else 0))

            efr_counts[condition_idx].append(sum(1 for r in res if r.get("answer") is None))
            run_results[run_idx][condition_idx] = hits
            scores[condition_idx].append(hits)

            if condition_idx == 0:
                scored = [r for r in res if "evidence_f1" in r]
                if scored:
                    for metric_key in reasoning_scores:
                        avg_val = sum(r[metric_key] for r in scored) / len(scored)
                        reasoning_scores[metric_key].append(avg_val)
                bcr_vals = [r["bcr"] for r in res if "bcr" in r]
                sbir_vals = [r["sbir"] for r in res if "sbir" in r]
                if bcr_vals:
                    retrieval_scores["bcr"].append(sum(bcr_vals) / len(bcr_vals))
                if sbir_vals:
                    retrieval_scores["sbir"].append(sum(sbir_vals) / len(sbir_vals))

            if only_with_store:
                if run_results[run_idx][0] is not None:
                    s1 = run_results[run_idx][0]
                    print(f"✓ Run {run_idx:>2}: [1] {s1}/{n_turns}", flush=True)
            else:
                if all(v is not None for v in run_results[run_idx]):
                    s1, s2 = run_results[run_idx]
                    print(f"✓ Run {run_idx:>2}: [1] {s1}/{n_turns} | [2] {s2}/{n_turns}", flush=True)

    elapsed = time.time() - start
    n = len(scores[0])
    wct_per_turn = elapsed / (runs * n_turns) if runs * n_turns > 0 else 0.0

    def _compute_afr_ds(ans_matrix: list[list]) -> tuple[float, float]:
        afr_vals, consistent = [], 0
        for turn_answers in ans_matrix:
            ta = [a for a in turn_answers if a is not None]
            if not ta:
                continue
            mode_count = Counter(ta).most_common(1)[0][1]
            afr_vals.append((len(ta) - mode_count) / len(ta))
            if len(set(ta)) == 1:
                consistent += 1
        mean_afr = sum(afr_vals) / len(afr_vals) if afr_vals else 0.0
        ds = consistent / len(ans_matrix) if ans_matrix else 0.0
        return mean_afr, ds

    afr_ds = [_compute_afr_ds(answers_per_turn[c]) for c in range(2)]

    def _ptc_variance(hits_vec: list[int], n_runs: int) -> float:
        if n_runs < 2 or not hits_vec:
            return 0.0
        rates = [h / n_runs for h in hits_vec]
        return statistics.variance(rates) if len(rates) > 1 else 0.0

    ptc_var = [_ptc_variance(hits_per_turn[c], n) for c in range(2)]

    print("\n" + "=" * 80)
    print(f"SUMMARY OVER {n} RUNS")
    print("=" * 80)

    # [BUGFIX: only print NO STORE summary if only_with_store is False]
    condition_labels = ["[1] WITH STORE            "]
    if not only_with_store:
        condition_labels.append("[2] NO STORE              ")

    for idx, (label, sc) in enumerate(zip(condition_labels, scores[:len(condition_labels)])):
        avg = sum(sc) / n if n > 0 else 0.0
        # [BUGFIX: safely guard statistics calls with len(sc) > 1 instead of n > 1]
        var = statistics.variance(sc) if len(sc) > 1 else 0.0
        std = statistics.stdev(sc) if len(sc) > 1 else 0.0
        sc_str = ", ".join(str(x) for x in sc)
        print(f"  {label} | Avg: {avg:.2f}/{n_turns} | Var: {var:.2f} | StdDev: {std:.2f} | Scores: [{sc_str}]")

        efr_list = efr_counts[idx]
        efr_avg = (sum(efr_list) / len(efr_list) / n_turns) if efr_list and n_turns else 0.0
        print(f"    EFR (Extraction Failure Rate)   | {efr_avg:.4f}")
        mean_afr, ds_score = afr_ds[idx]
        ds_note = " ← only meaningful at temp=0" if temperature != 0.0 else ""
        print(f"    AFR (Answer Flip Rate)          | {mean_afr:.4f}")
        print(f"    DS  (Determinism Score)         | {ds_score:.4f}{ds_note}")
        print(f"    PTC Variance (per-turn consist) | {ptc_var[idx]:.6f}")
        c_avg = sum(tpca_correct[idx]) / len(tpca_correct[idx]) if tpca_correct[idx] else 0.0
        w_avg = sum(tpca_wrong[idx]) / len(tpca_wrong[idx]) if tpca_wrong[idx] else 0.0
        print(f"    TPCA Correct / Wrong (words)    | {c_avg:.1f} / {w_avg:.1f}")
        total_extracted = sum(emds[idx].values())
        if total_extracted:
            emd_str = "  ".join(
                f"{m}={cnt/total_extracted*100:.1f}%" for m, cnt in emds[idx].most_common(5)
            )
            print(f"    EMD (Extraction Method Dist)    | {emd_str}")
        
        preds = calibration_preds[idx]
        if preds:
            bs = brier_score(preds)
            ll = log_loss_score(preds)
            ece = expected_calibration_error(preds)
            print(f"    Brier Score (Calibration)       | {bs:.4f} (lower is better)")
            print(f"    Log Loss (Uncertainty)          | {ll:.4f}")
            print(f"    ECE (Exp. Calibration Error)    | {ece:.4f}")
            mce = macro_calibration_error(preds)
            print(f"    MacroCE (Macro Calib. Error)    | {mce:.4f}")

    if reasoning_scores["evidence_f1"]:
        print("\n  REASONING EVIDENCE METRICS (WITH STORE only):")
        for metric_key, metric_label in (
            ("evidence_precision", "Precision"),
            ("evidence_recall", "Recall"),
            ("evidence_f1", "F1"),
            ("evidence_cited_count", "Cited Keys"),
            ("evidence_canonical_count", "Canonical Keys"),
        ):
            sc = reasoning_scores[metric_key]
            r_n = len(sc)
            r_avg = sum(sc) / r_n if r_n > 0 else 0.0
            r_var = statistics.variance(sc) if r_n > 1 else 0.0
            r_std = statistics.stdev(sc) if r_n > 1 else 0.0
            print(f"    Evidence {metric_label:<10} | Avg: {r_avg:.4f} | Var: {r_var:.6f} | StdDev: {r_std:.4f}")

    if retrieval_scores["bcr"]:
        print("\n  RETRIEVAL FIDELITY (WITH STORE only):")
        for key, label in (("bcr", "BCR  (Belief Coverage Rate)  "), ("sbir", "SBIR (Spurious Injection Rate)")):
            sc = retrieval_scores[key]
            r_avg = sum(sc) / len(sc) if sc else 0.0
            print(f"    {label} | Avg: {r_avg:.4f}")

    print("\n  PER-TURN ACCURACY:")
    if only_with_store:
        print(f"    {'Turn':<4} | {'[1]':<24}")
        print(f"    {'─'*4} | {'─'*24}")
        for t in range(n_turns):
            acc1 = hits_per_turn[0][t]
            s1 = f"{acc1:>2}/{n} ({acc1 * 100 // n:>3}%)"
            print(f"    {t+1:>4} | {s1:<24}")
    else:
        print(f"    {'Turn':<4} | {'[1]':<24} | {'[2]':<24}")
        print(f"    {'─'*4} | {'─'*24} | {'─'*24}")
        for t in range(n_turns):
            acc1, acc2 = hits_per_turn[0][t], hits_per_turn[1][t]
            s1 = f"{acc1:>2}/{n} ({acc1 * 100 // n:>3}%)"
            s2 = f"{acc2:>2}/{n} ({acc2 * 100 // n:>3}%)"
            print(f"    {t+1:>4} | {s1:<24} | {s2:<24}")


    print("=" * 80)
    print(f"Total wall-clock time: {elapsed:.1f}s  |  WCT/turn: {wct_per_turn:.3f}s\n")

    # ── CSV Export ────────────────────────────────────────────────────────
    if only_with_store:
        csv_filename = csv_out or "eval_results_with_store.csv"
    else:
        csv_filename = "eval_results.csv"
    file_exists = os.path.isfile(csv_filename)
    prompt_ver = get_eval_prompt_version(config.eval_prompt_version)
    header = [
        "Timestamp", "Domain", "Model", "Temp", "Prompt_Ver", "Runs",
        "Summary_Metric", "With_Store", "Store_History", "No_Store", "Class_Label",
    ]
    try:
        _ensure_csv_header(csv_filename, header)
        with open(csv_filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(header)

            display_model = model_alias or model
            avg0 = (sum(scores[0]) / n) / n_turns if n_turns > 0 else 0
            avg2 = (sum(scores[1]) / n) / n_turns if (not only_with_store and n_turns > 0) else 0
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            def _row(metric: str, v0: str, v2: str = "") -> None:
                # [BUGFIX: Ensure empty strings for v2 when only_with_store is true]
                if only_with_store:
                    v2 = ""
                writer.writerow([
                    timestamp, config.name, display_model, temperature, prompt_ver, runs,
                    metric, v0, "", v2, "",
                ])

            _row("Average_Accuracy", f"{avg0:.4f}", f"{avg2:.4f}" if not only_with_store else "")

            var0 = statistics.variance(scores[0]) if len(scores[0]) > 1 else 0.0
            var2 = statistics.variance(scores[1]) if len(scores[1]) > 1 else 0.0
            _row("Variance_Raw_Score", f"{var0:.4f}", f"{var2:.4f}" if not only_with_store else "")

            std0 = statistics.stdev(scores[0]) if len(scores[0]) > 1 else 0.0
            std2 = statistics.stdev(scores[1]) if len(scores[1]) > 1 else 0.0
            _row("StdDev_Raw_Score", f"{std0:.4f}", f"{std2:.4f}" if not only_with_store else "")

            efr0 = (sum(efr_counts[0]) / len(efr_counts[0]) / n_turns) if efr_counts[0] and n_turns else 0.0
            efr2 = (sum(efr_counts[1]) / len(efr_counts[1]) / n_turns) if (not only_with_store and efr_counts[1] and n_turns) else 0.0
            _row("EFR_Extraction_Failure_Rate", f"{efr0:.4f}", f"{efr2:.4f}" if not only_with_store else "")

            afr0, ds0 = afr_ds[0]
            afr2, ds2 = afr_ds[1] if not only_with_store else (0.0, 0.0)
            _row("AFR_Answer_Flip_Rate", f"{afr0:.4f}", f"{afr2:.4f}" if not only_with_store else "")
            _row("DS_Determinism_Score", f"{ds0:.4f}", f"{ds2:.4f}" if not only_with_store else "")

            _row("PTC_Variance_PerTurn_Consistency", f"{ptc_var[0]:.6f}", f"{ptc_var[1]:.6f}" if not only_with_store else "")
            _row("WCT_WallClock_PerTurn_Seconds", f"{wct_per_turn:.4f}")

            c0 = sum(tpca_correct[0]) / len(tpca_correct[0]) if tpca_correct[0] else 0.0
            w0 = sum(tpca_wrong[0]) / len(tpca_wrong[0]) if tpca_wrong[0] else 0.0
            c2 = sum(tpca_correct[1]) / len(tpca_correct[1]) if (not only_with_store and tpca_correct[1]) else 0.0
            w2 = sum(tpca_wrong[1]) / len(tpca_wrong[1]) if (not only_with_store and tpca_wrong[1]) else 0.0
            _row("TPCA_Words_Correct", f"{c0:.1f}", f"{c2:.1f}" if not only_with_store else "")
            _row("TPCA_Words_Wrong", f"{w0:.1f}", f"{w2:.1f}" if not only_with_store else "")

            bs0 = brier_score(calibration_preds[0]) if calibration_preds[0] else ""
            bs2 = brier_score(calibration_preds[1]) if (not only_with_store and calibration_preds[1]) else ""
            _row("Summary_Metric_Brier_Score", f"{bs0}", f"{bs2}")

            ll0 = log_loss_score(calibration_preds[0]) if calibration_preds[0] else ""
            ll2 = log_loss_score(calibration_preds[1]) if (not only_with_store and calibration_preds[1]) else ""
            _row("Summary_Metric_Log_Loss", f"{ll0}", f"{ll2}")

            ece0 = expected_calibration_error(calibration_preds[0]) if calibration_preds[0] else ""
            ece2 = expected_calibration_error(calibration_preds[1]) if (not only_with_store and calibration_preds[1]) else ""
            _row("Summary_Metric_ECE", f"{ece0}", f"{ece2}")

            mce0 = macro_calibration_error(calibration_preds[0]) if calibration_preds[0] else ""
            mce2 = macro_calibration_error(calibration_preds[1]) if (not only_with_store and calibration_preds[1]) else ""
            _row("Summary_Metric_MacroCE", f"{mce0}", f"{mce2}")

            # EMD rows
            cond_tuples = ((0, "WithStore"),) if only_with_store else ((0, "WithStore"), (1, "NoStore"))
            for cond_idx, cond_label in cond_tuples:
                total = sum(emds[cond_idx].values())
                if total:
                    for method, cnt in emds[cond_idx].most_common(5):
                        writer.writerow([
                            timestamp, config.name, display_model, temperature, prompt_ver, runs,
                            f"EMD_{cond_label}_{method}",
                            f"{cnt/total:.4f}", "", "", "",
                        ])

            for metric_key, csv_metric in (
                ("evidence_precision", "Average_Evidence_Precision"),
                ("evidence_recall", "Average_Evidence_Recall"),
                ("evidence_f1", "Average_Evidence_F1"),
                ("evidence_cited_count", "Average_Evidence_Cited_Keys"),
                ("evidence_canonical_count", "Average_Evidence_Canonical_Keys"),
            ):
                sc = reasoning_scores[metric_key]
                r_avg = sum(sc) / len(sc) if sc else 0.0
                _row(csv_metric, f"{r_avg:.4f}")

            for key, csv_name in (
                ("bcr", "Average_BCR_BeliefCoverage"),
                ("sbir", "Average_SBIR_SpuriousInjection"),
            ):
                sc = retrieval_scores[key]
                r_avg = sum(sc) / len(sc) if sc else 0.0
                _row(csv_name, f"{r_avg:.4f}")

        print(f"Results exported to {csv_filename}")
    except Exception as e:
        print(f"Failed to write CSV: {e}")


def run_multi_eval_dual_agent(
    config: DomainConfig,
    runs: int = 10,
    workers: int = 4,
    model: str = "gemma3:1b",
    temperature: float = 0.0,
    model_alias: str | None = None,
    reasoner_model: str | None = None,
    matcher_model: str | None = None,
    ollama_options: dict[str, object] | None = None,
    cache_dir: str | None = None,
    cache_enabled: bool = False,
    cache_namespace: str = "eval",
    shuffle_options: bool = False,
) -> None:
    """Run evaluation N times with dual-agent conditions in parallel."""
    reasoner_model = reasoner_model or model
    matcher_model = matcher_model or model
    
    print(f"Connecting to Ollama (Reasoner: {reasoner_model}, Matcher: {matcher_model})...\n")
    n_turns = len(config.turns)

    cache_path = _build_cache_path(cache_dir, cache_namespace)

    print(f"Launching {runs} runs ({runs * 1} total tasks) with DUAL-AGENT in pool of {workers} workers\n", flush=True)
    start = time.time()

    scores: list[list[int]] = [[]]
    metric_scores: list[dict[str, list[float]]] = [{"binding": [], "end_to_end": []}]
    hits_per_turn: list[list[int]] = [[0] * n_turns]
    
    reasoning_scores: dict[str, list[float]] = {
        "evidence_precision": [],
        "evidence_recall": [],
        "evidence_f1": [],
        "evidence_cited_count": [],
        "evidence_canonical_count": [],
    }
    
    answers_per_turn_da: list[list] = [[] for _ in range(n_turns)]
    efr_counts_da: list[int] = []
    emds_da: Counter = Counter()
    tpca_correct_da: list[int] = []
    tpca_wrong_da: list[int] = []
    retrieval_scores_da: dict[str, list[float]] = {"bcr": [], "sbir": []}
    reasoner_binding_metrics: list[tuple[bool, bool]] = []
    matcher_calibration_preds: list[tuple[float, int]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_task: dict[concurrent.futures.Future, tuple[int, int]] = {}
        for i in range(runs):
            run_idx = i + 1
            
            run_turns = config.seed_fn() if config.seed_fn else config.turns
            if shuffle_options:
                shuffled_turns = []
                for turn in run_turns:
                    t_copy = turn.copy()
                    if "options" in t_copy:
                        labels = list(t_copy["options"].keys())
                        phrases = list(t_copy["options"].values())
                        correct_phrase = t_copy["options"].get(t_copy["correct"])
                        random.shuffle(phrases)
                        new_options = dict(zip(labels, phrases))
                        new_correct = next(l for l, p in new_options.items() if p == correct_phrase)
                        t_copy["options"] = new_options
                        t_copy["correct"] = new_correct
                    shuffled_turns.append(t_copy)
                run_turns = shuffled_turns

            future_to_task[
                pool.submit(
                    _run_dual_agent_eval_task,
                    config, model, temperature, reasoner_model, matcher_model,
                    ollama_options, cache_path, cache_enabled, run_turns
                )
            ] = (run_idx, 0)

        run_results: dict[int, list[int | None]] = {i + 1: [None] for i in range(runs)}

        for future in concurrent.futures.as_completed(future_to_task):
            run_idx, condition_idx = future_to_task[future]
            res = future.result()
            end_to_end_hits = sum(1 for r in res if r.get("end_to_end_correct", False))
            binding_total = sum(1 for r in res if r.get("binding_scored", False))
            binding_hits = sum(1 for r in res if r.get("binding_scored", False) and r.get("binding_correct", False))

            end_to_end_ratio = (end_to_end_hits / n_turns) if n_turns else 0.0
            binding_ratio = (binding_hits / binding_total) if binding_total else 0.0

            for r in res:
                t_idx = r["turn"] - 1
                if r.get("end_to_end_correct", False):
                    hits_per_turn[condition_idx][t_idx] += 1
                answers_per_turn_da[t_idx].append(r.get("answer"))
                resp_len = len((r.get("response") or "").split())
                (tpca_correct_da if r.get("end_to_end_correct", False) else tpca_wrong_da).append(resp_len)
                method = r.get("extraction_method")
                if method:
                    emds_da[method] += 1
                
                binding_scored = r.get("binding_scored", False)
                binding_correct = r.get("binding_correct", False)
                reasoner_binding_metrics.append((binding_scored, binding_correct))
                
                matcher_conf = r.get("agent2_matcher_confidence", 0.0)
                end_to_end_correct = 1 if r.get("end_to_end_correct", False) else 0
                matcher_calibration_preds.append((matcher_conf, end_to_end_correct))

            efr_counts_da.append(sum(1 for r in res if r.get("answer") is None))
            run_results[run_idx][condition_idx] = end_to_end_hits
            scores[condition_idx].append(end_to_end_hits)

            metric_scores[condition_idx]["end_to_end"].append(end_to_end_ratio)
            metric_scores[condition_idx]["binding"].append(binding_ratio)

            scored = [r for r in res if "evidence_f1" in r]
            if scored:
                for metric_key in reasoning_scores:
                    avg_val = sum(r[metric_key] for r in scored) / len(scored)
                    reasoning_scores[metric_key].append(avg_val)

            bcr_vals = [r["bcr"] for r in res if "bcr" in r]
            sbir_vals = [r["sbir"] for r in res if "sbir" in r]
            if bcr_vals:
                retrieval_scores_da["bcr"].append(sum(bcr_vals) / len(bcr_vals))
            if sbir_vals:
                retrieval_scores_da["sbir"].append(sum(sbir_vals) / len(sbir_vals))

            if all(v is not None for v in run_results[run_idx]):
                (s1,) = run_results[run_idx]
                print(f"✓ Run {run_idx:>2}: [1 DA] {s1}/{n_turns}", flush=True)

    elapsed = time.time() - start
    n = len(scores[0])
    wct_per_turn_da = elapsed / (runs * n_turns) if runs * n_turns > 0 else 0.0

    afr_da_vals, consistent_da = [], 0
    for turn_answers in answers_per_turn_da:
        ta = [a for a in turn_answers if a is not None]
        if not ta:
            continue
        mode_count = Counter(ta).most_common(1)[0][1]
        afr_da_vals.append((len(ta) - mode_count) / len(ta))
        if len(set(ta)) == 1:
            consistent_da += 1
    mean_afr_da = sum(afr_da_vals) / len(afr_da_vals) if afr_da_vals else 0.0
    ds_da = consistent_da / len(answers_per_turn_da) if answers_per_turn_da else 0.0
    efr_da = (sum(efr_counts_da) / len(efr_counts_da) / n_turns) if efr_counts_da and n_turns else 0.0
    c_da = sum(tpca_correct_da) / len(tpca_correct_da) if tpca_correct_da else 0.0
    w_da = sum(tpca_wrong_da) / len(tpca_wrong_da) if tpca_wrong_da else 0.0
    total_da = sum(emds_da.values())

    print("\n" + "=" * 80)
    print(f"SUMMARY OVER {n} RUNS (DUAL-AGENT)")
    print("=" * 80)

    condition_labels = ["[1] WITH STORE (Dual-Agent)            "]

    for idx, label in enumerate(condition_labels):
        print(f"  {label}")
        for metric_name, metric_label in (
            ("binding", "Belief Binding Rate (BBR)"),
            ("end_to_end", "End-to-End (BTR if counterfactual)"),
        ):
            sc = metric_scores[idx][metric_name]
            avg = sum(sc) / len(sc) if sc else 0.0
            var = statistics.variance(sc) if len(sc) > 1 else 0.0
            std = statistics.stdev(sc) if len(sc) > 1 else 0.0
            print(f"    - {metric_label:<10} Avg: {avg:.4f} | Var: {var:.6f} | StdDev: {std:.4f}")

        raw_hits = ", ".join(str(x) for x in scores[idx])
        print(f"    - End-to-End raw hits: [{raw_hits}]")

        ds_note = " ← only meaningful at temp=0" if temperature != 0.0 else ""
        print(f"    EFR (Extraction Failure Rate)   | {efr_da:.4f}")
        print(f"    AFR (Answer Flip Rate)          | {mean_afr_da:.4f}")
        print(f"    DS  (Determinism Score)         | {ds_da:.4f}{ds_note}")
        print(f"    TPCA Correct / Wrong (words)    | {c_da:.1f} / {w_da:.1f}")
        if total_da:
            emd_str = "  ".join(f"{m}={cnt/total_da*100:.1f}%" for m, cnt in emds_da.most_common(5))
            print(f"    EMD (Extraction Method Dist)    | {emd_str}")

    if reasoning_scores["evidence_f1"]:
        print("\n  REASONING EVIDENCE METRICS:")
        for metric_key, metric_label in (
            ("evidence_precision", "Precision"),
            ("evidence_recall", "Recall"),
            ("evidence_f1", "F1"),
            ("evidence_cited_count", "Cited Keys"),
            ("evidence_canonical_count", "Canonical Keys"),
        ):
            sc = reasoning_scores[metric_key]
            r_n = len(sc)
            r_avg = sum(sc) / r_n if r_n > 0 else 0.0
            r_var = statistics.variance(sc) if r_n > 1 else 0.0
            r_std = statistics.stdev(sc) if r_n > 1 else 0.0
            print(f"    Evidence {metric_label:<10} | Avg: {r_avg:.4f} | Var: {r_var:.6f} | StdDev: {r_std:.4f}")

    if retrieval_scores_da["bcr"]:
        print("\n  RETRIEVAL FIDELITY:")
        for key, label in (("bcr", "BCR  (Belief Coverage Rate)  "), ("sbir", "SBIR (Spurious Injection Rate)")):
            sc = retrieval_scores_da[key]
            r_avg = sum(sc) / len(sc) if sc else 0.0
            print(f"    {label} | Avg: {r_avg:.4f}")

    reasoner_metrics = _compute_reasoner_metrics(reasoner_binding_metrics)
    if reasoner_binding_metrics:
        print("\n  REASONER (Agent 1) METRICS:")
        print(f"    Binding Accuracy                | {reasoner_metrics['reasoner_binding_accuracy']:.4f}")
        print(f"    Correct / Scored                | {reasoner_metrics['reasoner_correct_count']:.0f} / {reasoner_metrics['reasoner_scored_count']:.0f}")

    bs_matcher = ll_matcher = ece_matcher = mce_matcher = 0.0
    if matcher_calibration_preds:
        bs_matcher = brier_score(matcher_calibration_preds)
        ll_matcher = log_loss_score(matcher_calibration_preds)
        ece_matcher = expected_calibration_error(matcher_calibration_preds)
        mce_matcher = macro_calibration_error(matcher_calibration_preds)
        print("\n  MATCHER (Agent 2) CALIBRATION METRICS:")
        print(f"    Brier Score (Calibration)       | {bs_matcher:.4f}")
        print(f"    Log Loss (Uncertainty)          | {ll_matcher:.4f}")
        print(f"    ECE (Exp. Calibration Error)    | {ece_matcher:.4f}")
        print(f"    MacroCE (Macro Calib. Error)    | {mce_matcher:.4f}")

    print("\n  PER-TURN ACCURACY:")
    print(f"    {'Turn':<4} | {'[1 DA]':<24}")
    print(f"    {'─'*4} | {'─'*24}")
    for t in range(n_turns):
        acc1 = hits_per_turn[0][t]
        s1 = f"{acc1:>2}/{n} ({acc1 * 100 // n:>3}%)"
        print(f"    {t+1:>4} | {s1:<24}")

    print("=" * 80)
    print(f"Total wall-clock time: {elapsed:.1f}s  |  WCT/turn: {wct_per_turn_da:.3f}s\n")

    csv_filename = "eval_results_dual_agent.csv"
    file_exists = os.path.isfile(csv_filename)
    prompt_ver = get_eval_prompt_version(config.eval_prompt_version)
    header = [
        "Timestamp", "Domain", "Model", "Reasoner_Model", "Matcher_Model",
        "Temp", "Prompt_Ver", "Runs", "Metric_Family", "Summary_Metric",
        "Dual_Agent_Store", "Dual_Agent_Store_History", "Class_Label",
    ]
    try:
        _ensure_csv_header(csv_filename, header)
        with open(csv_filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(header)

            display_model = model_alias or model
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            def _da_row(family: str, metric: str, value: str) -> None:
                writer.writerow([
                    timestamp, config.name, display_model,
                    reasoner_model, matcher_model,
                    temperature, prompt_ver, runs,
                    family, metric, value, "", "",
                ])

            for metric_key, metric_family in (("binding", "Binding"), ("end_to_end", "End_to_End")):
                sc0 = metric_scores[0][metric_key]
                avg0 = sum(sc0) / len(sc0) if sc0 else 0.0
                _da_row(metric_family, "Average_Accuracy", f"{avg0:.4f}")
                var0 = statistics.variance(sc0) if len(sc0) > 1 else 0.0
                _da_row(metric_family, "Variance_Accuracy", f"{var0:.6f}")
                std0 = statistics.stdev(sc0) if len(sc0) > 1 else 0.0
                _da_row(metric_family, "Standard_Deviation_Accuracy", f"{std0:.6f}")

            _da_row("Efficiency", "WCT_WallClock_PerTurn_Seconds", f"{wct_per_turn_da:.4f}")
            _da_row("Stability", "EFR_Extraction_Failure_Rate", f"{efr_da:.4f}")
            _da_row("Stability", "AFR_Answer_Flip_Rate", f"{mean_afr_da:.4f}")
            _da_row("Stability", "DS_Determinism_Score", f"{ds_da:.4f}")
            _da_row("Efficiency", "TPCA_Words_Correct", f"{c_da:.1f}")
            _da_row("Efficiency", "TPCA_Words_Wrong", f"{w_da:.1f}")
            for method, cnt in emds_da.most_common(5):
                _da_row("Extraction", f"EMD_{method}", f"{cnt/total_da:.4f}" if total_da else "0.0")

            for metric_key, csv_metric in (
                ("evidence_precision", "Average_Evidence_Precision"),
                ("evidence_recall", "Average_Evidence_Recall"),
                ("evidence_f1", "Average_Evidence_F1"),
                ("evidence_cited_count", "Average_Evidence_Cited_Keys"),
                ("evidence_canonical_count", "Average_Evidence_Canonical_Keys"),
            ):
                sc = reasoning_scores[metric_key]
                r_avg = sum(sc) / len(sc) if sc else 0.0
                _da_row("Reasoning", csv_metric, f"{r_avg:.4f}")

            for key, csv_name in (
                ("bcr", "Average_BCR_BeliefCoverage"),
                ("sbir", "Average_SBIR_SpuriousInjection"),
            ):
                sc = retrieval_scores_da[key]
                r_avg = sum(sc) / len(sc) if sc else 0.0
                _da_row("Retrieval", csv_name, f"{r_avg:.4f}")

            _da_row("Reasoner", "Binding_Accuracy", f"{reasoner_metrics['reasoner_binding_accuracy']:.4f}")
            _da_row("Reasoner", "Correct_Count", f"{reasoner_metrics['reasoner_correct_count']:.0f}")
            _da_row("Reasoner", "Scored_Count", f"{reasoner_metrics['reasoner_scored_count']:.0f}")

            if matcher_calibration_preds:
                _da_row("Matcher", "Brier_Score", f"{bs_matcher:.4f}")
                _da_row("Matcher", "Log_Loss", f"{ll_matcher:.4f}")
                _da_row("Matcher", "ECE", f"{ece_matcher:.4f}")
                _da_row("Matcher", "MacroCE", f"{mce_matcher:.4f}")

        print(f"Results exported to {csv_filename}")
    except Exception as e:
        print(f"Failed to write CSV: {e}")

