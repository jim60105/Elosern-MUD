"""SkillBook use actions through the real dispatcher, registry, and presenter.

Covers ``explore.skill_preview`` (epoch-scoped presentation selection, read
only) and ``explore.cast`` (exact payload forms, identity re-resolution, the
shared deterministic field entry, full-snapshot completion), plus the
``skill_use`` panel those publications carry.
"""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.skill_use_actions import (
    SkillUseActionError,
    validate_field_cast_payload,
    validate_skill_preview_payload,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.protocol import json_byte_size
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.skill_use import (
    SKILL_USE_SCHEMA_VERSION,
    SkillUseError,
    validate_skill_use,
)
from web.webclient.presentation.skill_use_selection import (
    SkillUseSelection,
    retire_skill_use_selection,
)
from world.rules.clock import get_world_clock, read_world_clock
from world.rules.combat_session import clear_session, read_session
from world.rules.tests._combat_session_helpers import (
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS

_T_DAMAGE = SYNTH_SKILLS["t_ember_burst"].key
_T_HEAL = SYNTH_SKILLS["t_hush_mend"].key
_T_SELF = SYNTH_SKILLS["t_moss_veil"].key
_T_NONE = SYNTH_SKILLS["t_cinder_breath"].key
_T_PASSIVE = SYNTH_SKILLS["t_steady_stride"].key
_T_AREA_DAMAGE = SYNTH_SEAM_AREA_SKILL.key
_T_AREA_HEAL = replace(
    SYNTH_SKILLS["t_hush_mend"],
    key="t_hush_chorus",
    label="靜謐合唱",
    description="以溫潤的合唱同時撫平身邊每一道傷口。",
    target_spec=TargetSpec.AREA,
    effects=["heal:area"],
)


class _Session:
    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 1
        self.protocol_key = "websocket"

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class SkillUsePayloadValidationTests(EvenniaTest):
    def test_preview_accepts_only_skill_key_and_closed_scale(self):
        self.assertEqual(
            validate_skill_preview_payload({"skill_key": "t_a"}),
            {"skill_key": "t_a", "scale": 1.0},
        )
        for bad in (
            {},
            {"skill_key": ""},
            {"skill_key": "a b"},
            {"skill_key": "x" * 65},
            {"skill_key": "t_a", "scale": True},
            {"skill_key": "t_a", "scale": 0.3},
            {"skill_key": "t_a", "actor": 1},
        ):
            with self.subTest(payload=bad), self.assertRaises(SkillUseActionError):
                validate_skill_preview_payload(bad)

    def test_cast_rejects_every_tampered_shape(self):
        ok = validate_field_cast_payload({"skill_key": "t_a", "target_ids": [3, 1]})
        self.assertEqual(ok["target_ids"], (3, 1))
        self.assertIsNone(ok["opening_target_id"])
        anchor = validate_field_cast_payload({"skill_key": "t_a", "opening_target_id": 9})
        self.assertEqual(anchor["opening_target_id"], 9)
        for bad in (
            {"skill_key": "t_a", "target_ids": [1], "opening_target_id": 2},
            {"skill_key": "t_a", "target_ids": []},
            {"skill_key": "t_a", "target_ids": [1, 1]},
            {"skill_key": "t_a", "target_ids": [True]},
            {"skill_key": "t_a", "target_ids": [0]},
            {"skill_key": "t_a", "target_ids": [2**53]},
            {"skill_key": "t_a", "target_ids": list(range(1, 66))},
            {"skill_key": "t_a", "opening_target_id": True},
            {"skill_key": "t_a", "target_shorthand": "all"},
            {"skill_key": "t_a", "scale": False},
            {"skill_key": "t_a", "actor_id": 1},
            {"skill_key": "t_a", "cost": {"mp": 0}},
            {"skill_key": "flee"},
        ):
            with self.subTest(payload=bad), self.assertRaises(SkillUseActionError):
                validate_field_cast_payload(bad)


class _SkillUseCase(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        open_synthetic_scope(
            self,
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
                    _T_AREA_DAMAGE: SYNTH_SEAM_AREA_SKILL,
                    _T_AREA_HEAL.key: _T_AREA_HEAL,
                }
            },
        )
        super().setUp()
        self.room = create_object(Room, key="skill use glade")
        self.player = _player("skill user")
        self.player.location = self.room
        self.player.traits.mp.current = self.player.traits.mp.max
        grant_lineage(
            self.player,
            [_T_DAMAGE, _T_HEAL, _T_SELF, _T_NONE, _T_AREA_DAMAGE, _T_AREA_HEAL.key],
            [_T_PASSIVE],
        )
        self.clock = get_world_clock()
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()
        self.session = _Session(self.player)
        self.coordinator = attach_coordinator(self.session, self.registry)
        self.coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        self.sequence = 0

    def tearDown(self):
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

    def _act(self, action_id, payload):
        self.sequence += 1
        handle_ui_action(
            self.session,
            self.player,
            {
                "protocol_version": 1,
                "presentation_epoch": self.coordinator.epoch,
                "request_id": f"r{self.sequence}",
                "base_revision": self.coordinator.revision,
                "action_id": action_id,
                "payload": payload,
            },
            self.action_registry,
            self.registry,
        )
        results = [call for call in self.session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    def _last_publication(self):
        for call in reversed(self.session.sent):
            for name in ("ui_snapshot", "ui_update"):
                if name in call:
                    return name, call[name][0][0]
        raise AssertionError("no publication")

    def _panel(self):
        context = build_presentation_context(self.session, self.player)
        return self.registry.render("skill_use", context)


class SkillPreviewActionTests(_SkillUseCase):
    def test_preview_publishes_only_the_panel_and_mutates_nothing(self):
        npc = self._npc("preview npc")
        wolf = self._wolf("preview wolf")
        mp_before = self.player.traits.mp.value
        tick_before = read_world_clock().tick
        result = self._act("explore.skill_preview", {"skill_key": _T_HEAL})
        self.assertEqual(result["outcome"], "success")
        kind, envelope = self._last_publication()
        self.assertEqual(kind, "ui_update")
        self.assertEqual(set(envelope["panels"]), {"skill_use"})
        panel = envelope["panels"]["skill_use"]
        self.assertEqual(panel["schema_version"], SKILL_USE_SCHEMA_VERSION)
        self.assertEqual(panel["skill"]["key"], _T_HEAL)
        self.assertEqual(
            [row["identity"] for row in panel["skill"]["targets"]],
            [self.player.pk, npc.pk],
        )
        self.assertEqual(panel["skill"]["openings"][0]["identity"], wolf.pk)
        self.assertEqual(panel["skill"]["openings"][0]["target_ids"], [wolf.pk])
        self.assertIn("開戰", panel["skill"]["openings"][0]["label"])
        self.assertTrue(panel["skill"]["usable_out_of_combat"])
        self.assertEqual(self.player.traits.mp.value, mp_before)
        self.assertIsNone(read_session(self.player))
        self.assertEqual(read_world_clock().tick, tick_before)

    def test_disabled_skill_is_still_inspectable(self):
        self.player.traits.mp.current = 0
        result = self._act("explore.skill_preview", {"skill_key": _T_NONE})
        self.assertEqual(result["outcome"], "success")
        panel = self._panel()
        self.assertFalse(panel["skill"]["enabled"])
        self.assertEqual(panel["skill"]["disabled_reason"]["code"], "insufficient_resource")
        self.assertIn("MP", panel["skill"]["disabled_reason"]["message"])

    def test_passive_unknown_and_combat_mode_are_rejected(self):
        for key in (_T_PASSIVE, "t_never_owned"):
            with self.subTest(key=key):
                result = self._act("explore.skill_preview", {"skill_key": key})
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], "unknown_skill")
        self.assertEqual(self._panel()["available"], False)
        from world.rules.combat_session import engage

        engage(self.player, self._wolf("mode wolf"))
        result = self._act("explore.skill_preview", {"skill_key": _T_HEAL})
        self.assertEqual(result["code"], "not_in_exploration")

    def test_selection_is_epoch_scoped_and_never_crosses_sessions(self):
        self._act("explore.skill_preview", {"skill_key": _T_HEAL})
        other = _Session(self.player)
        attach_coordinator(other, self.registry)
        other_context = build_presentation_context(other, self.player)
        self.assertIsNone(other_context.skill_use)
        self.assertEqual(
            build_presentation_context(self.session, self.player).skill_use,
            (_T_HEAL, 1.0),
        )
        self.coordinator.reset()
        self.assertIsNone(build_presentation_context(self.session, self.player).skill_use)
        self.assertEqual(self._panel()["available"], False)

    def test_retired_selection_renders_unavailable(self):
        self._act("explore.skill_preview", {"skill_key": _T_SELF})
        retire_skill_use_selection(self.session)
        self.assertEqual(self._panel()["available"], False)

    def test_preview_without_presentation_session_rejects(self):
        from web.webclient.actions.skill_use_actions import _skill_preview_adapter

        result = _skill_preview_adapter(self.player, {"skill_key": _T_HEAL, "scale": 1.0})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_presentation_session")

    def test_duplicate_names_keep_distinct_identities(self):
        first = self._npc("twin villager")
        second = self._npc("twin villager")
        self._act("explore.skill_preview", {"skill_key": _T_HEAL})
        targets = self._panel()["skill"]["targets"]
        by_id = {row["identity"]: row["label"] for row in targets}
        self.assertNotEqual(by_id[first.pk], by_id[second.pk])
        self.assertTrue(by_id[first.pk].startswith("twin villager"))

    def test_area_opening_discloses_every_living_monster(self):
        wolves = [self._wolf(f"area wolf {index}") for index in range(3)]
        self._act("explore.skill_preview", {"skill_key": _T_AREA_DAMAGE})
        openings = self._panel()["skill"]["openings"]
        ids = sorted(wolf.pk for wolf in wolves)
        self.assertEqual([row["identity"] for row in openings], ids)
        for row in openings:
            self.assertEqual(row["target_ids"], ids)
            self.assertIn("3", row["label"])


