"""Module 1 – Ingestion: fetch RSS/Atom feeds and turn entries into Items.

One failing source must never stop the run, so every fetch is isolated and
reported back as a SourceStatus that the dashboard shows as "source health".
"""
from __future__ import annotations

import html
import re
import time
from pathlib import Path

import feedparser
import requests

from .models import Item, SourceStatus

USER_AGENT = "regmon/1.0 (+https://github.com/; EU regulatory monitor coursework project)"
TIMEOUT = 20
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SPACE_PUNCT_RE = re.compile(r"\s+([.,;:!?)])")


def clean_text(raw: str, limit: int = 400) -> str:
    text = html.unescape(_TAG_RE.sub(" ", raw or ""))
    text = _WS_RE.sub(" ", text).strip()
    text = _SPACE_PUNCT_RE.sub(r"\1", text)  # "GDPR ." left behind by stripped tags → "GDPR."
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def _published(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return time.strftime("%Y-%m-%d", value)
    return ""


def parse_feed(content: bytes | str, source: dict) -> list[Item]:
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"unparseable feed: {parsed.bozo_exception}")
    items = []
    for entry in parsed.entries:
        url = entry.get("link", "").strip()
        title = clean_text(entry.get("title", ""), limit=300)
        if not url or not title:
            continue
        items.append(
            Item(
                url=url,
                title=title,
                summary=clean_text(entry.get("summary", "") or entry.get("description", "")),
                published=_published(entry),
                source_id=source["id"],
                source_name=source["name"],
            )
        )
    return items


def fetch_source(source: dict, session: requests.Session | None = None) -> tuple[list[Item], SourceStatus]:
    session = session or requests.Session()
    try:
        resp = session.get(source["url"], headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        items = parse_feed(resp.content, source)
        return items, SourceStatus(source["id"], source["name"], True, len(items))
    except Exception as exc:  # noqa: BLE001 – any failure is reported, never raised
        return [], SourceStatus(source["id"], source["name"], False, 0, f"{type(exc).__name__}: {exc}"[:200])


def load_fixture(source: dict, fixtures_dir: Path) -> tuple[list[Item], SourceStatus]:
    path = fixtures_dir / source.get("fixture", f"{source['id']}.xml")
    try:
        items = parse_feed(path.read_bytes(), source)
        return items, SourceStatus(source["id"], source["name"], True, len(items))
    except Exception as exc:  # noqa: BLE001
        return [], SourceStatus(source["id"], source["name"], False, 0, f"{type(exc).__name__}: {exc}"[:200])


def ingest(sources: list[dict], fixtures_dir: Path | None = None) -> tuple[list[Item], list[SourceStatus]]:
    """Fetch every source (live, or from fixtures when fixtures_dir is given)."""
    all_items: list[Item] = []
    statuses: list[SourceStatus] = []
    session = requests.Session()
    for source in sources:
        if fixtures_dir is not None:
            items, status = load_fixture(source, fixtures_dir)
        else:
            items, status = fetch_source(source, session)
        all_items.extend(items)
        statuses.append(status)
    return all_items, statuses
