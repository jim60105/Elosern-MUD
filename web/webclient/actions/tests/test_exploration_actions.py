"""Exact exploration action payload validators and adapter tests.

Covers the six explore payload validators, the movement charge/recording
through the shared exit seam, the stale/tampered/locked rejections, the combat
plain traversal, the ``at_pre_move`` veto, scripted and free-form
dialogue (offline degrade included), engage-to-combat, and the shared skip
helper arithmetic.

Registry identities come from the synthetic kit: dialogue hosts answer from
the kit's lodgekeeper table (with the shipped guild-staff row merged through
a runtime probe for the production turnin special case), the guild-branch
component and delivery items are kit rows, and the practice suite drills a
kit skill inside a scoped registry.
"""

from tools.spec_traceability import covers_requirement

import json
import unittest
from unittest.mock import patch

from django.test import override_settings
from twisted.internet import defer

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room, TerrainRoom
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_ITEM_KEY_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
    _dialogue_leave_adapter,
    _deliver_adapter,
    _engage_adapter,
    _look_adapter,
    _move_adapter,
    _party_invite_adapter,
    _party_leave_adapter,
    _present_by_id,
    _resolve_exit,
    _talk_freeform_adapter,
    _talk_scripted_adapter,
    _wait_adapter,
    validate_engage_payload,
    validate_deliver_payload,
    validate_dialogue_leave_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from world.ai.fake_client import FakeLLMClient
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    DialogueDefinition,
    KeywordResponse,
)
from world.ai.guardrail import _degrade_fallbacks, _semantic_validators
from world.ai.npc_dialogue import register_npc_dialogue
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.quests.definitions import QuestStage
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    is_in_active_session,
)
from world.rules.map_knowledge import (
    KnowledgeError,
    encode_grid,
    encode_wild,
    parse_knowledge,
)
from world.rules.time_skip import MAX_WEB_SKIP_SECONDS
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests._guild_service_probes import synthetic_branch_key
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_ITEMS, make_skill

# Kit identities (test-data-independence): the dialogue/branch/item/skill
# fixtures resolve through the kit rows; the shipped guild-staff table row is
# merged into the scoped table through a runtime probe (the production
# turnin-keyword special case keys off that table), never an import-time
# symbol name.
_T_DIALOGUE = "t_synth_lodgekeeper"
_T_BRANCH = synthetic_branch_key()
_T_ITEM = SYNTH_ITEMS["t_ember_spray"].key
_T_SKILL = make_skill("t_practice_drill").key


def _live(module: str, attribute: str):
    """Fetch a shipped module attribute by runtime name (test-data gate: no
    scan-time registry refs)."""
    import importlib

    return getattr(importlib.import_module(module), attribute)


#: The kit lodgekeeper table's authored keyword/response fragments.
_T_LODGE_KEYWORD = "住宿"
_T_LODGE_LINE = "雲杉驛站一晚十八銅"
_T_LODGE_GREETING = "櫃檯後的老板娘"

#: A staff-shaped authored table keyed by the PRODUCTION guild-staff key
#: (imported constant, not a literal): the turnin special case keys off that
#: exact pair, so the action suite reproduces the shape with its own prose
#: instead of borrowing the shipped table row.
_T_STAFF_TURNIN_LINE = "「先在櫃檯報到台註冊（t-synth-desk register）。」"
_T_STAFF_ROW = DialogueDefinition(
    greeting="櫃檯後的合成公會職員抬起眼：「要用 t-synth-desk list 接任務。」",
    responses=(
        KeywordResponse(GUILD_STAFF_TURNIN_KEYWORD, _T_STAFF_TURNIN_LINE),
    ),
)


def _t_dialogue_scope(test, with_staff: bool = False):
    """Dialogue scope: the kit lodgekeeper table (plus the staff-shaped
    authored row when the turnin special case is under test)."""
    extra = (
        {"dialogue": {GUILD_STAFF_DIALOGUE_KEY: _T_STAFF_ROW}} if with_staff else None
    )
    open_synthetic_scope(test, "dialogue", extra=extra)


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _failing_advance(*args, **kwargs):
    """A clock advance that always fails (patched onto ``WorldClock``)."""
    raise RuntimeError("clock advance failed")