class FieldCastActionTests(_SkillUseCase):
    def _tick(self):
        return read_world_clock().tick

    def test_ordinary_single_heal_settles_and_publishes_a_full_snapshot(self):
        npc = self._npc("wounded npc")
        npc.traits.hp.current = 1
        self._act("explore.skill_preview", {"skill_key": _T_HEAL})
        tick_before = self._tick()
        result = self._act("explore.cast", {"skill_key": _T_HEAL, "target_ids": [npc.pk]})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "cast")
        kind, envelope = self._last_publication()
        self.assertEqual(kind, "ui_snapshot")
        self.assertEqual(result["presentation_revision"], envelope["revision"])
        self.assertGreater(int(npc.traits.hp.current), 1)
        self.assertGreater(self._tick(), tick_before)
        # Completion retires the preview selection.
        self.assertEqual(envelope["panels"]["skill_use"]["available"], False)
        self.assertNotIn("field_combat_terminal", result)

    def test_none_and_self_carry_no_target_authority(self):
        for key in (_T_NONE, _T_SELF):
            with self.subTest(skill=key):
                result = self._act("explore.cast", {"skill_key": key})
                self.assertEqual(result["outcome"], "success", result)

    def test_ordinary_area_uses_explicit_identities(self):
        npc = self._npc("chorus npc")
        with patch(
            "world.rules.cast_settlement.settle_out_of_combat_cast",
            wraps=__import__("world.rules.cast_settlement", fromlist=["x"]).settle_out_of_combat_cast,
        ) as settle:
            result = self._act(
                "explore.cast",
                {"skill_key": _T_AREA_HEAL.key, "target_ids": [self.player.pk, npc.pk]},
            )
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(settle.call_args.args[0].targets, [self.player, npc])

    def test_monster_in_ordinary_list_is_refused_before_settlement(self):
        wolf = self._wolf("listed wolf")
        with patch("world.rules.cast_settlement.settle_out_of_combat_cast") as settle:
            result = self._act("explore.cast", {"skill_key": _T_HEAL, "target_ids": [wolf.pk]})
        self.assertEqual(result["code"], "monster_requires_opening")
        settle.assert_not_called()
        self.assertIsNone(read_session(self.player))

    def test_remote_or_vanished_identities_reject(self):
        elsewhere = create_object(Room, key="elsewhere")
        far_npc = create_object(NPC, key="far npc", location=elsewhere)
        mp_before = self.player.traits.mp.value
        for payload in (
            {"skill_key": _T_HEAL, "target_ids": [far_npc.pk]},
            {"skill_key": _T_DAMAGE, "opening_target_id": far_npc.pk},
        ):
            with self.subTest(payload=payload):
                result = self._act("explore.cast", payload)
                self.assertEqual(result["code"], "target_not_present")
        self.assertEqual(self.player.traits.mp.value, mp_before)

    def test_damage_without_an_opening_spends_nothing(self):
        npc = self._npc("spared npc")
        mp_before = self.player.traits.mp.value
        result = self._act("explore.cast", {"skill_key": _T_DAMAGE, "target_ids": [npc.pk]})
        self.assertEqual(result["code"], "damage_requires_monster_target")
        self.assertEqual(self.player.traits.mp.value, mp_before)
        self.assertIsNone(read_session(self.player))

    def test_monster_anchor_opens_combat_with_a_round_record(self):
        wolf = self._wolf("opening wolf")
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch(
            "world.rules.combat.damage.roll_d100", return_value=50
        ), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            result = self._act(
                "explore.cast", {"skill_key": _T_HEAL, "opening_target_id": wolf.pk}
            )
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(result["code"], "round")
        kind, envelope = self._last_publication()
        self.assertEqual(kind, "ui_snapshot")
        self.assertEqual(envelope["mode"], "combat")
        self.assertIsNotNone(read_session(self.player))
        self.assertEqual(envelope["panels"]["combat_beats"]["available"], True)
        self.assertNotIn("combat_round", result)

    def test_instant_terminal_opening_publishes_settled_exploration(self):
        for trait_key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, trait_key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        doomed = _monster("doomed wolf", hp=100, atk=10)
        doomed.location = self.room
        payload = {"skill_key": _T_DAMAGE, "opening_target_id": doomed.pk}
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch("web.webclient.actions.dispatcher._schedule_terminal_combat_options") as schedule,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = self._act("explore.cast", payload)
            # A duplicate delivery replays the cached result and never
            # re-schedules (or re-settles) anything.
            replay = {
                "protocol_version": 1,
                "presentation_epoch": self.coordinator.epoch,
                "request_id": f"r{self.sequence}",
                "base_revision": self.coordinator.revision,
                "action_id": "explore.cast",
                "payload": payload,
            }
            handle_ui_action(self.session, self.player, replay, self.action_registry, self.registry)
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(result["code"], "victory")
        self.assertNotIn("field_combat_terminal", result)
        schedule.assert_called_once_with(self.player)
        snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
        envelope = snapshots[-1]["ui_snapshot"][0][0]
        # No transient combat view: the snapshot is already settled exploration.
        self.assertEqual(envelope["mode"], "exploration")
        self.assertEqual(envelope["panels"]["context_actions"]["kind"], "exploration")
        self.assertIsNone(read_session(self.player))

    def test_dead_or_unadvertised_monster_ids_read_as_absent(self):
        dead = self._wolf("fallen wolf")
        dead.traits.hp.current = 0
        for identity in (dead.pk, 987654):
            with self.subTest(identity=identity):
                result = self._act("explore.cast", {"skill_key": _T_HEAL, "target_ids": [identity]})
                self.assertEqual(result["code"], "target_not_present")

    def test_ordinary_area_with_a_departed_member_spends_nothing(self):
        npc = self._npc("wandering npc")
        npc.location = create_object(Room, key="elsewhere glade")
        mp_before = self.player.traits.mp.value
        tick_before = self._tick()
        result = self._act(
            "explore.cast",
            {"skill_key": _T_AREA_HEAL.key, "target_ids": [self.player.pk, npc.pk]},
        )
        self.assertEqual(result["code"], "target_not_present")
        self.assertEqual(self.player.traits.mp.value, mp_before)
        self.assertEqual(self._tick(), tick_before)

    def test_active_session_rejects_the_field_action(self):
        from world.rules.combat_session import engage

        engage(self.player, self._wolf("busy wolf"))
        with patch("world.rules.combat_session.submit_player_action") as submit:
            result = self._act("explore.cast", {"skill_key": _T_NONE})
        self.assertEqual(result["code"], "not_in_exploration")
        submit.assert_not_called()

    def test_duplicate_named_area_opening_rejects_without_internal_error(self):
        first = self._wolf("twin wolf")
        self._wolf("twin wolf")
        result = self._act(
            "explore.cast", {"skill_key": _T_AREA_DAMAGE, "opening_target_id": first.pk}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertNotEqual(result["code"], "internal_error")
        self.assertIsNone(read_session(self.player))

    def test_duplicate_request_executes_once(self):
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": self.coordinator.epoch,
            "request_id": "same",
            "base_revision": self.coordinator.revision,
            "action_id": "explore.cast",
            "payload": {"skill_key": _T_NONE},
        }
        handle_ui_action(self.session, self.player, envelope, self.action_registry, self.registry)
        mp_after_first = self.player.traits.mp.value
        tick_after_first = self._tick()
        handle_ui_action(self.session, self.player, envelope, self.action_registry, self.registry)
        self.assertEqual(self.player.traits.mp.value, mp_after_first)
        self.assertEqual(self._tick(), tick_after_first)


