# Build plan — a personal astrology engine that grows with you

**Goal.** Software that computes charts from the Swiss Ephemeris, interprets them through
*Under A Libra God*'s method, lets you compare that method against other schools, and
accumulates your own takes until the readings are yours rather than the book's.

**Shape of the answer.** Three things have to be separated that most astrology software
fuses together:

1. **Calculation** — where the bodies are. Objective, testable, school-independent.
2. **Doctrine** — which bodies, which aspects, which orbs, which houses, what counts as
   significant. *Data, not code.* This is what a "school" is.
3. **Interpretation** — what a configuration means. Retrieved from a corpus with citations,
   then progressively overridden by you.

Fuse them and you get a black box you can't argue with. Separate them and you get a system
where "I think inconjuncts hit harder than the book says" is a one-line change with a
recorded history.

---

## 1. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  ui/         chart wheel · timeline scrubber · reading · journal │
├──────────────────────────────────────────────────────────────────┤
│  reading/    assembles cited readings; ranks what matters today  │
├──────────────────────────────────────────────────────────────────┤
│  overlay/    YOUR takes, notes, edits, event log  ← the "growth" │
│  corpus/     book passages, tagged + indexed, cited by id        │
├──────────────────────────────────────────────────────────────────┤
│  doctrine/   school packs (hatch.yaml, modern.yaml, …) as DATA   │
├──────────────────────────────────────────────────────────────────┤
│  ephem/      pyswisseph: positions, houses, stations, events     │
└──────────────────────────────────────────────────────────────────┘
```

### `ephem/` — the calculation core
Thin, deterministic, heavily tested wrapper over `pyswisseph` (verified available, 2.10.3.2).
Responsibilities:
- Positions, speeds, declinations for all bodies at any instant; house cusps in **any**
  system (Placidus, whole-sign, equal, Koch, Campanus) — not just the one school you use,
  because you're comparing schools.
- **Event search**, not just snapshots. Root-find over time for: exact aspect perfection,
  sign/house ingress, stations, shadow-period boundaries, returns (solar, lunar, Saturn,
  nodal), lunations, eclipses. This is what makes a timeline possible rather than a
  day-by-day recompute.
- No interpretation, no doctrine, no opinions. It answers "where" and "when," never "what
  it means."

**Acceptance test:** positions and cusps match astro.com to <1 arcsecond for a set of fixed
reference charts, including high-latitude and cusp cases. Lock these in as golden files on
day one — every later refactor checks against them.

### `doctrine/` — schools as swappable data
`schools/hatch.yaml` is drafted in this repo already. A school pack declares bodies, aspect
set and weights, the asymmetric influence windows, house frames, rulerships, emphasis rules,
cycle definitions, and output stance. The engine reads it; nothing is hardcoded.

This is the single most important design decision in the plan, and it falls straight out of
what you said you're doing: **comparing schools**. Once doctrine is data, "what does this
transit look like under Hatch vs. under traditional Hellenistic rules?" is a dropdown, and
later a side-by-side diff view. Packs now drafted in `schools/`: `hatch`, `modern-western` (the untuned control),
`hellenistic` (sect, whole-sign-from-ASC, moiety orbs, time lords, no outers), `uranian`
(midpoints, hard aspects only, 90° dial), and `cosmodynamics` (stub — blocked on source
text). `yours` forks from `hatch` and diverges as you train it. See
[`docs/schools.md`](schools.md) for what each contributes and the three structural axes they
disagree on.

### `corpus/` — the book, as a retrievable index
Ingest pipeline: EPUB → clean text → stable paragraph IDs → **factor tags** (which planet /
sign / house / aspect / angle / technique / life-domain each passage speaks to) → SQLite with
FTS5 + vector embeddings.

Tagging is LLM-assisted with human review — the book is continuous prose, not a lookup table,
so a pure regex pass will miss most of it. Every tag keeps its paragraph ID, so a reading can
always show you *exactly* which passage produced a line, and you can challenge it.

Three passage classes, tagged separately (see doctrine §6): **spec**, **delineation**,
**claim**. You can exclude `claim` passages from readings without losing them.

The book's text stays local. Ingested from your own copy, never redistributed.

### `overlay/` — the part that grows
Three mechanisms, all versioned in git as plain JSON so nothing is ever silently lost:

1. **Annotations.** Attach your take to any passage, rule, or factor. `"Inconjuncts: the
   book's impulsivity read matches my experience, but it shows up as *other people's*
   impulsivity landing on me."` Annotations outrank book passages for the same factor at
   render time, and the reading shows both.
