# Component 2 Recommendation Memo

## Decision

Recommendation: `SHIP_TREATMENT_GRADUALLY`

The simulated A/B experiment supports gradually rolling out Treatment B, the
RAG configuration with `top_k=3`, because it improves the primary success metric
and passes all defined guardrails.

## Result Summary

| Metric | Control A `top_k=5` | Treatment B `top_k=3` |
|---|---:|---:|
| Sample size | 9,909 | 10,091 |
| Successful answer rate | 0.720 | 0.761 |
| Average latency ms | 2913.99 | 2402.17 |
| P95 latency ms | 3973.48 | 3323.69 |
| Groundedness score | 0.780 | 0.820 |
| Recall proxy | 0.994 | 0.958 |
| Error rate | 0.010 | 0.011 |

The treatment improved successful answer rate by `0.0411` absolute points,
equivalent to a `5.71%` relative lift. The two-proportion z-test produced a
p-value of `3.20e-11`, and the 95% confidence interval for absolute lift was
`[0.0290, 0.0532]`. Because the full interval is above zero, the simulated
result is statistically significant and directionally positive.

## Guardrail Review

All guardrails passed:

| Guardrail | Result |
|---|---|
| Recall proxy | Passed. Relative degradation was `3.57%`, below the `5%` limit. |
| Error rate | Passed. Absolute increase was `0.0010`, below the `0.005` limit. |
| P95 latency | Passed. Treatment improved P95 latency by `16.35%`. |

The recall proxy decreased as expected because `top_k=3` retrieves fewer
chunks, but the degradation stayed inside the launch threshold. The latency
improvement is material and supports the narrower-context treatment.

## Recommendation

Ship Treatment B gradually rather than switching all traffic immediately. In a
real deployment, the rollout should start with a small production traffic share
and continue monitoring recall, answer quality, error rate, and P95 latency.
If production recall falls below the guardrail or error rate rises beyond the
threshold, rollback to Control A.

The final Component 2 artifacts are:

- `src/ab_test/ab_test_simulation.py`
- `docs/experiment-specification.md`
- `docs/recommendation-memo.md`
- `docs/ab_test_results.json`
- `docs/ab_test_summary.md`
