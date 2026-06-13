# RSS Aggregator

RSS订阅内容收集器 - 为OpenCalw提供RSS数据

## 功能特性

- **RSS源管理**: 添加、删除、列出、更新RSS源
- **内容抓取**: 支持RSS 2.0、Atom格式
- **本地存储**: SQLite数据库存储
- **过滤搜索**: 按标签、时间、关键词过滤
- **格式化输出**: Markdown和JSON格式
- **导入导出**: 支持OPML格式
- **定时任务**: 后台自动抓取

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd rss-aggregator

# 安装依赖
uv sync
```

## 使用方法

### RSS源管理

```bash
# 添加RSS源
rss-aggregator source add https://hnrss.org/newest --name "Hacker News" --tags "tech,news"

# 列出所有源
rss-aggregator source list

# 更新源配置
rss-aggregator source update 1 --name "HN" --interval 30

# 删除源
rss-aggregator source remove 1
```

### 内容操作

```bash
# 抓取所有源的最新内容
rss-aggregator fetch

# 抓取指定源
rss-aggregator fetch 1

# 读取内容（Markdown格式）
rss-aggregator read --limit 10

# 读取未读文章
rss-aggregator read --unread

# 按标签过滤
rss-aggregator read --tag tech

# 搜索文章
rss-aggregator search "python"

# 标记文章为已读
rss-aggregator mark-read 1
```

### 导入导出

```bash
# 导入OPML文件
rss-aggregator import feeds.opml

# 导出为OPML
rss-aggregator export --format opml --output feeds.opml

# 导出为JSON
rss-aggregator export --format json
```

### 定时任务

```bash
# 启动定时抓取（每60分钟）
rss-aggregator daemon start --interval 60

# 停止定时任务
rss-aggregator daemon stop

# 查看状态
rss-aggregator daemon status
```

## 输出格式

### Markdown格式（默认）

```markdown
# RSS Update - 2024-01-15

## Hacker News
**共 5 篇文章**

### [文章标题](https://example.com/article)
- **作者**: John Doe | **发布时间**: 2024-01-15 10:30 | **标签**: technology

文章摘要内容...

---
```

### JSON格式

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
      "tags": ["technology"],
      "is_read": false
    }
  ]
}
```

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
│   ├── cli.py          # CLI命令定义
│   ├── models.py       # 数据模型
│   ├── database.py     # SQLite操作
│   ├── fetcher.py      # RSS抓取解析
│   ├── exporter.py     # 格式化输出
│   ├── importer.py     # OPML导入
│   └── scheduler.py    # 定时任务
├── tests/
├── main.py
└── pyproject.toml
```

## 依赖

- feedparser: RSS/Atom解析
- httpx: HTTP客户端
- click: CLI框架
- rich: 终端美化输出
- schedule: 定时任务
