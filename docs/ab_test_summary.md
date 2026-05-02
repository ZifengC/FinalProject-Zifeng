# Component 2 A/B Test Summary

## Experiment Design

- Experiment: `rag_topk_context_ab_test`
- Control: A: baseline RAG top_k=5
- Treatment: B: narrower RAG top_k=3
- Simulated users: 20,000
- Traffic split: 50% control / 50% treatment
- Required sample size per variant: 2,340

## Variant Outcomes

| Metric | Control A | Treatment B |
|---|---:|---:|
| n | 9,909 | 10,091 |
| Successful answer rate | 0.720 | 0.761 |
| Average latency ms | 2913.99 | 2402.17 |
| P95 latency ms | 3973.48 | 3323.69 |
| Groundedness score | 0.780 | 0.820 |
| Recall proxy | 0.994 | 0.958 |
| Error rate | 0.010 | 0.011 |

## Primary Statistical Test

- Metric: `successful_answer_rate`
- Absolute lift: 0.0411
- Relative lift: 5.71%
- p-value: 0.000000
- 95% CI: [0.0290, 0.0532]

## Guardrails

| Metric | Passed | Reason |
|---|---:|---|
| recall_proxy | True | relative degradation=3.57% |
| error_rate | True | absolute increase=0.0010 |
| p95_latency_ms | True | relative change=-16.35% |

## Recommendation

`SHIP_TREATMENT_GRADUALLY`

If this were an online deployment, the treatment should be rolled out only after production monitoring confirms that recall, error rate, and latency guardrails continue to hold under real traffic.
