# AI News Crawler

每日自动抓取 AI 领域 RSS 新闻 → DeepSeek 撰写深度长文 → 生成标准格式 Markdown → 跨仓库推送至 [jellyfaith.github.io](https://github.com/jellyfaith/jellyfaith.github.io)。

## 工作流程

```
RSS 源 ──→ 抓取(每源限5条) ──→ 去重 ──→ DeepSeek 挑选2~3条写长文
                                              │
                                              ↓
                                          生成 .md
                                              │
                                              ↓
                                       推送至博客仓库
```

1. **抓取** — 从 HuggingFace、Google AI RSS 获取最新条目（每源限 5 条）
2. **去重** — 通过 `processed_state.json` 跳过已处理条目（30 天自动清理）
3. **创作** — LLM 从新闻中挑选最有价值的 2~3 条，每篇撰写 **400-600 字中文深度文章**（含背景分析、专业点评）
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

## 背景

正文内容...

## 核心分析

更多内容...

## 行业影响

点评...
```

- 文件名由标题自动清洗生成（去特殊字符、空格转连字符、小写）
- 首个标签固定为 `ai-update`
- 正文为 LLM 独立撰写的完整文章，非 RSS 摘要的简单翻译

## 目录结构

```
ai-news-crawler/
├── src/
│   ├── config.py               # 环境变量读取 + 配置常量
│   ├── rss_fetcher.py          # RSS 抓取与 HTML 清洗
│   ├── state_manager.py        # 去重状态管理 (持久化)
│   ├── llm_summarizer.py       # DeepSeek API 集成（生成长文）
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
| `LLM_MODEL` | 模型名 | `deepseek-reasoner` |
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
python -m src.main
```

## 去重机制说明

- 每条 RSS 条目有一个唯一 ID，处理前会检查 `processed_state.json`
- 已存在的 ID 会被跳过，不会重复处理
- 运行结束后新的 ID 会写入该文件（**持久化到磁盘**，不会因重启丢失）
- 30 天前的旧记录自动清理，防止文件无限膨胀

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

编辑 [src/config.py](src/config.py)：

```python
# RSS 源
RSS_SOURCES = [
    {"name": "HuggingFace", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/"},
]

# 每源取前 N 条（默认 5）
MAX_ENTRIES_PER_SOURCE = 5

# LLM 每轮最多写几篇文章（默认 3）
MAX_ARTICLES = 3
```
