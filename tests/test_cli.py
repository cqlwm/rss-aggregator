"""CLI命令测试"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from rss_aggregator.cli import cli
from rss_aggregator.database import Database


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
