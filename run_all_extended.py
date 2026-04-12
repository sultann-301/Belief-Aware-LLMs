#!/usr/bin/env python3
"""
run_all_extended.py — Overnight execution script for belief-aware evaluations.
Runs all main extended domains sequentially with a single worker for stability.
"""

import subprocess
import os
import sys

BASE_DOMAINS = ["loan", "alien_clinic", "crime_scene", "thorncrester"]
SUBSETS = ["negation", "1hop", "2hop", "3hop", "4hop", "belief_maintenance"]

DOMAINS = [f"{d}_{s}" for d in BASE_DOMAINS for s in SUBSETS]

LOG_FILE = "nightly_eval.log"
RUNS = 10
WORKERS = 1 # Single worker to avoid GPU status 3 errors on Metal

def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

def run_eval(domain):
    cmd = [
        sys.executable, "-u", "evaluation/run_evals.py",
        "--domain", domain,
        "--runs", str(RUNS),
        "--workers", str(WORKERS)
    ]
    log(f"\n{'='*60}")
    log(f"STARTING DOMAIN: {domain}")
    log(f"COMMAND: {' '.join(cmd)}")
    log(f"{'='*60}\n")
    
    try:
        # We use subprocess.Popen to stream output to the log file in real-time
        with open(LOG_FILE, "a") as f:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    f.write(line)
            
            process.wait()
            if process.returncode == 0:
                log(f"\nCOMPLETED DOMAIN: {domain} successfully.")
            else:
                log(f"\nFAILED DOMAIN: {domain} with exit code {process.returncode}")
    except Exception as e:
        log(f"ERROR running {domain}: {str(e)}")

def main():
    # Clear log file or start fresh
    with open(LOG_FILE, "w") as f:
        f.write(f"Nightly Evaluation Run - Started at {subprocess.check_output(['date']).decode().strip()}\n")
        f.write(f"Config: runs={RUNS}, workers={WORKERS}\n")
    
    for domain in DOMAINS:
        run_eval(domain)
    
    log(f"\n{'='*60}")
    log("ALL RUNS FINISHED")
    log(f"{'='*60}")

if __name__ == "__main__":
    main()
