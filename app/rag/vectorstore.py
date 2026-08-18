"""Dense vector store for semantic retrieval.

Stores L2-normalised embeddings in a FAISS IndexFlatIP index (inner product
== cosine similarity on normalised vectors) plus a JSON metadata file with
the original chunk texts. Persisted under app/kb/vectorstore/.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

INDEX_FILE = "index.bin"
META_FILE = "meta.json"


@dataclass
class VectorHit:
    text: str
    source: str
    page: int
    score: float


class VectorStore:
    """Minimal cosine-similarity vector store built on FAISS."""

    def __init__(self, dimension: int = 384):
        if faiss is None:
            raise RuntimeError("faiss is required: pip install faiss-cpu")
        self.dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)
        self._meta: list[dict] = []
        self._lock = threading.Lock()

    def add(self, embeddings: "list[list[float]]", meta: "list[dict]") -> int:
        if len(embeddings) != len(meta):
            raise ValueError("embeddings and meta must have equal length")
        if embeddings:
            vectors = np.asarray(embeddings, dtype="float32")
            with self._lock:
                self._index.add(vectors)
                self._meta.extend(meta)
        return self._index.ntotal

    def search(self, query_embedding: "list[float]", top_k: int = 3) -> list[VectorHit]:
        if self._index.ntotal == 0:
            return []
        query = np.asarray([query_embedding], dtype="float32")
        scores, ids = self._index.search(query, min(top_k, self._index.ntotal))
        hits: list[VectorHit] = []
        with self._lock:
            meta = list(self._meta)
        for score, idx in zip(scores[0], ids[0]):
            m = meta[int(idx)]
            hits.append(
                VectorHit(
                    text=m.get("text", ""),
                    source=m.get("source", ""),
                    page=int(m.get("page", 0)),
                    score=round(float(score), 4),
                )
            )
        return hits

    @property
    def size(self) -> int:
        return self._index.ntotal

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        with self._lock:
            meta = list(self._meta)
        faiss.write_index(self._index, str(directory / INDEX_FILE))
        (directory / META_FILE).write_text(
            json.dumps({"dimension": self.dimension, "chunks": meta}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        if not (directory / INDEX_FILE).exists():
            raise FileNotFoundError(f"no index at {directory / INDEX_FILE}")
        payload = json.loads((directory / META_FILE).read_text(encoding="utf-8"))
        store = cls(dimension=int(payload["dimension"]))
        store._index = faiss.read_index(str(directory / INDEX_FILE))
        store._meta = payload["chunks"]
        return store
