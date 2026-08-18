"""Tests for the PDF -> embedding -> vectorstore pipeline."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ROOT
from app.rag import embedder
from app.rag.vectorstore import VectorStore
from scripts import ingest_pdf

PDF_PATH = ROOT / "multimodal.pdf"
OUT_DIR = ROOT / "app" / "kb" / "vectorstore"


@pytest.fixture(scope="module")
def store() -> VectorStore:
    embedder._load()
    return VectorStore.load(OUT_DIR)


def test_pdf_text_is_extracted():
    pages = ingest_pdf.extract_text(PDF_PATH)
    assert pages
    assert all(text for _, text in pages)


def test_chunking_produces_text():
    text = pages = ingest_pdf.extract_text(PDF_PATH)[0][1]
    chunks = ingest_pdf.chunk_text(text, size=350, overlap=60)
    assert chunks
    assert len("".join(chunks)) >= len(text)


def test_vectorstore_persisted():
    assert (OUT_DIR / "index.bin").exists()
    assert (OUT_DIR / "meta.json").exists()


def test_vectorstore_loads_and_has_chunks(store):
    assert store.size >= 2


def test_meta_carries_source_and_page(store):
    assert store._meta
    first = store._meta[0]
    assert first["source"] == "multimodal.pdf"
    assert first["page"] >= 1


def test_semantic_search_returns_relevant_chunk(store):
    query = embedder.embed_one("Which major has the strongest growth?")
    hits = store.search(query, top_k=3)
    assert hits
    assert hits[0].score > 0.5
    assert "Food Science" in hits[0].text
