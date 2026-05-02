from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

try:
    from .rag_pipeline import DEFAULT_DOCUMENTS_DIR, DEFAULT_MODEL, RAGPipeline, RetrievedChunk
    RAG_IMPORT_ERROR = None
except (ImportError, ModuleNotFoundError) as exc:
    RAG_CODE_DIR = Path(__file__).resolve().parent / "data" / "rag_pipeline"
    if str(RAG_CODE_DIR) not in sys.path:
        sys.path.insert(0, str(RAG_CODE_DIR))
    try:
        from rag_pipeline import DEFAULT_DOCUMENTS_DIR, DEFAULT_MODEL, RAGPipeline, RetrievedChunk
        RAG_IMPORT_ERROR = None
    except ModuleNotFoundError:
        DEFAULT_DOCUMENTS_DIR = Path(__file__).resolve().parent / "data" / "documents"
        DEFAULT_MODEL = "qwen2.5:7b"
        RAGPipeline = None
        RAG_IMPORT_ERROR = exc


DEFAULT_AGENT_TRACE_DIR = Path(__file__).resolve().parent / "agent_traces"


@dataclass
class FallbackRetrievedChunk:
    chunk_id: str
    source: str
    chunk_index: int
    text: str
    score: float
    rank: int


if "RetrievedChunk" not in globals():
    RetrievedChunk = FallbackRetrievedChunk


AGENT_TASKS = [
    {
        "id": "task_01",
        "task": "Retrieve evidence about RAG and summarize the two-stage RAG pipeline.",
    },
    {
        "id": "task_02",
        "task": "Explain why grounding reduces hallucination and cite the retrieved evidence.",
    },
    {
        "id": "task_03",
        "task": "Extract the recommended chunk size and overlap settings for this project.",
    },
    {
        "id": "task_04",
        "task": "Compare short-term and long-term LLM memory and explain how memory supports personalization.",
    },
    {
        "id": "task_05",
        "task": "Extract the components of a basic LLM agent controller and summarize why traces matter.",
    },
    {
        "id": "task_06",
        "task": "Explain the relationship between Ollama and Qwen in this project.",
    },
    {
        "id": "task_07",
        "task": "List the personalization signals used by recommender systems and summarize how they support ranking.",
    },
    {
        "id": "task_08",
        "task": "Explain personalization bias and recommend mitigation strategies based on the documents.",
    },
    {
        "id": "task_09",
        "task": "Compare FAISS and Chroma as vector database options for a small RAG project.",
    },
    {
        "id": "task_10",
        "task": "Create a concise implementation checklist for building this local RAG system.",
    },
]


@dataclass
class AgentStep:
    step: int
    decision: str
    tool: str
    reason: str
    input: str
    output: Any
    latency_ms: float


