"""Chat endpoint: RAG retrieval + DeepSeek LLM + optional TTS for the digital human."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app import schemas
from app.config import CHAT_TOP_K, TTS_AUTO
from app.dh import tts as tts_engine

router = APIRouter(prefix="/api/v1", tags=["chat"])


async def _run_tts(text: str, voice: str | None) -> tuple[str | None, float | None]:
    _, url, duration = await tts_engine.synthesize_async(text, voice or "female")
    return url, duration


@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(req: schemas.ChatRequest, request: Request) -> schemas.ChatResponse:
    state = request.app.state

    hits = state.index.search(req.message, top_k=CHAT_TOP_K)
    context = [hit.content for hit in hits]
    messages = state.llm.build_messages(req.message, context, req.history)
    answer = state.llm.chat(messages)

    mode = "online" if state.llm.available else "offline-demo"

    use_tts = TTS_AUTO if req.use_tts is None else req.use_tts
    audio_url = None
    duration = None
    if use_tts:
        audio_url, duration = await _run_tts(answer, req.voice)

    sources = [
        schemas.SourceModel(
            source=h.source,
            doc_title=h.doc_title,
            section=h.section,
            score=h.score,
        )
        for h in hits
    ]
    return schemas.ChatResponse(answer=answer, mode=mode, sources=sources, audio_url=audio_url, duration=duration)