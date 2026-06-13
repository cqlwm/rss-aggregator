"""数据库模块测试"""

import tempfile
from pathlib import Path

from rss_aggregator.database import Database
from rss_aggregator.models import Article, Source


def test_add_source():
    """测试添加RSS源"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = Source(url="https://example.com/rss", name="Test Source", tags=["tech"])
        result = database.add_source(source)

        assert result.id is not None
        assert result.name == "Test Source"
        assert result.url == "https://example.com/rss"
        assert result.tags == ["tech"]
    finally:
        db.unlink(missing_ok=True)


def test_get_source():
    """测试获取RSS源"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = Source(url="https://example.com/rss", name="Test Source")
        added = database.add_source(source)

        result = database.get_source(added.id)
        assert result is not None
        assert result.name == "Test Source"

        assert database.get_source(999) is None
    finally:
        db.unlink(missing_ok=True)


def test_list_sources():
    """测试列出RSS源"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        assert len(database.list_sources()) == 0

        database.add_source(Source(url="https://example.com/1", name="Source 1"))
        database.add_source(Source(url="https://example.com/2", name="Source 2"))

        sources = database.list_sources()
        assert len(sources) == 2
    finally:
        db.unlink(missing_ok=True)


def test_delete_source():
    """测试删除RSS源"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = database.add_source(Source(url="https://example.com/rss", name="Test"))

        assert database.delete_source(source.id) is True
        assert database.get_source(source.id) is None
        assert database.delete_source(999) is False
    finally:
        db.unlink(missing_ok=True)


def test_add_article():
    """测试添加文章"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = database.add_source(Source(url="https://example.com/rss", name="Test"))

        article = Article(
            source_id=source.id,
            title="Test Article",
            url="https://example.com/article1",
            summary="Test summary",
        )
        result = database.add_article(article)

        assert result is not None
        assert result.id is not None
        assert result.title == "Test Article"

        duplicate = database.add_article(article)
        assert duplicate is None
    finally:
        db.unlink(missing_ok=True)


def test_list_articles():
    """测试列出文章"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = database.add_source(Source(url="https://example.com/rss", name="Test"))

        for i in range(3):
            database.add_article(
                Article(
                    source_id=source.id,
                    title=f"Article {i}",
                    url=f"https://example.com/article{i}",
                )
            )

        articles = database.list_articles()
        assert len(articles) == 3

        articles = database.list_articles(source_id=source.id)
        assert len(articles) == 3

        articles = database.list_articles(limit=2)
        assert len(articles) == 2
    finally:
        db.unlink(missing_ok=True)


def test_search_articles():
    """测试搜索文章"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = database.add_source(Source(url="https://example.com/rss", name="Test"))

        database.add_article(
            Article(
                source_id=source.id,
                title="Python Tutorial",
                url="https://example.com/python",
            )
        )
        database.add_article(
            Article(
                source_id=source.id,
                title="JavaScript Guide",
                url="https://example.com/js",
            )
        )

        results = database.search_articles("Python")
        assert len(results) == 1
        assert results[0].title == "Python Tutorial"

        results = database.search_articles("Guide")
        assert len(results) == 1
    finally:
        db.unlink(missing_ok=True)


def test_mark_article_read():
    """测试标记文章已读"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = database.add_source(Source(url="https://example.com/rss", name="Test"))
        article = database.add_article(
            Article(
                source_id=source.id,
                title="Test",
                url="https://example.com/article",
            )
        )

        assert article.is_read is False
        assert database.mark_article_read(article.id) is True

        updated = database.get_article(article.id)
        assert updated.is_read is True
    finally:
        db.unlink(missing_ok=True)


def test_update_article_content():
    """测试更新文章全文内容"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = database.add_source(Source(url="https://example.com/rss", name="Test"))
        article = database.add_article(
            Article(
                source_id=source.id,
                title="Test",
                url="https://example.com/article",
            )
        )

        assert article.content == ""

        result = database.update_article_content(article.id, "# Full Content\n\nThis is the full article.")
        assert result is True

        updated = database.get_article(article.id)
        assert updated.content == "# Full Content\n\nThis is the full article."

        assert database.update_article_content(999, "nope") is False
    finally:
        db.unlink(missing_ok=True)


def test_get_article_by_url():
    """测试通过URL获取文章"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Path(f.name)

    try:
        database = Database(db)
        source = database.add_source(Source(url="https://example.com/rss", name="Test"))
        database.add_article(
            Article(
                source_id=source.id,
                title="Test",
                url="https://example.com/article",
            )
        )

        result = database.get_article_by_url("https://example.com/article")
        assert result is not None
        assert result.title == "Test"

        assert database.get_article_by_url("https://example.com/nonexistent") is None
    finally:
        db.unlink(missing_ok=True)


def test_content_migration():
    """测试 content 列迁移"""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    fetch_interval INTEGER DEFAULT 60,
                    last_fetched_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    author TEXT,
                    published_at TIMESTAMP,
                    summary TEXT,
                    tags TEXT DEFAULT '[]',
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
                )
            """)
            conn.execute("INSERT INTO sources (url, name) VALUES (?, ?)", ("https://example.com/rss", "Test"))
            conn.execute(
                "INSERT INTO articles (source_id, title, url) VALUES (?, ?, ?)",
                (1, "Old Article", "https://example.com/old"),
            )

        database = Database(db_path)
        article = database.get_article_by_url("https://example.com/old")
        assert article is not None
        assert article.content == ""

        database.update_article_content(article.id, "migrated content")
        updated = database.get_article(article.id)
        assert updated.content == "migrated content"
    finally:
        db_path.unlink(missing_ok=True)
