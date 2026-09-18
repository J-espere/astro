# Doctrine spec — *Under A Libra God* (Nathan Guy Hatch, 2025)

This is a **specification**, not a summary of the book. It records the technical decisions the
book's method commits to, so they can be encoded as a machine-readable school pack
(`schools/hatch.yaml`) and compared against other schools.

Citations are by chapter number. Paragraph indices refer to the extracted text
(`tools/ingest/` output), so every rule below can be traced to source passages.
The book's text is **not** redistributed with this software — it is ingested locally from the
reader's own copy.

---

## 1. Bodies and points

| Class | Members | Notes |
|---|---|---|
| Planets | Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto | Ch. 15. Pluto retained. "Planet" = wanderer, so luminaries included. |
| Angles | ASC, DSC, MC, IC | Ch. 15. Treated as chartable points that both *receive* and *define*. |
| Points | North Node, South Node | Ch. 24. SN should be **drawn**, not inferred — explicit UI requirement. |
| Asteroids | Chiron | Ch. 24. First-class, not optional. Watched as closely as Pluto. |
| Speculative | "Planet X" as true ruler of Virgo | Ch. 16. Flagged as the author's conjecture; not computable. Record as a doctrine note only. |

Rulerships are modern (Pluto→Scorpio, Uranus→Aquarius, Neptune→Pisces), with the author
declining the shared Venus rulership of Taurus and reserving Virgo for an undiscovered body
(Ch. 16). The school pack must therefore carry an explicit `rulerships` table rather than
inheriting a library default.

## 2. Zodiac, aspects, orbs

- **Tropical**, 12 × 30°, decans noted as a subdivision (Ch. 15).
- **Aspect set:** 0° conjunction, 30° semisextile, 60° sextile, 90° square, 120° trine,
  150° inconjunct, 180° opposition (Ch. 15).
  - No semisquare (45°), sesquiquadrate (135°), quintile, or other minor aspects.
  - **The 150° inconjunct is promoted, not demoted.** The book treats the mainstream
    deemphasis of it as an error, and assigns it a specific signature: *impulsivity and
    significant consequence*. Any school pack that inherits a generic "minor aspect, small
    orb, low weight" default will produce readings this book would call wrong.
  - The 30° semisextile is minor in force but **must always be surfaced**, because it marks
    the opening and closing of a cycle and carries the cycle's theme.
- **Cycle framing:** aspects are phases of one continuous conjunction-to-conjunction cycle,
  not isolated events. Sextile/trine results follow causally from what was begun at the
  conjunction; the opposition is the evaluation point; hard aspects are consequence and
  course-correction (Ch. 15). **The UI must therefore be able to show any aspect in its cycle
  context** — where in the current Saturn/Jupiter/etc. cycle this hit falls, and what the
  prior phases were.
- **Orbs: the book gives no numeric orbs.** It instead specifies an *asymmetric influence
  window* keyed to the transiting body (Ch. 15):

  | Body | Window shape |
  |---|---|
  | Mars | Onset well before exact; often **concludes before exact** |
  | Uranus | Onset early, persists through most of the passage |
  | Jupiter, Venus | Effect often **does not begin until after exact** |
  | Saturn, Neptune, Pluto | Active across the whole passage; peak near exact |
  | Mercury, Moon | Short, fleeting, low amplitude except at retrograde |

  This is the single most distinctive computable feature of the system, and mainstream
  software cannot express it: everyone else uses a symmetric orb. Implement as a per-body
  `(lead_deg, lag_deg, peak_offset, amplitude_curve)` profile. **Numeric values are
  unspecified by the book and are therefore the first thing the user tunes** — they are
  seeded from modern Western defaults and adjusted against the user's own logged events.

## 3. Houses — two frames, both required

The book uses **two distinct house frames** and moves between them without always flagging
which. Encoding only one will silently corrupt most transit readings.

1. **Natal (angular) houses.** Quadrant-based, derived from ASC/MC; the book explicitly notes
   quadrants are divided into three houses each and that house sizes distort with latitude
   (Ch. 15). Astro Dienst is the author's reference tool, so **Placidus** is the implied
   default. These govern *life path and fate*.
2. **"Zodiac houses."** Whole-sign houses counted **from the Sun sign**, not the Ascendant.
   The author (Sun in Libra) calls Scorpio "the second zodiac house," Capricorn "the fourth
   zodiac house," Cancer "the tenth," and so on (Ch. 17, 21, 23, 26). **Nearly all of the
   book's transit-through-house delineations in Chs. 17–28 are written in this frame.**

Doctrinal split (Ch. 15): **planets in signs → personality; planets in houses → life path.**
The angles describe the *journey*, not the temperament.

