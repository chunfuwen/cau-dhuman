"""Sentence embedding engine for semantic retrieval.

Wraps sentence-transformers behind a lazily-initialised singleton so that the
heavy model is only loaded on first use. Model weights are resolved via the
HuggingFace hub (supports an offline cache / mirror via HF_ENDPOINT).
"""
from __future__ import annotations

import os
import threading

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
DIMENSION = int(os.getenv("EMBED_DIM", "384"))

_lock = threading.Lock()
_model = None


def _load() -> "object":
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME)
    return _model


def encode(texts: list[str], batch_size: int = 32) -> "list[list[float]]":
    """Return L2-normalised embeddings for a list of texts (cosine-ready)."""
    if not texts:
        return []
    model = _load()
    vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
    return vectors.tolist()


def embed_one(text: str) -> "list[float]":
    return encode([text])[0]


def is_available() -> bool:
    try:
        _load()
        return True
    except Exception:
        return False
