"""The backend's job is to never lie about where a number came from."""

from __future__ import annotations

import pytest

from astro import ephem
from astro.ephem.backend import Source, SourceSubstituted, calc, init
from astro.ephem.bodies import get


def test_data_files_are_present(nyc):
    assert ephem.data_files_present()


def test_swiss_request_is_served_by_swiss(nyc):
    """Regression: swisseph silently substitutes Moshier when its data files are
    missing, reporting it only in a return flag. That substitution once made two
    'independent' backends agree perfectly because they were the same backend."""
    reading = calc(nyc.jd, get("sun").swe_id, source=Source.SWISS, body_name="sun")
    assert reading.source is Source.SWISS


def test_substitution_raises_rather_than_degrading_quietly(nyc, tmp_path):
    init(tmp_path)  # a directory with no data files
    try:
        with pytest.raises(SourceSubstituted) as caught:
            calc(nyc.jd, get("sun").swe_id, source=Source.SWISS, body_name="sun")
        assert "fetch_ephemeris" in str(caught.value)
        assert caught.value.served is Source.MOSHIER
    finally:
        init()


def test_substitution_can_be_opted_into(nyc, tmp_path):
    init(tmp_path)
    try:
        reading = calc(
            nyc.jd, get("sun").swe_id, source=Source.SWISS,
            body_name="sun", allow_substitution=True,
        )
        assert reading.source is Source.MOSHIER
    finally:
        init()


def test_moshier_cannot_do_asteroids(nyc, tmp_path):
    """Chiron is first-class in the hatch pack, and it needs seas_18.se1.
    Without the file there is no fallback at all -- it fails outright."""
    init(tmp_path)
    try:
        with pytest.raises(ephem.EphemerisError):
            calc(nyc.jd, get("chiron").swe_id, source=Source.SWISS, body_name="chiron")
    finally:
        init()


@pytest.mark.parametrize("body", ephem.CLASSICAL_TEN)
def test_swiss_and_moshier_agree(reference, body):
    """A genuine cross-check: the Swiss files are JPL-derived, Moshier is an
    independent analytical theory. Agreement here means the flags, units and
    time scale are right -- it is not two views of one computation."""
    swiss = ephem.position(reference.jd, body, source=Source.SWISS).longitude
    moshier = ephem.position(reference.jd, body, source=Source.MOSHIER).longitude
    arcseconds = abs(ephem.wrap180(swiss - moshier)) * 3600.0
    tolerance = 3.0 if body == "moon" else 1.0
    assert arcseconds < tolerance, f"{body}: {arcseconds:.3f}\" apart"


def test_retrograde_matches_speed_sign(nyc):
    for body in ephem.CLASSICAL_TEN:
        placement = ephem.position(nyc.jd, body)
        assert placement.retrograde == (placement.speed < 0)


def test_luminaries_never_retrograde(nyc):
    assert not ephem.position(nyc.jd, "sun").retrograde
    assert not ephem.position(nyc.jd, "moon").retrograde
