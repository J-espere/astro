"""Event search, checked against events with known dates.

A regression suite built only on the library's own output can drift as a whole
and never notice. These pin the solver to things that happened.
"""

from __future__ import annotations

import datetime as dt

import pytest

from astro import ephem
from astro.ephem.search import bisect, exact_aspects, ingresses, retrogrades, stations, wrap180


def _jd(year, month, day, hour=0.0):
    return ephem.julian_day(
        dt.datetime(year, month, day, tzinfo=dt.UTC)
    ) + hour / 24.0


def _date(jd):
    return ephem.from_julian_day(jd).date()


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0), (90, 90), (180, 180), (181, -179), (359, -1), (360, 0), (-181, 179), (720, 0)],
)
def test_wrap180(value, expected):
    assert wrap180(value) == pytest.approx(expected)


def test_separation_is_symmetric_and_bounded():
    for a, b in [(0, 359), (10, 350), (180, 0), (95, 5)]:
        assert ephem.separation(a, b) == pytest.approx(ephem.separation(b, a))
        assert 0.0 <= ephem.separation(a, b) <= 180.0


def test_bisect_requires_a_bracket():
    with pytest.raises(ValueError, match="not bracketed"):
        bisect(lambda x: x**2 + 1.0, 0.0, 1.0)


def test_march_equinox_is_the_suns_aries_ingress():
    """The equinox is definitionally the Sun reaching 0 Aries. In 2026 that is
    20 March; the solver has to agree with the almanac, not just with itself."""
    found = ingresses("sun", _jd(2026, 3, 15), _jd(2026, 3, 25), boundaries=(0.0,))
    assert len(found) == 1
    assert _date(found[0].jd) == dt.date(2026, 3, 20)
    assert ephem.position(found[0].jd, "sun").longitude == pytest.approx(0.0, abs=1e-4)


def test_great_conjunction_of_2020():
    """Jupiter conjunct Saturn on 21 December 2020, at 0 degrees Aquarius --
    the closest the pair had come since 1623 and a well-documented date."""
    hits = exact_aspects("jupiter", "saturn", 0.0, _jd(2020, 11, 1), _jd(2021, 2, 1))
    assert len(hits) == 1
    hit = hits[0]
    assert _date(hit.jd) == dt.date(2020, 12, 21)
    position = ephem.position(hit.jd, "jupiter")
    assert position.sign == "aquarius"
    assert position.degree_in_sign < 1.0
    assert ephem.separation(hit.longitude_moving, hit.longitude_target) < 1e-4


def test_saturn_return_lands_near_the_expected_age():
    """The book builds its life-cycle model on this: Saturn comes back at
    about 29.5 years, and the software has to reproduce that, not assume it."""
    natal = _jd(1985, 7, 13, 14.5)
    natal_saturn = ephem.position(natal, "saturn").longitude
    found = ephem.returns("saturn", natal_saturn, natal + 365.25 * 27, natal + 365.25 * 32)
    assert found
    age = (found[0].jd - natal) / 365.25
    assert 28.0 < age < 31.0


def test_aspect_solver_finds_both_sides_of_a_square():
    """A waxing square and a waning square are different events. Solving only
    +90 silently loses half of them."""
    hits = exact_aspects("sun", "saturn", 90.0, _jd(2026, 1, 1), _jd(2027, 1, 1))
    assert len(hits) == 2
    for hit in hits:
        assert ephem.separation(hit.longitude_moving, hit.longitude_target) == pytest.approx(
            90.0, abs=1e-4
        )


def test_every_hit_is_actually_exact():
    for angle in (0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0):
        hits = exact_aspects("mars", "jupiter", angle, _jd(2026, 1, 1), _jd(2027, 1, 1))
        for hit in hits:
            assert ephem.separation(
                hit.longitude_moving, hit.longitude_target
            ) == pytest.approx(angle, abs=1e-4)


def test_sun_enters_every_sign_once_a_year():
    found = ingresses("sun", _jd(2026, 1, 1), _jd(2026, 12, 31, 23.9))
    assert len(found) == 12
    assert all(event.direct for event in found)
    assert sorted(event.boundary for event in found) == [30.0 * i for i in range(12)]


def test_mercury_stations_three_or_four_times_a_year():
    """Mercury retrogrades three times in most years, four occasionally --
    so six or eight stations."""
    marks = stations("mercury", _jd(2026, 1, 1), _jd(2027, 1, 1))
    assert 6 <= len(marks) <= 8
    assert len(marks) % 2 == 0
    for earlier, later in zip(marks, marks[1:], strict=False):
        assert earlier.direction != later.direction


def test_stations_have_near_zero_speed():
    for mark in stations("mars", _jd(2024, 1, 1), _jd(2026, 1, 1)):
        assert abs(ephem.position(mark.jd, "mars").speed) < 1e-4


@pytest.mark.slow
def test_retrograde_shadows_are_ordered_and_bracket_the_retrograde():
    """The doctrine treats the shadows as first-class: the pre-shadow opens
    when the body first reaches the degree it will later station direct on, and
    the post-shadow closes when it re-reaches its retrograde station degree.
    Resolution is located in the post-shadow, so these boundaries carry meaning
    and have to be right."""
    passages = retrogrades("mercury", _jd(2026, 1, 1), _jd(2027, 1, 1))
    assert passages
    for passage in passages:
        assert passage.pre_shadow_start is not None
        assert passage.post_shadow_end is not None
        assert (
            passage.pre_shadow_start
            < passage.station_retrograde
            < passage.station_direct
            < passage.post_shadow_end
        )
        # The shadow is the full ground covered twice, so it must exceed the
        # retrograde it contains.
        assert passage.shadow_span_days > passage.retrograde_span_days
        assert ephem.position(passage.pre_shadow_start, "mercury").longitude == pytest.approx(
            passage.degree_direct, abs=1e-3
        )
        assert ephem.position(passage.post_shadow_end, "mercury").longitude == pytest.approx(
            passage.degree_retrograde, abs=1e-3
        )


def test_moon_search_does_not_step_over_events():
    """The Moon moves ~13 degrees a day, so a step sized for planets misses its
    aspects entirely. The sampler has to adapt to the bodies involved."""
    hits = exact_aspects("moon", 0.0, 0.0, _jd(2026, 1, 1), _jd(2026, 2, 1))
    assert len(hits) == 1  # one lunar return to 0 Aries per month
