"""eval_harness.py — Backwards-compatible façade.

All functionality has been split into focused modules:
  - answer_extraction: Answer parsing from LLM responses
  - eval_metrics: Calibration, evidence, retrieval metrics
  - eval_common: DomainConfig, belief helpers, logging
  - eval_conditions: Evaluation condition runners
  - eval_orchestrator: Multi-run orchestrators + CSV export
"""

from evaluation.answer_extraction import * 
from evaluation.eval_metrics import *        
from evaluation.eval_common import *         
from evaluation.eval_conditions import *     
from evaluation.eval_orchestrator import *   

# Backwards-compatible re-exports for a few internal helpers that were
# imported directly by the web UI and tests. These have leading underscores
# in `eval_common.py`, so `from evaluation.eval_harness import *` would not
# expose them; export explicitly to guarantee compatibility.
from evaluation.eval_common import _get_filter_spec, _resolve_and_serialize, _format_question  # noqa: F401
