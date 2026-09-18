"""Swiss Ephemeris backend: initialisation, flags, and honest source reporting.

The one thing this module exists to prevent: swisseph does not error when its
data files are missing. It silently substitutes the Moshier analytical theory
and reports the substitution only in a return flag almost nobody reads. Two
"independent" backends then agree perfectly, because they are the same backend,
and a cross-check built on that agreement proves nothing.

Every call here checks the served source against the requested one.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import swisseph as swe

DEFAULT_EPHE_PATH = Path(__file__).resolve().parents[3] / "data" / "ephe"

# Degrees per day below which a body reads as stationary rather than moving.
STATIONARY_THRESHOLD = 1e-4


class Source(Enum):
    """Which computation the positions actually came from."""

    SWISS = "swiss"      # compressed JPL-derived data files (needs data/ephe)
    MOSHIER = "moshier"  # analytical theory, no data files, no asteroids
    JPL = "jpl"          # full JPL ephemeris file (not shipped)

    @property
    def flag(self) -> int:
        return {
            Source.SWISS: swe.FLG_SWIEPH,
            Source.MOSHIER: swe.FLG_MOSEPH,
            Source.JPL: swe.FLG_JPLEPH,
        }[self]

    @classmethod
    def from_retflag(cls, retflag: int) -> Source:
        if retflag & swe.FLG_MOSEPH:
            return cls.MOSHIER
        if retflag & swe.FLG_JPLEPH:
            return cls.JPL
        return cls.SWISS


class EphemerisError(RuntimeError):
    """A Swiss Ephemeris call failed."""


class SourceSubstituted(EphemerisError):
    """swisseph served a different ephemeris than the one requested.

    Almost always means the data files are missing. Raised rather than warned:
    a silent downgrade invalidates asteroid positions entirely and quietly
    degrades everything else.
    """

    def __init__(self, requested: Source, served: Source, body: str) -> None:
        super().__init__(
            f"requested {requested.value} ephemeris for {body}, got {served.value}. "
            f"Run scripts/fetch_ephemeris.sh, or pass source=Source.MOSHIER explicitly."
        )
        self.requested = requested
        self.served = served


_init_lock = threading.Lock()
_ephe_path: Path | None = None


def init(ephe_path: str | os.PathLike[str] | None = None) -> Path:
    """Point swisseph at the data files. Idempotent and safe to call repeatedly.

    swisseph keeps this as process-global state, so this is guarded by a lock
    and records what it set.
    """
    global _ephe_path
    path = Path(ephe_path) if ephe_path is not None else DEFAULT_EPHE_PATH
    with _init_lock:
        if _ephe_path != path:
            swe.set_ephe_path(str(path))
            _ephe_path = path
    return path


def ephe_path() -> Path | None:
    """The data-file path currently set, or None if init() has not run."""
    return _ephe_path


def data_files_present(ephe_path_: str | os.PathLike[str] | None = None) -> bool:
    """Whether the binary data files the Swiss ephemeris needs are on disk."""
    path = Path(ephe_path_) if ephe_path_ is not None else (_ephe_path or DEFAULT_EPHE_PATH)
    return all((path / name).is_file() for name in ("sepl_18.se1", "semo_18.se1", "seas_18.se1"))


@dataclass(frozen=True, slots=True)
class Reading:
    """One body's state at one instant, with the ephemeris that produced it."""

    longitude: float       # ecliptic longitude, degrees [0, 360)
    latitude: float        # ecliptic latitude, degrees
    distance: float        # AU
    speed_longitude: float # degrees/day; negative means retrograde
    speed_latitude: float
    speed_distance: float
    source: Source

    @property
    def retrograde(self) -> bool:
        return self.speed_longitude < 0.0

    @property
    def stationary(self) -> bool:
        """Apparent motion below the threshold at which a station is readable."""
        return abs(self.speed_longitude) < STATIONARY_THRESHOLD


def calc(
    jd_ut: float,
    body_id: int,
    *,
    source: Source = Source.SWISS,
    extra_flags: int = 0,
    body_name: str = "",
    allow_substitution: bool = False,
) -> Reading:
    """Compute one body at one Julian day (UT).

    Raises SourceSubstituted if swisseph quietly served a different ephemeris,
    unless allow_substitution is set.
    """
    flags = source.flag | swe.FLG_SPEED | extra_flags
    try:
        values, retflag = swe.calc_ut(jd_ut, body_id, flags)
    except Exception as exc:  # swisseph raises a bare Error
        raise EphemerisError(f"{body_name or body_id} at jd={jd_ut}: {exc}") from exc

    if retflag < 0:
        raise EphemerisError(f"{body_name or body_id} at jd={jd_ut}: swisseph returned {retflag}")

    served = Source.from_retflag(retflag)
    if served is not source and not allow_substitution:
        raise SourceSubstituted(source, served, body_name or str(body_id))

    return Reading(
        longitude=values[0] % 360.0,
        latitude=values[1],
        distance=values[2],
        speed_longitude=values[3],
        speed_latitude=values[4],
        speed_distance=values[5],
        source=served,
    )


def close() -> None:
    """Release swisseph's file handles."""
    global _ephe_path
    swe.close()
    _ephe_path = None
