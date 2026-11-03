"""End-to-end: the CLI runs the full pipeline on fixtures and writes a working dashboard."""
import json

from regmon.cli import main


def run_offline(tmp_path, *extra):
    return main(["--db", str(tmp_path / "db.sqlite"), "run", "--offline", "--out", str(tmp_path / "site"), *extra])


def test_offline_run_builds_dashboard(tmp_path, capsys):
    assert run_offline(tmp_path) == 0
    out = capsys.readouterr().out
    assert "4 items" in out and "10 new" in out  # 11 fetched, 1 duplicate URL

    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "EU Reg Monitor" in html
    assert "Offline demo" in html
    assert "Debate on Digital Markets Act gatekeeper compliance" in html
    assert 'data-area="Competition"' in html
    # Regression: source health once rendered "<built-in method items ...>" instead of the count.
    assert "built-in method" not in html
    assert "4 items" in html

    data = json.loads((tmp_path / "site" / "data.json").read_text(encoding="utf-8"))
    assert len(data["items"]) == 10


def test_second_run_finds_nothing_new(tmp_path, capsys):
    run_offline(tmp_path)
    capsys.readouterr()
    run_offline(tmp_path)
    assert "0 new" in capsys.readouterr().out


def test_titles_are_html_escaped(tmp_path, fixtures_dir):
    feed = fixtures_dir.parent / "_tmp_xss.xml"
    feed.write_text(
        '<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>'
        "<item><title>&lt;script&gt;alert(1)&lt;/script&gt; GDPR</title>"
        "<link>https://example.org/x</link></item></channel></rss>",
        encoding="utf-8",
    )
    try:
        sources = tmp_path / "sources.yaml"
        sources.write_text(f"sources:\n  - {{id: x, name: X, url: 'https://example.org', fixture: '{feed.name}'}}\n")
        main(["--db", str(tmp_path / "db.sqlite"), "run", "--offline", "--fixtures", str(feed.parent),
              "--sources", str(sources), "--out", str(tmp_path / "site")])
        html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
        assert "<script>alert(1)" not in html
    finally:
        feed.unlink()


def test_all_sources_failing_returns_error_code(tmp_path):
    sources = tmp_path / "sources.yaml"
    sources.write_text("sources:\n  - {id: b, name: Broken, url: 'https://example.org', fixture: broken.xml}\n")
    assert run_offline(tmp_path, "--sources", str(sources)) == 2


def test_stats_command(tmp_path, capsys):
    run_offline(tmp_path)
    capsys.readouterr()
    assert main(["--db", str(tmp_path / "db.sqlite"), "stats"]) == 0
    out = capsys.readouterr().out
    assert "10 items stored" in out and "Privacy" in out
