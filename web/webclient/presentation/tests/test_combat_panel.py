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
    ContextActionsError,
    validate_context_actions,
)
from web.webclient.presentation.context import (
    FrozenCard,
    OptionsSnapshot,
    PresentationContext,
)
from web.webclient.presentation.options import (
    MAX_OPTION_CARDS,
    MAX_OPTION_HINT,
    MAX_OPTION_LABEL,
    MAX_OPTION_PARAMS,
    OPTIONS_CARD_KINDS,
    OPTIONS_STATUSES,
    validate_suggestions,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_LIST_ITEMS,
    ProtocolValidationError,
    check_envelope,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from world.rules.combat_session import engage
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage


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
        "schema_version": 5,
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
        "suggestions": {"status": "unavailable"},
    }
    value.update(overrides)
    return value


def _recovery_panel(**overrides):
    value = {
        "schema_version": 5,
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
        "suggestions": {"status": "unavailable"},
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
        # hand-built payload whose flattened total is 193 must be rejected
        # even though its top-level count is far below len(SkillCategory).
        # Skills are spread across sub-groups so each group stays within the
        # global MAX_LIST_ITEMS bound — the flattened total, not any single
        # array, is what exceeds MAX_SKILLS.
        skills_by_group = []
        for group in range(3):
            count = 65 if group == 2 else 64
            skills_by_group.append(
                _valid_skill_group(
                    group=f"group_{group}",
                    label=f"群組{group}",
                    skills=[
                        _valid_skill(
                            key=f"skill_{group * 64 + index}",
                            label=f"技能名稱{group * 64 + index}",
                            targets=[2],
                        )
                        for index in range(1, count + 1)
                    ],
                )
            )
        panel = _valid_panel(
            skills=[_valid_category_group(groups=skills_by_group)]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)

        # 192 skills across the same shape still passes.
        skills_by_group[2]["skills"].pop()
        panel = _valid_panel(
            skills=[_valid_category_group(groups=skills_by_group)]
        )
        validate_context_actions(panel)
        # The 192-skill payload also satisfies the global envelope safety the
        # real client applies before panel validation: every array stays
        # within MAX_LIST_ITEMS and the canonical JSON fits the byte bound.
        check_envelope(panel)
        for group in panel["skills"][0]["groups"]:
            self.assertLessEqual(len(group["skills"]), MAX_LIST_ITEMS)
        self.assertLessEqual(json_byte_size(panel), MAX_CANONICAL_JSON_BYTES)

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
            "missing the 0.25 prefix": valid_entries[2:],
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


def _exploration_panel(**overrides):
    value = {
        "schema_version": 5,
        "available": True,
        "kind": "exploration",
        "affordances": [
            {
                "action_id": "explore.look",
                "label": "南門",
                "params": {"room": True},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            },
            {
                "action_id": "explore.talk_scripted",
                "label": "註冊",
                "params": {"npc_id": 5, "keyword_id": "註冊"},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            },
            {
                "surface": "guild",
                "label": "公會服務",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
            },
        ],
        "suggestions": {"status": "unavailable"},
    }
    value.update(overrides)
    return value


def _suggestion_card(**overrides):
    value = {
        "kind": "known_action",
        "action_code": "explore.look",
        "label": "查看房間",
        "params": {"room": True},
    }
    value.update(overrides)
    return value


def _ready_suggestions(count=3):
    cards = [
        _suggestion_card(),
        _suggestion_card(action_code="explore.wait", label="等待片刻", params={"daypart": "noon"}),
        _suggestion_card(label="查看木箱", params={"target_id": 9}),
        _suggestion_card(label="前往東邊", params={"target_id": 9}),
        _suggestion_card(label="查看南門", params={"target_id": 9}),
        _suggestion_card(label="查看北門", params={"target_id": 9}),
    ]
    return {"status": "ready", "cards": cards[:count]}


class ContextActionsExplorationFormTests(unittest.TestCase):
    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-5-panel")
    def test_valid_exploration_form_passes(self):
        normalized = validate_context_actions(_exploration_panel())
        self.assertEqual(normalized["schema_version"], CONTEXT_ACTIONS_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "exploration")
        self.assertEqual(normalized["affordances"][0]["params"], {"room": True})
        self.assertEqual(
            normalized["affordances"][1]["params"],
            {"npc_id": 5, "keyword_id": "註冊"},
        )
        self.assertTrue(normalized["affordances"][2]["navigation"])
        self.assertNotIn("surface", normalized["affordances"][0])
        self.assertNotIn("action_id", normalized["affordances"][2])

    def test_combat_fields_in_the_exploration_form_reject(self):
        payload = _exploration_panel(session={"session_id": "x"}, skills=[])
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(payload)

    def test_exploration_fields_in_the_combat_form_reject(self):
        payload = _valid_panel(affordances=[_exploration_panel()["affordances"][0]])
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(payload)

    def test_wrong_kind_and_version_reject(self):
        with self.assertRaises(Exception):
            validate_context_actions(_exploration_panel(kind="combat"))
        with self.assertRaises(ContextActionsError):
            validate_context_actions(_exploration_panel(schema_version=4))
        with self.assertRaises(Exception):
            validate_context_actions(_exploration_panel(kind="bogus"))

    def test_affordance_bounds_reject(self):
        from web.webclient.presentation.combat_panel import MAX_CONTEXT_AFFORDANCES

        payload = _exploration_panel(
            affordances=[_exploration_panel()["affordances"][0]]
            * (MAX_CONTEXT_AFFORDANCES + 1)
        )
        with self.assertRaises(ContextActionsError):
            validate_context_actions(payload)
        payload = _exploration_panel(affordances=42)
        with self.assertRaises(Exception):
            validate_context_actions(payload)

    def test_affordance_entry_shapes_reject(self):
        valid = _exploration_panel()["affordances"][0]
        cases = (
            {**valid, "action_id": "explore.take"},
            {**valid, "action_id": "explore.interact"},
            {**valid, "freeform": "yes"},
            {**valid, "freeform": True},
            {
                **valid,
                "action_id": "explore.talk_freeform",
                "freeform": False,
                "params": {"npc_id": 9},
            },
            {**valid, "params": {"room": "yes"}},
            {**valid, "params": {"room": True, "extra": 1}},
            {**valid, "label": " "},
            {**valid, "enabled": False, "disabled_reason": None},
            {**valid, "enabled": True, "disabled_reason": {"code": "x", "message": "說明"}},
            {**valid, "navigation": "false"},
            {**valid, "navigation": True},
            {
                "surface": "bank",
                "label": "公會",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
            },
            {
                "surface": "guild",
                "label": "公會服務",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
                "action_id": "explore.look",
            },
            {
                "action_id": "explore.look",
                "label": "南門",
                "params": {"room": True},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
                "surface": "guild",
            },
            {**valid, "params": "room"},
            {**valid, "params": {"room": True, "target_id": 1}},
        )
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(Exception):
                    validate_context_actions(_exploration_panel(affordances=[payload]))

    def test_freeform_entry_params_are_exactly_the_binding_shape(self):
        valid = _exploration_panel()["affordances"][0]
        entry = {
            **valid,
            "action_id": "explore.talk_freeform",
            "freeform": True,
            "params": {"npc_id": 9},
        }
        normalized = validate_context_actions(_exploration_panel(affordances=[entry]))
        self.assertEqual(normalized["affordances"][0]["params"], {"npc_id": 9})
        for bad in (
            {**entry, "params": {"npc_id": 9, "speech": "你好"}},
            {**entry, "params": {"npc_id": 0}},
            {**entry, "params": {}},
        ):
            with self.assertRaises(Exception):
                validate_context_actions(_exploration_panel(affordances=[bad]))

    def test_combat_form_is_byte_identical_to_version_4_plus_suggestions(self):
        version4 = {
            "schema_version": 4,
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
        version5 = _valid_panel()
        self.assertEqual(version4["schema_version"], 4)
        self.assertEqual(version5["schema_version"], 5)
        # Every combat field serializes exactly as at version 4; only the
        # version field and the suggestions envelope are added.
        self.assertEqual(
            {
                key: value
                for key, value in version5.items()
                if key not in ("schema_version", "suggestions")
            },
            {
                key: value
                for key, value in version4.items()
                if key != "schema_version"
            },
        )
        self.assertEqual(version5["suggestions"], {"status": "unavailable"})
        normalized = validate_context_actions(version5)
        self.assertEqual(normalized["schema_version"], 5)
        self.assertEqual(normalized["session"], version4["session"])
        self.assertEqual(normalized["participants"], version4["participants"])
        self.assertEqual(normalized["root_actions"], version4["root_actions"])
        self.assertEqual(normalized["secondary_actions"], version4["secondary_actions"])
        self.assertEqual(normalized["skills"], version4["skills"])
        self.assertEqual(normalized["suggestions"], {"status": "unavailable"})
        # A version-4 payload is rejected by the version-5 validator.
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(version4)

    def test_over_envelope_exploration_form_fails_closed(self):
        wide = "寬" * 128
        affordances = [
            {
                "action_id": "explore.look",
                "label": wide,
                "params": {"room": True},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            }
            for _ in range(320)
        ]
        with self.assertRaises(ContextActionsError):
            validate_context_actions(
                _exploration_panel(affordances=affordances)
            )

    def test_unavailable_form_differs_only_in_schema_version(self):
        from web.webclient.presentation.protocol import unavailable_payload

        version4 = unavailable_payload(4, "presentation_unavailable", "目前無法顯示此介面")
        version5 = unavailable_payload(5, "presentation_unavailable", "目前無法顯示此介面")
        self.assertEqual(
            {key: value for key, value in version5.items() if key != "schema_version"},
            {key: value for key, value in version4.items() if key != "schema_version"},
        )
        self.assertEqual(version5["schema_version"], 5)
        # The common unavailable form carries exactly schema_version,
        # available, and reason — never a suggestions field (design D-1
        # amendment; the shared builder in presentation/registry.py is
        # unchanged).
        self.assertEqual(
            set(version5),
            {"schema_version", "available", "reason"},
        )
        self.assertNotIn("suggestions", version5)


class SuggestionsEnvelopeTests(unittest.TestCase):
    """Per-status suggestions schema tests (tasks 1.3-1.4)."""

    @covers_requirement("webclient-context-actions-suggestions::the-context-actions-panel-carries-a-suggestions-envelope-at-version-5")
    def test_generating_and_unavailable_carry_only_status(self):
        for status in ("generating", "unavailable"):
            with self.subTest(status=status):
                normalized = validate_context_actions(
                    _exploration_panel(suggestions={"status": status})
                )
                self.assertEqual(normalized["suggestions"], {"status": status})

    def test_unknown_status_rejects(self):
        for status in ("bogus", "", 1, None):
            with self.subTest(status=status):
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions={"status": status, "cards": []})
                    )

    def test_generating_and_unavailable_reject_cards_and_extra_keys(self):
        for status in ("generating", "unavailable"):
            with self.subTest(status=status):
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions={"status": status, "cards": []})
                    )
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions={"status": status, "extra": 1})
                    )

    def test_ready_and_degraded_require_both_fields(self):
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(_exploration_panel(suggestions={"status": "ready"}))
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(suggestions={"status": "degraded"})
            )
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(suggestions={"status": "ready", "cards": [], "extra": 1})
            )

    def test_ready_count_bound_rejects(self):
        for count in (0, 1, 2, 6):
            with self.subTest(count=count):
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions=_ready_suggestions(count))
                    )

    def test_degraded_count_bound_accepts_zero_and_rejects_over_cap(self):
        normalized = validate_context_actions(
            _exploration_panel(suggestions={"status": "degraded", "cards": []})
        )
        self.assertEqual(normalized["suggestions"], {"status": "degraded", "cards": []})
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(
                    suggestions={"status": "degraded", "cards": [_suggestion_card()] * 6}
                )
            )

    def test_ready_suggestions_accept_and_normalize(self):
        payload = _ready_suggestions()
        normalized = validate_context_actions(_exploration_panel(suggestions=payload))
        self.assertEqual(normalized["suggestions"]["status"], "ready")
        self.assertEqual(len(normalized["suggestions"]["cards"]), 3)
        self.assertEqual(normalized["suggestions"]["cards"][0]["params"], {"room": True})
        self.assertEqual(
            normalized["suggestions"]["cards"][1]["params"],
            {"daypart": "noon"},
        )

    @covers_requirement("webclient-context-actions-suggestions::suggestion-cards-are-a-bounded-closed-exact-shape")
    def test_card_exact_keys_reject(self):
        valid = _suggestion_card()
        cases = (
            {**valid, "extra": 1},
            {k: v for k, v in valid.items() if k != "params"},
            {**valid, "kind": "bogus"},
            {**valid, "action_code": "explore.take"},
            {**valid, "action_code": "explore.talk_freeform"},
            {**valid, "label": " "},
            {**valid, "label": "abc"},
            {**valid, "label": "很" * 25},
            {**valid, "hint": "很" * 61},
            {**valid, "params": {"room": True, "extra": 1}},
            {**valid, "params": {"room": False}},
            {**valid, "params": {"room": "yes"}},
            {**valid, "params": {"target_id": 0}},
            {**valid, "params": {}},
            {**valid, "params": [1, 2]},
        )
        for card in cases:
            with self.subTest(card=card):
                with self.assertRaises(Exception):
                    validate_context_actions(
                        _exploration_panel(
                            suggestions={"status": "ready", "cards": [card] * 3}
                        )
                    )

    def test_freeform_card_pins_explore_talk_freeform_and_binding_params(self):
        freeform = {
            "kind": "freeform",
            "action_code": "explore.talk_freeform",
            "label": "隨意聊聊",
            "params": {"npc_id": 9},
        }
        cards = [_suggestion_card(), freeform, _suggestion_card(label="查看木箱")]
        normalized = validate_context_actions(
            _exploration_panel(suggestions={"status": "ready", "cards": cards})
        )
        self.assertEqual(normalized["suggestions"]["cards"][1]["kind"], "freeform")
        self.assertEqual(
            normalized["suggestions"]["cards"][1]["action_code"],
            "explore.talk_freeform",
        )
        self.assertEqual(normalized["suggestions"]["cards"][1]["params"], {"npc_id": 9})
        bad_freeform_cards = (
            {**freeform, "action_code": "explore.move"},
            {**freeform, "params": {"npc_id": 9, "speech": "你好"}},
            {**freeform, "params": {"npc_id": 0}},
            {**freeform, "params": {}},
        )
        for bad in bad_freeform_cards:
            with self.subTest(bad=bad):
                with self.assertRaises(Exception):
                    validate_context_actions(
                        _exploration_panel(
                            suggestions={
                                "status": "ready",
                                "cards": [_suggestion_card(), bad, _suggestion_card(label="查看木箱")],
                            }
                        )
                    )

    def test_room_survey_boolean_accepts_and_other_booleans_reject(self):
        payload = validate_context_actions(
            _exploration_panel(suggestions=_ready_suggestions())
        )
        self.assertEqual(payload["suggestions"]["cards"][0]["params"], {"room": True})
        bad = {
            "kind": "known_action",
            "action_code": "explore.wait",
            "label": "等待片刻",
            "params": {"sleep": True},
        }
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(
                    suggestions={
                        "status": "ready",
                        "cards": [_suggestion_card(), bad, _suggestion_card(label="查看木箱")],
                    }
                )
            )

    def test_hint_optional_and_bounded(self):
        card = {**_suggestion_card(), "hint": "可以查看整個房間。"}
        normalized = validate_context_actions(
            _exploration_panel(
                suggestions={
                    "status": "ready",
                    "cards": [card, _suggestion_card(label="查看木箱"), _suggestion_card(label="查看南門")],
                }
            )
        )
        self.assertEqual(normalized["suggestions"]["cards"][0]["hint"], "可以查看整個房間。")
        self.assertIsNone(normalized["suggestions"]["cards"][1]["hint"])

    def test_combat_form_pins_suggestions_unavailable(self):
        normalized = validate_context_actions(_valid_panel())
        self.assertEqual(normalized["suggestions"], {"status": "unavailable"})
        for suggestions in (
            {"status": "ready", "cards": [_suggestion_card()] * 3},
            {"status": "generating"},
            {"status": "degraded", "cards": []},
        ):
            with self.subTest(suggestions=suggestions):
                with self.assertRaises(ContextActionsError):
                    validate_context_actions(_valid_panel(suggestions=suggestions))

    def test_deepest_legitimate_envelope_leaf_stays_at_depth_eleven(self):
        # Design D-5: with suggestions.cards[].params present (leaf depth 7),
        # the deepest legitimate envelope leaf remains combat skills at depth
        # 11 (the freeform_scales entry value), so MAX_DEPTH = 12 needs no
        # change. Depth is measured from the ui_snapshot envelope root exactly
        # like check_json_safety.
        from web.webclient.presentation.protocol import MAX_DEPTH, check_json_safety

        payload = _valid_panel(
            skills=[
                _valid_category_group(
                    groups=[_valid_skill_group(
                        skills=[
                            _valid_skill(
                                freeform_scales=[
                                    {"scale": 0.25, "label": "1/4", "mp_cost": 5},
                                    {"scale": 0.5, "label": "1/2", "mp_cost": 10},
                                    {"scale": 1.0, "label": "1", "mp_cost": 20},
                                    {"scale": 2.0, "label": "2", "mp_cost": 40},
                                    {"scale": 4.0, "label": "4", "mp_cost": 80},
                                ]
                            )
                        ]
                    )]
                )
            ],
            suggestions={
                "status": "ready",
                "cards": [
                    {**_suggestion_card(), "hint": "查看房間"},
                    _suggestion_card(label="查看木箱"),
                    _suggestion_card(label="查看南門"),
                ],
            },
        )
        envelope = {"panels": {"context_actions": payload}}

        def _leaf_depth(value, depth=0):
            if isinstance(value, dict):
                children = value.values()
            elif isinstance(value, list):
                children = value
            else:
                return depth
            if not children:
                return depth
            return max(_leaf_depth(child, depth + 1) for child in children)

        check_json_safety(envelope)
        self.assertEqual(_leaf_depth(envelope), 11)
        self.assertLessEqual(_leaf_depth(envelope), MAX_DEPTH)


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
        grant_lineage(self.player, ["fire_ball"], ["defense_instinct"])
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
        # The unconditionally-owned seed acts form the sexual_act category
        # with their Chinese line names as sub-group keys, in first-seen
        # group order (sorted seed keys: combat_tease first, then the seven
        # 神之秘法 acts whose unlock={} makes them owned by everyone).
        sexual = payload["skills"][3]
        self.assertEqual(sexual["label"], "性愛行為")
        self.assertEqual(
            [sub_group["group"] for sub_group in sexual["groups"]],
            ["戰鬥", "神之秘法", "關係", "羞恥", "獨處"],
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
    def test_exploration_uses_the_available_exploration_form_without_fabrication(self):
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        self.assertEqual(payload["schema_version"], 5)
        self.assertNotIn("session", payload)
        self.assertNotIn("participants", payload)
        self.assertNotIn("root_actions", payload)
        self.assertNotIn("secondary_actions", payload)
        self.assertNotIn("skills", payload)
        self.assertNotIn("attack", repr(payload))
        self.assertGreaterEqual(len(payload["affordances"]), 1)
        # Without trigger-service state the exploration suggestions are inert.
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})

    def test_combat_presenter_pins_suggestions_unavailable_in_both_forms(self):
        # A ready options snapshot must never leak into the combat form: the
        # combat presenter does not read options_state at all.
        engage(self.player, self.monster)
        context = PresentationContext(
            actor=self.player,
            protocol_version=1,
            options_state=OptionsSnapshot(
                fingerprint="fp",
                status="ready",
                generation_token=1,
                displayed=(
                    FrozenCard(
                        kind="known_action",
                        action_code="explore.look",
                        label="查看房間",
                        params={"room": True},
                    ),
                ),
            ),
        )
        payload = self.registry.render("context_actions", context)
        self.assertEqual(payload["kind"], "combat")
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})
        # The recovery form carries the same pin (schema-level; the presenter
        # emits it verbatim in both branches).
        normalized = validate_context_actions(_recovery_panel())
        self.assertEqual(normalized["suggestions"], {"status": "unavailable"})

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
        grant_lineage(
            self.player,
            ["wind_blade", "gale_step"],
            ["wind_mastery"],
            rungs={"wind_blade": 10},
        )
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
        # Outside combat the exploration form is available; only a
        # creation-pending or locationless puppet renders unavailable.
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        self.player.db.creation_pending = True
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "presentation_unavailable")

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_catalog_complete_panel_fits_protocol_envelope(self):
        # Design.md D-2: the raised MAX_SKILLS stands only while the
        # catalog-complete payload still fits the OOB envelope limits. Own
        # every obtainable active skill (the 91 base active skills including
        # innate, plus all 65 registered sexual acts) and measure the
        # serialized panel: it must build without a presentation error and
        # stay at or below MAX_CANONICAL_JSON_BYTES with every array within
        # MAX_LIST_ITEMS.
        from world.skills.registry import SKILL_REGISTRY, SkillKind

        all_active = sorted(
            key
            for key, skill in SKILL_REGISTRY.items()
            if skill.kind is SkillKind.ACTIVE
        )
        self.player.db.skills = {"active": all_active, "passive": []}
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        flattened = self._flatten_skills(payload)
        self.assertGreater(len(flattened), 32)
        self.assertEqual(len(flattened), len(all_active))

        def _walk_arrays(value):
            if isinstance(value, list):
                yield value
                for item in value:
                    yield from _walk_arrays(item)
            elif isinstance(value, dict):
                for item in value.values():
                    yield from _walk_arrays(item)

        for array in _walk_arrays(payload):
            self.assertLessEqual(len(array), MAX_LIST_ITEMS)
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)

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
                    "lineage",
                    "character",
                }
            ),
        )

    @covers_requirement("webclient-context-actions::the-exploration-context-form-enumerates-the-complete-canonical-affordance-list")
    def test_maximal_legal_room_serializes_untruncated(self):
        from evennia.objects.objects import DefaultObject
        from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
        from typeclasses.npcs import LLMNPC, NPC
        from web.webclient.presentation.combat_panel import MAX_CONTEXT_AFFORDANCES
        from web.webclient.presentation.affordances import exploration_affordances

        # The combat fixture monster leaves the room so the vocabulary reaches
        # the shared caps: 30 generative hosts with a full authored keyword
        # list (6 keywords + freeform + invite = 8 per target), the guild and
        # shop hosts (6 keywords + one navigation entry each), 12 exits,
        # 32 look objects, and the 2-entry safe baseline: 30*8 + 7 + 7 +
        # 12 + 32 + 2 = 300 entries.
        self.monster.location = None
        for index in range(30):
            npc = create_object(LLMNPC, key=f"話者{index}", location=self.room)
            npc.components.add(
                ScriptedDialogue.create(npc, dialogue_key="guild_staff")
            )
        staff = create_object(NPC, key="公會職員", location=self.room)
        staff.components.add(
            ScriptedDialogue.create(staff, dialogue_key="guild_staff")
        )
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        shop = create_object(NPC, key="商人", location=self.room)
        shop.components.add(
            ScriptedDialogue.create(shop, dialogue_key="guild_staff")
        )
        shop.components.add(
            Merchant.create(shop, service_id="shop", branch_key="guild_branch_altoria")
        )
        destinations = [
            create_object(Room, key=f"目的地{index}", location=None)
            for index in range(12)
        ]
        for index, destination in enumerate(destinations):
            create_object(
                "evennia.objects.objects.DefaultExit",
                key=f"出口{index}",
                location=self.room,
                destination=destination,
            )
        for index in range(32):
            create_object(DefaultObject, key=f"木箱{index}", location=self.room)
        vocabulary = exploration_affordances(self.player)
        self.assertEqual(len(vocabulary), 300)
        self.assertLessEqual(len(vocabulary), MAX_CONTEXT_AFFORDANCES)
        # Every target slot and every navigation surface is present; only the
        # monster-bound engage code and the companion-bound leave code are
        # absent from this room.
        from web.webclient.presentation.affordances import ACTION_CODE_ALLOWLIST

        ids = {
            entry.action_id
            for entry in vocabulary
            if not entry.navigation
        }
        self.assertEqual(
            ids,
            set(ACTION_CODE_ALLOWLIST) - {"explore.engage", "explore.party_leave"},
        )
        surfaces = {entry.surface for entry in vocabulary if entry.navigation}
        self.assertEqual(surfaces, {"guild", "shop"})
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        self.assertEqual(len(payload["affordances"]), len(vocabulary))
        normalized = validate_context_actions(payload)
        self.assertEqual(normalized["affordances"], payload["affordances"])
        # The maximal form must also survive the global envelope safety gate
        # the client enforces before accepting any snapshot or update, and
        # stays within the OOB byte bound on its own.
        check_envelope(payload)
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        # A full snapshot for this degenerate maximal room combines two
        # full-size panels (the version-1 exploration panel and this form) and
        # can exceed the envelope; the client rejects such snapshots
        # fail-closed exactly like the version-1 panel's own over-envelope
        # rejection — the form-level bound above is this change's guarantee.

    def test_exploration_presenter_is_read_only(self):
        before = {
            "location": self.player.location,
            "wallet": self.player.db.wallet,
            "map_knowledge": self.player.attributes.get("map_knowledge"),
        }
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        self.assertIs(self.player.location, before["location"])
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(
            self.player.attributes.get("map_knowledge"), before["map_knowledge"]
        )

    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-5-panel")
    def test_creation_pending_renders_the_version_five_unavailable_form(self):
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        self.player.db.creation_pending = True
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertFalse(payload["available"])
        self.assertEqual(payload["schema_version"], 5)
        self.assertEqual(payload["reason"]["code"], "presentation_unavailable")
        self.assertNotIn("affordances", payload)
        self.assertNotIn("suggestions", payload)

