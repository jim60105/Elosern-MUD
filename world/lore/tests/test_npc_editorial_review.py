"""Data-contract test: registry-indexed NPC characterization editorial review contract

Every live NPC source the registries derive carries exactly one dated ledger
entry, with a disposition for each authored surface its kind owns -- profile,
card and voice for place hosts and persistent people, greeting, responses and
service semantics for dialogue tables, a card and a voice for starting
companions, and a card for quest-template occupants and import cards. The
ledger is checked both ways against the actual derived source set, so a new
source arrives with its entry and an entry that outlives its source fails.

This module also proves the ledger is not an expected-dialogue fixture --
rewording the shipped prose cannot fail a relationship check -- and drives
every named ledger fault (duplicate, orphan, missing, undated, wrong face
count, blank face, blank disposition and unknown kind) through the same pure
parser and checker with synthetic rows.

No expected greeting, response, card or voice line appears here: the prose half
of the authored content stays editable, and the ledger's own limits (it proves
coverage and structure, never editorial quality and never freshness) are
stated rather than faked.
"""

from __future__ import annotations

import pathlib
import unittest

from tools.spec_traceability import covers_requirement
from world.ai.director_templates import QUEST_TEMPLATE_POOL
from world.lore.dialogue import DIALOGUE_ROWS
from world.lore.npc_editorial_review import (
    check_npc_editorial_ledger,
    parse_npc_editorial_ledger,
    unparsed_ledger_rows,
)
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.rules.npc_roster_validation import derive_shipped_sources

LEDGER = (
    pathlib.Path(__file__).resolve().parents[3]
    / "docs"
    / "development"
    / "npc-editorial-review.md"
)


def _live_sources() -> frozenset[tuple[str, str]]:
    """The actual live NPC sources, derived from the live registries."""
    return derive_shipped_sources(quest_templates=QUEST_TEMPLATE_POOL)


def _shipped_spoken_lines() -> list[str]:
    """Every shipped spoken line, across all six source kinds.

    Dialogue greetings and keyword responses, the profile voice lines of hosts
    and persistent people, and the companion presets' offline greetings - every
    authored surface that is a spoken line rather than a card field.
    """
    lines: list[str] = []
    for definition in DIALOGUE_ROWS.values():
        lines.append(definition.greeting)
        lines.extend(response.response for response in definition.responses)
    for profile in NPC_PROFILE_REGISTRY.values():
        for line in (profile.voice.greeting, profile.voice.misunderstood):
            if line:
                lines.append(line)
    for preset in PLAYER_PRESET_REGISTRY.values():
        if preset.persona.greeting:
            lines.append(preset.persona.greeting)
    return lines


class LiveNpcEditorialLedgerTests(unittest.TestCase):
    """Requirement: the shipped ledger covers every actual live source."""

    maxDiff = None

    @covers_requirement(
        "npc-profile-registry::authored-host-dialogue-preserves-service-semantics"
    )
    def test_every_actual_source_has_one_dated_dispositioned_entry(self):
        text = LEDGER.read_text(encoding="utf-8")
        entries = parse_npc_editorial_ledger(text)
        # No row-shaped line may be silently dropped by the anchored parser: a
        # dropped live row still surfaces as a missing entry, but a dropped
        # orphan row would otherwise be invisible.
        self.assertEqual(unparsed_ledger_rows(text), ())
        live = _live_sources()
        self.assertEqual({(entry.kind, entry.key) for entry in entries}, set(live))
        self.assertEqual(check_npc_editorial_ledger(live, entries), ())

    @covers_requirement(
        "npc-profile-registry::authored-host-dialogue-preserves-service-semantics"
    )
    def test_the_ledger_is_not_an_expected_dialogue_fixture(self):
        text = LEDGER.read_text(encoding="utf-8")
        lines = _shipped_spoken_lines()
        # Guard against a vacuous scan: the checked population is dominated by
        # lines far longer than the ledger's structural vocabulary, so a
        # membership hit would be a real quotation rather than a coincidence.
        long_lines = [
            line for line in lines if len(line) > len("service-semantics")
        ]
        self.assertGreaterEqual(len(long_lines), len(DIALOGUE_ROWS))
        for line in lines:
            self.assertNotIn(line, text)

    @covers_requirement(
        "npc-profile-registry::authored-host-dialogue-preserves-service-semantics"
    )
    def test_a_wording_only_edit_of_the_ledger_still_passes(self):
        text = LEDGER.read_text(encoding="utf-8")
        entries = parse_npc_editorial_ledger(text)
        live = _live_sources()
        # Both cell kinds are freely editable prose: a disposition-cell reword
        # and a face-cell reword each leave the relationship check untouched.
        edits = (
            ("accepted:", "reviewed and accepted:"),
            ("resolves under slice", "resolves cleanly under slice"),
        )
        for old, new in edits:
            reworded = text.replace(old, new)
            self.assertNotEqual(reworded, text)
            self.assertEqual(
                check_npc_editorial_ledger(
                    live, parse_npc_editorial_ledger(reworded)
                ),
                (),
            )
            self.assertEqual(
                len(parse_npc_editorial_ledger(reworded)), len(entries)
            )
        disposition_edit = text.replace(*edits[0])
        hits = sum(
            1
            for before, after in zip(
                text.splitlines(), disposition_edit.splitlines()
            )
            if before != after
        )
        # Every row's overall disposition carries the reworded marker, so the
        # edit reaches every kind rather than only one block.
        self.assertGreaterEqual(hits, len(entries))


