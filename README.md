# CRE Research Agent — Capstone Project

A production-grade **Agentic RAG** system for Commercial Real Estate (CRE) intelligence.  
The agent answers complex market research queries by planning multi-step retrieval, executing specialized workers, and synthesizing evidence-grounded recommendations.

---

## Architecture Overview

```
User Query
    │
    ▼
┌──────────────────────────────────────┐
│  Planner (LLM-driven decomposition)  │
└──────────────┬───────────────────────┘
               │
   Complexity gate (simple vs complex)
          │                │
      simple           complex
          │                │
          ▼                ▼
┌───────────────┐  ┌────────────────────────┐
│ Linear ReAct  │  │ Parallel Workers       │
│ (retrieve →   │  │ (Cost / Talent / Risk) │
│  synthesize)  │  │ + Vector Search        │
└──────┬────────┘  └──────────┬─────────────┘
       │                      │
       │                      ▼
       │       ┌──────────────────────────────┐
       │       │ Tree-of-Thought Synthesis    │
       │       │ (beam-3, prune <0.5, select) │
       │       └─────────────┬────────────────┘
       │                     │
       ▼                     ▼
  ┌────────────────────────────────┐
  │ Final Response + Citations     │
  └────────────────────────────────┘
```

### Key Components

| Module | Responsibility |
|--------|---------------|
| `agent_state.py` | State management, execution plan, working memory |
| `agentic_orchestrator.py` | ReAct loop, planning, execution, synthesis |
| `tot_synthesizer.py` | Tree-of-Thought multi-branch reasoning |
| `agent_tools.py` | Unified tool interface (vector search, SQL, charts, maps) |
| `config.py` | Feature flags and environment-based configuration |
| `logging_setup.py` | Color-coded structured logging |

---

## Features

- **ReAct Reasoning Loop** — Plan → Execute → Observe → Evaluate → Refine
- **Tree of Thought (ToT)** — Beam-3 synthesis across cost/talent/risk lenses with self-critique scoring and pruning
- **Multi-Agent Workers** — Specialized cost, talent, and risk analysis workers executing in parallel
- **Hybrid Retrieval** — BM25 + dense embedding vector search over chunked documents
- **Self-Critique** — LLM-based quality scoring (relevance, support, usefulness) with automatic refinement
- **Working Memory** — In-session fact accumulation, source deduplication, step result tracking
- **Feature Flags** — `ENABLE_TOT_SYNTHESIS`, `ENABLE_AGENTIC_MODE`, etc.
- **Structured Logging** — Color-coded agent stages (Planning, Fetch, Execution, Synthesis, Quality, Delivery)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run automated tests (validates ToT + orchestrator logic)
pytest src/tests/ -v

# Demo stub (no cloud credentials required)
python src/agent/main_demo.py
```

For a connected deployment, set Databricks env vars (see Configuration) and wire vector search in your runtime.

**Supporting materials:** `docs/evaluation.md`, `examples/expected_outputs.md`, `examples/test_results.txt`

---

## Configuration

All configuration lives in `src/agent/config.py` and is driven by environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CATALOG` | `your_catalog` | Unity Catalog name (set your own) |
| `SCHEMA` | `your_schema` | Schema name (set your own) |
| `VECTOR_INDEX` | `{CATALOG}.{SCHEMA}.your_documents_index_demo` | Vector search index |
| `LLM_ENDPOINT` | `databricks-claude-sonnet-4` | LLM serving endpoint |
| `ENABLE_TOT_SYNTHESIS` | `false` | Enable Tree-of-Thought for complex queries |
| `ENABLE_AGENTIC_MODE` | `true` | Enable full agentic orchestration |
| `MAX_AGENTIC_ITERATIONS` | `10` | Max refinement loops |

---

## Tree of Thought (ToT) — Design

ToT activates when a query completes 3+ pillar workers (cost + talent + risk):

1. **Branch Generation** — 3 parallel branches, each synthesizing through a different lens
2. **Scoring** — Self-critique evaluates each branch (relevance, support, usefulness → composite score)
3. **Pruning** — Branches scoring < 0.5 are discarded
4. **Selection** — Highest-scoring branch wins; ties (within 0.1) present both perspectives

This avoids **premature commitment** — where a linear chain of thought locks into one framing early and misses better alternatives.

---

## Project Structure

```
cmu-capstone-cre-agent/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── main_demo.py            # Demo entry point (no cloud required)
│   │   ├── agent_state.py          # State, plan, working memory
│   │   ├── agentic_orchestrator.py # ReAct loop + ToT integration
│   │   ├── tot_synthesizer.py      # Tree-of-Thought engine
│   │   ├── agent_tools.py          # Tool interface (vector search, SQL, charts)
│   │   ├── config.py               # Environment-based configuration
│   │   └── logging_setup.py        # Color-coded structured logging
│   └── tests/
│       ├── test_tot_synthesizer.py
│       └── test_tot_orchestrator_integration.py
├── docs/
│   ├── architecture.md             # Detailed design documentation
│   └── evaluation.md               # Test results + design metrics
└── examples/
    ├── sample_queries.md           # Example queries and expected behavior
    ├── expected_outputs.md         # Response shape examples
    └── test_results.txt            # pytest output (12/12 passed)
```

---

## Capstone Checkpoints

This project was developed across 6 iterative checkpoints:

1. **Checkpoint 1.1** — Problem scoping and initial agent design
2. **Checkpoint 2.1** — Reasoning loops, memory, and tool integration
3. **Checkpoint 3.1** — RAG and retrieval design
4. **Checkpoint 4.1** — Tree of Thought reasoning integration
5. **Checkpoint 5.1** — Multi-agent architecture and coordination
6. **Checkpoint 6.1** — Safety guardrails and human intervention plan

---

## License

Academic project — not for commercial use.
