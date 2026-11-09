"""Tests for the two-stage monster species research (lore-species-research).

Covers the sighted/defeated writers, the defeated-species reader, the
best-effort post-commit schedulers, and the sole-writer boundary of
``lore_species_defeated``. Every species is a synthetic kit row or a
factory-built row; no shipped species, variant or tier key appears here.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.rules.lore_knowledge import (
    LoreKeyError,
    LoreRecordError,
    list_species_defeated,
    record_species_defeat,
    record_species_sighting,
    schedule_species_defeat_best_effort,
    schedule_species_sighting_best_effort,
)
from world.tests.synthetic_data import make_monster_species, synthetic_registries

from ._knowledge_probes import live_monster_species_registry

_SECOND_SPECIES = "t_second_species"
_SPECIES_EXTRA = {
    "monster_species": {_SECOND_SPECIES: make_monster_species(_SECOND_SPECIES)},
}
_PUSH = "world.rules.lore_knowledge._schedule_lore_codex_push"


class _StubDb:
    """Evennia-like ``db`` attribute surface: missing attributes read as None."""

    def __getattr__(self, name):
        return None


class _Stub:
    """A minimal player stand-in exposing only ``db`` and ``key``."""

    def __init__(self):
        self.db = _StubDb()
        self.key = "t-research-char"


def _player(**attrs):
    stub = _Stub()
    for key, value in attrs.items():
        setattr(stub.db, key, value)
    return stub


def _species_keys() -> tuple[str, str]:
    """Two registered species keys of the current scope, in sorted order."""
    registry = live_monster_species_registry()
    first = next(key for key in registry if key != _SECOND_SPECIES)
    return tuple(sorted((first, _SECOND_SPECIES)))


@synthetic_registries("monster_species", "monster_tiers", extra=_SPECIES_EXTRA)
class SpeciesWriterTests(unittest.TestCase):
    def setUp(self):
        patcher = patch(_PUSH)
        self.push = patcher.start()
        self.addCleanup(patcher.stop)

    def test_first_sighting_records_the_species_once(self):
        species, _ = _species_keys()
        player = _player()
        record_species_sighting(player, species)
        self.assertEqual(player.db.lore_discovered, {f"monster:{species}"})
        self.assertIsNone(player.db.lore_species_defeated)
        self.assertEqual(self.push.call_count, 1)

    def test_defeat_implies_a_sighting(self):
        species, _ = _species_keys()
        player = _player()
        record_species_defeat(player, species)
        self.assertEqual(player.db.lore_discovered, {f"monster:{species}"})
        self.assertEqual(player.db.lore_species_defeated, {species})
        # One push per changed record: the sighting and the defeat.
        self.assertEqual(self.push.call_count, 2)

    def test_defeat_of_a_sighted_species_pushes_once(self):
        species, _ = _species_keys()
        player = _player(lore_discovered={f"monster:{species}"})
        record_species_defeat(player, species)
        self.assertEqual(player.db.lore_species_defeated, {species})
        self.assertEqual(self.push.call_count, 1)

    def test_repeat_sighting_and_defeat_are_no_ops(self):
        species, _ = _species_keys()
        player = _player()
        record_species_defeat(player, species)
        discovered = set(player.db.lore_discovered)
        defeated = set(player.db.lore_species_defeated)
        self.push.reset_mock()
        record_species_sighting(player, species)
        record_species_defeat(player, species)
        self.assertEqual(player.db.lore_discovered, discovered)
        self.assertEqual(player.db.lore_species_defeated, defeated)
        self.push.assert_not_called()

    def test_unknown_species_rejects_through_both_writers(self):
        species, _ = _species_keys()
        for writer in (record_species_sighting, record_species_defeat):
            for bad in ("t_absent_species", None, 7):
                with self.subTest(writer=writer.__name__, key=bad):
                    player = _player(
                        lore_discovered={f"monster:{species}"},
                        lore_species_defeated={species},
                    )
                    with self.assertRaises(LoreKeyError):
                        writer(player, bad)
                    self.assertEqual(player.db.lore_discovered, {f"monster:{species}"})
                    self.assertEqual(player.db.lore_species_defeated, {species})
        self.push.assert_not_called()

    def test_corrupt_defeated_record_is_never_repaired(self):
        species, _ = _species_keys()
        for corrupt in ({42}, "x", {"a:b"}, {""}, {"t_absent_species"}):
            with self.subTest(record=corrupt):
                player = _player(lore_species_defeated=corrupt)
                stored = player.db.lore_species_defeated
                with self.assertRaises(LoreRecordError):
                    record_species_defeat(player, species)
                self.assertIs(player.db.lore_species_defeated, stored)
                self.assertEqual(player.db.lore_species_defeated, corrupt)
                self.assertIsNone(player.db.lore_discovered)
        self.push.assert_not_called()

    def test_corrupt_codex_record_blocks_the_defeat_too(self):
        species, _ = _species_keys()
        player = _player(lore_discovered={42}, lore_species_defeated=set())
        with self.assertRaises(LoreRecordError):
            record_species_defeat(player, species)
        self.assertEqual(player.db.lore_discovered, {42})
        self.assertEqual(player.db.lore_species_defeated, set())
        self.push.assert_not_called()


@synthetic_registries("monster_species", "monster_tiers", extra=_SPECIES_EXTRA)
class SpeciesReaderTests(unittest.TestCase):
    def test_reader_returns_sorted_keys(self):
        first, second = _species_keys()
        player = _player(lore_species_defeated={second, first})
        self.assertEqual(list_species_defeated(player), (first, second))

    def test_absent_record_reads_as_empty(self):
        self.assertEqual(list_species_defeated(_player()), ())

    def test_tolerant_reader_keeps_a_vanished_key(self):
        first, _ = _species_keys()
        player = _player(lore_species_defeated={first, "t_vanished_species"})
        with self.assertRaises(LoreRecordError):
            list_species_defeated(player)
        self.assertEqual(
            list_species_defeated(player, tolerant=True),
            (first, "t_vanished_species"),
        )

    def test_tolerant_reader_still_rejects_malformed_entries(self):
        for corrupt in ({42}, "x", {"a:b"}):
            with self.subTest(record=corrupt):
                with self.assertRaises(LoreRecordError):
                    list_species_defeated(
                        _player(lore_species_defeated=corrupt), tolerant=True
                    )


@synthetic_registries("monster_species", "monster_tiers", extra=_SPECIES_EXTRA)
class SpeciesBestEffortTests(unittest.TestCase):
    """Outside a transaction Django runs on-commit callbacks immediately."""

    def test_failing_callback_is_logged_with_its_stage(self):
        species, _ = _species_keys()
        cases = (
            (schedule_species_sighting_best_effort, "record_species_sighting", "sighted"),
            (schedule_species_defeat_best_effort, "record_species_defeat", "defeated"),
        )
        for scheduler, writer, stage in cases:
            with self.subTest(stage=stage):
                error = RuntimeError("boom")
                player = _player()
                with patch(
                    f"world.rules.lore_knowledge.{writer}", side_effect=error
                ), patch("world.rules.lore_knowledge.log_warn") as log:
                    scheduler(player, species)
                log.assert_called_once()
                self.assertEqual(log.call_args.args[0], "lore_reveal_failed")
                self.assertIs(log.call_args.kwargs["exc"], error)
                context = log.call_args.kwargs["context"]
                self.assertEqual(context["stage"], stage)
                self.assertEqual(context["category"], "monster")
                self.assertEqual(context["key"], species)

    def test_registration_failure_is_logged_and_swallowed(self):
        species, _ = _species_keys()
        error = RuntimeError("no transaction")
        with patch(
            "world.rules.presentation_events.on_publication_commit",
            side_effect=error,
        ), patch("world.rules.lore_knowledge.log_warn") as log:
            schedule_species_defeat_best_effort(_player(), species)
        log.assert_called_once()
        self.assertEqual(log.call_args.kwargs["context"]["stage"], "defeated")

    def test_successful_schedule_writes_both_records(self):
        species, _ = _species_keys()
        player = _player()
        with patch(_PUSH):
            schedule_species_defeat_best_effort(player, species)
        self.assertEqual(player.db.lore_discovered, {f"monster:{species}"})
        self.assertEqual(player.db.lore_species_defeated, {species})

    def test_empty_or_non_string_key_schedules_nothing(self):
        for bad in (None, "", 3):
            with self.subTest(key=bad), patch(
                "world.rules.presentation_events.on_publication_commit"
            ) as register:
                schedule_species_sighting_best_effort(_player(), bad)
                schedule_species_defeat_best_effort(_player(), bad)
            register.assert_not_called()


class SpeciesSoleWriterBoundaryTests(unittest.TestCase):
    @covers_requirement("lore-knowledge::the-codex-is-discoverable-with-every-generative-service-offline")
    def test_no_other_module_writes_the_defeated_record(self):
        root = Path(__file__).resolve().parents[3]
        references = []
        for package in ("commands", "server", "typeclasses", "web", "world"):
            for path in sorted((root / package).rglob("*.py")):
                text = str(path)
                if "/tests/" in text or "/__pycache__/" in text or "/node_modules/" in text:
                    continue
                if "lore_species_defeated" in path.read_text(encoding="utf-8"):
                    references.append(str(path.relative_to(root)))
        self.assertEqual(references, ["world/rules/lore_knowledge.py"])


if __name__ == "__main__":
    unittest.main()
