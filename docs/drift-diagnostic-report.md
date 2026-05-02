# Component 4 Drift and Integrity Diagnostic Report

## Summary

The `synthetic` production windows show increasing data quality risk after the stable first window. The strongest drift appears in retrieval quality and input length, with a visible integrity spike in `window_4_integrity_spike`.

- Worst PSI: `4.2123` for `input_length_chars` in `window_4_integrity_spike`.
- Windows with drift or label alerts: 4 of 5.

## Window Results

| Window | Input Length PSI | Response Length PSI | Retrieval Score PSI | Latency PSI | Chunk Count PSI | Label Drift | Empty | Oversized | Low Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| window_1_stable | 0.0171 | 0.0053 | 0.0336 | 0.0036 | 0.0048 | 0.0230 | 3 | 7 | 40 |
| window_2_longer_inputs | 1.5682 | 0.0807 | 0.0869 | 0.0018 | 0.0217 | 0.0390 | 5 | 10 | 101 |
| window_3_low_retrieval | 1.7993 | 0.0178 | 1.2338 | 0.0024 | 0.2095 | 0.1010 | 4 | 9 | 333 |
| window_4_integrity_spike | 4.2123 | 0.1880 | 1.9519 | 0.0099 | 0.3458 | 0.1110 | 20 | 45 | 515 |
| window_5_partial_recovery | 0.6861 | 0.0148 | 0.3485 | 0.0015 | 0.0612 | 0.0540 | 7 | 12 | 162 |

## Impact Analysis

- Input length drift can increase latency and raise prompt-integrity risk.
- Response length drift can indicate changes in answer verbosity, abstention behavior, or grounding quality.
- Retrieval score drift can reduce groundedness and increase hallucination risk.
- Latency drift can indicate longer prompts, slower local generation, or service pressure.
- Label distribution drift indicates that the successful-answer outcome mix is changing.
- Integrity anomalies such as oversized inputs and low retrieval scores should trigger review before relying on model output.

## Recommended Intervention

1. Add alerts for PSI >= 0.10 and page-level review for PSI >= 0.25.
2. Investigate `window_3_low_retrieval` and `window_4_integrity_spike` for corpus mismatch or anomalous prompts.
3. Add an abstention or fallback response when top retrieval score is below 0.25.
4. Keep Component 1 monitoring active and load these Component 4 metrics into Prometheus using `POST /drift/component4/load`.

## Visualizations

- `input_length_drift.svg`
- `response_length_drift.svg`
- `retrieval_score_drift.svg`
- `integrity_anomalies.svg`
