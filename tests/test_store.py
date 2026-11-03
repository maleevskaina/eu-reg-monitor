from regmon.models import Item, SourceStatus, item_id, normalize_url
from regmon.store import Store


def make(url, title="t", areas=("Privacy",), published="2026-11-01"):
    return Item(url, title, "s", published, "src", "Source", list(areas))


def test_normalize_url_strips_query_fragment_and_slash():
    assert normalize_url("HTTPS://Example.org/a/b/?utm=x#top") == "https://example.org/a/b"
    assert item_id("https://example.org/a/") == item_id("https://example.org/a?x=1")


def test_add_items_returns_only_new():
    s = Store(":memory:")
    assert len(s.add_items([make("https://e.org/1"), make("https://e.org/2")])) == 2
    new = s.add_items([make("https://e.org/2"), make("https://e.org/3")])
    assert [i.url for i in new] == ["https://e.org/3"]
    assert s.count() == 3


def test_duplicates_within_one_batch_are_stored_once():
    s = Store(":memory:")
    new = s.add_items([make("https://e.org/1?utm=a"), make("https://e.org/1/")])
    assert len(new) == 1 and s.count() == 1


def test_recent_is_sorted_newest_first_and_decodes_areas():
    s = Store(":memory:")
    s.add_items([make("https://e.org/old", published="2026-01-01"),
                 make("https://e.org/new", published="2026-11-01", areas=("AI", "Privacy"))])
    rows = s.recent()
    assert rows[0]["url"] == "https://e.org/new" and rows[0]["areas"] == ["AI", "Privacy"]


def test_counts_by_area():
    s = Store(":memory:")
    s.add_items([make("https://e.org/1", areas=("AI", "Privacy")), make("https://e.org/2", areas=("AI",))])
    assert s.counts_by_area() == {"AI": 2, "Privacy": 1}


def test_run_log_round_trip():
    s = Store(":memory:")
    s.record_run(3, [SourceStatus("a", "A", True, 3), SourceStatus("b", "B", False, 0, "Timeout")])
    last = s.last_run()
    assert last["new_items"] == 3 and last["statuses"][1]["error"] == "Timeout"


def test_persists_to_disk(tmp_path):
    db = tmp_path / "x" / "db.sqlite"
    s = Store(db)
    s.add_items([make("https://e.org/1")])
    s.close()
    assert Store(db).count() == 1
