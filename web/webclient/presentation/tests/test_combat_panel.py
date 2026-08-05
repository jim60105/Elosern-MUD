"""Exact ``context_actions`` schema and presenter tests (tasks 3.1-3.2)."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.presentation.combat_panel import (
    CONTEXT_ACTIONS_SCHEMA_VERSION,
    validate_context_actions,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import json_byte_size
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from world.rules.combat_session import engage


def _valid_skill(**overrides):
    value = {
        "key": "fire_ball",
        "label": "火球術",
        "description": "凝聚火焰魔力，對單一敵人造成魔法傷害。",
        "cost": {"mp": 20},
        "target_spec": "single",
        "element": "fire",
        "enabled": True,
        "disabled_reason": None,
        "targets": [2],
        "shorthands": [],
    }
    value.update(overrides)
    return value


def _valid_participant(**overrides):
    value = {
        "identity": 2,
        "token": "e1",
        "display_name": "goblin",
        "team": "foes",
        "state": "active",
        "hp_current": 100,
        "hp_maximum": 100,
        "portrait_ref": None,
    }
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": 2,
        "available": True,
        "kind": "combat",
        "session": {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "round": 0,
            "state": "ready",
            "reason": None,
        },
        "participants": [_valid_participant()],
        "root_actions": ["attack", "skills", "items", "defend", "flee"],
        "secondary_actions": ["forfeit"],
        "skills": [_valid_skill()],
    }
    value.update(overrides)
    return value


def _recovery_panel(**overrides):
    value = {
        "schema_version": 2,
        "available": True,
        "kind": "combat",
        "session": {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "round": 2,
            "state": "recovery",
            "reason": {"code": "missing_participant", "message": "戰鬥成員已無法確認。"},
        },
        "participants": [],
        "root_actions": [],
        "secondary_actions": ["forfeit"],
        "skills": [],
    }
    value.update(overrides)
    return value


class ContextActionsSchemaTests(unittest.TestCase):
    def test_valid_ready_panel_passes(self):
        payload = _valid_panel()
        normalized = validate_context_actions(payload)
        self.assertEqual(normalized["schema_version"], CONTEXT_ACTIONS_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "combat")

    def test_valid_recovery_panel_passes(self):
        normalized = validate_context_actions(_recovery_panel())
        self.assertEqual(normalized["session"]["state"], "recovery")
        self.assertEqual(normalized["secondary_actions"], ["forfeit"])

    def test_rejects_unknown_fields_and_missing_fields(self):
        payload = _valid_panel()
        payload["bogus"] = 1
        with self.assertRaises(Exception):
            validate_context_actions(payload)

        payload = _valid_panel()
        del payload["skills"]
        with self.assertRaises(Exception):
            validate_context_actions(payload)

    def test_rejects_wrong_availability_and_kind(self):
        payload = _valid_panel()
        payload["available"] = False
        with self.assertRaises(Exception):
            validate_context_actions(payload)

        payload = _valid_panel()
        payload["kind"] = "exploration"
        with self.assertRaises(Exception):
            validate_context_actions(payload)

    def test_session_requires_reason_rules(self):
        ready = _valid_panel()
        ready["session"]["reason"] = {"code": "x", "message": "說明"}
        with self.assertRaises(Exception):
            validate_context_actions(ready)

        recovery = _recovery_panel()
        recovery["session"]["reason"] = None
        with self.assertRaises(Exception):
            validate_context_actions(recovery)

    def test_rejects_non_null_portrait_ref(self):
        panel = _valid_panel()
        panel["participants"][0]["portrait_ref"] = "https://example.test/a.png"
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_accepts_decimal_portrait_ref_and_null(self):
        panel = _valid_panel()
        panel["participants"][0]["portrait_ref"] = "42"
        normalized = validate_context_actions(panel)
        self.assertEqual(normalized["participants"][0]["portrait_ref"], "42")
        panel = _valid_panel()
        panel["participants"][0]["portrait_ref"] = None
        validate_context_actions(panel)

    def test_rejects_malformed_portrait_ref(self):
        for value in ("abc", "4.2", "42a", "a" * 33, True, 42):
            panel = _valid_panel()
            panel["participants"][0]["portrait_ref"] = value
            with self.assertRaises(Exception):
                validate_context_actions(panel)

    def test_rejects_skill_shorthand_on_single(self):
        panel = _valid_panel()
        panel["skills"][0]["shorthands"] = ["all-enemies"]
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_rejects_disabled_skill_without_reason(self):
        panel = _valid_panel()
        panel["skills"][0]["enabled"] = False
        panel["skills"][0]["disabled_reason"] = None
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_rejects_enabled_skill_with_reason(self):
        panel = _valid_panel()
        panel["skills"][0]["disabled_reason"] = {"code": "x", "message": "說明"}
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_rejects_target_not_in_participants(self):
        panel = _valid_panel()
        panel["skills"][0]["targets"] = [99]
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_recovery_rejects_root_actions(self):
        panel = _recovery_panel()
        panel["root_actions"] = ["attack"]
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_worst_case_envelope_fits_protocol_limit(self):
        participants = []
        for index in range(1, 17):
            participants.append(
                _valid_participant(
                    identity=index,
                    token=f"e{index}",
                    display_name=f"怪物名稱{index}",
                )
            )
        skills = []
        for index in range(1, 33):
            skills.append(
                _valid_skill(
                    key=f"skill_{index}",
                    label=f"技能名稱{index}",
                    description="很長的效果說明。" * 20,
                    cost={"mp": 100, "sp": 50},
                    target_spec="area",
                    targets=[i for i in range(1, 17)],
                    shorthands=["all-enemies", "all-allies", "all"],
                )
            )
        panel = _valid_panel(participants=participants, skills=skills)
        normalized = validate_context_actions(panel)
        self.assertLessEqual(json_byte_size(normalized), 65536)

    def test_duplicate_skill_and_target_are_rejected(self):
        panel = _valid_panel()
        panel["skills"].append(_valid_skill())
        with self.assertRaises(Exception):
            validate_context_actions(panel)

        panel = _valid_panel()
        panel["skills"][0]["targets"] = [2, 2]
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_participant_token_and_field_bounds_reject(self):
        panel = _valid_panel()
        panel["participants"][0]["token"] = "x1"
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["participants"][0]["token"] = 5
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["participants"][0]["token"] = "e1" * 30
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_session_field_bounds_reject(self):
        panel = _valid_panel()
        panel["session"]["session_id"] = "  "
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["session"]["mode"] = "arena"
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["session"]["state"] = "paused"
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["session"]["round"] = -1
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_participant_state_and_team_bounds_reject(self):
        panel = _valid_panel()
        panel["participants"][0]["team"] = "spectator"
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["participants"][0]["state"] = "teleporting"
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["participants"][0]["hp_current"] = -1
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["participants"][0]["hp_current"] = 999
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["participants"][0]["display_name"] = ""
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_skill_field_bounds_reject(self):
        panel = _valid_panel()
        panel["skills"][0]["label"] = ""
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["description"] = "  "
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["cost"] = {"mp": -1}
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["cost"] = {"mp": True}
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["element"] = 42
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["target_spec"] = "cone"
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["targets"] = [0]
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["shorthands"] = ["all", "all"]
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["skills"][0]["shorthands"] = ["bogus"]
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_actions_key_bounds_reject(self):
        panel = _valid_panel()
        panel["root_actions"].append("extra")
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["root_actions"] = ["attack"]
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel()
        panel["secondary_actions"] = ["forfeit", "forfeit"]
        with self.assertRaises(Exception):
            validate_context_actions(panel)


def _player(key="panel player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _monster(key="panel goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class ContextActionsPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="panel arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": ["defense_instinct"]}
        self.monster = _monster()
        self.monster.location = self.room
        self.registry = build_production_registry()

    @covers_requirement("webclient-combat-menu::combat-context-actions-are-an-exact-read-only-panel")
    def test_ready_session_presents_canonical_combat_choices(self):
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "combat")
        self.assertEqual(payload["session"]["mode"], "hostile")
        self.assertEqual(payload["session"]["round"], 0)
        self.assertEqual(payload["session"]["state"], "ready")
        self.assertEqual(payload["root_actions"], ["attack", "skills", "items", "defend", "flee"])
        self.assertEqual(payload["secondary_actions"], ["forfeit"])
        self.assertEqual(
            [p["identity"] for p in payload["participants"]],
            [self.player.pk, self.monster.pk],
        )
        self.assertEqual(
            [p["token"] for p in payload["participants"]],
            ["a1", "e1"],
        )
        keys = [skill["key"] for skill in payload["skills"]]
        self.assertIn("fire_ball", keys)
        self.assertIn("basic_attack", keys)
        self.assertIn("flee", keys)
        self.assertNotIn("defense_instinct", keys)
        self.assertEqual(
            [p["portrait_ref"] for p in payload["participants"]],
            [str(self.player.pk), str(self.monster.pk)],
        )
        self.assertEqual(
            [p["portrait_ref"] for p in payload["participants"]],
            [str(p["identity"]) for p in payload["participants"]],
        )

    @covers_requirement("webclient-combat-menu::combat-context-actions-are-an-exact-read-only-panel")
    def test_exploration_uses_unavailable_form_without_fabrication(self):
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "presentation_unavailable")
        self.assertNotIn("skills", payload)
        self.assertNotIn("attack", repr(payload))

    def test_presenter_is_read_only(self):
        engage(self.player, self.monster)
        before = {
            "player_hp": self.player.traits.hp.current,
            "monster_hp": self.monster.traits.hp.current,
            "rounds": self.player.db.active_combat["rounds_elapsed"],
        }
        self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        after = {
            "player_hp": self.player.traits.hp.current,
            "monster_hp": self.monster.traits.hp.current,
            "rounds": self.player.db.active_combat["rounds_elapsed"],
        }
        self.assertEqual(before, after)

    def test_disabled_skill_appears_with_stable_reason(self):
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        fire = next(skill for skill in payload["skills"] if skill["key"] == "fire_ball")
        self.assertFalse(fire["enabled"])
        self.assertEqual(fire["disabled_reason"]["code"], "insufficient_resource")
        self.assertTrue(fire["disabled_reason"]["message"].strip())

    def test_presenter_isolation_on_missing_session(self):
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertFalse(payload["available"])

    def test_production_registry_contains_every_registered_panel(self):
        self.assertEqual(
            self.registry.panel_names,
            frozenset(
                {"art", "status", "context_actions", "local_map", "services", "creation"}
            ),
        )


if __name__ == "__main__":
    unittest.main()
