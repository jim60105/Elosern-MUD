"""Character panel schema tests: the v9 ``selected_skill`` section."""
import unittest
from tools.spec_traceability import covers_requirement
from web.webclient.presentation.character import (
    MAX_FREEFORM_LADDER_RUNGS,
    MAX_SELECTED_LINEAGE_ROWS,
    CharacterPanelError,
    validate_character,
)
from web.webclient.presentation.protocol import ProtocolValidationError
from ._support import _valid_panel

_LADDER = [
    {"scale": 0.25, "label": "1/4", "mp_cost": 4},
    {"scale": 0.5, "label": "1/2", "mp_cost": 7},
    {"scale": 1, "label": "1", "mp_cost": 14},
    {"scale": 2, "label": "2", "unlock_level": 6},
    {"scale": 4, "label": "4", "unlock_level": 10},
]


def _selected(**overrides):
    value = {
        "key": "t_selected_skill",
        "lineage": {
            "prerequisites": [{"key": "t_parent", "label": "合成前置", "level": 1}],
            "next": [{"key": "t_child", "label": "合成後續", "min_level": 3}],
        },
        "freeform_ladder": [dict(rung) for rung in _LADDER],
    }
    value.update(overrides)
    return value


class SelectedSkillSchemaTests(unittest.TestCase):

    @covers_requirement("webclient-exploration-menu::the-selected-skill-carries-lineage-position-and-the-freeform-ladder")
    def test_null_and_a_full_section_are_accepted(self):
        self.assertIsNone(validate_character(_valid_panel())["selected_skill"])
        normalized = validate_character(_valid_panel(selected_skill=_selected()))
        self.assertEqual(normalized["selected_skill"], _selected())

    def test_the_section_is_required_and_exact(self):
        payload = _valid_panel()
        del payload["selected_skill"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(selected_skill={**_selected(), "extra": 1}))
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(selected_skill=_selected(lineage={"prerequisites": []}))
            )

    @covers_requirement("webclient-exploration-menu::the-selected-skill-carries-lineage-position-and-the-freeform-ladder")
    def test_each_lineage_side_is_bounded_and_typed(self):
        for field, level_field in (("prerequisites", "level"), ("next", "min_level")):
            with self.subTest(field=field):
                rows = [
                    {"key": f"t_edge_{i}", "label": "合成邊", level_field: 1}
                    for i in range(MAX_SELECTED_LINEAGE_ROWS + 1)
                ]
                lineage = {"prerequisites": [], "next": []}
                lineage[field] = rows
                with self.assertRaises(CharacterPanelError):
                    validate_character(
                        _valid_panel(selected_skill=_selected(lineage=lineage))
                    )
                at_bound = {"prerequisites": [], "next": []}
                at_bound[field] = rows[:MAX_SELECTED_LINEAGE_ROWS]
                self.assertEqual(
                    validate_character(
                        _valid_panel(selected_skill=_selected(lineage=at_bound))
                    )["selected_skill"]["lineage"][field],
                    at_bound[field],
                )
                for bad_level in (0, -1, 1.5, "1", True):
                    with self.subTest(level=bad_level):
                        lineage = {
                            "prerequisites": [],
                            "next": [],
                            field: [
                                {"key": "t_edge", "label": "合成邊", level_field: bad_level}
                            ],
                        }
                        with self.assertRaises(ProtocolValidationError):
                            validate_character(
                                _valid_panel(selected_skill=_selected(lineage=lineage))
                            )
                # The level field is side-specific: the other side's name is
                # an unknown field.
                wrong = "min_level" if level_field == "level" else "level"
                lineage = {"prerequisites": [], "next": []}
                lineage[field] = [{"key": "t_edge", "label": "合成邊", wrong: 1}]
                with self.assertRaises(ProtocolValidationError):
                    validate_character(
                        _valid_panel(selected_skill=_selected(lineage=lineage))
                    )

    @covers_requirement("webclient-exploration-menu::the-freeform-ladder-lists-every-rung-for-a-mastery-owner")
    def test_the_ladder_is_the_canonical_five_rungs(self):
        self.assertEqual(len(_LADDER), MAX_FREEFORM_LADDER_RUNGS)
        # Short, over-long, and mis-ordered ladders fail closed.
        for ladder in (
            _LADDER[:4],
            [*_LADDER, {"scale": 8, "label": "8", "mp_cost": 56}],
            [_LADDER[1], _LADDER[0], *_LADDER[2:]],
            [_LADDER[0], _LADDER[1], _LADDER[2], _LADDER[4], _LADDER[3]],
        ):
            with self.subTest(ladder=ladder):
                with self.assertRaises(CharacterPanelError):
                    validate_character(
                        _valid_panel(selected_skill=_selected(freeform_ladder=ladder))
                    )
        # A canonical label never pairs with another scale.
        relabelled = [dict(rung) for rung in _LADDER]
        relabelled[2]["label"] = _LADDER[1]["label"]
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(selected_skill=_selected(freeform_ladder=relabelled))
            )
        # A boolean is an int in Python but never a canonical scale.
        boolean_scale = [dict(rung) for rung in _LADDER]
        boolean_scale[2]["scale"] = True
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(selected_skill=_selected(freeform_ladder=boolean_scale))
            )

    @covers_requirement("webclient-exploration-menu::the-freeform-ladder-lists-every-rung-for-a-mastery-owner")
    def test_each_rung_carries_exactly_one_of_cost_and_level(self):
        both = [dict(rung) for rung in _LADDER]
        both[3]["mp_cost"] = 28
        neither = [dict(rung) for rung in _LADDER]
        del neither[3]["unlock_level"]
        extra = [dict(rung) for rung in _LADDER]
        extra[0]["extra"] = 1
        for ladder in (both, neither):
            with self.subTest(ladder=ladder):
                with self.assertRaises(CharacterPanelError):
                    validate_character(
                        _valid_panel(selected_skill=_selected(freeform_ladder=ladder))
                    )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(selected_skill=_selected(freeform_ladder=extra))
            )

    @covers_requirement("webclient-exploration-menu::the-freeform-ladder-lists-every-rung-for-a-mastery-owner")
    def test_costs_and_unlock_levels_are_bounded(self):
        # A zero adjusted cost is legal on an unlocked rung.
        free = [dict(rung) for rung in _LADDER]
        free[0]["mp_cost"] = 0
        validate_character(_valid_panel(selected_skill=_selected(freeform_ladder=free)))
        for index, field, bad in (
            (0, "mp_cost", -1),
            (3, "unlock_level", 0),
            (3, "unlock_level", -1),
            (3, "unlock_level", 1.5),
        ):
            with self.subTest(field=field, bad=bad):
                ladder = [dict(rung) for rung in _LADDER]
                ladder[index][field] = bad
                with self.assertRaises(ProtocolValidationError):
                    validate_character(
                        _valid_panel(selected_skill=_selected(freeform_ladder=ladder))
                    )

    @covers_requirement("webclient-exploration-menu::the-freeform-ladder-lists-every-rung-for-a-mastery-owner")
    def test_the_ladder_is_omittable_for_a_non_master(self):
        without = _selected()
        del without["freeform_ladder"]
        normalized = validate_character(_valid_panel(selected_skill=without))
        self.assertNotIn("freeform_ladder", normalized["selected_skill"])
        # Present-but-null is not the omission: the exact-field contract keeps
        # "absent" and "null" distinct on this optional section.
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(selected_skill=_selected(freeform_ladder=None))
            )


if __name__ == "__main__":
    unittest.main()
