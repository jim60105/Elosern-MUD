import unittest
from tools.spec_traceability import covers_requirement
from web.webclient.presentation.combat_panel import (
    CONTEXT_ACTIONS_SCHEMA_VERSION,
    validate_context_actions,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_LIST_ITEMS,
    check_envelope,
    json_byte_size,
)
from world.skills.registry import SkillCategory
from world.tests.synthetic_data import SYNTH_SKILLS

from ._support import (
    T_EMBER,
    _T_RECOVERY_STATE,
    _recovery_panel,
    _valid_category_group,
    _valid_panel,
    _valid_participant,
    _valid_skill,
    _valid_skill_group,
)



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
                            skills=[_valid_skill(key="t_solo_probe")],
                        ),
                        _valid_skill_group(
                            group="戰鬥",
                            label="戰鬥",
                            skills=[_valid_skill(key="t_battle_probe")],
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
        self.assertEqual(normalized["session"]["state"], _T_RECOVERY_STATE)
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
                    groups=[
                        _valid_skill_group(
                            group=None, label=SYNTH_SKILLS["t_ember_burst"].label
                        )
                    ]
                )
            ]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        panel = _valid_panel(
            skills=[
                _valid_category_group(
                    groups=[_valid_skill_group(group=T_EMBER, label=None)]
                )
            ]
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        # The top-level array is bounded by the number of SkillCategory
        # members, not by MAX_SKILLS.
        panel = _valid_panel(
            skills=[_valid_category_group() for _ in range(len(SkillCategory) + 1)]
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


if __name__ == "__main__":
    unittest.main()
