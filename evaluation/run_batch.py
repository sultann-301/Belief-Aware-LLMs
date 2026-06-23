#!/usr/bin/env python3
import subprocess
import json
import os
import time
import sys
import importlib

# ────────────────────────────────────────────────────────────────────
# BATCH CONFIGURATION
# ────────────────────────────────────────────────────────────────────

# Batch mode: "standard" (single model) or "dual-agent" (reasoner + matcher)
MODE = "dual-agent"  # Change to "standard" for single-model batch

# Prompt Versions
DEFAULT_EVAL_PROMPT_VERSION = "v15"
DEFAULT_BASELINE_PROMPT_VERSION = "v1"

# STANDARD MODE: Single model configuration
MODELS = [
     "gemma3:1b",
    "llama3.2:1b",
     "ministral-3:3b",
    "hoangquan456/qwen3-nothink:4b",
     "gemma4:e2b"
]

HARD_SCENARIO_EXCLUDED_MODELS = {
    "gemma3:1b",
    "llama3.2:1b",
}


# ministral-3:3b                   
# qwen3.5:0.8b                       
# llama3.2:1b                      
# hoangquan456/qwen3-nothink:4b    
# gpt-oss:120b-cloud               
# gemma3:1b                        
# qwen3:4b                         
# DUAL-AGENT MODE: Separate reasoner and matcher models
REASONER_MODELS = [
    "llama3.2:1b",
    "hoangquan456/qwen3-nothink:4b",
]
COOLDOWN_SECONDS = 2
MATCHER_MODELS = [
   "gemma3:1b",
   "ministral-3:3b",
   "hoangquan456/qwen3-nothink:4b",

]

# Prompt versions to compare
PROMPTS = [DEFAULT_EVAL_PROMPT_VERSION]

# Temperature(s) to test
TEMPERATURES = [0.0]  # Set to [0.0, 0.7] to test both deterministic and stochastic

# Domains to iterate through
DOMAINS = [
    # 1. Prior Suppression (Core Thesis)
      "loan_absurd", "alien_clinic_absurd", "crime_scene_absurd", "thorncrester_absurd",
    
    # 2. Hallucination Resistance (Core Thesis)
     "loan_grounding", "alien_clinic_grounding", "crime_scene_grounding", "thorncrester_grounding",
    
    # 3. Temporal Tracking (Supporting)
     "loan_absurd_temporal", "alien_clinic_absurd_temporal", "crime_scene_absurd_temporal", "thorncrester_absurd_temporal",
    #  "loan_absurd_temporal_noise", "alien_clinic_absurd_temporal_noise", "crime_scene_absurd_temporal_noise", "thorncrester_absurd_temporal_noise",
    
    # 4. Context Stability (Supporting)
     "loan_belief_maintenance", "alien_clinic_belief_maintenance", "crime_scene_belief_maintenance", "thorncrester_belief_maintenance",
    
    # 5. Reasoning Depth (Supporting)
    # "loan_2hop", "alien_clinic_2hop", "crime_scene_2hop", "thorncrester_2hop",
    # "loan_3hop", "alien_clinic_3hop", "crime_scene_3hop", "thorncrester_3hop",
    
    # 6. Transparency (Unique)
    # "alien_clinic_trace_selection",
    
    # 7. Stress Testing (Hard Belief Revision)
    #   "loan_hard", "alien_clinic_hard", "crime_scene_hard", "thorncrester_hard",
]

# Sequential mode: Phase-specific configuration
PHASE1_DOMAINS = [
    "loan_absurd_temporal_noise",
    "alien_clinic_absurd_temporal_noise",
    "crime_scene_absurd_temporal_noise",
    "thorncrester_absurd_temporal_noise",
]

# Phase 2 (dual-agent) overrides
PHASE2_RUNS = 5
PHASE2_PAIRS = [
    ("gemma3:1b", "gemma3:1b"),
    ("gemma3:1b", "ministral-3:3b"),
    ("ministral-3:3b", "gemma3:1b"),
    ("ministral-3:3b", "hoangquan456/qwen3-nothink:4b"),
]

# Phase 1 runs (single-agent)
PHASE1_RUNS = 10

# Helper import for domain registry (used to enumerate available domains)
try:
    import evaluation.run_evals as run_evals
except Exception:
    run_evals = None

