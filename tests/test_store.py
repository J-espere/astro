"""The delineation store: append-only, attributed, and never quietly partial."""

from __future__ import annotations

import pytest

from astro.corpus.store import DelineationStore, Provenance, format_lookup
from astro.doctrine.factors import parse


@pytest.fixture
def store(tmp_path):
    with DelineationStore(tmp_path / "test.db") as opened:
        yield opened


def test_entries_are_stored_under_canonical_keys(store):
    """Written one way, found the other. Otherwise the same configuration
    accumulates two divergent delineations neither of which sees the other."""
    store.add("hatch", "sign:leo body:venus", "written one way")
    found = store.lookup(parse("body:venus sign:leo"), generalise=False)
    assert found["hatch"][0][1].text == "written one way"


def test_lookup_returns_every_school_not_a_preferred_one(store):
    store.add("hatch", "sign:scorpio", "power, death and rebirth")
    store.add("cosmodynamics", "sign:scorpio", "a fixed water mechanism")
    store.add("hellenistic", "sign:scorpio", "the house of Mars, nocturnal")

    found = store.lookup("sign:scorpio")
    assert set(found) == {"hatch", "cosmodynamics", "hellenistic"}


def test_narrowing_to_one_school_has_to_be_asked_for(store):
    store.add("hatch", "sign:scorpio", "a")
    store.add("cosmodynamics", "sign:scorpio", "b")
    assert set(store.lookup("sign:scorpio")) == {"hatch", "cosmodynamics"}
    assert set(store.lookup("sign:scorpio", school="hatch")) == {"hatch"}


def test_revision_supersedes_and_keeps_the_original(store):
    first = store.add("cosmodynamics", "body:mars sign:cancer", "first understanding")
    second = store.revise(first.id, "second understanding")

    assert store.get(first.id).superseded_by == second.id
    assert second.supersedes == first.id
    assert not store.get(first.id).active

    history = store.history("body:mars sign:cancer")
    assert [entry.text for entry in history] == ["first understanding", "second understanding"]


def test_only_the_current_version_is_returned_by_default(store):
    first = store.add("cosmodynamics", "sign:aries", "old")
    store.revise(first.id, "new")

    current = store.lookup("sign:aries")["cosmodynamics"]
    assert [entry.text for _, entry in current] == ["new"]

    everything = store.lookup("sign:aries", include_superseded=True)["cosmodynamics"]
    assert {entry.text for _, entry in everything} == {"old", "new"}


def test_a_superseded_entry_cannot_be_revised_again(store):
    """Keeps the history a chain rather than a tree, so 'what do I think now'
    always has one answer."""
    first = store.add("hatch", "sign:aries", "one")
    store.revise(first.id, "two")
    with pytest.raises(ValueError, match="already superseded"):
        store.revise(first.id, "three")


def test_generalisation_answers_when_the_exact_factor_has_none(store):
    store.add("hatch", "body:saturn house:11@natal", "friendship taken too seriously")
    found = store.lookup("body:saturn sign:aries house:11@natal")

    rung, entry = found["hatch"][0]
    assert entry.text == "friendship taken too seriously"
    assert str(rung) == "body:saturn house:11@natal"
    assert rung != parse("body:saturn sign:aries house:11@natal")


def test_a_general_answer_never_masquerades_as_a_specific_one(store):
    """The rung that answered is returned alongside the entry, and the renderer
    prints it, so a note about Saturn generally is not read as a note about
    Saturn in Aries in the 11th."""
    store.add("hatch", "body:saturn", "structure and consequence")
    factor = parse("body:saturn sign:aries house:11@natal")
    rendered = format_lookup(factor, store.lookup(factor))
    assert "(general: body:saturn)" in rendered


def test_a_specific_entry_wins_over_a_general_one_for_the_same_school(store):
    store.add("hatch", "body:saturn", "general")
    store.add("hatch", "body:saturn house:11@natal", "specific")
    found = store.lookup("body:saturn house:11@natal")
    assert [entry.text for _, entry in found["hatch"]] == ["specific"]


def test_provenance_travels_with_the_text(store):
    transcribed = store.add(
        "cosmodynamics", "sign:leo", "typed from a reading",
        provenance=Provenance.TRANSCRIBED, source_detail="astrologerapp, 2026-09-19",
    )
    quoted = store.add(
        "hatch", "sign:leo", "the star of the zodiac",
        provenance=Provenance.SOURCE_TEXT, source_detail="Under A Libra God, ch. 16",
    )

    assert "transcribed" in transcribed.attribution()
    assert "astrologerapp" in transcribed.attribution()
    assert not transcribed.provenance.quotable
    assert quoted.provenance.quotable


def test_empty_delineations_are_refused(store):
    with pytest.raises(ValueError, match="empty delineation"):
        store.add("hatch", "sign:leo", "   ")


@pytest.mark.parametrize("confidence", [0, 6, -1])
def test_confidence_is_bounded(store, confidence):
    with pytest.raises(ValueError, match="confidence must be"):
        store.add("hatch", "sign:leo", "text", confidence=confidence)


def test_search_finds_text_across_schools(store):
    store.add("hatch", "sign:capricorn", "rules, authority and society")
    store.add("cosmodynamics", "sign:capricorn", "a cardinal earth mechanism of structure")
    assert {entry.school for entry in store.search("structure")} == {"cosmodynamics"}
    assert {entry.school for entry in store.search("authority")} == {"hatch"}


def test_coverage_reports_what_is_missing(store):
    store.add("cosmodynamics", "sign:aries", "done")
    coverage = dict(store.coverage("cosmodynamics", ["sign:aries", "sign:taurus"]))
    assert coverage["sign:aries"] is True
    assert coverage["sign:taurus"] is False


def test_school_counts_exclude_superseded_entries(store):
    first = store.add("cosmodynamics", "sign:aries", "one")
    store.revise(first.id, "two")
    store.add("cosmodynamics", "sign:taurus", "three")
    assert dict(store.schools())["cosmodynamics"] == 2


def test_an_empty_lookup_says_so_and_says_how_to_fix_it(store):
    factor = parse("sign:pisces")
    rendered = format_lookup(factor, store.lookup(factor))
    assert "no school has a delineation" in rendered
    assert "astro define" in rendered
