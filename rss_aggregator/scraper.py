"""全文内容抓取"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
IMAGE_TIMEOUT = 15
IMAGES_DIR = Path.home() / ".rss-aggregator" / "images"

IMAGE_URL_PATTERN = re.compile(r"!\[.*?\]\((https?://[^)]+)\)")


@dataclass
class ScrapeResult:
    """抓取结果"""

    content: str
    success: bool
    images: list[str] = field(default_factory=list)
    error: str | None = None


def fetch_article_content(url: str, use_playwright: bool = False) -> ScrapeResult:
    """抓取文章全文内容

    Args:
        url: 文章URL
        use_playwright: 是否使用Playwright渲染JS页面

    Returns:
        ScrapeResult，包含提取的Markdown内容和已下载的图片路径
    """
    if use_playwright:
        return _fetch_with_playwright(url)
    return _fetch_with_httpx(url)


def _fetch_with_httpx(url: str) -> ScrapeResult:
    """使用 httpx + trafilatura 抓取"""
    try:
        response = httpx.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("抓取失败 %s: %s", url, e)
        return ScrapeResult(content="", success=False, error=str(e))

    return _extract_content(response.text, url)


def _fetch_with_playwright(url: str) -> ScrapeResult:
    """使用 Playwright 抓取 JS 渲染页面"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ScrapeResult(
            content="",
            success=False,
            error="Playwright 未安装，运行: uv add --optional-group playwright playwright",
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
    except Exception as e:
        logger.error("Playwright 抓取失败 %s: %s", url, e)
        return ScrapeResult(content="", success=False, error=str(e))

    return _extract_content(html, url)


def _extract_content(html: str, url: str) -> ScrapeResult:
    """从 HTML 提取文章正文并下载图片"""
    content = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_links=True,
        include_images=True,
    )

    if not content:
        logger.warning("未能从 %s 提取到内容", url)
        return ScrapeResult(content="", success=False, error="未找到文章正文内容")

    content, downloaded_images = _download_images(content)

    return ScrapeResult(content=content, success=True, images=downloaded_images)


def _download_images(markdown: str) -> tuple[str, list[str]]:
    """从 Markdown 中提取图片 URL，下载到本地，替换链接

    Returns:
        (替换后的markdown, 已下载的本地图片路径列表)
    """
    image_urls = IMAGE_URL_PATTERN.findall(markdown)
    if not image_urls:
        return markdown, []

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    downloaded: list[str] = []
    seen_urls: dict[str, str] = {}

    for img_url in image_urls:
        if img_url in seen_urls:
            local_path = seen_urls[img_url]
        else:
            local_path = _download_single_image(img_url)
            seen_urls[img_url] = local_path

        if local_path:
            markdown = markdown.replace(img_url, local_path)
            downloaded.append(local_path)

    return markdown, downloaded


def _download_single_image(url: str) -> str | None:
    """下载单张图片到本地

    Returns:
        本地文件路径，失败返回 None
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    ext = _guess_extension(url)
    filename = f"{url_hash}{ext}"
    local_path = IMAGES_DIR / filename

    if local_path.exists():
        return str(local_path)

    try:
        response = httpx.get(
            url,
            timeout=IMAGE_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; rss-aggregator/0.1)"},
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("图片下载失败 %s: %s", url, e)
        return None

    content_type = response.headers.get("content-type", "")
    if ext == "" and "jpeg" in content_type:
        local_path = IMAGES_DIR / f"{url_hash}.jpg"
    elif ext == "" and "png" in content_type:
        local_path = IMAGES_DIR / f"{url_hash}.png"
    elif ext == "" and "webp" in content_type:
        local_path = IMAGES_DIR / f"{url_hash}.webp"

    local_path.write_bytes(response.content)
    logger.debug("已下载图片: %s -> %s", url, local_path)
    return str(local_path)


def _guess_extension(url: str) -> str:
    """从 URL 猜测图片扩展名"""
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ""
