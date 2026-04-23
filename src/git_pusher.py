"""Cross-repository git operations — clone blog repo, copy files, commit, push."""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from src.config import Config

logger = logging.getLogger(__name__)


def push_files(local_files: list[Path]) -> None:
    """Clone the blog repo, place .md files into ``POSTS_DIR``, then commit & push.

    If *local_files* is empty the function is a no-op.
    """
    if not local_files:
        logger.info("No files to push — skipping.")
        return

    clone_dir = Path(Config.BLOG_CLONE_DIR)

    # Clean up any leftover from a previous run
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    repo_url = _authed_url()

    logger.info("Cloning blog repo %s ...", Config.BLOG_REPO)
    _run_git(["clone", "--depth", "1", repo_url, str(clone_dir)], cwd=Path.cwd())

    posts_dir = clone_dir / Config.POSTS_DIR
    posts_dir.mkdir(parents=True, exist_ok=True)

    for f in local_files:
        dest = posts_dir / f.name
        shutil.copy2(f, dest)
        logger.debug("Copied %s -> %s", f.name, dest)

    # Check if there are changes
    _run_git(["add", "."], cwd=clone_dir)
    status = _run_git(["status", "--porcelain"], cwd=clone_dir, capture=True)
    if not status.strip():
        logger.info("No new changes — skipping commit and push.")
        shutil.rmtree(clone_dir)
        return

    date_str = _get_date_str()
    commit_msg = f"🤖 auto-update: ai-news-crawler {date_str}"
    _run_git(["commit", "-m", commit_msg], cwd=clone_dir)

    logger.info("Pushing to %s ...", Config.BLOG_REPO)
    _run_git(["push"], cwd=clone_dir)

    # Cleanup
    shutil.rmtree(clone_dir)
    logger.info("Push complete (cloned repo cleaned up).")


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _authed_url() -> str:
    """Return HTTPS URL with embedded token for authentication."""
    return (
        f"https://x-access-token:{Config.MY_BLOG_REPO_TOKEN}"
        f"@github.com/{Config.BLOG_REPO}.git"
    )


def _get_date_str() -> str:
    from datetime import date
    return date.today().isoformat()


def _run_git(args: list[str], *, cwd: Path, capture: bool = False) -> str:
    """Run a git command and return stdout.

    Raises ``RuntimeError`` on non-zero exit.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()
