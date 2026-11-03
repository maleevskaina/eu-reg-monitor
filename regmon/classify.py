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


def classify(items: list[Item], rules: dict[str, dict]) -> list[Item]:
    matchers = build_matchers(rules)
    for item in items:
        # Title counts double: it is the strongest signal of what the item is about.
        text = f"{item.title} {item.title} {item.summary}"
        item.areas = classify_text(text, matchers)
    return items
