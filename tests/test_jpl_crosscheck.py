"""The only external check worth having: NASA, not another Swiss Ephemeris caller.

astro.com, astrologerapp and most other astrology software all run the Swiss
Ephemeris. Agreeing with them shows we call the library correctly; it cannot
show the library is right, because it is the same library on both sides.

JPL Horizons is a different source and different code. These fixtures were
pulled from it once and committed, so the check runs offline forever after.
Refresh with tests/fetch_jpl_reference.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro import ephem
from astro.ephem.backend import Source
from conftest import REFERENCES

JPL_DIR = Path(__file__).parent / "golden" / "jpl"

# Arcseconds. Set just above the observed worst case (0.25", the Moon at
# tromso_1990) rather than at a comfortable round number, so that a real drift
# has nowhere to hide.
TOLERANCE = {"moon": 0.4}
DEFAULT_TOLERANCE = 0.2


def _jpl(reference) -> dict:
    path = JPL_DIR / f"{reference.key}.json"
    if not path.exists():
        pytest.skip(f"no JPL fixture for {reference.key}; run tests/fetch_jpl_reference.py")
    return json.loads(path.read_text())


def test_fixture_epoch_matches_the_reference_chart(reference):
    """Guards the whole comparison: if the epochs drifted apart, every body
    would still 'agree' within a loose tolerance while measuring nothing."""
    fixture = _jpl(reference)
    assert fixture["julian_day_ut"] == pytest.approx(reference.jd, abs=1e-9)
    assert fixture["epoch_utc"] == ephem.from_julian_day(reference.jd).isoformat()


def test_fixtures_are_not_paired_with_the_wrong_chart(reference):
    """Regression for a real bug: Horizons returns rows in CHRONOLOGICAL order,
    not in the order they were requested. Zipping by position paired each chart
    with a different chart's sky. Every body then disagreed by hundreds of
    degrees -- which reads as a catastrophic ephemeris failure and is really a
    sorting bug in the fetcher.

    A per-body tolerance cannot catch that on its own, because it fails loudly
    in a way that invites loosening the tolerance. This asserts the fixture fits
    its OWN chart better than any other, which is the property that was violated.
    """
    own = _jpl(reference)["bodies"]["moon"]["longitude"]
    mine = ephem.position(reference.jd, "moon").longitude
    own_error = abs(ephem.wrap180(mine - own))

    for other in REFERENCES:
        if other.key == reference.key:
            continue
        other_error = abs(
            ephem.wrap180(mine - _jpl(other)["bodies"]["moon"]["longitude"])
        )
        assert own_error < other_error, (
            f"{reference.key}'s Moon matches {other.key}'s fixture better than its own"
        )


@pytest.mark.parametrize(
    "body",
    ephem.CLASSICAL_TEN + ("chiron",),
)
def test_longitude_matches_jpl_horizons(reference, body):
    expected = _jpl(reference)["bodies"][body]["longitude"]
    computed = ephem.position(reference.jd, body).longitude
    arcseconds = abs(ephem.wrap180(computed - expected)) * 3600.0
    assert arcseconds < TOLERANCE.get(body, DEFAULT_TOLERANCE), (
        f"{body} at {reference.key}: swisseph {computed:.7f} vs JPL {expected:.7f} "
        f"= {arcseconds:.4f}\" apart"
    )


@pytest.mark.parametrize("body", ephem.CLASSICAL_TEN)
def test_latitude_matches_jpl_horizons(reference, body):
    """Latitude is checked too: a longitude-only comparison passes even when the
    reference frame is wrong, because the error mostly lands in longitude."""
    expected = _jpl(reference)["bodies"][body]["latitude"]
    computed = ephem.position(reference.jd, body).reading.latitude
    arcseconds = abs(computed - expected) * 3600.0
    assert arcseconds < TOLERANCE.get(body, DEFAULT_TOLERANCE)


def test_moshier_also_agrees_with_jpl(reference):
    """Closes the triangle. Swiss and Moshier agree with each other, and both
    agree with JPL -- so the agreement is not two implementations sharing one
    mistake."""
    fixture = _jpl(reference)["bodies"]
    for body in ephem.CLASSICAL_TEN:
        computed = ephem.position(reference.jd, body, source=Source.MOSHIER).longitude
        arcseconds = abs(ephem.wrap180(computed - fixture[body]["longitude"])) * 3600.0
        assert arcseconds < 2.0, f"{body}: Moshier is {arcseconds:.3f}\" from JPL"


def test_reference_frame_mismatch_would_be_caught(reference):
    """A negative control. If the fixtures had been fetched in J2000 coordinates
    instead of ecliptic-of-date, precession would put them roughly a minute of
    arc out -- far outside tolerance. This proves the tolerance is tight enough
    to notice the most likely way this comparison could be silently wrong."""
    import swisseph as swe

    fixture = _jpl(reference)["bodies"]
    wrong_frame = swe.calc_ut(
        reference.jd, swe.JUPITER, swe.FLG_SWIEPH | swe.FLG_J2000
    )[0][0]
    error = abs(ephem.wrap180(wrong_frame - fixture["jupiter"]["longitude"])) * 3600.0
    assert error > 10.0, "the J2000/of-date distinction should be plainly visible"
