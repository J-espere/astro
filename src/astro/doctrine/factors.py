"""Factor keys: the stable address of an astrological configuration.

Everything downstream hangs off these -- delineations, your own annotations,
the ranking engine, the comparison view. So the scheme has to satisfy two
things that pull against each other:

  * **Stable.** A key written today must still resolve in two years, or the
    delineation attached to it is orphaned.
  * **Open.** Cosmodynamics is a mechanics-first system and may address things
    no other school here does -- declination, distance, phase angle, something
    unnamed. A closed taxonomy would make it unrecordable.

The resolution is a component grammar with a registry of known component types
and an explicit path for new ones. An unrecognised component is never silently
accepted and never silently dropped: it raises, naming what it would take to
register it. That is the project's first rule applied to its addressing scheme.

    sign:aries
    body:venus sign:leo
    body:saturn house:11@solar
    aspect:square body:saturn body:venus
    transit:saturn aspect:conjunction natal:sun
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from ..ephem import SIGNS, bodies
from ..ephem.houses import HouseSystem

ANGLES = ("asc", "dsc", "mc", "ic")
ASPECTS = {
    "conjunction": 0.0, "semisextile": 30.0, "semisquare": 45.0, "sextile": 60.0,
    "square": 90.0, "trine": 120.0, "sesquiquadrate": 135.0, "inconjunct": 150.0,
    "quincunx": 150.0, "opposition": 180.0, "quintile": 72.0, "biquintile": 144.0,
}
# Which frame a house number is counted in. The distinction is load-bearing:
# Under A Libra God writes most of its transit delineations in the solar frame
# and its natal ones in the angular frame, and conflating them silently
# mis-files a large part of the book.
HOUSE_FRAMES = ("natal", "solar", "asc")

_VALUE = re.compile(r"^[a-z0-9_]+$")


class FactorError(ValueError):
    """A factor key could not be parsed, validated, or canonicalised."""


@dataclass(frozen=True, slots=True)
class ComponentType:
    """One addressable dimension of a factor."""

    name: str
    order: int                       # position in canonical form
    validate: Callable[[str], None]
    repeatable: bool = False         # e.g. two bodies in an aspect
    symmetric: bool = False          # repeats sort, because order carries no meaning
    takes_qualifier: bool = False    # the '@frame' suffix on houses
    description: str = ""


def _one_of(name: str, allowed: Iterable[str]) -> Callable[[str], None]:
    allowed = tuple(allowed)

    def check(value: str) -> None:
        if value not in allowed:
            shown = ", ".join(sorted(allowed)[:14])
            raise FactorError(f"unknown {name} {value!r}; expected one of: {shown}...")

    return check


def _house_number(value: str) -> None:
    number, _, frame = value.partition("@")
    if not number.isdigit() or not 1 <= int(number) <= 12:
        raise FactorError(f"house must be 1-12, got {number!r}")
    if frame and frame not in HOUSE_FRAMES:
        raise FactorError(
            f"unknown house frame {frame!r}; expected one of: {', '.join(HOUSE_FRAMES)}. "
            f"The frame is not decoration -- 'house:11@natal' and 'house:11@solar' are "
            f"different claims about different parts of a chart."
        )


def _free_text(_value: str) -> None:
    return None


_TYPES: dict[str, ComponentType] = {}


def register_component(component: ComponentType, *, replace: bool = False) -> None:
    """Add a component type. Schools with their own dimensions extend here."""
    if component.name in _TYPES and not replace:
        raise FactorError(f"component type {component.name!r} already registered")
    _TYPES[component.name] = component


for _component in (
    ComponentType("transit", 0, _free_text, description="the transiting body"),
    ComponentType("progressed", 0, _free_text, description="the progressed body"),
    ComponentType("body", 10, _one_of("body", bodies.names()), repeatable=True,
                  symmetric=True, description="a planet, point or asteroid"),
    ComponentType("angle", 15, _one_of("angle", ANGLES), repeatable=True, symmetric=True,
                  description="ASC, DSC, MC or IC"),
    ComponentType("natal", 18, _free_text, repeatable=True,
                  description="the natal point a transit contacts"),
    ComponentType("aspect", 20, _one_of("aspect", ASPECTS), description="an angular relation"),
    ComponentType("sign", 30, _one_of("sign", SIGNS), description="a zodiac sign"),
    ComponentType("house", 40, _house_number, takes_qualifier=True,
                  description="house 1-12, optionally @natal / @solar / @asc"),
    ComponentType("decan", 50, _one_of("decan", ("1", "2", "3")), description="10-degree third"),
    ComponentType("phase", 60, _one_of(
        "phase", ("pre_shadow", "retrograde", "post_shadow", "direct", "station")),
        description="retrograde cycle phase"),
    ComponentType("star", 70, _free_text, description="a fixed star"),
    ComponentType("condition", 80, _free_text, repeatable=True,
                  description="sect, dignity, or another school-specific condition"),
):
    register_component(_component)


def component_types() -> dict[str, ComponentType]:
    return dict(_TYPES)


@dataclass(frozen=True, slots=True)
class Factor:
    """A canonical, comparable address for one astrological configuration."""

    components: tuple[tuple[str, str], ...] = field(default=())

    def __str__(self) -> str:
        return " ".join(f"{name}:{value}" for name, value in self.components)

    def __repr__(self) -> str:
        return f"Factor({str(self)!r})"

    @property
    def types(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(name for name, _ in self.components))

    def get(self, type_name: str) -> tuple[str, ...]:
        return tuple(value for name, value in self.components if name == type_name)

    def has(self, type_name: str) -> bool:
        return any(name == type_name for name, _ in self.components)

    def with_component(self, type_name: str, value: str) -> Factor:
        return parse(f"{self} {type_name}:{value}".strip())

    def without(self, type_name: str) -> Factor:
        kept = " ".join(f"{n}:{v}" for n, v in self.components if n != type_name)
        return parse(kept) if kept else Factor(())

    def generalisations(self, *, max_components: int = 6) -> tuple[Factor, ...]:
        """Progressively less specific versions of this factor, most specific first.

        A delineation for `body:saturn house:11@solar` is the best answer for
        that placement, but if none has been written, `house:11@solar` and
        `body:saturn` are both relevant and should be offered rather than
        nothing. Retrieval walks this ladder and always reports which rung
        answered, so a general note is never mistaken for a specific one.

        These are SUBSETS, not prefixes. Dropping only trailing components
        would mean `body:saturn sign:aries house:11` never finds an entry
        written for `body:saturn house:11`, because the sign sits between them
        in canonical order -- so the most useful generalisation of all would be
        invisible. Above `max_components` the subset count stops being
        reasonable and this falls back to dropping from the end.
        """
        from itertools import combinations

        count = len(self.components)
        if count > max_components:
            ladder = [self]
            remaining = list(self.components)
            while len(remaining) > 1:
                remaining = remaining[:-1]
                ladder.append(Factor(tuple(remaining)))
            return tuple(ladder)

        ladder: list[Factor] = []
        for size in range(count, 0, -1):
            for subset in combinations(self.components, size):
                ladder.append(Factor(subset))
        return tuple(ladder)


def parse(text: str, *, allow_unknown_types: bool = False) -> Factor:
    """Parse a factor key into canonical form.

    Canonicalising means `sign:leo body:venus` and `body:venus sign:leo` are the
    same factor, and a symmetric aspect's bodies sort, so `venus square saturn`
    and `saturn square venus` do not become two separate entries with two
    separate delineations that drift apart.
    """
    tokens = [token for token in text.replace(",", " ").split() if token]
    if not tokens:
        raise FactorError("empty factor key")

    parsed: list[tuple[str, str]] = []
    for token in tokens:
        name, separator, value = token.partition(":")
        name = name.strip().lower()
        value = value.strip().lower()
        if not separator:
            raise FactorError(
                f"{token!r} is not a component: expected '<type>:<value>', "
                f"for example 'sign:aries' or 'body:saturn house:11@solar'"
            )
        if not value:
            raise FactorError(f"{token!r} has no value")

        component = _TYPES.get(name)
        if component is None:
            if not allow_unknown_types:
                raise FactorError(
                    f"unknown component type {name!r}. Known types: "
                    f"{', '.join(sorted(_TYPES))}.\n"
                    f"If this school addresses something the others do not, register it "
                    f"with register_component() rather than working around it -- an "
                    f"unregistered type would be silently unsearchable."
                )
            parsed.append((name, value))
            continue

        component.validate(value)
        if component.repeatable is False and any(existing == name for existing, _ in parsed):
            raise FactorError(
                f"component {name!r} given more than once; it is not repeatable"
            )
        parsed.append((name, value))

    ordered = sorted(
        parsed,
        key=lambda pair: (_TYPES[pair[0]].order if pair[0] in _TYPES else 999, pair[0]),
    )

    # Sort the repeats of symmetric types so that argument order stops mattering.
    result: list[tuple[str, str]] = []
    index = 0
    while index < len(ordered):
        name = ordered[index][0]
        run_end = index
        while run_end < len(ordered) and ordered[run_end][0] == name:
            run_end += 1
        run = ordered[index:run_end]
        component = _TYPES.get(name)
        if component is not None and component.symmetric and len(run) > 1:
            run = sorted(run, key=lambda pair: pair[1])
        result.extend(run)
        index = run_end

    return Factor(tuple(result))


def describe(factor: Factor) -> str:
    """A plain-language rendering, for anything a person reads."""
    parts: list[str] = []
    if factor.has("transit"):
        parts.append(f"transiting {factor.get('transit')[0].replace('_', ' ')}")
    if factor.has("aspect"):
        aspect = factor.get("aspect")[0]
        subjects = [*factor.get("body"), *factor.get("angle")]
        natal = factor.get("natal")
        if parts and natal:
            parts.append(f"{aspect} natal {', '.join(n.replace('_', ' ') for n in natal)}")
        elif len(subjects) >= 2:
            parts = [f"{subjects[0].replace('_', ' ')} {aspect} {subjects[1].replace('_', ' ')}"]
        else:
            parts.append(aspect)
    else:
        parts.extend(value.replace("_", " ") for value in factor.get("body"))
        parts.extend(value.upper() for value in factor.get("angle"))
    if factor.has("sign"):
        parts.append(f"in {factor.get('sign')[0].title()}")
    if factor.has("house"):
        number, _, frame = factor.get("house")[0].partition("@")
        parts.append(f"in the {_ordinal(int(number))} house" + (f" ({frame})" if frame else ""))
    if factor.has("phase"):
        parts.append(f"[{factor.get('phase')[0].replace('_', ' ')}]")
    for extra in factor.get("condition"):
        parts.append(f"[{extra.replace('_', ' ')}]")
    return " ".join(parts) if parts else str(factor)


def _ordinal(number: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(number, f"{number}th")


def house_frame_for(system: HouseSystem, counted_from: str) -> str:
    """The frame label a house component should carry, given a pack's settings."""
    if system is HouseSystem.WHOLE_SIGN and counted_from == "sun":
        return "solar"
    if system is HouseSystem.WHOLE_SIGN:
        return "asc"
    return "natal"


