"""Pure parser and checker for the indexed NPC characterization review ledger.

The shipped NPC characterization is authored content: immutable profiles (key,
compact card, bounded ages, voice lines) under ``world/lore/npc_profiles/``
and scripted dialogue tables (a greeting plus keyword responses) under
``world/lore/dialogue/``. Whether that prose *reads well* is not something a
test can assert, so -- exactly like the bestiary's editorial ledger -- this
module owns a dated, source-indexed review record instead of an
expected-prose fixture.

Both halves are pure: :func:`parse_npc_editorial_ledger` turns the ledger
markdown into entries, and :func:`check_npc_editorial_ledger` compares those
entries with the actual live sources -- the ``(kind, key)`` pairs the live
registries derive through
``world.rules.npc_roster_validation.derive_shipped_sources``. Neither reads a
file, opens a database, or pins a single line of dialogue, so rewording valid
prose can never fail a relationship check. The record proves coverage only: it
never judges prose quality and never claims a review is still fresh after a
later content edit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: The authored surfaces each source kind owns, so one ledger entry records a
#: disposition for every face its kind authors. A kind that grows a surface
#: extends this declaration (and the author guide names it); a count mismatch is
#: reported instead of silently accepted. Deliberately a tuple of tuples, never
#: a mapping, so this checker is never mistaken for a catalog-data module by the
#: test-data universe derivation.
LEDGER_FACES_BY_KIND = (
    ("place_host", ("profile", "card", "voice")),
    ("dialogue_table", ("greeting", "responses", "service-semantics")),
    ("persistent_adventurer", ("profile", "card", "voice")),
    ("starting_companion", ("card", "voice")),
    ("quest_template_occupant", ("card",)),
    ("import_example", ("card",)),
)
#: ``| `kind` | `key` | reviewed | face... | disposition |``. A cell must not
#: carry a bare ``|`` (escape it or use a fullwidth ｜): the greedy cell group
#: reads to the row's last pipe, so a raw pipe shifts the faces right. The
#: anchoring ``^\|`` is kept without ``$`` so a wrapped cell never drops a whole
#: row, and :func:`unparsed_ledger_rows` reports any row the anchor rejects.
LEDGER_ROW = re.compile(
    r"^\|\s*`(?P<kind>[a-z_]+)`\s*\|\s*`(?P<key>[^`]+)`\s*\|(?P<cells>.+)\|"
)
LEDGER_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class LedgerEntry:
    """One indexed editorial review of one live NPC source."""

    kind: str
    key: str
    reviewed: str
    faces: tuple[str, ...]
    disposition: str


def parse_npc_editorial_ledger(text: str) -> tuple[LedgerEntry, ...]:
    """Parse the ledger's ``| `kind` | `key` | date | face... | disposition |`` rows."""
    entries: list[LedgerEntry] = []
    for line in text.splitlines():
        match = LEDGER_ROW.match(line.strip())
        if match is None:
            continue
        cells = [cell.strip() for cell in match.group("cells").split("|")]
        entries.append(
            LedgerEntry(
                kind=match.group("kind"),
                key=match.group("key"),
                reviewed=cells[0] if cells else "",
                faces=tuple(cells[1:-1]),
                disposition=cells[-1] if len(cells) > 1 else "",
            )
        )
    return tuple(entries)


def unparsed_ledger_rows(text: str) -> tuple[str, ...]:
    """Row-looking lines a strict parse dropped, so an orphan row cannot hide.

    A line is a candidate when it starts a table row and carries a backticked
    token; a candidate that :func:`parse_npc_editorial_ledger` rejects is
    returned verbatim. That rejection is the anchored regex's one silent-drop
    path, and it is exactly the path an unnoticed orphan entry would take.
    """
    return tuple(
        line
        for line in text.splitlines()
        if line.strip().startswith("|")
        and "`" in line
        and LEDGER_ROW.match(line.strip()) is None
    )


def check_npc_editorial_ledger(
    sources, entries: tuple[LedgerEntry, ...]
) -> tuple[str, ...]:
    """Return one problem per broken ledger relationship (empty when valid).

    The record proves coverage -- every live source was reviewed on a stated
    date with a disposition for each face its kind authors -- and never judges
    the prose itself nor claims the review is still fresh. ``sources`` is the
    actual live ``(kind, key)`` set, so a missing entry, an orphan entry and an
    unknown kind are each named.
    """
    problems: list[str] = []
    live = set(sources)
    faces_by_kind = dict(LEDGER_FACES_BY_KIND)
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        ident = (entry.kind, entry.key)
        label = f"{entry.kind}:{entry.key}"
        if ident in seen:
            problems.append(f"{label}: reviewed more than once")
            continue
        seen.add(ident)
        expected = faces_by_kind.get(entry.kind)
        if expected is None:
            problems.append(f"{label}: ledger entry names an unknown source kind")
            continue
        if ident not in live:
            problems.append(f"{label}: ledger entry for an unshipped source")
        if LEDGER_DATE.match(entry.reviewed) is None:
            problems.append(f"{label}: review date {entry.reviewed!r} is not YYYY-MM-DD")
        if len(entry.faces) != len(expected):
            problems.append(
                f"{label}: records {len(entry.faces)} reviewed faces, "
                f"expected {len(expected)}"
            )
        elif not all(entry.faces):
            problems.append(f"{label}: a reviewed face carries no disposition")
        if not entry.disposition:
            problems.append(f"{label}: carries no overall disposition")
    for kind, key in sorted(live - seen):
        problems.append(f"{kind}:{key}: no editorial review entry")
    return tuple(problems)
