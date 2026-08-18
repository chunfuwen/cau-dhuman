"""RAG indexer + retriever facade used by the API layer."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path

from app.config import DENSE_TOP_K, VECTORSTORE_DIR
from app.rag.bm25 import BM25Index
from app.rag.document import Chunk, read_documents
from app.rag.tokenizer import tokenize

STATS_PATH = "kb_stats.json"  # written next to the index artifact


@dataclass
class Hit:
    source: str
    doc_title: str
    section: str
    text: str
    score: float

    @property
    def content(self) -> str:
        head = f"{self.doc_title} > {self.section}" if self.section and self.section != self.doc_title else self.doc_title
        return f"[{head}]\n{self.text}".strip()


@dataclass
class RetrievalStats:
    n_documents: int
    n_chunks: int
    top_k: int = 4


class KnowledgeIndex:
    """Hybrid RAG index: BM25 over the markdown KB + optional dense
    vectorstore (e.g. PDF chunks) for semantic retrieval."""

    def __init__(self, docs_dir: Path, vectorstore_dir: Path | None = VECTORSTORE_DIR):
        self.docs_dir = docs_dir
        self.vectorstore_dir = vectorstore_dir
        self.chunks: list[Chunk] = []
        self.bm25 = BM25Index()
        self.dense = None
        self._lock = threading.Lock()
        self.refresh()
        self._load_dense()

    def _load_dense(self) -> None:
        if self.vectorstore_dir is None:
            return
        try:
            from app.rag.vectorstore import VectorStore

            if (self.vectorstore_dir / "index.bin").exists():
                self.dense = VectorStore.load(self.vectorstore_dir)
        except Exception:
            self.dense = None

    def refresh(self) -> RetrievalStats:
        chunks = read_documents(self.docs_dir)
        bm25 = BM25Index()
        for chunk in chunks:
            terms = tokenize(chunk.content)
            # title/section words are strong signals -> weighted up
            terms += tokenize(chunk.doc_title) * 2
            terms += tokenize(chunk.section)
            bm25.add(terms)
        bm25.build()
        with self._lock:
            self.chunks = chunks
            self.bm25 = bm25
        return RetrievalStats(n_documents=len({c.source for c in chunks}), n_chunks=len(chunks))

    def search(self, query: str, top_k: int = 4) -> list[Hit]:
        query_terms = tokenize(query)
        if not query_terms:
            return []
        with self._lock:
            bm25 = self.bm25
            chunks = list(self.chunks)
        hits: list[Hit] = []
        if query_terms:
            for doc_id, score in bm25.search(query_terms, top_k=top_k):
                chunk = chunks[doc_id]
                hits.append(
                    Hit(
                        source=chunk.source,
                        doc_title=chunk.doc_title,
                        section=chunk.section,
                        text=chunk.text.strip(),
                        score=round(score, 4),
                    )
                )
        hits.extend(self._dense_search(query, top_k=DENSE_TOP_K, seen=hits))
        return hits

    def _dense_search(self, query: str, top_k: int = 2, seen: "list[Hit] | None" = None) -> list[Hit]:
        """Semantic retrieval over the optional PDF vectorstore. Returns [] when
        the dense store or embedding model is unavailable (graceful fallback)."""
        if self.dense is None:
            return []
        try:
            from app.rag import embedder

            query_vec = embedder.embed_one(query)
            known = {(h.source, h.text) for h in (seen or [])}
            dense_hits: list[Hit] = []
            for v in self.dense.search(query_vec, top_k=top_k):
                if (v.source, v.text) in known:
                    continue
                dense_hits.append(
                    Hit(
                        source=v.source,
                        doc_title=v.source,
                        section=f"第 {v.page} 页",
                        text=v.text.strip(),
                        score=v.score,
                    )
                )
            return dense_hits
        except Exception:
            return []

    def dump(self, out: Path) -> None:
        payload = {
            "n_documents": len({c.source for c in self.chunks}),
            "n_chunks": len(self.chunks),
            "sources": sorted({c.source for c in self.chunks}),
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_index(docs_dir: Path | None = None) -> KnowledgeIndex:
    docs_dir = docs_dir or (Path(__file__).resolve().parent.parent / "kb" / "docs")
    return KnowledgeIndex(docs_dir)