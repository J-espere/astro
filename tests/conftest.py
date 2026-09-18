"""Shared fixtures: the reference charts every golden test is pinned to."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pytest

from astro import ephem


@dataclass(frozen=True)
class Reference:
    """A birth chart used as a fixed point for regression tests."""

    key: str
    local: dt.datetime
    tz: str
    latitude: float
    longitude: float
    note: str

    @property
    def jd(self) -> float:
        _, jd = ephem.chart_moment(self.local, self.tz)
        return jd


REFERENCES = (
    Reference(
        "nyc_1985",
        dt.datetime(1985, 7, 13, 10, 30),
        "America/New_York",
        40.7128, -74.0060,
        "mid-latitude, daylight saving in force",
    ),
    Reference(
        "tromso_1990",
        dt.datetime(1990, 12, 2, 3, 15),
        "Europe/Oslo",
        69.6492, 18.9553,
        "above the polar circle: Placidus is undefined here",
    ),
    Reference(
        "sydney_2001",
        dt.datetime(2001, 1, 5, 23, 45),
        "Australia/Sydney",
        -33.8688, 151.2093,
        "southern hemisphere, east longitude",
    ),
    Reference(
        "quito_1970",
        dt.datetime(1970, 3, 21, 6, 0),
        "America/Guayaquil",
        -0.1807, -78.4678,
        "equator, near an equinox",
    ),
)


@pytest.fixture(scope="session", autouse=True)
def _ephemeris() -> None:
    ephem.init()
    if not ephem.data_files_present():
        pytest.exit(
            "Swiss Ephemeris data files missing. Run scripts/fetch_ephemeris.sh.",
            returncode=1,
        )


@pytest.fixture(params=REFERENCES, ids=lambda ref: ref.key)
def reference(request: pytest.FixtureRequest) -> Reference:
    return request.param


@pytest.fixture
def nyc() -> Reference:
    return REFERENCES[0]
