"""Shared fixtures: build the KB docs once and expose a FastAPI TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _build_kb_docs() -> None:
    from scripts import build_kb

    build_kb.main()
    # refresh the in-memory index built during app import
    app.state.index.refresh()
    app.state.index.dump(app.state.index.docs_dir.parent / "kb_index.json")


@pytest.fixture(scope="session", autouse=True)
def _offline_tts() -> None:
    from app.dh import tts

    tts.FORCE_OFFLINE = True


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c