@dataclass
class AgentTrace:
    task_id: str
    task: str
    model: str
    policy: str
    steps: list[AgentStep]
    final_answer: str
    total_latency_ms: float


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, host: str = "http://localhost:11434") -> str:
    response = requests.post(
        f"{host.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=240,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def format_retrieved_chunks(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for chunk in chunks:
        blocks.append(
            f"[Source: {chunk.source}, chunk {chunk.chunk_index}, rank {chunk.rank}, score {chunk.score:.3f}]\n"
            f"{chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)


def compact_retrieval_output(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "rank": chunk.rank,
            "source": chunk.source,
            "chunk_index": chunk.chunk_index,
            "score": round(chunk.score, 3),
            "text": chunk.text,
        }
        for chunk in chunks
    ]


class MultiToolAgent:
    """Lightweight agent controller with observable tool choices."""

    policy = (
        "Always retrieve evidence first. Then choose summarizer for summarize/checklist tasks, "
        "extractor for list/extract/component tasks, and reasoning for compare/why/how/explain tasks. "
        "Use the local open-weight LLM for tool outputs and final answer synthesis."
    )

    def __init__(
        self,
        data_dir: Path = DEFAULT_DOCUMENTS_DIR,
        model: str = DEFAULT_MODEL,
        top_k: int = 5,
        dry_run: bool = False,
        plan_only: bool = False,
    ) -> None:
        self.model = model
        self.top_k = top_k
        self.dry_run = dry_run
        self.plan_only = plan_only
        if plan_only:
            self.rag = None
        elif RAGPipeline is None:
            if not dry_run:
                raise RuntimeError(
                    "Part 1 FAISS RAG dependencies are unavailable. "
                    "Install requirements.txt, use --dry-run, or use --plan-only for trace-structure debugging."
                ) from RAG_IMPORT_ERROR
            self.rag = KeywordRetriever(data_dir=data_dir)
        else:
            self.rag = RAGPipeline(data_dir=data_dir)
        if self.rag is not None:
            self.rag.ingest()

    def choose_tools(self, task: str) -> list[dict[str, str]]:
        lower = task.lower()
        plan = [
            {
                "tool": "retriever",
                "reason": "The task asks for document-grounded evidence, so retrieval must run before other tools.",
            }
        ]

        if any(word in lower for word in ["extract", "list", "components", "signals", "settings"]):
            plan.append(
                {
                    "tool": "extractor",
                    "reason": "The task asks for structured fields or a list, so extraction is the best second tool.",
                }
            )
        elif any(word in lower for word in ["compare", "why", "how", "explain", "relationship"]):
            plan.append(
                {
                    "tool": "reasoning",
                    "reason": "The task requires explanation or comparison, so reasoning over retrieved evidence is needed.",
                }
            )
        else:
            plan.append(
                {
                    "tool": "summarizer",
                    "reason": "The task asks for a concise synthesis, so summarization is the best second tool.",
                }
            )

        plan.append(
            {
                "tool": "final_answer",
                "reason": "The agent must produce a complete answer with source evidence after using tools.",
            }
        )
        return plan

    def run_tool(self, tool: str, task: str, retrieved: list[RetrievedChunk], intermediate: str) -> Any:
        context = format_retrieved_chunks(retrieved)

        if tool == "retriever":
            return compact_retrieval_output(retrieved)

        if tool == "summarizer":
            if self.dry_run or self.plan_only:
                return dry_run_response(tool, task, retrieved, intermediate)
            prompt = f"""Summarize the retrieved context for the task.

Use only the context. Include source filenames when useful.

Task:
{task}

Context:
{context}

Summary:"""
            return call_ollama(prompt, model=self.model)

        if tool == "extractor":
            if self.dry_run or self.plan_only:
                return dry_run_response(tool, task, retrieved, intermediate)
            prompt = f"""Extract the requested facts from the retrieved context.

Use only the context. Return concise bullet points. Include source filenames.

Task:
{task}

Context:
{context}

Extracted facts:"""
            return call_ollama(prompt, model=self.model)

        if tool == "reasoning":
            if self.dry_run or self.plan_only:
                return dry_run_response(tool, task, retrieved, intermediate)
            prompt = f"""Reason over the retrieved context to solve the task.

Use only the context. Explain the answer in a grounded way and include source filenames.

Task:
{task}

Context:
{context}

Reasoned answer:"""
            return call_ollama(prompt, model=self.model)

        if tool == "final_answer":
            if self.dry_run or self.plan_only:
                return dry_run_response(tool, task, retrieved, intermediate)
            prompt = f"""Create the final answer for this multi-tool agent task.

Use only the retrieved context and the intermediate tool output. Include an evidence trail with source filenames.

Task:
{task}

Retrieved context:
{context}

Intermediate tool output:
{intermediate}

Final answer:"""
            return call_ollama(prompt, model=self.model)

        raise ValueError(f"Unknown tool: {tool}")

    def run_task(self, task_id: str, task: str) -> AgentTrace:
        total_start = time.perf_counter()
        steps: list[AgentStep] = []
        retrieved: list[RetrievedChunk] = []
        intermediate = ""

        for idx, planned in enumerate(self.choose_tools(task), start=1):
            tool = planned["tool"]
            start = time.perf_counter()

            if tool == "retriever":
                if self.plan_only:
                    retrieved = plan_only_retrieval(task)
                else:
                    retrieved = self.rag.retrieve(task, top_k=self.top_k)
                output = self.run_tool(tool, task, retrieved, intermediate)
            else:
                output = self.run_tool(tool, task, retrieved, intermediate)
                intermediate = str(output)

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            steps.append(
                AgentStep(
                    step=idx,
                    decision=f"Select {tool}",
                    tool=tool,
                    reason=planned["reason"],
                    input=task if tool == "retriever" else intermediate[:500],
                    output=output,
                    latency_ms=latency_ms,
                )
            )

        final_answer = str(steps[-1].output)
        total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)
        return AgentTrace(
            task_id=task_id,
            task=task,
            model=self.model,
            policy=self.policy,
            steps=steps,
            final_answer=final_answer,
            total_latency_ms=total_latency_ms,
        )


