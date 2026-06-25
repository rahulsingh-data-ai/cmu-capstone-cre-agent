# Sample Queries and Expected Behavior

## Simple Query (Linear ReAct)

**Query**: "What is the average Class A office vacancy rate in Austin?"

**Expected Flow**:
1. Planner: 1 step (RETRIEVE)
2. Vector search returns 4-6 relevant chunks
3. Synthesis: direct answer with citation

**Expected Output**:
> Austin's Class A office vacancy rate is approximately 15.2% as of Q3 2024.
> [Source: "Austin Market Report Q3 2024.pdf", Page 8]

---

## Complex Query (Multi-Worker + ToT)

**Query**: "Compare Dallas vs. Phoenix for a 50,000 sqft regional headquarters — consider cost, talent, and risk factors."

**Expected Flow**:
1. Planner: 5 steps (RETRIEVE, WORKER_COST, WORKER_TALENT, WORKER_RISK, SYNTHESIZE)
2. Vector search retrieves 12+ sources across both markets
3. Cost Worker: analyzes lease rates, opex, tax incentives
4. Talent Worker: labor pool, wages, commute, education
5. Risk Worker: market volatility, climate, regulatory
6. **ToT Synthesis** (3 branches in parallel):
   - Cost lens → recommendation based on financial efficiency
   - Talent lens → recommendation based on workforce access
   - Risk lens → recommendation based on downside protection
7. Self-critique scores each branch
8. Winner selected (or tied response with both perspectives)

**Expected Output**:
> ### Recommendation (primary lens: cost)
>
> Dallas offers a 22% cost advantage for a 50,000 sqft Class A lease...
> [Source: "Dallas Office Market 2024.pdf", Page 12]
> [Source: "Southwest CRE Comparison.pdf", Page 5]
>
> ---
>
> ### Alternative view (lens: talent)
>
> Phoenix's tech talent pipeline has grown 18% year-over-year...
> [Source: "Phoenix Workforce Analysis.pdf", Page 3]

---

## Research Query (STORM Delegation)

**Query**: "Produce a comprehensive market intelligence report on the Southeast industrial logistics corridor."

**Expected Flow**:
1. Complexity: RESEARCH
2. Delegated to STORM research mode
3. Multiple retrieval rounds with iterative refinement
4. Structured report with sections, charts, and citations

---

## Edge Cases

### Low-Confidence Fallback
**Query**: "What will Austin office rents be in 2030?"

- Retrieval finds only historical data, no forecasts
- Self-critique scores < 0.5
- Response includes explicit gap warning:
  > "Available evidence covers historical trends through 2024. No indexed sources contain 2030 projections. Based on current trajectory..."

### Out-of-Domain Rejection
**Query**: "What's the best stock to buy right now?"

- Domain scope filter detects non-CRE query
- Redirects: "I specialize in commercial real estate research. I can help with market analysis, site selection, or location intelligence questions."
