# Final Project

## Overview

This repository is a submission-facing version of the Module 8 final project.
It contains only the top-level structures explicitly expected by the assignment
and checklist:

- `src/`
- `docs/`
- `dashboards/`
- `logs/`
- `visualizations/`
- `requirements.txt`
- `README.md`

The original working repository layout has been preserved separately in
`FinalProject-old/`.

## Component Links

### Component 1: Production Monitoring Dashboard

- instrumentation code: `src/monitoring/metrics.py`
- service integration: `src/monitoring/service.py`
- dashboard configs: `dashboards/prometheus.yml`, `dashboards/docker-compose.yml`, `dashboards/finalproject-dashboard.json`
- screenshot: `docs/dashboard-screenshot.png`
- interpretation: `docs/dashboard-interpretation.md`

### Component 2: A/B Test Design & Simulation

- experiment specification: `docs/experiment-specification.md`
- simulation code: `src/ab_test/ab_test_simulation.py`
- recommendation memo: `docs/recommendation-memo.md`

### Component 3: Model Card & Governance Packet

- model card: `docs/model-card.md`
- lineage diagram: `docs/lineage-diagram.png`
- risk register: `docs/risk-register.md`
- audit trail: `logs/audit-trail.jsonl`

### Component 4: Data Integrity & Drift Detection

- drift detection code: `src/drift/drift_detection.py`
- diagnostic report: `docs/drift-diagnostic-report.md`
- drift visualizations: `visualizations/input_length_drift.png`, `visualizations/response_length_drift.png`, `visualizations/retrieval_score_drift.png`, `visualizations/integrity_anomalies.png`

### Component 5: AI Risk Assessment

- governance review: `docs/governance-review.md`
- risk matrix: `docs/risk-matrix.md`
- system boundary diagram: `docs/system-boundary-diagram.png`
- CTO memo: `docs/cto-memo.md`

## Setup

From `FinalProject`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduction

### Monitoring Dashboard

Start the API:

```bash
python -m src.monitoring.service
```

In a second terminal, start the dashboard stack:

```bash
cd dashboards
docker compose up -d
```

Generate traffic:

```bash
python src/monitoring/simulate_traffic.py \
  --base-url http://127.0.0.1:8000 \
  --requests 20 \
  --skip-rag-generation \
  --plan-only-agent
```

### A/B Simulation

```bash
python src/ab_test/ab_test_simulation.py
```

### Drift Detection

Synthetic drift run:

```bash
python src/drift/drift_detection.py
```

Optional real RAG/Ollama run:

```bash
python src/drift/drift_detection.py \
  --mode real-rag \
  --reference-size 12 \
  --window-size 8 \
  --top-k 5 \
  --model qwen2.5:7b \
  --continue-on-error
```

## Lessons Learned

1. Monitoring is more valuable when metrics connect directly to system risk.
   Retrieval score, drift, and input anomalies were more actionable than raw
   request counts alone.
2. A/B testing becomes defensible only after explicit randomization, power
   calculation, and guardrail design are written down.
3. Governance artifacts are strongest when they are system-specific. Generic
   model-card language is much weaker than describing the actual RAG pipeline,
   local runtime, and known failure modes.
4. Drift analysis needs impact reasoning. The most useful Component 4 findings
   were the ones that connected retrieval degradation to grounded-answer risk.
5. Repository structure affects grading. A clean submission-facing layout makes
   the project much easier to audit against the rubric.
