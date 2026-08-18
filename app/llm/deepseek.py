"""DeepSeek LLM client (OpenAI-compatible) with an offline mock fallback.

The mock is used whenever no DEEPSEEK_API_KEY is configured or the upstream
call fails, and lets the whole platform be demoed/tested without network.
"""
from __future__ import annotations

import os
from typing import Any

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
        self.model = model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
        self._client: Any | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat(self, messages: list[dict], temperature: float = 0.4, max_tokens: int = 1024) -> str:
        if not self.available:
            return mock_answer(messages)
        try:
            resp = self._get_client().chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            return mock_answer(messages)

    def build_messages(self, question: str, context: list[str], history: list[dict] | None = None) -> list[dict]:
        system = (
            "你是一个中国农业大学（CAU）的数字人招生与校园智能助手，名字叫'农小田'。"
            "你负责在知识库范围内回答关于学校概况、学院与院系设置、专业与方向、重点学科、"
            "主要课程、导师介绍和重点科研成就等问题。\n"
            "规则：\n"
            "1. 优先依据下方【知识库片段】作答，不要编造知识库之外的事实。\n"
            "2. 回答使用简体中文，条理清晰、亲切友好，语气像一位熟悉的学长/学姐。\n"
            "3. 如果知识库中没有相关信息，请如实说明'知识库中没有找到该信息'，并提出相关建议。\n"
            "4. 引用知识库内容时，可在句末用(来源：文件名)标注。\n"
        )
        messages: list[dict] = [{"role": "system", "content": system}]
        for msg in (history or [])[-6:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        if context:
            system_for_user = "\n\n【知识库片段】\n" + "\n---\n".join(context)
            # put the retrieved context into the last user message for clarity
            messages.append({"role": "user", "content": system_for_user})
        messages.append({"role": "user", "content": f"问题：{question}\n请给出完整、友好、分点的回答。"})
        return messages


def mock_answer(messages: list[dict]) -> str:
    """Offline fallback that synthesises a polite answer from any context."""
    context = ""
    for m in messages:
        if m.get("role") == "user" and "【知识库片段】" in m.get("content", ""):
            context = m["content"].split("【知识库片段】", 1)[1]
            break

    lines = []
    if context:
        for block in context.split("---"):
            block = block.strip()
            if not block:
                continue
            first_line, rest = block.split("\n", 1) if "\n" in block else (block, "")
            lines.append(f"- {first_line.strip()}")
            if rest:
                snippet = rest.strip().split("\n")[0]
                if snippet and snippet not in {first_line.strip()}:
                    lines.append(f"  {snippet}")
    if not lines:
        lines = ["- 当前知识库中暂无该问题的直接答案，建议您换个说法再问我，或访问中国农业大学官网查阅更多信息。"]

    header = "（离线演示模式·未配置 DeepSeek API Key，以下为基于知识库检索的要点回复）"
    return header + "\n" + "\n".join(lines)