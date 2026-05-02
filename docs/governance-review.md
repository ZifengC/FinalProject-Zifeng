# Governance Review

## Scope

This governance review covers the complete Final Project RAG and agent system.
It focuses on the full operational boundary rather than only the base model.

System in scope:

- retriever over local Markdown documents
- prompt assembly and grounded generation
- local Ollama-served `qwen2.5:7b`
- agent controller with retrieval, summarization, extraction, and reasoning steps
- monitoring, audit, and drift artifacts

## Data Security

- The curated knowledge base is intentionally non-sensitive educational
  reference content.
- The primary security concern is free-form user input, which may contain
  secrets, personal data, or confidential text.
- Monitoring artifacts are mostly aggregate, but trace expansion or raw logging
  could still create retention risk.

Current controls:

- local-only prototype deployment
- no intentional sensitive data in the corpus
- documented out-of-scope and sensitive-data boundaries

Recommended controls:

- redact prompts and outputs before long-term storage
- define retention TTL and purge procedures
- add authentication and access control before any real-user deployment

## Retrieval Risks

### Exposure and contamination

- Retrieved chunks are injected directly into the prompt context.
- If the corpus is stale, incomplete, or contaminated, that bad context can
  propagate into the answer.

### Stale knowledge

- Component 4 already shows severe retrieval-score drift and low-score windows.
- This makes stale or mismatched knowledge an operational risk rather than a
  hypothetical one.

Current controls:

- retrieval score monitoring
- Component 4 drift and anomaly analysis
- source metadata returned with retrieved chunks

Recommended controls:

- document freshness review
- knowledge-base update logging
- abstention or fallback when top retrieval score drops below threshold

## Hallucination Risk Points

Hallucination risk appears at three points:

1. Retrieval misses the right evidence.
2. Retrieval returns weakly related evidence.
3. Generation expands beyond the retrieved context even when some evidence is present.

Current controls:

- grounded prompt template
- source citation behavior
- retrieval-score observability
- documented intended-use boundaries

Recommended controls:

- minimum retrieval-score threshold
- citation validation or support scoring
- human review for high-impact outputs

## Tool-Misuse Pathways

This project uses a lightweight agent controller rather than external write
tools, so the main tool-misuse risks are:

- routing to an inappropriate intermediate tool
- giving a high-confidence final answer after weak retrieval
- exposing sensitive input content in traces or step outputs

Current controls:

- transparent rule-based tool routing
- observable tool-step depth and latency
- local-only deployment boundary

Recommended controls:

- add refusal or fallback behavior for unsafe or unsupported tasks
- restrict trace retention
- require human approval before expanding to external tools

## Compliance Concerns

- prompts may contain PII
- outputs may be misused outside the intended low-risk educational scope
- caches or traces may become regulated artifacts if personal data enters the system

Current controls:

- model and governance documentation clearly state out-of-scope uses
- system is not approved for production deployment

Recommended controls:

- input screening for regulated content
- explicit retention and deletion policy
- documented approval workflow for any deployment scope change

## Summary

The system is acceptable as a local prototype because the exposure is limited
and the governance boundaries are documented. It is not ready for
production deployment without authentication, prompt screening, retrieval
fallback behavior, and formal retention controls.
