# Component 3 Lineage Diagram

## System Lineage

```text
Curated Markdown documents
  src/monitoring/documents/*.md
        |
        v
Document loading
  src/monitoring/rag_pipeline.py
        |
        v
Chunking
  chunk_tokens=320
  overlap_tokens=60
        |
        v
Embedding
  sentence-transformers/all-MiniLM-L6-v2
        |
        v
Vector index
  FAISS IndexFlatIP with normalized vectors
        |
        v
Retrieval
  query embedding -> top-k chunks -> source metadata
        |
        v
Prompt construction
  user query + retrieved context + grounded-answer instructions
        |
        v
Generation
  qwen2.5:7b served locally through Ollama
        |
        v
FastAPI service
  POST /rag/query
  POST /agent/run
        |
        v
Monitoring
  /metrics -> Prometheus -> Grafana dashboard
  /stats -> service counters
        |
        v
Governance artifacts
  model card, risk register, audit trail, A/B recommendation
```

## Agentic Workflow Lineage

```text
User task
   |
   v
Agent controller
   |
   v
Retriever tool
   |
   v
Rule-based tool selection
  summarizer | extractor | reasoning
   |
   v
Final answer synthesis
   |
   v
Trace logging
  tool path, inputs, outputs, source metadata, latency
```

## Lifecycle Mapping

| Stage | Artifact | Governance Relevance |
|---|---|---|
| Data | `src/monitoring/documents` | Defines knowledge scope and data sensitivity boundary |
| Training | No local LLM training; pretrained Qwen and MiniLM are used | Must document inherited model limitations |
| Indexing | `src/monitoring/rag_pipeline.py` chunking, embeddings, FAISS index | Determines retrieval quality and context scope |
| Evaluation | Milestone 6 RAG evaluation and agent traces | Measures retrieval, groundedness, latency, and failure modes |
| Deployment | `src/monitoring/service.py` FastAPI app | Exposes RAG and agent endpoints |
| Monitoring | Prometheus/Grafana Component 1 dashboard | Tracks latency, errors, input integrity, drift proxy, retrieval quality |
| Experimentation | Component 2 A/B simulation | Supports configuration recommendation with statistical reasoning |
| Governance | Component 3 model card, risk register, audit trail | Documents intended use, limitations, risks, and controls |

## Ownership and Change Boundaries

- Corpus changes require review because they alter the system's knowledge base.
- Chunking, embedding, or `top_k` changes require retrieval evaluation and
  monitoring review.
- Base LLM changes require model card updates and latency/quality comparison.
- Endpoint or trace logging changes require privacy and retention review.
- Monitoring threshold changes require an audit event.