def write_trace(trace: AgentTrace, output_dir: Path) -> Path:
    """Write one trace file. Kept for optional debugging, not used by default evaluation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{trace.task_id}.json"
    path.write_text(json.dumps(asdict(trace), indent=2), encoding="utf-8")
    return path


def write_all_traces(traces: list[AgentTrace], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "all_traces.json"
    path.write_text(json.dumps([asdict(trace) for trace in traces], indent=2), encoding="utf-8")
    return path


def dry_run_response(
    tool: str,
    task: str,
    retrieved: list[RetrievedChunk],
    intermediate: str,
) -> str:
    sources = ", ".join(f"{chunk.source} (rank {chunk.rank})" for chunk in retrieved[:3])
    if tool == "summarizer":
        return f"DRY RUN summary for task: {task}. Evidence sources: {sources}."
    if tool == "extractor":
        return f"DRY RUN extracted facts for task: {task}. Evidence sources: {sources}."
    if tool == "reasoning":
        return f"DRY RUN reasoning for task: {task}. Evidence sources: {sources}."
    if tool == "final_answer":
        return (
            f"DRY RUN final answer for task: {task}. "
            f"This trace verifies tool routing and retrieval integration only. "
            f"Final evaluated runs must use qwen2.5:7b. Evidence sources: {sources}. "
            f"Intermediate output: {intermediate[:250]}"
        )
    return f"DRY RUN output for {tool}."


def plan_only_retrieval(task: str) -> list[RetrievedChunk]:
    """Return placeholder retrieval records without importing FAISS or embedding models."""
    source_hint = infer_source_hint(task)
    return [
        RetrievedChunk(
            chunk_id=f"{source_hint}::plan-only",
            source=source_hint,
            chunk_index=0,
            text=(
                "PLAN ONLY TRACE: final evaluated runs must replace this placeholder "
                "with actual FAISS retrieval output from Part 1."
            ),
            score=0.0,
            rank=1,
        )
    ]


def infer_source_hint(task: str) -> str:
    lower = task.lower()
    if "memory" in lower:
        return "llm_memory.md"
    if "agent" in lower or "traces" in lower:
        return "llm_agents.md"
    if "ollama" in lower or "qwen" in lower:
        return "local_llm.md"
    if "recommender" in lower or "signals" in lower:
        return "recommender_systems.md"
    if "bias" in lower:
        return "personalization_bias.md"
    if "faiss" in lower or "chroma" in lower or "vector" in lower:
        return "vector_databases.md"
    if "chunk" in lower:
        return "chunking.md"
    if "ground" in lower or "hallucination" in lower:
        return "grounding.md"
    if "embedding" in lower:
        return "embeddings.md"
    return "rag_overview.md"


class KeywordRetriever:
    """Dependency-light fallback retriever for dry-run traces only."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.documents: list[dict[str, str]] = []

    def ingest(self) -> int:
        self.documents = []
        for path in sorted(self.data_dir.glob("*.md")):
            self.documents.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
        if not self.documents:
            raise FileNotFoundError(f"No .md documents found in {self.data_dir}")
        return len(self.documents)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        query_terms = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
        scored = []
        for doc in self.documents:
            text_terms = set(re.findall(r"[a-zA-Z0-9]+", doc["text"].lower()))
            overlap = query_terms.intersection(text_terms)
            score = len(overlap) / max(1, len(query_terms))
            scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for rank, (score, doc) in enumerate(scored[:top_k], start=1):
            results.append(
                RetrievedChunk(
                    chunk_id=f"{doc['source']}::dry-run",
                    source=doc["source"],
                    chunk_index=0,
                    text=doc["text"],
                    score=score,
                    rank=rank,
                )
            )
        return results


def run_evaluation(output_dir: Path, model: str, top_k: int, dry_run: bool, plan_only: bool) -> list[AgentTrace]:
    agent = MultiToolAgent(model=model, top_k=top_k, dry_run=dry_run, plan_only=plan_only)
    traces = []
    for item in AGENT_TASKS:
        trace = agent.run_task(item["id"], item["task"])
        traces.append(trace)
        print(f"Completed trace for {item['id']}: {trace.total_latency_ms} ms")
    all_traces_path = write_all_traces(traces, output_dir)
    print(f"Wrote all traces: {all_traces_path}")
    return traces


def write_agent_summary(traces: list[AgentTrace], output_dir: Path) -> Path:
    rows = []
    for trace in traces:
        tools = " -> ".join(step.tool for step in trace.steps)
        summary = summarize_final_answer(trace.final_answer)
        rows.append(
            f"| {trace.task_id} | {tools} | {trace.total_latency_ms:.2f} | "
            f"{summary.replace('|', '/') } |"
        )

    summary = [
        "# Agent Trace Summary",
        "",
        "| Task | Tool Path | Total Latency ms | Final Answer Preview |",
        "|---|---|---:|---|",
        *rows,
        "",
    ]
    path = output_dir / "trace_summary.md"
    path.write_text("\n".join(summary), encoding="utf-8")
    return path


def summarize_final_answer(answer: str) -> str:
    """Create a complete one-sentence summary for trace_summary.md."""
    cleaned = " ".join(answer.split())
    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned)[0]
    return first_sentence if first_sentence else "Final answer completed; see all_traces.json for details."


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Part 2 multi-tool agent evaluation.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_AGENT_TRACE_DIR)
    parser.add_argument("--task", help="Run one custom task instead of the 10-task evaluation.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate traces without calling Ollama/Qwen. Use only for debugging structure.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Generate placeholder trace skeletons without importing RAG dependencies or calling Ollama/Qwen.",
    )
    args = parser.parse_args()

    if args.task:
        agent = MultiToolAgent(model=args.model, top_k=args.top_k, dry_run=args.dry_run, plan_only=args.plan_only)
        trace = agent.run_task("custom_task", args.task)
        write_trace(trace, args.output_dir)
        print(json.dumps(asdict(trace), indent=2))
        return

    traces = run_evaluation(
        args.output_dir,
        model=args.model,
        top_k=args.top_k,
        dry_run=args.dry_run,
        plan_only=args.plan_only,
    )
    summary_path = write_agent_summary(traces, args.output_dir)
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
