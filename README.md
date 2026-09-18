# astro

A personal astrology engine: Swiss Ephemeris calculation, doctrine as swappable data, and an
interpretation layer that accumulates your own takes over time.

**Status:** planning. Nothing is built yet.

- [`docs/PLAN.md`](docs/PLAN.md) — architecture, stack, UI, phased roadmap, open questions.
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

## Source texts

Book corpora are ingested from your own copies into a local index and are not redistributed
with this repository.
