"""The `chart` command."""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from .. import ephem
from ..ephem.houses import HouseSystem, HouseSystemUndefined, house_of_whole_sign, houses

DISPLAY_BODIES = ephem.CLASSICAL_TEN + ("chiron", "true_node", "true_south_node")


def format_angle(longitude: float) -> str:
    degree = int(longitude % 30)
    minutes = int(round(((longitude % 30) - degree) * 60))
    if minutes == 60:
        degree, minutes = degree + 1, 0
    return f"{degree:2d}°{minutes:02d}' {ephem.SIGNS[int(longitude // 30) % 12].title()}"


def run(args: argparse.Namespace) -> int:
    try:
        local = dt.datetime.strptime(args.moment, "%Y-%m-%d %H:%M")
    except ValueError:
        print(f"could not parse {args.moment!r}; expected 'YYYY-MM-DD HH:MM'", file=sys.stderr)
        return 2

    try:
        utc, jd = ephem.chart_moment(local, args.tz)
    except ephem.timeline.TimeError as exc:
        print(f"time error: {exc}", file=sys.stderr)
        return 2

    ephem.init()
    if not ephem.data_files_present():
        print("Swiss Ephemeris data files missing; run scripts/fetch_ephemeris.sh", file=sys.stderr)
        return 1

    system = HouseSystem[args.houses.upper()]
    try:
        frame = houses(jd, args.lat, args.lon, system)
    except HouseSystemUndefined as exc:
        print(f"note: {exc}\nnote: falling back to Porphyry for this chart.\n", file=sys.stderr)
        frame = houses(jd, args.lat, args.lon, system, fallback=HouseSystem.PORPHYRY)

    sun = ephem.position(jd, "sun").longitude

    print(f"{local:%Y-%m-%d %H:%M} {args.tz}   =   {utc:%Y-%m-%d %H:%M} UTC   JD {jd:.6f}")
    substitution = (
        f" (SUBSTITUTED for {frame.requested_system.name.title()})" if frame.substituted else ""
    )
    print(f"{args.lat:+.4f}, {args.lon:+.4f}   "
          f"houses: {frame.system.name.title()}{substitution}\n")

    print(f"{'body':16s} {'position':>18s}  {'house':>5s}  {'solar':>5s}  {'speed':>9s}")
    print("-" * 62)
    for name in DISPLAY_BODIES:
        placement = ephem.position(jd, name)
        print(
            f"{name:16s} {placement.format():>18s}  "
            f"{frame.house_of(placement.longitude):5d}  "
            f"{house_of_whole_sign(placement.longitude, sun):5d}  "
            f"{placement.speed:+9.4f}"
        )

    print()
    for label, longitude in frame.angles.items():
        print(f"{label.upper():16s} {format_angle(longitude):>18s}")

    print("\ncusps")
    for index, cusp in enumerate(frame.cusps, start=1):
        print(f"  {index:2d}  {format_angle(cusp):>18s}   span {frame.span(index):6.2f}°")

    print("\n'house' is the natal frame; 'solar' is whole-sign counted from the Sun sign,")
    print("which is the frame Under A Libra God uses for most transit delineations.")
    return 0


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("chart", help="print a chart's positions, houses and angles")
    parser.add_argument("moment", help="local date and time, 'YYYY-MM-DD HH:MM'")
    parser.add_argument("--tz", required=True, help="IANA zone, e.g. America/New_York")
    parser.add_argument("--lat", type=float, required=True, help="degrees, north positive")
    parser.add_argument("--lon", type=float, required=True, help="degrees, east positive")
    parser.add_argument("--houses", default="placidus", help="house system (default: placidus)")
    parser.set_defaults(func=run)
