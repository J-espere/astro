# Comparison targets

The point of making doctrine into data is that these can be run against the same chart and
diffed. This file records what each pack is for and what state it's in.

| Pack | State | What it contributes to the comparison |
|---|---|---|
| `hatch` | **drafted** | The book's method. Asymmetric influence windows, promoted 150°, whole-sign-from-the-Sun house frame, cumulative transits. |
| `modern-western` | **drafted** | The control. Symmetric orbs by aspect, Placidus, full aspect set, modern rulers. Deliberately untuned — differences against this pack *are* the other schools' contributions. |
| `hellenistic` | **drafted** | Structural opposite of modern practice: seven visible planets, Ptolemaic aspects only, orbs by *body* (moiety), whole-sign from the *Ascendant*, sect, dignity, and time-lord techniques that decide which transits even count. |
| `uranian` | **drafted** | Meaning lives in **midpoints**, not signs or houses. Hard aspects only, ~1.5° orbs, 90° dial, solar arc ahead of transits. Needs a dial view in the UI. |
| `cosmodynamics` | **stub — blocked** | Logan Cross's method, as used by astrologerapp.org. See below. |
| `yours` | *later* | Forked from `hatch`, diverges as you train it. |

## Three structural axes the packs disagree on

Worth naming, because these are what the compare view should highlight — not individual
aspect readings, but the shape of the disagreement:

1. **What an orb attaches to.** The aspect (`modern-western`), the body symmetrically
   (`uranian`), the body *asymmetrically* (`hatch`), or the pair by moiety (`hellenistic`).
2. **What houses are counted from.** The Ascendant by quadrant (`modern-western`), the
   Ascendant by whole sign (`hellenistic`), the **Sun sign** by whole sign (`hatch`, for
   transit delineation), or barely at all (`uranian`).
3. **Whether the 150° is an aspect.** `hatch` promotes it to a major with a specific
   signature; `modern-western` treats it as a weak minor; `hellenistic` says it is *aversion*
   — a relationship of non-relation; `uranian` excludes it. Four schools, four incompatible
   answers to one angle. This alone justifies the compare view.

## Cosmodynamics — what's blocking it

I could not reach anything technical. `astrologerapp.org` and `mysticrebels.com` are both
blocked by this sandbox's network egress proxy, and every search result is promotional copy:
"mechanics-first," "removes mythology and symbolic projection," "verifiable," built on free
will and alignment, using natal + relocated + progressed + transits with astrocartography,
electional and synastry. That tells us the system's *posture* and its *chart types*. It tells
us nothing about its zodiac, bodies, aspect set, orb model, or house logic — the five things
a pack actually needs.

**I did not guess them.** A pack of plausible-looking invented values would generate readings
attributed to a method that never said them, which is worse than having no pack.

The path is the same one that worked for the book: get the primary text — *I Fixed Astrology:
A Treatise on Alchemystic Cosmodynamics*, Vols 1–2, ~1,000+ pages — ingest it locally, extract
the doctrine spec, fill the pack. If you can get the ebook editions, that pipeline is already
designed.

Two of its named techniques are real engine work regardless of whether the pack ever gets
filled, and they're now on the roadmap:

- **Astrocartography** — planetary lines over a world map (MC/IC/ASC/DSC lines, paran
  latitudes, local space). New geometry in `ephem/`, plus a map view.
- **Electional** — search *forward* for a datetime satisfying a constraint set. That's an
  inverse solver, not a chart renderer, and it's the most interesting piece of engineering in
  the whole project.
- **Relocation** — recompute angles and houses for a different place. Cheap once the core
  exists, and useful to every pack.
