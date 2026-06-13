"""CLI命令测试"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from rss_aggregator.cli import CONTENT_CACHE_DIR, cli
from rss_aggregator.database import Database
from rss_aggregator.models import Article, Source


def get_test_runner():
    """获取测试运行器"""
    return CliRunner()


@patch("rss_aggregator.cli.get_db")
def test_source_add(mock_get_db):
    """测试添加RSS源命令"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        mock_get_db.return_value = Database(db_path)
        runner = get_test_runner()

        result = runner.invoke(cli, ["source", "add", "https://example.com/rss", "--name", "Test Source"])
        assert result.exit_code == 0
        assert "成功添加RSS源" in result.output

        result = runner.invoke(cli, ["source", "list"])
        assert result.exit_code == 0
        assert "Test Source" in result.output
    finally:
        db_path.unlink(missing_ok=True)


@patch("rss_aggregator.cli.get_db")
def test_source_list_empty(mock_get_db):
    """测试列出空RSS源"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        mock_get_db.return_value = Database(db_path)
        runner = get_test_runner()

        result = runner.invoke(cli, ["source", "list"])
        assert result.exit_code == 0
        assert "暂无RSS源" in result.output
    finally:
        db_path.unlink(missing_ok=True)


@patch("rss_aggregator.cli.get_db")
def test_source_remove(mock_get_db):
    """测试删除RSS源命令"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        db = Database(db_path)
        mock_get_db.return_value = db
        runner = get_test_runner()

        runner.invoke(cli, ["source", "add", "https://example.com/rss", "--name", "Test"])

        result = runner.invoke(cli, ["source", "remove", "1"])
        assert result.exit_code == 0
        assert "成功删除源" in result.output
    finally:
        db_path.unlink(missing_ok=True)


@patch("rss_aggregator.cli.get_db")
def test_read_empty(mock_get_db):
    """测试读取空内容"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        mock_get_db.return_value = Database(db_path)
        runner = get_test_runner()

        result = runner.invoke(cli, ["read"])
        assert result.exit_code == 0
        assert "暂无文章" in result.output
    finally:
        db_path.unlink(missing_ok=True)


@patch("rss_aggregator.cli.get_db")
def test_search_no_results(mock_get_db):
    """测试搜索无结果"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        mock_get_db.return_value = Database(db_path)
        runner = get_test_runner()

        result = runner.invoke(cli, ["search", "nonexistent"])
        assert result.exit_code == 0
        assert "未找到" in result.output
    finally:
        db_path.unlink(missing_ok=True)


def test_version():
    """测试版本命令"""
    runner = get_test_runner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help():
    """测试帮助命令"""
    runner = get_test_runner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "RSS订阅内容收集器" in result.output
    assert "source" in result.output
    assert "fetch" in result.output
    assert "read" in result.output
    assert "search" in result.output
    assert "cron" in result.output


@patch("rss_aggregator.cli.is_installed")
@patch("rss_aggregator.cli.install_cron")
def test_cron_install(mock_install, mock_is_installed):
    """测试安装定时任务"""
    mock_is_installed.return_value = False
    mock_install.return_value = True
    runner = get_test_runner()

    result = runner.invoke(cli, ["cron", "install", "--interval", "30"])
    assert result.exit_code == 0
    assert "成功安装定时任务" in result.output


@patch("rss_aggregator.cli.is_installed")
@patch("rss_aggregator.cli.remove_cron")
def test_cron_remove(mock_remove, mock_is_installed):
    """测试移除定时任务"""
    mock_is_installed.return_value = True
    mock_remove.return_value = True
    runner = get_test_runner()

    result = runner.invoke(cli, ["cron", "remove"])
    assert result.exit_code == 0
    assert "成功移除定时任务" in result.output


@patch("rss_aggregator.cli.is_installed")
@patch("rss_aggregator.cli.get_cron_schedule")
def test_cron_status_installed(mock_get_schedule, mock_is_installed):
    """测试查看已安装的定时任务状态"""
    mock_is_installed.return_value = True
    mock_get_schedule.return_value = "0 * * * *"
    runner = get_test_runner()

    result = runner.invoke(cli, ["cron", "status"])
    assert result.exit_code == 0
    assert "定时任务已安装" in result.output


