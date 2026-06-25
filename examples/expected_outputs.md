# Expected Output Shapes

Illustrative response formats for reviewers. Figures are synthetic examples for documentation — not live system output.

---

## 1. Simple query (linear ReAct)

**Input**
```
What is the average Class A office vacancy rate in Austin?
```

**Expected response shape**
```text
Austin's Class A office vacancy rate is approximately 15.2% as of Q3 2024.
[Source: Austin Market Report Q3 2024.pdf, Page 8]

Confidence: 0.82
Sources: 4 documents retrieved
```

**Metadata (API / logs)**
```json
{
  "complexity": "simple",
  "plan_steps": ["retrieve", "synthesize"],
  "tot_used": false,
  "iterations": 1
}
```

---

## 2. Complex query (workers + ToT)

**Input**
```
Compare Dallas vs Phoenix for a 50,000 sqft regional headquarters —
consider cost, talent, and risk factors.
```

**Expected response shape**
```markdown
### Recommendation (primary lens: cost)

Dallas offers a lower total occupancy cost for Class A space at this scale...
[Source: Dallas Office Market 2024.pdf, Page 12]
[Source: Southwest CRE Comparison.pdf, Page 5]

---

### Alternative view (lens: talent)

Phoenix shows stronger tech labor pipeline growth...
[Source: Phoenix Workforce Analysis.pdf, Page 3]
```

**Metadata**
```json
{
  "complexity": "complex",
  "plan_steps": ["retrieve", "worker_cost", "worker_talent", "worker_risk", "synthesize"],
  "tot_used": true,
  "tot_selected_branch": "cost",
  "tot_score": 0.85,
  "runner_up": null
}
```

---

## 3. Low-confidence / thin evidence

**Input**
```
What will Austin office rents be in 2030?
```

**Expected response shape**
```text
Available evidence covers historical trends through 2024. No indexed sources
contain 2030 projections. I cannot provide a grounded forecast.

Confidence: 0.42 (below escalation threshold 0.5)
Recommendation: Human analyst review suggested.
```

---

## 4. Out-of-domain

**Input**
```
What's the best stock to buy right now?
```

**Expected response shape**
```text
I specialize in commercial real estate research. I can help with market
analysis, site selection, or location intelligence questions.
```
