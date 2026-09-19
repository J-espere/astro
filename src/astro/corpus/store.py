"""The delineation store: what a configuration means, under which school, on whose word.

Three properties this has to have, all of them consequences of the project's
first rule:

  * **Nothing is overwritten.** Revising an entry supersedes it and keeps the
    old text. Your take on Saturn in the 11th in 2026 is data about you, and a
    system meant to grow with you cannot quietly discard the position you have
    grown out of.
  * **Nothing is anonymous.** Every entry records where it came from -- a book
    with a passage id, a reading transcribed out of another program, your own
    observation -- and that provenance travels with the text everywhere it is
    displayed. A line you typed from astrologerapp must never be able to pass
    itself off as a quotation from a source you own.
  * **Nothing is silently preferred.** Looking up a factor returns every
    school's answer, not the selected school's. Disagreement between schools is
    the thing being studied; hiding it behind a default would defeat the point.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..doctrine.factors import Factor, describe, parse

DEFAULT_STORE = Path(__file__).resolve().parents[3] / "data" / "delineations.db"


class Provenance(Enum):
    """How an entry came to be. Displayed with the text, always."""

    SOURCE_TEXT = "source_text"   # quoted from a book you hold, with a passage id
    TRANSCRIBED = "transcribed"   # typed from another program or reading
    OBSERVED = "observed"         # your own correlation, from your own logged events
    INFERRED = "inferred"         # derived from the school's stated rules
    PROVISIONAL = "provisional"   # a placeholder you intend to replace

    @property
    def label(self) -> str:
        return {
            Provenance.SOURCE_TEXT: "from source text",
            Provenance.TRANSCRIBED: "transcribed",
            Provenance.OBSERVED: "your observation",
            Provenance.INFERRED: "inferred from rules",
            Provenance.PROVISIONAL: "provisional",
        }[self]

    @property
    def quotable(self) -> bool:
        """Whether this may be presented as the school's own words."""
        return self is Provenance.SOURCE_TEXT


@dataclass(frozen=True, slots=True)
class Entry:
    """One delineation, as stored."""

    id: int
    school: str
    factor: str
    text: str
    provenance: Provenance
    source_detail: str
    confidence: int          # 1 low - 5 high; how settled you consider this
    created_at: str
    supersedes: int | None
    superseded_by: int | None

    @property
    def active(self) -> bool:
        return self.superseded_by is None

    @property
    def parsed(self) -> Factor:
        return parse(self.factor, allow_unknown_types=True)

    def attribution(self) -> str:
        parts = [f"{self.school}", self.provenance.label]
        if self.source_detail:
            parts.append(self.source_detail)
        parts.append(f"confidence {self.confidence}/5")
        parts.append(self.created_at[:10])
        return " · ".join(parts)


SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    school        TEXT    NOT NULL,
    factor        TEXT    NOT NULL,
    text          TEXT    NOT NULL,
    provenance    TEXT    NOT NULL,
    source_detail TEXT    NOT NULL DEFAULT '',
    confidence    INTEGER NOT NULL DEFAULT 3,
    created_at    TEXT    NOT NULL,
    supersedes    INTEGER REFERENCES entries(id),
    superseded_by INTEGER REFERENCES entries(id)
);
CREATE INDEX IF NOT EXISTS entries_factor ON entries(factor);
CREATE INDEX IF NOT EXISTS entries_school ON entries(school);
CREATE INDEX IF NOT EXISTS entries_active ON entries(superseded_by);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
    USING fts5(text, factor, school, content='entries', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, text, factor, school)
        VALUES (new.id, new.text, new.factor, new.school);
END;
CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, text, factor, school)
        VALUES ('delete', old.id, old.text, old.factor, old.school);
