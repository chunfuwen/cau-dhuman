"""Tests for the RAG indexer/retriever components."""
from __future__ import annotations

from app.config import KB_DOCS_DIR
from app.rag.retriever import KnowledgeIndex
from app.rag.tokenizer import tokenize
from app.rag.bm25 import BM25Index


def test_tokenizer_handles_chinese_and_ascii():
    toks = tokenize("中国农业大学 农学院 CAU 2024")
    assert "中国" in toks or "农学" in toks
    assert all(t in toks for t in ["农学院", "cau", "2024"])


def test_bm25_ranks_relevant_doc_first():
    index = BM25Index()
    index.add(tokenize("学校概况 中国农业大学 双一流 985 工程"))
    index.add(tokenize("专业 农学 遗传育种 栽培耕作 智慧农业"))
    index.add(tokenize("导师 张福锁 植物营养 科技小院 养分管理"))
    index.build()
    hits = index.search(tokenize("农学专业 有哪些 方向"), top_k=3)
    assert hits
    top_doc = hits[0][0]
    assert top_doc == 1


def test_index_builds_and_counts_docs():
    idx = KnowledgeIndex(KB_DOCS_DIR)
    stats = idx.refresh()
    assert stats.n_documents >= 20  # overview + 21 colleges + professors + achievements
    assert stats.n_chunks > stats.n_documents


def test_retrieval_finds_college_docs():
    idx = KnowledgeIndex(KB_DOCS_DIR)
    hits = idx.search("农学院有哪些专业和主要课程", top_k=3)
    assert hits
    assert any("农学院" in h.doc_title for h in hits)


def test_retrieval_finds_professor():
    idx = KnowledgeIndex(KB_DOCS_DIR)
    hits = idx.search("张福锁院士的研究方向 科技小院", top_k=3)
    assert hits
    assert any("导师介绍" in h.doc_title or "张福锁" in h.content for h in hits)


def test_retrieval_finds_major_courses():
    idx = KnowledgeIndex(KB_DOCS_DIR)
    hits = idx.search("食品科学与工程专业学什么课程", top_k=3)
    assert hits
    assert any("食品" in h.doc_title for h in hits)


def test_retrieval_empty_for_empty_query():
    idx = KnowledgeIndex(KB_DOCS_DIR)
    assert idx.search("  ") == []