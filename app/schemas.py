"""API request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, Any]] = Field(default_factory=list)
    voice: str | None = None
    use_tts: bool | None = None


class SourceModel(BaseModel):
    source: str
    doc_title: str
    section: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    mode: str = "online"
    sources: list[SourceModel] = Field(default_factory=list)
    audio_url: str | None = None
    duration: float | None = None


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    voice: str = "female"


class TtsResponse(BaseModel):
    audio_url: str
    duration: float


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_connected: bool
    retrieval: dict[str, int]