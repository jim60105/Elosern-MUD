"""Behavior tests for the positional-marker primitive and reachability gate."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules import combat
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    has_positional_marker,
    load_buff_definitions,
    remove_ground_markers,
    remove_positional_markers,
    tick_buffs,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_session import (
    _basic_attack_request,
    engage,
    is_in_active_session,
    read_session,
    submit_player_action,
)
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.party import join_party
from world.rules.spell_conditions import is_strike_class
from world.rules.tests._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import grant_lineage
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill

_T_CAST = SYNTH_SKILLS["t_ember_burst"].key

_SYNTH_POSITIONAL_MARKER = BuffDefinition(
    key="t_displaced_hazard",
    duration=30,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
    polarity="debuff",
    marker="positional",
)

_SYNTH_GROUND_MARKER = BuffDefinition(
    key="t_ground_hazard",
    duration=30,
    tick_interval=10,
    stacking="refresh",
    modifiers={"rate": {"target": "hp", "delta": -10}},
    polarity="debuff",
    marker="ground",
)

_SYNTH_CONTROL_BUFF = BuffDefinition(
    key="t_control_buff",
    duration=30,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
    polarity="buff",
    marker=None,
)

_SYNTH_STRIKE_SKILL = make_skill(
    "t_synth_strike",
    label="測試打擊",
    target_spec=TargetSpec.SINGLE,
    effects=["damage:fire:physical"],
)

_SYNTH_MAGIC_SINGLE_SKILL = make_skill(
    "t_synth_magic_single",
    label="測試法術",
    target_spec=TargetSpec.SINGLE,
    effects=["damage:fire:magic"],
)

_SYNTH_AREA_SKILL = make_skill(
    "t_synth_area",
    label="測試範圍",
    target_spec=TargetSpec.AREA,
    effects=["damage:fire:physical"],
)


def _write_yaml(content: str) -> Path:
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    handle.write(content)
    handle.close()
    return Path(handle.name)


def _companion(player, key, hp=100, agility=10):
    npc = create_object(NPC, key=key, location=player.location)
    npc.race = _race_key()
    npc.apply_race_baseline()
    npc.traits.hp.base = hp
    npc.traits.hp.current = hp
    npc.traits.agility.base = agility
    join_party(npc, player)
    return npc


class PositionalMarkerDefinitionTests(unittest.TestCase):
    """Load-time validation for marker: positional buff definition clause."""

    @covers_requirement(
        "positional-marker::a-positional-marker-buff-row-makes-holding-it-the-canonical-out-of-position-fact"
    )
    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_marker_positional_loads_carrying_clause(self):
        path = _write_yaml("- key: displaced\n  marker: positional\n")
        definitions = load_buff_definitions(path)
        self.assertEqual(definitions["displaced"].marker, "positional")

    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_marker_ground_still_loads_carrying_clause(self):
        path = _write_yaml("- key: fissure\n  marker: ground\n")
        definitions = load_buff_definitions(path)
        self.assertEqual(definitions["fissure"].marker, "ground")

    @covers_requirement(
        "positional-marker::a-positional-marker-buff-row-makes-holding-it-the-canonical-out-of-position-fact"
    )
    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_malformed_marker_clause_fails_closed(self):
        for bad_value in ("knockback", "fire", "true", "false", "3", "null", "['positional']"):
            with self.subTest(bad_value=bad_value):
                path = _write_yaml(f"- key: bad_marker_row\n  marker: {bad_value}\n")
                with self.assertRaises(ValueError) as ctx:
                    load_buff_definitions(path)
                self.assertIn("bad_marker_row", str(ctx.exception))
                self.assertIn("invalid marker", str(ctx.exception))


class PositionalMarkerReachabilityTests(BattlefieldIsolation, EvenniaTestCase):
    """Behavior tests for the bidirectional single-target physical strike gate and self-return."""

    def setUp(self):
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            "races",
            "subraces",
            "static_tiers",
            "monster_tiers",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.buff_patch = patch.dict(
            BUFF_DEFINITIONS,
            {
                _SYNTH_POSITIONAL_MARKER.key: _SYNTH_POSITIONAL_MARKER,
                _SYNTH_GROUND_MARKER.key: _SYNTH_GROUND_MARKER,
                _SYNTH_CONTROL_BUFF.key: _SYNTH_CONTROL_BUFF,
            },
        )
        self.buff_patch.start()
        self.addCleanup(self.buff_patch.stop)

        from world.skills.registry import SKILL_REGISTRY

        self.skill_patch = patch.dict(
            SKILL_REGISTRY,
            {
                _SYNTH_STRIKE_SKILL.key: _SYNTH_STRIKE_SKILL,
                _SYNTH_MAGIC_SINGLE_SKILL.key: _SYNTH_MAGIC_SINGLE_SKILL,
                _SYNTH_AREA_SKILL.key: _SYNTH_AREA_SKILL,
            },
        )
        self.skill_patch.start()
        self.addCleanup(self.skill_patch.stop)

        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(
            self.player,
            [
                _T_CAST,
                _SYNTH_STRIKE_SKILL.key,
                _SYNTH_MAGIC_SINGLE_SKILL.key,
                _SYNTH_AREA_SKILL.key,
            ],
        )
        self.monster = _monster("goblin", hp=200)
        self.monster.location = self.room
        grant_lineage(
            self.monster,
            [
                _SYNTH_STRIKE_SKILL.key,
                _SYNTH_MAGIC_SINGLE_SKILL.key,
                _SYNTH_AREA_SKILL.key,
            ],
        )

    def tearDown(self):
        super().tearDown()
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)

    def test_is_strike_class_helper(self):
        """Classification helper identifies SINGLE physical damage skills and ignores malformed/magic effects."""
        self.assertTrue(is_strike_class(_SYNTH_STRIKE_SKILL))
        self.assertFalse(is_strike_class(_SYNTH_MAGIC_SINGLE_SKILL))
        self.assertFalse(is_strike_class(_SYNTH_AREA_SKILL))

        # Hybrid physical + magic is NOT a strike
        hybrid = make_skill(
            "t_hybrid",
            target_spec=TargetSpec.SINGLE,
            effects=["damage:fire:physical", "damage:wind:magic"],
        )
        self.assertFalse(is_strike_class(hybrid))

        # Malformed damage string does not raise and is not a strike
        from types import SimpleNamespace
        malformed = SimpleNamespace(target_spec=TargetSpec.SINGLE, effects=["damage:unknown_element"])
        self.assertFalse(is_strike_class(malformed))

    @covers_requirement(
        "positional-marker::a-displaced-holder-is-unreachable-to-single-target-physical-strikes-in-both-directions"
    )
    def test_displaced_target_cannot_be_selected_for_strike_but_magic_and_area_hit(self):
        """An attacker selecting a displaced target is rejected for strike-class but magic/area resolve normally."""
        apply_buff(self.monster, "t_displaced_hazard")
        self.assertTrue(has_positional_marker(self.monster))

        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={str(self.player.key): self.player, str(self.monster.key): self.monster},
        )
        ctx = BattlefieldActionContext(bf)

        # 1. Strike rejects at preflight and resolution with CAST_CONDITION_UNMET
        req_strike = ActionRequest(self.player, _SYNTH_STRIKE_SKILL.key, [self.monster], ctx)
        pre_res = ActionResolver.preflight(req_strike)
        self.assertEqual(pre_res.outcome, "rejected")
        self.assertEqual(pre_res.reason, RejectReason.CAST_CONDITION_UNMET)
        self.assertIn("displaced", str(pre_res.detail))

        res_strike = ActionResolver.resolve(req_strike)
        self.assertEqual(res_strike.outcome, "rejected")
        self.assertEqual(res_strike.reason, RejectReason.CAST_CONDITION_UNMET)

        # 2. Magic single-target resolves normally
        with patch("world.rules.combat.roll_d100", return_value=100):
            hp_before = self.monster.traits.hp.current
            req_magic = ActionRequest(self.player, _SYNTH_MAGIC_SINGLE_SKILL.key, [self.monster], ctx)
            res_magic = ActionResolver.resolve(req_magic)
        self.assertEqual(res_magic.outcome, "success")
        self.assertLess(self.monster.traits.hp.current, hp_before)

        # 3. Area spell resolves normally
        with patch("world.rules.combat.roll_d100", return_value=100):
            hp_before_area = self.monster.traits.hp.current
            req_area = ActionRequest(self.player, _SYNTH_AREA_SKILL.key, "all-enemies", ctx)
            res_area = ActionResolver.resolve(req_area)
        self.assertEqual(res_area.outcome, "success")
        self.assertLess(self.monster.traits.hp.current, hp_before_area)

    @covers_requirement(
        "positional-marker::the-holder-s-own-single-target-strike-is-the-self-return-act"
    )
    def test_displaced_holder_own_strike_is_self_return_act(self):
        """Displaced actor's strike against reachable target clears marker before strike resolves."""
        apply_buff(self.player, "t_displaced_hazard")
        self.assertTrue(has_positional_marker(self.player))

        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={str(self.player.key): self.player, str(self.monster.key): self.monster},
        )
        ctx = BattlefieldActionContext(bf)

        req_strike = ActionRequest(self.player, _SYNTH_STRIKE_SKILL.key, [self.monster], ctx)

        # Preflight passes because self-return is allowed
        pre_res = ActionResolver.preflight(req_strike)
        self.assertEqual(pre_res.outcome, "success")
        self.assertTrue(has_positional_marker(self.player))

        # Resolution clears the marker and lands the strike
        hp_before = self.monster.traits.hp.current
        with patch("world.rules.combat.roll_d100", return_value=100):
            res = ActionResolver.resolve(req_strike)
        self.assertEqual(res.outcome, "success")
        self.assertLess(self.monster.traits.hp.current, hp_before)
        self.assertFalse(has_positional_marker(self.player))

        # Subsequent strike resolves ordinarily (no longer displaced)
        with patch("world.rules.combat.roll_d100", return_value=100):
            res_second = ActionResolver.resolve(req_strike)
        self.assertEqual(res_second.outcome, "success")

    def test_displaced_holder_magic_and_area_never_climb_back(self):
        """Casting magic single, casting area, or passing rounds does not clear the displaced marker."""
        apply_buff(self.player, "t_displaced_hazard")
        self.assertTrue(has_positional_marker(self.player))

        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={str(self.player.key): self.player, str(self.monster.key): self.monster},
        )
        ctx = BattlefieldActionContext(bf)

        # Magic cast
        req_magic = ActionRequest(self.player, _SYNTH_MAGIC_SINGLE_SKILL.key, [self.monster], ctx)
        with patch("world.rules.combat.roll_d100", return_value=100):
            res_magic = ActionResolver.resolve(req_magic)
        self.assertEqual(res_magic.outcome, "success")
        self.assertTrue(has_positional_marker(self.player))

        # Area cast
        req_area = ActionRequest(self.player, _SYNTH_AREA_SKILL.key, "all-enemies", ctx)
        with patch("world.rules.combat.roll_d100", return_value=100):
            res_area = ActionResolver.resolve(req_area)
        self.assertEqual(res_area.outcome, "success")
        self.assertTrue(has_positional_marker(self.player))

    def test_displaced_holder_keeps_sovereign_agency_and_blocks_action_is_false(self):
        """Displaced marker is not stillness or turn denial: blocks_action is false, turn passage retains marker."""
        from world.rules.buffs import blocks_action

        apply_buff(self.player, "t_displaced_hazard")
        self.assertTrue(has_positional_marker(self.player))
        # Sovereignty: displaced marker NEVER denies action or freezes turn
        self.assertFalse(blocks_action(self.player))

    def test_self_return_clears_only_actor_marker_not_third_party(self):
        """Self-returning strike clears only the actor's own positional instances, never a third party's."""
        bystander = _companion(self.player, "bystander", hp=100)
        apply_buff(self.player, "t_displaced_hazard")
        apply_buff(bystander, "t_displaced_hazard")
        self.assertTrue(has_positional_marker(self.player))
        self.assertTrue(has_positional_marker(bystander))

        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key), str(bystander.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={
                str(self.player.key): self.player,
                str(bystander.key): bystander,
                str(self.monster.key): self.monster,
            },
        )
        ctx = BattlefieldActionContext(bf)
        req = ActionRequest(self.player, _SYNTH_STRIKE_SKILL.key, [self.monster], ctx)
        with patch("world.rules.combat.roll_d100", return_value=100):
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertFalse(has_positional_marker(self.player))
        self.assertTrue(has_positional_marker(bystander))

    @covers_requirement(
        "positional-marker::a-displaced-holder-is-unreachable-to-single-target-physical-strikes-in-both-directions"
    )
    def test_two_displaced_holders_cannot_strike_each_other_and_neither_consumed(self):
        """Two displaced entities striking each other reject at target-side gate first, consuming neither marker."""
        apply_buff(self.player, "t_displaced_hazard")
        apply_buff(self.monster, "t_displaced_hazard")
        self.assertTrue(has_positional_marker(self.player))
        self.assertTrue(has_positional_marker(self.monster))

        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={str(self.player.key): self.player, str(self.monster.key): self.monster},
        )
        ctx = BattlefieldActionContext(bf)

        req = ActionRequest(self.player, _SYNTH_STRIKE_SKILL.key, [self.monster], ctx)
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "rejected")
        self.assertEqual(res.reason, RejectReason.CAST_CONDITION_UNMET)

        # Both markers remain live!
        self.assertTrue(has_positional_marker(self.player))
        self.assertTrue(has_positional_marker(self.monster))

    @covers_requirement(
        "positional-marker::the-holder-s-own-single-target-strike-is-the-self-return-act"
    )
    def test_failed_settlement_restores_positional_marker_from_snapshot(self):
        """If a self-returning strike fails commit, the pre-commit snapshot restores the positional marker."""
        apply_buff(self.player, "t_displaced_hazard")
        self.assertTrue(has_positional_marker(self.player))

        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={str(self.player.key): self.player, str(self.monster.key): self.monster},
        )
        ctx = BattlefieldActionContext(bf)
        req = ActionRequest(self.player, _SYNTH_STRIKE_SKILL.key, [self.monster], ctx)

        # Force a commit failure during damage effect application
        with (
            patch("world.rules.combat._apply_hp_delta", side_effect=RuntimeError("simulated commit failure")),
            patch("world.rules.combat.roll_d100", return_value=100),
        ):
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "rejected")
        self.assertEqual(res.reason, RejectReason.COMMIT_FAILED)

        # Positional marker was restored from the snapshot!
        self.assertTrue(has_positional_marker(self.player))