RUNS_PER_CONFIG = 10
WORKERS = 4
FAST_EVAL = False
OLLAMA_NUM_PREDICT = 768
OLLAMA_NUM_CTX = 8162
OLLAMA_REPEAT_PENALTY = None
OLLAMA_REPEAT_LAST_N = None
OLLAMA_TOP_K = None
OLLAMA_TOP_P = None
OLLAMA_KEEP_ALIVE = "10m"
CACHE_ENABLED = False
CACHE_DIR = ".cache/ollama_eval"

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
    elif MODE == "sequential":
        run_sequential_batch(state)
    else:
        log(f"ERROR: Unknown MODE '{MODE}'. Use 'standard' or 'dual-agent'")

def run_standard_batch(state):
    """Standard single-model batch evaluation."""
    configs = []
    for model in MODELS:
        for prompt in PROMPTS:
            for temperature in TEMPERATURES:
                for domain in DOMAINS:
                    if domain.endswith("_hard") and model in HARD_SCENARIO_EXCLUDED_MODELS:
                        continue
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
            "--baseline-prompt-version", DEFAULT_BASELINE_PROMPT_VERSION,
            "--runs", str(RUNS_PER_CONFIG),
            "--workers", str(WORKERS),
            "--temperature", str(temperature)
        ]
        if FAST_EVAL:
            cmd.append("--fast-eval")
        if OLLAMA_NUM_PREDICT is not None:
            cmd += ["--num-predict", str(OLLAMA_NUM_PREDICT)]
        if OLLAMA_NUM_CTX is not None:
            cmd += ["--num-ctx", str(OLLAMA_NUM_CTX)]
        if OLLAMA_REPEAT_PENALTY is not None:
            cmd += ["--repeat-penalty", str(OLLAMA_REPEAT_PENALTY)]
        if OLLAMA_REPEAT_LAST_N is not None:
            cmd += ["--repeat-last-n", str(OLLAMA_REPEAT_LAST_N)]
        if OLLAMA_TOP_K is not None:
            cmd += ["--top-k", str(OLLAMA_TOP_K)]
        if OLLAMA_TOP_P is not None:
            cmd += ["--top-p", str(OLLAMA_TOP_P)]
        if OLLAMA_KEEP_ALIVE is not None:
            cmd += ["--keep-alive", str(OLLAMA_KEEP_ALIVE)]
        if CACHE_ENABLED:
            cmd += ["--cache", "--cache-dir", CACHE_DIR]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                log(f"SUCCESS: {config_id}")
                state["completed"].append(config_id)
                save_state(state)
                
                log(f"Cooldown: Sleeping for {COOLDOWN_SECONDS} seconds...")
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
    log("Standard Batch Evaluation Complete!")

def run_dual_agent_batch(state):
    """Dual-agent batch evaluation with separate reasoner and matcher models."""
    if run_evals and hasattr(run_evals, "DOMAIN_REGISTRY"):
        all_domains = list(run_evals.DOMAIN_REGISTRY.keys())
    else:
        all_domains = list(DOMAINS)

    filtered_domains = DOMAINS

    configs = []
    for reasoner_model, matcher_model in PHASE2_PAIRS:
        for prompt in PROMPTS:
            for temperature in TEMPERATURES:
                for domain in filtered_domains:
                    configs.append(f"da|{reasoner_model}|{matcher_model}|{prompt}|{temperature}|{domain}")

    total_configs = len(configs)
    current_count = len(state["completed"])
    
    log(f"Starting DUAL-AGENT Batch Eval: {total_configs} total configurations planned.")
    log(f"Already completed: {current_count}")
    log(f"Model pairs: {PHASE2_PAIRS}")
    log(f"Domains: {filtered_domains}")
    log(f"Temperatures: {TEMPERATURES}")
    
    for i, config_id in enumerate(configs):
        if config_id in state["completed"]:
            continue
            
        parts = config_id.split("|")
        _, reasoner_model, matcher_model, prompt, temperature, domain = parts

        print_progress(i, total_configs)
        print()
        log(f"RUNNING: {domain} | Reasoner: {reasoner_model} | Matcher: {matcher_model} | Prompt: {prompt} | Temp: {temperature} | Runs: {PHASE2_RUNS}")
        
        cmd = [
            sys.executable, "evaluation/run_evals.py",
            "--domain", domain,
            "--dual-agent",
            "--reasoner-model", reasoner_model,
            "--matcher-model", matcher_model,
            "--eval-prompt-version", prompt,
            "--baseline-prompt-version", DEFAULT_BASELINE_PROMPT_VERSION,
            "--runs", str(PHASE2_RUNS),
            "--workers", str(WORKERS),
            "--temperature", str(temperature)
        ]
        if FAST_EVAL:
            cmd.append("--fast-eval")
        if OLLAMA_NUM_PREDICT is not None:
            cmd += ["--num-predict", str(OLLAMA_NUM_PREDICT)]
        if OLLAMA_NUM_CTX is not None:
            cmd += ["--num-ctx", str(OLLAMA_NUM_CTX)]
        if OLLAMA_REPEAT_PENALTY is not None:
            cmd += ["--repeat-penalty", str(OLLAMA_REPEAT_PENALTY)]
        if OLLAMA_REPEAT_LAST_N is not None:
            cmd += ["--repeat-last-n", str(OLLAMA_REPEAT_LAST_N)]
        if OLLAMA_TOP_K is not None:
            cmd += ["--top-k", str(OLLAMA_TOP_K)]
        if OLLAMA_TOP_P is not None:
            cmd += ["--top-p", str(OLLAMA_TOP_P)]
        if OLLAMA_KEEP_ALIVE is not None:
            cmd += ["--keep-alive", str(OLLAMA_KEEP_ALIVE)]
        if CACHE_ENABLED:
            cmd += ["--cache", "--cache-dir", CACHE_DIR]
        
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


