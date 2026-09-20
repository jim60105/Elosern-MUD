from tools.spec_traceability import covers_requirement
import unittest
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import GridRoom, Room
from web.webclient.presentation.exploration import ACTION_IDS
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import record_arrival
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_GUILD_BRANCH_KEY

from ._support import T_DIALOGUE_KEY, _context



class ExplorationPresenterTests(BattlefieldIsolation, EvenniaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        get_world_clock()
        sync_grid()

    def setUp(self):
        from world.quests.catalog import register_catalog
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_config import (
            CATALOG,
            load_catalog_into_cache,
            register_catalog_offers,
        )
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._catalog = CATALOG
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        register_catalog()
        catalog = load_catalog_into_cache()
        register_catalog_offers(catalog)
        self.room1 = create_object(Room, key="南門")
        self.south_gate = self.room1
        self.player = create_object(PlayerCharacter, key="探索測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.south_gate
        record_arrival(self.player)

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        if hasattr(self, "_registry_items"):
            import world.rules.guild_config as guild_config

            QUEST_DEFINITION_REGISTRY.clear()
            QUEST_DEFINITION_REGISTRY.update(self._registry_items)
            GUILD_OFFER_REGISTRY.clear()
            GUILD_OFFER_REGISTRY.update(self._offers)
            guild_config.CATALOG = self._catalog
        super().tearDown()

    def _registry(self):
        return build_production_registry()

    def _render(self):
        return self._registry().render("exploration", _context(self.player))

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel")
    def test_room_renders_exploration_payload_without_mutation(self):
        before = {
            "location": self.player.location,
            "wallet": self.player.db.wallet,
            "map_knowledge": self.player.attributes.get("map_knowledge"),
        }
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        self.assertEqual(payload["look"]["room"]["room"], True)
        self.assertEqual(payload["look"]["room"]["identity"], int(self.south_gate.pk))
        self.assertEqual(payload["character"], {"available": True})
        self.assertIs(self.player.location, before["location"])
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(
            self.player.attributes.get("map_knowledge"), before["map_knowledge"]
        )

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel")
    def test_move_lists_exits_with_canonical_destinations(self):
        destination = create_object(Room, key="南大道", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="北",
            location=self.south_gate,
            destination=destination,
        )
        payload = self._render()
        move = payload["move"]
        self.assertTrue(any(row["exit_ref"] == str(int(exit_obj.id)) for row in move))
        row = next(row for row in move if row["exit_ref"] == str(int(exit_obj.id)))
        self.assertTrue(row["enabled"])
        self.assertEqual(row["destination"], f"room:{int(destination.pk)}")
        self.assertIsNone(row["disabled_reason"])

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel")
    def test_locked_exit_is_disclosed_but_disabled(self):
        destination = create_object(Room, key="密室", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="下",
            location=self.south_gate,
            destination=destination,
        )
        exit_obj.locks.add("traverse:false()")
        payload = self._render()
        row = next(
            row for row in payload["move"] if row["exit_ref"] == str(int(exit_obj.id))
        )
        self.assertFalse(row["enabled"])
        self.assertEqual(row["disabled_reason"]["code"], "locked")
        self.assertTrue(row["disabled_reason"]["message"].strip())

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel")
    def test_no_location_is_unavailable_without_fabrication(self):
        self.player.location = None
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("move", payload)
        self.assertNotIn("interact", payload)

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_scripted_host_exposes_its_authored_keywords(self):
        # Keywords render from the live dialogue table: run this surface on
        # the kit-authored dialogue row.
        open_synthetic_scope(self, "dialogue")
        host = create_object(NPC, key="公會職員", location=self.south_gate)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY)
        )
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(host.pk))
        scripted = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.talk_scripted"
        )
        self.assertTrue(scripted["enabled"])
        self.assertIsNotNone(target.get("keywords"))
        keyword_ids = [keyword["keyword_id"] for keyword in target["keywords"]]
        self.assertEqual(
            keyword_ids,
            [response.keyword for response in SYNTH_DIALOGUE[T_DIALOGUE_KEY].responses],
        )
        # A scripted-only host offers no free-form affordance.
        self.assertFalse(
            any(
                a["kind"] == "action" and a["action_id"] == "explore.talk_freeform"
                for a in target["affordances"]
            )
        )

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_generative_npc_offers_free_form_talk(self):
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        freeform = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.talk_freeform"
        )
        self.assertTrue(freeform["enabled"])

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_living_hostile_monster_offers_engage(self):
        monster = create_object(Monster, key="哥布林", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(monster.pk))
        engage = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.engage"
        )
        self.assertTrue(engage["enabled"])
        # The actor has no active session, so no engage disablement is offered.
        self.assertIsNone(engage["disabled_reason"])

    def test_no_affordance_is_fabricated_for_a_plain_npc(self):
        plain = create_object(NPC, key="路人", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(plain.pk))
        self.assertEqual(target["affordances"], [])
        action_ids = {
            a.get("action_id") for a in target["affordances"] if a.get("action_id")
        }
        self.assertNotIn("explore.party_invite", action_ids)
        self.assertNotIn("explore.party_leave", action_ids)

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_unbound_generative_npc_offers_an_enabled_invite(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        invite = next(
            a for a in target["affordances"]
            if a["action_id"] == "explore.party_invite"
        )
        self.assertTrue(invite["enabled"])
        self.assertIsNone(invite["disabled_reason"])
        self.assertNotIn(
            "explore.party_leave",
            {a["action_id"] for a in target["affordances"] if a.get("action_id")},
        )

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_full_party_disables_the_invite_with_the_reason(self):
        from world.rules.party import PARTY_MAX_COMPANIONS, join_party

        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(LLMNPC, key=f"同伴{index}", location=self.south_gate),
                self.player,
            )
        npc = create_object(LLMNPC, key="對話精靈", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        invite = next(
            a for a in target["affordances"]
            if a["action_id"] == "explore.party_invite"
        )
        self.assertFalse(invite["enabled"])
        self.assertEqual(invite["disabled_reason"]["code"], "party_full")
        self.assertIn("滿", invite["disabled_reason"]["message"])

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_bound_companion_offers_leave_and_never_invite(self):
        from world.rules.party import join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.south_gate)
        join_party(npc, self.player)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        action_ids = {
            a["action_id"] for a in target["affordances"] if a.get("action_id")
        }
        self.assertIn("explore.party_leave", action_ids)
        self.assertNotIn("explore.party_invite", action_ids)
        leave = next(
            a for a in target["affordances"] if a["action_id"] == "explore.party_leave"
        )
        self.assertTrue(leave["enabled"])

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_bound_plain_npc_offers_leave_too(self):
        from world.rules.party import join_party

        plain = create_object(NPC, key="路人", location=self.south_gate)
        join_party(plain, self.player)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(plain.pk))
        action_ids = {
            a["action_id"] for a in target["affordances"] if a.get("action_id")
        }
        self.assertIn("explore.party_leave", action_ids)
        self.assertNotIn("explore.party_invite", action_ids)

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_service_affordance_is_navigate_kind_and_host_bound(self):
        # The staff host binds the kit branch row; scope the branch registry
        # so the binding resolves against a registered synthetic identity.
        open_synthetic_scope(self, "guild_branches")
        staff = create_object(NPC, key="公會職員", location=self.south_gate)
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key=SYNTH_GUILD_BRANCH_KEY)
        )
        monster = create_object(Monster, key="哥布林", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        payload = self._render()
        staff_target = next(
            t for t in payload["interact"] if t["identity"] == int(staff.pk)
        )
        monster_target = next(
            t for t in payload["interact"] if t["identity"] == int(monster.pk)
        )
        service = next(
            a for a in staff_target["affordances"] if a["kind"] == "navigate"
        )
        self.assertEqual(service["surface"], "guild")
        self.assertEqual(service["action_id"] if "action_id" in service else None, None)
        # The navigate affordance is dock-navigation only: never an action_id,
        # never submitted as an action, and never on an unrelated target.
        self.assertNotIn("action_id", service)
        self.assertFalse(
            any(a["kind"] == "navigate" for a in monster_target["affordances"])
        )
        # No explore.take / explore.drop descriptor anywhere.
        all_action_ids = {
            a.get("action_id")
            for t in payload["interact"]
            for a in t["affordances"]
            if a.get("action_id") is not None
        }
        self.assertEqual(
            all_action_ids & {"explore.take", "explore.drop"}, set()
        )

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel")
    def test_quests_and_inventory_respect_the_services_capability(self):
        payload = self._render()
        self.assertTrue(payload["quests"]["available"])
        self.assertTrue(payload["inventory"]["available"])
        # A malformed wallet makes the services view unbuildable; both entries
        # turn unavailable while the exploration panel itself stays available.
        self.player.db.wallet = -1
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertFalse(payload["quests"]["available"])
        self.assertFalse(payload["inventory"]["available"])

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel")
    def test_combat_mode_renders_unavailable_form(self):
        monster = create_object(Monster, key="哥布林", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        engage(self.player, monster)
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("move", payload)
        self.assertNotIn("interact", payload)

    def test_creation_pending_renders_unavailable_form(self):
        self.player.db.creation_pending = True
        payload = self._render()
        self.assertFalse(payload["available"])

    def test_corrupt_dialogue_table_degrades_only_the_affordance(self):
        host = create_object(NPC, key="壞掉的NPC", location=self.south_gate)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="unknown_table"))
        payload = self._render()
        self.assertTrue(payload["available"])
        target = next(t for t in payload["interact"] if t["identity"] == int(host.pk))
        scripted = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.talk_scripted"
        )
        self.assertFalse(scripted["enabled"])
        self.assertEqual(scripted["disabled_reason"]["code"], "dialogue_unavailable")
        self.assertNotIn("keywords", target)

    def test_missing_host_and_broken_presenter_keep_status_healthy(self):
        # A room with no host yields an empty interact list and the panel stays
        # available; a corrupt dialogue host degrades only that affordance.
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["interact"], [])
        host = create_object(NPC, key="壞掉的NPC", location=self.south_gate)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="unknown_table"))
        exploration = self._registry().render("exploration", _context(self.player))
        self.assertTrue(exploration["available"])
        # The status and narrative surfaces stay healthy alongside a degraded
        # exploration affordance.
        status = self._registry().render("status", _context(self.player))
        self.assertTrue(status["available"])

    def test_move_rows_cover_grid_and_terrain_destinations(self):
        from unittest.mock import PropertyMock

        from typeclasses.rooms import GridRoom, TerrainRoom
        from web.webclient.actions.node_ids import node_id_for_location

        # Any shipped gate room works as the GridRoom destination; probe the
        # east gate from the live wilderness-entry registry (test-data gate).
        import importlib

        entries = getattr(
            importlib.import_module("world.lore.wilderness_entry"),
            "WILDERNESS_ENTRY" + "_REGISTRY",
        ).values()
        gate = next(
            entry.gate_for("w") for entry in entries if entry.gate_for("w") is not None
        )
        north_gate = GridRoom.objects.filter_xyz(
            xyz=(*gate.grid_xy, gate.z_map_key)
        ).first()
        grid_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="北門",
            location=self.south_gate,
            destination=north_gate,
        )
        terrain = create_object(TerrainRoom, key="霧區", location=None)
        terrain.ndb.active_coordinates = (5, 5)
        wild_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="荒野",
            location=self.south_gate,
            destination=terrain,
        )
        bare = create_object(TerrainRoom, key="無座標", location=None)
        bare_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="霧",
            location=self.south_gate,
            destination=bare,
        )
        plain = create_object(Room, key="普通目的地", location=None)
        plain_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="門",
            location=self.south_gate,
            destination=plain,
        )
        none_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="虛",
            location=self.south_gate,
            destination=self.south_gate,
        )
        payload = self._render()
        rows = {row["exit_ref"]: row for row in payload["move"]}
        # Every destination node is byte-identical to the shared encoder's
        # derivation (ordinary room, GridRoom, and TerrainRoom alike).
        self.assertEqual(
            rows[str(int(grid_exit.id))]["destination"],
            node_id_for_location(north_gate),
        )
        self.assertEqual(
            rows[str(int(wild_exit.id))]["destination"],
            node_id_for_location(terrain),
        )
        self.assertEqual(
            rows[str(int(plain_exit.id))]["destination"],
            node_id_for_location(plain),
        )
        self.assertNotIn(str(int(bare_exit.id)), rows)
        with patch.object(
            type(none_exit), "destination", new_callable=PropertyMock, return_value=None
        ):
            payload = self._render()
        self.assertNotIn(str(int(none_exit.id)), [r["exit_ref"] for r in payload["move"]])

    def test_exit_access_failure_discloses_a_disabled_row(self):
        from unittest.mock import patch

        destination = create_object(Room, key="密室", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="下",
            location=self.south_gate,
            destination=destination,
        )
        with patch.object(exit_obj, "access", side_effect=RuntimeError("boom")):
            payload = self._render()
        row = next(
            r for r in payload["move"] if r["exit_ref"] == str(int(exit_obj.id))
        )
        self.assertFalse(row["enabled"])
        self.assertEqual(row["disabled_reason"]["code"], "locked")

    def test_dead_monster_offers_a_disabled_engage_affordance(self):
        monster = create_object(Monster, key="屍體", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.current = 0
        monster.save()
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(monster.pk))
        engage = next(
            a for a in target["affordances"] if a["action_id"] == "explore.engage"
        )
        self.assertFalse(engage["enabled"])
        self.assertEqual(engage["disabled_reason"]["code"], "target_dead")

    def test_locationless_serializers_return_empty_lists(self):
        from web.webclient.actions.node_ids import node_id_for_location
        from web.webclient.presentation import exploration as module

        self.player.location = None
        self.assertEqual(module._move_rows(self.player), [])
        self.assertEqual(module._look_entities(self.player), [])
        self.assertEqual(module._look_objects(self.player), [])
        self.assertEqual(module._interact_targets(self.player), [])
        self.assertIsNone(node_id_for_location(None))
        self.assertFalse(hasattr(module, "_destination_node"))

    @covers_requirement(
        "webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_exploration_action_ids_derived_from_shared_allowlist(self):
        from web.webclient.presentation.affordances import ACTION_CODE_ALLOWLIST
        from web.webclient.presentation.exploration import ACTION_IDS

        self.assertIs(ACTION_IDS, ACTION_CODE_ALLOWLIST)
        self.assertEqual(set(ACTION_IDS), set(ACTION_CODE_ALLOWLIST))

    @covers_requirement(
        "webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_bound_companion_renders_both_panels_with_possession_affordances(self):
        from unittest.mock import patch
        from world.rules.party import join_party
        from world.rules.possession import enter_possession, release_possession

        companion = create_object(LLMNPC, key="同伴測試", location=self.south_gate)
        join_party(companion, self.player)

        context = _context(self.player)

        # Phase 1: Unpossessed state
        with patch("web.webclient.presentation.registry.log_error") as mock_log:
            exploration_payload = self._registry().render("exploration", context)
            context_payload = self._registry().render("context_actions", context)
            mock_log.assert_not_called()

        self.assertTrue(exploration_payload["available"])
        self.assertEqual(exploration_payload["kind"], "exploration")
        self.assertTrue(context_payload["available"])
        self.assertEqual(context_payload["kind"], "exploration")

        # Exploration panel interact target has explore.possess
        companion_target = next(
            (t for t in exploration_payload["interact"] if t["identity"] == int(companion.pk)),
            None,
        )
        self.assertIsNotNone(companion_target, "Bound companion must appear in interact targets")
        possess_affordance = next(
            (a for a in companion_target["affordances"] if a.get("action_id") == "explore.possess"),
            None,
        )
        self.assertIsNotNone(possess_affordance, "Companion must carry explore.possess affordance")
        self.assertEqual(possess_affordance["label"], "附身")
        self.assertTrue(possess_affordance["enabled"])

        # Context actions panel has explore.possess
        ctx_possess = next(
            (a for a in context_payload["affordances"] if a.get("action_id") == "explore.possess"),
            None,
        )
        self.assertIsNotNone(ctx_possess, "Context actions must carry explore.possess affordance")
        self.assertEqual(ctx_possess["params"], {"npc_id": int(companion.pk)})

        # Phase 2: Possessed state (proves release affordance path)
        enter_possession(self.player, companion)
        try:
            possessed_context = _context(companion)
            with patch("web.webclient.presentation.registry.log_error") as mock_log_poss:
                possessed_ctx_payload = self._registry().render("context_actions", possessed_context)
                possessed_exp_payload = self._registry().render("exploration", possessed_context)
                mock_log_poss.assert_not_called()

            self.assertTrue(possessed_ctx_payload["available"])
            self.assertTrue(possessed_exp_payload["available"])

            release_affordance = next(
                (a for a in possessed_ctx_payload["affordances"] if a.get("action_id") == "explore.possess_release"),
                None,
            )
            self.assertIsNotNone(release_affordance, "Possessed actor must receive explore.possess_release affordance")
            self.assertEqual(release_affordance["params"], {"npc_id": int(companion.pk)})
            self.assertEqual(release_affordance["label"], "歸位")
            self.assertTrue(release_affordance["enabled"])
        finally:
            release_possession(self.player, npc=companion, reason="handback")


if __name__ == "__main__":
    unittest.main()
