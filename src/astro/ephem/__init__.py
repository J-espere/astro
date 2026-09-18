"""Calculation layer: where the bodies are, and when they get there.

This layer holds no doctrine. It answers "where" and "when" and never "what it
means" -- that separation is what lets schools/*.yaml be swapped without
touching any of this.
"""

from . import timeline as timeline  # re-exported: cli catches timeline.TimeError
from .backend import (
    EphemerisError,
    Reading,
    Source,
    SourceSubstituted,
    data_files_present,
    init,
)
from .bodies import CLASSICAL_TEN, TRANSNEPTUNIAN, VISIBLE_SEVEN, Body, Kind
from .houses import (
    Houses,
    HouseSystem,
    HouseSystemUndefined,
    house_of_whole_sign,
    houses,
    whole_sign_from,
)
from .positions import SIGNS, Position, position, positions
from .search import (
    Hit,
    Ingress,
    Retrograde,
    Station,
    exact_aspects,
    ingresses,
    retrogrades,
    returns,
    separation,
    stations,
    wrap180,
)
from .timeline import chart_moment, from_julian_day, is_ambiguous, julian_day, to_utc

__all__ = [
    "CLASSICAL_TEN", "TRANSNEPTUNIAN", "VISIBLE_SEVEN", "SIGNS",
    "Body", "EphemerisError", "Hit", "HouseSystem", "HouseSystemUndefined", "Houses",
    "Ingress", "Kind", "Position", "Reading", "Retrograde", "Source",
    "SourceSubstituted", "Station",
    "chart_moment", "data_files_present", "exact_aspects", "from_julian_day",
    "house_of_whole_sign", "houses", "ingresses", "init", "is_ambiguous",
    "julian_day", "position", "positions", "retrogrades", "returns", "separation",
    "stations", "to_utc", "whole_sign_from", "wrap180",
]
