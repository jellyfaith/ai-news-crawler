"""Orchestrate the AI news crawl workflow."""

import logging
import sys
from datetime import date

from src.config import Config
from src.git_pusher import push_files
from src.llm_summarizer import summarize_batch
from src.markdown_generator import generate_md
from src.rss_fetcher import fetch_all
from src.state_manager import StateManager

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    _setup_logging()

    try:
        Config.validate()
    except EnvironmentError as exc:
        logger.error(exc)
        sys.exit(1)

    state = StateManager()

    # 1. 获取所有未处理的 RSS 条目
    all_entries = fetch_all(state)
    if not all_entries:
        logger.info("No new entries — nothing to do.")
        return

    all_entry_ids = [e.id for e in all_entries]

    # 限制只把最新的 10 条发给 LLM，省钱且防报错
    entries_to_process = all_entries[:10]

    logger.info("Fetched %d entries, but only processing the top %d ...", len(all_entries), len(entries_to_process))

    # 2. LLM 处理
    summaries = summarize_batch(entries_to_process)

    # 3. 生成本地的 .md 文件
    output_dir = f".out/{date.today().isoformat()}"
    files = generate_md(entries_to_process, summaries, output_dir)

    # 4. 跨仓库推送到你的博客
    push_files(files)

    # 5. 保存状态（把今天抓到的所有 700 多条历史记录全部标记为已读）
    state.mark_batch(all_entry_ids)
    state.save()

    logger.info("Workflow complete — %d article(s) published.", len(files))


if __name__ == "__main__":
    main()