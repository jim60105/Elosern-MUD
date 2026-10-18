"""Character panel presenter tests: viewed member, conditions, and disguise."""
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from web.webclient.presentation.character import CHARACTER_SCHEMA_VERSION
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.party import join_party
from world.rules.status_query import StatusQueryError
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from ._support import (
    BRANCH,
    T_EMBER,
    T_STEADY,
    _T_ITEM_DISPLAY,
    _T_PANEL_RITE_A,
    _T_PANEL_RITE_B,
    _T_THORN,
    _cap_roster_rows,
    _context,
    _element_mastery_key,
    _flattened_keys,
    _innate_key,
    _live_skill_registry,
    _scope_extra,
    _unlock_free_act_keys,
)
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


    def _render(self, *, actor=None, member=None):
        """Render the panel for ``member`` as the session's viewed member."""
        selection = (
            None
            if member is None
            else PartyViewSelection(int(self.player.pk), int(member.pk), "status")
        )
        context = PresentationContext(
            actor=actor or self.player,
            protocol_version=1,
            party_view=selection,
        )
        return self._registry().render("character", context)

    @covers_requirement(
        "skill-identity-eligibility::player-catalogs-and-lineage-use-identity-filtering"
    )
    def test_identity_ineligible_owned_rows_are_absent_from_character_catalog(self):
        from dataclasses import replace
        from world.skills.registry import SkillEligibility

        registry = _live_skill_registry()
        rows = {
            key: replace(registry[key], eligibility=SkillEligibility(
                allowed_actor_kinds=("monster",),
            ))
            for key in (T_EMBER, T_STEADY)
        }
        with patch.dict(registry, rows):
            payload = self._render()
            self.assertTrue(payload["available"])
            self.assertNotIn(T_EMBER, _flattened_keys(payload["actives"]))
            self.assertNotIn(T_STEADY, _flattened_keys(payload["passives"]))


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
    def test_character_renders_true_values_without_mutation(self):
        before_traits = dict(self.player.attributes.get("traits", category="traits"))
        before_wallet = self.player.db.wallet
        before_equipment = self.player.db.equipment
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "character")
        self.assertEqual(payload["schema_version"], CHARACTER_SCHEMA_VERSION)
        self.assertEqual(payload["member_id"], int(self.player.pk))
        self.assertIsInstance(payload["conditions"], list)
        # Persona prose and intimate state belong to `party_member` now.
        self.assertNotIn("persona", payload)
        self.assertNotIn("intimate", payload)
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

    def test_character_renders_zero_maximum_gauge_as_available(self):
        traits = dict(self.player.attributes.get("traits", category="traits"))
        traits["mp"] = {"base": 0, "mod": 0, "mult": 1, "current": 0}
        self.player.attributes.add("traits", traits, category="traits")
        payload = self._render()
        self.assertTrue(payload["available"])
        mp_row = next(row for row in payload["traits"] if row["key"] == "mp")
        self.assertEqual(mp_row["max"], 0)
        self.assertEqual(mp_row["current"], 0)
        self.assertEqual(mp_row["effective"], 0)
        self.assertEqual(mp_row["layers"], [])


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


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
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


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
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


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
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


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
    def test_persona_record_never_leaks_into_the_payload(self):
        self.player.db.persona = {
            "identity": {"public_view": {"name": "甲"}},
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
            "appearance": {},
            "social_connection": {},
            "background": "渡口成長的灰誓成員",
        }
        payload = self._render()
        self.assertTrue(payload["available"])
        for key in (
            "persona",
            "intimate",
            "identity",
            "appearance",
            "social_connection",
            "background",
            "personality",
            "life_story",
            "habit",
        ):
            with self.subTest(key=key):
                self.assertNotIn(key, payload)


    def _companion(self, key="艾拉"):
        companion = create_object(NPC, key=key, location=self.room1)
        companion.race = "human"
        companion.apply_race_baseline()
        self.player.location = self.room1
        join_party(companion, self.player)
        return companion


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
    def test_the_panel_follows_the_viewed_companion(self):
        companion = self._companion()
        payload = self._render(member=companion)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["member_id"], int(companion.pk))
        # Every section is the companion's own: the commander's wallet and
        # guild rank never substitute for it.
        self.assertEqual(payload["wallet"], 0)
        self.assertIsNone(payload["guild"]["rank"])
        hp = next(row for row in payload["traits"] if row["key"] == "hp")
        self.assertEqual(hp["current"], companion.traits.hp.current)
        # The selection falls back to the commander once the member leaves.
        from world.rules.party import leave_party

        leave_party(companion, self.player, "dismissal")
        fallback = self._render(member=companion)
        self.assertEqual(fallback["member_id"], int(self.player.pk))


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
    def test_the_payload_is_identical_with_and_without_possession(self):
        from world.rules.possession import enter_possession, release_possession

        companion = self._companion()
        before = self._render(member=companion)
        possessor = self._companion("卡恩")
        self.player.location = self.room1
        enter_possession(self.player, possessor)
        try:
            while_possessing = self._render(actor=possessor, member=companion)
        finally:
            release_possession(self.player)
        self.assertEqual(while_possessing, before)


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
    def test_combat_keeps_the_panel_available(self):
        from typeclasses.monsters import Monster

        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        self.player.location = self.room1
        engage(self.player, monster)
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertTrue(payload["traits"])
        self.assertEqual(payload["member_id"], int(self.player.pk))


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
    def test_conditions_carry_buff_and_indefinite_rule_rows(self):
        from types import SimpleNamespace

        from world.rules.buffs import apply_buff
        from world.rules.combat_modifiers import Rule
        from world.rules.status_display import display_for

        apply_buff(self.player, "water_film")
        rules = [
            Rule(
                "t_fatigue",
                {"buff_active": "water_film"},
                {"accuracy": -2},
            )
        ]

        def fake_display(code):
            if code == "t_fatigue":
                return SimpleNamespace(label="合成疲勞", severity="warning")
            return display_for(code)

        with patch("world.rules.combat_modifiers._RULES", rules), patch(
            "world.rules.status_query.conditions.display_for",
            side_effect=fake_display,
        ):
            payload = self._render()
        self.assertTrue(payload["available"])
        rows = {row["code"]: row for row in payload["conditions"]}
        # The buff row carries its registry label/severity, the definition's
        # remaining duration, and its own-state origin.
        buff = rows["water_film"]
        self.assertEqual(buff["severity"], "beneficial")
        self.assertEqual(buff["remaining_seconds"], 60)
        self.assertEqual(buff["modifiers"], {})
        self.assertEqual(buff["source"], "狀態")
        # The rule row is indefinite and carries its canonical modifier value
        # verbatim.
        rule = rows["t_fatigue"]
        self.assertEqual(rule["severity"], "warning")
        self.assertIsNone(rule["remaining_seconds"])
        self.assertEqual(rule["modifiers"], {"accuracy": -2})
        self.assertEqual(rule["source"], "狀態")
        # The status panel's deterministic order: buffs, then matched rules.
        self.assertEqual(
            [row["code"] for row in payload["conditions"]],
            ["water_film", "t_fatigue"],
        )


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
        # Enrichment mirrors the live row: the kit burst's own target rides the
        # wire, and its cost is the actor's effective one — the resolver's own
        # adjusted amount (the equipped kit dagger's percent adjustment
        # included), which is the base the freeform rungs would scale.
        from world.rules.action_preview import adjusted_cost

        effective = adjusted_cost(self.player, _live_skill_registry()[T_EMBER])
        self.assertEqual(row["cost"], effective)
        self.assertNotEqual(
            effective,
            dict(_live_skill_registry()[T_EMBER].cost),
            "the equipped percent cost adjustment must move the presented cost",
        )
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
        # Ladder rungs available at the Lv.3 ceiling: 0.25/0.5/1.0. Each rung
        # scales the actor's EFFECTIVE cost: the kit burst declares 12 MP and
        # the equipped kit dagger adjusts it by −5%, so the base the rungs
        # scale is 11 and the rounded rungs are 3, 6 and 11.
        self.assertEqual(row["cost"], {"mp": 11})
        self.assertEqual(
            [entry["mp_cost"] for entry in row["freeform_scales"]],
            [3, 6, 11],
        )


    def test_unregistered_active_key_stays_bare_in_presenter(self):
        self.player.db.skills = {"active": ["no_such_skill"], "passive": []}
        payload = self._render()
        fallback = next(c for c in payload["actives"] if c["category"] == "unknown")
        self.assertEqual(
            fallback["groups"][0]["skills"][0],
            {"key": "no_such_skill", "label": "no_such_skill"},
        )


    @covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")
    def test_progressed_active_roster_above_32_renders_the_available_panel(self):
        # The regression: a roster the read model legitimately assembles above
        # the old 32-row bound (stored keys + the innate grants + the
        # unlock-free catalogue act) must render the available panel with
        # every row present — never the internal-unavailable fail-closed
        # payload the old bound produced for a progressed character.
        rows = _cap_roster_rows()
        stored = sorted(rows)
        with patch.dict(_live_skill_registry(), rows):
            self.player.db.skills = {"active": stored, "passive": []}
            payload = self._render()
        self.assertTrue(payload["available"])
        flattened = _flattened_keys(payload["actives"])
        expected = {
            *stored,
            _innate_key("world.rules.disengage", "FLEE_SKILL" + "_KEY"),
            _innate_key("world.rules.combat_session", "BASIC" + "_ATTACK_KEY"),
            *_unlock_free_act_keys(),
        }
        self.assertGreater(len(expected), 32)
        self.assertEqual(sorted(flattened), sorted(expected))
        # Every row survives the full validator, enriched like any registry
        # row rather than degrading to the bare unregistered-key shape.
        row = next(
            r
            for c in payload["actives"]
            for g in c["groups"]
            for r in g["skills"]
            if r["key"] in rows
        )
        self.assertEqual(
            set(row),
            {"key", "label", "cost", "target_spec", "usable_out_of_combat"},
        )
        # The declared 12 MP carries the equipped kit dagger's −5% adjustment
        # like every other presented row.
        self.assertEqual(row["cost"], {"mp": 11})
        self.assertEqual(row["target_spec"], "single")
        self.assertIs(row["usable_out_of_combat"], True)

    @covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")
    def test_holy_rite_rows_list_in_seventh_group_under_client_bound(self):
        # Kit holy-rite twins (null and 聖禮 groups) plus the kit enhancement
        # passive: only the seventh-category grouping rule is under test.
        self.player.db.skills = {
            "active": [_T_PANEL_RITE_A, _T_PANEL_RITE_B],
            "passive": [T_STEADY],
        }
        payload = self._render()
        holy_rite = payload["actives"][-1]
        self.assertEqual(holy_rite["category"], "holy_rite")
        self.assertEqual(holy_rite["label"], "神聖聖儀")
        self.assertEqual(
            [sub_group["group"] for sub_group in holy_rite["groups"]],
            [None, "聖禮"],
        )
        self.assertEqual(
            [sub_group["label"] for sub_group in holy_rite["groups"]],
            [None, "聖禮"],
        )
        self.assertEqual(
            [r["key"] for r in holy_rite["groups"][0]["skills"]],
            [_T_PANEL_RITE_A],
        )
        self.assertEqual(
            [r["key"] for r in holy_rite["groups"][1]["skills"]],
            [_T_PANEL_RITE_B],
        )
        self.assertNotIn(
            "holy_rite",
            [c["category"] for c in payload["passives"]],
        )
        enh = next(c for c in payload["passives"] if c["category"] == "enhancement")
        self.assertIn(T_STEADY, [r["key"] for g in enh["groups"] for r in g["skills"]])
        from web.webclient.presentation.character import validate_character
        normalized = validate_character(payload)
        self.assertEqual(normalized["actives"], payload["actives"])


if __name__ == "__main__":
    unittest.main()
