# RSS Aggregator

RSS 订阅内容收集器 — 抓取、解析、存储 RSS 订阅源，并支持抓取文章全文内容和图片。

## 功能特性

- **RSS 源管理** — 添加、删除、列出、更新 RSS 源
- **内容抓取** — 支持 RSS 2.0、Atom 格式
- **全文提取** — 抓取文章 URL 背后的完整正文，HTML 转 Markdown
- **图片保存** — 从 HTML 提取正文图片，下载到本地，Markdown 中替换为本地路径
- **JS 渲染** — 可选 Playwright 支持防爬网站（如 Twitter）
- **本地存储** — SQLite 数据库存储，图片存文件系统
- **过滤搜索** — 按标签、时间、关键词过滤
- **格式化输出** — Markdown 和 JSON 格式
- **导入导出** — 支持 OPML 格式
- **定时任务** — Crontab 后台自动抓取

## 安装

```bash
git clone <repository-url>
cd rss-aggregator
uv sync
```

## 使用流程

典型使用流程：

```
添加 RSS 源 → 抓取订阅内容 → 浏览文章列表 → 抓取感兴趣文章的全文 → 阅读
```

> 在 Openclaw 、 claudecode 等agents中使用
> 使用 `uv run --project /Users/li/projects/rss-aggregator rss-aggregator xxxx` 命令使用rss-aggregator工具
> `uv run --project <rss-aggregator-project-path> rss-aggregator <command>`

### 1. 添加 RSS 源

```bash
# 添加源（名称、标签、抓取间隔均为可选）
rss-aggregator source add https://hnrss.org/newest --name "Hacker News" --tags "tech,news"

# 从 OPML 文件批量导入
rss-aggregator import feeds.opml
```

### 2. 抓取订阅内容

```bash
# 抓取所有源的最新内容
rss-aggregator fetch

# 只抓取指定源
rss-aggregator fetch 1

# 限制每个源最多抓取的文章数
rss-aggregator fetch --limit 10
```

### 3. 浏览文章

```bash
# 查看最新文章（默认最多 20 篇）
rss-aggregator read

# 只看未读文章
rss-aggregator read --unread

# 按源、标签、时间过滤
rss-aggregator read --source 1 --tag tech --since 2024-01-01 --limit 50

# 搜索文章
rss-aggregator search "python"

# JSON 格式输出（便于程序处理）
rss-aggregator read --format json
```

### 4. 抓取全文内容

```bash
# 按 URL 抓取全文（结果自动缓存到本地）
rss-aggregator fetch-content https://example.com/some-article

# 强制重新抓取，跳过缓存
rss-aggregator fetch-content https://example.com/some-article --no-cache

# 对 JS 渲染页面使用 Playwright
rss-aggregator fetch-content https://example.com/article --playwright

# 抓取后输出到文件
rss-aggregator fetch-content https://example.com/article --output article.md
```

全文抓取会自动：
- 提取文章正文，转换为 Markdown 格式
- 从 HTML 中提取正文图片，下载到 `~/.rss-aggregator/images/`
- 替换 Markdown 中的图片链接为本地路径
- HTML 中有但正文 Markdown 中未引用的图片，追加到正文末尾
- 缓存抓取结果到 `~/.rss-aggregator/content/`，同一 URL 默认使用缓存

### 5. 阅读全文

```bash
# 读取文章时，已抓取全文的文章会展示完整内容（而非摘要）
rss-aggregator read --source 1
```

### 6. 标记已读

```bash
rss-aggregator mark-read 42
```

### 7. 定时自动抓取

```bash
# 安装定时任务
rss-aggregator cron install --interval 30

# 查看定时任务状态
rss-aggregator cron status

# 移除定时任务
rss-aggregator cron remove
```

## CLI 命令参考

### 全局选项

```
rss-aggregator --version    # 显示版本号
rss-aggregator --help       # 显示帮助信息
```

### source — RSS 源管理