END;
"""


class DelineationStore:
    """A local, append-only record of what each school says about each factor."""

    def __init__(self, path: Path | str = DEFAULT_STORE) -> None:
        self.path = Path(path)
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> DelineationStore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        with closing(self._connection.cursor()) as cursor:
            yield cursor
            self._connection.commit()

    def add(
        self,
        school: str,
        factor: str | Factor,
        text: str,
        *,
        provenance: Provenance = Provenance.TRANSCRIBED,
        source_detail: str = "",
        confidence: int = 3,
        supersedes: int | None = None,
    ) -> Entry:
        """Record a delineation. Canonicalises the factor so lookups find it."""
        if not text.strip():
            raise ValueError("refusing to store an empty delineation")
        if not 1 <= confidence <= 5:
            raise ValueError(f"confidence must be 1-5, got {confidence}")
        key = str(factor if isinstance(factor, Factor) else parse(factor, allow_unknown_types=True))

        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO entries (school, factor, text, provenance, source_detail,"
                " confidence, created_at, supersedes) VALUES (?,?,?,?,?,?,?,?)",
                (
                    school, key, text.strip(), provenance.value, source_detail,
                    confidence, dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                    supersedes,
                ),
            )
            new_id = cursor.lastrowid
            if supersedes is not None:
                cursor.execute(
                    "UPDATE entries SET superseded_by = ? WHERE id = ?", (new_id, supersedes)
                )
        return self.get(new_id)

    def revise(self, entry_id: int, text: str, **kwargs: object) -> Entry:
        """Replace an entry's text, keeping the original as history."""
        previous = self.get(entry_id)
        if previous.superseded_by is not None:
            raise ValueError(
                f"entry {entry_id} was already superseded by {previous.superseded_by}; "
                f"revise that one instead so the chain stays linear"
            )
        return self.add(
            previous.school,
            previous.factor,
            text,
            provenance=kwargs.get("provenance", previous.provenance),  # type: ignore[arg-type]
            source_detail=kwargs.get("source_detail", previous.source_detail),  # type: ignore[arg-type]
            confidence=kwargs.get("confidence", previous.confidence),  # type: ignore[arg-type]
            supersedes=entry_id,
        )

    def get(self, entry_id: int) -> Entry:
        with self._cursor() as cursor:
            row = cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            raise KeyError(f"no entry {entry_id}")
        return _to_entry(row)

    def lookup(
        self,
        factor: str | Factor,
        *,
        school: str | None = None,
        include_superseded: bool = False,
        generalise: bool = True,
    ) -> dict[str, list[tuple[Factor, Entry]]]:
        """Every school's answer for a factor, keyed by school.

        `school` narrows the result but never changes which schools are
        consulted -- the caller has to ask for narrowing explicitly, so the
        default can never quietly present one school's reading as the reading.

        With `generalise`, a factor with no exact entry falls back through
        progressively less specific keys, and the returned Factor says which
        rung answered, so a general note is never mistaken for a specific one.
        """
        parsed = factor if isinstance(factor, Factor) else parse(factor, allow_unknown_types=True)
        ladder = parsed.generalisations() if generalise else (parsed,)

        found: dict[str, list[tuple[Factor, Entry]]] = {}
        for rung in ladder:
            query = "SELECT * FROM entries WHERE factor = ?"
            params: list[object] = [str(rung)]
            if school is not None:
                query += " AND school = ?"
                params.append(school)
            if not include_superseded:
                query += " AND superseded_by IS NULL"
            query += " ORDER BY confidence DESC, id DESC"

            with self._cursor() as cursor:
                rows = cursor.execute(query, params).fetchall()
            for row in rows:
                entry = _to_entry(row)
                # A school that answered at a more specific rung is not asked again.
                if entry.school in found and rung != ladder[0]:
                    continue
                found.setdefault(entry.school, []).append((rung, entry))
        return found

    def history(self, factor: str | Factor, school: str | None = None) -> list[Entry]:
        """Every version ever recorded for a factor, oldest first."""
        key = str(factor if isinstance(factor, Factor) else parse(factor, allow_unknown_types=True))
        query = "SELECT * FROM entries WHERE factor = ?"
        params: list[object] = [key]
        if school is not None:
            query += " AND school = ?"
            params.append(school)
        with self._cursor() as cursor:
            rows = cursor.execute(query + " ORDER BY id", params).fetchall()
        return [_to_entry(row) for row in rows]

    def search(self, text: str, *, limit: int = 20) -> list[Entry]:
        """Full-text search across delineations."""
        with self._cursor() as cursor:
            rows = cursor.execute(
                "SELECT entries.* FROM entries_fts JOIN entries ON entries.id = entries_fts.rowid"
                " WHERE entries_fts MATCH ? AND entries.superseded_by IS NULL"
                " ORDER BY rank LIMIT ?",
                (text, limit),
            ).fetchall()
        return [_to_entry(row) for row in rows]

    def schools(self) -> list[tuple[str, int]]:
        """Schools present in the store, with their active entry counts."""
        with self._cursor() as cursor:
            rows = cursor.execute(
                "SELECT school, COUNT(*) AS n FROM entries WHERE superseded_by IS NULL"
                " GROUP BY school ORDER BY n DESC"
            ).fetchall()
        return [(row["school"], row["n"]) for row in rows]

    def coverage(self, school: str, factors: list[str]) -> list[tuple[str, bool]]:
        """Which of a list of factors this school has an entry for.

        Answers 'what have I not written up yet', which is the question that
        actually drives manual authoring forward.
        """
        with self._cursor() as cursor:
            rows = cursor.execute(
                "SELECT DISTINCT factor FROM entries WHERE school = ? AND superseded_by IS NULL",
                (school,),
            ).fetchall()
        have = {row["factor"] for row in rows}
        return [
            (key, str(parse(key, allow_unknown_types=True)) in have)
            for key in factors
        ]


def _to_entry(row: sqlite3.Row) -> Entry:
    return Entry(
        id=row["id"],
        school=row["school"],
        factor=row["factor"],
        text=row["text"],
        provenance=Provenance(row["provenance"]),
        source_detail=row["source_detail"],
        confidence=row["confidence"],
        created_at=row["created_at"],
        supersedes=row["supersedes"],
        superseded_by=row["superseded_by"],
    )


def format_lookup(
    factor: Factor, results: dict[str, list[tuple[Factor, Entry]]], *, width: int = 88
) -> str:
    """Render a lookup so that disagreement between schools is the visible thing."""
    import textwrap

    lines = [f"{describe(factor)}", f"  {factor}", ""]
    if not results:
        lines.append("  no school has a delineation for this factor yet.")
        lines.append(f"  add one:  astro define '{factor}' --school <name> --text '...'")
        return "\n".join(lines)

    for school in sorted(results):
        for rung, entry in results[school]:
            heading = f"  [{school}]"
            if rung != factor:
                heading += f"  (general: {rung})"
            lines.append(heading)
            for paragraph in entry.text.split("\n"):
                lines.extend(
                    textwrap.wrap(paragraph, width=width, initial_indent="    ",
                                  subsequent_indent="    ") or ["    "]
                )
            lines.append(f"    — {entry.attribution()}  [#{entry.id}]")
            lines.append("")

    if len(results) > 1:
        lines.append(f"  {len(results)} schools answered. They are shown together on purpose:")
        lines.append("  where they disagree, the disagreement is the finding.")
    return "\n".join(lines)
