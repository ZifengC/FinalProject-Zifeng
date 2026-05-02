"""Thin service wrapper around the migrated RAG pipeline."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .rag_pipeline import DEFAULT_MODEL, RAGPipeline

MONITORING_ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = MONITORING_ROOT / "documents"


class RAGService:
    """Manage one in-memory Milestone 6 RAG pipeline instance."""

    def __init__(
        self,
        documents_dir: Path = DOCUMENTS_DIR,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self.documents_dir = documents_dir
        self.default_model = default_model
        self.pipeline: RAGPipeline | None = None
        self.total_queries = 0
        self.failed_queries = 0
        self.latencies_ms: list[float] = []

    @property
    def ready(self) -> bool:
        return self.pipeline is not None

    def load(self) -> None:
        """Initialize embeddings, chunks, and FAISS index from Milestone 6 documents."""
        if self.pipeline is not None:
            return

        pipeline = RAGPipeline(data_dir=self.documents_dir)
        pipeline.ingest()
        self.pipeline = pipeline

    def answer(
        self,
        query: str,
        top_k: int = 5,
        model: str | None = None,
        skip_generation: bool = False,
    ) -> dict[str, Any]:
        """Answer a query using the Milestone 6 RAG implementation."""
        if self.pipeline is None:
            self.load()

        assert self.pipeline is not None
        start = time.perf_counter()
        self.total_queries += 1

        try:
            result = self.pipeline.answer(
                query=query,
                top_k=top_k,
                ollama_model=model or self.default_model,
                skip_generation=skip_generation,
            )
        except Exception:
            self.failed_queries += 1
            raise
        finally:
            self.latencies_ms.append((time.perf_counter() - start) * 1000)

        existing_metadata = result.get("metadata", {})
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}
        result["metadata"] = {
            **existing_metadata,
            "source_system": "FinalProject migrated Milestone 6 RAG",
            "documents_dir": str(self.documents_dir),
            "model": model or self.default_model,
            "top_k": top_k,
            "skip_generation": skip_generation,
        }
        return result

    def metrics(self) -> dict[str, Any]:
        """Return simple counters until Component 1 adds Prometheus instrumentation."""
        total_latency = sum(self.latencies_ms)
        count = len(self.latencies_ms)
        return {
            "total_rag_queries": self.total_queries,
            "failed_rag_queries": self.failed_queries,
            "avg_rag_latency_ms": round(total_latency / count, 2) if count else 0.0,
            "rag_ready": self.ready,
        }
