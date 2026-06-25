"""
Configuration for CRE Research Agent.

All settings are driven by environment variables with sensible defaults.
"""

import os

# =============================================================================
# Data Platform Configuration
# =============================================================================

CATALOG = os.environ.get("CATALOG", "your_catalog")
SCHEMA = os.environ.get("SCHEMA", "your_schema")
NAME_SUFFIX = os.environ.get("NAME_SUFFIX", "demo")

# =============================================================================
# LLM Endpoints
# =============================================================================

LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4")
TOOL_LLM_ENDPOINT = os.environ.get("TOOL_LLM_ENDPOINT", "databricks-claude-sonnet-4")
RAG_ENDPOINT = os.environ.get("RAG_ENDPOINT", "your-rag-endpoint")

# =============================================================================
# Vector Search
# =============================================================================

VECTOR_INDEX = os.environ.get(
    "VECTOR_INDEX",
    f"{CATALOG}.{SCHEMA}.your_documents_index_{NAME_SUFFIX}",
)
VS_ENDPOINT = os.environ.get("VECTOR_ENDPOINT", "your_vs_endpoint")

# =============================================================================
# Feature Flags
# =============================================================================

ENABLE_AGENTIC_MODE = os.environ.get("ENABLE_AGENTIC_MODE", "true").lower() == "true"
ENABLE_TRACING = os.environ.get("ENABLE_TRACING", "true").lower() == "true"

# Tree of Thought synthesis (experimental). When enabled and a query has
# completed ≥3 pillar workers (cost + talent + risk), runs beam-3 synthesis
# across cost/talent/risk lenses and selects the highest-scoring branch.
# Adds 3-6 LLM calls per complex query — disabled by default.
ENABLE_TOT_SYNTHESIS = os.environ.get("ENABLE_TOT_SYNTHESIS", "false").lower() == "true"

# Self-critique refinement: when enabled and self-critique score < threshold,
# re-retrieves with a gap-targeted query and re-synthesizes.
ENABLE_CRITIQUE_REFINEMENT = os.environ.get("ENABLE_CRITIQUE_REFINEMENT", "true").lower() == "true"

# =============================================================================
# Agent Parameters
# =============================================================================

MAX_AGENTIC_ITERATIONS = int(os.environ.get("MAX_AGENTIC_ITERATIONS", "10"))
MAX_PLAN_STEPS = int(os.environ.get("MAX_PLAN_STEPS", "5"))
QUALITY_THRESHOLD = float(os.environ.get("QUALITY_THRESHOLD", "0.6"))
MIN_SOURCES_THRESHOLD = int(os.environ.get("MIN_SOURCES_THRESHOLD", "3"))

# =============================================================================
# Databricks Connection
# =============================================================================

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "")
SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "")

# =============================================================================
# Demo Mode (when Databricks is unavailable)
# =============================================================================

DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
