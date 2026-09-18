"""Fetch independent reference positions from JPL Horizons.

Every mainstream astrology program -- astro.com, astrologerapp, and most of the
rest -- runs the Swiss Ephemeris. Comparing against them therefore cannot tell
us whether the positions are right, only whether we are calling the same library
the same way. They would all agree, and the agreement would mean nothing.

JPL Horizons is a genuinely separate source: NASA's own DE441-based service, not
Astrodienst's code. This script pulls geocentric apparent ecliptic longitudes
from it and writes them to tests/golden/jpl/, so the cross-check is committed,
permanent, and runs offline afterwards.

    .venv/bin/python tests/fetch_jpl_reference.py

Requires network access to ssd.jpl.nasa.gov.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from astro import ephem  # noqa: E402
from conftest import REFERENCES  # noqa: E402

HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
OUTPUT = Path(__file__).parent / "golden" / "jpl"

# Horizons target ids. The planets are the 99-suffixed bodies, NOT the barycentres:
# for the inner planets the difference is nil, but for Jupiter and Saturn the
# barycentre sits noticeably off the planet.
TARGETS = {
    "sun": "10",
    "moon": "301",
    "mercury": "199",
    "venus": "299",
    "mars": "499",
    "jupiter": "599",
    "saturn": "699",
    "uranus": "799",
    "neptune": "899",
    "pluto": "999",
    "chiron": "2060;",   # the trailing semicolon selects the small-body record
}

ROW = re.compile(
    r"^\s*(\d{4}-\w{3}-\d{2}\s[\d:.]+)\s+([\d.]+)\s+(-?[\d.]+)\s*$", re.MULTILINE
)

# Julian day per requested epoch, within which a returned row is taken to be
# that epoch. Horizons prints to the millisecond, so this is generous.
EPOCH_MATCH_DAYS = 1e-5


def _row_julian_day(stamp: str) -> float:
    """Parse Horizons' '1998-Nov-18 21:11:00.010' back into a Julian day (UT)."""
    moment = dt.datetime.strptime(stamp.strip(), "%Y-%b-%d %H:%M:%S.%f").replace(
        tzinfo=dt.UTC
    )
    return ephem.julian_day(moment)


def fetch(target: str, julian_days: list[float]) -> dict[float, tuple[float, float]]:
    """Geocentric apparent ecliptic longitude and latitude, of date.

    QUANTITIES=31 is Horizons' observer ecliptic longitude/latitude, corrected
    for light-time, aberration, deflection, precession and nutation -- which is
    exactly what swisseph returns by default. Matching conventions is the whole
    game here: asking for J2000 coordinates instead would disagree by over a
    minute of arc and look like a bug in one of the two.
    """
    query = urllib.parse.urlencode(
        {
            "format": "text",
            "COMMAND": f"'{target}'",
            "OBJ_DATA": "NO",
            "MAKE_EPHEM": "YES",
            "EPHEM_TYPE": "OBSERVER",
            "CENTER": "'500@399'",        # geocentric
            "QUANTITIES": "'31'",
            "TLIST": "'" + " ".join(f"{jd:.9f}" for jd in julian_days) + "'",
            "TLIST_TYPE": "'JD'",
            "TIME_TYPE": "'UT'",
        }
    )
    with urllib.request.urlopen(f"{HORIZONS}?{query}", timeout=90) as response:
        body = response.read().decode()

    if "$$SOE" not in body:
        raise RuntimeError(f"Horizons returned no ephemeris for {target}:\n{body[:600]}")
    block = body.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    rows = ROW.findall(block)
    if len(rows) != len(julian_days):
        raise RuntimeError(
            f"{target}: asked for {len(julian_days)} epochs, parsed {len(rows)}"
        )

    # Horizons returns rows in CHRONOLOGICAL order, not in the order they were
    # requested. Zipping by position silently pairs each chart with another
    # chart's sky -- which looks like a catastrophic ephemeris failure and is
    # really a sorting bug. Match each row to its epoch by its own timestamp.
    matched: dict[float, tuple[float, float]] = {}
    for stamp, longitude, latitude in rows:
        returned = _row_julian_day(stamp)
        candidates = [jd for jd in julian_days if abs(jd - returned) < EPOCH_MATCH_DAYS]
        if len(candidates) != 1:
            raise RuntimeError(
                f"{target}: returned epoch {stamp} (jd {returned:.9f}) matched "
                f"{len(candidates)} requested epochs; expected exactly one"
            )
        matched[candidates[0]] = (float(longitude), float(latitude))

    if len(matched) != len(julian_days):
        raise RuntimeError(f"{target}: matched {len(matched)} of {len(julian_days)} epochs")
    return matched


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    julian_days = [reference.jd for reference in REFERENCES]
    collected: dict[str, dict[str, dict[str, float]]] = {
        reference.key: {} for reference in REFERENCES
    }

    for body, target in TARGETS.items():
        print(f"  {body:9s} ", end="", flush=True)
        rows = fetch(target, julian_days)
        for reference in REFERENCES:
            longitude, latitude = rows[reference.jd]
            collected[reference.key][body] = {
                "longitude": longitude,
                "latitude": latitude,
            }
        print("ok")
        time.sleep(1.0)  # Horizons asks for restraint; this is 11 requests total

    for reference in REFERENCES:
        path = OUTPUT / f"{reference.key}.json"
        path.write_text(
            json.dumps(
                {
                    "source": "JPL Horizons, geocentric apparent ecliptic of date (QUANTITIES=31)",
                    "julian_day_ut": round(reference.jd, 9),
                    "epoch_utc": ephem.from_julian_day(reference.jd).isoformat(),
                    "note": reference.note,
                    "bodies": collected[reference.key],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print(f"  wrote {path.relative_to(Path(__file__).parent.parent)}")


if __name__ == "__main__":
    main()
