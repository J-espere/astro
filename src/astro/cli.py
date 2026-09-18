"""A minimal chart printer, for checking this engine against other software.

Phase 0 has no interpretation and no doctrine -- this exists so the numbers can
be compared against astro.com or astrologerapp.org by eye, which is the only
external validation available until one of those is reachable.

    python -m astro.cli chart "1985-07-13 10:30" --tz America/New_York \
        --lat 40.7128 --lon -74.0060
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from astro import ephem
from astro.ephem.houses import HouseSystem, HouseSystemUndefined, house_of_whole_sign, houses

DISPLAY_BODIES = ephem.CLASSICAL_TEN + ("chiron", "true_node", "true_south_node")


def _format_angle(longitude: float) -> str:
    degree = int(longitude % 30)
    minutes = int(round(((longitude % 30) - degree) * 60))
    if minutes == 60:
        degree, minutes = degree + 1, 0
    return f"{degree:2d}°{minutes:02d}' {ephem.SIGNS[int(longitude // 30) % 12].title()}"


def chart(args: argparse.Namespace) -> int:
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
        print(f"{exc}\nfalling back to Porphyry for this chart.\n", file=sys.stderr)
        frame = houses(jd, args.lat, args.lon, system, fallback=HouseSystem.PORPHYRY)

    sun = ephem.position(jd, "sun").longitude

    print(f"{local:%Y-%m-%d %H:%M} {args.tz}   =   {utc:%Y-%m-%d %H:%M} UTC   JD {jd:.6f}")
    print(f"{args.lat:+.4f}, {args.lon:+.4f}   houses: {frame.system.name.title()}"
          f"{' (substituted)' if frame.substituted else ''}\n")

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
        print(f"{label.upper():16s} {_format_angle(longitude):>18s}")

    print("\ncusps")
    for index, cusp in enumerate(frame.cusps, start=1):
        print(f"  {index:2d}  {_format_angle(cusp):>18s}   span {frame.span(index):6.2f}°")

    print("\n'house' is the natal frame; 'solar' is whole-sign counted from the Sun sign,")
    print("which is the frame Under A Libra God uses for most transit delineations.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="astro", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    chart_parser = sub.add_parser("chart", help="print a chart's positions, houses and angles")
    chart_parser.add_argument("moment", help="local date and time, 'YYYY-MM-DD HH:MM'")
    chart_parser.add_argument("--tz", required=True, help="IANA zone, e.g. America/New_York")
    chart_parser.add_argument("--lat", type=float, required=True, help="degrees, north positive")
    chart_parser.add_argument("--lon", type=float, required=True, help="degrees, east positive")
    chart_parser.add_argument(
        "--houses", default="placidus", help="house system (default: placidus)"
    )
    chart_parser.set_defaults(func=chart)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
