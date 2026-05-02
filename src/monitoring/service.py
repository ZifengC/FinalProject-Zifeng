"""Final project FastAPI service backbone."""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .metrics import (
    CONTENT_TYPE_LATEST,
    load_component4_drift_metrics,
    observe_agent_result,
    observe_input,
    observe_rag_result,
    record_request,
    render_prometheus_metrics,
)
from .schemas import (
    AgentRunRequest,
    AgentRunResponse,
    DriftLoadResponse,
    DriftStatusResponse,
    HealthResponse,
    MetricsResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)


DRIFT_ONLY_MODE = os.getenv("FINALPROJECT_DRIFT_ONLY", "").lower() in {"1", "true", "yes"}

if DRIFT_ONLY_MODE:
    DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"
    rag_service = None
    agent_service = None
else:
    from .agent_service import AgentService
    from .rag_service import DOCUMENTS_DIR, RAGService

    rag_service = RAGService()
    agent_service = AgentService()

COMPONENT4_RESULTS_FILE = Path(__file__).resolve().parents[2] / "docs" / "drift_results.json"
component4_drift_status = {
    "loaded": False,
    "result_file": None,
    "loaded_windows": 0,
    "alert_count": 0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare the RAG index once at startup."""
    if rag_service is not None:
        rag_service.load()
    yield


app = FastAPI(
    title="Final Project RAG Service",
    description="FastAPI backbone wrapping the local RAG system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return service readiness."""
    return HealthResponse(
        status="drift_only" if DRIFT_ONLY_MODE else ("healthy" if rag_service.ready else "starting"),
        rag_ready=False if rag_service is None else rag_service.ready,
        knowledge_base=str(DOCUMENTS_DIR),
    )


@app.get("/stats", response_model=MetricsResponse)
async def stats() -> MetricsResponse:
    """Return human-readable service counters."""
    if rag_service is None or agent_service is None:
        return MetricsResponse(
            total_rag_queries=0,
            failed_rag_queries=0,
            avg_rag_latency_ms=0.0,
            rag_ready=False,
            total_agent_runs=0,
            failed_agent_runs=0,
            avg_agent_latency_ms=0.0,
        )
    return MetricsResponse(
        **rag_service.metrics(),
        **agent_service.metrics(),
    )


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics for Component 1 monitoring."""
    return Response(
        content=render_prometheus_metrics(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/drift/component4/load", response_model=DriftLoadResponse)
async def load_component4_drift() -> DriftLoadResponse:
    """Load offline Component 4 drift results into Prometheus gauges."""
    endpoint = "/drift/component4/load"
    with record_request(endpoint):
        report = json.loads(COMPONENT4_RESULTS_FILE.read_text(encoding="utf-8"))
        summary = load_component4_drift_metrics(report)
        component4_drift_status.update(
            {
                "loaded": True,
                "result_file": str(COMPONENT4_RESULTS_FILE),
                "loaded_windows": summary["loaded_windows"],
                "alert_count": summary["alert_count"],
            }
        )
    return DriftLoadResponse(
        status="loaded",
        result_file=str(COMPONENT4_RESULTS_FILE),
        loaded_windows=int(component4_drift_status["loaded_windows"]),
        alert_count=int(component4_drift_status["alert_count"]),
    )


@app.get("/drift/component4/status", response_model=DriftStatusResponse)
async def component4_drift_load_status() -> DriftStatusResponse:
    """Return the most recent Component 4 drift metrics load status."""
    return DriftStatusResponse(**component4_drift_status)


@app.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    """Answer a question with retrieval and grounded generation."""
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG endpoint is disabled in drift-only mode.")
    endpoint = "/rag/query"
    observe_input(endpoint, request.query)
    with record_request(endpoint):
        result = rag_service.answer(
            query=request.query,
            top_k=request.top_k,
            model=request.model,
            skip_generation=request.skip_generation,
        )
        observe_rag_result(result)
    return RAGQueryResponse(
        query=result["query"],
        answer=result["answer"],
        retrieved_chunks=result["retrieved_chunks"],
        timings=result["timings"],
        metadata=result["metadata"],
    )


@app.post("/agent/run", response_model=AgentRunResponse)
async def agent_run(request: AgentRunRequest) -> AgentRunResponse:
    """Run one multi-tool agent task with observable tool decisions."""
    if agent_service is None:
        raise HTTPException(status_code=503, detail="Agent endpoint is disabled in drift-only mode.")
    endpoint = "/agent/run"
    observe_input(endpoint, request.task)
    with record_request(endpoint):
        result = agent_service.run(
            task=request.task,
            task_id=request.task_id,
            model=request.model,
            top_k=request.top_k,
            dry_run=request.dry_run,
            plan_only=request.plan_only,
        )
        observe_agent_result(result)
    return AgentRunResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.monitoring.service:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
    )
