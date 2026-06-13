"""OPML导入导出"""

import xml.etree.ElementTree as ET
from pathlib import Path

from rss_aggregator.models import Source


def parse_opml(file_path: Path) -> list[Source]:
    """解析OPML文件，返回RSS源列表"""
    tree = ET.parse(file_path)
    root = tree.getroot()

    sources = []

    for outline in root.iter("outline"):
        xml_url = outline.get("xmlUrl") or outline.get("xmlurl")
        if not xml_url:
            continue

        name = outline.get("title") or outline.get("text") or ""
        tags = []

        parent = outline.find("..")
        if parent is not None and parent.tag == "outline":
            parent_title = parent.get("title") or parent.get("text")
            if parent_title:
                tags.append(parent_title)

        sources.append(Source(url=xml_url, name=name, tags=tags))

    return sources


def to_opml(sources: list[Source]) -> str:
    """将RSS源列表导出为OPML格式"""
    root = ET.Element("opml", version="2.0")

    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "RSS Aggregator Subscriptions"

    body = ET.SubElement(root, "body")

    tag_groups: dict[str, list[Source]] = {}
    untagged: list[Source] = []

    for source in sources:
        if source.tags:
            for tag in source.tags:
                tag_groups.setdefault(tag, []).append(source)
        else:
            untagged.append(source)

    for tag, group_sources in tag_groups.items():
        folder = ET.SubElement(body, "outline", text=tag, title=tag)
        for source in group_sources:
            ET.SubElement(
                folder,
                "outline",
                text=source.name,
                title=source.name,
                xmlUrl=source.url,
            )

    for source in untagged:
        ET.SubElement(
            body,
            "outline",
            text=source.name,
            title=source.name,
            xmlUrl=source.url,
        )

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