FAMILIES: dict[str, str] = {
    "sign": "the twelve signs on their own",
    "house-natal": "the twelve houses in the natal (angular) frame",
    "house-solar": "the twelve houses in the solar frame, counted from the Sun sign",
    "body": "each body on its own",
    "angle": "the four angles on their own",
    "body-in-sign": "each body in each sign",
    "body-in-house-natal": "each body in each natal house",
    "body-in-house-solar": "each body in each solar house",
    "angle-in-sign": "each angle in each sign",
    "aspect-pairs": "each aspect between each pair of bodies",
}


def family(name: str, *, body_set: tuple[str, ...] = bodies.CLASSICAL_TEN,
           aspect_set: tuple[str, ...] = ("conjunction", "sextile", "square",
                                          "trine", "inconjunct", "opposition")) -> list[Factor]:
    """Enumerate a family of factors, for answering 'what have I not written yet'.

    Manual authoring needs a horizon. Without one it is impossible to tell
    whether a school has been half recorded or barely started.
    """
    if name == "sign":
        return [parse(f"sign:{sign}") for sign in SIGNS]
    if name == "house-natal":
        return [parse(f"house:{n}@natal") for n in range(1, 13)]
    if name == "house-solar":
        return [parse(f"house:{n}@solar") for n in range(1, 13)]
    if name == "body":
        return [parse(f"body:{body}") for body in body_set]
    if name == "angle":
        return [parse(f"angle:{angle}") for angle in ANGLES]
    if name == "body-in-sign":
        return [parse(f"body:{b} sign:{s}") for b in body_set for s in SIGNS]
    if name == "body-in-house-natal":
        return [parse(f"body:{b} house:{n}@natal") for b in body_set for n in range(1, 13)]
    if name == "body-in-house-solar":
        return [parse(f"body:{b} house:{n}@solar") for b in body_set for n in range(1, 13)]
    if name == "angle-in-sign":
        return [parse(f"angle:{a} sign:{s}") for a in ANGLES for s in SIGNS]
    if name == "aspect-pairs":
        out = []
        for index, first in enumerate(body_set):
            for second in body_set[index + 1:]:
                out.extend(
                    parse(f"body:{first} body:{second} aspect:{aspect}") for aspect in aspect_set
                )
        return out
    raise FactorError(f"unknown family {name!r}; known: {', '.join(sorted(FAMILIES))}")


FACTOR_HELP = """A factor key is one or more '<type>:<value>' components, space separated:

    sign:aries                                  a sign on its own
    body:venus sign:leo                         a body in a sign
    body:saturn house:11@natal                  a body in a natal house
    body:saturn house:11@solar                  a body in a solar house (counted from the Sun)
    angle:mc sign:libra                         an angle in a sign
    body:saturn body:venus aspect:square        an aspect between two bodies
    transit:saturn natal:sun aspect:conjunction a transit to a natal point

Component order does not matter; keys are canonicalised so the same
configuration always addresses the same entry."""
