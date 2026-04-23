"""LLM integration — send RSS entries to DeepSeek / OpenAI-compatible API.

Returns full-length articles, not just summaries.
"""

import json
import logging

from openai import OpenAI

from src.config import Config
from src.retriever import fetch_article
from src.rss_fetcher import FeedEntry

logger = logging.getLogger(__name__)

_MAX_OUTPUT_TOKENS = 8192
"""Leave enough headroom for 2-3 × ~1500 word articles in JSON."""

# Note: the word "JSON" in the prompt is required by json_object response mode.
_PROMPT = """\
你是一个资深的 AI 领域技术编辑。你的任务是从提供的新闻素材中挑选最有价值的 2-3 条，为每条撰写一篇深度中文长文。

## 重要约束
- **必须严格基于下方提供的「原文内容」写文章，不得编造训练数据中没有的信息**
- 如果原文内容不足以支撑完整文章，就如实围绕已有的信息写，不要无中生有
- 每条文章约 1500 字中文

## 文章结构要求
每篇文章应包含：背景介绍 → 核心内容分析 → 行业影响/专业点评
- **文末必须附上原文链接**（引用下方提供的原始链接，使用 Markdown 格式 `[来源](url)`）

## 输出格式
输出 JSON 对象，包含 articles 数组，每个元素：
- "title": 中文标题（总结性、吸引人）
- "description": 一句话摘要（不超过 100 字）
- "tags": 标签数组，第 1 个固定为 "ai-update"，再加 1-2 个分类标签（如：模型、工具、开源、研究、安全、业界）
- "body": 完整的文章正文（约 1500 字中文，Markdown 格式，用小标题分段，文末附原文链接）

示例：
{
  "articles": [
    {
      "title": "示例标题",
      "description": "一句话摘要",
      "tags": ["ai-update", "模型"],
      "body": "## 背景\\n\\n正文内容...\\n\\n## 分析\\n\\n更多内容...\\n\\n---\\n[来源](https://...)"
    }
  ]
}
"""


def summarize_batch(entries: list[FeedEntry]) -> list[dict]:
    """Send RSS entries to LLM and return full-length article dicts.

    Each returned dict contains: title, description, tags, body.
    Returns an empty list when *entries* is empty.
    """
    if not entries:
        return []

    client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)

    # ------------------------------------------------------------------
    # 1. Fetch full article content for each entry (RAG source material)
    # ------------------------------------------------------------------
    logger.info("Fetching full article content for %d entries …", len(entries))
    news_parts: list[str] = []
    for entry in entries:
        full_text = fetch_article(entry.link)
        content = (
            f"[来源: {entry.source}]\n"
            f"标题: {entry.title}\n"
            f"链接: {entry.link}\n"
            f"--- 原文内容 ---\n"
            f"{full_text or entry.summary}\n"
            f"--- 原文结束 ---\n"
        )
        news_parts.append(content)

    news_block = "\n\n".join(news_parts)

    # ------------------------------------------------------------------
    # 2. Call LLM
    # ------------------------------------------------------------------
    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": f"请根据以下新闻素材撰写文章（务必基于原文，不要编造）：\n\n{news_block}"},
    ]

    logger.info(
        "Sending ~%d entries to LLM (%s), max_tokens=%s",
        len(entries),
        Config.LLM_MODEL,
        _MAX_OUTPUT_TOKENS,
    )

    try:
        resp = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=_MAX_OUTPUT_TOKENS,
            response_format={"type": "json_object"},
        )
    except Exception:
        logger.exception("LLM API call failed")
        raise

    raw = resp.choices[0].message.content or '{"articles": []}'

    # ------------------------------------------------------------------
    # 3. Parse JSON with repair fallback for truncated output
    # ------------------------------------------------------------------
    data = _parse_json_safe(raw)
    if data is None:
        logger.error("Failed to parse LLM output. Raw snippet:\n%s", raw[:500])
        return []

    articles = data if isinstance(data, list) else data.get("articles", [data])
    if not isinstance(articles, list):
        articles = [articles]

    # Validate
    valid = []
    for item in articles:
        if not isinstance(item, dict) or "title" not in item or "body" not in item:
            logger.warning("Skipping malformed article: %s", str(item)[:100])
            continue
        if "tags" not in item or not item["tags"]:
            item["tags"] = ["ai-update"]
        if "description" not in item:
            item["description"] = ""
        valid.append(item)

    logger.info("LLM generated %d articles", len(valid))
    return valid


def _parse_json_safe(raw: str) -> dict | list | None:
    """Try ``json.loads`` first, fall back to ``json_repair``.

    Returns ``None`` when both fail.
    """
    # Fast path — standard parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback — repair truncated JSON
    try:
        from json_repair import repair_json  # type: ignore[import-untyped]
        repaired = repair_json(raw)
        return json.loads(repaired)
    except Exception:
        return None
