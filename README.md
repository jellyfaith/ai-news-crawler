# AI News Crawler

每日自动抓取 AI 领域 RSS 新闻 → DeepSeek 总结 → 生成标准格式 Markdown → 跨仓库推送至 [jellyfaith.github.io](https://github.com/jellyfaith/jellyfaith.github.io)。

## 工作流程

```
RSS 源 ──→ 抓取解析 ──→ 去重过滤 ──→ DeepSeek 总结
                                        │
                                        ↓
                                    生成 .md
                                        │
                                        ↓
                                 推送至博客仓库
```

1. **抓取** — 同时从 HuggingFace、Google AI、Anthropic 获取最新 RSS 条目
2. **去重** — 通过 `processed_state.json` 跳过已经处理的条目（自动清理 30 天前的记录）
3. **总结** — 调用 DeepSeek Chat API，为每条新闻生成中文标题、摘要（≤100 字）、分类标签
4. **生成** — 按标准 YAML frontmatter 格式输出 `.md` 文件
5. **推送** — 克隆博客仓库 → 复制文件 → commit → push

## 生成的 Markdown 格式

```yaml
---
title: "Hugging Face 发布新模型 XYZ"
published: 2026-04-24
draft: false
description: "Hugging Face 发布了最新开源模型 XYZ，在推理任务上表现优异。"
tags: [ai-update, 模型]
---
```

- 文件名由标题自动清洗生成（去特殊字符、空格转连字符、小写）
- 首个标签固定为 `ai-update`

## 目录结构

```
ai-news-crawler/
├── src/
│   ├── config.py               # 环境变量读取 + 配置常量
│   ├── rss_fetcher.py          # RSS 抓取与解析
│   ├── state_manager.py        # 去重状态管理
│   ├── llm_summarizer.py       # DeepSeek API 集成
│   ├── markdown_generator.py   # .md 文件生成
│   ├── git_pusher.py           # 跨仓库 Git 操作
│   └── main.py                 # 工作流编排入口
├── .github/workflows/
│   └── daily-crawl.yml         # GitHub Actions 定时任务
├── requirements.txt
└── README.md
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | DeepSeek（或兼容 OpenAI 协议）的 API 密钥 | **必填** |
| `LLM_BASE_URL` | API 端点地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 模型名 | `deepseek-chat` |
| `MY_BLOG_REPO_TOKEN` | GitHub PAT（需 `repo` 权限） | **必填** |

## 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量
# Windows (cmd)
set LLM_API_KEY=sk-your-key
set MY_BLOG_REPO_TOKEN=ghp_your-token

# Windows (PowerShell)
$env:LLM_API_KEY = "sk-your-key"
$env:MY_BLOG_REPO_TOKEN = "ghp_your-token"

# macOS / Linux
export LLM_API_KEY=sk-your-key
export MY_BLOG_REPO_TOKEN=ghp_your-token

# 3. 运行
python src/main.py
```

## GitHub Actions

工作流 [.github/workflows/daily-crawl.yml](.github/workflows/daily-crawl.yml) 已配置：
- **定时触发** — 每日 UTC 02:00（北京时间 10:00）自动执行
- **手动触发** — 可在 GitHub 仓库 Actions 页面点击 `Run workflow`

### 配置 Secrets

在 GitHub 仓库 **Settings → Secrets and variables → Actions** 添加以下四个 secret：

| Secret | 说明 |
|--------|------|
| `LLM_API_KEY` | DeepSeek API 密钥 |
| `MY_BLOG_REPO_TOKEN` | GitHub PAT（需 `repo` 权限） |
| `LLM_BASE_URL` | (可选) 自定义 API 端点 |
| `LLM_MODEL` | (可选) 自定义模型名 |

## 自定义配置

如需修改 RSS 源、目标分支、文章路径等，编辑 [src/config.py](src/config.py)：

```python
# 修改 RSS 源
RSS_SOURCES = [
    {"name": "HuggingFace", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "Anthropic", "url": "https://www.anthropic.com/blog/rss.xml"},
]

# 目标博客仓库
BLOG_REPO = "jellyfaith/jellyfaith.github.io"
POSTS_DIR = "src/content/posts/"
```
