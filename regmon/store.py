"""Module 3 – Storage: persist Items in SQLite and deduplicate by normalized URL.

The database file is committed back to the repo by the GitHub Action, so the
monitor keeps its history across runs and each run only reports what is new.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Item, SourceStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    published TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    areas TEXT NOT NULL,
    first_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_published ON items(published);
CREATE TABLE IF NOT EXISTS runs (
    run_at TEXT NOT NULL,
    new_items INTEGER NOT NULL,
    statuses TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def add_items(self, items: list[Item], now: str | None = None) -> list[Item]:
        """Insert items not seen before; return only the new ones."""
        now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        new: list[Item] = []
        seen_this_batch: set[str] = set()
        with self.conn:
            for item in items:
                if item.id in seen_this_batch:
                    continue
                seen_this_batch.add(item.id)
                cur = self.conn.execute(
                    "INSERT OR IGNORE INTO items VALUES (?,?,?,?,?,?,?,?,?)",
                    (item.id, item.url, item.title, item.summary, item.published,
                     item.source_id, item.source_name, json.dumps(item.areas), now),
                )
                if cur.rowcount == 1:
                    new.append(item)
        return new

    def iter_texts(self):
        """Yield (id, title, summary, areas) for every stored item."""
        for row in self.conn.execute("SELECT id, title, summary, areas FROM items"):
            yield row["id"], row["title"], row["summary"], json.loads(row["areas"])

    def set_areas(self, updates: dict[str, list[str]]) -> None:
        with self.conn:
            self.conn.executemany(
                "UPDATE items SET areas = ? WHERE id = ?",
                [(json.dumps(areas), item_id) for item_id, areas in updates.items()],
            )

    def record_run(self, new_items: int, statuses: list[SourceStatus], now: str | None = None) -> None:
        now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs VALUES (?,?,?)",
                (now, new_items, json.dumps([s.__dict__ for s in statuses])),
            )

    def last_run(self) -> dict | None:
        row = self.conn.execute("SELECT * FROM runs ORDER BY run_at DESC LIMIT 1").fetchone()
        if not row:
            return None
        return {"run_at": row["run_at"], "new_items": row["new_items"], "statuses": json.loads(row["statuses"])}

    def recent(self, limit: int = 300) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM items ORDER BY published DESC, first_seen DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) | {"areas": json.loads(r["areas"])} for r in rows]

    def counts_by_area(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for (areas,) in self.conn.execute("SELECT areas FROM items"):
            for area in json.loads(areas):
                counts[area] = counts.get(area, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
