"""内容抓取模块测试"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from rss_aggregator.scraper import (
    IMAGES_DIR,
    ScrapeResult,
    _download_images,
    _extract_content,
    _guess_extension,
    fetch_article_content,
)


SAMPLE_HTML = """
<html>
<body>
<article>
<h1>Test Article Title</h1>
<p>This is the main content of the article. It contains enough text to be
considered a real article by trafilatura's content extraction algorithm.</p>
<p>The article discusses various topics related to technology and software
development. It provides insights into modern best practices.</p>
</article>
</body>
</html>
"""

SAMPLE_HTML_WITH_IMAGES = """
<html>
<body>
<article>
<h1>Article With Images</h1>
<p>This is the first paragraph of the article with enough content to be
considered a real article by the extraction algorithm. It discusses various
important topics related to technology and software development.</p>
<figure><img src="https://example.com/photo1.jpg" alt="Photo 1"></figure>
<p>The second paragraph continues the discussion with more details and insights
about the subject matter being covered in this article.</p>
<img src="https://example.com/diagram.png" alt="Diagram">
<p>The final paragraph wraps up the article with concluding thoughts and summary
of the key points discussed throughout.</p>
</article>
</body>
</html>
"""


@patch("rss_aggregator.scraper.httpx.get")
def test_fetch_content_success(mock_get: MagicMock) -> None:
    """测试正常抓取流程"""
    mock_response = MagicMock()
    mock_response.text = SAMPLE_HTML
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = fetch_article_content("https://example.com/article")

    assert result.success is True
    assert len(result.content) > 0
    assert result.error is None


@patch("rss_aggregator.scraper.httpx.get")
def test_fetch_content_http_error(mock_get: MagicMock) -> None:
    """测试HTTP请求失败"""
    import httpx

    mock_get.side_effect = httpx.HTTPError("Connection failed")

    result = fetch_article_content("https://example.com/article")

    assert result.success is False
    assert result.error is not None
    assert "Connection failed" in result.error


def test_extract_content_empty_html() -> None:
    """测试空HTML提取失败"""
    result = _extract_content("<html><body></body></html>", "https://example.com")

    assert result.success is False
    assert result.error is not None


def test_extract_content_valid_html() -> None:
    """测试有效HTML提取"""
    result = _extract_content(SAMPLE_HTML, "https://example.com/article")

    assert result.success is True
    assert len(result.content) > 0


def test_playwright_not_installed() -> None:
    """测试Playwright未安装时返回错误"""
    with patch.dict("sys.modules", {"playwright.sync_api": None}):
        result = fetch_article_content("https://example.com", use_playwright=True)

        assert result.success is False
        assert result.error is not None
        assert "未安装" in result.error


def test_scrape_result_dataclass() -> None:
    """测试 ScrapeResult 数据类"""
    result = ScrapeResult(content="test", success=True)
    assert result.content == "test"
    assert result.success is True
    assert result.error is None
    assert result.images == []

    result = ScrapeResult(content="", success=False, error="failed")
    assert result.success is False
    assert result.error == "failed"


def test_guess_extension() -> None:
    """测试从URL猜测图片扩展名"""
    assert _guess_extension("https://example.com/photo.jpg") == ".jpg"
    assert _guess_extension("https://example.com/photo.jpeg") == ".jpg"
    assert _guess_extension("https://example.com/photo.png") == ".png"
    assert _guess_extension("https://example.com/photo.gif") == ".gif"
    assert _guess_extension("https://example.com/photo.webp") == ".webp"
    assert _guess_extension("https://example.com/photo.svg") == ".svg"
    assert _guess_extension("https://example.com/image?v=1") == ""


@patch("rss_aggregator.scraper.httpx.get")
def test_download_images(mock_get: MagicMock) -> None:
    """测试图片下载和URL替换"""
    mock_img_response = MagicMock()
    mock_img_response.content = b"\x89PNG\r\n\x1a\n"
    mock_img_response.raise_for_status = MagicMock()
    mock_img_response.headers = {"content-type": "image/png"}
    mock_get.return_value = mock_img_response

    markdown = "![Photo](https://example.com/photo.png)\n\nSome text\n\n![Diagram](https://example.com/diagram.png)"

    with patch("rss_aggregator.scraper.IMAGES_DIR") as mock_dir:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_dir.__truediv__ = lambda self, x: Path(tmpdir) / x
            mock_dir.mkdir = MagicMock()
            mock_dir.exists = MagicMock(return_value=False)

            result_md, images = _download_images(markdown)

            assert len(images) == 2
            assert "https://example.com/photo.png" not in result_md
            assert "https://example.com/diagram.png" not in result_md


@patch("rss_aggregator.scraper.httpx.get")
def test_download_images_failure_skips(mock_get: MagicMock) -> None:
    """测试单张图片下载失败时跳过"""
    import httpx

    mock_get.side_effect = httpx.HTTPError("Download failed")

    markdown = "![Photo](https://example.com/photo.png)\n\nSome text"

    with patch("rss_aggregator.scraper.IMAGES_DIR") as mock_dir:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_dir.__truediv__ = lambda self, x: Path(tmpdir) / x
            mock_dir.mkdir = MagicMock()
            mock_dir.exists = MagicMock(return_value=False)

            result_md, images = _download_images(markdown)

            assert len(images) == 0
            assert "https://example.com/photo.png" in result_md


def test_download_images_no_images() -> None:
    """测试没有图片的Markdown"""
    markdown = "Just some text without images."
    result_md, images = _download_images(markdown)

    assert result_md == markdown
    assert images == []


@patch("rss_aggregator.scraper.httpx.get")
def test_extract_content_with_images(mock_get: MagicMock) -> None:
    """测试带图片的HTML提取"""
    mock_img_response = MagicMock()
    mock_img_response.content = b"\x89PNG\r\n\x1a\n"
    mock_img_response.raise_for_status = MagicMock()
    mock_img_response.headers = {"content-type": "image/png"}
    mock_get.return_value = mock_img_response

    with patch("rss_aggregator.scraper.IMAGES_DIR") as mock_dir:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_dir.__truediv__ = lambda self, x: Path(tmpdir) / x
            mock_dir.mkdir = MagicMock()
            mock_dir.exists = MagicMock(return_value=False)

            result = _extract_content(SAMPLE_HTML_WITH_IMAGES, "https://example.com")

            assert result.success is True
            assert len(result.content) > 0


def test_scrape_result_with_images() -> None:
    """测试 ScrapeResult 包含图片路径"""
    result = ScrapeResult(
        content="![img](/local/path.jpg)",
        success=True,
        images=["/local/path.jpg"],
    )
    assert len(result.images) == 1
    assert result.images[0] == "/local/path.jpg"
