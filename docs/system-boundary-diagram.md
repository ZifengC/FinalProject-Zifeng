# Component 5 System Boundary Diagram

## Purpose

This diagram maps the trust boundaries, data flows, and main exposure points of
the Final Project RAG and agent assistant. It is the boundary view used for the
Component 5 AI risk assessment.

## Boundary Diagram

```text
[User]
  |
  | raw prompt / task text
  | risk: prompt injection, PII, abusive traffic
  v
[FastAPI Service: /rag/query, /agent/run]
  |
  | validated request + observable telemetry
  | risk: missing auth, missing rate limits, unsafe logging
  v
[Input Monitoring + Controller]
  |
  | input integrity checks, task routing, retrieval request
  | risk: suspicious input still reaches downstream components
  +----------------------------+
  |                            |
  v                            v
[Retriever / FAISS Index]    [Metrics + Audit Artifacts]
  |                            |
  | retrieved chunks           | counters, histograms, drift gauges,
  | + similarity scores        | reports, audit documents
  | risk: stale corpus,        | risk: sensitive trace retention
  | weak grounding             |
  v                            |
[Prompt Assembly] <------------+
  |
  | user input + retrieved context + prompt template
  | risk: context injection, overlong prompt, sensitive data propagation
  v
[Ollama / qwen2.5:7b]
  |
  | generated answer
  | risk: hallucination, unsafe output, latency spikes
  v
[Response Returned To User]
```

## Trust Boundaries

| Boundary Crossing | Data Exposed | Primary Risk | Current Controls | Recommended Controls |
|---|---|---|---|---|
| User -> FastAPI service | Raw prompt or task text | Prompt injection, PII submission, abuse | Input metrics, anomaly counting, local-only coursework deployment | Add authentication, rate limiting, prompt classification, and request rejection for unsafe inputs |
| Service -> Retriever | User query and retrieval parameters | Query mismatch, coverage gaps, stale corpus | Retrieval latency and top-score monitoring; Component 4 drift analysis | Add source freshness checks, corpus review cadence, and low-score fallback behavior |
| Retriever -> Prompt assembly | Retrieved chunks and metadata | Context injection, irrelevant evidence, long prompt growth | Grounded prompt structure, source metadata returned | Add minimum retrieval-score threshold and document allowlist review |
| Prompt assembly -> LLM | Full combined prompt | Third-party-style trust risk even in local serving, sensitive data propagation, overlong prompts | Local Ollama deployment, observable latency metrics | Add prompt redaction, max prompt size policy, and sensitive-content screening |
| LLM -> User | Generated answer | Hallucination, unsafe or unsupported advice | Grounded retrieval workflow, model card limitations, manual review only in coursework context | Add abstention templates, citation checks, and human review for high-impact use cases |
| Service -> Metrics / audit artifacts | Request statistics, traces, drift outputs | Sensitive content retention in logs or traces | Existing metrics are mostly aggregate; governance docs mention retention concerns | Redact raw content, define retention TTL, and restrict artifact access |

## Boundary-Driven Risk Notes

- The highest-risk boundary is `User -> FastAPI service` because harmful input,
  PII, and misuse originate there.
- The most important grounding boundary is `Retriever -> Prompt assembly`
  because weak retrieval quality can silently turn into hallucinated output.
- The most important governance boundary is `Service -> Metrics / audit
  artifacts` because even a non-sensitive knowledge base does not prevent user
  prompts from containing regulated content.

## Operational Signals Mapped To Boundaries

| Signal | Boundary | Why It Matters |
|---|---|---|
| `finalproject_input_integrity_anomalies_total` | User -> Service | Flags suspicious or malformed inputs before they are treated as normal traffic |
| `finalproject_rag_top_retrieval_score` | Retriever -> Prompt assembly | Low scores indicate weak evidence and higher hallucination risk |
| `finalproject_drift_psi` and Component 4 drift gauges | User -> Service, Retriever -> Prompt assembly | Show changing query mix and retrieval behavior over time |
| `finalproject_request_latency_seconds` and generation latency | Prompt assembly -> LLM | Surface prompt growth, model slowness, or local resource pressure |
| Component 4 integrity anomalies | User -> Service, Retriever -> Prompt assembly | Highlight empty, oversized, and low-score windows that require intervention |
