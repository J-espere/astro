"""Event search: solving for WHEN, not just computing WHERE.

Everything astrological that has a date -- an exact aspect, an ingress, a
station, a return, the edges of a retrograde shadow -- is a root of some
function of time. This module finds those roots. It is the difference between
software that can draw today's chart and software that can draw a timeline.

No scipy: the functions here are smooth and cheaply evaluated, so a bracketed
bisection is both sufficient and easier to reason about at the wrap points,
which is where angular root-finding usually goes wrong.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .backend import Source
from .positions import position

# One second of a day. Refining past this is meaningless: the underlying
# ephemeris is not that precise, and birth times never are.
DEFAULT_TOLERANCE_DAYS = 1.0 / 86400.0


def wrap180(degrees: float) -> float:
    """Fold an angle into (-180, 180]."""
    value = (degrees + 180.0) % 360.0 - 180.0
    return 180.0 if value == -180.0 else value


def separation(lon_a: float, lon_b: float) -> float:
    """Unsigned angular separation, 0 to 180 degrees."""
    return abs(wrap180(lon_a - lon_b))


def longitude_of(body: str, *, source: Source = Source.SWISS) -> Callable[[float], float]:
    """A body's longitude as a function of Julian day."""
    return lambda jd: position(jd, body, source=source).longitude


def fixed(longitude: float) -> Callable[[float], float]:
    """A natal point: a longitude that does not move."""
    value = longitude % 360.0
    return lambda _jd: value


