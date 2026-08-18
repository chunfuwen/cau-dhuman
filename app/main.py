"""CAU Digital Human Platform - FastAPI application entrypoint.

Run with:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import avatar, chat, knowledge
from app.llm.deepseek import LLMClient
from app.rag.retriever import KnowledgeIndex, build_index

app = FastAPI(
    title="中国农业大学数字人模拟平台",
    version="1.0.0",
    description="RAG 知识库 + DeepSeek LLM + 数字人与语音播报",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_school_data() -> dict:
    return json.loads(config.KB_DATA_PATH.read_text(encoding="utf-8"))


app.state.school_data = _load_school_data()
app.state.index = build_index(config.KB_DOCS_DIR)
app.state.index.dump(config.KB_INDEX_PATH)
app.state.llm = LLMClient()

app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(avatar.router)
app.mount("/audio", StaticFiles(directory=config.AUDIO_DIR), name="audio")

STATIC = config.ROOT / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/healthz")
def health() -> dict:
    dense = getattr(app.state.index, "dense", None)
    return {
        "status": "ok",
        "llm_connected": app.state.llm.available,
        "retrieval": {
            "n_documents": len({c.source for c in app.state.index.chunks}),
            "n_chunks": len(app.state.index.chunks),
        },
        "dense": {"n_chunks": dense.size if dense else 0},
    }