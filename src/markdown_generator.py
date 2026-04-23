"""Generate Markdown files with YAML frontmatter."""

import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_FORBIDDEN_RE = re.compile(r'[\\/:*?"<>|]')
_MULTI_DASH_RE = re.compile(r"-{2,}")

# China Standard Time (UTC+8)
_CST = timezone(timedelta(hours=8))


def sanitise_filename(title: str) -> str:
    name = _FORBIDDEN_RE.sub("", title)
    name = re.sub(r"\s+", "-", name.strip())
    name = _MULTI_DASH_RE.sub("-", name)
    name = name.strip("-").lower()
    return name or "untitled"


def generate_md(articles: list[dict], output_dir: str | Path) -> list[Path]:
    """Write one .md file per article dict.

    Each article should have: ``title``, ``description``, ``tags``, ``body``.
    Returns the list of created file paths.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now(_CST).strftime("%Y-%m-%d")
    created: list[Path] = []

    for article in articles:
        title = (article.get("title") or "").strip()
        if not title:
            logger.warning("Skipping article with empty title")
            continue

        description = article.get("description", "")
        raw_tags = article.get("tags", ["ai-update"])
        tags = ["ai-update"] + [t for t in raw_tags if t != "ai-update"]
        body = article.get("body", "")

        tags_yaml = ", ".join(tags)
        frontmatter = (
            "---\n"
            f'title: "{title}"\n'
            f"published: {today}\n"
            "draft: false\n"
            f'description: "{description}"\n'
            f"tags: [{tags_yaml}]\n"
            "---\n"
        )

        content = frontmatter + "\n" + body.strip() + "\n"

        filename = f"{sanitise_filename(title)}.md"
        filepath = output_path / filename
        filepath.write_text(content, encoding="utf-8")
        created.append(filepath)
        logger.info("Generated: %s", filepath)

    return created
