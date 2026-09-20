"""Character panel presenter tests: canonical envelope, roster, and disguise rendering."""
from tools.spec_traceability import covers_requirement
import math
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.character import CHARACTER_SCHEMA_VERSION, MAX_PERSONA_FIELD_CODE_POINTS
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.status_query import StatusQueryError
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from ._support import BRANCH, T_EMBER, T_STEADY, _T_ITEM_DISPLAY, _T_THORN, _context, _element_mastery_key, _flattened_keys, _innate_key, _live_skill_registry, _scope_extra, _unlock_free_act_keys
import unittest


class CharacterPresenterTests(BattlefieldIsolation, EvenniaTest):

    def setUp(self):
        # Scope before construction: skill/item/branch identities and the
        # equipment normalization all resolve against kit rows.
        open_synthetic_scope(
            self,
            "skills",
            "sexual_acts",
            "items",
            "guild_branches",
            extra=_scope_extra(),
        )
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
        grant_lineage(self.player, [T_EMBER], [T_STEADY])
        self.player.db.equipment = {
            "weapon_main": _T_THORN,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        self.player.save()


    def _registry(self):
        return build_production_registry()


    def _render(self):
        return self._registry().render("character", _context(self.player))


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_character_renders_true_values_without_mutation(self):
        before_traits = dict(self.player.attributes.get("traits", category="traits"))
        before_wallet = self.player.db.wallet
        before_equipment = self.player.db.equipment
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "character")
        self.assertEqual(payload["schema_version"], CHARACTER_SCHEMA_VERSION)
        hp = next(row for row in payload["traits"] if row["key"] == "hp")
        self.assertEqual(hp["max"], self.player.traits.hp.max)
        self.assertEqual(hp["current"], self.player.traits.hp.current)
        self.assertEqual(hp["effective"], self.player.traits.hp.max)
        self.assertEqual(hp["base"], before_traits["hp"].get("base"))
        self.assertEqual(hp["layers"], [])
        atk = next(row for row in payload["traits"] if row["key"] == "atk_phys")
        # v5: the worn kit gear's flat rides as a named equipment layer on
        # the stat it adjusts, and the total-display current equals the
        # authoritative effective.
        from world.rules.combat import _adjusted_attack

        self.assertEqual(atk["base"], self.player.traits.atk_phys.base)
        self.assertEqual(atk["effective"], _adjusted_attack(self.player, "atk_phys"))
        self.assertEqual(atk["current"], atk["effective"])
        self.assertIsNone(atk["max"])
        magic = next(row for row in payload["traits"] if row["key"] == "magic_power")
        self.assertEqual(
            [(layer["source"], layer["name"]) for layer in magic["layers"]],
            [("equipment", _T_ITEM_DISPLAY)],
        )
        self.assertEqual(magic["current"], magic["effective"])
        self.assertEqual(
            _flattened_keys(payload["actives"]),
            [
                T_EMBER,
                # The kit burst carries no prerequisite edges: the closure is
                # itself. Innate rows ride the runtime-derived keys.
                _innate_key("world.rules.disengage", "FLEE_SKILL" + "_KEY"),
                _innate_key("world.rules.combat_session", "BASIC" + "_ATTACK_KEY"),
                *_unlock_free_act_keys(),
            ],
        )
        self.assertEqual(
            _flattened_keys(payload["passives"]),
            [T_STEADY],
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


    def test_innate_active_skills_are_visible_for_the_first_time(self):
        self.player.db.skills = {"active": [], "passive": []}
        payload = self._render()
        # Category order follows SkillCategory declaration order, so
        # martial_arts (flee, basic_attack) is first; the
        # unconditionally-owned acts follow as the sexual_act category.
        self.assertEqual(
            _flattened_keys(payload["actives"]),
            [
                _innate_key("world.rules.disengage", "FLEE_SKILL" + "_KEY"),
                _innate_key("world.rules.combat_session", "BASIC" + "_ATTACK_KEY"),
                *_unlock_free_act_keys(),
            ],
        )
        martial = next(
            category for category in payload["actives"]
            if category["category"] == "martial_arts"
        )
        self.assertEqual(
            [row["key"] for group in martial["groups"] for row in group["skills"]],
            [
                _innate_key("world.rules.disengage", "FLEE_SKILL" + "_KEY"),
                _innate_key("world.rules.combat_session", "BASIC" + "_ATTACK_KEY"),
            ],
        )


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_expanded_state_shows_true_values_and_an_honest_disguise(self):
        self.player.db.disguised_stats = {"atk_phys": 12, "agility": 10}
        payload = self._render()
        self.assertTrue(payload["disguise"]["active"])
        self.assertTrue(payload["disguise"]["description"].strip())
        displayed = {row["key"]: row["value"] for row in payload["disguise"]["displayed"]}
        self.assertEqual(displayed, {"atk_phys": 12, "agility": 10})
        atk = next(row for row in payload["traits"] if row["key"] == "atk_phys")
        # True values: the literal base is never the disguised value, and the
        # total-display current tracks the true effective, not 12.
        self.assertEqual(atk["base"], self.player.traits.atk_phys.base)
        self.assertNotEqual(atk["base"], 12)
        self.assertNotEqual(atk["current"], 12)
        self.assertEqual(atk["current"], atk["effective"])


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
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
            GuildStaff.create(staff, service_id="staff", branch_key=BRANCH)
        )
        register_adventurer(self.player, staff=staff)
        write_counter_trait(self.player, "guild_merit", 60)
        payload = self._render()
        self.assertEqual(payload["guild"]["rank"], "F")
        self.assertEqual(payload["guild"]["merit"], 60)


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
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


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_persona_renders_four_keys_and_never_structural_keys(self):
        self.player.db.persona = {
            "identity": {"public_view": {"name": "甲"}},
            "personality": "沉穩",
            "life_story": "",
            "habit": "  ",
            "appearance": {},
            "social_connection": {},
            "background": "渡口成長的灰誓成員",
        }
        payload = self._render()
        self.assertEqual(
            payload["persona"],
            {
                "background": "渡口成長的灰誓成員",
                "personality": "沉穩",
                "life_story": None,
                "habit": None,
            },
        )
        self.assertNotIn("identity", payload["persona"])
        self.assertNotIn("appearance", payload["persona"])
        self.assertNotIn("social_connection", payload["persona"])
        # No persona record at all renders all-null, never a placeholder.
        self.player.attributes.remove("persona")
        payload = self._render()
        self.assertEqual(
            payload["persona"],
            {
                "background": None,
                "personality": None,
                "life_story": None,
                "habit": None,
            },
        )


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_structural_or_non_string_persona_values_degrade_to_null(self):
        self.player.db.persona = {
            "identity": {},
            "personality": 42,
            "life_story": "",
            "habit": "",
            "appearance": {},
            "social_connection": {},
            "background": "",
        }
        payload = self._render()
        self.assertEqual(payload["persona"]["personality"], None)


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_over_bound_persona_text_fails_the_panel_closed(self):
        self.player.db.persona = {
            "identity": {},
            "personality": "長" * (MAX_PERSONA_FIELD_CODE_POINTS + 1),
            "life_story": "",
            "habit": "",
            "appearance": {},
            "social_connection": {},
            "background": "",
        }
        payload = self._render()
        self.assertFalse(payload["available"])


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
        self.assertEqual(_flattened_keys(payload["passives"]), ["no_such_skill"])
        fallback = next(
            category for category in payload["passives"]
            if category["category"] == "unknown"
        )
        self.assertEqual(fallback["label"], "未知技能")
        self.assertEqual(fallback["groups"][0]["skills"][0]["label"], "no_such_skill")
        self.assertNotIn(
            "no_such_skill",
            _flattened_keys(payload["actives"]),
            "an unknown passive key must not leak into the actives listing",
        )


    def test_read_model_failure_renders_unavailable(self):
        with patch(
            "web.webclient.presentation.character.build_character_read_model",
            side_effect=StatusQueryError("broken"),
        ):
            payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("traits", payload)


    def test_active_skill_rows_are_enriched_by_the_registry(self):
        payload = self._render()
        row = next(
            r
            for c in payload["actives"]
            for g in c["groups"]
            for r in g["skills"]
            if r["key"] == T_EMBER
        )
        # Enrichment mirrors the live row: the kit burst's own cost/target
        # ride the wire (no shipped pricing numbers anywhere).
        self.assertEqual(row["cost"], dict(_live_skill_registry()[T_EMBER].cost))
        self.assertEqual(row["target_spec"], "single")
        # The kit burst carries a DamageEffect: skill-field-availability
        # flipped every damage-carrying skill to selectable-outside-combat
        # (the damaging-action gate, not this flag, confines it to a
        # battlefield).
        self.assertIs(row["usable_out_of_combat"], True)
        self.assertNotIn("freeform_scales", row)
        # Passive rows stay bare {key, label}.
        for c in payload["passives"]:
            for g in c["groups"]:
                for r in g["skills"]:
                    self.assertEqual(set(r), {"key", "label"})


    def test_freeform_scales_populated_for_mastery_holder(self):
        # The kit burst's derived tip cap is Lv.3 (the file-local mastery
        # passive's consuming edge), so the ladder can never unlock above
        # the 1.0 rung for it (use-driven-skill-lineage D6: a ceiling is
        # the max consuming edge). Entitlement is the registry-idiom
        # element-mastery passive ownership (direct, never conferred); the
        # entitlement query never resolves the row through the catalog, and
        # the ladder's mp_costs scale the burst's own registered cost.
        grant_lineage(
            self.player,
            [T_EMBER],
            [T_STEADY, _element_mastery_key()],
            rungs={T_EMBER: 3},
        )
        payload = self._render()
        row = next(
            r
            for c in payload["actives"]
            for g in c["groups"]
            for r in g["skills"]
            if r["key"] == T_EMBER
        )
        # Ladder rungs available at the Lv.3 ceiling: 0.25/0.5/1.0.
        base_mp = int(_live_skill_registry()[T_EMBER].cost["mp"])
        self.assertEqual(
            [entry["mp_cost"] for entry in row["freeform_scales"]],
            [max(1, math.floor(base_mp * scale + 0.5)) for scale in (0.25, 0.5, 1)],
        )


    def test_unregistered_active_key_stays_bare_in_presenter(self):
        self.player.db.skills = {"active": ["no_such_skill"], "passive": []}
        payload = self._render()
        fallback = next(c for c in payload["actives"] if c["category"] == "unknown")
        self.assertEqual(
            fallback["groups"][0]["skills"][0],
            {"key": "no_such_skill", "label": "no_such_skill"},
        )


if __name__ == "__main__":
    unittest.main()
