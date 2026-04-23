"""LLM integration — send RSS entries to DeepSeek / OpenAI-compatible API."""

import json
import logging

from openai import OpenAI

from src.config import Config
from src.rss_fetcher import FeedEntry

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """\
你是一个 AI 领域的新闻编辑。请为以下 RSS 条目生成中文总结。

每条新闻请返回一个 JSON 对象，包含：
- "title": 中文标题（总结性、吸引人）
- "description": 简短摘要（不超过 100 字）
- "tags": 标签数组（第 1 个固定为 "ai-update"，再加 1-2 个精准分类标签，例如：模型、工具、开源、研究、安全、业界）

最终返回一个 JSON 数组，数组中每个元素对应一条新闻。

示例输出格式：
[
  {{
    "title": "示例标题",
    "description": "这是示例描述。",
    "tags": ["ai-update", "模型"]
  }}
]

请严格按 JSON 格式返回，不要包含其他内容。
"""


def summarize_batch(entries: list[FeedEntry]) -> list[dict]:
    """Send RSS entries to LLM and return structured summaries.

    Returns a list of dicts with keys: title, description, tags.
    """
    if not entries:
        return []

    client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)

    # Build a concise representation of each entry for the LLM
    news_block = "\n\n".join(
        f"[来源: {e.source}]\n标题: {e.title}\n链接: {e.link}\n摘要: {e.summary[:500]}"
        for e in entries
    )

    messages = [
        {"role": "system", "content": _SUMMARIZE_PROMPT},
        {"role": "user", "content": f"请处理以下新闻条目：\n\n{news_block}"},
    ]

    logger.info("Sending %d entries to LLM (%s)", len(entries), Config.LLM_MODEL)

    try:
        resp = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
    except Exception:
        logger.exception("LLM API call failed")
        raise

    raw = resp.choices[0].message.content or "[]"

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON: %s", raw[:300])
        raise

    # Normalise to a list
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise TypeError(f"Expected list from LLM, got {type(data).__name__}")

    # Validate each item
    for item in data:
        if "title" not in item or "description" not in item:
            raise ValueError(f"Missing required keys in LLM response item: {item}")
        if "tags" not in item:
            item["tags"] = ["ai-update"]

    logger.info("LLM summarised %d articles", len(data))
    return data
