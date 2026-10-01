"""Tests for the 編輯人物設定 exploration entry affordance and presentation boundaries."""

import json
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.exploration import (
    MAX_AFFORDANCES,
    MAX_INTERACT_TARGETS,
    SURFACES,
    exploration_presenter,
    validate_exploration,
)
from web.webclient.presentation.protocol import ProtocolValidationError
from world.rules.clock import get_world_clock
from world.rules.npc_persona import initialize_npc_persona, is_card_available


class ExplorationNpcPersonaAffordanceTest(EvenniaTest):
    def setUp(self):
        super().setUp()
        get_world_clock()
        self.room = create_object(Room, key="探索展示間")
        self.player = create_object(PlayerCharacter, key="探索玩家")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room

        self.valid_card = {
            "identity": {"public": "店小二", "hidden": ""},
            "appearance": "樸實俐落。",
            "personality": "熱情機靈。",
            "speech_style": "客氣得體。",
            "life_story": "在店裡幫忙三年。",
            "habit": "隨時拿抹布。",
            "social_connection": "",
        }

    def _context(self, actor=None):
        return PresentationContext(
            actor=actor or self.player,
            protocol_version=1,
        )

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_affordance_enabled_for_valid_card_disabled_for_uninitialized_absent_for_monster(self):
        # 1. Valid card NPC
        npc_valid = create_object(NPC, key="合格NPC")
        npc_valid.location = self.room
        initialize_npc_persona(npc_valid, self.valid_card, {"kind": "profile", "profile": "npc_ok"})

        # 2. Uninitialized NPC
        npc_uninit = create_object(NPC, key="未初始化NPC")
        npc_uninit.location = self.room

        # 3. Monster
        monster = create_object(Monster, key="野狼")
        monster.location = self.room

        payload = exploration_presenter(self._context())
        validated = validate_exploration(payload)

        targets_by_id = {t["identity"]: t for t in validated["interact"]}

        # Monster has no npc_persona affordance
        monster_target = targets_by_id[monster.id]
        monster_surfaces = [a.get("surface") for a in monster_target["affordances"] if a["kind"] == "navigate"]
        self.assertNotIn("npc_persona", monster_surfaces)

        # Valid NPC has enabled npc_persona affordance as last entry
        valid_target = targets_by_id[npc_valid.id]
        self.assertTrue(len(valid_target["affordances"]) >= 1)
        last_aff = valid_target["affordances"][-1]
        self.assertEqual(last_aff["kind"], "navigate")
        self.assertEqual(last_aff["surface"], "npc_persona")
        self.assertEqual(last_aff["label"], "編輯人物設定")
        self.assertTrue(last_aff["enabled"])
        self.assertIsNone(last_aff["disabled_reason"])

        # Uninitialized NPC has disabled npc_persona affordance with npc_persona.unavailable
        uninit_target = targets_by_id[npc_uninit.id]
        last_uninit = uninit_target["affordances"][-1]
        self.assertEqual(last_uninit["kind"], "navigate")
        self.assertEqual(last_uninit["surface"], "npc_persona")
        self.assertFalse(last_uninit["enabled"])
        self.assertEqual(last_uninit["disabled_reason"]["code"], "npc_persona.unavailable")

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_possessed_actor_gets_possession_reason_and_silent_check(self):
        npc = create_object(NPC, key="被附身看守者")
        npc.location = self.room
        initialize_npc_persona(npc, self.valid_card, {"kind": "profile", "profile": "npc_ok"})

        with patch("world.rules.possession.is_possessed_actor", return_value=True), \
             patch("world.observability.log_warn") as mock_warn:
            payload = exploration_presenter(self._context())
            target = payload["interact"][0]
            aff = target["affordances"][-1]
            self.assertEqual(aff["surface"], "npc_persona")
            self.assertFalse(aff["enabled"])
            self.assertEqual(aff["disabled_reason"]["code"], "possessed_talk")
            # Verify silent check: no warning logged
            mock_warn.assert_not_called()

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-3-presentation-panel")
    def test_version_3_validator_accepts_surface_and_rejects_extra_fields(self):
        self.assertIn("npc_persona", SURFACES)
        valid_row = {
            "kind": "navigate",
            "surface": "npc_persona",
            "label": "編輯人物設定",
            "enabled": True,
            "disabled_reason": None,
        }
        npc = create_object(NPC, key="驗證NPC")
        npc.location = self.room
        initialize_npc_persona(npc, self.valid_card, {"kind": "profile", "profile": "npc_ok"})

        payload = exploration_presenter(self._context())
        validated = validate_exploration(payload)
        self.assertEqual(validated["schema_version"], 3)

        # Extra field on navigate affordance rejects
        bad_payload = dict(payload)
        bad_target = dict(bad_payload["interact"][0])
        bad_target["affordances"] = list(bad_target["affordances"])
        bad_target["affordances"][-1] = {**valid_row, "extra_field": "illegal"}
        bad_payload["interact"] = [bad_target]
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(bad_payload)

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-3-presentation-panel")
    def test_maximal_room_fixture_fits_envelope(self):
        # 32 NPC targets * 8 affordances with maximal names
        interact_targets = []
        for i in range(MAX_INTERACT_TARGETS):
            affordances = []
            for j in range(MAX_AFFORDANCES - 1):
                affordances.append({
                    "kind": "navigate",
                    "surface": "shop" if j % 2 == 0 else "guild",
                    "label": "超長導航標籤測試文字" * 2,
                    "enabled": True,
                    "disabled_reason": None,
                })
            affordances.append({
                "kind": "navigate",
                "surface": "npc_persona",
                "label": "編輯人物設定",
                "enabled": True,
                "disabled_reason": None,
            })
            interact_targets.append({
                "identity": i + 1,
                "display_name": "極限長度名稱測試用角色" * 2,
                "portrait_ref": None,
                "affordances": affordances,
            })

        max_payload = {
            "schema_version": 3,
            "available": True,
            "kind": "exploration",
            "move": [],
            "look": {
                "room": {"identity": 100, "display_name": "宏偉宮殿大廳", "room": True},
                "entities": [],
                "objects": [],
            },
            "interact": interact_targets,
            "character": {"available": True},
            "quests": {"available": True},
            "inventory": {"available": True},
        }
        validated = validate_exploration(max_payload)
        self.assertEqual(len(validated["interact"]), MAX_INTERACT_TARGETS)
        self.assertEqual(len(validated["interact"][0]["affordances"]), MAX_AFFORDANCES)
