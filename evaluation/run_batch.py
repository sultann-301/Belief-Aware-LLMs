#!/usr/bin/env python3
import subprocess
import json
import os
import time
import sys

# ────────────────────────────────────────────────────────────────────
# BATCH CONFIGURATION
# ────────────────────────────────────────────────────────────────────

# Batch mode: "standard" (single model) or "dual-agent" (reasoner + matcher)
MODE = "dual-agent"  # Change to "standard" for single-model batch

# STANDARD MODE: Single model configuration
MODELS = [
    "ministral-3:3b",
    "hoangquan456/qwen3-nothink:4b"


    # "ministral:latest",
]

# DUAL-AGENT MODE: Separate reasoner and matcher models
REASONER_MODELS = [
    "gemma3:1b",
]
COOLDOWN_SECONDS = 330
MATCHER_MODELS = [
    # "ministral-3:3b",
    "gemma3:1b",  # Uncomment to test same-model baseline
]

# Prompt versions to compare
PROMPTS = ["v13"]

# Temperature(s) to test
TEMPERATURES = [0.7]  # Set to [0.0, 0.7] to test both deterministic and stochastic

# Domains to iterate through
DOMAINS = [
    "crime_scene_belief_maintenance",
    "thorncrester_belief_maintenance",
    "thorncrester_negation",
    "loan_negation",
    "crime_scene_negation",
    "alien_clinic_negation",
    "loan_absurd_temporal",
    "alien_clinic_absurd_temporal",
    "crime_scene_absurd_temporal",
    "thorncrester_absurd_temporal"
    "loan_grounding",
    "alien_clinic_grounding",
    "crime_scene_grounding",
    "thorncrester_grounding"
]

RUNS_PER_CONFIG = 10
WORKERS = 4

def print_progress(current, total):
    """Prints a simple ASCII progress bar."""
    percent = 100 * (current / total)
    bar_length = 40
    filled_length = int(bar_length * current // total)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    sys.stdout.write(f"\rProgress: |{bar}| {percent:.1f}% ({current}/{total})")
    sys.stdout.flush()

# State and log files include mode in filename
STATE_FILE = f"evaluation/batch_state_{MODE}.json"
LOG_FILE = f"evaluation/batch_progress_{MODE}.log"

# ────────────────────────────────────────────────────────────────────

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with open(LOG_FILE, "a") as f:
        f.write(formatted + "\n")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {"completed": []}
    return {"completed": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def main():
    state = load_state()
    
    if MODE == "standard":
        run_standard_batch(state)
    elif MODE == "dual-agent":
        run_dual_agent_batch(state)
    else:
        log(f"ERROR: Unknown MODE '{MODE}'. Use 'standard' or 'dual-agent'")

def run_standard_batch(state):
    """Standard single-model batch evaluation."""
    configs = []
    for model in MODELS:
        for prompt in PROMPTS:
            for temperature in TEMPERATURES:
                for domain in DOMAINS:
                    configs.append(f"std|{model}|{prompt}|{temperature}|{domain}")
    
    total_configs = len(configs)
    current_count = len(state["completed"])
    
    log(f"Starting STANDARD Batch Eval: {total_configs} total configurations planned.")
    log(f"Already completed: {current_count}")
    
    for i, config_id in enumerate(configs):
        if config_id in state["completed"]:
            continue
            
        parts = config_id.split("|")
        _, model, prompt, temperature, domain = parts
        
        print_progress(i, total_configs)
        print() # Move to next line for log
        log(f"RUNNING: {domain} | Model: {model} | Prompt: {prompt} | Temp: {temperature} | Runs: {RUNS_PER_CONFIG}")
        
        cmd = [
            sys.executable, "evaluation/run_evals.py",
            "--domain", domain,
            "--model", model,
            "--eval-prompt-version", prompt,
            "--runs", str(RUNS_PER_CONFIG),
            "--workers", str(WORKERS),
            "--temperature", str(temperature)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                log(f"SUCCESS: {config_id}")
                state["completed"].append(config_id)
                save_state(state)
                
                log("Cooldown: Sleeping for 300 seconds (5 mins)...")
                for remaining in range(300, 0, -1):
                    sys.stdout.write(f"\rCooling down... {remaining}s remaining   ")
                    sys.stdout.flush()
                    time.sleep(1)
                print()
            else:
                log(f"FAILURE: {config_id}\nError: {result.stderr}")
        except Exception as e:
            log(f"CRITICAL ERROR running {config_id}: {str(e)}")

    print_progress(total_configs, total_configs)
    print()
    log("Standard Batch Evaluation Complete!")

def run_dual_agent_batch(state):
    """Dual-agent batch evaluation with separate reasoner and matcher models."""
    configs = []
    for reasoner_model in REASONER_MODELS:
        for matcher_model in MATCHER_MODELS:
            for prompt in PROMPTS:
                for temperature in TEMPERATURES:
                    for domain in DOMAINS:
                        configs.append(f"da|{reasoner_model}|{matcher_model}|{prompt}|{temperature}|{domain}")

    total_configs = len(configs)
    current_count = len(state["completed"])
    
    log(f"Starting DUAL-AGENT Batch Eval: {total_configs} total configurations planned.")
    log(f"Already completed: {current_count}")
    log(f"Reasoner models: {REASONER_MODELS}")
    log(f"Matcher models: {MATCHER_MODELS}")
    log(f"Temperatures: {TEMPERATURES}")
    
    for i, config_id in enumerate(configs):
        if config_id in state["completed"]:
            continue
            
        parts = config_id.split("|")
        _, reasoner_model, matcher_model, prompt, temperature, domain = parts

        print_progress(i, total_configs)
        print()
        log(f"RUNNING: {domain} | Reasoner: {reasoner_model} | Matcher: {matcher_model} | Prompt: {prompt} | Temp: {temperature} | Runs: {RUNS_PER_CONFIG}")
        
        cmd = [
            sys.executable, "evaluation/run_evals.py",
            "--domain", domain,
            "--dual-agent",
            "--reasoner-model", reasoner_model,
            "--matcher-model", matcher_model,
            "--eval-prompt-version", prompt,
            "--runs", str(RUNS_PER_CONFIG),
            "--workers", str(WORKERS),
            "--temperature", str(temperature)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                log(f"SUCCESS: {config_id}")
                state["completed"].append(config_id)
                save_state(state)
                
                log("Cooldown: Sleeping for 300 seconds (5 mins)...")
                for remaining in range(COOLDOWN_SECONDS, 0, -1):
                    sys.stdout.write(f"\rCooling down... {remaining}s remaining   ")
                    sys.stdout.flush()
                    time.sleep(1)
                print()
            else:
                log(f"FAILURE: {config_id}\nError: {result.stderr}")
        except Exception as e:
            log(f"CRITICAL ERROR running {config_id}: {str(e)}")

    print_progress(total_configs, total_configs)
    print()
    log("Dual-Agent Batch Evaluation Complete!")

if __name__ == "__main__":
    main()
