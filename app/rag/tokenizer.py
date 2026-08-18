"""Chinese tokenizer for the RAG engine.

Uses jieba when available and falls back to a coarse bigram/character
tokenizer so the platform can still run in minimal environments.
"""
from __future__ import annotations

try:
    import jieba

    jieba.setLogLevel(60)  # silence the INFO preamble
    _HAS_JIEBA = True
except Exception:  # pragma: no cover - exercised only in exotic envs
    _HAS_JIEBA = False

import re

_WORD_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]+")
_CJK_BIGRAMS = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """Return lower-case tokens for the given text.

    CJK words are kept whole AND exploded into character bigrams to improve
    recall when a query uses slightly different segmentation than the docs.
    """
    text = (text or "").lower()
    words = []
    if _HAS_JIEBA:
        import jieba

        words = [w for w in jieba.cut(text) if w and not w.isspace()]
    else:  # pragma: no cover - fallback for minimal environments
        words = _WORD_RE.findall(text)

    toks: list[str] = []
    for w in words:
        if re.fullmatch(r"[a-zA-Z0-9_]+", w):
            toks.append(w)
            continue
        toks.append(w)
        chars = _CJK_BIGRAMS.findall(w)
        if len(chars) >= 2:
            toks.extend("".join(chars[i : i + 2]) for i in range(len(chars) - 1))
    return toks