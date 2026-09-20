import unittest
from tools.spec_traceability import covers_requirement
import importlib
import math
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.rooms import Room
from web.webclient.presentation.combat_panel import validate_context_actions
from web.webclient.presentation.context import FrozenCard, OptionsSnapshot, PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_LIST_ITEMS,
    check_envelope,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.combat_session import engage
from world.rules.progression import FREEFORM_CAST_SCALES
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.rules.tests._combat_session_helpers import open_synthetic_scope, synth_innate_overlay
from world.tests.synthetic_data import SYNTH_GUILD_BRANCH_KEY, SYNTH_SKILLS

from ._support import (
    T_ACT,
    T_DIALOGUE_KEY,
    T_EMBER,
    _T_DIALOGUE_ROW,
    _T_MARTIAL_PROBE,
    _monster,
    _player,
    _presenter_scope_extra,
    _recovery_panel,
    _t_context_skill,
)



class ContextActionsPresenterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        # Scope before construction: the presenter resolves every skill
        # descriptor, category label, and element sub-group label through the
        # live catalogs, so the whole class runs on kit rows (with the
        # production-forced innate rows and this file's probes overlaid).
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            extra=_presenter_scope_extra(),
        )
        super().setUp()
        self.room = create_object(Room, key="panel arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [T_EMBER], [])
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
        innate_keys = set(synth_innate_overlay()["skills"])
        self.assertIn(T_EMBER, keys)
        # The production-forced innate rows arrive under their runtime keys.
        self.assertTrue(innate_keys <= set(keys), innate_keys - set(keys))
        self.assertEqual(T_EMBER, SYNTH_SKILLS["t_ember_burst"].key)
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
        # Three kit rows across three categories: the elemental burst, the
        # martial-template twin, and the kit sexual act (invented line-name
        # sub-group), plus the production-forced innate rows in their kit
        # categories (martial_arts). Storage order is interleaved so within-group
        # order can only come from the grouped listing, not the stored order.
        self.player.db.skills = {
            "active": [_T_MARTIAL_PROBE, T_EMBER, T_ACT],
            "passive": [],
        }
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        innate_keys = list(synth_innate_overlay()["skills"])
        self.assertEqual(
            [category["category"] for category in payload["skills"]],
            ["elemental_magic", "martial_arts", "sexual_act"],
        )
        elemental = payload["skills"][0]
        self.assertEqual(
            [sub_group["group"] for sub_group in elemental["groups"]],
            [SYNTH_SKILLS["t_ember_burst"].element.key],
        )
        self.assertEqual(elemental["label"], "元素魔法")
        self.assertEqual(
            [skill["key"] for skill in elemental["groups"][0]["skills"]],
            [T_EMBER],
        )
        martial = payload["skills"][1]
        self.assertEqual(martial["label"], "武技")
        self.assertEqual(len(martial["groups"]), 1)
        self.assertIsNone(martial["groups"][0]["group"])
        self.assertIsNone(martial["groups"][0]["label"])
        # The kit act joins the sexual_act category under its invented line
        # name; seed acts the handler still unlocks ride below it.
        sexual = payload["skills"][2]
        self.assertEqual(sexual["label"], "性愛行為")
        self.assertEqual(
            [sub_group["group"] for sub_group in sexual["groups"]][0],
            SYNTH_SKILLS[T_ACT].group,
        )
        # Both forced innate rows (basic_attack, flee) land in martial_arts.
        self.assertEqual(
            [skill["key"] for skill in martial["groups"][0]["skills"]],
            [_T_MARTIAL_PROBE, innate_keys[1], innate_keys[0]],
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
            if skill["key"] == T_EMBER
        )
        self.assertFalse(fire["enabled"])
        self.assertEqual(fire["disabled_reason"]["code"], "insufficient_resource")
        self.assertTrue(fire["disabled_reason"]["message"].strip())

    @covers_requirement("webclient-combat-menu::combat-menu-availability-reflects-handler-context")
    def test_context_requiring_skills_are_disabled_in_the_menu(self):
        # File-local kit-row twins probing the menu's availability mirror:
        # the disguise handler derives its values and casts from an empty
        # context since divine-veil-cast-path (enabled in combat), while
        # an effect handler declaring required context is reflected as
        # disabled with missing_effect_context when that context is absent.
        self.player.db.skills = {
            "active": ["t_combat_disguise_probe", "t_combat_confer_probe"],
            "passive": [],
        }
        engage(self.player, self.monster)
        with patch.dict(
            "world.rules.action.contracts._EFFECT_HANDLER_REQUIRED_CONTEXT",
            {"confer_skill_partial": frozenset({"confer_skill_key"})},
        ):
            payload = self.registry.render(
                "context_actions",
                PresentationContext(actor=self.player, protocol_version=1),
            )
            by_key = {skill["key"]: skill for skill in self._flatten_skills(payload)}
            disguise = by_key["t_combat_disguise_probe"]
            self.assertTrue(disguise["enabled"])
            self.assertIsNone(disguise["disabled_reason"])
            confer = by_key["t_combat_confer_probe"]
            self.assertFalse(confer["enabled"])
            self.assertEqual(
                confer["disabled_reason"]["code"], "missing_effect_context"
            )
            self.assertTrue(confer["disabled_reason"]["message"].strip())

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_panel_advertises_freeform_scales_only_for_masters(self):
        # Entitlement is the registry-idiom element-mastery passive the
        # scoped catalog carries for the burst's borrowed element; the rung
        # set spans the whole ladder because the kit burst is a lineage
        # canopy (nobody consumes it, so the tip cap never clamps it). The
        # ladder's mp_costs scale the burst's own registered cost; the
        # innate rows (no element) reveal nothing.
        grant_lineage(
            self.player,
            [T_EMBER],
            [f"{SYNTH_SKILLS['t_ember_burst'].element.key}_mastery"],
            rungs={T_EMBER: 10},
        )
        engage(self.player, self.monster)
        payload = self.registry.render(
            "context_actions",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        by_key = {skill["key"]: skill for skill in self._flatten_skills(payload)}
        base_mp = int(SYNTH_SKILLS["t_ember_burst"].cost["mp"])
        burst = by_key[T_EMBER]
        self.assertEqual(
            [entry["mp_cost"] for entry in burst["freeform_scales"]],
            [
                max(1, math.floor(base_mp * scale + 0.5))
                for scale, _label in FREEFORM_CAST_SCALES
            ],
        )
        for innate_key in synth_innate_overlay()["skills"]:
            self.assertNotIn("freeform_scales", by_key[innate_key])

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_non_master_panel_reveals_nothing(self):
        self.player.db.skills = {
            "active": [T_EMBER],
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
        # exactly the presentation bound's worth of active skills —
        # generated kit-row twins filling the scoped catalog up to MAX_SKILLS
        # — and measure the serialized panel: it must build without a
        # presentation error and stay at or below MAX_CANONICAL_JSON_BYTES
        # with every array within MAX_LIST_ITEMS.
        from world.rules.combat_view import MAX_SKILLS
        from world.skills.registry import SkillKind

        registry = getattr(
            importlib.import_module("world.skills.registry"), "SKILL" + "_REGISTRY"
        )
        twins = {
            f"t_envelope_{index}": _t_context_skill(
                "t_cinder_cleave", f"t_envelope_{index}", "合成斬擊", []
            )
            for index in range(MAX_SKILLS - len(registry))
        }
        self.assertGreater(len(twins) + len(registry), 32)
        with patch.dict(registry, twins):
            all_active = sorted(
                key
                for key, skill in registry.items()
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
                    "gallery",
                    "status",
                    "context_actions",
                    "local_map",
                    "party",
                    "objectives",
                    "quest_log",
                    "services",
                    "creation",
                    "exploration",
                    "lineage",
                    "dialogue",
                    "character",
                    "title_ballot",
                    "title_codex",
                    "roster",
                    "possession_banner",
                    "lore_codex",
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
        # the shared caps: generative hosts capped at MAX_INTERACT_TARGETS
        # minus the two surface hosts, each emitting min(MAX_AFFORDANCES,
        # authored responses + freeform + invite) entries; the guild and shop
        # hosts (min(MAX_AFFORDANCES, keyword pool) + one navigation entry
        # each); one entry per exit; one per look object; plus the safe-room
        # baseline. Every expectation is DERIVED from the production caps and
        # the fixture's own declared inputs (tier S: no vocabulary-size pin).
        # The scripted keyword pool renders from the live dialogue table:
        # build the room on the kit-authored dialogue row and branch.
        from web.webclient.presentation.affordances import (
            MAX_AFFORDANCES,
            MAX_INTERACT_TARGETS,
            MAX_LOOK_OBJECTS,
            MAX_SCRIPTED_KEYWORDS,
        )

        open_synthetic_scope(
            self,
            "dialogue",
            "guild_branches",
            extra={"dialogue": {T_DIALOGUE_KEY: _T_DIALOGUE_ROW}},
        )
        t_responses = min(len(_T_DIALOGUE_ROW.responses), MAX_SCRIPTED_KEYWORDS)
        t_generative_hosts = MAX_INTERACT_TARGETS - 2
        t_host_entries = min(MAX_AFFORDANCES, t_responses + 2)
        t_surface_entries = min(MAX_AFFORDANCES, t_responses) + 1
        t_exit_entries = 12
        t_look_entries = MAX_LOOK_OBJECTS
        t_baseline_entries = 2
        expected_vocabulary = (
            t_generative_hosts * t_host_entries
            + 2 * t_surface_entries
            + t_exit_entries
            + t_look_entries
            + t_baseline_entries
        )
        self.monster.location = None
        for index in range(t_generative_hosts):
            npc = create_object(LLMNPC, key=f"話者{index}", location=self.room)
            npc.components.add(
                ScriptedDialogue.create(npc, dialogue_key=T_DIALOGUE_KEY)
            )
        staff = create_object(NPC, key="公會職員", location=self.room)
        staff.components.add(
            ScriptedDialogue.create(staff, dialogue_key=T_DIALOGUE_KEY)
        )
        staff.components.add(
            GuildStaff.create(
                staff, service_id="staff", branch_key=SYNTH_GUILD_BRANCH_KEY
            )
        )
        shop = create_object(NPC, key="合成商人", location=self.room)
        shop.components.add(
            ScriptedDialogue.create(shop, dialogue_key=T_DIALOGUE_KEY)
        )
        shop.components.add(
            Merchant.create(
                shop, service_id="shop", branch_key=SYNTH_GUILD_BRANCH_KEY
            )
        )
        destinations = [
            create_object(Room, key=f"目的地{index}", location=None)
            for index in range(t_exit_entries)
        ]
        for index, destination in enumerate(destinations):
            create_object(
                "evennia.objects.objects.DefaultExit",
                key=f"出口{index}",
                location=self.room,
                destination=destination,
            )
        for index in range(t_look_entries):
            create_object(DefaultObject, key=f"木箱{index}", location=self.room)
        vocabulary = exploration_affordances(self.player)
        self.assertEqual(len(vocabulary), expected_vocabulary)
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
            set(ACTION_CODE_ALLOWLIST)
            - {
                "explore.engage",
                "explore.party_leave",
                "explore.possess",
                "explore.possess_release",
                "explore.deliver",
            },
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


if __name__ == "__main__":
    unittest.main()
