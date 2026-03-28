"""
run_evals.py  —  Run the MCQ evaluation N times and average the results.

Perf improvements over the subprocess version:
  - Imports mcq_eval directly (no per-run Python startup overhead).
  - Shares a single OllamaClient across all runs.
  - In each run, all 3 conditions are executed concurrently using threads.
  - All 7 runs are also executed concurrently (thread per run).
"""
import sys, os, re, time, random, concurrent.futures, statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mcq_eval as ev
from belief_store.llm_client import OllamaClient

RUNS = 10



def main():
    print("Connecting to Ollama (gemma3:1b)...\n")
    llm = OllamaClient(model="gemma3:1b")

    print(f"Launching {RUNS} runs ({RUNS * 3} total tasks in flat parallel pool of 4)\n")
    start = time.time()

    scores = [[], [], []]
    turns = ev.TURNS

    # Dispatch all (RUNS * 3) tasks into a single flat pool
    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        future_to_task = {}
        for i in range(RUNS):
            idx = i + 1
            future_to_task[pool.submit(ev.run_with_store, llm, turns)] = (idx, 0)
            future_to_task[pool.submit(ev.run_with_store_with_history, llm, turns)] = (idx, 1)
            future_to_task[pool.submit(ev.run_without_store, llm, turns)] = (idx, 2)

        # Track completed runs (to print progress when all 3 conditions for a run are done)
        run_results = {i+1: [None, None, None] for i in range(RUNS)}

        for future in concurrent.futures.as_completed(future_to_task):
            run_idx, condition_idx = future_to_task[future]
            res = future.result()
            hits = sum(r["hit"] for r in res)
            
            run_results[run_idx][condition_idx] = hits
            scores[condition_idx].append(hits)

            # If all 3 conditions for this run are finished, print the progress line
            if all(v is not None for v in run_results[run_idx]):
                s1, s2, s3 = run_results[run_idx]
                print(f"✓ Run {run_idx:>2}: [1] {s1}/10 | [2] {s2}/10 | [3] {s3}/10")

    elapsed = time.time() - start
    n = len(scores[0])

    print("\n" + "=" * 65)
    print(f"SUMMARY OVER {n} RUNS")
    print("=" * 65)
    for label, sc in zip(
        ["[1] WITH STORE            ", "[2] WITH STORE (+History) ", "[3] NO STORE              "],
        scores,
    ):
        avg = sum(sc) / n
        var = statistics.variance(sc) if n > 1 else 0.0
        sc_str = ", ".join(str(x) for x in sc)
        print(f"  {label} | Avg: {avg:.2f}/10 | Var: {var:.2f} | Scores: [{sc_str}]")
    print("=" * 65)
    print(f"Total wall-clock time: {elapsed:.1f}s\n")


if __name__ == "__main__":
    main()