class PositionalMarkerLifecycleAndSynergyTests(BattlefieldIsolation, EvenniaTestCase):
    """Behavior tests for ground sweep on mount, refusal conditions, and exit sweeps."""

    def setUp(self):
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            "races",
            "subraces",
            "static_tiers",
            "monster_tiers",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.buff_patch = patch.dict(
            BUFF_DEFINITIONS,
            {
                _SYNTH_POSITIONAL_MARKER.key: _SYNTH_POSITIONAL_MARKER,
                _SYNTH_GROUND_MARKER.key: _SYNTH_GROUND_MARKER,
                _SYNTH_CONTROL_BUFF.key: _SYNTH_CONTROL_BUFF,
            },
        )
        self.buff_patch.start()
        self.addCleanup(self.buff_patch.stop)

        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        self.monster = _monster("goblin", hp=100)
        self.monster.location = self.room

    def tearDown(self):
        super().tearDown()
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)

    def test_buff_cache_never_stores_battlefield_context_on_any_buff(self):
        """Unconditional pop in apply_buff ensures neither positional nor control buffs store battlefield in cache."""
        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={str(self.player.key): self.player, str(self.monster.key): self.monster},
        )
        apply_buff(self.monster, "t_control_buff", battlefield=bf, event_context={"battlefield": bf})
        cache = self.monster.buffs.all["t_control_buff"].cache
        self.assertNotIn("battlefield", cache)
        self.assertNotIn("event_context", cache)

    def test_refuse_positional_mount_on_fled_player_via_session_record(self):
        """Player with a durable session record listing them fled refuses positional mount without writes."""
        from world.rules.combat_session import CombatSessionRecord, _persist

        engage(self.player, self.monster)
        rec = read_session(self.player)
        # Mark player as fled in the session record
        fled_rec = CombatSessionRecord(
            session_id=rec.session_id,
            mode=rec.mode,
            room_id=rec.room_id,
            player_ids=rec.player_ids,
            enemy_ids=rec.enemy_ids,
            fled_ids=(int(self.player.pk),),
            knocked_out_ids=(),
            rounds_elapsed=rec.rounds_elapsed,
            exam_id=rec.exam_id,
        )
        _persist(self.player, fled_rec)

        # Direct apply_buff without battlefield context falls back to read_session and refuses
        apply_buff(self.player, "t_displaced_hazard")
        self.assertNotIn("t_displaced_hazard", entity_active_buffs(self.player))

    @covers_requirement(
        "positional-marker::mounting-a-positional-marker-sweeps-the-holder-s-ground-markers-and-refuses-impossible-mounts"
    )
    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_mounting_positional_marker_sweeps_ground_markers_first(self):
        """Applying a positional marker removes live ground markers, logs combat_marker_swept, keeps controls."""
        apply_buff(self.monster, "t_ground_hazard")
        apply_buff(self.monster, "t_control_buff")
        self.assertIn("t_ground_hazard", entity_active_buffs(self.monster))
        self.assertIn("t_control_buff", entity_active_buffs(self.monster))

        events = []
        with self.captureOnCommitCallbacks(execute=True):
            with patch("world.observability.log_info", side_effect=lambda name, context=None: events.append((name, context))):
                apply_buff(self.monster, "t_displaced_hazard")

        self.assertNotIn("t_ground_hazard", entity_active_buffs(self.monster))
        self.assertIn("t_control_buff", entity_active_buffs(self.monster))
        self.assertIn("t_displaced_hazard", entity_active_buffs(self.monster))

        swept_events = [e for e in events if e[0] == "combat_marker_swept"]
        self.assertEqual(len(swept_events), 1)
        self.assertEqual(swept_events[0][1]["count"], 1)
        self.assertEqual(swept_events[0][1]["reason"], "displaced_mount")

    @covers_requirement(
        "positional-marker::mounting-a-positional-marker-sweeps-the-holder-s-ground-markers-and-refuses-impossible-mounts"
    )
    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_impossible_mounts_refuse_without_writes(self):
        """Positional mount refuses defeated, fled, or knocked out entities across actor and enemy shapes."""
        # 1. Defeated entity (hp <= 0)
        dead_monster = _monster("dead_goblin", hp=0)
        dead_monster.location = self.room
        apply_buff(dead_monster, "t_displaced_hazard")
        self.assertNotIn("t_displaced_hazard", entity_active_buffs(dead_monster))

        # 2. Fled and Knocked-out in battlefield context
        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster.key)})},
            roster={str(self.player.key): self.player, str(self.monster.key): self.monster},
        )
        bf.fled.add(str(self.monster.key))

        apply_buff(self.monster, "t_displaced_hazard", battlefield=bf)
        self.assertNotIn("t_displaced_hazard", entity_active_buffs(self.monster))

        bf.fled.clear()
        bf.knocked_out.add(str(self.monster.key))
        apply_buff(self.monster, "t_displaced_hazard", battlefield=bf)
        self.assertNotIn("t_displaced_hazard", entity_active_buffs(self.monster))

        # 3. Living, active entity mounts cleanly
        bf.knocked_out.clear()
        apply_buff(self.monster, "t_displaced_hazard", battlefield=bf)
        self.assertIn("t_displaced_hazard", entity_active_buffs(self.monster))

    def test_trait_less_and_pk_less_recipient_mounts_cleanly(self):
        """An entity without traits or pk mounts positional row rather than raising AttributeError."""
        from types import SimpleNamespace
        dummy = SimpleNamespace(db=SimpleNamespace(equipment=None), buffs=SimpleNamespace(all={}))
        dummy.buffs.add = lambda *a, **k: None
        # Does not raise
        apply_buff(dummy, "t_displaced_hazard")

    @covers_requirement(
        "positional-marker::a-positional-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_exit_sweeps_extinguish_both_marker_classes(self):
        """Flee, knockout, and session end sweep both ground and positional markers, leaving control buffs."""
        comp_pos = _companion(self.player, "fighter_pos", hp=50)
        comp_ground = _companion(self.player, "fighter_ground", hp=50)
        engage(self.player, self.monster)

        # comp_pos holds positional + control buff
        apply_buff(comp_pos, "t_displaced_hazard")
        apply_buff(comp_pos, "t_control_buff")
        self.assertIn("t_displaced_hazard", entity_active_buffs(comp_pos))
        self.assertIn("t_control_buff", entity_active_buffs(comp_pos))

        # comp_ground holds ground + control buff
        apply_buff(comp_ground, "t_ground_hazard")
        apply_buff(comp_ground, "t_control_buff")
        self.assertIn("t_ground_hazard", entity_active_buffs(comp_ground))
        self.assertIn("t_control_buff", entity_active_buffs(comp_ground))

        # Knockout transition knocking out both companions
        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch(
                "world.rules.combat_session._knocked_out_ids",
                return_value=(int(comp_pos.pk), int(comp_ground.pk)),
            ),
        ):
            submit_player_action(self.player, _T_CAST, [self.monster])

        # Both markers extinguished, control buffs persist
        self.assertNotIn("t_displaced_hazard", entity_active_buffs(comp_pos))
        self.assertIn("t_control_buff", entity_active_buffs(comp_pos))
        self.assertNotIn("t_ground_hazard", entity_active_buffs(comp_ground))
        self.assertIn("t_control_buff", entity_active_buffs(comp_ground))

    @covers_requirement(
        "positional-marker::a-positional-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_session_end_sweeps_both_markers(self):
        """Session end sweeps both ground and positional markers."""
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)

        apply_buff(self.player, "t_ground_hazard")
        apply_buff(self.player, "t_displaced_hazard")
        apply_buff(self.player, "t_control_buff")

        # Win fight
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertFalse(is_in_active_session(self.player))

        self.assertNotIn("t_ground_hazard", entity_active_buffs(self.player))
        self.assertNotIn("t_displaced_hazard", entity_active_buffs(self.player))
        self.assertIn("t_control_buff", entity_active_buffs(self.player))


