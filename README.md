# astro

A personal astrology engine: Swiss Ephemeris calculation, doctrine as swappable data, and an
interpretation layer that accumulates your own takes over time.

**Status:** planning. Nothing is built yet.

- [`docs/PLAN.md`](docs/PLAN.md) — architecture, stack, UI, phased roadmap, open questions.
- [`docs/doctrine/under-a-libra-god.md`](docs/doctrine/under-a-libra-god.md) — the technical
  method extracted from the source text, as a specification.
- [`schools/hatch.yaml`](schools/hatch.yaml) — that method encoded as a machine-readable
  school pack. Swapping this file swaps the astrological method.

## Design principle

Calculation, doctrine, and interpretation are three separate layers. Most astrology software
fuses them, which makes the output impossible to argue with. Keeping them apart means a
disagreement with the method is a data change with a recorded history, not a code rewrite.

## Source texts

Book corpora are ingested from your own copies into a local index and are not redistributed
with this repository.
