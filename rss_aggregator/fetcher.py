"""RSS内容抓取和解析"""

import logging
from datetime import datetime, timezone

import feedparser
import httpx

from rss_aggregator.models import Article, Source

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


def fetch_feed(source: Source) -> list[Article]:
    """抓取并解析RSS源"""
    try:
        response = httpx.get(source.url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("抓取RSS源失败 %s: %s", source.url, e)
        return []

    feed = feedparser.parse(response.text)

    if feed.bozo and not feed.entries:
        logger.error("解析RSS源失败 %s: %s", source.url, feed.bozo_exception)
        return []

    articles = []
    for entry in feed.entries:
        article = _parse_entry(source, entry)
        if article:
            articles.append(article)

    logger.info("从 %s 抓取了 %d 篇文章", source.name or source.url, len(articles))
    return articles


def _parse_entry(source: Source, entry: feedparser.FeedParserDict) -> Article | None:
    """解析单个RSS条目"""
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()

    if not title or not link:
        return None

    published_at = _parse_date(entry)

    return Article(
        source_id=source.id or 0,
        title=title,
        url=link,
        author=entry.get("author"),
        published_at=published_at,
        summary=_get_summary(entry),
        tags=_get_tags(entry),
    )


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    """解析发布日期"""
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                from time import mktime

                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue

    for field in ("published", "updated"):
        date_str = entry.get(field)
        if date_str:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                continue

    return None


def _get_summary(entry: feedparser.FeedParserDict) -> str:
    """获取文章摘要"""
    if entry.get("summary"):
        return entry["summary"].strip()
    if entry.get("description"):
        return entry["description"].strip()
    if entry.get("content"):
        contents = entry["content"]
        if isinstance(contents, list) and len(contents) > 0:
            return contents[0].get("value", "").strip()
    return ""


def _get_tags(entry: feedparser.FeedParserDict) -> list[str]:
    """获取文章标签"""
    tags = []
    for tag in entry.get("tags", []):
        term = tag.get("term", "").strip()
        if term:
            tags.append(term)
    return tags