| 命令 | 说明 |
|------|------|
| `source add <url> [-n NAME] [-t TAGS] [-i INTERVAL]` | 添加 RSS 源 |
| `source remove <source_id>` | 删除 RSS 源及其所有文章 |
| `source list [-f table\|json]` | 列出所有 RSS 源 |
| `source update <source_id> [-n NAME] [-t TAGS] [-i INTERVAL]` | 更新源配置 |

### 内容操作

| 命令 | 说明 |
|------|------|
| `fetch [source_id] [-l LIMIT]` | 抓取 RSS 内容 |
| `read [-s SOURCE] [-t TAG] [--since DATE] [-l LIMIT] [--unread] [-f markdown\|json]` | 读取文章列表 |
| `search <keyword> [-s SOURCE] [-l LIMIT] [-f markdown\|json]` | 搜索文章 |
| `mark-read <article_id>` | 标记文章为已读 |
| `fetch-content <url> [-p] [-o FILE] [--no-cache]` | 抓取 URL 全文内容（带本地缓存） |

**fetch-content 参数说明：**

| 参数 | 说明 |
|------|------|
| `<url>` | 文章 URL 链接 |
| `--playwright, -p` | 使用 Playwright 渲染 JS 页面（需额外安装） |
| `--output, -o FILE` | 将抓取结果写入文件 |
| `--no-cache` | 跳过缓存，强制重新抓取 |

### 导入导出

| 命令 | 说明 |
|------|------|
| `import <file>` | 导入 OPML 文件 |
| `export [-f opml\|json] [-o FILE]` | 导出数据 |

### cron — 定时任务

| 命令 | 说明 |
|------|------|
| `cron install [-i INTERVAL]` | 安装 crontab 定时任务（间隔单位：分钟） |
| `cron remove` | 移除定时任务 |
| `cron status` | 查看定时任务状态 |

## 输出格式

### Markdown 格式（默认）

```markdown
# RSS Update - 2024-01-15 10:30

## Hacker News
**共 5 篇文章**

### [文章标题](https://example.com/article)
- **作者**: John Doe | **发布时间**: 2024-01-15 10:30 | **标签**: technology

（全文内容或摘要）

---
```

### JSON 格式

```json
{
  "fetched_at": "2024-01-15T10:30:00",
  "count": 5,
  "articles": [
    {
      "id": 1,
      "title": "文章标题",
      "url": "https://example.com/article",
      "author": "John Doe",
      "published_at": "2024-01-15T10:30:00",
      "summary": "文章摘要",
      "content": "全文内容（如已抓取）",
      "tags": ["technology"],
      "is_read": false
    }
  ]
}
```

## 数据存储

| 内容 | 路径 |
|------|------|
| 数据库 | `~/.rss-aggregator/data.db` |
| 文章图片 | `~/.rss-aggregator/images/` |
| 全文缓存 | `~/.rss-aggregator/content/` |

## 开发

### 运行测试

```bash
uv run pytest tests/ -v
```

### 项目结构

```
rss-aggregator/
├── rss_aggregator/
│   ├── __init__.py
│   ├── cli.py          # CLI 命令定义
│   ├── models.py       # 数据模型
│   ├── database.py     # SQLite 操作
│   ├── fetcher.py      # RSS 抓取解析
│   ├── scraper.py      # 全文内容抓取 + 图片下载
│   ├── exporter.py     # 格式化输出
│   ├── importer.py     # OPML 导入导出
│   └── scheduler.py    # 定时任务管理
├── tests/
├── main.py
└── pyproject.toml
```

### 依赖

| 依赖 | 用途 |
|------|------|
| feedparser | RSS/Atom 解析 |
| httpx | HTTP 客户端 |
| click | CLI 框架 |
| rich | 终端美化输出 |
| trafilatura | 全文内容提取 + HTML→Markdown |
| lxml | HTML 解析（图片 URL 提取） |
| playwright（可选） | JS 渲染页面抓取 |

安装 Playwright 支持：

```bash
uv add --optional-group playwright playwright
playwright install chromium
```
