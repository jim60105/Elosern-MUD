"""Tests for the sexual resist contest (sexual-resist-contest B6a).

Pure formula and rulebook-loading tests use in-memory ``FakeEntity``
fixtures with a patched ``evaluate_combat_modifiers_no_create``; tests that
exercise the affinity paths, the real combat-modifier query, or the real
``SexualState`` use database-backed ``EvenniaTest`` entities.
"""

from tools.spec_traceability import covers_requirement

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yaml

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.lore.sexual_vocab import CLIMAX_PHASE_LEVELS
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.affinity_config import get_config
from world.rules.sexual_resist import (
    ResistVerdict,
    _affinity_term,
    _blended_score,
    get_resist_config,
    load_sexual_resist_config,
    resist_verdict,
)

from .combat_fixtures import FakeEntity

_RULEBOOK = Path(__file__).parents[1] / "rulebook" / "sexual_resist.yaml"

_FAKE_ID_COUNTER = iter(range(1, 1_000_000))


class _FakeAttributes:
    """Minimal attributes stub for the no-create stored-state reads.

    Keys are ``(name, category)`` tuples, mirroring the storage layout
    ``build_no_create_condition_context`` and ``SexualState.climax_turns``
    read from real entities.
    """

    def __init__(self, values=None):
        self._values = {} if values is None else dict(values)

    def get(self, name, default=None, category=None):
        return self._values.get((name, category), default)


def _entity(
    key: str,
    agility: int = 10,
    atk_phys: int = 10,
    sexual_state=None,
) -> FakeEntity:
    entity = FakeEntity(key, agility=agility, atk_phys=atk_phys)
    entity.attributes = _FakeAttributes(sexual_state)
    # The submission-mark term keys on str(actor.id); a bare fake needs an id.
    entity.id = next(_FAKE_ID_COUNTER)
    return entity


def _stored_sexual_state(level: str, turns: int) -> dict:
    """The stored sexual-state facts for one resister's climax bookkeeping."""
    return {
        ("sexual_traits", "traits"): {
            "climax_phase": {
                "value": CLIMAX_PHASE_LEVELS.index(level),
                "levels": CLIMAX_PHASE_LEVELS,
            },
        },
        ("climax_turns", "sexual_state"): turns,
    }


def _mid_climax(turns: int) -> dict:
    """Stored state mirroring a resister in 進行中."""
    return _stored_sexual_state("進行中", turns)


class _SpyRelations:
    """Records every read of the relations handler it replaces."""

    def __init__(self):
        self.touched = False

    def stage_for(self, player):
        self.touched = True
        raise AssertionError("relations must never be read for this resister")


