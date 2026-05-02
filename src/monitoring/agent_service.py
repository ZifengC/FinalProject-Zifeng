"""Service wrapper for the migrated multi-tool agent."""
from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from .agent_controller import MultiToolAgent
from .rag_service import DOCUMENTS_DIR


class AgentService:
    """Run agent tasks without writing trace result files."""

    def __init__(self) -> None:
        self.total_runs = 0
        self.failed_runs = 0
        self.latencies_ms: list[float] = []

    def run(
        self,
        task: str,
        task_id: str = "api_task",
        model: str = "qwen2.5:7b",
        top_k: int = 5,
        dry_run: bool = False,
        plan_only: bool = False,
    ) -> dict[str, Any]:
        """Run one task through the migrated Milestone 6 agent controller."""
        start = time.perf_counter()
        self.total_runs += 1

        try:
            agent = MultiToolAgent(
                data_dir=DOCUMENTS_DIR,
                model=model,
                top_k=top_k,
                dry_run=dry_run,
                plan_only=plan_only,
            )
            trace = agent.run_task(task_id=task_id, task=task)
            result = asdict(trace)
        except Exception:
            self.failed_runs += 1
            raise
        finally:
            self.latencies_ms.append((time.perf_counter() - start) * 1000)

        result["tool_path"] = [step["tool"] for step in result["steps"]]
        result["metadata"] = {
            "source_system": "FinalProject migrated Milestone 6 agent",
            "documents_dir": str(DOCUMENTS_DIR),
            "top_k": top_k,
            "dry_run": dry_run,
            "plan_only": plan_only,
            "writes_trace_files": False,
        }
        return result

    def metrics(self) -> dict[str, Any]:
        """Return simple counters until Component 1 Prometheus work."""
        total_latency = sum(self.latencies_ms)
        count = len(self.latencies_ms)
        return {
            "total_agent_runs": self.total_runs,
            "failed_agent_runs": self.failed_runs,
            "avg_agent_latency_ms": round(total_latency / count, 2) if count else 0.0,
        }
