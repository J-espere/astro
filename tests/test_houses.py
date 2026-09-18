"""House geometry, and the invariants that hold in every system."""

from __future__ import annotations

import pytest

from astro import ephem
from astro.ephem.houses import (
    HouseSystem,
    HouseSystemUndefined,
    house_of_whole_sign,
    houses,
    whole_sign_from,
)

SYSTEMS = [
    HouseSystem.PLACIDUS,
    HouseSystem.KOCH,
    HouseSystem.PORPHYRY,
    HouseSystem.REGIOMONTANUS,
    HouseSystem.CAMPANUS,
    HouseSystem.EQUAL,
    HouseSystem.WHOLE_SIGN,
    HouseSystem.MERIDIAN,
    HouseSystem.ALCABITIUS,
]


def _houses(reference, system):
    if system.fails_near_poles and abs(reference.latitude) > 66.0:
        pytest.skip(f"{system.name} is undefined at latitude {reference.latitude}")
    return houses(reference.jd, reference.latitude, reference.longitude, system)


@pytest.mark.parametrize("system", SYSTEMS, ids=lambda s: s.name.lower())
def test_angles_are_opposed(reference, system):
    result = _houses(reference, system)
    assert ephem.separation(result.ascendant, result.descendant) == pytest.approx(180.0, abs=1e-9)
    assert ephem.separation(result.midheaven, result.imum_coeli) == pytest.approx(180.0, abs=1e-9)


@pytest.mark.parametrize("system", SYSTEMS, ids=lambda s: s.name.lower())
def test_cusps_partition_the_circle(reference, system):
    """Twelve spans that sum to exactly one turn, with none collapsed to zero."""
    result = _houses(reference, system)
    spans = [result.span(house) for house in range(1, 13)]
    assert sum(spans) == pytest.approx(360.0, abs=1e-9)
    assert all(span > 0.0 for span in spans)


@pytest.mark.parametrize("system", SYSTEMS, ids=lambda s: s.name.lower())
def test_every_cusp_lands_in_its_own_house(reference, system):
    """Catches off-by-one and wrap errors in house_of(), which are otherwise
    invisible until a planet near 0 Aries reads as the wrong house."""
    result = _houses(reference, system)
    for house in range(1, 13):
        assert result.house_of(result.cusps[house - 1] + 1e-7) == house


@pytest.mark.parametrize("system", SYSTEMS, ids=lambda s: s.name.lower())
def test_house_lookup_covers_the_whole_circle(reference, system):
    result = _houses(reference, system)
    for tenth_degree in range(0, 3600):
        assert 1 <= result.house_of(tenth_degree / 10.0) <= 12


def test_ascendant_opens_the_first_house(reference):
    """True of every quadrant system and of equal houses -- but NOT of whole
    sign, where the Ascendant falls somewhere inside the first house."""
    for system in (HouseSystem.PORPHYRY, HouseSystem.CAMPANUS, HouseSystem.EQUAL):
        result = _houses(reference, system)
        assert result.cusps[0] == pytest.approx(result.ascendant, abs=1e-9)


def test_midheaven_opens_the_tenth_in_quadrant_systems(reference):
    for system in (HouseSystem.PORPHYRY, HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS):
        result = _houses(reference, system)
        assert result.cusps[9] == pytest.approx(result.midheaven, abs=1e-9)


def test_quadrant_houses_are_unequal_away_from_the_equator(nyc):
    """The book's own point: house sizes distort with latitude, so some life
    themes get far more of a life than others."""
    result = houses(nyc.jd, nyc.latitude, nyc.longitude, HouseSystem.PLACIDUS)
    spans = [result.span(house) for house in range(1, 13)]
    assert max(spans) - min(spans) > 5.0


def test_whole_sign_cusps_sit_on_sign_boundaries(reference):
    result = _houses(reference, HouseSystem.WHOLE_SIGN)
    for cusp in result.cusps:
        assert cusp % 30.0 == pytest.approx(0.0, abs=1e-9)


def test_placidus_is_undefined_beyond_the_polar_circle():
    tromso = houses  # name kept for clarity in the failure message
    with pytest.raises(HouseSystemUndefined, match="undefined at latitude"):
        tromso(2448227.6354, 69.6492, 18.9553, HouseSystem.PLACIDUS)


def test_polar_fallback_is_explicit_and_recorded():
    """Substituting Porphyry is fine. Substituting it without saying so is not."""
    result = houses(
        2448227.6354, 69.6492, 18.9553,
        HouseSystem.PLACIDUS, fallback=HouseSystem.PORPHYRY,
    )
    assert result.substituted
    assert result.system is HouseSystem.PORPHYRY
    assert result.requested_system is HouseSystem.PLACIDUS


def test_whole_sign_frame_is_agnostic_about_its_origin(reference):
    """The same geometry serves the Hellenistic frame (counted from the
    Ascendant) and the hatch frame (counted from the Sun). Only the caller's
    choice of origin differs -- which is why that choice lives in the school
    pack, not here."""
    result = _houses(reference, HouseSystem.PLACIDUS)
    sun = ephem.position(reference.jd, "sun").longitude

    from_asc = whole_sign_from(result.ascendant)
    from_sun = whole_sign_from(sun)

    assert house_of_whole_sign(result.ascendant, result.ascendant) == 1
    assert house_of_whole_sign(sun, sun) == 1
    assert from_asc[0] == (result.ascendant // 30) * 30
    assert from_sun[0] == (sun // 30) * 30


def test_solar_house_frame_matches_the_books_own_example():
    """Under A Libra God is a Libra Sun and calls Scorpio 'the second zodiac
    house', Capricorn 'the fourth', and Cancer 'the tenth'. Those are whole
    signs counted from the Sun sign, and they pin the frame precisely."""
    libra_sun = 195.0  # 15 Libra
    scorpio, capricorn, cancer = 225.0, 285.0, 105.0
    assert house_of_whole_sign(scorpio, libra_sun) == 2
    assert house_of_whole_sign(capricorn, libra_sun) == 4
    assert house_of_whole_sign(cancer, libra_sun) == 10
