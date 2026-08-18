"""Tests for the RAG + LLM chat endpoint (offline mock mode, no API key)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)


def test_chat_returns_rag_grounded_answer(client):
    r = client.post(
        "/api/v1/chat",
        json={"message": "介绍一下中国农业大学的学院构成", "use_tts": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "offline-demo"
    assert body["answer"]
    assert len(body["sources"]) > 0
    assert any("中国农业大学" in s["doc_title"] for s in body["sources"]) or any(
        "学院" in s["doc_title"] for s in body["sources"]
    )


def test_chat_with_tts_returns_audio(client):
    r = client.post(
        "/api/v1/chat",
        json={"message": "农学院的导师是谁", "voice": "female", "use_tts": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["audio_url"]
    # offline: fallback wav is served from /audio
    resp = client.get(body["audio_url"])
    assert resp.status_code == 200


def test_chat_unknown_query_graceful(client):
    r = client.post(
        "/api/v1/chat",
        json={"message": "食堂今晚有哪些菜", "use_tts": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]  # still returns a helpful mock reply


def test_chat_rejects_empty_message(client):
    r = client.post("/api/v1/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_accepts_history(client):
    r = client.post(
        "/api/v1/chat",
        json={
            "message": "再具体一点",
            "history": [
                {"role": "user", "content": "介绍一下农学院"},
                {"role": "assistant", "content": "农学院主要研究作物学。"},
            ],
            "use_tts": False,
        },
    )
    assert r.status_code == 200