import requests

from regmon.ingest import clean_text, fetch_source, ingest, load_fixture, parse_feed

SRC = {"id": "t", "name": "Test source", "url": "https://example.org/feed"}


def test_parses_rss_items(fixtures_dir):
    items = parse_feed((fixtures_dir / "edpb.xml").read_bytes(), SRC)
    assert len(items) == 4
    assert items[0].title == "Board adopts statement on GDPR enforcement cooperation"
    assert items[0].published == "2026-11-02"
    assert items[0].source_name == "Test source"


def test_parses_atom_items(fixtures_dir):
    items = parse_feed((fixtures_dir / "edps.xml").read_bytes(), SRC)
    assert [i.url for i in items] == [
        "https://example.org/edps/press/transfers",
        "https://example.org/edps/press/genai-speech",
    ]
    assert items[1].published == "2026-10-28"


def test_html_is_stripped_from_summaries(fixtures_dir):
    item = parse_feed((fixtures_dir / "edpb.xml").read_bytes(), SRC)[0]
    assert "<" not in item.summary and "GDPR" in item.summary
    assert item.summary.endswith("under the GDPR.")  # no stray space before punctuation


def test_missing_date_is_empty_string(fixtures_dir):
    plenary = parse_feed((fixtures_dir / "edpb.xml").read_bytes(), SRC)[3]
    assert plenary.published == ""


def test_clean_text_truncates_on_word_boundary():
    out = clean_text("word " * 200, limit=50)
    assert len(out) <= 50 and out.endswith("…") and not out.endswith(" …")


def test_broken_fixture_reports_failure_instead_of_raising(fixtures_dir):
    items, status = load_fixture({**SRC, "fixture": "broken.xml"}, fixtures_dir)
    assert items == [] and status.ok is False and status.error


def test_network_error_is_reported(monkeypatch):
    class Boom(requests.Session):
        def get(self, *a, **k):
            raise requests.ConnectionError("network down")

    items, status = fetch_source(SRC, session=Boom())
    assert items == [] and not status.ok and "network down" in status.error


def test_http_error_is_reported():
    class NotFound(requests.Session):
        def get(self, *a, **k):
            r = requests.Response()
            r.status_code = 404
            r.url = SRC["url"]
            return r

    _, status = fetch_source(SRC, session=NotFound())
    assert not status.ok and "404" in status.error


def test_ingest_all_fixtures(sources, fixtures_dir):
    items, statuses = ingest(sources, fixtures_dir=fixtures_dir)
    assert all(s.ok for s in statuses)
    assert len(items) == 11
