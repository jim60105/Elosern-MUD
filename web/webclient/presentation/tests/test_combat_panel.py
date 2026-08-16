"""Exact ``context_actions`` schema and presenter tests (tasks 3.1-3.2)."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

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
from world.rules.tests.combat_fixtures import BattlefieldIsolation


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


def _valid_skill_group(**overrides):
    value = {
        "group": "fire",
        "label": "火",
        "skills": [_valid_skill()],
    }
    value.update(overrides)
    return value


def _valid_category_group(**overrides):
    value = {
        "category": "elemental_magic",
        "label": "元素魔法",
        "groups": [_valid_skill_group()],
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
        "schema_version": 3,
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
        "skills": [_valid_category_group()],
    }
    value.update(overrides)
    return value


def _recovery_panel(**overrides):
    value = {
        "schema_version": 3,
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
    def _nested_skills(self, *skills):
        """Wrap a flat skill list into one nested category group."""
        return [_valid_category_group(groups=[_valid_skill_group(skills=list(skills))])]

    def test_valid_ready_panel_passes(self):
        payload = _valid_panel()
        normalized = validate_context_actions(payload)
        self.assertEqual(normalized["schema_version"], CONTEXT_ACTIONS_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "combat")

    def test_sexual_act_group_key_accepts_a_chinese_line_name(self):
        # The act catalog keys sexual_act sub-groups by their Traditional
        # Chinese line names (獨處, 羞恥, 關係, 戰鬥); the group key is a
        # bounded string, not an ASCII identifier.
        panel = _valid_panel(
            skills=[
                _valid_category_group(
                    category="sexual_act",
                    label="性愛行為",
                    groups=[
                        _valid_skill_group(
                            group="獨處",
                            label="獨處",
                            skills=[_valid_skill(key="solo_self_touch")],
                        ),
                        _valid_skill_group(
                            group="戰鬥",
                            label="戰鬥",
                            skills=[_valid_skill(key="combat_tease")],
                        ),
                    ],
                )
            ]
        )
        normalized = validate_context_actions(panel)
        groups = normalized["skills"][0]["groups"]
        self.assertEqual([group["group"] for group in groups], ["獨處", "戰鬥"])

    def test_skill_group_key_rejects_empty_or_whitespace_strings(self):
        # The group key is a bounded non-empty string: empty and whitespace
        # keys are rejected, mirroring the character panel's group contract.
        for bad in ("", "   "):
            with self.subTest(group=bad):
                panel = _valid_panel(
                    skills=[
                        _valid_category_group(
                            category="sexual_act",
                            label="性愛行為",
                            groups=[
                                _valid_skill_group(
                                    group=bad,
                                    label="獨處",
                                )
                            ],
                        )
                    ]
                )
                with self.assertRaises(Exception):
                    validate_context_actions(panel)

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
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(shorthands=["all-enemies"]))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_rejects_disabled_skill_without_reason(self):
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(enabled=False, disabled_reason=None))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_rejects_enabled_skill_with_reason(self):
        panel = _valid_panel(
            skills=self._nested_skills(
                _valid_skill(disabled_reason={"code": "x", "message": "說明"})
            )
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_rejects_target_not_in_participants(self):
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(targets=[99]))
        )
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
        panel = _valid_panel(
            participants=participants, skills=self._nested_skills(*skills)
        )
        normalized = validate_context_actions(panel)
        self.assertLessEqual(json_byte_size(normalized), 65536)

    def test_duplicate_skill_and_target_are_rejected(self):
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(), _valid_skill())
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(targets=[2, 2]))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_duplicate_skill_across_categories_is_rejected(self):
        # The whole-payload unique-key check runs against the flattened set,
        # so a duplicate key hidden in two different categories is still
        # caught.
        panel = _valid_panel(
            skills=[
                _valid_category_group(),
                _valid_category_group(
                    category="martial_arts",
                    label="武技",
                    groups=[_valid_skill_group(group=None, label=None)],
                ),
            ]
        )
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
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(label=""))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(description="  "))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(cost={"mp": -1}))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(cost={"mp": True}))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(element=42))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(target_spec="cone"))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(targets=[0]))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(shorthands=["all", "all"]))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=self._nested_skills(_valid_skill(shorthands=["bogus"]))
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    def test_category_group_field_bounds_reject(self):
        # An unregistered category key is rejected.
        panel = _valid_panel(
            skills=[_valid_category_group(category="bogus")]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        # A null group key must pair with a null label and vice versa.
        panel = _valid_panel(
            skills=[
                _valid_category_group(
                    groups=[_valid_skill_group(group=None, label="火")]
                )
            ]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=[
                _valid_category_group(
                    groups=[_valid_skill_group(group="fire", label=None)]
                )
            ]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        # The top-level array is bounded by the number of SkillCategory
        # members, not by MAX_SKILLS.
        panel = _valid_panel(
            skills=[_valid_category_group() for _ in range(9)]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        # An empty groups array is rejected: empty categories are omitted,
        # not emitted empty.
        panel = _valid_panel(
            skills=[_valid_category_group(groups=[])]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_flattened_skill_count_bound_rejects_small_category_payload(self):
        # Design.md D-5: MAX_SKILLS applies to the flattened descriptor
        # total, not to the number of top-level category-group entries. A
        # hand-built payload with one category group carrying 33 skills must
        # be rejected even though its top-level count is far below
        # len(SkillCategory).
        skills = []
        for index in range(1, 34):
            skills.append(
                _valid_skill(
                    key=f"skill_{index}",
                    label=f"技能名稱{index}",
                    targets=[2],
                )
            )
        panel = _valid_panel(skills=self._nested_skills(*skills))
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

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_freeform_scales_field_is_optional_and_exact(self):
        # Absent field is accepted (the server omits it for non-masters).
        payload = _valid_panel()
        normalized = validate_context_actions(payload)
        normalized_skill = normalized["skills"][0]["groups"][0]["skills"][0]
        self.assertNotIn("freeform_scales", normalized_skill)

        payload = _valid_panel(
            skills=self._nested_skills(
                _valid_skill(
                    freeform_scales=[
                        {"scale": 0.25, "label": "1/4", "mp_cost": 5},
                        {"scale": 0.5, "label": "1/2", "mp_cost": 10},
                        {"scale": 1.0, "label": "1", "mp_cost": 20},
                        {"scale": 2.0, "label": "2", "mp_cost": 40},
                        {"scale": 4.0, "label": "4", "mp_cost": 80},
                    ]
                )
            )
        )
        normalized = validate_context_actions(payload)
        normalized_skill = normalized["skills"][0]["groups"][0]["skills"][0]
        self.assertEqual(
            normalized_skill["freeform_scales"][0]["mp_cost"],
            5,
        )

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_freeform_scales_malformed_entries_reject(self):
        valid_entries = [
            {"scale": 0.25, "label": "1/4", "mp_cost": 5},
            {"scale": 0.5, "label": "1/2", "mp_cost": 10},
            {"scale": 1.0, "label": "1", "mp_cost": 20},
            {"scale": 2.0, "label": "2", "mp_cost": 40},
            {"scale": 4.0, "label": "4", "mp_cost": 80},
        ]
        cases = {
            "non-member scale": [{"scale": 3.0, "label": "3", "mp_cost": 60}],
            "non-ascending": list(reversed(valid_entries)),
            "duplicate scale": valid_entries[:2] + valid_entries[1:3],
            "unknown label": [{"scale": 1.0, "label": "x", "mp_cost": 20}],
            "swapped label pairing": [
                {"scale": 0.25, "label": "4", "mp_cost": 5},
                {"scale": 0.5, "label": "1/2", "mp_cost": 10},
                {"scale": 1.0, "label": "1", "mp_cost": 20},
                {"scale": 2.0, "label": "2", "mp_cost": 40},
                {"scale": 4.0, "label": "1/4", "mp_cost": 80},
            ],
            "wrong mp_cost": [
                {"scale": 1.0, "label": "1", "mp_cost": 21}
            ],
            "partial set": valid_entries[:3],
            "empty array": [],
            "entry with extra key": [
                {"scale": 1.0, "label": "1", "mp_cost": 20, "extra": 1}
            ],
            "missing field": [{"scale": 1.0, "label": "1"}],
        }
        for name, entries in cases.items():
            with self.subTest(case=name):
                panel = _valid_panel(
                    skills=self._nested_skills(
                        _valid_skill(freeform_scales=entries)
                    )
                )
                with self.assertRaises(Exception):
                    validate_context_actions(panel)
        # A skill without an mp cost can never carry the field.
        panel = _valid_panel(
            skills=self._nested_skills(
                _valid_skill(cost={}, freeform_scales=valid_entries)
            )
        )
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


class ContextActionsPresenterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="panel arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": ["defense_instinct"]}
        self.monster = _monster()
        self.monster.location = self.room
        self.registry = build_production_registry()

    def _flatten_skills(self, payload):
        """Flatten the nested category groups back into one skill list."""
        return [
            skill
            for category in payload["skills"]
            for sub_group in category["groups"]
            for skill in sub_group["skills"]
        ]

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
        keys = [skill["key"] for skill in self._flatten_skills(payload)]
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

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_ready_session_groups_skills_by_category(self):
        self.player.db.skills = {
            "active": ["wind_blade", "fire_ball", "shadow_slash"],
            "passive": [],
        }
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertEqual(
            [category["category"] for category in payload["skills"]],
            ["elemental_magic", "martial_arts", "movement", "sexual_act"],
        )
        self.assertEqual(payload["skills"][0]["label"], "元素魔法")
        elemental = payload["skills"][0]
        self.assertEqual(
            [sub_group["group"] for sub_group in elemental["groups"]],
            ["fire", "wind"],
        )
        wind = elemental["groups"][1]
        self.assertEqual(wind["label"], "風")
        self.assertEqual(
            [skill["key"] for skill in wind["skills"]],
            ["wind_blade"],
        )
        martial = payload["skills"][1]
        self.assertEqual(martial["label"], "武技")
        self.assertEqual(len(martial["groups"]), 1)
        self.assertIsNone(martial["groups"][0]["group"])
        self.assertIsNone(martial["groups"][0]["label"])
        # The seven unconditionally-owned seed acts form the sexual_act
        # category with their Chinese line names as sub-group keys, in
        # first-seen group order (sorted seed keys: combat_tease first).
        sexual = payload["skills"][3]
        self.assertEqual(sexual["label"], "性愛行為")
        self.assertEqual(
            [sub_group["group"] for sub_group in sexual["groups"]],
            ["戰鬥", "關係", "羞恥", "獨處"],
        )
        # shadow_slash is stored before the innate basic_attack.
        self.assertEqual(
            [skill["key"] for skill in martial["groups"][0]["skills"]],
            ["shadow_slash", "basic_attack"],
        )
        movement = payload["skills"][2]
        self.assertEqual(movement["label"], "移動")
        self.assertEqual(
            [skill["key"] for skill in movement["groups"][0]["skills"]],
            ["flee"],
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
        fire = next(
            skill
            for skill in self._flatten_skills(payload)
            if skill["key"] == "fire_ball"
        )
        self.assertFalse(fire["enabled"])
        self.assertEqual(fire["disabled_reason"]["code"], "insufficient_resource")
        self.assertTrue(fire["disabled_reason"]["message"].strip())

    @covers_requirement("webclient-combat-menu::combat-menu-availability-reflects-handler-context")
    def test_context_requiring_skills_are_disabled_in_the_menu(self):
        self.player.db.skills = {
            "active": ["status_disguise", "dominion_art"],
            "passive": [],
        }
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        by_key = {skill["key"]: skill for skill in self._flatten_skills(payload)}
        for skill_key in ("status_disguise", "dominion_art"):
            with self.subTest(skill_key=skill_key):
                skill = by_key[skill_key]
                self.assertFalse(skill["enabled"])
                self.assertEqual(
                    skill["disabled_reason"]["code"],
                    "missing_effect_context",
                )
                self.assertTrue(skill["disabled_reason"]["message"].strip())

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_panel_advertises_freeform_scales_only_for_masters(self):
        self.player.db.skills = {
            "active": ["wind_blade", "gale_step"],
            "passive": ["wind_mastery"],
        }
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        by_key = {skill["key"]: skill for skill in self._flatten_skills(payload)}
        wind = by_key["wind_blade"]
        self.assertEqual(
            wind["freeform_scales"],
            [
                {"scale": 0.25, "label": "1/4", "mp_cost": 4},
                {"scale": 0.5, "label": "1/2", "mp_cost": 7},
                {"scale": 1.0, "label": "1", "mp_cost": 14},
                {"scale": 2.0, "label": "2", "mp_cost": 28},
                {"scale": 4.0, "label": "4", "mp_cost": 56},
            ],
        )
        self.assertNotIn("freeform_scales", by_key["gale_step"])

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_non_master_panel_reveals_nothing(self):
        self.player.db.skills = {
            "active": ["wind_blade"],
            "passive": [],
        }
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        for skill in self._flatten_skills(payload):
            self.assertNotIn("freeform_scales", skill)
        self.assertNotIn("威力", repr(payload["skills"]))

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
                {
                    "art",
                    "status",
                    "context_actions",
                    "local_map",
                    "services",
                    "creation",
                    "exploration",
                    "character",
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