def bisect(
    f: Callable[[float], float],
    lo: float,
    hi: float,
    *,
    tolerance: float = DEFAULT_TOLERANCE_DAYS,
    max_iterations: int = 200,
) -> float:
    """Refine a bracketed sign change to a root.

    Requires f(lo) and f(hi) to straddle zero; the samplers below guarantee it.
    """
    f_lo, f_hi = f(lo), f(hi)
    if f_lo == 0.0:
        return lo
    if f_hi == 0.0:
        return hi
    if (f_lo > 0.0) == (f_hi > 0.0):
        raise ValueError(f"root not bracketed: f({lo})={f_lo}, f({hi})={f_hi}")

    for _ in range(max_iterations):
        if hi - lo <= tolerance:
            break
        mid = (lo + hi) / 2.0
        f_mid = f(mid)
        if f_mid == 0.0:
            return mid
        if (f_mid > 0.0) == (f_lo > 0.0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _scan(
    f: Callable[[float], float],
    jd_from: float,
    jd_to: float,
    step: float,
    *,
    tolerance: float = DEFAULT_TOLERANCE_DAYS,
    guard: float = 180.0,
) -> list[float]:
    """Find every sign change of f over an interval and refine each to a root.

    `guard` rejects apparent crossings that are really the function wrapping
    from +180 to -180 rather than passing through zero -- the single most
    common bug in angular event search.
    """
    roots: list[float] = []
    jd = jd_from
    previous = f(jd)
    while jd < jd_to:
        nxt = min(jd + step, jd_to)
        current = f(nxt)
        if previous == 0.0:
            roots.append(jd)
        elif (previous > 0.0) != (current > 0.0) and abs(current - previous) < guard:
            roots.append(bisect(f, jd, nxt, tolerance=tolerance))
        jd, previous = nxt, current
    return roots


def _auto_step(moving: str, target: str | None, jd: float) -> float:
    """A sample step that advances roughly 2 degrees of relative motion.

    Two degrees is comfortably finer than the narrowest feature these functions
    have, and keeps Moon searches from stepping straight over an aspect.
    """
    speed = abs(position(jd, moving).speed)
    if target is not None:
        speed += abs(position(jd, target).speed)
    return max(0.02, min(5.0, 2.0 / max(speed, 0.01)))


@dataclass(frozen=True, slots=True)
class Hit:
    """An exact aspect, at the instant it perfects."""

    jd: float
    moving: str
    target: str
    angle: float
    longitude_moving: float
    longitude_target: float
    applying_before: bool   # was the separation closing on the way in?

    @property
    def separating_after(self) -> bool:
        return self.applying_before


def exact_aspects(
    moving: str,
    target: str | float,
    angle: float,
    jd_from: float,
    jd_to: float,
    *,
    step: float | None = None,
    tolerance: float = DEFAULT_TOLERANCE_DAYS,
) -> list[Hit]:
    """Every instant in [jd_from, jd_to] where `moving` perfects `angle` to `target`.

    `target` is another body's name, or a fixed longitude for a natal point.
    Both sides of a non-symmetric aspect are found: a square is solved at both
    +90 and -90, because those are different events.
    """
    target_name = target if isinstance(target, str) else f"{float(target):.4f}"
    target_fn = longitude_of(target) if isinstance(target, str) else fixed(float(target))
    moving_fn = longitude_of(moving)

    if step is None:
        step = _auto_step(moving, target if isinstance(target, str) else None, jd_from)

    offsets = {angle % 360.0, (-angle) % 360.0}
    hits: list[Hit] = []
    for offset in offsets:
        def error(jd: float, offset: float = offset) -> float:
            return wrap180(moving_fn(jd) - target_fn(jd) - offset)

        for root in _scan(error, jd_from, jd_to, step, tolerance=tolerance):
            before = separation(moving_fn(root - step), target_fn(root - step))
            hits.append(
                Hit(
                    jd=root,
                    moving=moving,
                    target=target_name,
                    angle=angle,
                    longitude_moving=moving_fn(root),
                    longitude_target=target_fn(root),
                    applying_before=before > separation(moving_fn(root), target_fn(root)),
                )
            )
    return sorted(hits, key=lambda hit: hit.jd)


@dataclass(frozen=True, slots=True)
class Ingress:
    """A body crossing a longitude boundary -- a sign, or a house cusp."""

    jd: float
    body: str
    boundary: float
    direct: bool   # False when it backed in retrograde


def ingresses(
    body: str,
    jd_from: float,
    jd_to: float,
    *,
    boundaries: tuple[float, ...] | None = None,
    step: float | None = None,
    tolerance: float = DEFAULT_TOLERANCE_DAYS,
) -> list[Ingress]:
    """Every boundary crossing in the interval. Defaults to the twelve signs.

    Retrograde re-crossings are included and flagged, not filtered: a planet
    backing into the previous sign and returning is three events, and all three
    show up in a life.
    """
    bounds = boundaries if boundaries is not None else tuple(30.0 * i for i in range(12))
    lon = longitude_of(body)
    if step is None:
        step = _auto_step(body, None, jd_from)

    found: list[Ingress] = []
    for boundary in bounds:
        def error(jd: float, boundary: float = boundary) -> float:
            return wrap180(lon(jd) - boundary)

        for root in _scan(error, jd_from, jd_to, step, tolerance=tolerance):
            found.append(
                Ingress(
                    jd=root,
                    body=body,
                    boundary=boundary % 360.0,
                    direct=position(root, body).speed >= 0.0,
                )
            )
    return sorted(found, key=lambda event: event.jd)


@dataclass(frozen=True, slots=True)
class Station:
    """The instant a body's apparent motion reverses."""

    jd: float
    body: str
    direction: Literal["retrograde", "direct"]  # the motion it turns INTO
    longitude: float


def stations(
    body: str,
    jd_from: float,
    jd_to: float,
    *,
    step: float | None = None,
    tolerance: float = DEFAULT_TOLERANCE_DAYS,
) -> list[Station]:
    """Every station in the interval, in order."""
    speed = lambda jd: position(jd, body).speed  # noqa: E731
    if step is None:
        step = max(0.25, _auto_step(body, None, jd_from))

    found: list[Station] = []
    for root in _scan(speed, jd_from, jd_to, step, tolerance=tolerance, guard=float("inf")):
        found.append(
            Station(
                jd=root,
                body=body,
                direction="retrograde" if speed(root + step) < 0 else "direct",
                longitude=position(root, body).longitude,
            )
        )
    return found


@dataclass(frozen=True, slots=True)
class Retrograde:
    """A retrograde passage, with its shadow periods.

    Under A Libra God treats the shadows as first-class and locates the
    resolution of the retrograde in the post-shadow, so these are computed
    rather than left implicit:

        pre_shadow_start   body first reaches the degree it will later station direct on
        station_retrograde apparent motion reverses
        station_direct     apparent motion resumes
        post_shadow_end    body re-reaches the degree it stationed retrograde on
    """

    body: str
    station_retrograde: float
    station_direct: float
    pre_shadow_start: float | None
    post_shadow_end: float | None
    degree_retrograde: float
    degree_direct: float

    @property
    def shadow_span_days(self) -> float | None:
        if self.pre_shadow_start is None or self.post_shadow_end is None:
            return None
        return self.post_shadow_end - self.pre_shadow_start

    @property
    def retrograde_span_days(self) -> float:
        return self.station_direct - self.station_retrograde


def retrogrades(
    body: str,
    jd_from: float,
    jd_to: float,
    *,
    search_margin_days: float = 400.0,
) -> list[Retrograde]:
    """Retrograde passages overlapping the interval, with shadow boundaries.

    The search is widened by `search_margin_days` on both sides, because a
    shadow reaches outside the retrograde itself and a passage that straddles
    the interval edge is still a passage.
    """
    lo, hi = jd_from - search_margin_days, jd_to + search_margin_days
    marks = stations(body, lo, hi)

    passages: list[Retrograde] = []
    for index, mark in enumerate(marks):
        if mark.direction != "retrograde" or index + 1 >= len(marks):
            continue
        direct = marks[index + 1]
        if direct.direction != "direct":
            continue
        if direct.jd < jd_from or mark.jd > jd_to:
            continue

        pre = exact_aspects(body, direct.longitude, 0.0, lo, mark.jd)
        post = exact_aspects(body, mark.longitude, 0.0, direct.jd, hi)
        passages.append(
            Retrograde(
                body=body,
                station_retrograde=mark.jd,
                station_direct=direct.jd,
                pre_shadow_start=pre[-1].jd if pre else None,
                post_shadow_end=post[0].jd if post else None,
                degree_retrograde=mark.longitude,
                degree_direct=direct.longitude,
            )
        )
    return passages


def returns(
    body: str,
    natal_longitude: float,
    jd_from: float,
    jd_to: float,
) -> list[Hit]:
    """Every return of a body to a natal longitude -- solar, lunar, Saturn, nodal."""
    return exact_aspects(body, natal_longitude, 0.0, jd_from, jd_to)
