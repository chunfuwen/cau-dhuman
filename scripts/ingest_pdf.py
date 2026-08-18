"""Ingest a PDF into the dense vector store.

Extracts text page-by-page (pypdf), splits it into overlapping chunks,
embeds each chunk (sentence-transformers) and persists a FAISS vectorstore
under app/kb/vectorstore/.

Run:
    python scripts/ingest_pdf.py [path/to/file.pdf]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pypdf import PdfReader

from app.rag import embedder
from app.rag.vectorstore import VectorStore

DEFAULT_PDF = ROOT / "multimodal.pdf"
OUT_DIR = ROOT / "app" / "kb" / "vectorstore"
CHUNK_SIZE = 350
OVERLAP = 60


def extract_text(pdf_path: Path) -> "list[tuple[int, str]]":
    """Return [(page_number_1based, text)] for each non-empty page."""
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i, text))
    return pages


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> "list[str]":
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = start + size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        if end >= n:
            break
        start = end - overlap
    return chunks


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    pages = extract_text(pdf_path)
    chunks: list[tuple[str, dict]] = []
    for page_no, text in pages:
        for c in chunk_text(text):
            chunks.append(
                (
                    c,
                    {"text": c, "source": pdf_path.name, "page": page_no},
                )
            )
    print(f"parsed {len(pages)} page(s) -> {len(chunks)} chunk(s)")

    print(f"loading embedding model {embedder.MODEL_NAME} ...")
    vectors = embedder.encode([text for text, _ in chunks])

    store = VectorStore(dimension=embedder.DIMENSION)
    n = store.add(vectors, [meta for _, meta in chunks])
    store.save(OUT_DIR)
    print(f"stored {n} vectors into {OUT_DIR}")


if __name__ == "__main__":
    main()
