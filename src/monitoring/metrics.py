"""Prometheus instrumentation for the final project service."""
from __future__ import annotations

import time
import math
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


REQUESTS_TOTAL = Counter(
    "finalproject_requests_total",
    "Total API requests by endpoint and status.",
    ["endpoint", "status"],
)

ERRORS_TOTAL = Counter(
    "finalproject_errors_total",
    "Total API errors by endpoint and error type.",
    ["endpoint", "error_type"],
)

REQUEST_LATENCY_SECONDS = Histogram(
    "finalproject_request_latency_seconds",
    "End-to-end request latency by endpoint.",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)

INPUT_LENGTH_CHARS = Histogram(
    "finalproject_input_length_chars",
    "Input query or task length in characters.",
    ["endpoint"],
    buckets=(25, 50, 100, 250, 500, 1000, 2000, 4096, 8192),
)

INPUT_INTEGRITY_ANOMALIES_TOTAL = Counter(
    "finalproject_input_integrity_anomalies_total",
    "Input integrity anomalies detected before model execution.",
    ["endpoint", "anomaly_type"],
)

RAG_RETRIEVAL_LATENCY_SECONDS = Histogram(
    "finalproject_rag_retrieval_latency_seconds",
    "RAG retrieval latency reported by the pipeline.",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

RAG_GENERATION_LATENCY_SECONDS = Histogram(
    "finalproject_rag_generation_latency_seconds",
    "RAG generation latency reported by the pipeline.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 240),
)

RAG_RETRIEVED_CHUNKS = Histogram(
    "finalproject_rag_retrieved_chunks",
    "Number of chunks returned by retrieval.",
    buckets=(0, 1, 2, 3, 5, 8, 10),
)

RAG_TOP_SCORE = Gauge(
    "finalproject_rag_top_retrieval_score",
    "Most recent top retrieval similarity score.",
)

LLM_TTFT_APPROX_SECONDS = Histogram(
    "finalproject_llm_ttft_approx_seconds",
    "Approximate time to first token for non-streaming generation calls.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 240),
)

LLM_TOKENS_TOTAL = Counter(
    "finalproject_llm_tokens_total",
    "Estimated prompt and completion token counts for local generation.",
    ["direction"],
)

AGENT_TOOL_STEPS = Histogram(
    "finalproject_agent_tool_steps",
    "Number of tool steps in an agent run.",
    buckets=(1, 2, 3, 4, 5, 8, 10),
)

AGENT_LATENCY_SECONDS = Histogram(
    "finalproject_agent_latency_seconds",
    "Agent controller latency reported by the trace.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 240),
)

DRIFT_PSI = Gauge(
    "finalproject_drift_psi",
    "Latest drift PSI value by feature.",
    ["feature"],
)

COMPONENT4_FEATURE_DRIFT_PSI = Gauge(
    "finalproject_component4_feature_drift_psi",
    "Component 4 offline PSI drift score by feature and production window.",
    ["feature", "window"],
)

COMPONENT4_LABEL_DISTRIBUTION_DRIFT = Gauge(
    "finalproject_component4_label_distribution_drift",
    "Component 4 offline label distribution drift by production window.",
    ["window"],
)

COMPONENT4_INTEGRITY_ANOMALIES = Gauge(
    "finalproject_component4_integrity_anomalies",
    "Component 4 offline integrity anomaly count by anomaly type and production window.",
    ["anomaly_type", "window"],
)

COMPONENT4_OUTLIER_RATE = Gauge(
    "finalproject_component4_outlier_rate",
    "Component 4 offline outlier rate by feature and production window.",
    ["feature", "window"],
)

COMPONENT4_DRIFT_ALERT = Gauge(
    "finalproject_component4_drift_alert",
    "Component 4 binary drift alert by feature, severity, and production window.",
    ["feature", "severity", "window"],
)

CACHE_EVENTS_TOTAL = Counter(
    "finalproject_cache_events_total",
    "Cache events by cache name and outcome. Placeholder until cache is added.",
    ["cache", "outcome"],
)

_INPUT_LENGTH_BUCKETS = (50, 100, 250, 500, 1000, 4096)
_INPUT_LENGTH_REFERENCE = (0.10, 0.35, 0.30, 0.15, 0.07, 0.02, 0.01)
_input_length_counts = [0 for _ in _INPUT_LENGTH_REFERENCE]


def _input_length_bucket_index(length: int) -> int:
    for index, upper_bound in enumerate(_INPUT_LENGTH_BUCKETS):
        if length <= upper_bound:
            return index
    return len(_INPUT_LENGTH_BUCKETS)


def _update_input_length_drift(length: int) -> None:
    """Update a lightweight PSI drift signal for the live query-length mix."""
    _input_length_counts[_input_length_bucket_index(length)] += 1
    total = sum(_input_length_counts)
    if total < 5:
        DRIFT_PSI.labels(feature="input_length_chars").set(0.0)
        return

    epsilon = 1e-6
    psi = 0.0
    for count, expected in zip(_input_length_counts, _INPUT_LENGTH_REFERENCE):
        observed = max(count / total, epsilon)
        reference = max(expected, epsilon)
        psi += (observed - reference) * math.log(observed / reference)
    DRIFT_PSI.labels(feature="input_length_chars").set(max(0.0, psi))


@contextmanager
def record_request(endpoint: str) -> Iterator[None]:
    """Record success/error counts and end-to-end latency for an endpoint."""
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except Exception as exc:
        status = "error"
        ERRORS_TOTAL.labels(endpoint=endpoint, error_type=exc.__class__.__name__).inc()
        raise
    finally:
        REQUESTS_TOTAL.labels(endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY_SECONDS.labels(endpoint=endpoint).observe(time.perf_counter() - start)


def observe_input(endpoint: str, text: str) -> None:
    """Record input length and simple integrity anomalies."""
    INPUT_LENGTH_CHARS.labels(endpoint=endpoint).observe(len(text))
    _update_input_length_drift(len(text))
    stripped = text.strip()
    if not stripped:
        INPUT_INTEGRITY_ANOMALIES_TOTAL.labels(endpoint=endpoint, anomaly_type="empty").inc()
    if len(text) > 4096:
        INPUT_INTEGRITY_ANOMALIES_TOTAL.labels(endpoint=endpoint, anomaly_type="oversized").inc()
    lowered = text.lower()
    injection_markers = ["ignore previous", "ignore all previous", "system prompt", "developer message"]
    if any(marker in lowered for marker in injection_markers):
        INPUT_INTEGRITY_ANOMALIES_TOTAL.labels(
            endpoint=endpoint,
            anomaly_type="prompt_injection_marker",
        ).inc()


def observe_rag_result(result: dict[str, Any]) -> None:
    """Record RAG-specific retrieval and generation metrics."""
    retrieved = result.get("retrieved_chunks", [])
    RAG_RETRIEVED_CHUNKS.observe(len(retrieved))
    if retrieved:
        RAG_TOP_SCORE.set(float(retrieved[0].get("score", 0.0)))

    timings = result.get("timings", {})
    retrieval = timings.get("retrieval_ms", {})
    generation = timings.get("generation_ms", {})
    metadata = result.get("metadata", {})
    if isinstance(metadata, dict):
        prompt_tokens = int(metadata.get("prompt_estimated_tokens", 0) or 0)
        completion_tokens = int(metadata.get("completion_estimated_tokens", 0) or 0)
        if prompt_tokens > 0:
            LLM_TOKENS_TOTAL.labels(direction="prompt").inc(prompt_tokens)
        if completion_tokens > 0:
            LLM_TOKENS_TOTAL.labels(direction="completion").inc(completion_tokens)
    if "avg_ms" in retrieval:
        RAG_RETRIEVAL_LATENCY_SECONDS.observe(float(retrieval["avg_ms"]) / 1000)
    if "avg_ms" in generation:
        generation_seconds = float(generation["avg_ms"]) / 1000
        RAG_GENERATION_LATENCY_SECONDS.observe(generation_seconds)
        # Module 8 notes that true TTFT requires streaming. For this non-streaming
        # local service, total generation latency is the closest observable proxy.
        LLM_TTFT_APPROX_SECONDS.observe(generation_seconds)


def observe_agent_result(result: dict[str, Any]) -> None:
    """Record agent-specific tool and latency metrics."""
    AGENT_TOOL_STEPS.observe(len(result.get("steps", [])))
    if "total_latency_ms" in result:
        AGENT_LATENCY_SECONDS.observe(float(result["total_latency_ms"]) / 1000)


def load_component4_drift_metrics(report: dict[str, Any]) -> dict[str, Any]:
    """Load offline Component 4 drift results into Prometheus gauges."""
    windows = report.get("windows", [])
    alert_count = 0
    loaded_windows = 0

    for row in windows:
        window_name = str(row["window"])
        loaded_windows += 1

        for feature, value in row.get("feature_drift_psi", {}).items():
            score = float(value)
            COMPONENT4_FEATURE_DRIFT_PSI.labels(
                feature=str(feature),
                window=window_name,
            ).set(score)
            if str(feature) in {"input_length_chars", "retrieval_top_score"}:
                DRIFT_PSI.labels(feature=f"component4_{feature}").set(score)

        COMPONENT4_LABEL_DISTRIBUTION_DRIFT.labels(window=window_name).set(
            float(row.get("label_distribution_drift", 0.0))
        )

        for anomaly_type, count in row.get("integrity_anomalies", {}).items():
            COMPONENT4_INTEGRITY_ANOMALIES.labels(
                anomaly_type=str(anomaly_type),
                window=window_name,
            ).set(float(count))

        for feature, rate in row.get("outlier_rates", {}).items():
            COMPONENT4_OUTLIER_RATE.labels(
                feature=str(feature),
                window=window_name,
            ).set(float(rate))

        for feature, alert in row.get("alerts", {}).items():
            severity = str(alert.get("severity", "none"))
            is_alert = 1.0 if alert.get("alert", False) else 0.0
            COMPONENT4_DRIFT_ALERT.labels(
                feature=str(feature),
                severity=severity,
                window=window_name,
            ).set(is_alert)
            if is_alert:
                alert_count += 1

    return {
        "loaded_windows": loaded_windows,
        "alert_count": alert_count,
    }


def render_prometheus_metrics() -> bytes:
    """Return Prometheus exposition text."""
    return generate_latest()
