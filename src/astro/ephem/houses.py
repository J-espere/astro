"""House cusps, angles, and house frames.

Two things this module deliberately does NOT decide, because they are doctrine
and belong in schools/*.yaml:

  * which house system to use;
  * what a whole-sign frame is counted FROM. Counting from the Ascendant gives
    the Hellenistic frame; counting from the Sun gives the "zodiac houses" that
    Under A Libra God uses for most of its transit delineations. The geometry is
    identical, so both are served by whole_sign_from() and the choice is made
    above this layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import swisseph as swe

from .backend import EphemerisError


class HouseSystem(Enum):
    """The systems any school pack here might select."""

    PLACIDUS = "P"
    KOCH = "K"
    PORPHYRY = "O"
    REGIOMONTANUS = "R"
    CAMPANUS = "C"
    EQUAL = "A"            # equal from the Ascendant
    VEHLOW_EQUAL = "V"
    WHOLE_SIGN = "W"
    MERIDIAN = "X"         # axial rotation; used by the Uranian pack
    MORINUS = "M"
    ALCABITIUS = "B"
    TOPOCENTRIC = "T"
    HORIZONTAL = "H"

    @property
    def quadrant(self) -> bool:
        """Whether cusps derive from the ASC/MC quadrants (so, latitude-sensitive)."""
        return self in {
            HouseSystem.PLACIDUS,
            HouseSystem.KOCH,
            HouseSystem.PORPHYRY,
            HouseSystem.REGIOMONTANUS,
            HouseSystem.CAMPANUS,
            HouseSystem.ALCABITIUS,
            HouseSystem.TOPOCENTRIC,
        }

    @property
    def fails_near_poles(self) -> bool:
        """Time-based systems are undefined beyond the polar circle."""
        return self in {HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.TOPOCENTRIC}


class HouseSystemUndefined(EphemerisError):
    """The requested system has no solution at this latitude.

    Placidus and Koch divide diurnal arcs, and beyond the polar circle a body
    can have no rising or setting to divide. Most software silently substitutes
    Porphyry; this raises instead, because a chart quietly computed in a
    different system than the one named is a wrong chart.
    """

    def __init__(self, system: HouseSystem, latitude: float) -> None:
        super().__init__(
            f"{system.name.title()} houses are undefined at latitude {latitude:.4f}. "
            f"Pass fallback=HouseSystem.PORPHYRY (the usual convention) or "
            f"HouseSystem.WHOLE_SIGN to choose the substitution explicitly."
        )
        self.system = system
        self.latitude = latitude


@dataclass(frozen=True, slots=True)
class Houses:
    """Twelve cusps plus the angles, and an honest record of what produced them."""

    system: HouseSystem
    cusps: tuple[float, ...]   # 12 longitudes; cusps[0] is the 1st house
    ascendant: float
    midheaven: float
    armc: float                # right ascension of the MC
    vertex: float
    equatorial_ascendant: float
    latitude: float
    longitude: float
    requested_system: HouseSystem   # differs from `system` only if you asked for a fallback

    @property
    def descendant(self) -> float:
        return (self.ascendant + 180.0) % 360.0

    @property
    def imum_coeli(self) -> float:
        return (self.midheaven + 180.0) % 360.0

    @property
    def substituted(self) -> bool:
        return self.system is not self.requested_system

    @property
    def angles(self) -> dict[str, float]:
        return {
            "asc": self.ascendant,
            "dsc": self.descendant,
            "mc": self.midheaven,
            "ic": self.imum_coeli,
        }

    def house_of(self, longitude: float) -> int:
        """Which house (1-12) a longitude falls in.

        Handles cusps that wrap past 0 degrees, and unequal houses, by walking
        forward from each cusp rather than comparing raw longitudes.
        """
        lon = longitude % 360.0
        for index in range(12):
            start = self.cusps[index]
            span = (self.cusps[(index + 1) % 12] - start) % 360.0
            if span == 0.0:
                continue
            if (lon - start) % 360.0 < span:
                return index + 1
        return 12  # unreachable for well-formed cusps

    def span(self, house: int) -> float:
        """The width in degrees of a house (1-12). Quadrant houses are unequal."""
        index = house - 1
        return (self.cusps[(index + 1) % 12] - self.cusps[index]) % 360.0


def houses(
    jd_ut: float,
    latitude: float,
    longitude: float,
    system: HouseSystem = HouseSystem.PLACIDUS,
    *,
    fallback: HouseSystem | None = None,
) -> Houses:
    """Compute house cusps and angles.

    `latitude` and `longitude` are geographic, longitude positive east.
    """
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude {latitude} out of range")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude {longitude} out of range")

    try:
        cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, system.value.encode())
    except Exception as exc:
        if fallback is None:
            if system.fails_near_poles:
                raise HouseSystemUndefined(system, latitude) from exc
            raise EphemerisError(
                f"{system.name.title()} houses failed at lat={latitude}, lon={longitude}: {exc}"
            ) from exc
        resolved = houses(jd_ut, latitude, longitude, fallback)
        return Houses(
            system=fallback,
            cusps=resolved.cusps,
            ascendant=resolved.ascendant,
            midheaven=resolved.midheaven,
            armc=resolved.armc,
            vertex=resolved.vertex,
            equatorial_ascendant=resolved.equatorial_ascendant,
            latitude=latitude,
            longitude=longitude,
            requested_system=system,
        )

    return Houses(
        system=system,
        cusps=tuple(c % 360.0 for c in cusps[:12]),
        ascendant=ascmc[0] % 360.0,
        midheaven=ascmc[1] % 360.0,
        armc=ascmc[2] % 360.0,
        vertex=ascmc[3] % 360.0,
        equatorial_ascendant=ascmc[4] % 360.0,
        latitude=latitude,
        longitude=longitude,
        requested_system=system,
    )


def whole_sign_from(longitude: float) -> tuple[float, ...]:
    """Twelve whole-sign cusps counted from the sign containing `longitude`.

    Pass the Ascendant for the Hellenistic frame, or the Sun for the solar
    "zodiac houses" frame that Under A Libra God uses. The caller decides which.
    """
    first = (longitude // 30.0) * 30.0 % 360.0
    return tuple((first + 30.0 * i) % 360.0 for i in range(12))


def house_of_whole_sign(longitude: float, from_longitude: float) -> int:
    """Whole-sign house number (1-12) of `longitude`, counted from `from_longitude`."""
    first_sign = int(from_longitude // 30) % 12
    this_sign = int(longitude // 30) % 12
    return (this_sign - first_sign) % 12 + 1
