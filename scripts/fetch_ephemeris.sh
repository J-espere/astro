#!/usr/bin/env bash
# Fetch Swiss Ephemeris data files into data/ephe/.
#
# These are NOT committed: they are large, and they carry Astrodienst's dual
# AGPL/commercial licence. Each user fetches their own copy.
#
# Without them, swisseph SILENTLY falls back to the Moshier analytical theory --
# it does not error. Moshier is accurate to roughly an arcsecond for the planets
# over 1800-2100, but it cannot compute asteroids at all, so Chiron fails outright.
# astro.ephem.backend.positions() refuses that silent substitution by default.
set -euo pipefail

DEST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/data/ephe"
BASE="${SWE_EPHE_BASE:-https://raw.githubusercontent.com/aloistr/swisseph/master/ephe}"
mkdir -p "$DEST"

# _18 files cover 1800-2399 CE. Add _12 (1200-1799) or _24 (2400-2999) for wider ranges.
FILES=(
  sepl_18.se1    # planets
  semo_18.se1    # moon
  seas_18.se1    # main asteroids, including Chiron
  seasnam.txt    # asteroid name index
  sefstars.txt   # fixed stars
  seorbel.txt    # orbital elements for hypothetical bodies
)

for f in "${FILES[@]}"; do
  if [[ -s "$DEST/$f" ]]; then
    printf '  %-14s present\n' "$f"
    continue
  fi
  printf '  %-14s fetching... ' "$f"
  if curl -fsSL --retry 3 --max-time 120 -o "$DEST/$f.part" "$BASE/$f"; then
    mv "$DEST/$f.part" "$DEST/$f"
    printf 'ok (%s)\n' "$(du -h "$DEST/$f" | cut -f1)"
  else
    rm -f "$DEST/$f.part"
    printf 'FAILED\n'
    # seorbel/seasnam are optional; the binaries are not.
    case "$f" in sepl_*|semo_*|seas_*) exit 1 ;; esac
  fi
done
echo "Ephemeris files in $DEST"
