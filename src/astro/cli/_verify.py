"""The `verify` command: report every discrepancy, including the ones that pass.

A check that prints "OK" tells you nothing about how much room was left. This
prints the actual arcsecond figures for every body against every reference,
so drift is visible while it is still small.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .. import ephem
from ..ephem.backend import Source

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "golden" / "jpl"
TOLERANCE = {"moon": 0.4}
DEFAULT_TOLERANCE = 0.2


def run(args: argparse.Namespace) -> int:
    ephem.init()
    fixtures = sorted(FIXTURES.glob("*.json"))
    if not fixtures:
        print(f"no JPL fixtures in {FIXTURES}; run tests/fetch_jpl_reference.py")
        return 1

    print("Swiss Ephemeris vs JPL Horizons (geocentric apparent ecliptic longitude, of date)")
    print("JPL is a separate source and separate code. Other astrology programs are not:")
    print("astro.com and astrologerapp both run the Swiss Ephemeris, so agreeing with them")
    print("shows only that it is being called the same way.\n")

    worst = (0.0, "")
    failures = 0
    bodies = ephem.CLASSICAL_TEN + ("chiron",)

    for path in fixtures:
        data = json.loads(path.read_text())
        jd = data["julian_day_ut"]
        print(f"{path.stem}   {data['epoch_utc']}   — {data.get('note', '')}")
        print(f"  {'body':10s} {'swisseph':>13s} {'JPL':>13s} {'Δ arcsec':>10s} "
              f"{'moshier Δ':>11s}")
        for body in bodies:
            expected = data["bodies"][body]["longitude"]
            computed = ephem.position(jd, body).longitude
            delta = abs(ephem.wrap180(computed - expected)) * 3600.0
            moshier = ephem.position(jd, body, source=Source.MOSHIER).longitude
            moshier_delta = abs(ephem.wrap180(moshier - expected)) * 3600.0

            limit = TOLERANCE.get(body, DEFAULT_TOLERANCE)
            flag = "" if delta < limit else f"   OVER {limit}″"
            if flag:
                failures += 1
            if delta > worst[0]:
                worst = (delta, f"{path.stem}/{body}")
            print(f"  {body:10s} {computed:13.7f} {expected:13.7f} {delta:10.4f} "
                  f"{moshier_delta:11.4f}{flag}")
        print()

    print(f"worst disagreement: {worst[0]:.4f}″  ({worst[1]})")
    print(f"tolerances: {DEFAULT_TOLERANCE}″, Moon {TOLERANCE['moon']}″")
    if failures:
        print(f"\n{failures} value(s) outside tolerance.")
        return 1
    print("all within tolerance — figures above are printed in full so that drift is")
    print("visible before it becomes a failure.")
    return 0


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "verify", help="report Swiss Ephemeris discrepancies against JPL Horizons"
    )
    parser.set_defaults(func=run)
