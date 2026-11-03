from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """Strip query strings, fragments and trailing slashes so the same article dedupes."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def item_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode("utf-8")).hexdigest()[:16]


@dataclass
class Item:
    url: str
    title: str
    summary: str
    published: str  # ISO 8601 date, or "" when the feed gives none
    source_id: str
    source_name: str
    areas: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return item_id(self.url)


@dataclass
class SourceStatus:
    source_id: str
    name: str
    ok: bool
    items: int
    error: str = ""