class DeterministicAttackerExclusionTests(BattlefieldIsolation, EvenniaTestCase):
    """Behavior tests for deterministic pickers skipping displaced enemies."""

    def setUp(self):
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            "races",
            "subraces",
            "static_tiers",
            "monster_tiers",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.buff_patch = patch.dict(
            BUFF_DEFINITIONS,
            {_SYNTH_POSITIONAL_MARKER.key: _SYNTH_POSITIONAL_MARKER},
        )
        self.buff_patch.start()
        self.addCleanup(self.buff_patch.stop)

        from world.skills.registry import SKILL_REGISTRY

        self.skill_patch = patch.dict(
            SKILL_REGISTRY,
            {
                _SYNTH_STRIKE_SKILL.key: _SYNTH_STRIKE_SKILL,
                _SYNTH_MAGIC_SINGLE_SKILL.key: _SYNTH_MAGIC_SINGLE_SKILL,
                _SYNTH_AREA_SKILL.key: _SYNTH_AREA_SKILL,
            },
        )
        self.skill_patch.start()
        self.addCleanup(self.skill_patch.stop)

        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        self.monster_a = _monster("orc_a", hp=100)
        self.monster_a.location = self.room
        self.monster_b = _monster("orc_b", hp=100)
        self.monster_b.location = self.room

    def tearDown(self):
        super().tearDown()
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)

    @covers_requirement(
        "positional-marker::deterministic-single-target-attackers-skip-displaced-candidates"
    )
    def test_basic_attack_request_skips_displaced_enemy(self):
        """_basic_attack_request excludes displaced enemies; returns None if all enemies are displaced."""
        bf = Battlefield(
            teams={"players": frozenset({str(self.player.key)}), "enemies": frozenset({str(self.monster_a.key), str(self.monster_b.key)})},
            roster={
                str(self.player.key): self.player,
                str(self.monster_a.key): self.monster_a,
                str(self.monster_b.key): self.monster_b,
            },
        )
        engage(self.player, self.monster_a)
        record = read_session(self.player)

        # Displace monster A: basic attack targets reachable monster B
        apply_buff(self.monster_a, "t_displaced_hazard")
        req = _basic_attack_request(self.player, bf, record)
        self.assertIsNotNone(req)
        self.assertEqual(req.targets, [self.monster_b])

        # Displace monster B too: no candidates survive, returns None
        apply_buff(self.monster_b, "t_displaced_hazard")
        req_none = _basic_attack_request(self.player, bf, record)
        self.assertIsNone(req_none)

    @covers_requirement(
        "positional-marker::deterministic-single-target-attackers-skip-displaced-candidates"
    )
    @covers_requirement(
        "monster-action-policy::target-selection-differs-by-archetype-and-is-deterministic-under-a-fixed-seed"
    )
    def test_monster_policy_strike_vs_magic_displaced_candidate_handling(self):
        """Strike-only monster skips displaced candidates, while magic-owning monster keeps them reachable."""
        # Monster with strike-only kit
        strike_monster = _monster("striker", hp=100)
        strike_monster.location = self.room
        grant_lineage(strike_monster, [_SYNTH_STRIKE_SKILL.key])

        # Player is displaced, companion is reachable
        companion = _companion(self.player, "buddy", hp=100)
        apply_buff(self.player, "t_displaced_hazard")

        bf = Battlefield(
            teams={"monsters": frozenset({str(strike_monster.key)}), "party": frozenset({str(self.player.key), str(companion.key)})},
            roster={
                str(strike_monster.key): strike_monster,
                str(self.player.key): self.player,
                str(companion.key): companion,
            },
        )

        # 1. Strike-only monster picks the undisplaced companion
        req = monster_behaviour_policy(strike_monster, bf)
        self.assertIsNotNone(req)
        self.assertEqual(req.targets, [companion])

        # 2. If both enemies are displaced, strike-only monster yields None
        apply_buff(companion, "t_displaced_hazard")
        req_all_displaced = monster_behaviour_policy(strike_monster, bf)
        self.assertIsNone(req_all_displaced)

        # 3. Caster monster with magic-single kit keeps displaced target reachable
        caster_monster = _monster("caster", hp=100)
        caster_monster.location = self.room
        grant_lineage(caster_monster, [_SYNTH_MAGIC_SINGLE_SKILL.key])
        bf_caster = Battlefield(
            teams={"monsters": frozenset({str(caster_monster.key)}), "party": frozenset({str(self.player.key)})},
            roster={str(caster_monster.key): caster_monster, str(self.player.key): self.player},
        )
        req_caster = monster_behaviour_policy(caster_monster, bf_caster)
        self.assertIsNotNone(req_caster)
        self.assertEqual(req_caster.skill_key, _SYNTH_MAGIC_SINGLE_SKILL.key)
        self.assertEqual(req_caster.targets, [self.player])

    @covers_requirement(
        "positional-marker::deterministic-single-target-attackers-skip-displaced-candidates"
    )
    def test_default_attack_policy_scopes_displaced_exclusion_to_strike_class(self):
        """default_attack_policy excludes displaced for strike skills, but retains displaced for magic skills."""
        npc = create_object(NPC, key="delegated_npc", location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        grant_lineage(npc, [_SYNTH_STRIKE_SKILL.key])

        apply_buff(self.monster_a, "t_displaced_hazard")
        bf = Battlefield(
            teams={"allies": frozenset({str(npc.key)}), "enemies": frozenset({str(self.monster_a.key)})},
            roster={str(npc.key): npc, str(self.monster_a.key): self.monster_a},
        )

        # Strike-owning delegated NPC returns None when only enemy is displaced
        req_strike = combat.default_attack_policy(npc, bf)
        self.assertIsNone(req_strike)

        # Magic-owning delegated NPC can target displaced enemy
        npc_caster = create_object(NPC, key="delegated_mage", location=self.room)
        npc_caster.race = _race_key()
        npc_caster.apply_race_baseline()
        grant_lineage(npc_caster, [_SYNTH_MAGIC_SINGLE_SKILL.key])
        bf_mage = Battlefield(
            teams={"allies": frozenset({str(npc_caster.key)}), "enemies": frozenset({str(self.monster_a.key)})},
            roster={str(npc_caster.key): npc_caster, str(self.monster_a.key): self.monster_a},
        )
        req_magic = combat.default_attack_policy(npc_caster, bf_mage)
        self.assertIsNotNone(req_magic)
        self.assertEqual(req_magic.targets, [self.monster_a])
