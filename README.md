# EU Reg Monitor (`regmon`)

A small regulatory horizon-scanning tool. It pulls public EU regulatory RSS feeds, tags each item by legal area (AI, Privacy, Competition, IP, Platforms & E-commerce), stores it in SQLite with deduplication, and publishes a filterable dashboard to GitHub Pages. It refreshes once a day through GitHub Actions.

Built as the project for the *AI-Assisted Development* course (SoftUni, 2026) with AI coding agents. See the project document for how it was built, module by module.

## Architecture

```
sources.yaml ─► ingest.py ─► classify.py ─► store.py ─► render.py ─► docs/index.html (GitHub Pages)
 (RSS/Atom)     fetch+parse   keyword rules   SQLite +     Jinja2         + data.json
                per-source    (rules.yaml)    dedupe       static page
                health check
                                    ▲
             .github/workflows/monitor.yml: daily cron → tests → run → commit → deploy
```

| Module | File | Responsibility |
|---|---|---|
| 1. Ingestion | `regmon/ingest.py` | Fetch RSS/Atom feeds, clean HTML, normalise dates. A failing source is reported, never fatal. |
| 2. Classification | `regmon/classify.py`, `rules.yaml` | Word-boundary keyword rules; case-sensitive acronyms (so "AI" doesn't match "said"); multi-label, ranked by hits. |
| 3. Storage | `regmon/store.py` | SQLite; dedupes by normalised URL; logs each run with source health. |
| 4. Dashboard | `regmon/render.py`, `templates/index.html.j2` | Self-contained static page with area chips, source filter, search, and source-health table. |
| 5. Automation | `.github/workflows/` | Daily scheduled run, commits DB + page, deploys to Pages. CI runs tests on Python 3.10 and 3.12. |
| 6. Testing | `tests/` | 33 pytest tests on synthetic fixture feeds, so the suite never needs the network. |

## Run it

```bash
pip install -r requirements.txt

python -m pytest -v                 # 33 tests, no network needed
python -m regmon run --offline      # full pipeline on fixture feeds → build/offline/index.html
python -m regmon run                # live run → data/regmon.sqlite + docs/index.html
python -m regmon stats              # items per area + last-run source health
```

## Configure

- **Add a source:** add an entry to `sources.yaml` (`id`, `name`, `url`, optional `fixture`).
- **Tune tagging:** edit `rules.yaml`. `terms` match case-insensitively; `acronyms` match case-sensitively. Both match whole words only.

Fixture feeds in `tests/fixtures/` are synthetic test data, not real news. Tags are automated and indicative, not legal advice.
