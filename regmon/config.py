from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_sources(path: Path | None = None) -> list[dict]:
    data = yaml.safe_load((path or ROOT / "sources.yaml").read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    for s in sources:
        missing = {"id", "name", "url"} - s.keys()
        if missing:
            raise ValueError(f"source {s!r} is missing {sorted(missing)}")
    return sources


def load_rules(path: Path | None = None) -> dict[str, dict]:
    data = yaml.safe_load((path or ROOT / "rules.yaml").read_text(encoding="utf-8"))
    return data.get("areas", {})