Angle meanings: MC = public/material destiny; ASC = the means of reaching it (the self);
IC = inner, spiritual, home; DSC = partnership and relationship to others (Ch. 15).
The bottom of the chart is explicitly the inner/spiritual pole, and Saturn crossing the
IC→DSC→MC half is read as a long material-success arc (Ch. 17).

## 4. Time-domain techniques the software must compute

| Technique | Source | Computation |
|---|---|---|
| Transits to natal planets, angles, nodes, Chiron | Ch. 15, 17–28 | Root-find exact hits; apply asymmetric window |
| Transits through houses (both frames) | Ch. 17–28 | Ingress into natal house cusps **and** into sign-as-house-from-Sun |
| Saturn return + the full 30-year cycle | Ch. 17 | Conjunction ~29.5y; **opposition at ~15/45/75**; squares at ~7/22/37…; the book ties the 45 and 60 marks to documented aging inflections |
| Saturn over the angles | Ch. 17 | Distinct from other transits; multi-year arc, treated as the spine of the life story |
| Nodal cycle | Ch. 24 | ~18.6y; nodal return and half-return phases; node ingress by house |
| Chiron transits | Ch. 24 | Both directions: Chiron→natal, and transits→natal Chiron. Natal Chiron retrograde is read as a health-challenge signature |
| Retrograde stations **and shadow periods** | Ch. 15, 19 | Pre-shadow (station-retrograde degree first crossed) → station → post-shadow exit. The book locates resolution in the **post-shadow**, so the shadow must be a first-class interval, not a footnote |
| Venus 8-year pentagram cycle and the 243-year super-cycle | Ch. 19, 21 | Venus synodic return to same degree every 8y − 2.4d; long cycle not evenly divisible, so phase drift must be modelled |
| Jupiter–Saturn ~20-year conjunction cycle | Ch. 21 | Mundane; tied by the author to economic cycles |
| Outer-planet mundane cycles (Barbault) | Ch. 21 | Saturn–Neptune, Saturn–Pluto, Uranus–Pluto etc., with the aspects *to* the conjunction read as modifiers |
| Precession / astrological Ages | Ch. 21 | ~25,772y; Age of Aquarius treated as underway |
| Moon transits | Ch. 14, 15 | Fast, 1–2 day; explicitly nominated as the **empirically testable** class |
| Synastry / relationship timing | Ch. 19 | Cross-aspects between two natals; transiting Venus–Mars conjunction flagged as a meeting trigger |
| Rectification | Ch. 15 | Reverse-engineer ASC/MC from dated life events; Moon/Sun/Mars hits are the recommended levers |

## 5. Interpretive stance (constrains the output layer)

These are not flavour notes; they change what the software is allowed to say.

- **Transits accumulate.** A transit is not a window that closes — its experience is added to
  the "suitcase" and persists (Ch. 16). So a reading should show a **cumulative life record**,
  not just "what's active now."
- **Describes, does not determine.** The book insists astrology describes a life path rather
  than dictating it, and is hostile to advice-giving that implies fate can be steered
  (Ch. 15). Output should be descriptive and phase-aware, and should avoid prescriptive
  "you should" framing.
- **Aspects are morally impartial.** Benefic aspects assist harmful projects as readily as
  good ones (Ch. 15). No "lucky day" framing.
- **Sun → Moon emphasis shifts with age.** Sun-sign expression is loudest in youth; the Moon
  sign is the "true sign" of lived inner experience in maturity (Ch. 15). Implementable as an
  age-weighted emphasis parameter.
- **Minimum viable personality = Sun + Moon + Ascendant**, and the book attacks studies that
  test Sun sign alone (Ch. 14). Readings should refuse to deliver a Sun-sign-only portrait.
- **Inventory therapy is a prerequisite, not an add-on** (Ch. 15). The book's central warning
  is that astrology without self-inventory feeds control and coping mechanisms — fear,
  self-pity, anxiety about the future. This is the strongest argument in the book for building
  a **journal/inventory feature into the core of the product** rather than an interpretation
  vending machine.
- **Sign-cusp cases must be handled explicitly** (Ch. 14) — no silent rounding.

## 6. Where the book is a spec and where it is a claim

Keep these separate in the data model, because the user is comparing schools and will want to
know which parts are load-bearing.

- **Computable spec:** bodies, aspect set, both house frames, asymmetric windows, cycle
  phases, shadow periods, the listed cycles.
- **Delineation content:** the per-sign / per-house / per-transit passages in Chs. 16–28.
  Retrieved and cited; never paraphrased into fabricated prose.
- **Author's claims and conjectures:** Planet X as Virgo's ruler; the Nobel-laureate
  sign-distribution argument (Ch. 14); specific historical correlations; past-life framing of
  the nodes. Tag these `claim` so they can be surfaced as "the book asserts…" and excluded
  from generated readings if the user wants.