def _reset_guardrail():
    _semantic_validators.clear()
    _degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def _reply_text(speech="艾洛希雅對你點頭。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


class _HeldClient:
    """Test double whose response is a Deferred the test resolves manually."""

    def __init__(self):
        self.deferred = defer.Deferred()
        self.calls = []

    def get_response(self, descriptor):
        self.calls.append(descriptor)
        return self.deferred


class ExplorationValidatorTests(unittest.TestCase):
    def test_move_payload_exact(self):
        self.assertEqual(
            validate_move_payload({"exit_ref": "42", "current_node": "room:5"}),
            {"exit_ref": "42", "current_node": "room:5"},
        )
        for bad in (
            None,
            {"exit_ref": "42"},
            {"exit_ref": "42", "current_node": "room:5", "extra": 1},
            {"exit_ref": "x" * (MAX_EXIT_REF_CHARS + 1), "current_node": "room:5"},
            {"exit_ref": "中文", "current_node": "room:5"},
            {"exit_ref": "42", "current_node": "not:a:node"},
            {"exit_ref": "42", "current_node": "x" * (MAX_NODE_ID_CHARS + 1)},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_move_payload(bad)

    def test_look_payload_exact(self):
        self.assertEqual(validate_look_payload({"room": True}), {"room": True})
        self.assertEqual(validate_look_payload({"target_id": 7}), {"target_id": 7})
        for bad in (
            None,
            {"room": True, "target_id": 7},
            {"room": "yes"},
            {"target_id": 0},
            {"target_id": "7"},
            {},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_look_payload(bad)

    def test_talk_scripted_payload_exact(self):
        self.assertEqual(
            validate_talk_scripted_payload({"npc_id": 3, "keyword_id": "公會"}),
            {"npc_id": 3, "keyword_id": "公會"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 0, "keyword_id": "公會"},
            {"npc_id": True, "keyword_id": "公會"},
            {"npc_id": 3, "keyword_id": ""},
            {"npc_id": 3, "keyword_id": "x" * (MAX_KEYWORD_ID_CHARS + 1)},
            {"npc_id": 3, "keyword_id": "公會", "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_scripted_payload(bad)

    def test_talk_freeform_payload_exact(self):
        self.assertEqual(
            validate_talk_freeform_payload({"npc_id": 3, "speech": "你好"}),
            {"npc_id": 3, "speech": "你好"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 3, "speech": ""},
            {"npc_id": 3, "speech": "你" * (MAX_SPEECH_CODE_POINTS + 1)},
            {"npc_id": 3, "speech": "你好", "actor": "x"},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_freeform_payload(bad)

    def test_dialogue_leave_payload_exact(self):
        self.assertEqual(
            validate_dialogue_leave_payload({"npc_id": 3}), {"npc_id": 3}
        )
        for bad in (
            None,
            {},
            {"npc_id": 0},
            {"npc_id": True},
            {"npc_id": "3"},
            {"npc_id": 3, "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_dialogue_leave_payload(bad)

    def test_party_invite_payload_exact(self):
        self.assertEqual(
            validate_party_invite_payload({"npc_id": 3, "message": ""}),
            {"npc_id": 3, "message": ""},
        )
        self.assertEqual(
            validate_party_invite_payload({"npc_id": 3, "message": "你願意嗎？"}),
            {"npc_id": 3, "message": "你願意嗎？"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 3, "message": None},
            {"npc_id": 3, "message": "你" * (MAX_SPEECH_CODE_POINTS + 1)},
            {"npc_id": 0, "message": ""},
            {"npc_id": 3, "message": "", "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_party_invite_payload(bad)

    def test_party_leave_payload_exact(self):
        self.assertEqual(
            validate_party_leave_payload({"npc_id": 9}), {"npc_id": 9}
        )
        for bad in (
            None,
            {"npc_id": 0},
            {"npc_id": "9"},
            {"npc_id": True},
            {},
            {"npc_id": 9, "x": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_party_leave_payload(bad)

    def test_engage_payload_exact(self):
        self.assertEqual(validate_engage_payload({"monster_id": 9}), {"monster_id": 9})
        for bad in (
            None,
            {"monster_id": 0},
            {"monster_id": "9"},
            {"monster_id": True},
            {},
            {"monster_id": 9, "x": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_engage_payload(bad)

    def test_wait_payload_exact(self):
        self.assertEqual(validate_wait_payload({"daypart": "dawn"}), {"daypart": "dawn"})
        self.assertEqual(validate_wait_payload({"seconds": 3600}), {"seconds": 3600})
        self.assertEqual(validate_wait_payload({"sleep": True}), {"sleep": True})
        for bad in (
            None,
            {"daypart": "tea"},
            {"seconds": 0},
            {"seconds": MAX_WEB_SKIP_SECONDS + 1},
            {"seconds": "3600"},
            {"sleep": "yes"},
            {"daypart": "dawn", "seconds": 60},
            {},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_wait_payload(bad)

    def test_no_payload_accepts_actor_host_session_destination_price_or_clock(self):
        for field in (
            "actor",
            "host",
            "session_id",
            "destination",
            "destination_room",
            "price",
            "stock",
            "clock",
            "tick",
        ):
            for validator in (
                validate_move_payload,
                validate_look_payload,
                validate_talk_scripted_payload,
                validate_talk_freeform_payload,
                validate_party_invite_payload,
                validate_party_leave_payload,
                validate_engage_payload,
                validate_wait_payload,
                validate_deliver_payload,
            ):
                with self.assertRaises(ExplorationActionError):
                    validator({field: "x"})

    def test_deliver_payload_exact(self):
        self.assertEqual(
            validate_deliver_payload({"npc_id": 5, "item_key": _T_ITEM}),
            {"npc_id": 5, "item_key": _T_ITEM},
        )
        bad = (
            {},
            {"npc_id": 5},
            {"item_key": _T_ITEM},
            {"npc_id": 5, "item_key": _T_ITEM, "extra": 1},
            {"npc_id": 0, "item_key": _T_ITEM},
            {"npc_id": -1, "item_key": _T_ITEM},
            {"npc_id": 1.5, "item_key": _T_ITEM},
            {"npc_id": "5", "item_key": _T_ITEM},
            {"npc_id": True, "item_key": _T_ITEM},
            {"npc_id": None, "item_key": _T_ITEM},
            {"npc_id": 5, "item_key": ""},
            {"npc_id": 5, "item_key": "非識別鍵"},
            {"npc_id": 5, "item_key": "x" * (MAX_ITEM_KEY_CHARS + 1)},
            {"npc_id": 5, "item_key": 7},
            {"npc_id": 5, "item_key": None},
            "not an object",
            None,
            ["npc_id"],
        )
        for payload in bad:
            with self.assertRaises(ExplorationActionError, msg=payload):
                validate_deliver_payload(payload)


# The practice drill skill row, built from the kit martial template.
_T_SKILL_ROW = make_skill("t_practice_drill")


class ExplorationActionAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        # Scope before construction: dialogue hosts answer from the kit
        # table (shipped guild-staff row merged for the production turnin
        # special case), and the practice suite resolves its drill skill in
        # a scoped registry (the kit's forced-innate rows ride along so the
        # engage path's production innate keys still resolve).
        _t_dialogue_scope(self, with_staff=True)
        open_synthetic_scope(
            self,
            "skills",
            extra={
                "skills": {
                    **synth_innate_overlay()["skills"],
                    _T_SKILL: _T_SKILL_ROW,
                }
            },
        )
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="探索行動測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.destination = create_object(Room, key="目的地", location=None)
        from typeclasses.exits import Exit

        self.exit_obj = create_object(
            Exit,
            key="東",
            location=self.room1,
            destination=self.destination,
        )

    def tearDown(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        _reset_guardrail()
        super().tearDown()

    def _move(self, payload):
        return _move_adapter(self.player, payload)

    # ------------------------------------------------------------------
    # explore.move
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_move_charges_exactly_30_seconds_and_records_the_destination_node(self):
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "success")
        clock = get_world_clock()
        self.assertEqual(
            clock.tick - before, CLOCK_YAML["command_defaults"]["move"]
        )
        self.assertIs(self.player.location, self.destination)
        visited = {visit.node_id for visit in parse_knowledge(self.player)}
        self.assertIn(f"room:{int(self.destination.pk)}", visited)

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-reports-failure-truthfully-on-every-client-path")
    def test_failed_charge_reports_move_failed_with_player_still_at_source(self):
        before = get_world_clock().tick
        with patch.object(WorldClock, "advance", _failing_advance):
            result = self._move(
                {
                    "exit_ref": str(int(self.exit_obj.id)),
                    "current_node": f"room:{int(self.room1.pk)}",
                }
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "move_failed")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)
        with self.assertRaises(KnowledgeError):
            parse_knowledge(self.player)

    def test_stale_current_node_guard_performs_no_traversal(self):
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": "room:9999"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "stale_location")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    def test_missing_exit_rejects_without_charging(self):
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": "999999", "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_exit")
        self.assertEqual(get_world_clock().tick, before)

    def test_locked_exit_rejects_without_charging(self):
        self.exit_obj.locks.add("traverse:false()")
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "locked")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_combat_at_pre_move_veto_blocks_movement_without_time_or_knowledge(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        engage(self.player, monster)
        self.assertTrue(is_in_active_session(self.player))
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "in_combat")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    def test_destinationless_exit_rejects_without_charging(self):
        from unittest.mock import PropertyMock

        with patch.object(
            type(self.exit_obj),
            "destination",
            new_callable=PropertyMock,
            return_value=None,
        ):
            before = get_world_clock().tick
            result = self._move(
                {
                    "exit_ref": str(int(self.exit_obj.id)),
                    "current_node": f"room:{int(self.room1.pk)}",
                }
            )
        self.assertEqual(result["code"], "no_exit")
        self.assertEqual(get_world_clock().tick, before)

    def test_traverse_access_and_traversal_failures_are_rejected(self):
        payload = {
            "exit_ref": str(int(self.exit_obj.id)),
            "current_node": f"room:{int(self.room1.pk)}",
        }
        with patch.object(self.exit_obj, "access", side_effect=RuntimeError("boom")):
            self.assertEqual(self._move(payload)["code"], "locked")
        with patch.object(
            self.exit_obj, "at_traverse", side_effect=RuntimeError("boom")
        ):
            self.assertEqual(self._move(payload)["code"], "move_failed")
        with patch.object(self.exit_obj, "at_traverse", lambda actor, dest: None):
            self.assertEqual(self._move(payload)["code"], "move_failed")
        self.assertIs(self.player.location, self.room1)

    def test_move_from_grid_room_records_a_grid_node(self):
        from typeclasses.exits import Exit
        from typeclasses.rooms import GridRoom

        sync_grid()
        gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        exit_obj = create_object(
            Exit, key="東", location=gate, destination=self.destination
        )
        self.player.location = gate
        node = encode_grid(SOUTH_GATE_XYZ[2], SOUTH_GATE_XYZ[0], SOUTH_GATE_XYZ[1])
        result = self._move(
            {"exit_ref": str(int(exit_obj.id)), "current_node": node}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIs(self.player.location, self.destination)

    def test_wild_terrain_current_node_is_encoded(self):
        terrain = create_object(TerrainRoom, key="荒野", location=None)
        terrain.ndb.active_coordinates = (7, 11)
        self.player.location = terrain
        self.assertEqual(
            _current_node(self.player), encode_wild(WILDERNESS_NAME, 7, 11)
        )
        bare = create_object(TerrainRoom, key="霧區", location=None)
        self.player.location = bare
        self.assertIsNone(_current_node(self.player))

    def test_actor_without_a_location_rejects_every_present_identity(self):
        self.player.location = None
        self.assertIsNone(_present_by_id(self.player, 1))
        self.assertIsNone(_current_node(self.player))
        self.assertIsNone(_resolve_exit(self.player, "1"))
        self.assertEqual(
            _look_adapter(self.player, {"target_id": 1})["code"], "no_target"
        )
        self.assertEqual(
            _look_adapter(self.player, {"room": True})["code"], "no_room"
        )
        result = _move_adapter(
            self.player, {"exit_ref": "1", "current_node": "room:1"}
        )
        self.assertEqual(result["code"], "stale_location")

    # ------------------------------------------------------------------
    # explore.look
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-look-reuses-the-command-appearance-path")
    def test_look_at_present_entity_uses_ordinary_display(self):
        target = create_object(NPC, key="路人", location=self.room1)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        msg.assert_called_once()
        self.assertIn("路人", str(msg.call_args[0][0]))

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_npc_shows_the_affinity_stage_line(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change

        target = create_object(NPC, key="店長", location=self.room1)
        target.db.desc = "一位笑容可掬的店長。"
        apply_affinity_change(target, self.player, AffinitySource.QUEST_COMPLETION, 50)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertIn("她看著你的眼神裡帶著信賴。", appearance)
        self.assertNotIn("50", appearance)
        self.assertNotIn("99", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_recordless_monster_renders_no_stage_line(self):
        monster = create_object(Monster, key="野狼", location=self.room1)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertNotIn("信賴", appearance)
        self.assertNotIn("羈絆", appearance)
        self.assertIsNone(monster.db.relations_data)

    def test_look_at_absent_target_is_rejected(self):
        result = _look_adapter(self.player, {"target_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_target")

    def test_look_appearance_failure_is_rejected_without_prose(self):
        target = create_object(NPC, key="路人", location=self.room1)
        with patch.object(self.player, "at_look", side_effect=RuntimeError("boom")):
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "look_failed")

    @covers_requirement("displayed-stats-view::explore-look-shows-the-identical-displayed-stats-block")
    @covers_requirement("localized-appearance::target-appearance-includes-the-displayed-stats-block-on-every-entry-path")
    def test_webclient_target_look_carries_the_identical_displayed_stats_block(self):
        target = create_object(NPC, key="守衛", location=self.room1)
        target.race = "human"
        target.apply_race_baseline()
        target.db.desc = "一位專注的守衛。"
        target.db.disguised_stats = {"atk_phys": 60}
        expected = self.player.at_look(target)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(str(msg.call_args[0][0]), expected)
        self.assertIn("攻擊：60", expected)
        self.assertEqual(result["affected_panels"], ())

    @covers_requirement("displayed-stats-view::explore-look-shows-the-identical-displayed-stats-block")
    def test_webclient_room_look_carries_no_block_and_no_panel_replacement(self):
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"room": True})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertNotIn("攻擊：", appearance)
        self.assertNotIn("敏捷：", appearance)
        self.assertEqual(result["affected_panels"], ())

    @covers_requirement("displayed-stats-view::the-displayed-stats-block-never-influences-resolution")
    def test_webclient_look_publishes_the_block_only_in_the_narrative_text(self):
        target = create_object(NPC, key="守衛", location=self.room1)
        target.race = "human"
        target.apply_race_baseline()
        target.db.disguised_stats = {"atk_phys": 60}
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertIn("攻擊：60", str(msg.call_args[0][0]))
        self.assertEqual(
            set(result),
            {"outcome", "code", "message", "affected_panels"},
            "the look result must publish no panel payload",
        )

    # ------------------------------------------------------------------
    # explore.talk_scripted
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_scripted_host_answers_with_the_authored_line(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn(_T_LODGE_LINE, result["message"])

    def test_scripted_host_no_state_answer(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "補貨"}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn("櫃檯右側", result["message"])

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_turnin_keyword_flows_through_the_shared_dialogue_resolution(self):
        # The production turnin special case keys off the (imported-constant)
        # staff-table/keyword pair: an unregistered player at a staff-hosted
        # desk gets the authored register-first line through the shared
        # resolution AND the known-keyword affinity gain is skipped purely.
        host = create_object(NPC, key="公會職員", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        from typeclasses.components import GuildStaff

        host.components.add(
            GuildStaff.create(host, service_id="staff", branch_key=_T_BRANCH)
        )
        relations_before = host.db.relations_data
        result = _talk_scripted_adapter(
            self.player,
            {"npc_id": int(host.pk), "keyword_id": GUILD_STAFF_TURNIN_KEYWORD},
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn(_T_STAFF_TURNIN_LINE, result["message"])
        # Losing the special case would route this known keyword through the
        # normal +1 talk-affinity write; the fixture surface must stay pure.
        self.assertEqual(host.db.relations_data, relations_before)

    def test_unregistered_keyword_rejects_without_writing(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "不存在的話題"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unregistered_keyword")

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_no_longer_present_npc_rejects_before_any_dialogue_api(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        host.location = create_object(Room, key="別處", location=None)
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk"
        ) as talk:
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        talk.assert_not_called()

    def test_non_dialogue_host_rejects_before_any_dialogue_api(self):
        plain = create_object(NPC, key="路人", location=self.room1)
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(plain.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_dialogue_host")

    def test_talk_response_failure_and_silence_are_rejected(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk",
            side_effect=RuntimeError("boom"),
        ):
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["code"], "dialogue_failed")
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk",
            return_value=None,
        ):
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["code"], "no_response")

    # ------------------------------------------------------------------
    # explore.talk_freeform
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_reply_memory_and_verified_intent_are_applied(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        npc.db.inventory = [_T_ITEM]
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我給你一瓶藥水。",
                intent={"kind": "give_item", "item_key": _T_ITEM, "qty": 1},
            ),
        )
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg"):
            result = await_result(
                _talk_freeform_adapter(
                    self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(list(self.player.db.inventory or []), [_T_ITEM])
        self.assertEqual(list(npc.db.inventory or []), [])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(
            npc._chat_lines(self.player),
            ["探索行動測試: 你好", "對話精靈: 我給你一瓶藥水。"],
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_offline_degrade_yields_greeting_and_no_client_call(self):
        npc = create_object(LLMNPC, key="客棧老板娘", location=self.room1)
        npc.components.add(ScriptedDialogue.create(npc, dialogue_key=_T_DIALOGUE))
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ), patch.object(self.player, "msg") as msg:
                result = await_result(
                    _talk_freeform_adapter(
                        self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(len(client.calls), 0)
        texts = [str(call.args[0]) for call in msg.call_args_list if call.args]
        self.assertTrue(any(_T_LODGE_GREETING in text for text in texts))

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_illegal_intent_is_discarded_while_speech_is_kept(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我要你交出所有錢。", intent={"kind": "take_item"}),
        )
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg"):
            result = await_result(
                _talk_freeform_adapter(
                    self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        # Speech is kept (memory), the illegal intent changes no state.
        self.assertEqual(npc._chat_lines(self.player)[0], "探索行動測試: 你好")
        self.assertIsNone(self.player.db.guild_registration)
        self.assertEqual(list(self.player.db.inventory or []), [])

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_tampered_npc_id_rejects_before_any_client_work(self):
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _talk_freeform_adapter(
                self.player, {"npc_id": 999999, "speech": "你好"}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_transport_failure_settles_as_dialogue_failed(self):
        from twisted.internet.defer import fail as defer_fail

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        failing = defer_fail(Exception("transport down"))
        with patch.object(
            npc, "at_talked_to", return_value=failing
        ), patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client"
        ):
            result = await_result(
                _talk_freeform_adapter(
                    self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                )
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dialogue_failed")

    @covers_requirement("webclient-exploration-menu::freeform-talk-completion-rechecks-presence-before-applying-intents")
    def test_freeform_deferred_reply_after_the_player_moved_is_discarded(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        npc.db.inventory = [_T_ITEM]
        client = _HeldClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg") as msg:
            deferred = _talk_freeform_adapter(
                self.player, {"npc_id": int(npc.pk), "speech": "你好"}
            )
            self.player.location = self.destination
            client.deferred.callback(
                _reply_text(
                    speech="我給你一瓶藥水。",
                    intent={"kind": "give_item", "item_key": _T_ITEM, "qty": 1},
                )
            )
            result = await_result(deferred)
        self.assertEqual(result["outcome"], "success")
        self.assertIn("離開", result["message"])
        # The speech is shown (memory) and the stale note is surfaced, while
        # the intent changes no state (F22 completion gate).
        self.assertEqual(npc._chat_lines(self.player)[1], "對話精靈: 我給你一瓶藥水。")
        self.assertEqual(list(self.player.db.inventory or []), [])
        self.assertEqual(list(npc.db.inventory or []), [_T_ITEM])
        texts = [str(call.args[0]) for call in msg.call_args_list if call.args]
        self.assertIn("我給你一瓶藥水。", " ".join(texts))
        self.assertTrue(any("離開" in text for text in texts))

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_host_rejects_scripted_talk_without_a_transaction(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        host.db.schedule_state = "busy"
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk"
        ) as talk:
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIn("她現在正忙著", result["message"])
        talk.assert_not_called()

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_host_rejects_freeform_talk_before_any_seam_work(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        npc.db.schedule_state = "resting"
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(npc, "at_talked_to") as seam:
            result = _talk_freeform_adapter(
                self.player, {"npc_id": int(npc.pk), "speech": "你好"}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIn("她現在正忙著", result["message"])
        seam.assert_not_called()
        self.assertEqual(len(client.calls), 0)
        self.assertEqual(npc._chat_lines(self.player), [])

    # ------------------------------------------------------------------
    # explore.party_invite / explore.party_leave
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_accept_joins_and_notifies(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我願意與你同行。",
                intent={"kind": "party_invite", "accept": True},
            ),
        )
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg") as msg:
            result = await_result(
                _party_invite_adapter(
                    self.player, {"npc_id": int(npc.pk), "message": "你願意嗎？"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import JOINED_MESSAGE, is_companion

        self.assertTrue(is_companion(npc, self.player))
        texts = " ".join(str(call.args[0]) for call in msg.call_args_list if call.args)
        self.assertIn(JOINED_MESSAGE, texts)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_threshold_decides_with_no_client_call(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 70)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import is_companion

        self.assertTrue(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_below_threshold_rejects(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import is_companion

        self.assertFalse(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_threshold_is_gated_when_the_npc_becomes_busy(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 70)
        npc.db.schedule_state = "busy"
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        self.assertIn("無法交談", result["message"])
        from world.rules.party import is_companion

        self.assertFalse(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_full_party_rejects_before_the_ai_call(self):
        from world.rules.party import PARTY_MAX_COMPANIONS, join_party

        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(LLMNPC, key=f"同伴{index}", location=self.room1),
                self.player,
            )
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "party_full")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_already_companion_rejects_before_the_ai_call(self):
        from world.rules.party import join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        join_party(npc, self.player)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_companion")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_non_llm_npc_rejects(self):
        npc = create_object(NPC, key="普通村民", location=self.room1)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_dismisses_without_affinity_change(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change
        from world.rules.party import is_companion, join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 55)
        join_party(npc, self.player)
        before = npc.relations.affinity_for(self.player)
        result = _party_leave_adapter(
            self.player, {"npc_id": int(npc.pk)}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertFalse(is_companion(npc, self.player))
        self.assertIsNone(npc.db.party_member)
        self.assertEqual(npc.relations.affinity_for(self.player), before)

    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_unbound_target_rejects(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        result = _party_leave_adapter(
            self.player, {"npc_id": int(npc.pk)}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_companion")

    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_tampered_npc_id_rejects(self):
        result = _party_leave_adapter(self.player, {"npc_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")

    # ------------------------------------------------------------------
    # explore.engage
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-engage-delegates-to-the-existing-engage-contract")
    def test_engage_transitions_to_combat(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "success")
        # Engage clears the dialogue session inside the deterministic core, so
        # the partial update must re-render ``dialogue`` too (webclient-align-10).
        self.assertEqual(
            result["affected_panels"], ("status", "context_actions", "dialogue")
        )
        self.assertTrue(is_in_active_session(self.player))

    def test_engage_rejects_remote_or_dead_target_without_session(self):
        result = _engage_adapter(self.player, {"monster_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_monster")
        self.assertFalse(is_in_active_session(self.player))

        monster = create_object(Monster, key="死掉的哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.current = 0
        monster.save()
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "target_dead")
        self.assertFalse(is_in_active_session(self.player))

    def test_engage_already_in_combat_and_session_failures_are_rejected(self):
        first = create_object(Monster, key="哥布林甲", location=self.room1)
        first.threat_tier = "low"
        first.apply_monster_tier("floor")
        second = create_object(Monster, key="哥布林乙", location=self.room1)
        second.threat_tier = "low"
        second.apply_monster_tier("floor")
        engage(self.player, first)
        self.assertTrue(is_in_active_session(self.player))
        result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "already_in_combat")

        with patch(
            "web.webclient.actions.exploration_actions.engage",
            side_effect=CombatSessionError(SessionReason.NOT_PRESENT),
        ):
            result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "no_monster")

        with patch(
            "web.webclient.actions.exploration_actions.engage",
            side_effect=CombatSessionError("unexpected"),
        ):
            result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "engage_failed")

    # ------------------------------------------------------------------
    # explore.wait
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-practice-advances-the-clock-for-one-declared-skill")
    def test_practice_grows_only_the_declared_skill_and_plain_rest_grows_nothing(self):
        from web.webclient.actions.exploration_actions import _practice_adapter
        from world.rules.progression import practice_xp_amount
        from world.skills.registry import SKILL_REGISTRY

        self.player.db.skills = {"active": [_T_SKILL], "passive": []}
        self.player.db.skill_proficiency = {_T_SKILL: 20.0}
        before = get_world_clock().tick
        gain = 10 * practice_xp_amount(
            self.player, _live("world.skills.registry", "SKILL" + "_REGISTRY")[_T_SKILL]
        )
        result = _practice_adapter(self.player, {"skill": _T_SKILL, "seconds": 3600})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick, before + 3600)
        self.assertAlmostEqual(self.player.db.skill_proficiency[_T_SKILL], 20.0 + gain)
        self.assertIsNone(self.player.db.practice_booking)
        _wait_adapter(self.player, {"seconds": 3600})
        self.assertAlmostEqual(self.player.db.skill_proficiency[_T_SKILL], 20.0 + gain)

    @covers_requirement("webclient-exploration-menu::explore-practice-advances-the-clock-for-one-declared-skill")
    def test_practice_rejects_unknown_capped_and_unsafe_without_advancing(self):
        from web.webclient.actions.exploration_actions import _practice_adapter
        from world.rules.progression import proficiency_cap

        self.player.db.skills = {"active": [_T_SKILL], "passive": []}
        before = get_world_clock().tick
        result = _practice_adapter(self.player, {"skill": "unknown", "seconds": 3600})
        self.assertEqual(result["code"], "PRACTICE_SKILL_UNKNOWN")
        self.assertEqual(get_world_clock().tick, before)
        self.player.db.skill_proficiency = {_T_SKILL: proficiency_cap(_T_SKILL) * 50.0}
        result = _practice_adapter(self.player, {"skill": _T_SKILL, "seconds": 3600})
        self.assertEqual(result["code"], "PRACTICE_SKILL_CAPPED")
        self.assertEqual(get_world_clock().tick, before)
        monster = create_object(Monster, key="修煉阻擋者", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        result = _practice_adapter(self.player, {"skill": _T_SKILL, "seconds": 3600})
        self.assertEqual(result["code"], "unsafe_skip")
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("webclient-exploration-menu::explore-practice-advances-the-clock-for-one-declared-skill")
    def test_practice_payload_rejects_ambiguous_or_unbounded_requests(self):
        from web.webclient.actions.exploration_actions import validate_practice_payload

        for payload in (
            {"skill": _T_SKILL, "seconds": True},
            {"skill": _T_SKILL, "seconds": 43201},
            {"skill": _T_SKILL, "seconds": 0},
            {"skill": _T_SKILL, "seconds": 1, "sleep": True},
            {"skill": "fire arrow", "seconds": 1},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_practice_payload(payload)

    @covers_requirement("webclient-exploration-menu::explore-practice-advances-the-clock-for-one-declared-skill")
    def test_failed_practice_rolls_back_clock_growth_and_new_booking(self):
        from web.webclient.actions.exploration_actions import _practice_adapter

        self.player.db.skills = {"active": [_T_SKILL], "passive": []}
        self.player.db.skill_proficiency = {_T_SKILL: 20.0}
        before = get_world_clock().tick
        with patch("world.rules.clock._settle_boundary_stages", side_effect=RuntimeError("settlement failed")):
            result = _practice_adapter(self.player, {"skill": _T_SKILL, "seconds": 28800})
        self.assertEqual(result["code"], "skip_failed")
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.player.db.skill_proficiency[_T_SKILL], 20.0)
        self.assertIsNone(self.player.db.practice_booking)

    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_wait_until_dawn_advances_to_the_next_occurrence(self):
        from world.rules.clock import seconds_until_daypart

        get_world_clock()._persist(2 * 3600)  # 2:00
        expected = seconds_until_daypart(get_world_clock().calendar, "dawn")
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"daypart": "dawn"})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, expected)
        self.assertIn("時間經過了", result["message"])

    def test_wait_custom_duration_is_parsed_server_side(self):
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"seconds": 3600})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, 3600)

    def test_wait_sleep_uses_full_regen_and_is_bounded(self):
        from world.rules.time_skip import seconds_to_full_regen

        expected = seconds_to_full_regen(self.player)
        self.assertLessEqual(expected, MAX_WEB_SKIP_SECONDS)
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"sleep": True})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, expected)

    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_unsafe_skip_rejects_before_any_clock_advance(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"daypart": "dawn"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unsafe_skip")
        self.assertIn("怪物", result["message"])
        self.assertEqual(get_world_clock().tick, before)

    def test_unknown_daypart_and_skip_failure_are_rejected(self):
        result = _wait_adapter(self.player, {"daypart": "tea"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_daypart")
        with patch(
            "web.webclient.actions.exploration_actions.advance_skip",
            side_effect=RuntimeError("boom"),
        ):
            result = _wait_adapter(self.player, {"seconds": 60})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "skip_failed")


class DialogueSessionRecordingAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    """The talk adapters are the WS-side dialogue-session writers (align-07).

    Every case observes only the persisted ``db.dialogue_session`` — the
    state-only surface this change ships; the panel/mode land in
    webclient-align-10.
    """

    def setUp(self):
        _t_dialogue_scope(self)
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="對話.session測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.destination = create_object(Room, key="目的地", location=None)

    def tearDown(self):
        _reset_guardrail()
        super().tearDown()

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-session-is-deterministic-core-only-character-state"
    )
    def test_scripted_success_records_the_delivered_authored_line(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "success")
        stored = self.player.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertEqual(stored["npc_id"], int(host.pk))
        self.assertIn(_T_LODGE_LINE, stored["line"])
        self.assertIn(stored["line"], result["message"])

    def test_scripted_rejections_record_nothing(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "不存在的話題"}
        )
        self.assertEqual(result["code"], "unregistered_keyword")
        self.assertIsNone(self.player.db.dialogue_session)

    def test_freeform_settled_reply_records_the_presented_line(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我對你點頭。"))
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg"):
            result = await_result(
                _talk_freeform_adapter(
                    self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        stored = self.player.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertEqual(stored["npc_id"], int(npc.pk))
        self.assertEqual(stored["line"], "我對你點頭。")

    def test_freeform_authored_degrade_greeting_records(self):
        npc = create_object(LLMNPC, key="客棧老板娘", location=self.room1)
        npc.components.add(ScriptedDialogue.create(npc, dialogue_key=_T_DIALOGUE))
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ), patch.object(self.player, "msg"):
                result = await_result(
                    _talk_freeform_adapter(
                        self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        stored = self.player.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertIn(_T_LODGE_GREETING, stored["line"])

    def test_freeform_silent_degrade_records_nothing(self):
        npc = create_object(LLMNPC, key="無表精靈", location=self.room1)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ), patch.object(self.player, "msg"):
                result = await_result(
                    _talk_freeform_adapter(
                        self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self.player.db.dialogue_session)

    def test_freeform_mid_flight_stale_completion_records_nothing(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = _HeldClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg"):
            deferred = _talk_freeform_adapter(
                self.player, {"npc_id": int(npc.pk), "speech": "你好"}
            )
            self.player.location = self.destination
            client.deferred.callback(_reply_text(speech="我對你點頭。"))
            result = await_result(deferred)
        self.assertEqual(result["outcome"], "success")
        self.assertIn("離開", result["message"])
        self.assertIsNone(self.player.db.dialogue_session)


class DialogueLeaveAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    """``explore.dialogue_leave`` ends the live session through the sole writer
    and writes nothing on rejection (webclient-align-11)."""

    def setUp(self):
        _t_dialogue_scope(self)
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="對話.leave測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.host = create_object(NPC, key="客棧老板娘", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_T_DIALOGUE)
        )

    def tearDown(self):
        _reset_guardrail()
        super().tearDown()

    def _open_session(self) -> None:
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(self.host.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNotNone(self.player.db.dialogue_session)

    @covers_requirement(
        "webclient-dialogue-session::explore-dialogue-leave-ends-the-live-session-through-the-sole-writer"
    )
    def test_success_clears_the_session_and_only_the_session(self):
        self._open_session()
        with patch.object(self.player, "msg"):
            result = _dialogue_leave_adapter(
                self.player, {"npc_id": int(self.host.pk)}
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dialogue_left")
        self.assertIn("你結束了對話。", result["message"])
        self.assertIsNone(self.player.db.dialogue_session)
        # The full-snapshot affected set lets the dispatcher's completion
        # publish recompute the mode back to exploration.
        self.assertEqual(result["affected_panels"], ())

    def test_mismatched_npc_id_rejects_with_zero_writes(self):
        self._open_session()
        other = create_object(NPC, key="路人", location=self.room1)
        stored = self.player.db.dialogue_session
        result = _dialogue_leave_adapter(self.player, {"npc_id": int(other.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dialogue_inactive")
        self.assertEqual(self.player.db.dialogue_session, stored)

    def test_no_live_session_rejects(self):
        result = _dialogue_leave_adapter(self.player, {"npc_id": int(self.host.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dialogue_inactive")
        self.assertIsNone(self.player.db.dialogue_session)


class DeliverAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    """``explore.deliver`` re-resolves the recipient and delegates to the rule.

    The adapter trusts no client-supplied quest state (delta: the adapter
    re-resolves rather than trusting the client); the rule's refusal and
    outcome contracts are pinned in world.rules.tests.test_quest_delivery.
    """

    def setUp(self):
        # The delivery resolves the objective item's display name from the
        # item registry, so the kit item table rides a scoped registry.
        open_synthetic_scope(self, "items")
        from world.quests.binding import bind_stage_runtime
        from world.quests.tests._fixtures import accept, deliver, quest, register

        self.room1 = create_object(Room, key="交付房")
        self.player = create_object(PlayerCharacter, key="交付行動測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.recipient = create_object(NPC, key="灰婆婆", location=self.room1)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()

        definition = register(
            quest(
                "deliver_adapter_quest",
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=2)),),
            )
        )
        record = accept(self.player, definition)
        bind_stage_runtime(
            self.player, record.quest_id, objective_targets=(self.recipient,)
        )

    def test_missing_recipient_rejects_as_no_npc(self):
        result = _deliver_adapter(
            self.player, {"npc_id": 999999, "item_key": _T_ITEM}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")

    @covers_requirement(
        "quest-delivery::the-delivery-action-is-registered-with-an-exact-bounded-payload"
    )
    def test_success_delegates_to_the_shared_rule_and_reports_full_snapshot(self):
        self.player.db.inventory = [_T_ITEM, _T_ITEM]
        self.recipient.db.inventory = []
        with patch.object(self.player, "msg") as mock_msg:
            result = _deliver_adapter(
                self.player,
                {"npc_id": int(self.recipient.pk), "item_key": _T_ITEM},
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "delivered")
        self.assertEqual(result["affected_panels"], ())
        display_name = _live("world.lore.items", "ITEM" + "_REGISTRY")[
            _T_ITEM
        ].display_name_zh
        mock_msg.assert_called_once_with(f"你把 2 個{display_name}交給了灰婆婆。")
        from world.quests.runtime import QuestState, read_records

        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_rule_refusal_passes_through_unchanged(self):
        self.player.db.inventory = []
        result = _deliver_adapter(
            self.player,
            {"npc_id": int(self.recipient.pk), "item_key": _T_ITEM},
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "item_not_held")
        self.assertEqual(result["message"], "你沒有帶著足夠的任務物品。")

    @covers_requirement(
        "quest-delivery::the-delivery-action-is-registered-with-an-exact-bounded-payload"
    )
    def test_production_registry_binds_the_exact_spec(self):
        from web.webclient.actions.registry import build_production_action_registry

        registry = build_production_action_registry()
        spec = registry.spec("explore.deliver")
        self.assertIs(spec.validate_payload, validate_deliver_payload)
        self.assertIs(spec.adapter, _deliver_adapter)
        self.assertEqual(spec.affected_panels, ())


if __name__ == "__main__":
    unittest.main()