class NpcEditorialLedgerFaultTests(unittest.TestCase):
    """Requirement: every named ledger fault is rejected, naming the source."""

    LIVE = frozenset({("dialogue_table", "t_table"), ("place_host", "t_host")})
    VALID = (
        "| `dialogue_table` | `t_table` | 2026-01-01 | a | b | c | accepted |",
        "| `place_host` | `t_host` | 2026-01-01 | p | c | v | accepted |",
    )

    def _entries(self, *rows: str):
        return parse_npc_editorial_ledger("\n".join(rows))

    @covers_requirement(
        "npc-profile-registry::authored-host-dialogue-preserves-service-semantics"
    )
    def test_named_ledger_relationship_faults_are_reported(self):
        self.assertEqual(
            check_npc_editorial_ledger(self.LIVE, self._entries(*self.VALID)), ()
        )

        problems = check_npc_editorial_ledger(
            self.LIVE, self._entries(*self.VALID, self.VALID[0])
        )
        self.assertIn("dialogue_table:t_table: reviewed more than once", problems)

        orphan = "| `dialogue_table` | `t_retired` | 2026-01-01 | a | b | c | accepted |"
        problems = check_npc_editorial_ledger(self.LIVE, self._entries(*self.VALID, orphan))
        self.assertIn(
            "dialogue_table:t_retired: ledger entry for an unshipped source", problems
        )

        ghost = "| `ghost_table` | `t_ghost` | 2026-01-01 | a | accepted |"
        problems = check_npc_editorial_ledger(self.LIVE, self._entries(*self.VALID, ghost))
        self.assertIn(
            "ghost_table:t_ghost: ledger entry names an unknown source kind", problems
        )

        undated = "| `dialogue_table` | `t_table` | yesterday | a | b | c | accepted |"
        problems = check_npc_editorial_ledger(
            self.LIVE, self._entries(undated, self.VALID[1])
        )
        self.assertIn(
            "dialogue_table:t_table: review date 'yesterday' is not YYYY-MM-DD",
            problems,
        )

        short = "| `dialogue_table` | `t_table` | 2026-01-01 | a | b | accepted |"
        problems = check_npc_editorial_ledger(
            self.LIVE, self._entries(short, self.VALID[1])
        )
        self.assertIn(
            "dialogue_table:t_table: records 2 reviewed faces, expected 3", problems
        )

        blank_face = "| `place_host` | `t_host` | 2026-01-01 | p |  | v | accepted |"
        problems = check_npc_editorial_ledger(
            self.LIVE, self._entries(self.VALID[0], blank_face)
        )
        self.assertIn(
            "place_host:t_host: a reviewed face carries no disposition", problems
        )

        silent = "| `place_host` | `t_host` | 2026-01-01 | p | c | v |  |"
        problems = check_npc_editorial_ledger(
            self.LIVE, self._entries(self.VALID[0], silent)
        )
        self.assertIn("place_host:t_host: carries no overall disposition", problems)

        problems = check_npc_editorial_ledger(self.LIVE, self._entries(self.VALID[0]))
        self.assertIn("place_host:t_host: no editorial review entry", problems)

    @covers_requirement(
        "npc-profile-registry::authored-host-dialogue-preserves-service-semantics"
    )
    def test_a_dropped_orphan_row_is_surfaced_by_the_parse_guard(self):
        orphan_row = (
            "| `dialogue_table` | t_hidden | 2026-01-01 | a | b | c | accepted |"
        )
        text = "\n".join((*self.VALID, orphan_row))
        # A backticked but unindexed row cannot match the anchored pattern, so
        # the strict parse drops it; the guard reports it instead of hiding the
        # orphan behind an invisible skip.
        self.assertEqual(len(parse_npc_editorial_ledger(text)), 2)
        self.assertEqual(unparsed_ledger_rows(text), (orphan_row,))
        # A well-formed header row (no backticked token) is not a candidate,
        # and neither is an ordinary marked-up row.
        self.assertEqual(
            unparsed_ledger_rows("| kind | key | reviewed | disposition |"), ()
        )
        self.assertEqual(unparsed_ledger_rows("\n".join(self.VALID)), ())


if __name__ == "__main__":
    unittest.main()
