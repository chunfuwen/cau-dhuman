"""Tests for the TTS / digital-human voice endpoints (offline fallback path)."""
from __future__ import annotations

import sys

import pytest


def test_voices_endpoint(client):
    r = client.get("/api/v1/avatar/voices")
    assert r.status_code == 200
    body = r.json()
    assert body["female"].endswith("Neural")
    assert body["male"].endswith("Neural")


def test_speak_endpoint_returns_audio(client):
    r = client.post("/api/v1/avatar/speak", json={"text": "欢迎报考中国农业大学", "voice": "female"})
    assert r.status_code == 200
    body = r.json()
    assert body["audio_url"].startswith("/audio/")
    assert body["duration"] > 0


def test_tts_synthesize_fallbacks_to_wav_when_edge_unavailable(monkeypatch, tmp_path):
    from app.dh import tts

    # force edge_tts import to fail -> silent wav fallback
    monkeypatch.setitem(sys.modules, "edge_tts", None)
    monkeypatch.setattr(tts, "AUDIO_DIR", tmp_path)

    path, url, duration = tts.synthesize("测试语音", voice="female")
    assert path.exists()
    assert path.suffix == ".wav"
    assert url == f"/audio/{path.name}"
    assert duration > 0


def test_tts_caches_by_content_hash(client, tmp_path):
    from app.dh import tts

    monkeypatch_result = {}

    orig = tts.synthesize_async
    async def fake(text, voice="female"):
        out = tmp_path / "fake.mp3"
        out.write_bytes(b"data")
        return out, f"/audio/{out.name}", 1.0

    tts.synthesize_async = fake
    try:
        _, url1, _ = tts.synthesize("重复的一句话", "female")
        _, url2, _ = tts.synthesize("重复的一句话", "female")
        assert url1 == url2
    finally:
        tts.synthesize_async = orig