2. **Event log.** Date-stamped life events with tags (move, illness, relationship start,
   money, work, conflict). The engine back-computes what was active on those dates and builds
   a **personal correlation table**: *"Uranus→natal Moon: 4 logged events, 3 involved
   domicile change."*
3. **Reading feedback.** Every generated reading is rate-able and editable. An edit becomes a
   new overlay passage for that factor. Over a year of use, your overlay outweighs the book —
   which is the stated goal.

**Honesty constraint, and I'd hold the line on this one:** the correlation engine reports
**counts and dates, never p-values**. With n=4 you will find "significance" in noise, and the
book itself warns that astrology without self-inventory becomes a control mechanism. The
feature should show you your own record and let you judge it, not hand you fake statistics.
The one place you get real sample size is **Moon transits** — ~13 lunar returns a year, and
the book explicitly nominates them as the empirically testable class. That earns a dedicated
"Moon lab" view where a personal pattern can actually accumulate evidence.

### `reading/` — assembly and ranking
Given a chart + date + school, produce an ordered list of what matters, each item carrying:
factor → active window (with the asymmetric curve) → cycle phase → retrieved passages
(book + your overlay, clearly distinguished) → your past logged events on the same factor.

Ranking weight = aspect weight × body weight × window amplitude at this moment × natal
significance (does it touch an angle, a luminary, a chart ruler, the nodes?) × recency of
your own engagement. All coefficients live in the school pack, so ranking is tunable too.

**On LLM-written prose:** optional, off by default, and *strictly* grounded — it may only
paraphrase and connect retrieved passages, and every sentence carries its citation. An
ungrounded model writing astrology text produces fluent generic mush that will quietly
destroy the value of everything else here. The default output is retrieved passages, well
laid out.

---

## 2. What to take from the two reference apps

I couldn't load astrologerapp.org from this sandbox — its domain is blocked by the network
egress proxy here — so I'm going off the URL structure you sent (`tlDate`, `tlTime`,
`tlInterval=day`) and what that implies. Correct me where I've got it wrong.

**From astrologerapp.org — the time model.** State lives in the URL: a date, a time, and an
interval granularity. That's the right core interaction and it should be the spine of the UI:

- A **scrubber** that moves the whole application through time, with `day / week / month /
  year` granularity, arrow-key steppable, and the wheel + every panel reacting live.
- **Shareable, bookmarkable state.** Any moment in your life is a URL you can return to.
- Deep-linking a date is also what makes the journal work: log an event, click the date, see
  the sky.

**From astro.com — the depth and the discipline.**
- Multiple house systems and body sets exposed as real settings, not buried.
- Precise aspect tables with exact orb, applying/separating, and exact-hit datetimes.
- The **transit calendar / time-band view**: transits as horizontal bars over a date axis, so
  you see overlap and density rather than a list of today's hits. This is the view that makes
  the book's "transits accumulate" doctrine visible.
- Chart data taken seriously: named/saved charts, atlas-grade location + timezone resolution
  (historical DST is a real correctness issue), rectification support.
- Its weakness to avoid: interpretation as anonymous prewritten blocks with no provenance.
  Ours cites everything.

**What neither does, and is your actual differentiator:** doctrine as a swappable pack, a
side-by-side school comparison, and an interpretation layer that accumulates your own takes.

### UI surface
- **Natal** — wheel, positions table, aspect grid, angle/house readout in both frames.
- **Now / Timeline** — bi-wheel (natal + transit) with the scrubber; time-band view below;
  ranked event list beside it.
- **Reading** — the ranked items with cited passages, book vs. your overlay side by side.
- **Journal / Inventory** — event log, prompts drawn from the active transit, past readings.
- **Compare** — same chart, two schools, differences highlighted.
- **Cycles** — Saturn life-arc, nodal cycle, Venus pentagram, mundane Jupiter–Saturn/Barbault.
- **Dial** — 90° dial with midpoint trees, required by the `uranian` pack.
- **Map** — astrocartography lines and relocated angles (Phase 9).

---

## 3. Stack

| Layer | Choice | Why |
|---|---|---|
| Ephemeris | `pyswisseph` 2.10.3.2 | The mature binding; confirmed installable here |
| Backend | Python 3.11 + FastAPI | Same language as the ephemeris; good for the event-search math |
| Storage | SQLite (+FTS5) + git-tracked JSON for overlays | Local-first; overlay history is a real git log you can diff |
| Frontend | SvelteKit + hand-rolled SVG wheel | URL-as-state fits SvelteKit routing; a chart wheel is bespoke SVG in any framework |
| Packaging | Runs locally (`localhost`), single user | Birth data never leaves your machine; also resolves the licence question below |

