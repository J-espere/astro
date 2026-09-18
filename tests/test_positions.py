"""Placement formatting, derived points, and the golden-file regression."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro import ephem
from astro.ephem.houses import HouseSystem, houses

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_BODIES = ephem.CLASSICAL_TEN + ("chiron", "true_node", "true_south_node")
GOLDEN_SYSTEMS = (HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY)


def snapshot(reference) -> dict:
    """The full computed state of a reference chart, to six decimal places.

    Six decimals is about a thousandth of an arcsecond -- far below anything
    interpretively meaningful, which is the point: the snapshot should only move
    if the computation changed, never because a rounding rule did.
    """
    jd = reference.jd
    out = {
        "julian_day": round(jd, 9),
        "utc": ephem.from_julian_day(jd).isoformat(),
        "bodies": {},
        "houses": {},
    }
    for name in GOLDEN_BODIES:
        placement = ephem.position(jd, name)
        out["bodies"][name] = {
            "longitude": round(placement.longitude, 6),
            "latitude": round(placement.reading.latitude, 6),
            "speed": round(placement.speed, 6),
            "sign": placement.sign,
            "retrograde": placement.retrograde,
        }
    for system in GOLDEN_SYSTEMS:
        if system.fails_near_poles and abs(reference.latitude) > 66.0:
            continue
        result = houses(jd, reference.latitude, reference.longitude, system)
        out["houses"][system.name.lower()] = {
            "cusps": [round(cusp, 6) for cusp in result.cusps],
            "asc": round(result.ascendant, 6),
            "mc": round(result.midheaven, 6),
            "vertex": round(result.vertex, 6),
        }
    return out


def test_golden_snapshot_is_unchanged(reference):
    """Pins every reference chart. Regenerate deliberately with
    `python -m tests.regenerate_golden` and read the diff before committing --
    a change here means the numbers moved."""
    path = GOLDEN_DIR / f"{reference.key}.json"
    assert path.exists(), f"missing golden file {path}; run tests/regenerate_golden.py"
    assert snapshot(reference) == json.loads(path.read_text())


def test_sign_and_degree_decomposition():
    cases = [(0.0, "aries", 0.0, 1), (29.99, "aries", 29.99, 3), (30.0, "taurus", 0.0, 1),
             (195.5, "libra", 15.5, 2), (359.9, "pisces", 29.9, 3)]
    for longitude, sign, degree, decan in cases:
        reading = ephem.Reading(longitude, 0, 1, 1, 0, 0, ephem.Source.SWISS)
        placement = ephem.Position("test", reading)
        assert placement.sign == sign
        assert placement.degree_in_sign == pytest.approx(degree)
        assert placement.decan == decan


def test_degree_formatting_rounds_without_overflowing():
    """29 deg 59.7 min must not format as 30 deg of the same sign."""
    placement = ephem.Position("test", ephem.Reading(29.995, 0, 1, 1, 0, 0, ephem.Source.SWISS))
    assert placement.format() == "30°00' Aries"


def test_south_node_is_exactly_opposite_the_north(reference):
    north = ephem.position(reference.jd, "true_node")
    south = ephem.position(reference.jd, "true_south_node")
    assert ephem.separation(north.longitude, south.longitude) == pytest.approx(180.0, abs=1e-12)
    assert south.reading.latitude == pytest.approx(-north.reading.latitude, abs=1e-12)


def test_unknown_body_names_are_refused():
    with pytest.raises(KeyError, match="unknown body"):
        ephem.position(2451545.0, "nibiru")


def test_uranian_bodies_are_available_for_that_school(reference):
    """schools/uranian.yaml needs the Hamburg School transneptunians. They are
    hypothetical, but they are computable and the pack is entitled to them."""
    for name in ephem.TRANSNEPTUNIAN:
        assert 0.0 <= ephem.position(reference.jd, name).longitude < 360.0
