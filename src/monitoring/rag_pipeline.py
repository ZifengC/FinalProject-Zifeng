from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import requests
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DATA_ROOT = Path(__file__).resolve().parent
DEFAULT_DOCUMENTS_DIR = DEFAULT_DATA_ROOT / "documents"
DEFAULT_VECTOR_STORE_DIR = DEFAULT_DATA_ROOT / "vector_store"


@dataclass
class Chunk:
    chunk_id: str
    source: str
    chunk_index: int
    text: str


@dataclass
class RetrievedChunk:
    chunk_id: str
    source: str
    chunk_index: int
    text: str
    score: float
    rank: int


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def load_documents(data_dir: Path) -> list[dict[str, str]]:
    documents = []
    for path in sorted(data_dir.glob("*.md")):
        documents.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    if not documents:
        raise FileNotFoundError(f"No .md documents found in {data_dir}")
    return documents


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def chunk_documents(
    documents: list[dict[str, str]],
    max_tokens: int = 320,
    overlap_tokens: int = 60,
) -> list[Chunk]:
    chunks: list[Chunk] = []

    for doc in documents:
        source = doc["source"]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", doc["text"]) if p.strip()]
        current: list[str] = []
        chunk_index = 0

        def flush() -> None:
            nonlocal current, chunk_index
            if not current:
                return

            text = "\n\n".join(current).strip()
            chunks.append(
                Chunk(
                    chunk_id=f"{source}::chunk-{chunk_index}",
                    source=source,
                    chunk_index=chunk_index,
                    text=text,
                )
            )
            chunk_index += 1

            words = text.split()
            overlap_words = words[-overlap_tokens:] if overlap_tokens > 0 else []
            current = [" ".join(overlap_words)] if overlap_words else []

        for paragraph in paragraphs:
            units = [paragraph]
            if estimate_tokens(paragraph) > max_tokens:
                units = split_sentences(paragraph)

            for unit in units:
                candidate = "\n\n".join(current + [unit]).strip()
                if current and estimate_tokens(candidate) > max_tokens:
                    flush()
                current.append(unit)

        flush()

    return chunks


def embed_chunks(
    chunks: list[Chunk],
    embedding_model: SentenceTransformer,
) -> np.ndarray:
    texts = [chunk.text for chunk in chunks]
    return embedding_model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype("float32")


def create_vector_index(embeddings: np.ndarray) -> faiss.Index:
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    return index


def save_vector_store(index: faiss.Index, chunks: list[Chunk], index_dir: Path) -> dict[str, str]:
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "faiss.index"
    chunks_path = index_dir / "chunks.json"

    faiss.write_index(index, str(index_path))
    chunks_path.write_text(json.dumps([asdict(chunk) for chunk in chunks], indent=2), encoding="utf-8")

    return {
        "index_path": str(index_path),
        "chunks_path": str(chunks_path),
    }


def prepare_vector_store(
    documents_dir: Path = DEFAULT_DOCUMENTS_DIR,
    vector_store_dir: Path = DEFAULT_VECTOR_STORE_DIR,
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
    chunk_tokens: int = 320,
    overlap_tokens: int = 60,
) -> dict[str, Any]:
    timings: dict[str, float] = {}

    start = time.perf_counter()
    documents = load_documents(documents_dir)
    timings["load_documents_ms"] = round((time.perf_counter() - start) * 1000, 2)

    start = time.perf_counter()
    chunks = chunk_documents(documents, max_tokens=chunk_tokens, overlap_tokens=overlap_tokens)
    timings["chunking_ms"] = round((time.perf_counter() - start) * 1000, 2)

    start = time.perf_counter()
    embedding_model = SentenceTransformer(embedding_model_name)
    embeddings = embed_chunks(chunks, embedding_model)
    timings["embedding_ms"] = round((time.perf_counter() - start) * 1000, 2)

    start = time.perf_counter()
    index = create_vector_index(embeddings)
    saved_paths = save_vector_store(index, chunks, vector_store_dir)
    timings["vector_store_save_ms"] = round((time.perf_counter() - start) * 1000, 2)

    manifest = {
        "data_root": str(DEFAULT_DATA_ROOT),
        "documents_dir": str(documents_dir),
        "vector_store_dir": str(vector_store_dir),
        "embedding_model": embedding_model_name,
        "chunk_tokens": chunk_tokens,
        "overlap_tokens": overlap_tokens,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        **saved_paths,
        "timings": timings,
    }

    manifest_path = vector_store_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


