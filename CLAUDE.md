# Working agreement for this repository

## Never do anything silently

This is the project's first rule, and it applies to the software and to the assistant
equally. When two things disagree, the disagreement is the interesting part — it must be
recorded and surfaced, never averaged away, defaulted past, or quietly resolved.

**In the software:**

- `backend.calc()` raises `SourceSubstituted` rather than accept swisseph's silent fallback
  from the Swiss data files to the Moshier theory.
- `houses()` raises `HouseSystemUndefined` beyond the polar circle rather than substitute
  Porphyry, and records `requested_system` alongside `system` when a caller opts into a
  fallback.
- Ephemeris discrepancies against JPL Horizons are reported, never suppressed. `astro verify`
  prints the full per-body table with the actual arcsecond figures, including the ones that
  pass.
- Where school packs disagree, the reading shows every reading, attributed. No pack is
  treated as the default that others deviate from, and no disagreement is hidden behind a
  selected pack.
- Delineations carry provenance. A manually entered one says who entered it, when, and on
  what authority, and is never presented as if it came from a source text.

**In reporting to the user:**

- State discrepancies between systems explicitly, with figures, whenever they appear —
  including small ones, and including ones that fall inside tolerance.
- Never present a fallback, an assumption, or a substitution as a result. Name it.
- When a check could not be run, say so rather than reporting what the other checks showed
  as if it covered the same ground.

## Verification

Comparing against other astrology software proves little: astro.com, astrologerapp and most
of the rest all run the Swiss Ephemeris, so they agree with each other whether or not any of
them is right. The checks that carry weight are JPL Horizons (separate source, separate
code), Swiss vs Moshier (different theories inside swisseph), and known astronomical dates.

## Layer boundaries

`ephem/` answers where and when, and holds no doctrine. `doctrine/` is data. `corpus/` is
retrieved and cited, never invented. Keeping these apart is what lets a school be swapped
without touching a line of calculation.

## Personal and third-party content

The repository is public. Birth data lives in `data/charts/`, delineations in
`data/delineations/`, ingested books in `data/corpus/` — all gitignored. Interpretations
transcribed from someone else's system are for personal use and do not go in a public repo.

## Conventions

- `.venv/bin/python -m pytest` before every commit; `.venv/bin/ruff check src tests` clean.
- Golden fixtures are regenerated deliberately, never as a way to make a failing test pass.
- Commit messages say what changed and why, and name any trap found along the way.
