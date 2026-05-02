# Component 3 Model Card

## Model/System Details

| Field | Value |
|---|---|
| System name | Final Project RAG/Agent Assistant |
| Version | `finalproject-rag-agent-v1` |
| Primary capability | Grounded question answering and lightweight agentic task execution over a small curated knowledge base |
| Base LLM | `qwen2.5:7b` served locally through Ollama |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Retriever | FAISS `IndexFlatIP` over normalized embeddings |
| Service interface | FastAPI endpoints: `POST /rag/query`, `POST /agent/run`, `GET /health`, `GET /metrics`, `GET /stats` |
| Monitoring stack | Prometheus and Grafana |
| Owner | IDS568 final project student team |
| Status | Coursework prototype, not production-approved |

This is a system card for a Retrieval-Augmented Generation workflow rather than
a traditional supervised model card. The deployed behavior comes from the
combination of the document collection, chunking settings, embedding model,
vector search, prompt construction, local LLM generation, and optional agent
tool-routing logic.

## Intended Use

The intended use is to answer educational questions about RAG, chunking,
embeddings, vector databases, grounding, local LLM serving, LLM memory, agentic
controllers, recommender systems, and personalization bias using the local
Markdown knowledge base in `src/monitoring/documents`.

Appropriate uses:

- Demonstration of an observable local LLM/RAG service.
- Grounded Q&A over the provided non-sensitive documents.
- Local experimentation with retrieval metrics, monitoring, and governance.
- Agent trace inspection for simple summarization, extraction, and reasoning
  tasks grounded in the same document collection.

Out-of-scope uses:

- Medical, legal, financial, employment, or safety-critical advice.
- Production user support without additional evaluation and controls.
- Processing confidential, regulated, or personal information.
- Open-domain answering where the answer is not covered by the retrieved
  knowledge base.
- Autonomous tool execution against external systems.

## Training Data Description

The project does not train the base LLM. `qwen2.5:7b` is used as an existing
open-weight instruct model through Ollama. The project also does not train the
embedding model; it uses `all-MiniLM-L6-v2` as a pretrained sentence embedding
model.

The system-specific data is the local retrieval corpus:

- Location: `src/monitoring/documents`
- Format: Markdown
- Count: 10 documents
- Topics: RAG overview, chunking, embeddings, vector databases, grounding,
  local LLM serving, LLM memory, LLM agents, recommender systems, and
  personalization bias.
- Sensitivity: no internal, proprietary, or personal data is intentionally
  included.

The corpus is small and curated for focused evaluation, so it is not representative of
a broad production knowledge base.

## Evaluation Data

The evaluation set contains 10 hand-written questions aligned to
the 10 local documents. Each question includes expected relevant source files.
The evaluation measures retrieval quality, generation groundedness, and latency.

Component 2 adds an offline simulated A/B experiment comparing:

- Control A: RAG `top_k=5`
- Treatment B: RAG `top_k=3`

The A/B simulation uses synthetic outcomes and does not represent live user
traffic.

## Performance Metrics

RAG evaluation:

| Metric | Result |
|---|---:|
| Average precision@5 | 0.22 |
| Average recall@5 | 1.00 |
| Average retrieval latency | 15.26 ms |
| Average generation latency | 2898.63 ms |
| Average total query latency | 2914.23 ms |

Observed generation quality:

- No severe hallucination was observed in the 10-question evaluation.
- Most answers were grounded in the retrieved context.
- One retrieval ranking issue was observed for a vector database question.
- One answer showed minor phrasing expansion beyond the exact source wording.

Agent evaluation:

| Metric | Result |
|---|---:|
| Evaluation tasks | 10 |
| Average agent task latency | 14649.54 ms |
| Fastest task | 4500.66 ms |
| Slowest task | 25829.36 ms |

Component 2 offline A/B result:

| Metric | Control A `top_k=5` | Treatment B `top_k=3` |
|---|---:|---:|
| Successful answer rate | 0.720 | 0.761 |
| Average latency ms | 2913.99 | 2402.17 |
| P95 latency ms | 3973.48 | 3323.69 |
| Groundedness score | 0.780 | 0.820 |
| Recall proxy | 0.994 | 0.958 |
| Error rate | 0.010 | 0.011 |

The A/B simulation recommended `SHIP_TREATMENT_GRADUALLY`, but this is an
offline simulated recommendation. A production launch would still require live
monitoring and a rollback plan.

## Assumptions

- The local documents are the authoritative source for answer generation.
- The user asks questions that are within the knowledge base scope.
- The service should prefer grounded answers over broad open-domain responses.
- The same embedding model is used for document chunks and queries.
- The local Ollama runtime has enough memory to serve `qwen2.5:7b` reliably.
- Prometheus/Grafana monitoring is available when the service is evaluated as a
  running API.

## Limitations

- The document corpus is very small, so precision@5 is low by construction.
- The evaluation set is small and manually authored.
- Groundedness is partly assessed with lightweight proxies and manual review,
  not a fully validated human evaluation process.
- The LLM can still over-expand, omit caveats, or blend retrieved context.
- The system does not include a moderation layer.
- The agent controller is rule-based and suitable for observability, not for
  broad autonomous planning.
- The service is a prototype and lacks production authentication,
  rate limiting, tenant isolation, and incident response automation.

## Failure Modes

- Retrieval misses the relevant source or ranks it too low.
- Retrieval returns partially related context that adds noise.
- Generation includes unsupported details despite grounded prompting.
- Local model generation latency becomes high under repeated requests.
- User input includes sensitive data that appears in outputs or traces.
- Agent tool routing selects a less appropriate intermediate tool.
- Monitoring signals are ignored or alert thresholds are not operationalized.

## Ethical Risks and Considerations

- Bias: the corpus includes recommender and personalization topics, but the
  system should not be treated as a fairness-certified recommender advisor.
- Privacy: prompts, generated answers, traces, and cached values may contain
  sensitive user input if users provide it.
- Robustness: the small corpus makes the system brittle outside its intended
  domain.
- Transparency: citations and retrieved source metadata are required so users
  can inspect evidence.
- Misuse: users may try to use the assistant for advice beyond course material
  or ask it to produce unsupported claims.

## Monitoring and Governance Controls

Implemented controls:

- FastAPI health and stats endpoints.
- Prometheus metrics endpoint.
- Grafana dashboard for throughput, errors, latency, input anomalies, retrieval
  quality, agent depth, and PSI-style input-length drift.
- Structured agent traces in the service workflow.
- Offline A/B simulation with guardrail metrics.

Recommended production controls:

- Authentication and request quotas.
- Prompt/content screening for sensitive or harmful inputs.
- Clear retention policy for prompts, outputs, traces, and caches.
- Human review workflow for high-impact outputs.
- Alert thresholds for latency, error rate, retrieval score degradation, and
  drift.
- Rollback procedure for retrieval configuration changes.

## Approval Status

This system is approved only for local prototype use. It is not approved
for production, regulated, or user-facing deployment without additional
security, privacy, monitoring, and human evaluation controls.
