"""Full-title presenter tests: composed-title envelope rendering through the registry."""
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.character import MAX_FULL_TITLE_CODE_POINTS
from web.webclient.presentation.registry import build_production_registry
from ._support import _T_COMPOSED_TITLE, _T_RANK, _T_TITLE, _context, _open_title_scope
import unittest
from dataclasses import replace
from unittest.mock import patch


class CharacterFullTitlePresenterTests(EvenniaTest):
    """Both panels address the player by the one composed title."""


    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.player = create_object(PlayerCharacter, key="稱號面板測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.save()


    def _character(self):
        return build_production_registry().render("character", _context(self.player))


    def _status(self):
        return build_production_registry().render("status", _context(self.player))

    @covers_requirement("webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers")
    def test_status_v3_serializes_and_rejects_invalid_frozen_provenance(self):
        from world.rules.status_query import build_status_read_model
        from world.rules.status_query.models import ConditionValue, ConditionProvenance, EquipmentSource

        model = build_status_read_model(self.player)
        source = EquipmentSource("t_a", "合成護符")
        valid = ConditionProvenance("equipment", (source,))
        row = ConditionValue("t_warning", "合成警告", "warning", 17, {"defense": -15}, valid)
        with patch("web.webclient.presentation.status.build_status_read_model", return_value=replace(model, conditions=(row,))):
            panel = self._status()
        self.assertEqual(panel["schema_version"], 3)
        self.assertEqual(panel["conditions"], [{
            "code": "t_warning", "label": "合成警告", "severity": "warning",
            "remaining_seconds": 17, "modifiers": {"defense": -15},
            "provenance": {"kind": "equipment", "equipment_sources": [{"item_key": "t_a", "label": "合成護符"}]},
        }])
        invalid = [
            None, ConditionProvenance("legacy", ()), ConditionProvenance("equipment", ()),
            ConditionProvenance("mixed", ()), ConditionProvenance("unknown", (source,)),
            ConditionProvenance("non_equipment", (source,)),
            ConditionProvenance("equipment", (source, source)),
            ConditionProvenance("equipment", (EquipmentSource("t_b", "乙"), source)),
            ConditionProvenance("equipment", tuple(EquipmentSource(f"t_{i}", "合成") for i in range(9))),
            ConditionProvenance("equipment", (EquipmentSource("BAD", "甲"),)),
            ConditionProvenance("equipment", (EquipmentSource("t_a", ""),)),
            ConditionProvenance("equipment", (EquipmentSource("t_a", "字" * 129),)),
        ]
        for value in invalid:
            with self.subTest(value=value), patch(
                "web.webclient.presentation.status.build_status_read_model",
                return_value=replace(model, conditions=(replace(row, provenance=value),)),
            ):
                panel = self._status()
                self.assertFalse(panel["available"])
                self.assertEqual(panel["schema_version"], 3)


    def test_an_untitled_actor_omits_the_row_on_both_panels(self):
        self.assertNotIn("full_title", self._character())
        self.assertNotIn("full_title", self._status()["actor"])


    @covers_requirement("title-system::narrative-consumers-compose-predicates-read-the-collection")
    def test_a_titled_actor_shares_one_composed_title_on_both_panels(self):
        _open_title_scope(self)
        from world.rules.titles import grant_first_quest_epithet, grant_rank_title

        grant_rank_title(self.player, _T_RANK.key)

        grant_first_quest_epithet(self.player)
        character = self._character()
        status = self._status()
        self.assertEqual(character["full_title"], _T_COMPOSED_TITLE)
        self.assertEqual(status["actor"]["full_title"], character["full_title"])


    def test_a_fixed_only_actor_shows_the_registry_display(self):
        _open_title_scope(self)
        from world.rules.titles import bank_fixed

        bank_fixed(self.player, _T_TITLE.key, 1)
        self.assertEqual(self._character()["full_title"], _T_TITLE.display_name_zh)


    def test_a_corrupt_title_record_fails_the_panel_closed(self):
        _open_title_scope(self)
        from world.rules.titles import grant_first_quest_epithet, grant_rank_title

        grant_rank_title(self.player, _T_RANK.key)

        grant_first_quest_epithet(self.player)
        self.player.attributes.add("title_collection", "damaged")
        self.assertFalse(self._character()["available"])
        self.assertFalse(self._status()["available"])


    def test_an_over_bound_composed_title_fails_the_panel_closed(self):
        # The presenter validates its own payload; the read model must fail
        # closed on a composed title past the wire bound (legacy/corrupt
        # storage that no writer can create anymore) instead of serializing a
        # panel the client validator would reject whole.
        self.player.attributes.add(
            "title_collection",
            [
                {
                    "kind": "epithet",
                    "display": "長" * (MAX_FULL_TITLE_CODE_POINTS + 1),
                    "origin_quote": "超出傳輸上限的異名。",
                    "granted_tick": 1,
                }
            ],
        )
        self.player.attributes.add(
            "title_equipped", {"fixed": None, "epithet": "長" * (MAX_FULL_TITLE_CODE_POINTS + 1)}
        )
        self.assertFalse(self._character()["available"])
        self.assertFalse(self._status()["available"])


    def test_a_title_at_the_wire_bound_renders_on_both_panels(self):
        at_bound = "長" * MAX_FULL_TITLE_CODE_POINTS
        self.player.attributes.add(
            "title_collection",
            [
                {
                    "kind": "epithet",
                    "display": at_bound,
                    "origin_quote": "正好貼線上限的異名。",
                    "granted_tick": 1,
                }
            ],
        )
        self.player.attributes.add(
            "title_equipped", {"fixed": None, "epithet": at_bound}
        )
        self.assertEqual(self._character()["full_title"], at_bound)
        self.assertEqual(self._status()["actor"]["full_title"], at_bound)


if __name__ == "__main__":
    unittest.main()
