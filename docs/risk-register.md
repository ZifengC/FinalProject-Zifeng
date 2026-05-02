# Component 3 Risk Register

This register uses the NIST AI RMF framing of Govern, Map, Measure, and Manage.
Likelihood and severity are scored from 1 low to 5 high. Risk score is
`likelihood x severity`.

| ID | Category | NIST Function | Risk | Likelihood | Severity | Score | Current Controls | Mitigation Plan | Owner |
|---|---|---|---|---:|---:|---:|---|---|---|
| R1 | Bias | Map / Measure | Small curated corpus may underrepresent alternative viewpoints or omit important caveats. | 3 | 3 | 9 | Curated non-sensitive course documents; source metadata returned. | Expand corpus review checklist; add source freshness and coverage review before deployment. | Project owner |
| R2 | Bias | Measure | Personalization or recommender answers may be interpreted as fairness-certified guidance. | 2 | 4 | 8 | Intended-use boundaries in model card. | Add explicit disclaimers for fairness-sensitive topics; require human review for high-impact recommendation use cases. | Project owner |
| R3 | Robustness | Measure / Manage | Retriever may return irrelevant chunks, causing noisy or unsupported generation. | 3 | 4 | 12 | Retrieval metrics; average recall@5 measured at 1.00; source metadata included. | Track retrieval score and source mix; evaluate top-k changes; add abstention when retrieval score is low. | ML owner |
| R4 | Robustness | Measure / Manage | LLM may hallucinate or over-expand beyond retrieved context. | 3 | 4 | 12 | Grounded prompts; manual hallucination review; monitoring of retrieval score. | Add citation checking, answer support scoring, and human review for important outputs. | ML owner |
| R5 | Robustness | Manage | Local Qwen generation latency may exceed acceptable thresholds. | 4 | 3 | 12 | Component 1 latency dashboard; Milestone 6 latency measurements. | Alert on P95 latency; consider smaller model for debug; use caching or narrower retrieval context where appropriate. | Ops owner |
| R6 | Privacy | Govern / Map | User prompts may contain PII, secrets, or confidential data. | 3 | 5 | 15 | No intentional sensitive data in corpus; governance memo notes prompt/cache privacy. | Add input classification, avoid raw prompt logging, define deletion/purge process, restrict access to traces and caches. | Security owner |
| R7 | Privacy | Manage | Agent traces or logs may retain sensitive input/output content. | 3 | 4 | 12 | Coursework traces are local artifacts; no external service required. | Redact traces, define retention windows, and avoid storing raw content in production logs. | Security owner |
| R8 | Compliance | Govern | System may be used outside approved educational scope. | 2 | 5 | 10 | Model card states out-of-scope uses and non-production status. | Add access controls, terms of use, and deployment approval workflow before production use. | Governance owner |
| R9 | Compliance | Govern / Manage | Cached outputs or retained traces may become regulated data if prompts contain personal data. | 3 | 4 | 12 | Milestone 5 governance memo recommends TTL and access controls. | Document retention policy, implement purge procedure, disable caching for sensitive classes. | Governance owner |
| R10 | Robustness | Measure | A/B simulation assumptions may not match real production behavior. | 3 | 3 | 9 | Component 2 labeled as offline synthetic simulation; guardrails included. | Validate with live shadow traffic or controlled pilot before full launch. | ML owner |
| R11 | Security | Map / Manage | Lack of production authentication and rate limiting could allow abuse or resource exhaustion. | 3 | 4 | 12 | Prototype local service only. | Add auth, rate limiting, request quotas, and gateway controls for production. | Ops owner |
| R12 | Data Quality | Measure | Corpus may become stale or inconsistent with intended answers. | 3 | 3 | 9 | Local corpus is version-controlled in project workspace. | Add corpus review dates, freshness checks, and audit events for document updates. | Data owner |

## Highest Priority Risks

The highest priority risk is privacy exposure through prompts, outputs, traces,
or caches. Even if the knowledge base is non-sensitive, user input may introduce
regulated or confidential content. The next most important risks are retrieval
noise, hallucination, and latency because they directly affect answer quality and
operational reliability.

## Risk Acceptance

For coursework demonstration, these risks are acceptable because the system runs
locally, uses non-sensitive documents, and is not exposed to real users. For
production, risks R3, R4, R6, R7, R9, and R11 require mitigation before launch.
