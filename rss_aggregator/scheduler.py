"""定时任务管理"""

import logging
import signal
import sys
from pathlib import Path

import schedule

from rss_aggregator.database import Database
from rss_aggregator.fetcher import fetch_feed

logger = logging.getLogger(__name__)

PID_FILE = Path.home() / ".rss-aggregator" / "scheduler.pid"


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


def start_scheduler(db: Database, interval_minutes: int = 60) -> None:
    """启动定时任务调度器"""

    def job() -> None:
        logger.info("开始定时抓取...")
        try:
            new_count = fetch_all_sources(db)
            logger.info("定时抓取完成，新增 %d 篇文章", new_count)
        except Exception:
            logger.exception("定时抓取失败")

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(sys.pid))

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    schedule.every(interval_minutes).minutes.do(job)

    logger.info("定时任务已启动，每 %d 分钟抓取一次", interval_minutes)

    job()

    while True:
        schedule.run_pending()
        import time

        time.sleep(1)


def stop_scheduler() -> bool:
    """停止定时任务调度器"""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        import os

        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        return True
    except (ValueError, ProcessLookupError):
        PID_FILE.unlink(missing_ok=True)
        return False


def is_running() -> bool:
    """检查调度器是否在运行"""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        import os

        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return False


def _handle_shutdown(signum: int, frame: object) -> None:
    """处理关闭信号"""
    logger.info("收到关闭信号，正在停止...")
    PID_FILE.unlink(missing_ok=True)
    sys.exit(0)
