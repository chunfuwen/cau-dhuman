"""Digital-human companion endpoints: TTS audio synthesis."""
from __future__ import annotations

from fastapi import APIRouter

from app import schemas
from app.dh import tts as tts_engine

router = APIRouter(prefix="/api/v1", tags=["avatar"])


@router.post("/avatar/speak", response_model=schemas.TtsResponse)
async def speak(req: schemas.TtsRequest) -> schemas.TtsResponse:
    _, url, duration = await tts_engine.synthesize_async(req.text, req.voice)
    return schemas.TtsResponse(audio_url=url, duration=duration)


@router.get("/avatar/voices")
async def voices() -> dict[str, str]:
    return tts_engine.VOICES