"""Markdown chunk reader used to build the RAG index.

A chunk maps to one heading section of a markdown document, e.g. a college's
'intro', the '专业：农学' section, or a professor's '重点科研成就'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")


@dataclass
class Chunk:
    source: str                 # markdown file path (relative to kb/docs)
    doc_title: str              # first H1 title of the file
    section: str                # heading title this chunk belongs to
    level: int = 1
    text: str = ""
    subsections: list[str] = field(default_factory=list)

    @property
    def content(self) -> str:
        head = f"{self.doc_title} > {self.section}" if self.section and self.section != self.doc_title else self.doc_title
        return f"[{head}]\n{self.text}".strip()


def read_documents(docs_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        doc_title = ""
        current: Chunk | None = None
        for raw in lines:
            m = _HEADING.match(raw)
            if m:
                if current is not None:
                    chunks.append(current)
                level, title = len(m.group(1)), m.group(2).strip()
                if level == 1 and not doc_title:
                    doc_title = title
                current = Chunk(
                    source=path.name,
                    doc_title=doc_title or title,
                    section=title,
                    level=level,
                )
                continue
            if current is None:
                continue
            line = raw.strip()
            if line.startswith("- "):
                current.subsections.append(line[2:].strip())
                current.text += line + "\n"
            elif line:
                current.text += line + "\n"
        if current is not None:
            chunks.append(current)
    # drop chunks that are empty or only an empty list marker
    chunks = [c for c in chunks if c.text.strip() or c.subsections]
    return chunks