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

RUNS = 5

def shuffled(turns):
    """Return a copy of TURNS with options shuffled so the correct letter varies."""
    result = []
    for turn in turns:
        opts = list(turn["options"].values())
        correct_text = turn["options"][turn["correct"]]
        random.shuffle(opts)
        new_options = {chr(65 + i): opt for i, opt in enumerate(opts)}
        new_correct = next(k for k, v in new_options.items() if v == correct_text)
        result.append({**turn, "options": new_options, "correct": new_correct})
    return result


def run_one(run_idx, llm):
    """Run all 3 conditions for a single evaluation trial, conditions run in parallel."""
    turns = shuffled(ev.TURNS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f1 = pool.submit(ev.run_with_store, llm, turns)
        f2 = pool.submit(ev.run_with_store_with_history, llm, turns)
        f3 = pool.submit(ev.run_without_store, llm, turns)

        r1 = f1.result()
        r2 = f2.result()
        r3 = f3.result()

    s1 = sum(r["hit"] for r in r1)
    s2 = sum(r["hit"] for r in r2)
    s3 = sum(r["hit"] for r in r3)

    print(f"✓ Run {run_idx:>2}: [1] {s1}/10 | [2] {s2}/10 | [3] {s3}/10")
    return s1, s2, s3


def main():
    print(f"Connecting to Ollama (gemma3:1b)...\n")
    llm = OllamaClient(model="gemma3:1b")

    print(f"Launching {RUNS} runs (3 conditions per run, all conditions run concurrently)\n")
    start = time.time()

    scores = [[], [], []]

    # Each run fires its 3 conditions in parallel internally; runs themselves also concurrent
    with concurrent.futures.ThreadPoolExecutor(max_workers=RUNS) as pool:
        futures = {pool.submit(run_one, i + 1, llm): i for i in range(RUNS)}
        for future in concurrent.futures.as_completed(futures):
            s1, s2, s3 = future.result()
            scores[0].append(s1)
            scores[1].append(s2)
            scores[2].append(s3)

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