class SkillUsePanelValidationTests(_SkillUseCase):
    def _valid(self):
        return {
            "schema_version": 1,
            "available": True,
            "kind": "skill_use",
            "scale": 1.0,
            "skill": {
                "key": _T_HEAL,
                "label": "靜謐癒合",
                "description": "說明",
                "target_spec": "single",
                "usable_out_of_combat": True,
                "cost": {"mp": 11},
                "enabled": True,
                "disabled_reason": None,
                "targets": [
                    {"identity": 1, "label": "甲", "enabled": True, "disabled_reason": None}
                ],
                "openings": [
                    {
                        "identity": 2,
                        "label": "對狼出手（將開戰）",
                        "target_ids": [2],
                        "enabled": False,
                        "disabled_reason": {"code": "x", "message": "不行"},
                    }
                ],
            },
        }

    def test_valid_form_round_trips(self):
        self.assertEqual(validate_skill_use(self._valid())["skill"]["key"], _T_HEAL)

    def test_malformed_forms_are_rejected(self):
        def mutate(change):
            payload = self._valid()
            change(payload)
            return payload

        for name, change in (
            ("unknown field", lambda p: p["skill"].update(extra=1)),
            ("wrong version", lambda p: p.update(schema_version=2)),
            ("duplicate identity", lambda p: p["skill"]["targets"].append(dict(p["skill"]["targets"][0]))),
            ("dangling line-up", lambda p: p["skill"]["openings"][0].update(target_ids=[2, 99])),
            ("single opening widened", lambda p: p["skill"]["openings"][0].update(target_ids=[2, 1])),
            ("target also opening", lambda p: p["skill"]["targets"][0].update(identity=2)),
            ("disabled without reason", lambda p: p["skill"]["targets"][0].update(enabled=False)),
            ("enabled with reason", lambda p: p["skill"]["targets"][0].update(disabled_reason={"code": "x", "message": "y"})),
            ("enabled mismatch", lambda p: p["skill"].update(enabled=False, disabled_reason={"code": "x", "message": "y"})),
            ("boolean identity", lambda p: p["skill"]["targets"][0].update(identity=True)),
            ("too many", lambda p: p["skill"].update(targets=[{"identity": i, "label": "x", "enabled": True, "disabled_reason": None} for i in range(3, 68)])),
            ("bad scale", lambda p: p.update(scale=0.3)),
        ):
            with self.subTest(case=name), self.assertRaises(Exception):
                validate_skill_use(mutate(change))

    def test_upper_bound_preview_fits_a_full_snapshot(self):
        for index in range(64):
            self._wolf(f"horde wolf {index:02d} " + "長" * 20)
        for index in range(63):
            self._npc(f"crowd npc {index:02d} " + "長" * 20)
        self._act("explore.skill_preview", {"skill_key": _T_AREA_HEAL.key})
        panel = self._panel()
        self.assertTrue(panel["available"])
        self.assertEqual(len(panel["skill"]["openings"]), 64)
        self.assertEqual(len(panel["skill"]["targets"]), 64)
        context = build_presentation_context(self.session, self.player)
        snapshot = self.coordinator.full_snapshot(context)
        self.assertLessEqual(json_byte_size(snapshot), 65_536)
        self.assertEqual(snapshot["panels"]["skill_use"]["available"], True)

    def test_overflowing_room_renders_unavailable_not_truncated(self):
        for index in range(64):
            self._npc(f"overflow npc {index}")
        self._act("explore.skill_preview", {"skill_key": _T_HEAL})
        self.assertEqual(self._panel()["available"], False)