class ResistContestFormulaTests(RegistryIsolationMixin, unittest.TestCase):
    """Pure formula and short-circuit tests with patched modifiers."""

    def setUp(self):
        register_catalog()
        self.modifiers = patch(
            "world.rules.sexual_resist.evaluate_combat_modifiers_no_create",
            return_value={},
        )
        self.modifiers.start()
        self.addCleanup(self.modifiers.stop)

    @covers_requirement("sexual-resist-contest::resist-verdict-is-a-pure-two-party-contest-function")
    def test_requires_no_battlefield(self):
        verdict = resist_verdict(
            _entity("actor"), _entity("resister"), rng=lambda: 1
        )
        self.assertIsInstance(verdict, ResistVerdict)
        self.assertIsInstance(verdict.resisted, bool)
        self.assertIsInstance(verdict.auto_comply, bool)
        self.assertIsInstance(verdict.actor_score, float)
        self.assertIsInstance(verdict.resister_score, float)

    @covers_requirement("sexual-resist-contest::resist-verdict-is-a-pure-two-party-contest-function")
    def test_roll_is_none_exactly_when_auto_comply(self):
        auto = resist_verdict(
            _entity("actor"),
            _entity("resister", sexual_state=_mid_climax(1)),
            rng=lambda: 1,
        )
        rolled = resist_verdict(_entity("actor"), _entity("resister"), rng=lambda: 1)
        for verdict in (auto, rolled):
            with self.subTest(verdict=verdict):
                self.assertEqual(verdict.roll is None, verdict.auto_comply)

    @covers_requirement("sexual-resist-contest::the-ordinary-contest-reuses-the-shipped-to-hit-formula-shape-with-blended-scores")
    def test_higher_blended_stats_resist_more_often(self):
        actor = _entity("actor")
        low = _entity("low")
        high = _entity("high", agility=20)
        low_verdict = resist_verdict(actor, low, rng=lambda: 50)
        high_verdict = resist_verdict(actor, high, rng=lambda: 50)
        self.assertFalse(low_verdict.resisted)
        self.assertTrue(high_verdict.resisted)

    @covers_requirement("sexual-resist-contest::the-ordinary-contest-reuses-the-shipped-to-hit-formula-shape-with-blended-scores")
    def test_blended_score_mirrors_stat_specific_treatments(self):
        entity = _entity("participant")
        with patch(
            "world.rules.sexual_resist.evaluate_combat_modifiers_no_create",
            return_value={"agility": "-20%", "atk_phys": 5},
        ):
            self.assertAlmostEqual(_blended_score(entity), 0.6 * 8 + 0.4 * 15)

    @covers_requirement("sexual-resist-contest::the-ordinary-contest-reuses-the-shipped-to-hit-formula-shape-with-blended-scores")
    def test_formula_reads_the_shipped_defender_constant(self):
        source = (Path(__file__).parents[1] / "sexual_resist.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'COMBAT_YAML["to_hit"]["defender_constant"]', source
        )
        contest_line = next(
            line for line in source.splitlines() if "defender_constant" in line
        )
        self.assertNotIn("51", contest_line)

    @covers_requirement("sexual-resist-contest::a-resister-mid-climax-auto-complies-for-the-first-five-settlement-points-then-resists-normally")
    def test_climax_turn_one_auto_complies_without_rolling(self):
        roller = MagicMock()
        verdict = resist_verdict(
            _entity("actor"),
            _entity("resister", sexual_state=_mid_climax(1)),
            rng=roller,
        )
        self.assertFalse(verdict.resisted)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)
        roller.assert_not_called()

    @covers_requirement("sexual-resist-contest::a-resister-mid-climax-auto-complies-for-the-first-five-settlement-points-then-resists-normally")
    def test_climax_turn_five_auto_complies(self):
        verdict = resist_verdict(
            _entity("actor"),
            _entity("resister", sexual_state=_mid_climax(5)),
            rng=lambda: 1,
        )
        self.assertFalse(verdict.resisted)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)

    @covers_requirement("sexual-resist-contest::a-resister-mid-climax-auto-complies-for-the-first-five-settlement-points-then-resists-normally")
    def test_climax_turn_six_rolls_the_ordinary_contest(self):
        actor = _entity("actor")
        resister = _entity("resister", sexual_state=_mid_climax(6))
        resist_fails = resist_verdict(actor, resister, rng=lambda: 50)
        resist_succeeds = resist_verdict(actor, resister, rng=lambda: 60)
        self.assertFalse(resist_fails.resisted)
        self.assertEqual(resist_fails.roll, 50)
        self.assertTrue(resist_succeeds.resisted)
        self.assertEqual(resist_succeeds.roll, 60)
        self.assertFalse(resist_succeeds.auto_comply)

    @covers_requirement("sexual-resist-contest::a-resister-mid-climax-auto-complies-for-the-first-five-settlement-points-then-resists-normally")
    def test_not_in_progress_never_triggers_the_short_circuit(self):
        for level, turns in (("未達", 1), ("接近", 5), ("餘韻", 6)):
            with self.subTest(level=level, turns=turns):
                resister = _entity(
                    "resister",
                    sexual_state=_stored_sexual_state(level, turns),
                )
                verdict = resist_verdict(
                    _entity("actor"), resister, rng=lambda: 42
                )
                self.assertFalse(verdict.auto_comply)
                self.assertEqual(verdict.roll, 42)

    @covers_requirement("sexual-resist-contest::resist-verdict-is-deterministic-under-an-injected-rng")
    def test_fixed_rng_produces_identical_verdicts(self):
        actor = _entity("actor")
        resister = _entity("resister")
        first = resist_verdict(actor, resister, rng=lambda: 42)
        second = resist_verdict(actor, resister, rng=lambda: 42)
        self.assertEqual(first, second)

    @covers_requirement("sexual-resist-contest::resist-verdict-is-deterministic-under-an-injected-rng")
    def test_default_rng_is_the_shipped_dice_roller(self):
        source = (Path(__file__).parents[1] / "sexual_resist.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("from world.rules.dice import roll_d100", source)
        self.assertIn("rng: Callable[[], int] = roll_d100", source)


class SexualResistConfigTests(RegistryIsolationMixin, unittest.TestCase):
    """Rulebook shape validation, failing closed on any deviation."""

    def setUp(self):
        register_catalog()
        self.canonical = yaml.safe_load(_RULEBOOK.read_text(encoding="utf-8"))

    def _deviant(self, **changes) -> Path:
        data = copy.deepcopy(self.canonical)
        data.update(changes)
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        with handle:
            yaml.dump(data, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    @covers_requirement("sexual-resist-contest::sexual-resist-yaml-validates-its-shape-at-load-time")
    def test_weights_sum_to_one(self):
        config = get_resist_config()
        self.assertEqual(
            config.agility_weight + config.atk_phys_weight,
            1.0,
        )

    @covers_requirement("sexual-resist-contest::sexual-resist-yaml-validates-its-shape-at-load-time")
    def test_affinity_table_covers_exactly_the_seven_stages(self):
        config = get_resist_config()
        stage_ids = {stage.id for stage in get_config().stages}
        self.assertEqual(
            set(config.resist_modifiers) | config.auto_comply_stages,
            stage_ids,
        )
        self.assertEqual(
            set(config.resist_modifiers) & config.auto_comply_stages,
            set(),
        )
        self.assertEqual(
            sorted(config.auto_comply_stages),
            ["absolute_bond", "beloved"],
        )

    @covers_requirement("sexual-resist-contest::sexual-resist-yaml-validates-its-shape-at-load-time")
    def test_malformed_weight_pair_fails_closed(self):
        with self.assertRaises(ValueError) as caught:
            load_sexual_resist_config(
                self._deviant(agility_weight=0.7, atk_phys_weight=0.4)
            )
        self.assertIn("sum", str(caught.exception))

    @covers_requirement("sexual-resist-contest::sexual-resist-yaml-validates-its-shape-at-load-time")
    def test_negative_weight_fails_closed_even_when_sum_is_one(self):
        with self.assertRaises(ValueError) as caught:
            load_sexual_resist_config(
                self._deviant(agility_weight=1.5, atk_phys_weight=-0.5)
            )
        self.assertIn("non-negative", str(caught.exception))

    @covers_requirement("sexual-resist-contest::sexual-resist-yaml-validates-its-shape-at-load-time")
    def test_missing_stage_key_fails_closed_naming_the_key(self):
        modifiers = dict(self.canonical["affinity_resist_modifier"])
        del modifiers["trusted"]
        with self.assertRaises(ValueError) as caught:
            load_sexual_resist_config(
                self._deviant(affinity_resist_modifier=modifiers)
            )
        self.assertIn("trusted", str(caught.exception))

    @covers_requirement("sexual-resist-contest::sexual-resist-yaml-validates-its-shape-at-load-time")
    def test_extra_stage_key_fails_closed_naming_the_key(self):
        modifiers = dict(self.canonical["affinity_resist_modifier"])
        modifiers["mystery"] = 0
        with self.assertRaises(ValueError) as caught:
            load_sexual_resist_config(
                self._deviant(affinity_resist_modifier=modifiers)
            )
        self.assertIn("mystery", str(caught.exception))

    def test_invalid_affinity_value_shape_fails_closed(self):
        for label, entry in (
            ("string", "high"),
            ("bool", True),
            ("auto_comply false", {"auto_comply": False}),
            ("extra mapping key", {"auto_comply": True, "other": 1}),
        ):
            with self.subTest(entry=label):
                modifiers = dict(self.canonical["affinity_resist_modifier"])
                modifiers["acquaintance"] = entry
                with self.assertRaises(ValueError) as caught:
                    load_sexual_resist_config(
                        self._deviant(affinity_resist_modifier=modifiers)
                    )
                self.assertIn("acquaintance", str(caught.exception))

    def test_unknown_or_missing_top_level_field_fails_closed(self):
        with self.assertRaises(ValueError):
            load_sexual_resist_config(self._deviant(mystery_field=1))
        data = copy.deepcopy(self.canonical)
        del data["affinity_resist_modifier"]
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        with handle:
            yaml.dump(data, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaises(ValueError):
            load_sexual_resist_config(Path(handle.name))


class SexualResistAffinityTests(EvenniaTestCase):
    """Database-backed tests for the affinity and real-state paths."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.player = self._character("resist-player")
        self.npc = self._character("resist-npc", cls=NPC)
        self.monster = create_object(Monster, key="resist-monster")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier()
        self.monster.db.skills = {"active": [], "passive": []}

    @staticmethod
    def _character(key: str, cls=PlayerCharacter):
        entity = create_object(cls, key=key)
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    def _set_affinity(self, npc: NPC, player: PlayerCharacter, value: int) -> None:
        npc.db.relations_data = {
            str(player.pk): {
                "value": value,
                "cap": 99,
                "daily_gain": 0,
                "daily_tick": 0,
            }
        }

    @covers_requirement("sexual-resist-contest::resist-verdict-is-a-pure-two-party-contest-function")
    def test_verdict_performs_no_state_mutation(self):
        self._set_affinity(self.npc, self.player, 40)

        def snapshot():
            return {
                "player_pleasure": self.player.sexual.pleasure.value,
                "npc_pleasure": self.npc.sexual.pleasure.value,
                "player_agility": self.player.skills.effective_value("agility"),
                "npc_atk_phys": self.npc.skills.effective_value("atk_phys"),
                "npc_relations": dict(self.npc.db.relations_data or {}),
                "npc_climax_turns": self.npc.sexual.climax_turns,
            }

        before = snapshot()
        for _ in range(3):
            resist_verdict(self.player, self.npc, rng=lambda: 42)
        self.assertEqual(snapshot(), before)

    @covers_requirement("sexual-resist-contest::resist-verdict-is-a-pure-two-party-contest-function")
    def test_verdict_never_materializes_sexual_state(self):
        fresh = self._character("fresh-npc", cls=NPC)
        self.assertIsNone(fresh.attributes.get("sexual_traits", category="traits"))
        for _ in range(2):
            resist_verdict(self.player, fresh, rng=lambda: 1)
        self.assertIsNone(fresh.attributes.get("sexual_traits", category="traits"))
        self.assertIsNone(
            fresh.attributes.get("climax_turns", category="sexual_state")
        )
        self.assertIsNone(fresh.attributes.get("virgin", category="sexual_state"))

    @covers_requirement("sexual-resist-contest::an-npc-resister-s-affinity-stage-can-grant-a-resist-modifier-or-auto-comply")
    def test_stranger_stage_npc_receives_positive_modifier(self):
        verdict = resist_verdict(self.player, self.npc, rng=lambda: 1)
        self.assertAlmostEqual(
            verdict.resister_score, _blended_score(self.npc) + 15
        )

    @covers_requirement("sexual-resist-contest::an-npc-resister-s-affinity-stage-can-grant-a-resist-modifier-or-auto-comply")
    def test_beloved_auto_complies_without_rolling(self):
        self._set_affinity(self.npc, self.player, 90)
        roller = MagicMock()
        verdict = resist_verdict(self.player, self.npc, rng=roller)
        self.assertFalse(verdict.resisted)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)
        roller.assert_not_called()

    @covers_requirement("sexual-resist-contest::an-npc-resister-s-affinity-stage-can-grant-a-resist-modifier-or-auto-comply")
    def test_absolute_bond_auto_complies(self):
        self._set_affinity(self.npc, self.player, 100)
        verdict = resist_verdict(self.player, self.npc, rng=lambda: 1)
        self.assertFalse(verdict.resisted)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)

    @covers_requirement("sexual-resist-contest::an-npc-resister-s-affinity-stage-can-grant-a-resist-modifier-or-auto-comply")
    def test_numeric_stage_modifiers_are_monotonic(self):
        previous = None
        for floor in (0, 10, 30, 50, 70):
            with self.subTest(floor=floor):
                self._set_affinity(self.npc, self.player, floor)
                verdict = resist_verdict(self.player, self.npc, rng=lambda: 1)
                if previous is not None:
                    self.assertLessEqual(verdict.resister_score, previous)
                previous = verdict.resister_score
        self.assertAlmostEqual(
            verdict.resister_score, _blended_score(self.npc) - 10
        )

    @covers_requirement("sexual-resist-contest::a-monster-resister-never-receives-an-affinity-term-and-never-auto-complies-from-affinity")
    def test_monster_resister_score_has_no_affinity_term(self):
        verdict = resist_verdict(self.player, self.monster, rng=lambda: 1)
        self.assertAlmostEqual(
            verdict.resister_score, _blended_score(self.monster)
        )

    @covers_requirement("sexual-resist-contest::a-monster-resister-never-receives-an-affinity-term-and-never-auto-complies-from-affinity")
    def test_monster_resister_never_auto_complies_via_affinity(self):
        self._set_affinity(self.monster, self.player, 90)
        verdict = resist_verdict(self.player, self.monster, rng=lambda: 1)
        self.assertFalse(verdict.auto_comply)
        self.assertEqual(verdict.roll, 1)

    @covers_requirement("sexual-resist-contest::a-monster-resister-never-receives-an-affinity-term-and-never-auto-complies-from-affinity")
    def test_monster_resister_never_reads_relations(self):
        spy = _SpyRelations()
        with patch.object(Monster, "relations", spy):
            term = _affinity_term(self.player, self.monster)
        self.assertEqual(term, (0.0, False))
        self.assertFalse(spy.touched)

    @covers_requirement("sexual-resist-contest::a-monster-resister-never-receives-an-affinity-term-and-never-auto-complies-from-affinity")
    def test_npc_resister_ignores_non_player_actor(self):
        actor_npc = self._character("actor-npc", cls=NPC)
        self._set_affinity(self.npc, self.player, 90)
        for actor in (actor_npc, self.monster):
            with self.subTest(actor=actor.key):
                spy = _SpyRelations()
                with patch.object(NPC, "relations", spy):
                    term = _affinity_term(actor, self.npc)
                self.assertEqual(term, (0.0, False))
                self.assertFalse(spy.touched)
                verdict = resist_verdict(actor, self.npc, rng=lambda: 1)
                self.assertFalse(verdict.auto_comply)
                self.assertAlmostEqual(
                    verdict.resister_score, _blended_score(self.npc)
                )

    @covers_requirement("sexual-resist-contest::an-npc-resister-s-affinity-stage-can-grant-a-resist-modifier-or-auto-comply")
    def test_swapping_actor_and_resister_flips_the_short_circuit(self):
        self._set_affinity(self.npc, self.player, 90)
        original = resist_verdict(self.player, self.npc, rng=lambda: 1)
        swapped = resist_verdict(self.npc, self.player, rng=lambda: 1)
        self.assertTrue(original.auto_comply)
        self.assertIsNone(original.roll)
        self.assertFalse(swapped.auto_comply)
        self.assertEqual(swapped.roll, 1)

    @covers_requirement("sexual-resist-contest::the-ordinary-contest-reuses-the-shipped-to-hit-formula-shape-with-blended-scores")
    def test_extreme_pleasure_band_resists_worse_via_existing_modifier(self):
        agility = float(self.player.skills.effective_value("agility"))
        atk_phys = float(self.player.skills.effective_value("atk_phys"))
        calm = _blended_score(self.player)
        self.player.sexual.pleasure.base = 85
        peak = _blended_score(self.player)
        self.assertLess(peak, calm)
        self.assertAlmostEqual(
            peak, 0.6 * (agility * 0.8) + 0.4 * atk_phys
        )

    @covers_requirement("sexual-resist-contest::the-ordinary-contest-reuses-the-shipped-to-hit-formula-shape-with-blended-scores")
    def test_flat_atk_phys_bonus_applies_additively(self):
        self.player.db.skills = {
            "active": [],
            "passive": ["retainer_martial_training"],
        }
        agility = float(self.player.skills.effective_value("agility"))
        atk_phys = float(self.player.skills.effective_value("atk_phys"))
        self.assertAlmostEqual(
            _blended_score(self.player),
            0.6 * agility + 0.4 * (atk_phys + 5),
        )

    @covers_requirement("sexual-resist-contest::a-resister-mid-climax-auto-complies-for-the-first-five-settlement-points-then-resists-normally")
    def test_real_climax_state_short_circuits_then_expires(self):
        self._set_affinity(self.npc, self.player, 70)
        self.npc.sexual.climax_phase.value = "進行中"
        self.npc.attributes.add("climax_turns", 1, category="sexual_state")
        roller = MagicMock()
        verdict = resist_verdict(self.player, self.npc, rng=roller)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)
        roller.assert_not_called()

        self.npc.attributes.add("climax_turns", 6, category="sexual_state")
        verdict = resist_verdict(self.player, self.npc, rng=lambda: 1)
        self.assertFalse(verdict.auto_comply)
        self.assertEqual(verdict.roll, 1)
        self.assertAlmostEqual(
            verdict.resister_score, _blended_score(self.npc) - 10
        )


class SexualResistSubmissionTests(EvenniaTestCase):
    """The submission_marks short circuit (divine-sexual-arts-mutators)."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.player = self._character("submission-player")
        self.npc = self._character("submission-npc", cls=NPC)

    @staticmethod
    def _character(key: str, cls=PlayerCharacter):
        entity = create_object(cls, key=key)
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    def _mark(self, resister: NPC, caster_id: int) -> None:
        resister.attributes.add(
            "submission_marks",
            frozenset({str(caster_id)}),
            category="sexual_state",
        )

    @covers_requirement("sexual-resist-contest::a-resister-marked-as-submissive-to-a-specific-caster-auto-complies-against-that-caster-only")
    def test_marked_caster_auto_complies_without_rolling(self):
        self._mark(self.npc, self.player.id)
        roller = MagicMock()
        verdict = resist_verdict(self.player, self.npc, rng=roller)
        self.assertFalse(verdict.resisted)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)
        roller.assert_not_called()

    @covers_requirement("sexual-resist-contest::a-resister-marked-as-submissive-to-a-specific-caster-auto-complies-against-that-caster-only")
    def test_mark_naming_a_different_caster_does_not_short_circuit(self):
        other = self._character("unrelated-submission-player")
        self._mark(self.npc, other.id)
        verdict = resist_verdict(self.player, self.npc, rng=lambda: 1)
        self.assertFalse(verdict.auto_comply)
        self.assertEqual(verdict.roll, 1)

    @covers_requirement("sexual-resist-contest::a-resister-marked-as-submissive-to-a-specific-caster-auto-complies-against-that-caster-only")
    def test_entity_sharing_the_marked_caster_key_does_not_short_circuit(self):
        # Two distinct entities with an identical .key (the wilderness monster
        # spawn shape): the stored mark names str(self.player.id), and the
        # impostor's distinct id never matches it.
        impostor = self._character("duplicate-name-player")
        impostor.key = self.player.key
        self.assertNotEqual(impostor.id, self.player.id)
        self._mark(self.npc, self.player.id)
        verdict = resist_verdict(impostor, self.npc, rng=lambda: 1)
        self.assertFalse(verdict.auto_comply)
        self.assertEqual(verdict.roll, 1)

    @covers_requirement("sexual-resist-contest::a-resister-marked-as-submissive-to-a-specific-caster-auto-complies-against-that-caster-only")
    def test_submission_read_never_materializes_sexual_state(self):
        fresh = self._character("fresh-submission-npc", cls=NPC)
        fresh.attributes.add(
            "submission_marks",
            frozenset({str(self.player.id)}),
            category="sexual_state",
        )
        self.assertIsNone(fresh.attributes.get("sexual_traits", category="traits"))
        verdict = resist_verdict(self.player, fresh, rng=MagicMock())
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)
        self.assertIsNone(fresh.attributes.get("sexual_traits", category="traits"))
        self.assertIsNone(
            fresh.attributes.get("climax_turns", category="sexual_state")
        )

    def test_mark_and_climax_terms_are_independent_short_circuits(self):
        # A marked resister mid-climax past the limit still auto-complies via
        # the mark alone — the third term does not disturb the existing two.
        self._mark(self.npc, self.player.id)
        self.npc.sexual.climax_phase.value = "進行中"
        self.npc.attributes.add("climax_turns", 6, category="sexual_state")
        verdict = resist_verdict(self.player, self.npc, rng=lambda: 1)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)


if __name__ == "__main__":
    unittest.main()
