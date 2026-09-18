"""Civil time to Julian day, with the timezone handling done properly.

Historical DST and pre-standardisation local mean time are the classic source
of charts that are quietly an hour wrong, which moves every angle by ~15 deg.
Everything here goes through the IANA database rather than a fixed offset.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

J2000 = 2451545.0


class TimeError(ValueError):
    """A civil time could not be resolved to an unambiguous instant."""


def to_utc(
    local: datetime,
    tz_name: str,
    *,
    fold: int = 0,
    strict: bool = True,
) -> datetime:
    """Resolve a naive local datetime in a named zone to UTC.

    A local time inside a DST fall-back hour happens twice; `fold` selects
    which (0 = first, the pre-transition reading). A local time inside a
    spring-forward gap never happened at all -- with strict=True that is an
    error rather than a silently shifted chart.
    """
    if local.tzinfo is not None:
        raise TimeError("pass a naive local datetime; the zone is given separately")
    try:
        zone = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise TimeError(f"unknown timezone {tz_name!r}") from exc

    aware = local.replace(tzinfo=zone, fold=fold)
    if strict:
        # A gap time round-trips to a different wall clock than it started with.
        round_tripped = aware.astimezone(UTC).astimezone(zone)
        if round_tripped.replace(tzinfo=None) != local:
            raise TimeError(
                f"{local.isoformat()} does not exist in {tz_name} "
                f"(daylight-saving gap); nearest valid time is "
                f"{round_tripped.replace(tzinfo=None).isoformat()}"
            )
    return aware.astimezone(UTC)


def is_ambiguous(local: datetime, tz_name: str) -> bool:
    """Whether this local time occurs twice (a DST fall-back repeat)."""
    zone = ZoneInfo(tz_name)
    return local.replace(tzinfo=zone, fold=0).utcoffset() != local.replace(
        tzinfo=zone, fold=1
    ).utcoffset()


def julian_day(moment: datetime) -> float:
    """Julian day (UT) for a timezone-aware datetime."""
    if moment.tzinfo is None:
        raise TimeError("julian_day requires a timezone-aware datetime")
    utc = moment.astimezone(UTC)
    hour = utc.hour + utc.minute / 60.0 + (utc.second + utc.microsecond / 1e6) / 3600.0
    return swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL)


def from_julian_day(jd_ut: float) -> datetime:
    """The UTC datetime for a Julian day (UT). Inverse of julian_day()."""
    year, month, day, hour = swe.revjul(jd_ut, swe.GREG_CAL)
    whole = int(hour)
    return datetime(year, month, day, tzinfo=UTC) + timedelta(
        hours=whole, seconds=round((hour - whole) * 3600.0, 6)
    )


def chart_moment(
    local: datetime, tz_name: str, *, fold: int = 0, strict: bool = True
) -> tuple[datetime, float]:
    """Convenience: naive local time + zone -> (UTC datetime, Julian day)."""
    utc = to_utc(local, tz_name, fold=fold, strict=strict)
    return utc, julian_day(utc)
