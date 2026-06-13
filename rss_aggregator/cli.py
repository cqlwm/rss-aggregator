"""CLI命令定义"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from rss_aggregator.database import Database
from rss_aggregator.exporter import sources_to_json, to_json, to_markdown
from rss_aggregator.fetcher import fetch_feed
from rss_aggregator.importer import parse_opml, to_opml
from rss_aggregator.models import Source
from rss_aggregator.scraper import fetch_article_content
from rss_aggregator.scheduler import fetch_all_sources, get_cron_schedule, install_cron, is_installed, remove_cron

console = Console()


def get_db() -> Database:
    """获取数据库实例"""
    return Database()


@click.group()
@click.version_option(version="0.1.0", prog_name="rss-aggregator")
def cli() -> None:
    """RSS订阅内容收集器 - 为OpenCalw提供RSS数据"""
    pass


# ===== Source管理 =====


@cli.group()
def source() -> None:
    """管理RSS源"""
    pass


@source.command("add")
@click.argument("url")
@click.option("--name", "-n", default="", help="源名称")
@click.option("--tags", "-t", default="", help="标签，逗号分隔")
@click.option("--interval", "-i", default=60, help="抓取间隔（分钟）")
def source_add(url: str, name: str, tags: str, interval: int) -> None:
    """添加RSS源"""
    db = get_db()

    if db.get_source_by_url(url):
        console.print(f"[red]错误：URL已存在 - {url}[/red]")
        sys.exit(1)

    if not name:
        name = url

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    source = Source(url=url, name=name, tags=tag_list, fetch_interval=interval)
    source = db.add_source(source)

    console.print(f"[green]成功添加RSS源：{source.name} (ID: {source.id})[/green]")


@source.command("remove")
@click.argument("source_id", type=int)
def source_remove(source_id: int) -> None:
    """删除RSS源"""
    db = get_db()

    if not db.get_source(source_id):
        console.print(f"[red]错误：未找到ID为 {source_id} 的源[/red]")
        sys.exit(1)

    if db.delete_source(source_id):
        console.print(f"[green]成功删除源 ID: {source_id}[/green]")
    else:
        console.print("[red]删除失败[/red]")


@source.command("list")
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json"]), default="table", help="输出格式")
def source_list(fmt: str) -> None:
    """列出所有RSS源"""
    db = get_db()
    sources = db.list_sources()

    if not sources:
        console.print("[yellow]暂无RSS源[/yellow]")
        return

    if fmt == "json":
        console.print(sources_to_json(sources))
        return

    table = Table(title="RSS源列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("URL", style="blue")
    table.add_column("标签", style="magenta")
    table.add_column("间隔(分)", style="yellow")
    table.add_column("最后抓取", style="dim")

    for s in sources:
        last_fetched = s.last_fetched_at.strftime("%Y-%m-%d %H:%M") if s.last_fetched_at else "从未"
        table.add_row(
            str(s.id),
            s.name,
            s.url,
            ", ".join(s.tags) if s.tags else "-",
            str(s.fetch_interval),
            last_fetched,
        )

    console.print(table)


@source.command("update")
@click.argument("source_id", type=int)
@click.option("--name", "-n", help="源名称")
@click.option("--tags", "-t", help="标签，逗号分隔")
@click.option("--interval", "-i", type=int, help="抓取间隔（分钟）")
def source_update(source_id: int, name: str | None, tags: str | None, interval: int | None) -> None:
    """更新RSS源配置"""
    db = get_db()
    source = db.get_source(source_id)

    if not source:
        console.print(f"[red]错误：未找到ID为 {source_id} 的源[/red]")
        sys.exit(1)

    if name is not None:
        source.name = name
    if tags is not None:
        source.tags = [t.strip() for t in tags.split(",") if t.strip()]
    if interval is not None:
        source.fetch_interval = interval

    db.update_source(source)
    console.print(f"[green]成功更新源 ID: {source_id}[/green]")


# ===== 内容操作 =====


@cli.command("fetch")
@click.argument("source_id", required=False, type=int)
@click.option("--limit", "-l", type=int, help="每个源最多抓取的文章数")
def fetch_cmd(source_id: int | None, limit: int | None) -> None:
    """抓取RSS内容"""
    db = get_db()

    if source_id:
        source = db.get_source(source_id)
        if not source:
            console.print(f"[red]错误：未找到ID为 {source_id} 的源[/red]")
            sys.exit(1)

        articles = fetch_feed(source)
        new_count = 0
        for article in articles[:limit]:
            result = db.add_article(article)
            if result is not None:
                new_count += 1

        if new_count > 0:
            db.update_source_fetched_time(source.id)

        console.print(f"[green]从 {source.name} 抓取了 {new_count} 篇新文章[/green]")
    else:
        new_count = fetch_all_sources(db, limit)
        console.print(f"[green]抓取完成，共新增 {new_count} 篇文章[/green]")


@cli.command("read")
@click.option("--source", "-s", "source_id", type=int, help="指定源ID")
@click.option("--tag", "-t", help="按标签过滤")
@click.option("--since", help="起始时间（YYYY-MM-DD）")
@click.option("--limit", "-l", default=20, help="最多显示文章数")
@click.option("--unread", is_flag=True, help="只显示未读文章")
@click.option("--format", "-f", "fmt", type=click.Choice(["markdown", "json"]), default="markdown", help="输出格式")
def read_cmd(
    source_id: int | None,
    tag: str | None,
    since: str | None,
    limit: int,
    unread: bool,
    fmt: str,
) -> None:
    """读取RSS内容"""
    db = get_db()

    since_dt = None
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            console.print("[red]错误：日期格式应为 YYYY-MM-DD[/red]")
            sys.exit(1)

    articles = db.list_articles(
        source_id=source_id,
        tag=tag,
        since=since_dt,
        unread_only=unread,
        limit=limit,
    )

    if not articles:
        console.print("[yellow]暂无文章[/yellow]")
        return

    if fmt == "json":
        sources = {s.id: s for s in db.list_sources()}
        console.print(to_json(articles, sources))
    else:
        sources = {s.id: s for s in db.list_sources()}
        console.print(to_markdown(articles, sources))


@cli.command("search")
@click.argument("keyword")
@click.option("--source", "-s", "source_id", type=int, help="指定源ID")
@click.option("--limit", "-l", default=20, help="最多显示文章数")
@click.option("--format", "-f", "fmt", type=click.Choice(["markdown", "json"]), default="markdown", help="输出格式")
def search_cmd(keyword: str, source_id: int | None, limit: int, fmt: str) -> None:
    """搜索文章"""
    db = get_db()

    articles = db.search_articles(keyword, source_id=source_id, limit=limit)

    if not articles:
        console.print(f"[yellow]未找到包含 '{keyword}' 的文章[/yellow]")
        return

    if fmt == "json":
        sources = {s.id: s for s in db.list_sources()}
        console.print(to_json(articles, sources))
    else:
        sources = {s.id: s for s in db.list_sources()}
        console.print(to_markdown(articles, sources))


@cli.command("mark-read")
@click.argument("article_id", type=int)
def mark_read_cmd(article_id: int) -> None:
    """标记文章为已读"""
    db = get_db()

    if db.mark_article_read(article_id):
        console.print(f"[green]文章 {article_id} 已标记为已读[/green]")
    else:
        console.print(f"[red]错误：未找到文章 ID: {article_id}[/red]")


@cli.command("fetch-content")
@click.argument("target")
@click.option("--playwright", "-p", is_flag=True, help="使用 Playwright 渲染 JS 页面")
@click.option("--output", "-o", help="输出内容到文件")
def fetch_content_cmd(target: str, playwright: bool, output: str | None) -> None:
    """抓取文章全文内容

    TARGET 可以是文章 ID（整数）或 URL 链接
    """
    db = get_db()

    if target.isdigit():
        article_id = int(target)
        article = db.get_article(article_id)
        if not article:
            console.print(f"[red]错误：未找到文章 ID: {article_id}[/red]")
            sys.exit(1)

        if article.content:
            console.print("[yellow]文章已有全文内容，跳过抓取[/yellow]")
            if output:
                Path(output).write_text(article.content, encoding="utf-8")
                console.print(f"[green]已写入 {output}[/green]")
            else:
                console.print(article.content)
            return

        url = article.url
    else:
        url = target
        article = None

    console.print(f"正在抓取: {url}")
    result = fetch_article_content(url, use_playwright=playwright)

    if not result.success:
        console.print(f"[red]抓取失败: {result.error}[/red]")
        sys.exit(1)

    if article and article.id:
        db.update_article_content(article.id, result.content)
        console.print(f"[green]已存储全文内容（{len(result.content)} 字符）[/green]")
    elif article is None:
        matched = db.get_article_by_url(url)
        if matched and matched.id:
            db.update_article_content(matched.id, result.content)
            console.print(f"[green]已匹配并更新文章 #{matched.id} 的全文内容[/green]")
        else:
            console.print(f"[green]抓取成功（{len(result.content)} 字符）[/green]")

    if output:
        Path(output).write_text(result.content, encoding="utf-8")
        console.print(f"[green]已写入 {output}[/green]")
    elif not article:
        console.print(result.content)


# ===== 导入导出 =====


@cli.command("import")
@click.argument("file", type=click.Path(exists=True))
def import_cmd(file: str) -> None:
    """导入OPML文件"""
    db = get_db()

    file_path = Path(file)
    sources = parse_opml(file_path)

    added = 0
    skipped = 0

    for source in sources:
        if db.get_source_by_url(source.url):
            skipped += 1
            continue

        db.add_source(source)
        added += 1

    console.print(f"[green]导入完成：新增 {added} 个源，跳过 {skipped} 个已存在的源[/green]")


@cli.command("export")
@click.option("--format", "-f", "fmt", type=click.Choice(["opml", "json"]), default="opml", help="导出格式")
@click.option("--output", "-o", help="输出文件路径")
def export_cmd(fmt: str, output: str | None) -> None:
    """导出数据"""
    db = get_db()
    sources = db.list_sources()

    if not sources:
        console.print("[yellow]暂无RSS源可导出[/yellow]")
        return

    if fmt == "opml":
        content = to_opml(sources)
    else:
        content = sources_to_json(sources)

    if output:
        Path(output).write_text(content, encoding="utf-8")
        console.print(f"[green]已导出到 {output}[/green]")
    else:
        console.print(content)


# ===== 定时任务 =====


@cli.group()
def cron() -> None:
    """Crontab定时任务管理"""
    pass


@cron.command("install")
@click.option("--interval", "-i", default=60, help="抓取间隔（分钟）")
def cron_install(interval: int) -> None:
    """安装crontab定时任务"""
    if is_installed():
        console.print("[yellow]定时任务已安装，将覆盖现有配置[/yellow]")

    if install_cron(interval):
        console.print(f"[green]成功安装定时任务，每 {interval} 分钟抓取一次[/green]")
    else:
        console.print("[red]安装定时任务失败[/red]")
        sys.exit(1)


@cron.command("remove")
def cron_remove() -> None:
    """移除crontab定时任务"""
    if not is_installed():
        console.print("[yellow]定时任务未安装[/yellow]")
        return

    if remove_cron():
        console.print("[green]成功移除定时任务[/green]")
    else:
        console.print("[red]移除定时任务失败[/red]")
        sys.exit(1)


@cron.command("status")
def cron_status() -> None:
    """查看定时任务状态"""
    if is_installed():
        schedule = get_cron_schedule()
        console.print(f"[green]定时任务已安装[/green]")
        console.print(f"调度计划: {schedule}")
    else:
        console.print("[yellow]定时任务未安装[/yellow]")


def main() -> None:
    """主入口"""
    cli()
