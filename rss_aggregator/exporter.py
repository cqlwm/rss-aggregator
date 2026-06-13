"""格式化输出"""

import json
from datetime import datetime

from rss_aggregator.models import Article, Source


def to_markdown(articles: list[Article], sources: dict[int, Source] | None = None) -> str:
    """将文章列表转换为Markdown格式"""
    if not articles:
        return "暂无文章\n"

    lines = [f"# RSS Update - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

    if sources:
        source_groups: dict[int, list[Article]] = {}
        for article in articles:
            source_groups.setdefault(article.source_id, []).append(article)

        for source_id, group_articles in source_groups.items():
            source = sources.get(source_id)
            source_name = source.name if source else f"Source #{source_id}"
            lines.append(f"## {source_name}\n")
            lines.append(f"**共 {len(group_articles)} 篇文章**\n")

            for article in group_articles:
                lines.extend(_format_article(article))
    else:
        for article in articles:
            lines.extend(_format_article(article))

    return "\n".join(lines)


def _format_article(article: Article) -> list[str]:
    """格式化单篇文章"""
    lines = []

    lines.append(f"### [{article.title}]({article.url})")

    meta = []
    if article.author:
        meta.append(f"**作者**: {article.author}")
    if article.published_at:
        meta.append(f"**发布时间**: {article.published_at.strftime('%Y-%m-%d %H:%M')}")
    if article.tags:
        meta.append(f"**标签**: {', '.join(article.tags)}")
    if article.is_read:
        meta.append("**已读**")

    if meta:
        lines.append("- " + " | ".join(meta))

    if article.summary:
        summary = article.summary[:500]
        if len(article.summary) > 500:
            summary += "..."
        lines.append("")
        lines.append(summary)

    lines.append("")
    lines.append("---")
    lines.append("")

    return lines


def to_json(articles: list[Article], sources: dict[int, Source] | None = None) -> str:
    """将文章列表转换为JSON格式"""
    data = {
        "fetched_at": datetime.now().isoformat(),
        "count": len(articles),
        "articles": [],
    }

    for article in articles:
        article_data = {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "author": article.author,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "summary": article.summary,
            "tags": article.tags,
            "is_read": article.is_read,
        }
        if sources and article.source_id in sources:
            article_data["source"] = sources[article.source_id].name
        data["articles"].append(article_data)

    return json.dumps(data, ensure_ascii=False, indent=2)


def sources_to_json(sources: list[Source]) -> str:
    """将源列表转换为JSON格式"""
    data = []
    for source in sources:
        data.append(
            {
                "id": source.id,
                "url": source.url,
                "name": source.name,
                "tags": source.tags,
                "fetch_interval": source.fetch_interval,
                "last_fetched_at": source.last_fetched_at.isoformat() if source.last_fetched_at else None,
            }
        )
    return json.dumps(data, ensure_ascii=False, indent=2)
