"""Module 2 – Classification: tag Items with regulatory areas using keyword rules.

Rules live in rules.yaml so a lawyer can tune them without touching code.
Plain terms match case-insensitively; acronyms match case-sensitively. Both use
word boundaries, which prevents false positives such as "AI" inside "said".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Item

OTHER = "Other"


@dataclass
class AreaMatcher:
    area: str
    terms: re.Pattern | None
    acronyms: re.Pattern | None

    def score(self, text: str) -> int:
        hits = 0
        if self.terms:
            hits += len(self.terms.findall(text))
        if self.acronyms:
            hits += len(self.acronyms.findall(text))
        return hits


def _pattern(words: list[str], flags: int) -> re.Pattern | None:
    if not words:
        return None
    # Longest first so "AI Act" wins over "AI"; \b...\b keeps matches to whole words.
    alts = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![\w-])(?:{alts})(?![\w-])", flags)


def build_matchers(rules: dict[str, dict]) -> list[AreaMatcher]:
    return [
        AreaMatcher(
            area=area,
            terms=_pattern(spec.get("terms", []), re.IGNORECASE),
            acronyms=_pattern(spec.get("acronyms", []), 0),
        )
        for area, spec in rules.items()
    ]


def classify_text(text: str, matchers: list[AreaMatcher]) -> list[str]:
    scored = [(m.score(text), m.area) for m in matchers]
    areas = [area for score, area in sorted(scored, key=lambda s: -s[0]) if score > 0]
    return areas or [OTHER]


def _item_text(title: str, summary: str) -> str:
    # Title counts double: it is the strongest signal of what the item is about.
    return f"{title} {title} {summary}"


def classify(items: list[Item], rules: dict[str, dict]) -> list[Item]:
    matchers = build_matchers(rules)
    for item in items:
        item.areas = classify_text(_item_text(item.title, item.summary), matchers)
    return items


def reclassify_store(store, rules: dict[str, dict]) -> int:
    """Re-tag every stored item with the current rules, so rule edits apply to history too.

    Returns the number of items whose tags changed.
    """
    matchers = build_matchers(rules)
    updates = {}
    for item_id, title, summary, old in store.iter_texts():
        new = classify_text(_item_text(title, summary), matchers)
        if new != old:
            updates[item_id] = new
    if updates:
        store.set_areas(updates)
    return len(updates)
