# Final Project

## File Structure

```text
FinalProject/
├── README.md
├── requirements.txt
├── dashboards/
│   ├── docker-compose.yml
│   ├── finalproject-dashboard.json
│   └── prometheus.yml
├── docs/
│   ├── ab_test_results.json
│   ├── ab_test_summary.md
│   ├── cto-memo.md
│   ├── dashboard-interpretation.md
│   ├── dashboard-screenshot.png
│   ├── drift-diagnostic-report.md
│   ├── drift_results.json
│   ├── experiment-specification.md
│   ├── governance-review.md
│   ├── lineage-diagram.md
│   ├── lineage-diagram.png
│   ├── model-card.md
│   ├── recommendation-memo.md
│   ├── risk-matrix.md
│   ├── risk-register.md
│   ├── system-boundary-diagram.md
│   └── system-boundary-diagram.png
├── logs/
│   └── audit-trail.jsonl
├── src/
│   ├── ab_test/
│   │   └── ab_test_simulation.py
│   ├── drift/
│   │   └── drift_detection.py
│   └── monitoring/
│       ├── agent_controller.py
│       ├── agent_service.py
│       ├── metrics.py
│       ├── rag_pipeline.py
│       ├── rag_service.py
│       ├── schemas.py
│       ├── service.py
│       ├── simulate_traffic.py
│       └── documents/
└── visualizations/
    ├── dashboard-screenshot.png
    ├── input_length_drift.png
    ├── input_length_drift.svg
    ├── integrity_anomalies.png
    ├── integrity_anomalies.svg
    ├── response_length_drift.png
    ├── response_length_drift.svg
    ├── retrieval_score_drift.png
    ├── retrieval_score_drift.svg
    └── README.md
```

## Overview

This repository contains a local Retrieval-Augmented Generation (RAG) and
agent-assisted question answering system built around a curated Markdown
knowledge base, a FAISS retriever, and a locally served `qwen2.5:7b` model
through Ollama. The project focuses on five operational areas:

- production monitoring for a running LLM service
- A/B evaluation of retrieval configurations
- model and governance documentation
- drift and data-integrity diagnostics
- AI risk assessment and deployment readiness

The service exposes two primary workflows:

- `POST /rag/query` for grounded question answering over the local corpus
- `POST /agent/run` for lightweight multi-step agent execution using retrieval,
  extraction, summarization, and reasoning steps

## System Architecture

The system uses the following pipeline:

1. Markdown documents under `src/monitoring/documents/` are loaded and chunked.
2. Chunks are embedded with `sentence-transformers/all-MiniLM-L6-v2`.
3. A FAISS `IndexFlatIP` index retrieves the top relevant chunks for a query.
4. Retrieved context is inserted into a grounded prompt template.
5. Ollama serves `qwen2.5:7b` to generate the final answer.
6. FastAPI exposes the RAG and agent endpoints.
7. Prometheus and Grafana collect runtime metrics for latency, throughput,
   integrity anomalies, retrieval quality, and drift signals.

## Repository Structure

- `src/monitoring/`: API service, RAG pipeline, agent controller, monitoring
  instrumentation, and traffic simulation
- `src/ab_test/`: offline A/B experiment simulation and statistical evaluation
- `src/drift/`: drift detection, anomaly analysis, and visualization generation
- `docs/`: technical write-ups, governance documents, interpretation reports,
  and executive summaries
- `dashboards/`: Prometheus and Grafana configuration
- `logs/`: structured audit artifacts
- `visualizations/`: exported charts and screenshots

## Execution Modes

- `Component 1`: live local service run with real FastAPI, Prometheus, and
  Grafana processes; the saved dashboard reflects end-to-end requests against
  the running system.
- `Component 2`: offline simulation of two retrieval configurations with
  statistical evaluation over synthetic user outcomes.
- `Component 3`: documentation and governance artifacts derived from the system
  design and observed operating characteristics.
- `Component 4`: checked-in results use synthetic production windows for drift
  and integrity analysis; the codebase also supports a `real-rag` mode for live
  local execution.
- `Component 5`: governance and deployment-readiness assessment based on the
  implemented system, monitoring outputs, and drift analysis.

## Document Index

### Monitoring Dashboard

Mode: `live local run`

- instrumentation code: `src/monitoring/metrics.py`
- service integration: `src/monitoring/service.py`
- Prometheus config: `dashboards/prometheus.yml`
- Grafana stack: `dashboards/docker-compose.yml`
- dashboard export: `dashboards/finalproject-dashboard.json`
- dashboard interpretation: `docs/dashboard-interpretation.md`
- dashboard screenshot: `docs/dashboard-screenshot.png`

