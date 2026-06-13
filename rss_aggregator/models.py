"""数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Source:
    """RSS源"""

    id: int | None = None
    url: str = ""
    name: str = ""
    tags: list[str] = field(default_factory=list)
    fetch_interval: int = 60  # 分钟
    last_fetched_at: datetime | None = None
    created_at: datetime | None = None


@dataclass
class Article:
    """RSS文章"""

    id: int | None = None
    source_id: int = 0
    title: str = ""
    url: str = ""
    author: str | None = None
    published_at: datetime | None = None
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    is_read: bool = False
    created_at: datetime | None = None
