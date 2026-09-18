"""Body positions: the public read path over backend.calc()."""

from __future__ import annotations

from dataclasses import dataclass

from . import bodies
from .backend import Reading, Source, calc, init

SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)


@dataclass(frozen=True, slots=True)
class Position:
    """A body's placement, in the terms a chart actually uses."""

    body: str
    reading: Reading

    @property
    def longitude(self) -> float:
        return self.reading.longitude

    @property
    def retrograde(self) -> bool:
        return self.reading.retrograde

    @property
    def speed(self) -> float:
        return self.reading.speed_longitude

    @property
    def sign(self) -> str:
        return SIGNS[int(self.longitude // 30) % 12]

    @property
    def sign_index(self) -> int:
        return int(self.longitude // 30) % 12

    @property
    def degree_in_sign(self) -> float:
        return self.longitude % 30.0

    @property
    def decan(self) -> int:
        """1, 2 or 3 -- the 10-degree division within the sign."""
        return int(self.degree_in_sign // 10) + 1

    def format(self) -> str:
        deg = int(self.degree_in_sign)
        minutes = int(round((self.degree_in_sign - deg) * 60))
        if minutes == 60:
            deg, minutes = deg + 1, 0
        mark = " R" if self.retrograde else ""
        return f"{deg:2d}°{minutes:02d}' {self.sign.title()}{mark}"


def position(
    jd_ut: float,
    body_name: str,
    *,
    source: Source = Source.SWISS,
    allow_substitution: bool = False,
) -> Position:
    """One body at one instant.

    The south nodes are derived by opposition rather than computed, which is
    exact: swisseph has no south-node id.
    """
    init()
    body = bodies.get(body_name)

    if body.derived:
        counterpart = bodies.opposite_of(body_name)
        if counterpart is None:
            raise KeyError(f"{body_name!r} is derived but has no counterpart")
        base = position(
            jd_ut, counterpart, source=source, allow_substitution=allow_substitution
        ).reading
        return Position(
            body=body_name,
            reading=Reading(
                longitude=(base.longitude + 180.0) % 360.0,
                latitude=-base.latitude,
                distance=base.distance,
                speed_longitude=base.speed_longitude,
                speed_latitude=-base.speed_latitude,
                speed_distance=base.speed_distance,
                source=base.source,
            ),
        )

    return Position(
        body=body_name,
        reading=calc(
            jd_ut,
            body.swe_id,
            source=source,
            body_name=body_name,
            allow_substitution=allow_substitution,
        ),
    )


def positions(
    jd_ut: float,
    body_names: tuple[str, ...] = bodies.CLASSICAL_TEN,
    *,
    source: Source = Source.SWISS,
    allow_substitution: bool = False,
) -> dict[str, Position]:
    """Several bodies at one instant, keyed by name."""
    return {
        name: position(
            jd_ut, name, source=source, allow_substitution=allow_substitution
        )
        for name in body_names
    }