class RAGPipeline:
    def __init__(
        self,
        data_dir: Path,
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
        chunk_tokens: int = 320,
        overlap_tokens: int = 60,
    ) -> None:
        self.data_dir = data_dir
        self.embedding_model_name = embedding_model_name
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.chunks: list[Chunk] = []
        self.index: faiss.Index | None = None
        self.timings: dict[str, list[float]] = {}

    def _record_time(self, stage: str, start: float) -> None:
        self.timings.setdefault(stage, []).append((time.perf_counter() - start) * 1000)

    def ingest(self) -> int:
        start = time.perf_counter()
        documents = load_documents(self.data_dir)
        self._record_time("load_documents_ms", start)

        start = time.perf_counter()
        self.chunks = chunk_documents(
            documents,
            max_tokens=self.chunk_tokens,
            overlap_tokens=self.overlap_tokens,
        )
        self._record_time("chunking_ms", start)

        start = time.perf_counter()
        embeddings = embed_chunks(self.chunks, self.embedding_model)
        self._record_time("embedding_ms", start)

        start = time.perf_counter()
        self.index = create_vector_index(embeddings)
        self._record_time("indexing_ms", start)

        return len(self.chunks)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if self.index is None:
            raise RuntimeError("Call ingest() before retrieve().")

        start = time.perf_counter()
        query_embedding = self.embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")
        scores, indices = self.index.search(query_embedding, top_k)
        self._record_time("retrieval_ms", start)

        results: list[RetrievedChunk] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
            if idx < 0:
                continue
            chunk = self.chunks[int(idx)]
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    score=float(score),
                    rank=rank,
                )
            )
        return results

    def build_prompt(self, query: str, retrieved: list[RetrievedChunk]) -> str:
        context_blocks = []
        for chunk in retrieved:
            context_blocks.append(
                f"[Source: {chunk.source}, chunk {chunk.chunk_index}, score {chunk.score:.3f}]\n"
                f"{chunk.text}"
            )
        context = "\n\n---\n\n".join(context_blocks)

        return f"""You are a grounded question-answering assistant.

Use ONLY the context below to answer the question.
If the context does not contain enough information, say: "The provided context is insufficient to answer this question."
Do not use outside knowledge.
Cite sources using the source filenames from the context.

Context:
{context}

Question:
{query}

Answer:"""

    def generate_with_ollama(
        self,
        prompt: str,
        ollama_model: str = DEFAULT_MODEL,
        host: str = "http://localhost:11434",
    ) -> str:
        start = time.perf_counter()
        response = requests.post(
            f"{host.rstrip('/')}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=240,
        )
        response.raise_for_status()
        self._record_time("generation_ms", start)
        return response.json()["response"].strip()

    def answer(
        self,
        query: str,
        top_k: int = 5,
        ollama_model: str = DEFAULT_MODEL,
        skip_generation: bool = False,
    ) -> dict[str, Any]:
        total_start = time.perf_counter()
        retrieved = self.retrieve(query, top_k=top_k)
        prompt = self.build_prompt(query, retrieved)
        answer = ""
        if not skip_generation:
            answer = self.generate_with_ollama(prompt, ollama_model=ollama_model)
        self._record_time("total_query_ms", total_start)

        return {
            "query": query,
            "answer": answer,
            "prompt": prompt,
            "retrieved_chunks": [asdict(chunk) for chunk in retrieved],
            "metadata": {
                "prompt_estimated_tokens": estimate_tokens(prompt),
                "completion_estimated_tokens": estimate_tokens(answer) if answer else 0,
                "response_length_chars": len(answer),
                "query_length_chars": len(query),
                "streaming_enabled": False,
                "ttft_note": (
                    "Non-streaming Ollama call: generation latency is used as a "
                    "TTFT approximation, consistent with the Module 8 caveat."
                ),
            },
            "timings": self.timing_summary(),
        }

    def timing_summary(self) -> dict[str, dict[str, float]]:
        summary = {}
        for stage, values in self.timings.items():
            summary[stage] = {
                "count": len(values),
                "total_ms": round(sum(values), 2),
                "avg_ms": round(sum(values) / len(values), 2),
            }
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Qwen/Ollama RAG pipeline.")
    subparsers = parser.add_subparsers(dest="command")

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Run Markdown Documents -> Chunking -> Embedding -> FAISS Vector Store.",
    )
    prepare_parser.add_argument("--documents-dir", type=Path, default=DEFAULT_DOCUMENTS_DIR)
    prepare_parser.add_argument("--vector-store-dir", type=Path, default=DEFAULT_VECTOR_STORE_DIR)
    prepare_parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    prepare_parser.add_argument("--chunk-tokens", type=int, default=320)
    prepare_parser.add_argument("--overlap-tokens", type=int, default=60)

    query_parser = subparsers.add_parser("query", help="Run one RAG query.")
    query_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DOCUMENTS_DIR)
    query_parser.add_argument("--query", default="How does RAG reduce hallucination?")
    query_parser.add_argument("--top-k", type=int, default=5)
    query_parser.add_argument("--model", default=DEFAULT_MODEL)
    query_parser.add_argument("--skip-generation", action="store_true")
    args = parser.parse_args()

    if args.command == "prepare":
        manifest = prepare_vector_store(
            documents_dir=args.documents_dir,
            vector_store_dir=args.vector_store_dir,
            embedding_model_name=args.embedding_model,
            chunk_tokens=args.chunk_tokens,
            overlap_tokens=args.overlap_tokens,
        )
        print(json.dumps(manifest, indent=2))
        return

    if args.command in (None, "query"):
        pipeline = RAGPipeline(data_dir=args.data_dir)
        chunk_count = pipeline.ingest()
        result = pipeline.answer(
            args.query,
            top_k=args.top_k,
            ollama_model=args.model,
            skip_generation=args.skip_generation,
        )

        print(f"Loaded {chunk_count} chunks")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
