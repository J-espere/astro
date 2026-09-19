"""Command line entry point.

    python -m astro <command>
"""

from __future__ import annotations

import argparse

from . import _chart, _doctrine, _verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="astro",
        description="A personal astrology engine: Swiss Ephemeris calculation, "
                    "doctrine as data, interpretation that grows.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _chart.add_parser(sub)
    _doctrine.add_parsers(sub)
    _verify.add_parser(sub)
    args = parser.parse_args(argv)
    return args.func(args)