### A/B Experiment

Mode: `offline simulation`

- experiment specification: `docs/experiment-specification.md`
- simulation code: `src/ab_test/ab_test_simulation.py`
- result summary: `docs/ab_test_summary.md`
- raw results: `docs/ab_test_results.json`
- recommendation memo: `docs/recommendation-memo.md`

### Model Card And Governance

Mode: `documentation and governance review`

- model card: `docs/model-card.md`
- lineage diagram: `docs/lineage-diagram.md`
- lineage image: `docs/lineage-diagram.png`
- risk register: `docs/risk-register.md`
- audit trail: `logs/audit-trail.jsonl`

### Drift And Integrity Diagnostics

Mode: `synthetic analysis in checked-in results`; optional `real-rag` execution
is supported by the script

- drift detection script: `src/drift/drift_detection.py`
- diagnostic report: `docs/drift-diagnostic-report.md`
- raw drift results: `docs/drift_results.json`
- visualizations:
  `visualizations/input_length_drift.png`,
  `visualizations/response_length_drift.png`,
  `visualizations/retrieval_score_drift.png`,
  `visualizations/integrity_anomalies.png`

### Risk Assessment

Mode: `documentation and risk review`

- governance review: `docs/governance-review.md`
- risk matrix: `docs/risk-matrix.md`
- system boundary diagram: `docs/system-boundary-diagram.md`
- system boundary image: `docs/system-boundary-diagram.png`
- CTO memo: `docs/cto-memo.md`

## Environment Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional local model runtime:

```bash
ollama serve
ollama pull qwen2.5:7b
```

## Running The System

### Start The API

```bash
python -m src.monitoring.service
```

Default endpoints:

- `GET /health`
- `GET /metrics`
- `GET /stats`
- `POST /rag/query`
- `POST /agent/run`

### Start Monitoring

In a second terminal:

```bash
cd dashboards
docker compose up -d
```

This starts Prometheus and Grafana using the local dashboard configuration.

### Generate Sample Traffic

```bash
python src/monitoring/simulate_traffic.py \
  --base-url http://127.0.0.1:8000 \
  --requests 20
```

This produces live end-to-end RAG and agent traffic for the dashboard and
updates the runtime metrics exposed by `/metrics` and `/stats`. The final saved
dashboard view corresponds to full service execution rather than retrieval-only
or plan-only traffic.

## Reproducing The Analyses

### A/B Simulation

```bash
python src/ab_test/ab_test_simulation.py
```

Outputs:

- `docs/ab_test_results.json`
- `docs/ab_test_summary.md`

### Drift Detection With Synthetic Windows

```bash
python src/drift/drift_detection.py
```

Outputs:

- `docs/drift_results.json`
- `docs/drift-diagnostic-report.md`
- charts under `visualizations/`

### Drift Detection With Real RAG Calls

```bash
python src/drift/drift_detection.py \
  --mode real-rag \
  --reference-size 12 \
  --window-size 8 \
  --top-k 5 \
  --model qwen2.5:7b \
  --continue-on-error
```

This mode runs the local retriever and Ollama-backed generation path, then
computes drift and integrity metrics from the observed outputs.

## Key Findings

### Monitoring

- Retrieval is fast relative to local generation, so end-to-end latency is
  dominated by LLM inference and agent orchestration.
- Input-integrity anomaly counts, retrieval score, and PSI drift provide more
  actionable operational signals than request totals alone.

### A/B Evaluation

- Reducing retrieval context from `top_k=5` to `top_k=3` improved the simulated
  successful-answer rate and reduced latency.
- The treatment passed the defined recall, error-rate, and P95-latency
  guardrails in the offline simulation.

### Drift Analysis

- The largest drift appears in input length and retrieval score.
- Low retrieval score and integrity anomalies are the strongest indicators of
  elevated unsupported-answer risk.

### Governance And Risk

- The system is well-instrumented and well-documented, but it is not ready for
  real production deployment without stronger access control, prompt screening,
  retention controls, and grounded fallback behavior.

## Lessons Learned

1. Monitoring is most useful when metrics are tied directly to answer quality,
   retrieval quality, and operational risk.
2. A/B conclusions are much stronger when the experiment design, guardrails,
   and decision thresholds are explicit before results are generated.
3. Governance artifacts are more credible when they describe the actual system
   architecture, model runtime, and failure modes rather than generic AI risks.
4. Drift reporting becomes substantially more valuable when feature movement is
   connected to likely model-quality impact.
5. A local RAG stack is practical for experimentation, but it exposes latency,
   screening, and governance gaps that must be addressed before broader use.
