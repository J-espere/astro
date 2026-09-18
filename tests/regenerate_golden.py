"""Rewrite the golden snapshots. Run deliberately; read the diff before committing.

    .venv/bin/python tests/regenerate_golden.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from astro import ephem  # noqa: E402
from conftest import REFERENCES  # noqa: E402
from test_positions import GOLDEN_DIR, snapshot  # noqa: E402


def main() -> None:
    ephem.init()
    GOLDEN_DIR.mkdir(exist_ok=True)
    for reference in REFERENCES:
        path = GOLDEN_DIR / f"{reference.key}.json"
        path.write_text(json.dumps(snapshot(reference), indent=2, sort_keys=True) + "\n")
        print(f"  wrote {path.relative_to(Path.cwd())}  ({reference.note})")


if __name__ == "__main__":
    main()
