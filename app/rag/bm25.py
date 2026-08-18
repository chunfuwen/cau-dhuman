"""Pure-python Okapi BM25 ranking over tokenized documents."""
from __future__ import annotations

import math
from collections import Counter


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_terms: list[list[str]] = []
        self.doc_freqs: list[Counter] = []
        self.doc_lens: list[int] = []
        self.avgdl = 0.0
        self.idf: dict[str, float] = {}

    def add(self, terms: list[str]) -> int:
        self.doc_terms.append(terms)
        self.doc_freqs.append(Counter(terms))
        self.doc_lens.append(len(terms))
        return len(self.doc_terms) - 1

    def build(self) -> None:
        n = len(self.doc_terms)
        self.avgdl = sum(self.doc_lens) / n if n else 0.0
        df: Counter[str] = Counter()
        for freqs in self.doc_freqs:
            df.update(freqs.keys())
        self.idf = {
            term: math.log(1 + (n - f + 0.5) / (f + 0.5))
            for term, f in df.items()
            if n > 0
        }

    def score(self, doc_id: int, query_terms: list[str]) -> float:
        doc_len = self.doc_lens[doc_id]
        freqs = self.doc_freqs[doc_id]
        denom = self.k1 * (1 - self.b + self.b * doc_len / self.avgdl) if self.avgdl else self.k1
        total = 0.0
        for term in query_terms:
            tf = freqs.get(term, 0)
            if not tf:
                continue
            total += self.idf.get(term, 0.0) * (tf * (self.k1 + 1)) / (tf + denom)
        return total

    def search(self, query_terms: list[str], top_k: int = 5) -> list[tuple[int, float]]:
        scored = [(doc_id, self.score(doc_id, query_terms)) for doc_id in range(len(self.doc_terms))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(d, s) for d, s in scored if s > 0][:top_k]

    def __len__(self) -> int:
        return len(self.doc_terms)