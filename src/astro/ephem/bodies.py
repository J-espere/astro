"""The body registry: every point any school pack might ask for.

Deliberately wider than any single school uses. Which of these a reading
actually includes is a doctrine decision that lives in schools/*.yaml, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import swisseph as swe


class Kind(Enum):
    LUMINARY = "luminary"
    PLANET = "planet"
    ASTEROID = "asteroid"
    POINT = "point"          # computed, not a body: nodes, lots
    HYPOTHETICAL = "hypothetical"  # Uranian transneptunians
    ANGLE = "angle"          # ASC/MC etc., produced by houses.py


@dataclass(frozen=True, slots=True)
class Body:
    name: str
    swe_id: int
    kind: Kind
    glyph: str
    needs_asteroid_file: bool = False
    derived: bool = False    # not computed by swe.calc_ut directly


_REGISTRY: dict[str, Body] = {}


def _register(*bodies: Body) -> None:
    for body in bodies:
        _REGISTRY[body.name] = body


_register(
    Body("sun", swe.SUN, Kind.LUMINARY, "☉"),
    Body("moon", swe.MOON, Kind.LUMINARY, "☽"),
    Body("mercury", swe.MERCURY, Kind.PLANET, "☿"),
    Body("venus", swe.VENUS, Kind.PLANET, "♀"),
    Body("mars", swe.MARS, Kind.PLANET, "♂"),
    Body("jupiter", swe.JUPITER, Kind.PLANET, "♃"),
    Body("saturn", swe.SATURN, Kind.PLANET, "♄"),
    Body("uranus", swe.URANUS, Kind.PLANET, "♅"),
    Body("neptune", swe.NEPTUNE, Kind.PLANET, "♆"),
    Body("pluto", swe.PLUTO, Kind.PLANET, "♇"),
    # Nodes. Mean vs true is a doctrine choice; both are available.
    Body("true_node", swe.TRUE_NODE, Kind.POINT, "☊"),
    Body("mean_node", swe.MEAN_NODE, Kind.POINT, "☊"),
    Body("true_south_node", -1, Kind.POINT, "☋", derived=True),
    Body("mean_south_node", -1, Kind.POINT, "☋", derived=True),
    Body("mean_lilith", swe.MEAN_APOG, Kind.POINT, "⚸"),
    Body("osculating_lilith", swe.OSCU_APOG, Kind.POINT, "⚸"),
    Body("earth", swe.EARTH, Kind.PLANET, "⊕"),
    # Asteroids: these are the ones that need seas_18.se1 on disk.
    Body("chiron", swe.CHIRON, Kind.ASTEROID, "⚷", needs_asteroid_file=True),
    Body("pholus", swe.PHOLUS, Kind.ASTEROID, "⯛", needs_asteroid_file=True),
    Body("ceres", swe.CERES, Kind.ASTEROID, "⚳", needs_asteroid_file=True),
    Body("pallas", swe.PALLAS, Kind.ASTEROID, "⚴", needs_asteroid_file=True),
    Body("juno", swe.JUNO, Kind.ASTEROID, "⚵", needs_asteroid_file=True),
    Body("vesta", swe.VESTA, Kind.ASTEROID, "⚶", needs_asteroid_file=True),
    # Uranian / Hamburg School hypotheticals, required by schools/uranian.yaml.
    Body("cupido", swe.CUPIDO, Kind.HYPOTHETICAL, "Cu"),
    Body("hades", swe.HADES, Kind.HYPOTHETICAL, "Ha"),
    Body("zeus", swe.ZEUS, Kind.HYPOTHETICAL, "Ze"),
    Body("kronos", swe.KRONOS, Kind.HYPOTHETICAL, "Kr"),
    Body("apollon", swe.APOLLON, Kind.HYPOTHETICAL, "Ap"),
    Body("admetos", swe.ADMETOS, Kind.HYPOTHETICAL, "Ad"),
    Body("vulkanus", swe.VULKANUS, Kind.HYPOTHETICAL, "Vu"),
    Body("poseidon", swe.POSEIDON, Kind.HYPOTHETICAL, "Po"),
)

# The ten "planets" of contemporary practice, in the order the book lists them.
CLASSICAL_TEN = (
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
)

# The seven visible bodies, for schools/hellenistic.yaml.
VISIBLE_SEVEN = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn")

TRANSNEPTUNIAN = (
    "cupido", "hades", "zeus", "kronos", "apollon", "admetos", "vulkanus", "poseidon",
)


def get(name: str) -> Body:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown body {name!r}; known: {', '.join(sorted(_REGISTRY))}") from None


def names() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def opposite_of(name: str) -> str | None:
    """The body whose longitude is this one's plus 180 degrees, if any."""
    return {
        "true_node": "true_south_node",
        "mean_node": "mean_south_node",
        "true_south_node": "true_node",
        "mean_south_node": "mean_node",
    }.get(name)
