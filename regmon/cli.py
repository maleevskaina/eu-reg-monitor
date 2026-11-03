"""Command-line entry point.

    python -m regmon run              # live: fetch, classify, store, render
    python -m regmon run --offline    # same pipeline on saved fixture feeds
    python -m regmon stats            # counts per area and last-run source health
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .classify import classify, reclassify_store
from .config import ROOT, load_rules, load_sources
from .ingest import ingest
from .render import render
from .store import Store

DEFAULT_DB = ROOT / "data" / "regmon.sqlite"
DEFAULT_OUT = ROOT / "docs"
DEFAULT_FIXTURES = ROOT / "tests" / "fixtures"
OFFLINE_DB = ROOT / "build" / "offline.sqlite"
OFFLINE_OUT = ROOT / "build" / "offline"


def cmd_run(args) -> int:
    sources = load_sources(args.sources)
    rules = load_rules(args.rules)
    fixtures = Path(args.fixtures) if args.offline else None
    # Offline demo runs never touch the live database or the published dashboard.
    db = args.db or (OFFLINE_DB if args.offline else DEFAULT_DB)
    out = args.out or (OFFLINE_OUT if args.offline else DEFAULT_OUT)

    items, statuses = ingest(sources, fixtures_dir=fixtures)
    classify(items, rules)

    store = Store(db)
    new = store.add_items(items)
    retagged = reclassify_store(store, rules)
    store.record_run(len(new), statuses)
    page = render(store, Path(out), list(rules), offline=args.offline)

    print(f"regmon {__version__} — {'offline (fixtures)' if args.offline else 'live'} run")
    for s in statuses:
        mark = "OK  " if s.ok else "FAIL"
        detail = f"{s.items} items" if s.ok else s.error
        print(f"  [{mark}] {s.name:<45} {detail}")
    print(f"Fetched {len(items)} items, {len(new)} new, {store.count()} stored in total.")
    if retagged:
        print(f"Re-tagged {retagged} stored items after a rules change.")
    for item in new[:10]:
        print(f"  + [{', '.join(item.areas)}] {item.title[:90]}")
    print(f"Dashboard written to {page}")
    store.close()

    if not any(s.ok for s in statuses):
        print("Error: every source failed.", file=sys.stderr)
        return 2
    return 0


def cmd_stats(args) -> int:
    store = Store(args.db or DEFAULT_DB)
    print(f"{store.count()} items stored")
    for area, n in store.counts_by_area().items():
        print(f"  {area:<25} {n:>4}")
    last = store.last_run()
    if last:
        print(f"Last run {last['run_at']}: {last['new_items']} new")
        for s in last["statuses"]:
            print(f"  [{'OK  ' if s['ok'] else 'FAIL'}] {s['name']}")
    store.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="regmon", description="Small EU regulatory monitor")
    p.add_argument("--version", action="version", version=f"regmon {__version__}")
    p.add_argument("--db", default=None, help="SQLite database path (default: data/regmon.sqlite)")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="fetch, classify, store and render")
    run.add_argument("--offline", action="store_true", help="read saved fixture feeds instead of the network")
    run.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    run.add_argument("--sources", type=Path, default=None)
    run.add_argument("--rules", type=Path, default=None)
    run.add_argument("--out", default=None, help="output folder (default: docs/, or build/offline with --offline)")
    run.set_defaults(func=cmd_run)

    stats = sub.add_parser("stats", help="show stored counts and source health")
    stats.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    return args.func(args)
