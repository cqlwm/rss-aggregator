"""Crontab定时任务管理"""

import logging
import subprocess
import os
from pathlib import Path

from rss_aggregator.database import Database
from rss_aggregator.fetcher import fetch_feed
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

CRON_MARKER = "# rss-aggregator cron job"
LOG_FILE = Path.home() / ".rss-aggregator" / "cron.log"
ENV_FILE = Path.home() / ".rss-aggregator" / ".env"

load_dotenv(ENV_FILE)

def fetch_all_sources(db: Database, limit: int | None = None) -> int:
    """抓取所有源的最新内容"""
    sources = db.list_sources()
    total_new = 0

    for source in sources:
        articles = fetch_feed(source)
        new_count = 0

        for article in articles[:limit]:
            result = db.add_article(article)
            if result is not None:
                new_count += 1

        if new_count > 0:
            db.update_source_fetched_time(source.id)
            logger.info("从 %s 新增 %d 篇文章", source.name, new_count)

        total_new += new_count

    return total_new


def _get_crontab() -> str:
    """获取当前用户的crontab内容"""
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout
    return ""


def _set_crontab(content: str) -> bool:
    """设置crontab内容"""
    result = subprocess.run(
        ["crontab", "-"],
        input=content,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def install_cron(interval_minutes: int = 60) -> bool:
    """安装crontab定时任务"""
    current_cron = _get_crontab()

    lines = [line for line in current_cron.splitlines() if CRON_MARKER not in line]

    project_dir = Path(__file__).parent.parent
    uv_path = os.getenv("UV_PATH")
    if not uv_path:
        raise ValueError("UV_PATH is not set in ~/.rss-aggregator/.env")
    cmd = f"{uv_path} run --project {project_dir} rss-aggregator fetch"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if interval_minutes < 60:
        cron_schedule = f"*/{interval_minutes} * * * *"
    elif interval_minutes == 60:
        cron_schedule = "0 * * * *"
    else:
        hours = interval_minutes // 60
        cron_schedule = f"0 */{hours} * * *"

    new_line = f"{cron_schedule} {cmd} >> {LOG_FILE} 2>&1 {CRON_MARKER}"
    lines.append(new_line)

    new_cron = "\n".join(lines) + "\n"
    return _set_crontab(new_cron)


def remove_cron() -> bool:
    """移除crontab定时任务"""
    current_cron = _get_crontab()

    lines = [line for line in current_cron.splitlines() if CRON_MARKER not in line]

    new_cron = "\n".join(lines)
    if new_cron.strip():
        new_cron += "\n"

    return _set_crontab(new_cron)


def is_installed() -> bool:
    """检查定时任务是否已安装"""
    current_cron = _get_crontab()
    return CRON_MARKER in current_cron


def get_cron_schedule() -> str | None:
    """获取当前的cron调度配置"""
    current_cron = _get_crontab()
    for line in current_cron.splitlines():
        if CRON_MARKER in line:
            parts = line.split()
            if len(parts) >= 5:
                return " ".join(parts[:5])
    return None
