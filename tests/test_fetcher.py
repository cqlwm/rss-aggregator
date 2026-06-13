"""RSS抓取模块测试"""

from unittest.mock import MagicMock, patch

from rss_aggregator.fetcher import fetch_feed
from rss_aggregator.models import Source


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test RSS feed</description>
    <item>
        <title>First Article</title>
        <link>https://example.com/article1</link>
        <author>John Doe</author>
        <pubDate>Sun, 01 Jan 2024 12:00:00 GMT</pubDate>
        <description>This is the first article summary.</description>
        <category>technology</category>
        <category>python</category>
    </item>
    <item>
        <title>Second Article</title>
        <link>https://example.com/article2</link>
        <description>Another article summary.</description>
    </item>
</channel>
</rss>"""


@patch("rss_aggregator.fetcher.httpx.get")
def test_fetch_feed(mock_get: MagicMock):
    """测试抓取RSS源"""
    mock_response = MagicMock()
    mock_response.text = RSS_XML
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    source = Source(id=1, url="https://example.com/rss", name="Test Feed")
    articles = fetch_feed(source)

    assert len(articles) == 2
    assert articles[0].title == "First Article"
    assert articles[0].url == "https://example.com/article1"
    assert articles[0].author == "John Doe"
    assert articles[0].summary == "This is the first article summary."
    assert articles[0].tags == ["technology", "python"]
    assert articles[0].published_at is not None

    assert articles[1].title == "Second Article"
    assert articles[1].author is None
    assert articles[1].tags == []


@patch("rss_aggregator.fetcher.httpx.get")
def test_fetch_feed_empty(mock_get: MagicMock):
    """测试空RSS源"""
    empty_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
    <channel>
        <title>Empty Feed</title>
    </channel>
    </rss>"""

    mock_response = MagicMock()
    mock_response.text = empty_rss
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    source = Source(id=1, url="https://example.com/empty", name="Empty")
    articles = fetch_feed(source)

    assert len(articles) == 0


@patch("rss_aggregator.fetcher.httpx.get")
def test_fetch_feed_error(mock_get: MagicMock):
    """测试抓取失败"""
    import httpx

    mock_get.side_effect = httpx.HTTPError("Connection failed")

    source = Source(id=1, url="https://example.com/error", name="Error")
    articles = fetch_feed(source)

    assert len(articles) == 0
