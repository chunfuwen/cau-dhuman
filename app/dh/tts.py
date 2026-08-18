"""Text-to-speech engine.

Uses Microsoft Edge TTS (edge-tts) to synthesize natural Chinese speech.
Audio files are cached by content hash under the audio/ directory. If
edge-tts is unavailable or the network fails, a short silent-ish WAV is
produced at `audio/<hash>.wav` so the conversation flow (and the digital
human's speaking animation) still works in offline/demo mode.
"""
from __future__ import annotations

import asyncio
import hashlib
import wave
from pathlib import Path

from app.config import AUDIO_DIR

VOICES = {
    "female": "zh-CN-XiaoxiaoNeural",  # 晓晓
    "male": "zh-CN-YunyangNeural",     # 云扬
}

DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "+0Hz"

# When True, never contact the edge-tts network service (used by tests and
# offline deployments). A short silent wav is generated instead.
FORCE_OFFLINE = False


def _make_silent_wav(path: Path, seconds: float = 0.4) -> Path:
    """Fallback audio so playback/avatar animations always work offline."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            frames = b"\x00\x00" * int(16000 * seconds)
            w.writeframes(frames)
    return path


def _cache_path(text: str, voice: str) -> Path:
    digest = hashlib.sha256(f"{voice}:{text}".encode("utf-8")).hexdigest()[:20]
    return AUDIO_DIR / f"{voice}_{digest}.mp3"


async def synthesize_async(text: str, voice: str = "female", rate: str = DEFAULT_RATE) -> tuple[Path, str, float]:
    """Return (audio_path, relative_url, duration_seconds)."""
    voice_key = voice if voice in VOICES else "female"
    voice_name = VOICES[voice_key]
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(text, voice_key)
    if path.exists():
        return path, f"/audio/{path.name}", _estimate_duration(text)

    try:
        if FORCE_OFFLINE:
            raise RuntimeError("TTS offline routing enabled")
        import edge_tts

        communicate = edge_tts.Communicate(text, voice_name, rate=rate)
        await asyncio.wait_for(communicate.save(str(path)), timeout=30)
    except Exception:
        path = _make_silent_wav(path.with_suffix(".wav"), seconds=max(0.4, len(text) / 6))
        return path, f"/audio/{path.name}", _estimate_duration(text)

    if not path.exists():  # edge_tts failed silently
        path = _make_silent_wav(path.with_suffix(".wav"), seconds=max(0.4, len(text) / 6))
        return path, f"/audio/{path.name}", _estimate_duration(text)
    return path, f"/audio/{path.name}", _estimate_duration(text)


def synthesize(text: str, voice: str = "female") -> tuple[Path, str, float]:
    return asyncio.run(synthesize_async(text, voice))


def _estimate_duration(text: str) -> float:
    """Heuristic duration for progressive estimation (Chinese ~4 chars/sec)."""
    return max(0.5, len(text) / 4.0)