@patch("rss_aggregator.cli.is_installed")
def test_cron_status_not_installed(mock_is_installed):
    """测试查看未安装的定时任务状态"""
    mock_is_installed.return_value = False
    runner = get_test_runner()

    result = runner.invoke(cli, ["cron", "status"])
    assert result.exit_code == 0
    assert "定时任务未安装" in result.output


@patch("rss_aggregator.cli.fetch_article_content")
def test_fetch_content_success(mock_fetch):
    """测试 URL 抓取成功并写入缓存"""
    from rss_aggregator.scraper import ScrapeResult

    mock_fetch.return_value = ScrapeResult(content="# Full Content", success=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("rss_aggregator.cli.CONTENT_CACHE_DIR", Path(tmpdir)):
            runner = get_test_runner()
            result = runner.invoke(cli, ["fetch-content", "https://example.com/article"])
            assert result.exit_code == 0
            assert "# Full Content" in result.output
            mock_fetch.assert_called_once()

            cache_files = list(Path(tmpdir).glob("*.md"))
            assert len(cache_files) == 1
            assert cache_files[0].read_text(encoding="utf-8") == "# Full Content"


@patch("rss_aggregator.cli.fetch_article_content")
def test_fetch_content_cache_hit(mock_fetch):
    """测试命中缓存时不调用抓取"""
    import hashlib

    url = "https://example.com/article"
    cache_key = hashlib.md5(url.encode()).hexdigest()

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / f"{cache_key}.md"
        cache_file.write_text("cached content", encoding="utf-8")

        with patch("rss_aggregator.cli.CONTENT_CACHE_DIR", Path(tmpdir)):
            runner = get_test_runner()
            result = runner.invoke(cli, ["fetch-content", url])
            assert result.exit_code == 0
            assert "命中缓存" in result.output
            assert "cached content" in result.output
            mock_fetch.assert_not_called()


@patch("rss_aggregator.cli.fetch_article_content")
def test_fetch_content_no_cache(mock_fetch):
    """测试 --no-cache 跳过缓存"""
    import hashlib

    from rss_aggregator.scraper import ScrapeResult

    mock_fetch.return_value = ScrapeResult(content="fresh content", success=True)

    url = "https://example.com/article"
    cache_key = hashlib.md5(url.encode()).hexdigest()

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / f"{cache_key}.md"
        cache_file.write_text("old cached content", encoding="utf-8")

        with patch("rss_aggregator.cli.CONTENT_CACHE_DIR", Path(tmpdir)):
            runner = get_test_runner()
            result = runner.invoke(cli, ["fetch-content", url, "--no-cache"])
            assert result.exit_code == 0
            assert "fresh content" in result.output
            mock_fetch.assert_called_once()


@patch("rss_aggregator.cli.fetch_article_content")
def test_fetch_content_failure(mock_fetch):
    """测试抓取失败"""
    from rss_aggregator.scraper import ScrapeResult

    mock_fetch.return_value = ScrapeResult(content="", success=False, error="连接超时")

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("rss_aggregator.cli.CONTENT_CACHE_DIR", Path(tmpdir)):
            runner = get_test_runner()
            result = runner.invoke(cli, ["fetch-content", "https://example.com/article"])
            assert result.exit_code == 1
            assert "抓取失败" in result.output
            assert "连接超时" in result.output


@patch("rss_aggregator.cli.fetch_article_content")
def test_fetch_content_output_file(mock_fetch):
    """测试 --output 写入文件"""
    from rss_aggregator.scraper import ScrapeResult

    mock_fetch.return_value = ScrapeResult(content="# Output Content", success=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "output.md"

        with patch("rss_aggregator.cli.CONTENT_CACHE_DIR", Path(tmpdir)):
            runner = get_test_runner()
            result = runner.invoke(cli, ["fetch-content", "https://example.com/article", "-o", str(output_file)])
            assert result.exit_code == 0
            assert "已写入" in result.output
            assert output_file.read_text(encoding="utf-8") == "# Output Content"
