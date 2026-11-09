"""Tests for the two-stage monster species research (lore-species-research).

Covers the sighted/defeated writers, the defeated-species reader, the
best-effort post-commit schedulers, and the sole-writer boundary of
``lore_species_defeated``. Every species is a synthetic kit row or a
factory-built row; no shipped species, variant or tier key appears here.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.combat_initiation import schedule_session_sightings
from world.rules.combat_session import engage_group, read_session
from world.rules.combat_session.rounds import _record_round_defeats

from world.rules.lore_knowledge import (
    LoreKeyError,
    LoreRecordError,
    list_discovered,
    list_species_defeated,
    record_species_defeat,
    record_species_sighting,
    schedule_species_defeat_best_effort,
    schedule_species_sighting_best_effort,
)
from world.rules.monster_individual import construct_species_individual
from world.tests.synthetic_data import (
    make_monster_species,
    make_monster_variant,
    synthetic_registries,
)

from ._combat_session_helpers import (
    _monster as _plain_monster,
    _player as _combat_player,
    open_synthetic_scope,
)
from ._knowledge_probes import live_monster_species_registry, live_registry
from .combat_fixtures import BattlefieldIsolation

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

    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
    def test_first_sighting_records_the_species_once(self):
        species, _ = _species_keys()
        player = _player()
        record_species_sighting(player, species)
        self.assertEqual(player.db.lore_discovered, {f"monster:{species}"})
        self.assertIsNone(player.db.lore_species_defeated)
        self.assertEqual(self.push.call_count, 1)

    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
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

    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
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

    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
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

    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
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
    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
    def test_reader_returns_sorted_keys(self):
        first, second = _species_keys()
        player = _player(lore_species_defeated={second, first})
        self.assertEqual(list_species_defeated(player), (first, second))

    def test_absent_record_reads_as_empty(self):
        self.assertEqual(list_species_defeated(_player()), ())

    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
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

    @covers_requirement("lore-knowledge::monster-research-has-a-sighted-and-a-defeated-stage-under-dedicated-writers")
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


_SECOND_VARIANT = "t_second_species_ordinary"
_SESSION_LOGICALS = (
    "monster_species",
    "monster_variants",
    "monster_tiers",
    "races",
    "subraces",
    "static_tiers",
    "elements",
)


def _session_extra():
    return {
        "monster_species": {
            _SECOND_SPECIES: make_monster_species(
                _SECOND_SPECIES, default_variant_key=_SECOND_VARIANT
            )
        },
        "monster_variants": {
            _SECOND_VARIANT: make_monster_variant(
                _SECOND_VARIANT, species_key=_SECOND_SPECIES
            )
        },
    }


class _SessionFixture(BattlefieldIsolation, EvenniaTest):
    """A player in a room plus species-backed monsters of two synthetic species."""

    def setUp(self):
        open_synthetic_scope(self, *_SESSION_LOGICALS, extra=_session_extra())
        super().setUp()
        self.room = create_object(Room, key="t research arena")
        self.player = _combat_player("t research hunter")
        self.player.location = self.room
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        variants = live_registry("world.lore.monster_species", "MONSTER_VARIANT" + "_REGISTRY")
        self.first_species = next(
            key for key in live_monster_species_registry() if key != _SECOND_SPECIES
        )
        first_variant = next(
            key
            for key, variant in variants.items()
            if variant.species_key == self.first_species and variant.ordinary_variant
        )
        self.first_a = self._individual(self.first_species, first_variant)
        self.first_b = self._individual(self.first_species, first_variant)
        self.second = self._individual(_SECOND_SPECIES, _SECOND_VARIANT)

    def _individual(self, species_key, variant_key):
        individual = construct_species_individual(species_key, variant_key)
        individual.traits.hp.base = 1000
        individual.traits.hp.current = 1000
        individual.location = self.room
        return individual

    def _sighted(self, player):
        return tuple(key for category, key in list_discovered(player) if category == "monster")


class SessionSightingTests(_SessionFixture):
    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_an_engagement_sights_each_species_once(self):
        with patch(_PUSH), self.captureOnCommitCallbacks(execute=True):
            engage_group(self.player, [self.first_a, self.second, self.first_b])
        self.assertEqual(
            self._sighted(self.player),
            tuple(sorted((self.first_species, _SECOND_SPECIES))),
        )
        self.assertEqual(list_species_defeated(self.player), ())

    def test_sightings_are_scheduled_once_per_species(self):
        with patch(
            "world.rules.lore_knowledge.schedule_species_sighting_best_effort"
        ) as schedule:
            engage_group(self.player, [self.first_a, self.second, self.first_b])
        self.assertEqual(
            sorted(call.args for call in schedule.call_args_list),
            sorted(
                [(self.player, self.first_species), (self.player, _SECOND_SPECIES)]
            ),
        )

    def test_creation_passes_the_actor_companions_and_targets(self):
        companion = _combat_player("t research bound ally")
        companion.location = self.room
        with patch(
            "world.rules.party.combat_companions", return_value=[companion]
        ), patch(
            "world.rules.combat_initiation.schedule_session_sightings"
        ) as sightings:
            engage_group(self.player, [self.second, self.first_a])
        sightings.assert_called_once()
        participants, targets = sightings.call_args.args
        self.assertEqual(tuple(participants), (self.player, companion))
        self.assertEqual(list(targets), [self.second, self.first_a])

    def test_a_non_player_companion_is_not_credited(self):
        companion = create_object(NPC, key="t research companion", location=self.room)
        with patch(
            "world.rules.lore_knowledge.schedule_species_sighting_best_effort"
        ) as schedule:
            schedule_session_sightings((self.player, companion), (self.second,))
            schedule_session_sightings((companion,), (self.first_a,))
        self.assertEqual(
            [call.args for call in schedule.call_args_list],
            [(self.player, _SECOND_SPECIES)],
        )

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_a_species_less_monster_records_nothing(self):
        plain = _plain_monster("t research plain", hp=1000)
        plain.location = self.room
        self.assertIsNone(plain.species_key)
        with patch(_PUSH), self.captureOnCommitCallbacks(execute=True):
            engage_group(self.player, [plain])
        self.assertIsNotNone(read_session(self.player))
        self.assertIsNone(self.player.db.lore_discovered)

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_a_rolled_back_engagement_records_nothing(self):
        with patch(_PUSH) as push, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    engage_group(self.player, [self.first_a, self.second])
                    raise RuntimeError("t injected rollback")
        self.assertIsNone(self.player.db.lore_discovered)
        push.assert_not_called()


_DEFEAT = "world.rules.lore_knowledge.schedule_species_defeat_best_effort"


class RoundDefeatTests(_SessionFixture):
    """``_record_round_defeats`` driven directly, as the population tests do."""

    def setUp(self):
        super().setUp()
        self.ally = _combat_player("t research ally")
        self.ally.location = self.room

    def _record(self, *enemies, mode="hostile", population_cell=None):
        return SimpleNamespace(
            session_id="hostile:1:100",
            engagement_id="hostile:1:100:1",
            mode=mode,
            enemy_ids=tuple(int(enemy.pk) for enemy in enemies),
            player_ids=(int(self.player.pk), int(self.ally.pk)),
            started_tick=100,
            population_cell=population_cell,
        )

    def _battlefield(self, *entities):
        return SimpleNamespace(
            roster={str(entity.pk): entity for entity in entities}, fled=set()
        )

    def _run(self, record, battlefield, hp_before, hp_after):
        with patch(_DEFEAT) as schedule:
            _record_round_defeats(record, battlefield, hp_before, hp_after, 1)
        return sorted((int(player.pk), key) for player, key in (
            call.args for call in schedule.call_args_list
        ))

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_a_lethal_crossing_credits_every_session_player(self):
        monster = self.first_a
        battlefield = self._battlefield(self.player, self.ally, monster)
        calls = self._run(
            self._record(monster), battlefield, {monster.pk: 5}, {monster.pk: 0}
        )
        self.assertEqual(
            calls,
            sorted(
                [
                    (int(self.player.pk), self.first_species),
                    (int(self.ally.pk), self.first_species),
                ]
            ),
        )

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_an_unmapped_session_still_records_the_defeat(self):
        monster = self.second
        record = self._record(monster)
        self.assertIsNone(record.population_cell)
        calls = self._run(
            record,
            self._battlefield(self.player, monster),
            {monster.pk: 5},
            {monster.pk: 0},
        )
        self.assertEqual(calls, [(int(self.player.pk), _SECOND_SPECIES)])

    def test_two_crossings_of_one_species_schedule_once_per_player(self):
        a, b = self.first_a, self.first_b
        calls = self._run(
            self._record(a, b),
            self._battlefield(self.player, a, b),
            {a.pk: 5, b.pk: 4},
            {a.pk: 0, b.pk: -2},
        )
        self.assertEqual(calls, [(int(self.player.pk), self.first_species)])

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_only_a_real_crossing_records(self):
        dead, hurt = self.first_a, self.second
        calls = self._run(
            self._record(dead, hurt),
            self._battlefield(self.player, dead, hurt),
            {dead.pk: 0, hurt.pk: 5},
            {dead.pk: 0, hurt.pk: 3},
        )
        self.assertEqual(calls, [])

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_a_guild_examination_records_nothing(self):
        monster = self.first_a
        calls = self._run(
            self._record(monster, mode="guild_exam"),
            self._battlefield(self.player, monster),
            {monster.pk: 5},
            {monster.pk: 0},
        )
        self.assertEqual(calls, [])

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_a_species_less_monster_records_nothing(self):
        plain = _plain_monster("t research plain foe", hp=5)
        self.assertIsNone(plain.species_key)
        calls = self._run(
            self._record(plain),
            self._battlefield(self.player, plain),
            {plain.pk: 5},
            {plain.pk: 0},
        )
        self.assertEqual(calls, [])

    def test_a_non_player_roster_entity_is_not_credited(self):
        monster = self.second
        companion = create_object(NPC, key="t research npc ally", location=self.room)
        record = self._record(monster)
        record.player_ids = (*record.player_ids, int(companion.pk))
        calls = self._run(
            record,
            self._battlefield(self.player, companion, monster),
            {monster.pk: 5},
            {monster.pk: 0},
        )
        self.assertEqual(calls, [(int(self.player.pk), _SECOND_SPECIES)])

    @covers_requirement("lore-knowledge::combat-records-the-species-it-sighted-and-defeated")
    def test_a_planned_target_defeated_event_stages_no_lore_effect(self):
        """Out-of-round defeats reach only the quest planner, which stages no
        species defeat and no tier reveal (the documented boundary).

        The entry carries the individual's registered threat tier, which the
        retired planner reveal would have turned into a lore effect; the
        actor holds no quest records, so any staged effect is a lore effect.
        """
        from world.quests.planner import quest_event_effect_planner

        monster = self.second
        entry = SimpleNamespace(
            kind="target_defeated",
            data={
                "target_id": int(monster.pk),
                "monster_tier": monster.threat_tier,
                "species_key": monster.species_key,
                "variant_key": monster.variant_key,
            },
        )
        request = SimpleNamespace(
            actor=self.player, context=SimpleNamespace(battlefield=None)
        )
        with patch(_DEFEAT) as defeat, patch(
            "world.rules.lore_knowledge.schedule_lore_reveal_best_effort"
        ) as reveal:
            effects = quest_event_effect_planner(request, SimpleNamespace(entries=[entry]))
            for effect in effects:
                effect.apply()
        self.assertEqual(effects, [])
        defeat.assert_not_called()
        reveal.assert_not_called()


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
