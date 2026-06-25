"""
Minimal demo entry point for the CRE Research Agent.

Runs without Databricks credentials. Prints architecture summary and
reminds reviewers to run pytest for full validation.

Usage:
    python src/agent/main_demo.py
    # or from repo root:
    PYTHONPATH=src/agent python src/agent/main_demo.py
"""

import os
import sys

# Allow imports when run directly from repo root or src/agent/
_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from config import (  # noqa: E402
    ENABLE_AGENTIC_MODE,
    ENABLE_TOT_SYNTHESIS,
    MAX_AGENTIC_ITERATIONS,
    MAX_PLAN_STEPS,
)


def main() -> None:
    print("=" * 60)
    print("CRE Research Agent — Demo Stub")
    print("=" * 60)
    print()
    print("This is a capstone skeleton. Core modules:")
    print("  - agentic_orchestrator.py  (ReAct loop)")
    print("  - tot_synthesizer.py       (Tree-of-Thought synthesis)")
    print("  - agent_state.py           (plan + working memory)")
    print("  - agent_tools.py           (vector search, SQL, charts)")
    print()
    print("Feature flags:")
    print(f"  ENABLE_AGENTIC_MODE   = {ENABLE_AGENTIC_MODE}")
    print(f"  ENABLE_TOT_SYNTHESIS  = {ENABLE_TOT_SYNTHESIS}")
    print(f"  MAX_PLAN_STEPS        = {MAX_PLAN_STEPS}")
    print(f"  MAX_AGENTIC_ITERATIONS= {MAX_AGENTIC_ITERATIONS}")
    print()
    print("Sample query (complex / ToT-eligible):")
    print('  "Compare Dallas vs Phoenix for a regional HQ — cost, talent, risk."')
    print()
    print("To validate logic locally (no cloud required):")
    print("  pytest src/tests/ -v")
    print()
    print("See examples/sample_queries.md and docs/evaluation.md for more.")
    print("=" * 60)


if __name__ == "__main__":
    main()
