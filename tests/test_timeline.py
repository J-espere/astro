"""Timezone handling: the quiet source of charts that are an hour wrong."""

from __future__ import annotations

import datetime as dt

import pytest

from astro import ephem
from astro.ephem.timeline import TimeError, is_ambiguous, to_utc


def test_j2000_epoch():
    """2000-01-01 12:00 UT is Julian day 2451545.0, by definition."""
    moment = dt.datetime(2000, 1, 1, 12, 0, tzinfo=dt.UTC)
    assert ephem.julian_day(moment) == pytest.approx(2451545.0, abs=1e-9)


@pytest.mark.parametrize(
    "moment",
    [
        dt.datetime(1899, 12, 31, 23, 59, 30, tzinfo=dt.UTC),
        dt.datetime(1985, 7, 13, 14, 30, tzinfo=dt.UTC),
        dt.datetime(2026, 9, 18, 19, 15, 42, tzinfo=dt.UTC),
    ],
)
def test_julian_day_round_trips(moment):
    recovered = ephem.from_julian_day(ephem.julian_day(moment))
    assert abs((recovered - moment).total_seconds()) < 0.001


def test_daylight_saving_offset_is_applied():
    """13 July 1985 in New York is EDT (UTC-4), not EST (UTC-5)."""
    utc = to_utc(dt.datetime(1985, 7, 13, 10, 30), "America/New_York")
    assert utc == dt.datetime(1985, 7, 13, 14, 30, tzinfo=dt.UTC)


def test_winter_uses_standard_time():
    utc = to_utc(dt.datetime(1985, 1, 13, 10, 30), "America/New_York")
    assert utc == dt.datetime(1985, 1, 13, 15, 30, tzinfo=dt.UTC)


def test_nonexistent_local_time_is_refused():
    """02:30 on a spring-forward morning never happened. Accepting it silently
    would shift every angle in the chart by about 15 degrees."""
    with pytest.raises(TimeError, match="does not exist"):
        to_utc(dt.datetime(2026, 3, 8, 2, 30), "America/New_York")


def test_ambiguous_local_time_is_detectable_and_selectable():
    """01:30 on a fall-back morning happens twice; the caller picks which."""
    local = dt.datetime(2026, 11, 1, 1, 30)
    assert is_ambiguous(local, "America/New_York")
    first = to_utc(local, "America/New_York", fold=0)
    second = to_utc(local, "America/New_York", fold=1)
    assert (second - first) == dt.timedelta(hours=1)


def test_aware_datetime_is_rejected():
    with pytest.raises(TimeError):
        to_utc(dt.datetime(1985, 7, 13, 10, 30, tzinfo=dt.UTC), "America/New_York")


def test_unknown_zone_is_rejected():
    with pytest.raises(TimeError, match="unknown timezone"):
        to_utc(dt.datetime(1985, 7, 13, 10, 30), "Mars/Olympus_Mons")
