# UI reference: astrologerapp.org

Read from a screenshot of `/chart?tlDate=2026-09-18&tlTime=12:00&tlInterval=day`, since the
domain is blocked from this sandbox. Observations, not documentation — correct anything wrong.

## What the screenshot shows

**A layer stack, not a bi-wheel.** The row under the toolbar reads `Sky · Sep 18, 2026, 19:1…`
followed by a removable chip for a saved chart (`● Joëlle ✕`), a `+`, and a clock icon. So the
sky at a chosen moment and any number of saved charts are *layers* composed onto one wheel,
each independently addable and removable.

**This is better than what I planned and I've changed the plan.** I had a fixed natal +
transit bi-wheel. A layer stack subsumes it and gets synastry, chart-to-chart comparison, and
multi-party work for free, with no separate view for each. The `tl` prefix on the URL
parameters ("timeline") and the clock icon confirm the time model I'd guessed at.

**Annotation on the wheel itself.** `Focus` sits top-left of the canvas, `Draw` top-right.
Drawing directly on the chart is a different kind of overlay from the annotations I planned —
mine attach to *factors*, these attach to *geometry*. Both are worth having; the second is
how you mark a pattern you don't yet have words for.

**Wheel construction.** Outer band of signs coloured by element; an inner rose band; degree
ticks; two concentric rings of glyphs; house numbers on the inner ring; angle labels AC, DC,
MC, IC; aspect lines drawn across the centre and coloured by aspect class, with dotted lines
for what look like minor aspects.

**Fixed stars are plotted.** A label reading `Alcy` (Alcyone) appears at ~29° Pisces on the
same ring as the bodies. Worth noting that `sefstars.txt` is already fetched by
`scripts/fetch_ephemeris.sh`, so this is available whenever a school pack asks for it.

**Chrome.** Back, a shared/people icon, a `Save <name>` dropdown, Search, Share, a broadcast
icon, and an account menu. A floating three-button toolbar sits at the bottom of the canvas.

## Changes to the plan

1. **Layers replace the bi-wheel.** `Now / Timeline` becomes a layer stack: one sky layer bound
   to the scrubber plus N chart layers, each toggleable. Synastry stops being a separate phase.
2. **Two kinds of annotation.** Factor-anchored (the overlay described in `PLAN.md` §1) and
   geometry-anchored (free drawing on the wheel). The second stores against chart coordinates
   so it survives a re-render at a different size.
3. **Fixed stars enter the body registry** as an optional class, off unless a pack enables them.

## Still unverified

Whether the scrubber is continuous or stepped; what the three bottom buttons do; whether
`tlInterval` changes the step size or the time-band zoom; how it renders more than two layers
without the aspect web becoming unreadable. Screenshots of the timeline in motion, or of the
settings panels, would settle these.
