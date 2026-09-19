"""Authoring commands: recording what a school says, and seeing where they differ.

These exist so a system can be entered by hand, a piece at a time, as you learn
it -- without a source text to ingest, and without any step that quietly turns
your typing into something that looks like a quotation.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

from ..corpus.store import DEFAULT_STORE, DelineationStore, Provenance, format_lookup
from ..doctrine.factors import FACTOR_HELP, FAMILIES, FactorError, describe, family, parse

TEMPLATE = """
# Delineation for: {described}
#   factor: {factor}
#   school: {school}
#
# Write what this configuration means under this school. Lines starting with '#'
# are ignored. Save an empty file to abort.
"""


def _resolve_text(args: argparse.Namespace, described: str, factor: str) -> str | None:
    """Text from --text, from stdin, or from $EDITOR -- in that order."""
    if args.text:
        return args.text
    if not sys.stdin.isatty():
        piped = sys.stdin.read()
        return piped if piped.strip() else None

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    header = TEMPLATE.format(described=described, factor=factor, school=args.school)
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as handle:
        handle.write(header)
        path = handle.name
    subprocess.run([editor, path], check=False)
    with open(path) as handle:
        body = "".join(line for line in handle if not line.startswith("#"))
    os.unlink(path)
    return body if body.strip() else None


def define(args: argparse.Namespace) -> int:
    try:
        factor = parse(args.factor, allow_unknown_types=args.allow_unknown_types)
    except FactorError as exc:
        print(f"{exc}\n\n{FACTOR_HELP}", file=sys.stderr)
        return 2

    described = describe(factor)
    text = _resolve_text(args, described, str(factor))
    if text is None:
        print("no text given; nothing stored.", file=sys.stderr)
        return 1

    provenance = Provenance(args.provenance)
    if provenance is Provenance.SOURCE_TEXT and not args.source:
        print(
            "provenance 'source_text' claims these are the source's own words, so it "
            "requires --source naming the text and location (e.g. 'Under A Libra God, "
            "ch. 15'). Use 'transcribed' for a reading you typed out of another program.",
            file=sys.stderr,
        )
        return 2

    with DelineationStore(args.store) as store:
        entry = store.add(
            args.school, factor, text,
            provenance=provenance, source_detail=args.source,
            confidence=args.confidence,
        )
        existing = store.lookup(factor, generalise=False)

    print(f"stored #{entry.id}: {described}")
    print(f"  {entry.attribution()}")
    others = {name: rows for name, rows in existing.items() if name != args.school}
    if others:
        print(f"\nnote: {len(others)} other school(s) already answer this factor: "
              f"{', '.join(sorted(others))}.")
        print(f"      compare them with:  astro lookup '{factor}'")
    return 0


def lookup(args: argparse.Namespace) -> int:
    try:
        factor = parse(args.factor, allow_unknown_types=True)
    except FactorError as exc:
        print(f"{exc}\n\n{FACTOR_HELP}", file=sys.stderr)
        return 2

    with DelineationStore(args.store) as store:
        results = store.lookup(
            factor, school=args.school,
            include_superseded=args.include_superseded,
            generalise=not args.exact,
        )
    print(format_lookup(factor, results))
    if args.school:
        print(f"\nnote: narrowed to school '{args.school}'. Other schools may also answer "
              f"this factor; run without --school to see them.")
    return 0


def revise(args: argparse.Namespace) -> int:
    with DelineationStore(args.store) as store:
        try:
            previous = store.get(args.entry_id)
        except KeyError as exc:
            print(exc, file=sys.stderr)
            return 1

        text = _resolve_text(args, describe(previous.parsed), previous.factor)
        if text is None:
            print("no text given; nothing changed.", file=sys.stderr)
            return 1

        updated = store.revise(
            args.entry_id, text,
            confidence=args.confidence if args.confidence is not None else previous.confidence,
        )

    print(f"revised #{previous.id} -> #{updated.id}")
    print(f"  the previous text is kept as history: astro history '{updated.factor}'")
    return 0


def history(args: argparse.Namespace) -> int:
    with DelineationStore(args.store) as store:
        entries = store.history(args.factor, school=args.school)
    if not entries:
        print("no entries recorded for that factor.")
        return 0
    for entry in entries:
        marker = " " if entry.active else "×"
        print(f"{marker} #{entry.id:<5d} {entry.attribution()}")
        for line in entry.text.splitlines():
            print(f"      {line}")
        if entry.superseded_by:
            print(f"      superseded by #{entry.superseded_by}")
        print()
    return 0


def search(args: argparse.Namespace) -> int:
    with DelineationStore(args.store) as store:
        for entry in store.search(args.query, limit=args.limit):
            print(f"#{entry.id:<5d} {describe(entry.parsed)}")
            print(f"      {entry.text[:160]}{'...' if len(entry.text) > 160 else ''}")
            print(f"      {entry.attribution()}\n")
    return 0


def schools(args: argparse.Namespace) -> int:
    with DelineationStore(args.store) as store:
        rows = store.schools()
    if not rows:
        print("no delineations recorded yet.")
        return 0
    print(f"{'school':24s} {'entries':>8s}")
    for name, count in rows:
        print(f"{name:24s} {count:8d}")
    return 0


def todo(args: argparse.Namespace) -> int:
    """What a school has not been given a delineation for yet."""
    if args.family not in FAMILIES:
        print(f"unknown family {args.family!r}. Known families:", file=sys.stderr)
        for name, description in FAMILIES.items():
            print(f"  {name:22s} {description}", file=sys.stderr)
        return 2

    factors = [str(f) for f in family(args.family)]
    with DelineationStore(args.store) as store:
        coverage = store.coverage(args.school, factors)

    done = [key for key, have in coverage if have]
    missing = [key for key, have in coverage if not have]
    print(f"{args.school} / {args.family}: {len(done)} of {len(coverage)} recorded")
    if missing and not args.done:
        print()
        for key in missing[: args.limit]:
            print(f"  {describe(parse(key, allow_unknown_types=True)):52s}  {key}")
        if len(missing) > args.limit:
            print(f"  ... and {len(missing) - args.limit} more")
    if args.done:
        print()
        for key in done[: args.limit]:
            print(f"  {describe(parse(key, allow_unknown_types=True)):52s}  {key}")
    return 0


def add_parsers(sub: argparse._SubParsersAction) -> None:
    def with_store(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--store", default=str(DEFAULT_STORE),
                            help=f"delineation database (default: {DEFAULT_STORE})")
        return parser

    define_parser = with_store(sub.add_parser(
        "define", help="record what a factor means under a school"))
    define_parser.add_argument("factor", help="e.g. 'body:saturn house:11@natal'")
    define_parser.add_argument("--school", required=True, help="e.g. cosmodynamics")
    define_parser.add_argument("--text", help="the delineation; omit to use $EDITOR or stdin")
    define_parser.add_argument(
        "--provenance", default="transcribed",
        choices=[p.value for p in Provenance],
        help="where this came from (default: transcribed). 'source_text' asserts these are "
             "the source's own words and requires --source.",
    )
    define_parser.add_argument("--source", default="",
                               help="the text and location, or the program and date")
    define_parser.add_argument("--confidence", type=int, default=3,
                               help="1-5, how settled you consider this (default: 3)")
    define_parser.add_argument("--allow-unknown-types", action="store_true",
                               help="permit a component type this codebase does not know")
    define_parser.set_defaults(func=define)

    lookup_parser = with_store(sub.add_parser(
        "lookup", help="show every school's delineation for a factor"))
    lookup_parser.add_argument("factor")
    lookup_parser.add_argument("--school", help="narrow to one school (shows a note when used)")
    lookup_parser.add_argument("--exact", action="store_true",
                               help="do not fall back to more general factors")
    lookup_parser.add_argument("--include-superseded", action="store_true")
    lookup_parser.set_defaults(func=lookup)

    revise_parser = with_store(sub.add_parser(
        "revise", help="replace an entry's text, keeping the original as history"))
    revise_parser.add_argument("entry_id", type=int)
    revise_parser.add_argument("--text")
    revise_parser.add_argument("--confidence", type=int)
    revise_parser.set_defaults(func=revise)

    history_parser = with_store(sub.add_parser(
        "history", help="every version ever recorded for a factor"))
    history_parser.add_argument("factor")
    history_parser.add_argument("--school")
    history_parser.set_defaults(func=history)

    search_parser = with_store(sub.add_parser("search", help="full-text search delineations"))
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.set_defaults(func=search)

    schools_parser = with_store(sub.add_parser("schools", help="schools present, with counts"))
    schools_parser.set_defaults(func=schools)

    todo_parser = with_store(sub.add_parser(
        "todo", help="which factors of a family a school has no delineation for"))
    todo_parser.add_argument("school")
    todo_parser.add_argument("family", nargs="?", default="sign",
                             help=f"one of: {', '.join(FAMILIES)}")
    todo_parser.add_argument("--done", action="store_true", help="list what IS recorded instead")
    todo_parser.add_argument("--limit", type=int, default=40)
    todo_parser.set_defaults(func=todo)