class SuggestionsRenderPathTests(BattlefieldIsolation, EvenniaTestCase):
    """Exploration suggestions render paths (design D-3; task 5.2)."""
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="建議測試房")
        self.player = _player()
        self.player.location = self.room
        self.registry = build_production_registry()
        self.fingerprint = "fp"

    def _render(self, options_state=None, fingerprint="fp"):
        return self.registry.render(
            "context_actions",
            PresentationContext(
                actor=self.player,
                protocol_version=1,
                options_state=options_state,
                options_fingerprint=fingerprint,
            ),
        )

    def test_absent_snapshot_is_inert(self):
        payload = self._render(options_state=None)
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})

    def test_unavailable_snapshot_is_inert(self):
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="unavailable",
                generation_token=0,
                displayed=None,
            )
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})

    def test_generating_carries_status_alone(self):
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="generating",
                generation_token=3,
                displayed=None,
            )
        )
        self.assertEqual(payload["suggestions"], {"status": "generating"})

    @covers_requirement("webclient-context-actions-suggestions::exploration-suggestions-render-from-an-immutable-session-snapshot")
    def test_ready_renders_the_snapshot_displayed_cards(self):
        cards = (
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看房間",
                params={"room": True},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.wait",
                label="等待片刻",
                params={"daypart": "noon"},
            ),
            FrozenCard(
                kind="freeform",
                action_code="explore.talk_freeform",
                label="隨意聊聊",
                params={"npc_id": 5},
            ),
        )
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="ready",
                generation_token=3,
                displayed=cards,
            )
        )
        self.assertEqual(payload["suggestions"]["status"], "ready")
        self.assertEqual(payload["suggestions"]["cards"][0]["params"], {"room": True})
        self.assertEqual(
            payload["suggestions"]["cards"][1]["params"],
            {"daypart": "noon"},
        )
        self.assertEqual(
            payload["suggestions"]["cards"][2]["action_code"],
            "explore.talk_freeform",
        )

    def test_ready_render_is_stable_across_repeated_renders(self):
        cards = (
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看房間",
                params={"room": True},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.wait",
                label="等待片刻",
                params={"daypart": "noon"},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看木箱",
                params={"target_id": 9},
            ),
        )
        snapshot = OptionsSnapshot(
            fingerprint="fp",
            status="ready",
            generation_token=3,
            displayed=cards,
        )
        first = self._render(snapshot)
        second = self._render(snapshot)
        self.assertEqual(first["suggestions"], second["suggestions"])
        # The snapshot writer may replace the session state object later; the
        # presenter never consults default_cards for a ready render.
        self.assertEqual(first["suggestions"]["cards"][0]["action_code"], "explore.look")

    @covers_requirement("webclient-context-actions-suggestions::exploration-suggestions-render-from-an-immutable-session-snapshot")
    def test_degraded_derives_rule_cards_from_default_cards(self):
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="degraded",
                generation_token=2,
                displayed=None,
            )
        )
        self.assertEqual(payload["suggestions"]["status"], "degraded")
        cards = payload["suggestions"]["cards"]
        self.assertGreaterEqual(len(cards), 1)
        self.assertLessEqual(len(cards), MAX_OPTION_CARDS)
        for card in cards:
            self.assertEqual(card["kind"], "known_action")
            self.assertIn(card["action_code"], ("explore.look", "explore.wait", "explore.move"))
        # The degraded derivation is a strict subset of the serialized form.
        affordance_payloads = {
            (entry["action_id"], str(entry["params"]), entry["label"])
            for entry in payload["affordances"]
            if entry.get("action_id") is not None
        }
        for card in cards:
            self.assertIn(
                (card["action_code"], str(card["params"]), card["label"]),
                affordance_payloads,
            )

    def test_corrupted_ready_falls_back_to_unavailable_without_fabrication(self):
        from unittest import mock

        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="ready",
                    generation_token=3,
                    displayed=None,
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="ready",
                    generation_token=3,
                    displayed=(
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.look",
                            label="bad",  # no CJK: fails the v5 shape gate
                            params={"room": True},
                        ),
                    ),
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()

    def test_degraded_with_ascii_display_names_fails_closed_to_unavailable(self):
        # The affordance vocabulary bounds display names at 128 code points
        # without a CJK requirement, while suggestion labels are 1..24 CJK.
        # An ASCII-named room must degrade the suggestions section alone —
        # never the whole exploration panel (rubber-duck review finding).
        from unittest import mock

        self.room.key = "english room name"
        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="degraded",
                    generation_token=2,
                    displayed=None,
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
        # The panel itself stays available and schema-valid.
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        validate_context_actions(payload)

    def test_degraded_with_overlong_display_name_fails_closed_to_unavailable(self):
        # A room display name beyond the 24-code-point suggestion label bound
        # must also fail closed to a section-level unavailable (rubber-duck
        # review finding); CJK content itself never guarantees the bound.
        from unittest import mock

        self.room.key = "這是一個非常非常非常非常非常非常非常非常長的房間名稱"
        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="degraded",
                    generation_token=2,
                    displayed=None,
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
        self.assertTrue(payload["available"])
        validate_context_actions(payload)

    @covers_requirement(
        "action-options-trigger-service::current-situation-freshness-gates-session-backed-suggestions"
    )
    def test_stale_non_unavailable_snapshots_fail_closed_to_unavailable(self):
        """A snapshot whose fingerprint no longer matches the current
        situation renders unavailable with a bounded diagnostic and never
        reaches the wire with old cards or a stale generating line
        (action-options-wiring-hardening R1 scenarios)."""
        from unittest import mock

        stale_cards = (
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看房間",
                params={"room": True},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.wait",
                label="等待片刻",
                params={"daypart": "noon"},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看木箱",
                params={"target_id": 9},
            ),
        )
        for status, displayed in (
            ("generating", None),
            ("ready", stale_cards),
            ("degraded", None),
        ):
            with self.subTest(status=status):
                with mock.patch(
                    "web.webclient.presentation.combat_panel.log_unavailable"
                ) as logged:
                    payload = self._render(
                        OptionsSnapshot(
                            fingerprint="fp",
                            status=status,
                            generation_token=3,
                            displayed=displayed,
                        ),
                        fingerprint="a-different-current-fingerprint",
                    )
                    self.assertEqual(payload["suggestions"], {"status": "unavailable"})
                    logged.assert_called_once()
                    self.assertNotIn("cards", payload["suggestions"])

    @covers_requirement(
        "action-options-trigger-service::current-situation-freshness-gates-session-backed-suggestions"
    )
    def test_absent_current_fingerprint_fails_closed_to_unavailable(self):
        """A context without a derivable exploration situation can never
        render a session-backed state: the gate emits unavailable even for a
        snapshot whose shape is valid (action-options-wiring-hardening R1)."""
        from unittest import mock

        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="ready",
                    generation_token=3,
                    displayed=(
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.look",
                            label="查看房間",
                            params={"room": True},
                        ),
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.wait",
                            label="等待片刻",
                            params={"daypart": "noon"},
                        ),
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.look",
                            label="查看木箱",
                            params={"target_id": 9},
                        ),
                    ),
                ),
                fingerprint=None,
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
            self.assertNotIn("cards", payload["suggestions"])

    def test_unavailable_snapshot_is_inert_regardless_of_fingerprint(self):
        """The ``unavailable`` status needs no fingerprint gate: it emits the
        same unavailable envelope whether or not the fingerprint matches."""
        from unittest import mock

        payload = self._render(
            OptionsSnapshot(
                fingerprint="stale",
                status="unavailable",
                generation_token=0,
                displayed=None,
            ),
            fingerprint="different",
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})
        payload = self._render(
            OptionsSnapshot(
                fingerprint="stale",
                status="unavailable",
                generation_token=0,
                displayed=None,
            ),
            fingerprint=None,
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})