**Swiss Ephemeris licensing — decide this before you host anything.** Swiss Ephemeris is
dual-licensed: AGPL-3.0, or a paid commercial licence (professional edition ~CHF 750 — confirm current terms with Astrodienst before relying on it).
AGPL's network clause means that if you ever put this on the public internet for others to
use, you must release the whole source under AGPL. Running it locally for yourself, or
open-sourcing it, is entirely fine. My recommendation: **build local-first and open-source
it.** You keep every option, your birth data stays put, and the licence question disappears.

**Copyright on the book.** Ingesting your own copy for your own reading tool is fine.
Shipping the corpus to others is not. The architecture keeps the book out of the repo: you
point the ingester at your EPUB, it builds a local index.

---

## 4. Roadmap

Each phase is independently useful — you can stop at any point and still have a working tool.

| Phase | Deliverable | Done when |
|---|---|---|
| **0. Foundation** | Repo scaffold, `ephem` core, golden-file tests | Positions + cusps match astro.com to <1″ on the reference set, incl. high latitude |
| **1. Natal** | Chart model, SVG wheel, positions/aspects tables, both house frames | Your chart renders correctly and the "zodiac houses" frame agrees with the book's own examples |
| **2. Doctrine** | School-pack loader, aspect engine, asymmetric windows, ranking | Swapping `hatch` ↔ `modern-western` visibly changes the aspect list and ordering |
| **3. Corpus** | EPUB ingest, factor tagging, review pass, FTS + embeddings | A factor query returns the right passages with IDs; spot-check accuracy on 50 sampled passages |
| **4. Time** | Event search, timeline scrubber + URL state, time-band view, transit calendar | Scrub a year of your life and see correct exact-hit dates, stations, shadows, ingresses |
| **5. Reading** | Assembled cited readings, ranked daily view | A day's reading is traceable line-by-line to passages |
| **6. Growth** | Annotations, event log, feedback loop, personal correlation table, Moon lab | Your overlay overrides the book for a factor and the change survives a restart and shows in git history |
| **7. Compare** | Second and third school packs, side-by-side diff view | Same transit read under three schools, differences highlighted |
| **8. Depth** | Returns, progressions, synastry, rectification assist, mundane/Barbault cycles | Each as an additive module; none required by the above |
| **9. Space & search** | Relocation, astrocartography (lines + parans + local space, map view), electional solver | Pick a place and see angles recomputed; find the next datetime meeting a constraint set |

Phases 0–2 are a couple of focused sessions. Phase 3 is the one with real grind in it — the
tagging review is where accuracy is won or lost, and it's worth doing slowly.

---

## 5. Risks worth naming up front

- **Tagging quality is the whole ballgame.** If the corpus index is sloppy, every reading is
  sloppy, and it'll be hard to tell whether a bad reading is bad doctrine or bad retrieval.
  Budget real review time in Phase 3 and keep a held-out sample to measure against.
- **Small-n pattern-matching.** Addressed above: counts and dates, no p-values, Moon lab for
  the one place sample size exists.
- **Birth-time accuracy.** The book is right that angles and houses are the first casualty of
  a wrong birth time. The UI should carry a birth-time confidence flag and visibly degrade
  angle-dependent output when it's low, rather than presenting it with false confidence.
- **Timezone and atlas correctness.** Historical DST and pre-standardization local time are a
  classic silent-wrong-answer source. Use a real timezone database from the start.
- **Scope.** Rectification and mundane forecasting are each their own project. They're in
  Phase 8 deliberately.

---

## 6. Decisions taken

- **Local-first, open source.** Runs on localhost for a single user. Birth data never leaves
  the machine, and the AGPL question resolves itself.
- **Retrieved passages, cited.** Default output is the source's own paragraphs plus your
  overlay, attributed and challengeable. No generated prose in v1.
- **Comparison packs:** `modern-western`, `hellenistic`, `uranian`, and `cosmodynamics`
  (Logan Cross / astrologerapp.org). All drafted except Cosmodynamics, which is blocked on
  its primary text — see [`docs/schools.md`](schools.md).

## 7. Still open

1. **Can you get the Cosmodynamics treatise as an ebook?** Two volumes, ~1,000+ pages. The
   ingest pipeline is designed for exactly this; without the text the pack stays a stub.
2. **Is my read of astrologerapp.org's time model right?** I'm working from the URL structure
   alone — the domain is blocked from this sandbox. A few screenshots would settle it.
3. **Other texts to ingest?** The corpus layer isn't book-specific, and a third and fourth
   source is where school comparison stops being structural and starts being substantive.
