import pytest

from regmon.classify import OTHER, build_matchers, classify, classify_text


@pytest.fixture
def matchers(rules):
    return build_matchers(rules)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Commission opens antitrust investigation into cartel", "Competition"),
        ("Guidelines on personal data and the GDPR", "Privacy"),
        ("Copyright and text and data mining exceptions", "IP"),
        ("Obligations for VLOPs under the Digital Services Act", "Platforms & E-commerce"),
        ("Implementing the AI Act for general-purpose AI", "AI"),
    ],
)
def test_primary_area(matchers, text, expected):
    assert classify_text(text, matchers)[0] == expected


def test_acronym_does_not_match_inside_words(matchers):
    # "said" contains "ai"; "dsa" lowercase is not the acronym DSA.
    assert classify_text("The chair said the agenda is ready", matchers) == [OTHER]


def test_acronyms_are_case_sensitive(matchers):
    assert "AI" in classify_text("New AI rules", matchers)
    assert "AI" not in classify_text("new ai rules", matchers)


def test_terms_are_case_insensitive(matchers):
    assert "Privacy" in classify_text("DATA PROTECTION day", matchers)


def test_hyphenated_words_do_not_match_parts(matchers):
    assert "Competition" not in classify_text("A fine-grained analysis", matchers)


def test_multiple_areas_ranked_by_hits(matchers):
    areas = classify_text("GDPR and personal data in AI training under the AI Act", matchers)
    assert set(areas[:2]) == {"AI", "Privacy"}


def test_unmatched_item_is_other(matchers):
    assert classify_text("Agriculture committee approves budget", matchers) == [OTHER]


def test_classify_sets_areas_on_items(sources, rules, fixtures_dir):
    from regmon.ingest import ingest

    items, _ = ingest(sources, fixtures_dir=fixtures_dir)
    classify(items, rules)
    by_title = {i.title: i.areas for i in items}
    assert by_title["Debate on Digital Markets Act gatekeeper compliance"][0] == "Competition"
    assert by_title["Agriculture committee approves budget amendments"] == [OTHER]
    assert by_title["Plenary meeting agenda published"] == [OTHER]
