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

    # 1. Fetch RSS entries (unprocessed only)
    entries = fetch_all(state)
    if not entries:
        logger.info("No new entries — nothing to do.")
        return

    logger.info("Processing %d new entries …", len(entries))

    # 2. LLM summarisation
    summaries = summarize_batch(entries)

    # 3. Generate .md files in a temporary local directory
    output_dir = f".out/{date.today().isoformat()}"
    files = generate_md(entries, summaries, output_dir)

    # 4. Push to blog repo
    push_files(files)

    # 5. Persist dedup state
    state.mark_batch([e.id for e in entries])
    state.save()

    logger.info("Workflow complete — %d article(s) published.", len(files))


if __name__ == "__main__":
    main()
