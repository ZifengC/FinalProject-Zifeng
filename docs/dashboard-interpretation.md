# Production Monitoring Interpretation

## Scope

This document describes the monitoring approach for the FinalProject RAG/agent
API and interprets the observed system behavior from the saved dashboard run.
The monitored service exposes:

- `POST /rag/query`
- `POST /agent/run`
- `GET /metrics`
- `GET /stats`

Related artifacts:

- `docs/dashboard-screenshot.png`
- `visualizations/dashboard-screenshot.png`
- `dashboards/finalproject-dashboard.json`

## Design Choice

Prometheus and Grafana were selected because they are open-source, easy to run
locally with Docker Compose, and directly support the metric types needed for a
production-style ML/LLM service: counters, histograms, and gauges.

The API exposes Prometheus-format metrics from `/metrics`. Prometheus scrapes
that endpoint every 5 seconds using `dashboards/prometheus.yml`, and Grafana
loads `dashboards/finalproject-dashboard.json`.

## Metrics Instrumented

The service records:

- Throughput: `finalproject_requests_total`
- Errors: `finalproject_errors_total`
- Endpoint latency: `finalproject_request_latency_seconds`
- Approximate TTFT: `finalproject_llm_ttft_approx_seconds`
- Estimated token volume: `finalproject_llm_tokens_total`
- Input size: `finalproject_input_length_chars`
- Input integrity anomalies:
  `finalproject_input_integrity_anomalies_total`
- RAG retrieval latency:
  `finalproject_rag_retrieval_latency_seconds`
- RAG generation latency:
  `finalproject_rag_generation_latency_seconds`
- Retrieved chunk count: `finalproject_rag_retrieved_chunks`
- Latest top retrieval score: `finalproject_rag_top_retrieval_score`
- Agent orchestration depth: `finalproject_agent_tool_steps`
- Agent latency: `finalproject_agent_latency_seconds`
- Input-length PSI drift gauge: `finalproject_drift_psi`
- Cache placeholder counter: `finalproject_cache_events_total`

Input integrity anomalies, top retrieval score, and input-length PSI are the
primary model and data-health signals on the dashboard. The PSI gauge can also
receive additional drift-detector outputs without redesigning the monitoring
layout.

Because the Ollama call is not streamed, total generation latency is used as
the closest observable TTFT proxy. Token volume is also estimated from prompt
and response text length rather than returned directly by the model runtime.

## Observed Run

The saved `/stats` snapshot shows:

| Metric | Value |
|---|---:|
| RAG queries | 26 |
| Failed RAG queries | 0 |
| Average RAG latency | 1615.74 ms |
| Agent runs | 14 |
| Failed agent runs | 0 |
| Average agent latency | 5632.82 ms |

The Prometheus request-total query confirms:

| Endpoint | Successful Requests |
|---|---:|
| `/rag/query` | 26 |
| `/agent/run` | 14 |

No failed requests were recorded in the saved counters.

## Diagnostic Interpretation

The dashboard shows that the API handled both RAG and agent traffic successfully.
The main performance bottleneck is generation and agent orchestration, not
retrieval. In the saved Prometheus snapshot, RAG retrieval latency totaled
0.28866 seconds across 26 RAG calls, or about 11 ms per call. RAG generation
latency totaled 40.6658 seconds across 13 generation-enabled calls, or about
3.13 seconds per generated answer. The difference between 26 retrieval calls
and 13 generation calls reflects the low-cost simulated traffic path, where some
RAG requests exercised retrieval while skipping local LLM generation. This still
shows the expected production pattern: FAISS retrieval over a small local
document set is much faster than local LLM generation through Ollama. The
approximate TTFT metric should therefore be interpreted as a generation-latency
proxy, not as a true streamed first-token measurement.

Agent runs are slower because each task executes a multi-step workflow:

```text
retriever -> reasoning/extractor/summarizer -> final_answer
```

The saved agent metrics show 42 tool steps across 14 agent runs, which means
each run used 3 tool steps. This matches the intended controller policy and
confirms that the endpoint is exercising the agent workflow, not only direct
RAG retrieval.

Input integrity monitoring also worked. The saved metrics include
prompt-injection-marker anomaly counts of 2 for `/rag/query` and 2 for
`/agent/run`.
Those events came from simulated traffic and demonstrate that the monitoring
layer can surface suspicious input patterns separately from ordinary request
failures.

The latest top retrieval score in the saved metrics was approximately 0.398.
This is a useful grounding-risk signal: when the top score is low, the system
may still generate an answer, but the retrieved evidence may be weakly related
to the user task. In production, this should trigger either a fallback response,
additional retrieval, or manual review depending on the use case.

The PSI panel is active in the running service. The service updates
`finalproject_drift_psi{feature="input_length_chars"}` on each request by
comparing the live input-length distribution with a fixed reference
distribution. The saved metric value is approximately 7.385, which is high
because the simulated traffic intentionally included a small, non-representative
mix of short prompts and anomalous inputs. The same metric family can be
extended with additional features such as retrieval score or source mix.

## Bottlenecks And Risks

The primary bottleneck is local model generation. RAG retrieval is fast, while
generation and agent synthesis dominate latency. The main operational risk is
that agent requests can take substantially longer than direct RAG requests
because agent runs may call the LLM multiple times.

The main reliability risks are:

- low retrieval scores causing weak grounding
- prompt-injection-like inputs reaching the model
- long local LLM generation latency
- future drift in query mix, retrieval score, or source distribution

## Alert Recommendations

Production alert thresholds should include:

- P95 `/rag/query` latency above 10 seconds for 5 minutes
- P95 `/agent/run` latency above 30 seconds for 5 minutes
- Any sustained nonzero error rate
- Prompt-injection-marker anomaly rate above normal baseline
- Top retrieval score persistently below 0.20
- Drift PSI above 0.20 for query length, retrieval score, or source mix

## Artifact Summary

The dashboard screenshot in `docs/dashboard-screenshot.png` captures the live
Grafana view after simulated traffic. The dashboard definition is preserved in
`dashboards/finalproject-dashboard.json`, and the instrumentation logic lives
in `src/monitoring/metrics.py`. Together, these artifacts document the metric
design, the observed runtime behavior, and the operational interpretation of
the system.
