"""Configuration — all secrets come from environment variables."""

import os


class Config:
    """Read-only config assembled from environment variables and defaults."""

    # LLM
    LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com/v1"
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "deepseek-chat")

    # Blog repo
    MY_BLOG_REPO_TOKEN: str = os.environ.get("MY_BLOG_REPO_TOKEN", "")
    BLOG_REPO: str = "jellyfaith/jellyfaith.github.io"
    BLOG_REPO_BRANCH: str = "main"
    POSTS_DIR: str = "src/content/posts/"

    # RSS sources
    RSS_SOURCES: list[dict[str, str]] = [
        {"name": "HuggingFace", "url": "https://huggingface.co/blog/feed.xml"},
        {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/"},
        {"name": "Anthropic", "url": "https://www.anthropic.com/blog/rss.xml"},
    ]

    # State
    STATE_FILE: str = "processed_state.json"

    # Temporary working directory for blog repo clone
    BLOG_CLONE_DIR: str = ".blog_repo"

    @classmethod
    def validate(cls) -> None:
        missing = []
        if not cls.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if not cls.MY_BLOG_REPO_TOKEN:
            missing.append("MY_BLOG_REPO_TOKEN")
        if missing:
            raise EnvironmentError(
                f"Missing required environment variable(s): {', '.join(missing)}"
            )
