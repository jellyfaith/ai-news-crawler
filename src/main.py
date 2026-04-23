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

    # 1. Fetch RSS — entries are already limited per source
    all_entries = fetch_all(state)
    if not all_entries:
        logger.info("No new entries — nothing to do.")
        return

    all_entry_ids = [e.id for e in all_entries]

    # 2. LLM: picks 2~3 from these entries and writes full articles
    articles = summarize_batch(all_entries)

    if not articles:
        logger.warning("LLM returned no articles — skipping.")
        return

    # 3. Generate .md files locally
    output_dir = f".out/{date.today().isoformat()}"
    files = generate_md(articles, output_dir)

    # 4. Push to blog repo
    push_files(files)

    # 5. Mark all fetched entries as processed (dedup)
    state.mark_batch(all_entry_ids)
    state.save()

    logger.info("Workflow complete — %d article(s) published.", len(files))


if __name__ == "__main__":
    main()
