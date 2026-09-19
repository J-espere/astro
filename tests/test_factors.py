"""The addressing scheme. Everything authored hangs off these keys staying stable."""

from __future__ import annotations

import pytest

from astro.doctrine.factors import (
    FAMILIES,
    ComponentType,
    Factor,
    FactorError,
    describe,
    family,
    parse,
    register_component,
)


@pytest.mark.parametrize(
    ("written", "canonical"),
    [
        ("sign:aries", "sign:aries"),
        ("body:venus sign:leo", "body:venus sign:leo"),
        ("sign:leo body:venus", "body:venus sign:leo"),
        ("house:11@solar body:saturn", "body:saturn house:11@solar"),
        ("SIGN:Leo BODY:Venus", "body:venus sign:leo"),
        ("body:venus, sign:leo", "body:venus sign:leo"),
    ],
)
def test_component_order_does_not_matter(written, canonical):
    """Two people writing the same configuration must address the same entry,
    or their delineations for it drift apart without either noticing."""
    assert str(parse(written)) == canonical


def test_symmetric_aspects_sort_their_bodies():
    """Venus square Saturn and Saturn square Venus are one aspect, not two."""
    assert parse("aspect:square body:venus body:saturn") == parse(
        "aspect:square body:saturn body:venus"
    )


def test_transit_is_not_symmetric_with_its_natal_target():
    """Transiting Saturn to natal Sun is a different event from transiting Sun
    to natal Saturn, and the scheme has to keep them apart."""
    assert parse("transit:saturn natal:sun aspect:conjunction") != parse(
        "transit:sun natal:saturn aspect:conjunction"
    )


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        ("body:nibiru", "unknown body"),
        ("house:13@natal", "house must be 1-12"),
        ("house:0", "house must be 1-12"),
        ("house:11@lunar", "unknown house frame"),
        ("sign:aries sign:leo", "not repeatable"),
        ("aspect:wobble", "unknown aspect"),
        ("floating", "is not a component"),
        ("body:", "has no value"),
        ("", "empty factor key"),
    ],
)
def test_invalid_keys_are_refused_with_a_reason(bad, message):
    with pytest.raises(FactorError, match=message):
        parse(bad)


def test_unknown_component_types_are_refused_but_not_forbidden():
    """A school this codebase has never seen may address something new. That has
    to be possible -- but never by accident, because an unregistered type would
    be silently unsearchable."""
    with pytest.raises(FactorError, match="unknown component type"):
        parse("declination:out_of_bounds body:mars")

    assert parse("declination:out_of_bounds body:mars", allow_unknown_types=True)


def test_a_school_can_register_its_own_dimension():
    register_component(
        ComponentType("phase_angle", 90, lambda _v: None, description="test-only"),
        replace=True,
    )
    factor = parse("body:venus phase_angle:superior")
    assert factor.get("phase_angle") == ("superior",)


def test_house_frames_are_different_factors():
    """The natal and solar frames are different claims about different parts of
    a chart. Collapsing them would mis-file most of the book's transit material."""
    assert parse("body:saturn house:11@natal") != parse("body:saturn house:11@solar")


def test_generalisations_are_subsets_not_prefixes():
    """Regression: dropping only trailing components meant an entry written for
    'body:saturn house:11' was invisible to a lookup of 'body:saturn sign:aries
    house:11', because the sign sits between them in canonical order -- losing
    the single most useful generalisation."""
    specific = parse("body:saturn sign:aries house:11@natal")
    ladder = [str(rung) for rung in specific.generalisations()]

    assert ladder[0] == str(specific)
    assert "body:saturn house:11@natal" in ladder
    assert "body:saturn sign:aries" in ladder
    assert "body:saturn" in ladder
    assert "house:11@natal" in ladder
    # most specific first, so retrieval can stop at the first answer
    assert ladder == sorted(ladder, key=lambda key: -len(key.split()))


def test_generalisation_falls_back_for_very_long_keys():
    """Subsets are exponential; past a threshold it degrades deliberately rather
    than enumerating hundreds of rungs."""
    long_key = parse(
        "transit:saturn natal:sun aspect:square sign:aries house:11@natal "
        "phase:retrograde decan:2"
    )
    assert len(long_key.generalisations()) == len(long_key.components)


def test_factor_editing_returns_canonical_factors():
    base = parse("body:saturn")
    assert str(base.with_component("sign", "aries")) == "body:saturn sign:aries"
    assert str(parse("body:saturn sign:aries").without("sign")) == "body:saturn"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("body:venus sign:leo", "venus in Leo"),
        ("body:saturn house:11@solar", "saturn in the 11th house (solar)"),
        ("angle:mc sign:libra", "MC in Libra"),
        ("body:saturn body:venus aspect:square", "saturn square venus"),
        ("transit:saturn natal:sun aspect:conjunction",
         "transiting saturn conjunction natal sun"),
    ],
)
def test_descriptions_are_readable(key, expected):
    assert describe(parse(key)) == expected


@pytest.mark.parametrize("name", sorted(FAMILIES))
def test_every_family_enumerates_valid_factors(name):
    factors = family(name)
    assert factors
    for factor in factors:
        assert isinstance(factor, Factor)
        assert parse(str(factor)) == factor


def test_family_sizes_are_what_they_claim():
    assert len(family("sign")) == 12
    assert len(family("house-solar")) == 12
    assert len(family("body-in-sign")) == 120       # 10 bodies x 12 signs
    assert len(family("angle-in-sign")) == 48       # 4 angles x 12 signs
    assert len(family("aspect-pairs")) == 45 * 6    # 45 pairs x 6 aspects


def test_unknown_family_is_refused():
    with pytest.raises(FactorError, match="unknown family"):
        family("vibes")
