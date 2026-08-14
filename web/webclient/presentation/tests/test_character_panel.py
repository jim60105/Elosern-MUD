"""Exact ``character`` schema, presenter, and parity tests.

Covers the D10 shared bounds, the version-1 payload validation, true-vs-
disguised values, the empty displayed list when undisguised, read-only
guarantees, and the status-vs-character parity proving both panels share the
same canonical trait source.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from world.rules.tests.combat_fixtures import BattlefieldIsolation

from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.character import (
    CHARACTER_SCHEMA_VERSION,
    MAX_DISPLAYED_ROWS,
    MAX_EQUIPMENT_ROWS,
    MAX_KEY_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_PASSIVE_ROWS,
    MAX_SLOT_CODE_POINTS,
    MAX_TRAIT_ROWS,
    CharacterPanelError,
    validate_character,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.status_query import StatusQueryError


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _trait(**overrides):
    value = {"key": "hp", "label": "生命", "current": 10, "max": 10}
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": 2,
        "available": True,
        "kind": "character",
        "traits": [_trait(), _trait(key="atk_phys", label="攻擊", current=5, max=None)],
        "passives": [{"key": "defense_instinct", "label": "防禦直覺"}],
        "equipment": [{"slot": "weapon_main", "item_key": "plain_sword", "display_name": "鐵劍"}],
        "disguise": {
            "active": False,
            "description": "",
            "displayed": [],
        },
        "guild": {"rank": None, "merit": 0},
        "wallet": 100,
        "persona": {"background": None},
    }
    value.update(overrides)
    return value


class CharacterSchemaTests(unittest.TestCase):
    def test_valid_panel_passes(self):
        normalized = validate_character(_valid_panel())
        self.assertEqual(normalized["schema_version"], CHARACTER_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "character")

    def test_rejects_unknown_and_missing_fields(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(bogus=1))
        payload = _valid_panel()
        del payload["wallet"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)

    def test_trait_max_consistency(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(traits=[_trait(current=11, max=10)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(traits=[_trait(key="hp"), _trait(key="hp")])
            )

    def test_disguise_requires_empty_displayed_when_inactive(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": False,
                        "description": "",
                        "displayed": [{"key": "atk_phys", "label": "攻擊", "value": 12}],
                    }
                )
            )

    def test_active_disguise_requires_description(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": True,
                        "description": "  ",
                        "displayed": [],
                    }
                )
            )

    def test_worst_case_legal_payload_fits_the_envelope(self):
        traits = [
            _trait(
                key=f"trait_{i}",
                label="很長的屬性名稱" * 3,
                current=1000,
                max=None if i % 2 else 1000,
            )
            for i in range(MAX_TRAIT_ROWS)
        ]
        passives = [
            {"key": f"passive_{i}", "label": "很長的主動技能名稱" * 3}
            for i in range(MAX_PASSIVE_ROWS)
        ]
        equipment = [
            {
                "slot": "weapon_main",
                "item_key": f"item_{i}",
                "display_name": "很長的裝備名稱" * 3,
            }
            for i in range(MAX_EQUIPMENT_ROWS)
        ]
        displayed = [
            {"key": f"stat_{i}", "label": "很長的顯示數值名稱" * 3, "value": 1000}
            for i in range(MAX_DISPLAYED_ROWS)
        ]
        payload = _valid_panel(
            traits=traits,
            passives=passives,
            equipment=equipment,
            disguise={
                "active": True,
                "description": "偽裝中的描述文字" * 10,
                "displayed": displayed,
            },
        )
        normalized = validate_character(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)

    def test_rejects_blank_labels_and_over_bound_values(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(traits=[_trait(label="  ")]))
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(passives=[{"key": "x", "label": "  "}])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    equipment=[{"slot": " ", "item_key": "x", "display_name": "劍"}]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    equipment=[{"slot": "w", "item_key": "x", "display_name": "  "}]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": True,
                        "description": "偽裝中",
                        "displayed": [{"key": "k", "label": "  ", "value": 1}],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": True,
                        "description": "偽裝中",
                        "displayed": [
                            {"key": f"k{i}", "label": "數值", "value": i}
                            for i in range(MAX_DISPLAYED_ROWS + 1)
                        ],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(guild={"rank": " ", "merit": 0}))
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(traits=[_trait(key="x" * 65)]))

    def test_rejects_wrong_version_kind_and_row_counts(self):
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version=1))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version=3))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(available=False))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(kind="services"))
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(traits=[_trait() for _ in range(MAX_TRAIT_ROWS + 1)])
            )
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    passives=[{"key": "x", "label": "技"} for _ in range(MAX_PASSIVE_ROWS + 1)]
                )
            )
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    equipment=[
                        {"slot": "w", "item_key": "x", "display_name": "劍"}
                        for _ in range(MAX_EQUIPMENT_ROWS + 1)
                    ]
                )
            )

    def test_over_limit_envelope_fails_closed(self):
        wide = "😀" * MAX_LABEL_CODE_POINTS
        payload = _valid_panel(
            traits=[_trait(key=f"t{i}", label=wide) for i in range(MAX_TRAIT_ROWS)],
            passives=[
                {"key": f"p{i}", "label": wide} for i in range(MAX_PASSIVE_ROWS)
            ],
            equipment=[
                {"slot": "weapon_main", "item_key": f"i{i}", "display_name": wide}
                for i in range(MAX_EQUIPMENT_ROWS)
            ],
            disguise={
                "active": True,
                "description": wide,
                "displayed": [
                    {"key": f"d{i}", "label": wide, "value": 1}
                    for i in range(MAX_DISPLAYED_ROWS)
                ],
            },
        )
        with self.assertRaises(CharacterPanelError):
            validate_character(payload)


class CharacterPresenterTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        # Register the quest catalog in this class's own setup: the affinity
        # rulebook load (reached through guild registration) resolves
        # ``introductory_hunt`` from the definition registry, so this class
        # must not depend on an earlier test to have registered it.
        from world.quests.catalog import register_catalog

        register_catalog()
        get_world_clock()
        self.player = create_object(PlayerCharacter, key="角色狀態測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.wallet = 500
        self.player.db.skills = {
            "active": ["fire_ball"],
            "passive": ["defense_instinct"],
        }
        self.player.db.equipment = {
            "weapon_main": "plain_sword",
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        self.player.save()

    def _registry(self):
        return build_production_registry()

    def _render(self):
        return self._registry().render("character", _context(self.player))

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-2-panel")
    def test_character_renders_true_values_without_mutation(self):
        before_traits = dict(self.player.attributes.get("traits", category="traits"))
        before_wallet = self.player.db.wallet
        before_equipment = self.player.db.equipment
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "character")
        hp = next(row for row in payload["traits"] if row["key"] == "hp")
        self.assertEqual(hp["max"], self.player.traits.hp.max)
        self.assertEqual(hp["current"], self.player.traits.hp.current)
        atk = next(row for row in payload["traits"] if row["key"] == "atk_phys")
        self.assertEqual(atk["current"], self.player.traits.atk_phys.base)
        self.assertIsNone(atk["max"])
        self.assertEqual(
            [row["key"] for row in payload["passives"]],
            ["defense_instinct"],
        )
        self.assertEqual(payload["equipment"][0]["slot"], "weapon_main")
        self.assertEqual(payload["wallet"], 500)
        # Byte-for-byte unchanged canonical state.
        self.assertEqual(
            dict(self.player.attributes.get("traits", category="traits")),
            before_traits,
        )
        self.assertEqual(self.player.db.wallet, before_wallet)
        self.assertEqual(self.player.db.equipment, before_equipment)

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-2-panel")
    def test_expanded_state_shows_true_values_and_an_honest_disguise(self):
        self.player.db.disguised_stats = {"atk_phys": 12, "agility": 10}
        payload = self._render()
        self.assertTrue(payload["disguise"]["active"])
        self.assertTrue(payload["disguise"]["description"].strip())
        displayed = {row["key"]: row["value"] for row in payload["disguise"]["displayed"]}
        self.assertEqual(displayed, {"atk_phys": 12, "agility": 10})
        atk = next(row for row in payload["traits"] if row["key"] == "atk_phys")
        self.assertEqual(atk["current"], self.player.traits.atk_phys.base)
        self.assertNotEqual(atk["current"], 12)
        self.assertEqual(self.player.traits.atk_phys.base, atk["current"])

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-2-panel")
    def test_undisguised_actor_has_empty_displayed_list(self):
        payload = self._render()
        self.assertFalse(payload["disguise"]["active"])
        self.assertEqual(payload["disguise"]["displayed"], [])
        self.assertTrue(payload["traits"])

    def test_guild_rank_and_merit_are_reported(self):
        from typeclasses.components import GuildStaff
        from typeclasses.npcs import NPC
        from world.rules.surfaces import write_counter_trait

        self.player.location = self.room1
        staff = create_object(NPC, key="公會職員", location=self.room1)
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        register_adventurer(self.player, staff=staff)
        write_counter_trait(self.player, "guild_merit", 60)
        payload = self._render()
        self.assertEqual(payload["guild"]["rank"], "F")
        self.assertEqual(payload["guild"]["merit"], 60)

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-2-panel")
    def test_status_character_parity_on_shared_values(self):
        status = self._registry().render("status", _context(self.player))
        character = self._render()
        self.assertTrue(status["available"])
        for key in ("hp", "mp", "sp"):
            gauge = status["resources"][key]
            row = next(row for row in character["traits"] if row["key"] == key)
            self.assertEqual(row["current"], gauge["current"])
            self.assertEqual(row["max"], gauge["maximum"])
        self.assertEqual(
            character["disguise"]["active"], status["disguise_active"]
        )

    def test_combat_mode_renders_unavailable_form(self):
        from typeclasses.monsters import Monster

        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        self.player.location = self.room1
        engage(self.player, monster)
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("traits", payload)

    def test_unknown_item_and_skill_degrade_to_their_keys(self):
        self.player.db.equipment = {
            "weapon_main": "no_such_item",
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        self.player.db.skills = {"active": [], "passive": ["no_such_skill"]}
        payload = self._render()
        row = next(r for r in payload["equipment"] if r["slot"] == "weapon_main")
        self.assertEqual(row["display_name"], "no_such_item")
        self.assertEqual([p["key"] for p in payload["passives"]], ["no_such_skill"])
        self.assertEqual(payload["passives"][0]["label"], "no_such_skill")

    def test_read_model_failure_renders_unavailable(self):
        with patch(
            "web.webclient.presentation.character.build_character_read_model",
            side_effect=StatusQueryError("broken"),
        ):
            payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("traits", payload)


if __name__ == "__main__":
    unittest.main()
