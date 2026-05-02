# CTO Memo: Component 5 AI Risk Assessment

## To

Project stakeholders and course evaluators

## From

CTO reviewer, Final Project risk assessment

## Subject

Launch decision for the Final Project RAG and agent assistant

## Executive Decision

The system is acceptable for `local coursework demonstration` but is `not
approved for production deployment` in its current form.

Formal gate decision:

- Coursework prototype: `PROCEED WITH CONDITIONS`
- Real production launch: `BLOCK LAUNCH`

## What We Reviewed

The assessment reviewed the deployed FastAPI backbone, the local RAG pipeline,
the agent workflow, Component 1 monitoring evidence, Component 3 governance
artifacts, and Component 4 drift diagnostics.

The current system already has meaningful strengths:

- Observable monitoring for latency, errors, retrieval score, integrity
  anomalies, and drift
- A documented system card and governance packet
- A risk register with named owners and mitigation plans
- Evidence that drift and low-retrieval conditions can be detected

## Why Production Launch Is Blocked

The largest concern is not infrastructure failure. It is system-level AI risk
at the trust boundaries where user input enters the service, retrieval context
is assembled, and model output is returned.

The key blockers are:

1. The API does not yet enforce authentication or rate limiting.
2. Suspicious prompts are monitored but not actively blocked or quarantined.
3. Low retrieval quality can be observed, but weak-grounding fallback behavior
   is not yet enforced.
4. Prompt, trace, and cache retention controls are documented conceptually but
   not operationalized.
5. The system is clearly not approved for high-impact or regulated use, yet no
   technical gate currently enforces that boundary.

## Highest-Priority Risks

- `Prompt injection`: monitored but not actively prevented
- `Knowledge base staleness / retrieval degradation`: evidenced by Component 4
  drift windows and low-score spikes
- `PII or confidential data in prompts and artifacts`: possible even with a
  non-sensitive corpus
- `Hallucinated unsupported answer`: still possible when retrieval quality is low

These risks are material because the monitored evidence already shows integrity
anomalies and retrieval-score degradation, so they are not purely theoretical.

## Conditions To Move Forward

Before any real-user deployment, I would require the following controls:

1. API authentication, quotas, and rate limiting
2. Prompt screening and rejection rules for malicious or sensitive inputs
3. Abstention or fallback response when retrieval score is below threshold
4. Trace/log redaction plus a written retention and purge procedure
5. Knowledge-base freshness review and documented update cadence
6. Human review requirement for high-impact use cases

## Final Recommendation

Ship Component 5 as a well-documented risk package for the final project. Do
not represent the system as production-ready. The correct executive posture is
that observability and governance foundations are in place, but several
mandatory operational controls remain incomplete.
