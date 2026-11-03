"""Module 4 – Output: render a static dashboard (docs/index.html) and a JSON export.

The page is self-contained (no CDN, no build step) so GitHub Pages can serve it
directly and it also opens from disk.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .store import Store

TEMPLATES = Path(__file__).resolve().parent / "templates"


def build_context(store: Store, area_order: list[str], offline: bool = False) -> dict:
    items = store.recent()
    counts = store.counts_by_area()
    areas = [a for a in area_order if a in counts] + [a for a in counts if a not in area_order]
    last = store.last_run() or {"run_at": "", "new_items": 0, "statuses": []}
    sources = sorted({i["source_name"] for i in items})
    return {
        "items": items,
        "areas": areas,
        "counts": counts,
        "sources": sources,
        "last_run": last,
        "total": store.count(),
        "offline": offline,
        "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
    }


def render(store: Store, out_dir: Path, area_order: list[str], offline: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = build_context(store, area_order, offline=offline)
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    html = env.get_template("index.html.j2").render(**ctx)
    page = out_dir / "index.html"
    page.write_text(html, encoding="utf-8")
    (out_dir / "data.json").write_text(
        json.dumps({"generated_at": ctx["generated_at"], "items": ctx["items"]}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return page
