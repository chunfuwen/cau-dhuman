"""Evaluate the project's RAG pipeline with RAGAS metrics.

Runs the real pipeline (KnowledgeIndex hybrid retrieval + LLMClient) over a
small golden question set, then scores each sample with RAGAS 0.4.x metrics:

    - Faithfulness               (LLM as judge, no reference)
    - AnswerRelevancy            (embeddings + LLM, no reference)
    - FactualCorrectness         (LLM + reference)
    - ContextRecall              (LLM + reference, retrieval coverage)
    - ContextPrecisionWithRef    (LLM + reference, retrieval ranking)

The evaluator LLM is DeepSeek (OpenAI-compatible) configured from .env; the
embedding model is the same sentence-transformers model used for the dense
vectorstore. A report is written to evals/experiments/.

Run:
    python scripts/evaluate_rag.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ragas.embeddings.base import BaseRagasEmbedding
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecisionWithReference,
    ContextRecall,
    FactualCorrectness,
    Faithfulness,
)

from app.config import CHAT_TOP_K, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, KB_DOCS_DIR
from app.rag.retriever import KnowledgeIndex

OUT_DIR = ROOT / "evals" / "experiments"

# Golden questions + reference answers grounded in the knowledge base / PDF.
EVAL_SET = [
    {
        "user_input": "中国农业大学是哪一年创建的？",
        "reference": "中国农业大学创建于1905年。",
    },
    {
        "user_input": "中国农业大学目前设有多少个学院？",
        "reference": "中国农业大学目前设有20个学院。",
    },
    {
        "user_input": "中国农业大学的校训是什么？",
        "reference": "中国农业大学的校训是'解民生之多艰，育天下之英才'。",
    },
    {
        "user_input": "农学院有哪些本科专业？",
        "reference": "农学院设有农学和种子科学与工程等专业。",
    },
    {
        "user_input": "张福锁院士的主要研究方向是什么？",
        "reference": "张福锁院士主要从事植物营养与养分资源管理研究，创立了'养分资源综合管理'理论与'科技小院'培养模式。",
    },
    {
        "user_input": "中国农业大学在校生规模如何？",
        "reference": "中国农业大学现有在校生4万余人，其中本科生与研究生约各半。",
    },
    {
        "user_input": "Which major shows the strongest enrollment growth in the multimodal document?",
        "reference": "Food Science shows the strongest growth at 12.0%.",
    },
    {
        "user_input": "What content does the multimodal.pdf document contain?",
        "reference": "The document contains text, an image (a bar chart of student counts by major), and an enrollment summary table.",
    },
]


class CAUEmbeddings(BaseRagasEmbedding):
    """Modern RAGAS embedding adapter over the project's embedder."""

    def embed_text(self, text: str, **kwargs) -> "list[float]":
        from app.rag import embedder

        return embedder.embed_one(text)

    async def aembed_text(self, text: str, **kwargs) -> "list[float]":
        from app.rag import embedder

        return embedder.embed_one(text)


def run_pipeline(index: KnowledgeIndex) -> "list[dict]":
    from app.llm.deepseek import LLMClient

    llm = LLMClient()
    rows: list[dict] = []
    for case in EVAL_SET:
        hits = index.search(case["user_input"], top_k=CHAT_TOP_K)
        contexts = [h.content for h in hits]
        messages = llm.build_messages(case["user_input"], contexts)
        answer = llm.chat(messages)
        rows.append(
            {
                "user_input": case["user_input"],
                "reference": case["reference"],
                "retrieved_contexts": contexts,
                "response": answer,
            }
        )
        print(f"  [done] {case['user_input'][:40]}")
    return rows


async def score_all(metrics: "list[tuple[str, object, list[str]]]", rows: "list[dict]") -> "list[dict]":
    """Run each metric's ascore per sample; metrics = [(name, instance, fields)]."""
    scored: list[dict] = []
    for row in rows:
        per: dict = {"user_input": row["user_input"]}
        for name, metric, fields in metrics:
            kwargs = {f: row[f] for f in fields}
            result = await metric.ascore(**kwargs)
            per[name] = result.value
        scored.append(per)
    return scored


def main() -> None:
    if not DEEPSEEK_API_KEY:
        raise SystemExit("DEEPSEEK_API_KEY is required for RAGAS evaluation (needs an LLM judge).")

    print("building knowledge index (BM25 + dense)...")
    index = KnowledgeIndex(KB_DOCS_DIR)

    print(f"running RAG pipeline over {len(EVAL_SET)} questions...")
    rows = run_pipeline(index)
    print(f"collected {len(rows)} samples")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    evaluator_llm = llm_factory(DEEPSEEK_MODEL, provider="openai", client=client, max_tokens=4096)
    evaluator_embeddings = CAUEmbeddings()

    metrics = [
        ("faithfulness", Faithfulness(llm=evaluator_llm), ["user_input", "response", "retrieved_contexts"]),
        ("answer_relevancy", AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings), ["user_input", "response"]),
        ("factual_correctness", FactualCorrectness(llm=evaluator_llm), ["response", "reference"]),
        ("context_recall", ContextRecall(llm=evaluator_llm), ["user_input", "retrieved_contexts", "reference"]),
        ("context_precision", ContextPrecisionWithReference(llm=evaluator_llm), ["user_input", "reference", "retrieved_contexts"]),
    ]

    print("evaluating with RAGAS (DeepSeek as judge)...")
    scored = asyncio.run(score_all(metrics, rows))
    names = [m[0] for m in metrics]

    print("\n=== per-sample scores ===")
    header = f"{'question':<46}" + "".join(f"{n:>22}" for n in names)
    print(header)
    for per in scored:
        q = (per["user_input"] or "")[:46]
        print(f"{q:<46}" + "".join(f"{per[n]:>22.3f}" for n in names))

    aggregate = {n: round(sum(p[n] for p in scored) / len(scored), 4) for n in names}
    print("\n=== aggregate (mean) ===")
    for n in names:
        print(f"  {n}: {aggregate[n]}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "ragas_report.json"
    out.write_text(
        json.dumps(
            {
                "model": DEEPSEEK_MODEL,
                "n_samples": len(rows),
                "aggregate": aggregate,
                "per_sample": scored,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nreport written to {out}")


if __name__ == "__main__":
    main()