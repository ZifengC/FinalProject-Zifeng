# Component 2 Experiment Specification

## Objective

This offline A/B experiment evaluates whether a narrower RAG retrieval context
improves user-facing answer quality and latency without violating retrieval,
error, or latency guardrails.

## Variants

| Variant | Configuration | Role |
|---|---|---|
| A | Baseline RAG with `top_k=5` | Control |
| B | Narrower RAG with `top_k=3` | Treatment |

Variant A reflects the current baseline RAG configuration in the service.
Variant B tests whether reducing retrieved context lowers
noise and response time while keeping enough evidence for grounded answers.

## Hypothesis

Null hypothesis:

`H0`: Treatment B has the same successful answer rate as Control A.

Alternative hypothesis:

`H1`: Treatment B has a higher successful answer rate than Control A while
passing operational guardrails.

## Metrics

Primary success metric:

- `successful_answer_rate`: binary outcome representing whether the user would
  accept the generated RAG answer as useful and grounded.

Secondary metrics:

- `latency_ms`: end-to-end answer latency.
- `groundedness_score`: synthetic quality proxy for how well the answer is
  supported by retrieved evidence.
- `business_value`: synthetic engagement / usefulness KPI.

Guardrail metrics:

- `recall_proxy`: treatment cannot degrade by more than 5% relative to control.
- `error_rate`: treatment cannot increase absolute error rate by more than 0.005.
- `p95_latency_ms`: treatment cannot be slower than control at P95.

## Randomization

Users are assigned with deterministic hashing:

`md5(user_id + experiment_name) -> bucket -> A or B`

This creates a reproducible 50/50 split and ensures the same synthetic user
always receives the same variant for this experiment.

## Sample Size

The simulation uses:

- baseline success rate: `0.72`
- minimum detectable effect: `5%` relative lift
- alpha: `0.05`
- power: `0.80`

The required sample size is `2,340` users per variant. The actual simulation
uses `20,000` users total, producing `9,909` control observations and `10,091`
treatment observations, which exceeds the requirement.

## Statistical Tests

- Primary binary metric: two-proportion z-test with a 95% confidence interval.
- Continuous metrics: Welch-style two-sample test with a normal approximation.
- Decision threshold: `p < 0.05` and 95% CI lower bound above zero for the
  primary metric.

## Decision Rule

Ship Treatment B gradually only if:

1. `successful_answer_rate` improves significantly.
2. The 95% confidence interval for absolute lift is fully above zero.
3. Recall, error-rate, and P95-latency guardrails all pass.

Otherwise, keep Control A or continue collecting data.