class OptionsSnapshotFactoryTests(unittest.TestCase):
    """Read-side options_snapshot factory (task 1.5; review hardening)."""

    def test_absent_state_yields_none(self):
        from web.webclient.presentation.ingress import options_snapshot

        class _Session:
            class _Ndb:
                options_state = None

            ndb = _Ndb()

        self.assertIsNone(options_snapshot(_Session()))

    def test_repuppeted_owner_is_refused(self):
        from web.webclient.presentation.ingress import options_snapshot

        class _Actor:
            pk = 7

        class _Session:
            puppet = _Actor()

            class _Ndb:
                options_state = {
                    "owner_actor_id": 99,
                    "fingerprint": "fp",
                    "status": "ready",
                    "generation_token": 1,
                    "displayed": [],
                }

            ndb = _Ndb()

        self.assertIsNone(options_snapshot(_Session()))

    def test_malformed_state_never_raises(self):
        # A corrupt ephemeral write must degrade to an inert snapshot (or
        # None), never raise into the ingress/dispatcher publication path
        # (review finding).
        from web.webclient.presentation.ingress import options_snapshot

        class _Actor:
            pk = 7

        class _Session:
            puppet = _Actor()

            class _Ndb:
                options_state = "not a dict"

            ndb = _Ndb()

        self.assertIsNone(options_snapshot(_Session()))

        class _BadCards:
            ndb = type(
                "Ndb",
                (),
                {"options_state": {"displayed": [42], "status": "ready"}},
            )()
            puppet = _Actor()

        snapshot = options_snapshot(_BadCards())
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.displayed, ())
        # The non-dict card entry is dropped; the presenter renders the
        # ready-without-valid-cards case as inert unavailable.
        from web.webclient.presentation.context import PresentationContext
        from web.webclient.presentation.registry import build_production_registry

        from typeclasses.characters import PlayerCharacter
        from evennia.utils.create import create_object
        from evennia.utils.test_resources import EvenniaTestCase

        room = create_object(Room, key="備援測試房")
        player = create_object(PlayerCharacter, key="備援測試角色")
        player.race = "human"
        player.apply_race_baseline()
        player.location = room
        payload = build_production_registry().render(
            "context_actions",
            PresentationContext(
                actor=player,
                protocol_version=1,
                options_state=snapshot,
            ),
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})

    def test_valid_state_copies_cards_immutably(self):
        from web.webclient.presentation.ingress import options_snapshot

        class _Actor:
            pk = 7

        class _Session:
            puppet = _Actor()

            class _Ndb:
                options_state = {
                    "owner_actor_id": 7,
                    "fingerprint": "fp-1234",
                    "status": "ready",
                    "generation_token": 3,
                    "displayed": [
                        {
                            "kind": "known_action",
                            "action_code": "explore.look",
                            "label": "查看房間",
                            "params": {"room": True},
                        },
                        {
                            "kind": "freeform",
                            "action_code": "explore.talk_freeform",
                            "label": "隨意聊聊",
                            "params": {"npc_id": 9},
                            "hint": "可以聊聊",
                        },
                    ],
                }

            ndb = _Ndb()

        snapshot = options_snapshot(_Session())
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.fingerprint, "fp-1234")
        self.assertEqual(snapshot.status, "ready")
        self.assertEqual(snapshot.generation_token, 3)
        self.assertEqual(len(snapshot.displayed), 2)
        card = snapshot.displayed[0]
        self.assertEqual(card.as_dict()["params"], {"room": True})
        # The deep copy is detached from the source state.
        _Session._Ndb.options_state["displayed"][0]["params"]["room"] = False
        self.assertEqual(card.as_dict()["params"], {"room": True})


if __name__ == "__main__":
    unittest.main()
