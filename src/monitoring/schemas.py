"""Request and response schemas for the final project service."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RAGQueryRequest(BaseModel):
    """Request body for a grounded RAG query."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "How does RAG reduce hallucination?",
                "top_k": 5,
                "model": "qwen2.5:7b",
                "skip_generation": False,
            }
        }
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Question to answer using the Milestone 6 knowledge base.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of retrieved chunks to include as context.",
    )
    model: str = Field(
        default="qwen2.5:7b",
        description="Ollama model name used for generation.",
    )
    skip_generation: bool = Field(
        default=False,
        description="Retrieve evidence without calling Ollama.",
    )


class RAGQueryResponse(BaseModel):
    """Response body for a grounded RAG query."""

    query: str
    answer: str
    retrieved_chunks: list[dict[str, Any]]
    timings: dict[str, Any]
    metadata: dict[str, Any]


class AgentRunRequest(BaseModel):
    """Request body for one multi-tool agent task."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task": "Explain why grounding reduces hallucination and cite evidence.",
                "top_k": 5,
                "model": "qwen2.5:7b",
                "dry_run": False,
                "plan_only": False,
            }
        }
    )

    task: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Task for the migrated Milestone 6 multi-tool agent.",
    )
    task_id: str = Field(
        default="api_task",
        min_length=1,
        max_length=128,
        description="Trace identifier returned in the response.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of retrieved chunks available to the agent.",
    )
    model: str = Field(
        default="qwen2.5:7b",
        description="Ollama model name used for agent tool calls.",
    )
    dry_run: bool = Field(
        default=False,
        description="Use real retrieval but placeholder LLM/tool outputs.",
    )
    plan_only: bool = Field(
        default=False,
        description="Use placeholder retrieval and placeholder outputs for route inspection.",
    )


class AgentRunResponse(BaseModel):
    """Response body for one multi-tool agent task."""

    task_id: str
    task: str
    model: str
    policy: str
    tool_path: list[str]
    steps: list[dict[str, Any]]
    final_answer: str
    total_latency_ms: float
    metadata: dict[str, Any]


class HealthResponse(BaseModel):
    """Service health response."""

    status: str
    rag_ready: bool
    knowledge_base: str


class MetricsResponse(BaseModel):
    """Lightweight operational counters for the initial service backbone."""

    total_rag_queries: int
    failed_rag_queries: int
    avg_rag_latency_ms: float
    rag_ready: bool
    total_agent_runs: int
    failed_agent_runs: int
    avg_agent_latency_ms: float


class DriftLoadResponse(BaseModel):
    """Response after loading Component 4 drift results into metrics."""

    status: str
    result_file: str
    loaded_windows: int
    alert_count: int


class DriftStatusResponse(BaseModel):
    """Latest Component 4 drift load status."""

    loaded: bool
    result_file: str | None
    loaded_windows: int
    alert_count: int
