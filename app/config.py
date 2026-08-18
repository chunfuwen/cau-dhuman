"""Central configuration. Values come from environment or a local .env file."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_loaded = False


def _load_dotenv() -> None:
    """Minimal .env parser (KEY=VALUE lines, # comments, no interpolation)."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def get_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- derived settings ---------------------------------------------------
DEEPSEEK_API_KEY = get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = get("DEEPSEEK_MODEL", "deepseek-chat")

KB_DATA_PATH = ROOT / "app" / "kb" / "school_data.json"
KB_DOCS_DIR = ROOT / "app" / "kb" / "docs"
KB_INDEX_PATH = ROOT / "app" / "kb" / "kb_index.json"
AUDIO_DIR = ROOT / "audio"
DEFAULT_TTS_VOICE = get("TTS_VOICE", "female")
TTS_AUTO = get_bool("TTS_AUTO", True)
CHAT_TOP_K = int(get("RAG_TOP_K", "4"))
DENSE_TOP_K = int(get("DENSE_TOP_K", "2"))
VECTORSTORE_DIR = ROOT / "app" / "kb" / "vectorstore"
HOST = get("HOST", "0.0.0.0")
PORT = int(get("PORT", "8000"))