"""SQLite数据库操作"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from rss_aggregator.models import Article, Source

DEFAULT_DB_DIR = Path.home() / ".rss-aggregator"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "data.db"

CREATE_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    tags TEXT DEFAULT '[]',
    fetch_interval INTEGER DEFAULT 60,
    last_fetched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_ARTICLES_TABLE = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    author TEXT,
    published_at TIMESTAMP,
    summary TEXT,
    content TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
)
"""


class Database:
    """SQLite数据库管理"""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(CREATE_SOURCES_TABLE)
            conn.execute(CREATE_ARTICLES_TABLE)
            conn.execute("PRAGMA foreign_keys = ON")
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """数据库迁移"""
        columns = {row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()}
        if "content" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN content TEXT DEFAULT ''")

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ===== Source操作 =====

    def add_source(self, source: Source) -> Source:
        """添加RSS源"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO sources (url, name, tags, fetch_interval) VALUES (?, ?, ?, ?)",
                (source.url, source.name, json.dumps(source.tags), source.fetch_interval),
            )
            source.id = cursor.lastrowid
            source.created_at = datetime.now()
            return source

    def get_source(self, source_id: int) -> Source | None:
        """获取单个RSS源"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_source(row)

    def get_source_by_url(self, url: str) -> Source | None:
        """通过URL获取RSS源"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM sources WHERE url = ?", (url,)).fetchone()
            if row is None:
                return None
            return self._row_to_source(row)

    def list_sources(self) -> list[Source]:
        """列出所有RSS源"""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall()
            return [self._row_to_source(row) for row in rows]

    def update_source(self, source: Source) -> Source:
        """更新RSS源"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sources SET name = ?, tags = ?, fetch_interval = ?, last_fetched_at = ? WHERE id = ?",
                (
                    source.name,
                    json.dumps(source.tags),
                    source.fetch_interval,
                    source.last_fetched_at.isoformat() if source.last_fetched_at else None,
                    source.id,
                ),
            )
            return source

    def delete_source(self, source_id: int) -> bool:
        """删除RSS源及其所有文章"""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            return cursor.rowcount > 0

    def update_source_fetched_time(self, source_id: int) -> None:
        """更新源的最后抓取时间"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sources SET last_fetched_at = ? WHERE id = ?",
                (datetime.now().isoformat(), source_id),
            )

    # ===== Article操作 =====

    def add_article(self, article: Article) -> Article | None:
        """添加文章，如果URL已存在则返回None"""
        with self._get_conn() as conn:
            try:
                cursor = conn.execute(
                    "INSERT INTO articles (source_id, title, url, author, published_at, summary, content, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        article.source_id,
                        article.title,
                        article.url,
                        article.author,
                        article.published_at.isoformat() if article.published_at else None,
                        article.summary,
                        article.content,
                        json.dumps(article.tags),
                    ),
                )
                article.id = cursor.lastrowid
                article.created_at = datetime.now()
                return article
            except sqlite3.IntegrityError:
                return None

    def get_article(self, article_id: int) -> Article | None:
        """获取单篇文章"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_article(row)

    def get_article_by_url(self, url: str) -> Article | None:
        """通过URL获取文章"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM articles WHERE url = ?", (url,)).fetchone()
            if row is None:
                return None
            return self._row_to_article(row)

    def list_articles(
        self,
        source_id: int | None = None,
        tag: str | None = None,
        since: datetime | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Article]:
        """列出文章，支持过滤"""
        query = "SELECT * FROM articles WHERE 1=1"
        params: list = []

        if source_id is not None:
            query += " AND source_id = ?"
            params.append(source_id)

        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        if since is not None:
            query += " AND published_at >= ?"
            params.append(since.isoformat())

        if unread_only:
            query += " AND is_read = FALSE"

        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_article(row) for row in rows]

    def search_articles(self, keyword: str, source_id: int | None = None, limit: int = 50) -> list[Article]:
        """搜索文章"""
        query = "SELECT * FROM articles WHERE (title LIKE ? OR summary LIKE ?)"
        params: list = [f"%{keyword}%", f"%{keyword}%"]

        if source_id is not None:
            query += " AND source_id = ?"
            params.append(source_id)

        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_article(row) for row in rows]

    def mark_article_read(self, article_id: int) -> bool:
        """标记文章为已读"""
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE articles SET is_read = TRUE WHERE id = ?", (article_id,))
            return cursor.rowcount > 0

    def mark_source_articles_read(self, source_id: int) -> int:
        """标记源的所有文章为已读"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE articles SET is_read = TRUE WHERE source_id = ? AND is_read = FALSE",
                (source_id,),
            )
            return cursor.rowcount

    def update_article_content(self, article_id: int, content: str) -> bool:
        """更新文章全文内容"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE articles SET content = ? WHERE id = ?", (content, article_id)
            )
            return cursor.rowcount > 0

    # ===== 工具方法 =====

    def _row_to_source(self, row: sqlite3.Row) -> Source:
        """将数据库行转换为Source对象"""
        return Source(
            id=row["id"],
            url=row["url"],
            name=row["name"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            fetch_interval=row["fetch_interval"],
            last_fetched_at=datetime.fromisoformat(row["last_fetched_at"]) if row["last_fetched_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    def _row_to_article(self, row: sqlite3.Row) -> Article:
        """将数据库行转换为Article对象"""
        return Article(
            id=row["id"],
            source_id=row["source_id"],
            title=row["title"],
            url=row["url"],
            author=row["author"],
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            summary=row["summary"] or "",
            content=row["content"] or "",
            tags=json.loads(row["tags"]) if row["tags"] else [],
            is_read=bool(row["is_read"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
