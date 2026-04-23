"""Generate Markdown files with YAML frontmatter."""

import logging
import re
from datetime import date
from pathlib import Path

from src.rss_fetcher import FeedEntry

logger = logging.getLogger(__name__)

# Characters forbidden in Windows / cross-platform filenames
_FORBIDDEN_RE = re.compile(r'[\\/:*?"<>|]')
_MULTI_DASH_RE = re.compile(r"-{2,}")


def sanitise_filename(title: str) -> str:
    """Convert *title* to a safe filename.

    - Replace forbidden characters with empty string
    - Replace whitespace runs with a single hyphen
    - Collapse multiple hyphens
    - Strip leading/trailing hyphens
    - Lowercase
    """
    name = _FORBIDDEN_RE.sub("", title)
    name = re.sub(r"\s+", "-", name.strip())
    name = _MULTI_DASH_RE.sub("-", name)
    name = name.strip("-").lower()
    return name or "untitled"


def generate_md(
    entries: list[FeedEntry],
    summaries: list[dict],
    output_dir: str | Path,
) -> list[Path]:
    """Write one .md file per entry+summary pair.

    Returns the list of created file paths.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    created: list[Path] = []

    for entry, summary in zip(entries, summaries, strict=True):
        title = summary["title"]
        description = summary.get("description", "")
        raw_tags = summary.get("tags", ["ai-update"])
        # Ensure first tag is always ai-update
        tags = ["ai-update"] + [t for t in raw_tags if t != "ai-update"]

        # Build YAML frontmatter
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

        # Body content
        body = f"\n## {title}\n\n"
        body += f"{description}\n\n"
        body += f"> 原文链接：[{entry.title}]({entry.link})\n"
        body += f"> 来源：{entry.source}\n"

        content = frontmatter + body

        # Write file
        filename = f"{sanitise_filename(title)}.md"
        filepath = output_path / filename
        filepath.write_text(content, encoding="utf-8")
        created.append(filepath)
        logger.info("Generated: %s", filepath)

    return created
