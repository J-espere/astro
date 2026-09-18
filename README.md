# astro

A personal astrology engine: Swiss Ephemeris calculation, doctrine as swappable data, and an
interpretation layer that accumulates your own takes over time.

**Status:** Phase 0 complete — the calculation core and its test suite. No doctrine, no
interpretation, no UI yet.

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
./scripts/fetch_ephemeris.sh          # Swiss Ephemeris data files, not committed
.venv/bin/python -m pytest            # 347 passing
.venv/bin/python -m astro.cli chart "1985-07-13 10:30" \
    --tz America/New_York --lat 40.7128 --lon -74.0060
```

- [`docs/PLAN.md`](docs/PLAN.md) — architecture, stack, UI, phased roadmap, open questions.
- [`docs/ui-reference.md`](docs/ui-reference.md) — what astrologerapp.org's interface does, and
  what it changed about the plan.
- [`docs/doctrine/under-a-libra-god.md`](docs/doctrine/under-a-libra-god.md) — the technical
  method extracted from the source text, as a specification.
- [`docs/schools.md`](docs/schools.md) — the comparison targets, what each contributes, and
  the three structural axes they disagree on.
- [`schools/`](schools/) — each method encoded as a machine-readable pack. Swapping the file
  swaps the astrological method: `hatch`, `modern-western`, `hellenistic`, `uranian`, and a
  blocked `cosmodynamics` stub.

## Design principle

Calculation, doctrine, and interpretation are three separate layers. Most astrology software
fuses them, which makes the output impossible to argue with. Keeping them apart means a
disagreement with the method is a data change with a recorded history, not a code rewrite.

## Layers built so far

`src/astro/ephem/` answers *where* and *when*, and nothing else:

| Module | Responsibility |
|---|---|
| `backend.py` | swisseph initialisation; refuses silent ephemeris substitution |
| `timeline.py` | civil time → Julian day, via IANA zones; refuses impossible local times |
| `bodies.py` | the body registry, wider than any one school uses |
| `positions.py` | placements, signs, decans, retrograde state |
| `houses.py` | 13 house systems, angles, and the origin-agnostic whole-sign frame |
| `search.py` | root-finding over time: exact aspects, ingresses, stations, retrograde shadows, returns |

## How the numbers are verified

Comparing against other astrology software proves less than it looks: astro.com,
astrologerapp and most of the rest all run the Swiss Ephemeris, so they would agree with each
other whether or not any of them were right. Three checks that do carry weight:

| Check | What it can catch |
|---|---|
| **JPL Horizons fixtures** (`tests/golden/jpl/`) | Wrong positions. NASA's DE441 service is a separate source and separate code; worst disagreement across all reference charts is **0.25″**, the Moon. |
| **Swiss vs Moshier** | Wrong flags, time scale or units — two different theories inside swisseph, agreeing under an arcsecond. |
| **Known dates** | Systematic drift. The 2026 equinox and the 2020 great conjunction are astronomical facts, not library output. |

Refresh the JPL fixtures with `tests/fetch_jpl_reference.py` (needs `ssd.jpl.nasa.gov`).

## Source texts

Book corpora are ingested from your own copies into a local index and are not redistributed
with this repository.