def run_sequential_batch(state):
    """Sequential orchestration: Phase A (single-agent) then Phase B (dual-agent)."""
    # Phase A: single-agent on the specified PHASE1_DOMAINS
    phase1_configs = []
    for model in MODELS:
        for prompt in PROMPTS:
            for temperature in TEMPERATURES:
                for domain in PHASE1_DOMAINS:
                    phase1_configs.append(f"std|{model}|{prompt}|{temperature}|{domain}")

    total_p1 = len(phase1_configs)
    log(f"Starting SEQUENTIAL Phase A (single-agent): {total_p1} configurations planned.")

    for i, config_id in enumerate(phase1_configs):
        if config_id in state.get("completed", []):
            continue
        _, model, prompt, temperature, domain = config_id.split("|")

        print_progress(i, total_p1)
        print()
        log(f"PHASE A RUNNING: {domain} | Model: {model} | Prompt: {prompt} | Temp: {temperature} | Runs: {PHASE1_RUNS}")

        cmd = [
            sys.executable, "evaluation/run_evals.py",
            "--domain", domain,
            "--model", model,
            "--eval-prompt-version", prompt,
            "--baseline-prompt-version", DEFAULT_BASELINE_PROMPT_VERSION,
            "--runs", str(PHASE1_RUNS),
            "--workers", str(WORKERS),
            "--temperature", str(temperature)
        ]
        if FAST_EVAL:
            cmd.append("--fast-eval")
        if OLLAMA_NUM_PREDICT is not None:
            cmd += ["--num-predict", str(OLLAMA_NUM_PREDICT)]
        if OLLAMA_NUM_CTX is not None:
            cmd += ["--num-ctx", str(OLLAMA_NUM_CTX)]
        if OLLAMA_REPEAT_PENALTY is not None:
            cmd += ["--repeat-penalty", str(OLLAMA_REPEAT_PENALTY)]
        if OLLAMA_REPEAT_LAST_N is not None:
            cmd += ["--repeat-last-n", str(OLLAMA_REPEAT_LAST_N)]
        if OLLAMA_TOP_K is not None:
            cmd += ["--top-k", str(OLLAMA_TOP_K)]
        if OLLAMA_TOP_P is not None:
            cmd += ["--top-p", str(OLLAMA_TOP_P)]
        if OLLAMA_KEEP_ALIVE is not None:
            cmd += ["--keep-alive", str(OLLAMA_KEEP_ALIVE)]
        if CACHE_ENABLED:
            cmd += ["--cache", "--cache-dir", CACHE_DIR]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                log(f"SUCCESS: {config_id}")
                state.setdefault("completed", []).append(config_id)
                save_state(state)

                log(f"Cooldown: Sleeping for {COOLDOWN_SECONDS} seconds...")
                for remaining in range(COOLDOWN_SECONDS, 0, -1):
                    sys.stdout.write(f"\rCooling down... {remaining}s remaining   ")
                    sys.stdout.flush()
                    time.sleep(1)
                print()
            else:
                log(f"FAILURE: {config_id}\nError: {result.stderr}")
        except Exception as e:
            log(f"CRITICAL ERROR running {config_id}: {str(e)}")

    print_progress(total_p1, total_p1)
    print()
    log("Phase A Complete — starting Phase B (dual-agent)")

    # Phase B: dual-agent across available domains excluding 'hop' variants and '_hard' variants
    if run_evals and hasattr(run_evals, "DOMAIN_REGISTRY"):
        all_domains = list(run_evals.DOMAIN_REGISTRY.keys())
    else:
        log("WARNING: cannot import DOMAIN_REGISTRY; falling back to configured DOMAINS list for Phase B")
        all_domains = list(DOMAINS)

    filtered_domains = [d for d in all_domains if "noise" in d]

    phase2_configs = []
    for reasoner_model, matcher_model in PHASE2_PAIRS:
        for prompt in PROMPTS:
            for temperature in TEMPERATURES:
                for domain in filtered_domains:
                    phase2_configs.append(f"da|{reasoner_model}|{matcher_model}|{prompt}|{temperature}|{domain}")

    total_p2 = len(phase2_configs)
    log(f"Starting SEQUENTIAL Phase B (dual-agent): {total_p2} configurations planned.")

    for i, config_id in enumerate(phase2_configs):
        if config_id in state.get("completed", []):
            continue

        _, reasoner_model, matcher_model, prompt, temperature, domain = config_id.split("|")

        print_progress(i, total_p2)
        print()
        log(f"PHASE B RUNNING: {domain} | Reasoner: {reasoner_model} | Matcher: {matcher_model} | Prompt: {prompt} | Temp: {temperature} | Runs: {PHASE2_RUNS}")

        cmd = [
            sys.executable, "evaluation/run_evals.py",
            "--domain", domain,
            "--dual-agent",
            "--reasoner-model", reasoner_model,
            "--matcher-model", matcher_model,
            "--eval-prompt-version", prompt,
            "--baseline-prompt-version", DEFAULT_BASELINE_PROMPT_VERSION,
            "--runs", str(PHASE2_RUNS),
            "--workers", str(WORKERS),
            "--temperature", str(temperature)
        ]
        if FAST_EVAL:
            cmd.append("--fast-eval")
        if OLLAMA_NUM_PREDICT is not None:
            cmd += ["--num-predict", str(OLLAMA_NUM_PREDICT)]
        if OLLAMA_NUM_CTX is not None:
            cmd += ["--num-ctx", str(OLLAMA_NUM_CTX)]
        if OLLAMA_REPEAT_PENALTY is not None:
            cmd += ["--repeat-penalty", str(OLLAMA_REPEAT_PENALTY)]
        if OLLAMA_REPEAT_LAST_N is not None:
            cmd += ["--repeat-last-n", str(OLLAMA_REPEAT_LAST_N)]
        if OLLAMA_TOP_K is not None:
            cmd += ["--top-k", str(OLLAMA_TOP_K)]
        if OLLAMA_TOP_P is not None:
            cmd += ["--top-p", str(OLLAMA_TOP_P)]
        if OLLAMA_KEEP_ALIVE is not None:
            cmd += ["--keep-alive", str(OLLAMA_KEEP_ALIVE)]
        if CACHE_ENABLED:
            cmd += ["--cache", "--cache-dir", CACHE_DIR]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                log(f"SUCCESS: {config_id}")
                state.setdefault("completed", []).append(config_id)
                save_state(state)

                log(f"Cooldown: Sleeping for {COOLDOWN_SECONDS} seconds...")
                for remaining in range(COOLDOWN_SECONDS, 0, -1):
                    sys.stdout.write(f"\rCooling down... {remaining}s remaining   ")
                    sys.stdout.flush()
                    time.sleep(1)
                print()
            else:
                log(f"FAILURE: {config_id}\nError: {result.stderr}")
        except Exception as e:
            log(f"CRITICAL ERROR running {config_id}: {str(e)}")

    print_progress(total_p2, total_p2)
    print()
    log("Sequential Batch Evaluation Complete!")

if __name__ == "__main__":
    main()
