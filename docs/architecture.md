# Architecture Documentation

## System Overview

The CRE Research Agent is a production-grade Agentic RAG system designed for Commercial Real Estate intelligence. It enables analysts to ask complex multi-dimensional questions and receive grounded, citation-backed recommendations.

---

## Core Design Principles

1. **Structured Extraction Beats Generic Agents** — Every document goes through entity extraction, summarization, and knowledge-graph construction (not just embedding).

2. **Three-Leg Research Stack** — Every query can draw from:
   - **Vectors**: Relevance-ranked text retrieval (BM25 + dense)
   - **Entity Tables**: Precise filtering via structured data
   - **Summaries**: High-level overviews without tool calls

3. **Synthesize by Default, Assets for Evidence** — Generate insights via synthesis unless the user requests exact data (tables, figures), in which case pull pre-extracted assets verbatim.

---

## Agent Architecture

### ReAct Loop (Reasoning + Acting)

```
Query → Planner → [Step₁ → Observe → Evaluate → Refine]ⁿ → Synthesize → Response
```

Each step follows: **Act** (call tool) → **Observe** (inspect result) → **Evaluate** (quality threshold?) → **Refine** (if below threshold, rephrase and retry).

Bounded by:
- **MAX_PLAN_STEPS = 5** — maximum steps in a plan
- **MAX_AGENTIC_ITERATIONS = 10** — total refinement loops

### Tree of Thought (ToT)

For complex comparative queries (≥3 pillar workers completed), replaces linear synthesis:

1. **3 parallel branches** — cost, talent, risk lenses
2. **Self-critique scoring** — each branch evaluated for relevance, support, usefulness
3. **Pruning** — branches < 0.5 discarded
4. **Winner selection** — highest score wins; ties (within 0.1) present both views

```
Workers Complete → build_evidence_block() → 3× _run_single_branch() → _select_winner() → final response
```

### Multi-Agent Workers

| Agent | Responsibility |
|-------|---------------|
| **Planner** | Decompose query into execution steps |
| **Retriever** | Vector search + source accumulation |
| **Cost Worker** | Lease rates, opex, capex, tax analysis |
| **Talent Worker** | Labor pool, wages, education pipeline |
| **Risk Worker** | Volatility, regulatory, climate exposure |
| **Critic/Synthesizer** | Self-critique + final synthesis |

---

## State Management

```python
AgentState:
  query: str
  complexity: QueryComplexity (SIMPLE | MODERATE | COMPLEX | RESEARCH)
  plan: List[ExecutionStep]
  memory: WorkingMemory
    - facts: Dict[str, Any]        # accumulated knowledge
    - sources: List[Dict]          # deduplicated retrieved docs
    - step_results: Dict[str, Any] # per-step outputs
```

---

## Safety Guardrails

| Guardrail | Enforcement |
|-----------|-------------|
| Domain scope | System prompt restricts to CRE/location intelligence |
| Input sanitization | Strip injection patterns, enforce character limits |
| Output citation | Every claim must cite [Source: file, page] |
| SQL read-only | SELECT only in production; DDL requires explicit approval |
| Iteration cap | Max 10 loops prevents runaway compute |
| Min source threshold | Gap warning if < 3 relevant sources |
| Token budget | 1500 tokens per worker step |

---

## Evaluation Metrics

| Metric | Target | Method |
|--------|--------|--------|
| Groundedness | ≥ 0.85 | % claims with citation |
| Source support | ≥ 0.70 | Critic scores evidence alignment |
| Relevance | ≥ 0.75 | Query-response semantic similarity |
| Confidence calibration | ±0.10 | Predicted vs actual accuracy |
| Latency (p95) | < 30s | End-to-end response time |
| Fallback rate | < 15% | % queries falling to linear synthesis |

---

## Human Intervention Criteria

The system escalates to human review when:
- Confidence < 0.5 after critique
- Conflicting sources with no resolution
- Query outside CRE domain scope
- DDL/write operations requested
- Retrieval returns < 3 relevant sources after refinement
