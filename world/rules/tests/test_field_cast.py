"""Shared field-cast routing entry and read-only field-use preview.

Covers ``world.rules.field_cast``: the one deterministic routing entry both the
text ``cast`` command and the WebClient ``explore.cast`` adapter use (monster
normalization, explicit anchors, mixed-list refusal, the damage gate, ordinary
settlement), and the side-effect-free preview the ``skill_use`` panel renders
(ordinary candidates, monster openings, NONE/SELF verdicts, scale costs).
"""

from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.action import DEFAULT_CAST_SECONDS, RejectReason
from world.rules.clock import WorldClock, read_world_clock
from world.rules.combat_session import read_session
from world.rules.field_cast import (
    cast_in_field,
    field_candidate_entities,
    owned_active_skill,
    preview_field_skill,
)
from world.rules.skip_safety import _BATTLEFIELDS
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS

from ._combat_session_helpers import (
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import BattlefieldIsolation, grant_lineage

_T_DAMAGE = SYNTH_SKILLS["t_ember_burst"].key
_T_HEAL = SYNTH_SKILLS["t_hush_mend"].key
_T_SELF = SYNTH_SKILLS["t_moss_veil"].key
_T_NONE = SYNTH_SKILLS["t_cinder_breath"].key
_T_AREA_DAMAGE = SYNTH_SEAM_AREA_SKILL.key
# A synthetic non-damaging AREA skill: the ordinary multi-target shape.
_T_AREA_HEAL = replace(
    SYNTH_SKILLS["t_hush_mend"],
    key="t_hush_chorus",
    label="靜謐合唱",
    description="以溫潤的合唱同時撫平身邊每一道傷口。",
    target_spec=TargetSpec.AREA,
    effects=["heal:area"],
)


def _open_scope(case):
    open_synthetic_scope(
        case,
        "skills",
        "buffs",
        "elements",
        "sexual_acts",
        "races",
        "subraces",
        "static_tiers",
        extra={
            "skills": {
                **synth_innate_overlay()["skills"],
                SYNTH_SEAM_AREA_SKILL.key: SYNTH_SEAM_AREA_SKILL,
                _T_AREA_HEAL.key: _T_AREA_HEAL,
            }
        },
    )


class _FieldCase(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="field cast meadow")
        self.player = _player("field caster")
        self.player.location = self.room
        self.player.traits.mp.current = self.player.traits.mp.max

    def tearDown(self):
        from world.rules.combat_session import clear_session

        clear_session(self.player)
        super().tearDown()

    def _npc(self, key):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        return npc

    def _wolf(self, key):
        wolf = _monster(key, hp=2000, atk=1)
        wolf.location = self.room
        return wolf


class CastInFieldRoutingTests(_FieldCase):
    def test_both_target_forms_together_are_a_shape_mismatch(self):
        wolf = self._wolf("both wolf")
        grant_lineage(self.player, [_T_HEAL])
        with patch("world.rules.field_cast.initiate_field_combat") as initiate:
            outcome = cast_in_field(
                self.player, _T_HEAL, targets=[self.player], opening_target=wolf
            )
        self.assertEqual(outcome.route, "rejected")
        self.assertEqual(outcome.reason, RejectReason.TARGET_SPEC_MISMATCH)
        initiate.assert_not_called()

    def test_single_monster_list_normalizes_to_the_opening_route(self):
        wolf = self._wolf("normalized wolf")
        grant_lineage(self.player, [_T_HEAL])
        with patch(
            "world.rules.field_cast.initiate_field_combat",
            return_value={"outcome": "round"},
        ) as initiate:
            outcome = cast_in_field(self.player, _T_HEAL, targets=[wolf])
        self.assertEqual(outcome.route, "initiation")
        initiate.assert_called_once_with(self.player, _T_HEAL, wolf, scale=1.0)

    def test_mixed_list_with_a_living_monster_never_settles(self):
        wolf = self._wolf("mixed wolf")
        npc = self._npc("mixed npc")
        grant_lineage(self.player, [_T_AREA_HEAL.key])
        with patch("world.rules.cast_settlement.settle_out_of_combat_cast") as settle, patch(
            "world.rules.field_cast.initiate_field_combat"
        ) as initiate:
            outcome = cast_in_field(
                self.player, _T_AREA_HEAL.key, targets=[npc, wolf]
            )
        self.assertEqual(outcome.route, "rejected")
        self.assertEqual(outcome.reason, RejectReason.TARGET_SPEC_MISMATCH)
        settle.assert_not_called()
        initiate.assert_not_called()

    def test_ordinary_multi_list_settles_even_with_a_monster_in_the_room(self):
        self._wolf("bystander wolf")
        npc = self._npc("chorus npc")
        grant_lineage(self.player, [_T_AREA_HEAL.key])
        with patch("world.rules.cast_settlement.settle_out_of_combat_cast") as settle:
            outcome = cast_in_field(
                self.player, _T_AREA_HEAL.key, targets=[self.player, npc]
            )
        self.assertEqual(outcome.route, "settlement")
        request = settle.call_args.args[0]
        self.assertEqual(request.targets, [self.player, npc])

    @covers_requirement("webclient-skillbook-casting::field-submissions-revalidate-and-preserve-deterministic-routing")
    def test_damage_aimed_elsewhere_is_refused_before_settlement_or_clock(self):
        npc = self._npc("damage npc")
        grant_lineage(self.player, [_T_DAMAGE])
        mp_before = self.player.traits.mp.value
        clock_before = read_world_clock()
        for label, targets in (("npc", [npc]), ("self", [self.player]), ("none", [])):
            with self.subTest(target=label), patch(
                "world.rules.cast_settlement.settle_out_of_combat_cast"
            ) as settle:
                outcome = cast_in_field(self.player, _T_DAMAGE, targets=targets)
                self.assertEqual(outcome.route, "rejected")
                self.assertEqual(
                    outcome.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET
                )
                settle.assert_not_called()
        self.assertEqual(self.player.traits.mp.value, mp_before)
        self.assertEqual(read_world_clock() is None, clock_before is None)
        self.assertIsNone(read_session(self.player))

    @covers_requirement("webclient-skillbook-casting::cast-settlement-is-atomic-and-publishes-the-complete-committed-view")
    def test_utility_cast_settles_once_with_command_time(self):
        npc = self._npc("healed npc")
        npc.traits.hp.current = 1
        grant_lineage(self.player, [_T_HEAL])
        mp_before = self.player.traits.mp.value
        clock = WorldClock()
        with patch(
            "world.rules.cast_settlement.read_world_clock", return_value=clock
        ), patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            outcome = cast_in_field(self.player, _T_HEAL, targets=[npc])
        self.assertEqual(outcome.route, "settlement")
        self.assertEqual(outcome.settlement.result.outcome, "success")
        self.assertEqual(clock.tick, DEFAULT_CAST_SECONDS)
        self.assertLess(self.player.traits.mp.value, mp_before)
        self.assertGreater(int(npc.traits.hp.current), 1)
        self.assertIsNone(read_session(self.player))

    @covers_requirement("webclient-skillbook-casting::field-submissions-revalidate-and-preserve-deterministic-routing")
    def test_explicit_anchor_opens_combat(self):
        wolf = self._wolf("anchored wolf")
        grant_lineage(self.player, [_T_DAMAGE])
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch(
            "world.rules.combat.damage.roll_d100", return_value=50
        ), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            outcome = cast_in_field(self.player, _T_DAMAGE, opening_target=wolf)
        self.assertEqual(outcome.route, "initiation")
        self.assertIn(outcome.combat_result["outcome"], ("round", "victory"))


class PreviewFieldSkillTests(_FieldCase):
    def test_none_skill_has_a_verdict_and_no_targets(self):
        grant_lineage(self.player, [_T_NONE])
        preview = preview_field_skill(self.player, owned_active_skill(self.player, _T_NONE))
        self.assertTrue(preview.verdict.enabled)
        self.assertEqual(preview.targets, ())
        self.assertEqual(preview.openings, ())

    def test_self_skill_binds_only_the_actor(self):
        self._npc("self bystander")
        grant_lineage(self.player, [_T_SELF])
        preview = preview_field_skill(self.player, owned_active_skill(self.player, _T_SELF))
        self.assertTrue(preview.verdict.enabled)
        self.assertEqual([choice.entity for choice in preview.targets], [self.player])

    @covers_requirement("webclient-skillbook-casting::field-previews-share-existing-deterministic-target-and-scale-rules")
    def test_single_heal_lists_ordinary_candidates_and_a_separate_opening(self):
        npc = self._npc("heal npc")
        wolf = self._wolf("heal wolf")
        grant_lineage(self.player, [_T_HEAL])
        preview = preview_field_skill(self.player, owned_active_skill(self.player, _T_HEAL))
        self.assertEqual(
            [choice.entity for choice in preview.targets], [self.player, npc]
        )
        self.assertTrue(all(choice.enabled for choice in preview.targets))
        self.assertEqual([choice.entity for choice in preview.openings], [wolf])
        self.assertTrue(preview.openings[0].enabled)
        self.assertEqual(preview.openings[0].line_up, (wolf,))
        self.assertIsNone(read_session(self.player))

    @covers_requirement("webclient-skillbook-casting::field-previews-share-existing-deterministic-target-and-scale-rules")
    def test_damage_skill_disables_ordinary_rows_but_enables_the_opening(self):
        self._npc("damage bystander")
        wolf = self._wolf("damage wolf")
        grant_lineage(self.player, [_T_DAMAGE])
        with patch.dict(_BATTLEFIELDS, {}, clear=True):
            preview = preview_field_skill(
                self.player, owned_active_skill(self.player, _T_DAMAGE)
            )
            self.assertEqual(_BATTLEFIELDS, {})
        self.assertTrue(preview.targets)
        for choice in preview.targets:
            self.assertFalse(choice.enabled)
            self.assertEqual(choice.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)
        self.assertEqual([choice.entity for choice in preview.openings], [wolf])
        self.assertTrue(preview.openings[0].enabled)
        self.assertIsNone(read_session(self.player))

    def test_area_opening_discloses_the_whole_living_line_up(self):
        wolves = [self._wolf(f"pack wolf {index}") for index in range(2)]
        dead = self._wolf("pack carcass")
        dead.traits.hp.current = 0
        grant_lineage(self.player, [_T_AREA_DAMAGE])
        preview = preview_field_skill(
            self.player, owned_active_skill(self.player, _T_AREA_DAMAGE)
        )
        expected = tuple(sorted(wolves, key=lambda wolf: int(wolf.pk)))
        self.assertEqual([choice.entity for choice in preview.openings], list(expected))
        for opening in preview.openings:
            self.assertEqual(opening.line_up, expected)

    def test_duplicate_named_line_up_disables_without_raising(self):
        self._wolf("twin wolf")
        self._wolf("twin wolf")
        grant_lineage(self.player, [_T_AREA_DAMAGE])
        preview = preview_field_skill(
            self.player, owned_active_skill(self.player, _T_AREA_DAMAGE)
        )
        self.assertEqual(len(preview.openings), 2)
        for opening in preview.openings:
            self.assertFalse(opening.enabled)
            self.assertEqual(opening.session_reason, "duplicate_participant")
            self.assertEqual(len(opening.line_up), 2)

    def test_preview_never_creates_the_world_clock(self):
        self._wolf("clockless wolf")
        grant_lineage(self.player, [_T_DAMAGE])
        before = read_world_clock()
        preview_field_skill(self.player, owned_active_skill(self.player, _T_DAMAGE))
        after = read_world_clock()
        self.assertEqual(after is None, before is None)
        if before is not None:
            self.assertEqual(after.tick, before.tick)

    def test_unaffordable_skill_reports_the_resource_and_adjusted_cost(self):
        grant_lineage(self.player, [_T_NONE])
        self.player.traits.mp.current = 0
        preview = preview_field_skill(self.player, owned_active_skill(self.player, _T_NONE))
        self.assertFalse(preview.verdict.enabled)
        self.assertEqual(preview.verdict.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(preview.cost, {"mp": SYNTH_SKILLS[_T_NONE].cost["mp"]})
        self.assertEqual(self.player.traits.mp.current, 0)

    def test_candidates_exclude_monsters_and_order_by_identity(self):
        npc_b = self._npc("candidate b")
        npc_a = self._npc("candidate a")
        self._wolf("candidate wolf")
        entities = field_candidate_entities(self.player)
        self.assertEqual(entities[0], self.player)
        self.assertEqual(entities[1:], sorted([npc_a, npc_b], key=lambda obj: int(obj.pk)))

    def test_unowned_or_passive_keys_are_not_previewable(self):
        self.assertIsNone(owned_active_skill(self.player, _T_HEAL))
        self.assertIsNone(owned_active_skill(self.player, "t_definitely_missing"))
