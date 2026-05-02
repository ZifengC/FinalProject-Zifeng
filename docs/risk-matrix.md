# Component 5 AI Risk Assessment

## Scope

This assessment converts the existing governance packet, monitoring evidence,
and drift diagnostics into a system-level launch decision for the Final Project
RAG and agent assistant.

Supporting artifacts:

- `docs/risk-register.md`
- `docs/model-card.md`
- `docs/dashboard-interpretation.md`
- `docs/drift-diagnostic-report.md`
- `src/monitoring/service.py`

## Risk Matrix

Likelihood and severity are scored from `1` low to `5` high. Score is
`likelihood x severity`.

| Likelihood \ Severity | 1 Negligible | 2 Minor | 3 Moderate | 4 Major | 5 Critical |
|---|---:|---:|---:|---:|---:|
| 5 Almost certain | 5 | 10 | 15 | 20 | 25 |
| 4 Likely | 4 | 8 | 12 | 16 | 20 |
| 3 Possible | 3 | 6 | 9 | 12 | 15 |
| 2 Unlikely | 2 | 4 | 6 | 8 | 10 |
| 1 Rare | 1 | 2 | 3 | 4 | 5 |

Risk level interpretation:

- `1-4`: LOW
- `5-9`: MEDIUM
- `10-15`: HIGH
- `16-25`: CRITICAL

## Priority Risks

| ID | Risk | Category | L | S | Inherent Score | Current Controls | Residual L | Residual S | Residual Score | Treatment | Owner | Trigger |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---|---|---|
| R006 | Prompt injection or malicious instructions bypass intended workflow controls | Security | 3 | 5 | 15 HIGH | Input anomaly monitoring, local-only prototype scope, explicit out-of-scope statement | 2 | 4 | 8 MEDIUM | Mitigate | ML platform owner | Prompt-injection marker spike, red-team finding, suspicious input pattern |
| R007 | Knowledge base staleness or weak retrieval causes unsupported answers | Data Quality | 4 | 4 | 16 CRITICAL | Retrieval score monitoring, Component 4 drift analysis, source metadata returned | 3 | 3 | 9 MEDIUM | Mitigate | Data / ML owner | Retrieval score PSI increase, low-score windows, stale corpus review |
| R008 | User prompts, traces, or caches contain PII or confidential content | Privacy | 3 | 5 | 15 HIGH | Coursework local deployment, no intentional sensitive corpus, governance warnings | 2 | 4 | 8 MEDIUM | Mitigate | Security owner | Sensitive prompt report, logging review failure, retention-policy gap |
| R009 | Hallucinated answer is returned when grounding is weak but generation still succeeds | Safety / Robustness | 3 | 4 | 12 HIGH | Grounded RAG pattern, source metadata, retrieval score telemetry, documented limitations | 2 | 4 | 8 MEDIUM | Mitigate | ML owner | Top retrieval score below threshold, low-score drift window, user escalation |
| R010 | Missing authentication and rate limiting allows abuse or resource exhaustion | Security / Reliability | 3 | 4 | 12 HIGH | Local prototype only, observable throughput and latency metrics | 3 | 3 | 9 MEDIUM | Mitigate | Ops owner | Request spike, latency degradation, unauthorized consumer onboarding |
| R011 | System is reused for high-impact decisions outside coursework scope | Compliance / Accountability | 2 | 5 | 10 HIGH | System card, governance packet, model limitations, out-of-scope statements | 2 | 4 | 8 MEDIUM | Avoid | Governance owner | New deployment request, external user onboarding, policy review |
| R012 | Logs and audit artifacts retain more raw content than intended | Privacy / Compliance | 3 | 4 | 12 HIGH | Aggregate metrics dominate current monitoring setup, local artifacts only | 2 | 3 | 6 MEDIUM | Mitigate | Security / governance owner | Artifact review, trace expansion, retention review |

## LLM/RAG-Specific Risks Required By Module 8

The project includes more than the minimum two LLM/RAG-specific risks required
by the slides:

- `R006` Prompt injection
- `R007` Knowledge base staleness / retrieval degradation
- `R009` Hallucination under weak grounding

These risks are system-specific and tied to observable signals already present
in Components 1 and 4.

## Evidence-Based Assessment

### Retrieval and grounding risk

Component 4 shows strong retrieval instability in real RAG windows:

- Worst retrieval-score PSI: `26.3013`
- `window_3_low_retrieval` recorded `8` low-score observations
- `window_4_integrity_spike` recorded `6` low-score observations

This is enough evidence to classify unsupported-answer risk as operationally
important even in a prototype.

### Input and integrity risk

Component 1 monitoring recorded prompt-injection-marker anomalies for both
`/rag/query` and `/agent/run`. Component 4 also found empty and oversized
inputs in `window_4_integrity_spike`. These findings support explicit treatment
for malicious or malformed input rather than treating the issue as hypothetical.

### Privacy and retention risk

The project is local and coursework-scoped, which lowers exposure, but the
system still accepts free-form user prompts. That means prompt content can
introduce secrets or personal data even when the curated corpus is safe. This
keeps privacy risk in the `HIGH` inherent range until retention and redaction
controls are formalized.

## Treatment Summary

| Treatment | Risks |
|---|---|
| Mitigate | R006, R007, R008, R009, R010, R012 |
| Avoid | R011 |
| Accept | None for production launch |
| Transfer | None used in this coursework prototype |

## Required Controls Before Any Production Launch

1. Add authentication, request quotas, and rate limiting in front of the API.
2. Reject or quarantine suspicious prompts using input validation and prompt screening.
3. Add abstention or fallback behavior when top retrieval score is below `0.25`.
4. Define retention, purge, and redaction rules for traces, caches, and logs.
5. Add corpus freshness review, knowledge-base update logging, and refresh triggers.
6. Require human review for policy-sensitive or high-impact usage scenarios.

## Deployment Gate

Decision:
`PROCEED WITH CONDITIONS` for local coursework submission.

Decision for real production deployment:
`BLOCK LAUNCH` until the required controls above are implemented and assigned to
named owners.

Rationale:

- Monitoring and drift instrumentation already provide useful observable signals.
- The project has documented limitations and governance artifacts.
- The system still lacks several baseline production controls: auth, rate
  limiting, prompt screening, formal retention policy, and grounded fallback
  behavior.
