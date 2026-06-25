# Evaluation Summary

## Automated Tests

**Result: 12 / 12 tests passed** (see `examples/test_results.txt` for full output).

| Suite | Tests | What it validates |
|-------|-------|-------------------|
| `test_tot_synthesizer.py` | 9 | Branch scoring, pruning, winner selection, tie handling, fallback |
| `test_tot_orchestrator_integration.py` | 3 | ToT gating: flag off, worker threshold, enabled + 3 workers |

Run locally:

```bash
pip install -r requirements.txt
pytest src/tests/ -v
```

## Design Metrics (from Checkpoint 6.1)

These are the targets the production system is designed against. The public repo validates orchestration and ToT logic via unit/integration tests; live groundedness and latency require a connected vector index.

| Metric | What it measures | Target |
|--------|------------------|--------|
| **Groundedness** | % of claims backed by a retrieved citation | > 95% |
| **Source support score** | Self-critique "support" dimension (0–1) | > 0.7 |
| **Relevance score** | Self-critique "relevance" to the query | > 0.7 |
| **Confidence calibration** | Stated confidence vs citation density | Monotonic |
| **Latency** | End-to-end response time | < 30s simple, < 60s complex |
| **Fallback rate** | Queries falling back when retrieval fails | < 5% |
| **Missing data transparency** | Workers populate `missing_data` when evidence is thin | 100% |

## What the Tests Prove

- **ToT beam-3** selects the highest-scoring branch above prune threshold (0.5).
- **Tie policy** surfaces runner-up when scores are within 0.1.
- **Graceful degradation** falls back to linear synthesis when all branches prune or error.
- **Orchestrator gating** invokes ToT only when `ENABLE_TOT_SYNTHESIS=true` and ≥3 pillar workers complete.

## Limitations (honest scope)

- Public repo is a **sanitized skeleton** — no live Databricks / vector index in this repository.
- `main_demo.py` prints architecture summary only; full RAG requires env configuration.
- Groundedness and latency metrics are **design targets**, not re-run benchmark numbers in this repo.

## Strengths

- Clear separation: plan → execute → synthesize → optional ToT.
- Feature-flagged ToT avoids overhead on simple queries.
- Self-critique hooks integrated into branch scoring and refinement design.
