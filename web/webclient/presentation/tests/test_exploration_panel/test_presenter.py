from tools.spec_traceability import covers_requirement
import contextlib
import hashlib
import io
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
from django.test import override_settings
from PIL import Image
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
from world.art import official, official_refs
from world.art.gallery import append_card, record_for
from world.art.official import load_catalog, reset_catalog
from world.art.presenter import ORIGIN_OFFICIAL, ORIGIN_RUNTIME
from world.art.subjects import character_subject_for
from world.rules.art_view import portrait_catalog_key
from world.rules.clock import get_world_clock
from world.rules.dialogue import greeting_for, open_or_refresh_dialogue
from world.rules.map_knowledge import record_arrival
from world.rules.party import join_party
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_GUILD_BRANCH_KEY

from ._support import T_DIALOGUE_KEY, _context



# The official-art harness below mirrors ``test_party_panel.py`` (which mirrors
# ``world/art/tests/test_gallery_match.py``) with file-local identities: the
# preset key, named portrait stable key and record-default image identity are
# synthetic, never shipped content.
_PRESET_KEY = "t_synth_preset"
_COMPANION_KEY = "t_synth_companion"
_CARD_IMAGE_ID = "eeeeeeee-5555-4555-8555-555555555555"


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG: the official catalog reads the header only."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class _OfficialArt:
    """A synthetic official root beside an isolated runtime store."""

    def __init__(self, tempdir: Path) -> None:
        self.root = tempdir / "official"
        self.store = tempdir / "store"
        self.store.mkdir()

    @property
    def content(self) -> Path:
        return self.root / "preset" / _PRESET_KEY

    def mount(self, name="hero.png") -> str:
        """Write one admitted image and reload the catalog snapshot."""
        self.content.mkdir(parents=True, exist_ok=True)
        (self.content / name).write_bytes(_png())
        load_catalog()
        return f"preset/{_PRESET_KEY}/{name}"

    def write_store_file(self, identity: str, data=b"synthetic image") -> None:
        """Place one runtime file under the isolated store root."""
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


@contextlib.contextmanager
def _official_art_scope():
    """Isolate both artwork roots and admit one synthetic preset key."""
    with contextlib.ExitStack() as stack:
        tempdir = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        art = _OfficialArt(tempdir)
        stack.enter_context(
            override_settings(
                ART_OFFICIAL_ROOT=str(art.root),
                ART_STORE_ROOT=str(art.store),
            )
        )
        stack.enter_context(
            patch.object(
                official_refs, "PLAYER_PRESET_REGISTRY", {_PRESET_KEY: object()}
            )
        )
        stack.enter_context(
            patch.object(
                official,
                "_registered_preset_keys",
                return_value=frozenset({_PRESET_KEY}),
            )
        )
        official_refs._reported_unresolved.clear()
        stack.callback(official_refs._reported_unresolved.clear)
        reset_catalog()
        stack.callback(reset_catalog)
        yield art


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

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel")
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

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel")
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

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel")
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

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel")
    def test_no_location_is_unavailable_without_fabrication(self):
        self.player.location = None
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("move", payload)
        self.assertNotIn("interact", payload)

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_scripted_host_exposes_its_authored_keywords(self):
        # A scripted host's talk is exactly one 交談 explore.talk_open row on
        # the descriptor; the authored keywords are the OPEN dialogue panel's
        # choices, not a target-level list.
        open_synthetic_scope(self, "dialogue")
        host = create_object(NPC, key="公會職員", location=self.south_gate)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY)
        )
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(host.pk))
        self.assertNotIn("keywords", target)
        talk = [
            a
            for a in target["affordances"]
            if a["kind"] == "action" and a["action_id"] == "explore.talk_open"
        ]
        self.assertEqual(len(talk), 1)
        self.assertTrue(talk[0]["enabled"])
        self.assertIsNone(talk[0]["disabled_reason"])
        self.assertEqual(talk[0]["label"], "交談")
        # The single conversation row is listed before the other affordances.
        self.assertIs(target["affordances"][0], talk[0])
        # A scripted-only host offers no free-form affordance, and none of the
        # retired in-conversation codes reaches the descriptor.
        action_ids = {a.get("action_id") for a in target["affordances"]}
        self.assertNotIn("explore.talk_freeform", action_ids)
        self.assertNotIn("explore.talk_scripted", action_ids)
        # Once the conversation opens, the dialogue panel carries the authored
        # keyword choices.
        open_or_refresh_dialogue(self.player, host, greeting_for(host))
        dialogue = self._registry().render("dialogue", _context(self.player))
        self.assertEqual(
            [choice["keyword_id"] for choice in dialogue["choices"]],
            [response.keyword for response in SYNTH_DIALOGUE[T_DIALOGUE_KEY].responses],
        )

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_generative_npc_offers_free_form_talk(self):
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        talk = [
            a
            for a in target["affordances"]
            if a["kind"] == "action" and a["action_id"] == "explore.talk_open"
        ]
        self.assertEqual(len(talk), 1)
        self.assertTrue(talk[0]["enabled"])
        self.assertIs(target["affordances"][0], talk[0])
        self.assertNotIn("keywords", target)
        # The free-form surface is the open conversation's own free row, not a
        # target-level affordance.
        self.assertNotIn(
            "explore.talk_freeform",
            {a.get("action_id") for a in target["affordances"]},
        )

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_possessed_actor_sees_a_disabled_talk_open(self):
        from world.rules.party import join_party
        from world.rules.possession import enter_possession, release_possession

        # The possessed puppet still sees every conversable host, but its 交談
        # is the vocabulary's own possession refusal, never an enabled row.
        open_synthetic_scope(self, "dialogue")
        companion = create_object(LLMNPC, key="被附身者", location=self.south_gate)
        join_party(companion, self.player)
        host = create_object(NPC, key="公會職員", location=self.south_gate)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY)
        )
        enter_possession(self.player, companion)
        try:
            payload = self._registry().render("exploration", _context(companion))
        finally:
            release_possession(self.player, npc=companion, reason="handback")
        target = next(t for t in payload["interact"] if t["identity"] == int(host.pk))
        talk = next(
            a for a in target["affordances"] if a.get("action_id") == "explore.talk_open"
        )
        self.assertFalse(talk["enabled"])
        self.assertEqual(talk["disabled_reason"]["code"], "possessed_talk")
        self.assertTrue(talk["disabled_reason"]["message"].strip())

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
        self.assertEqual(
            target["affordances"],
            [
                {
                    "kind": "navigate",
                    "surface": "npc_persona",
                    "label": "編輯人物設定",
                    "enabled": False,
                    "disabled_reason": {
                        "code": "npc_persona.unavailable",
                        "message": "此角色的設定目前無法編輯或尚未初始化。",
                    },
                }
            ],
        )
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

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel")
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

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel")
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
        talk = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.talk_open"
        )
        self.assertFalse(talk["enabled"])
        self.assertEqual(talk["disabled_reason"]["code"], "dialogue_unavailable")
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
        "webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel"
    )
    def test_exploration_action_ids_derived_from_shared_allowlist(self):
        from web.webclient.presentation.affordances import ACTION_CODE_ALLOWLIST
        from web.webclient.presentation.exploration import ACTION_IDS

        # The panel's target-scoped list is the shared allowlist minus the two
        # codes v3 folds into one explore.talk_open 交談 row.
        self.assertEqual(
            set(ACTION_IDS),
            set(ACTION_CODE_ALLOWLIST)
            - {"explore.talk_scripted", "explore.talk_freeform"},
        )
        self.assertIn("explore.talk_open", ACTION_IDS)
        self.assertNotIn("explore.talk_scripted", ACTION_IDS)
        self.assertNotIn("explore.talk_freeform", ACTION_IDS)

    @covers_requirement(
        "webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel"
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


class ExplorationPortraitRefTests(BattlefieldIsolation, EvenniaTestCase):
    """Schema-4 server-authored portrait references over the current art view.

    The reference is the same opaque decimal catalog key the party row emits:
    membership follows ``build_art_view`` and eligibility follows one
    ``describe_entity``-backed membership fact per identity (its own URL with origin
    runtime/official). Every case asserts through the production presenter.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        get_world_clock()
        sync_grid()

    def setUp(self):
        self.south_gate = create_object(Room, key="肖像大廳")
        self.player = create_object(PlayerCharacter, key="肖像測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.south_gate
        record_arrival(self.player)

    def _named_host(self, key, stable):
        """A present named-policy conversable NPC: an art-view member that
        also carries interact descriptor rows."""
        npc = create_object(LLMNPC, key=key, location=self.south_gate)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.db.portrait_policy = {"mode": "named", "stable_key": stable}
        npc.db.age = npc.db.apparent_age = 30
        npc.db.creation_preset_key = _PRESET_KEY
        return npc

    def _registry(self):
        return build_production_registry()

    def _panels(self):
        registry = self._registry()
        context = _context(self.player)
        with patch("web.webclient.presentation.registry.log_error") as mock_log:
            exploration = registry.render("exploration", context)
            art = registry.render("art", context)
            mock_log.assert_not_called()
        return exploration, art

    def _rows_for(self, payload, npc):
        identity = int(npc.pk)
        entity = next(
            (row for row in payload["look"]["entities"] if row["identity"] == identity),
            None,
        )
        target = next(
            (row for row in payload["interact"] if row["identity"] == identity), None
        )
        return entity, target

    @staticmethod
    def _root_digests(art) -> dict:
        digests = {}
        for root in (art.root, art.store):
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    digests[path.relative_to(root.parent).as_posix()] = (
                        hashlib.sha256(path.read_bytes()).hexdigest()
                    )
        return digests

    @covers_requirement(
        "webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam"
    )
    def test_official_and_runtime_images_yield_catalog_refs_in_both_lists(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            official_host = self._named_host("官方肖像host", "t_synth_portrait_official")
            runtime_host = self._named_host("runtime肖像host", "t_synth_portrait_runtime")
            join_party(official_host, self.player)
            join_party(runtime_host, self.player)
            subject = character_subject_for(runtime_host)
            # The party harness's stored-card identity shape.
            stored = f"gallery/character/t_synth_portrait_runtime/{_CARD_IMAGE_ID}.png"
            art.write_store_file(stored)
            append_card(
                subject,
                image_id=_CARD_IMAGE_ID,
                stored_identity=stored,
                prompt=None,
                seed=None,
                checkpoint=None,
                requested_fields=[],
                binding=None,
                source="seed",
                created_at=100,
                image_size={"width": 768, "height": 1024},
            )

            before = self._root_digests(art)
            payload, art_panel = self._panels()
            after = self._root_digests(art)
            self.assertEqual(before, after)

            catalog = art_panel["portrait_catalog"]
            for npc, expected_origin in (
                (official_host, ORIGIN_OFFICIAL),
                (runtime_host, ORIGIN_RUNTIME),
            ):
                key = portrait_catalog_key(npc.pk)
                entity, target = self._rows_for(payload, npc)
                self.assertIsNotNone(entity)
                self.assertIsNotNone(target)
                # Both descriptor paths join the same current image.
                self.assertEqual(entity["portrait_ref"], key)
                self.assertEqual(target["portrait_ref"], key)
                entry = catalog[key]["artwork"]
                resource = entry["attempts"][0]["resource"]
                self.assertEqual(resource["origin"], expected_origin)
                self.assertTrue(resource["url"])

    @covers_requirement(
        "webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam"
    )
    def test_non_interact_named_character_carries_a_ref_in_look_only(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            bystander = create_object(PlayerCharacter, key="旁觀者", location=self.south_gate)
            bystander.race = "human"
            bystander.apply_race_baseline()
            bystander.db.portrait_policy = {
                "mode": "named",
                "stable_key": "t_synth_portrait_bystander",
            }
            bystander.db.age = bystander.db.apparent_age = 30
            bystander.db.creation_preset_key = _PRESET_KEY

            payload, _ = self._panels()
            entity = next(
                row
                for row in payload["look"]["entities"]
                if row["identity"] == int(bystander.pk)
            )
            self.assertEqual(entity["kind"], "character")
            self.assertEqual(entity["portrait_ref"], portrait_catalog_key(bystander.pk))
            self.assertNotIn(
                int(bystander.pk), {row["identity"] for row in payload["interact"]}
            )

    @covers_requirement(
        "webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam"
    )
    def test_uncatalogued_monster_is_an_excluded_null_control(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            monster = create_object(Monster, key="無圖哥布林", location=self.south_gate)
            monster.threat_tier = "low"
            monster.apply_monster_tier("floor")
            monster.traits.hp.base = 100
            monster.traits.hp.current = 100

            payload, art_panel = self._panels()
            target = next(
                row for row in payload["interact"] if row["identity"] == int(monster.pk)
            )
            self.assertIsNone(target["portrait_ref"])
            self.assertNotIn(portrait_catalog_key(monster.pk), art_panel["portrait_catalog"])

    @covers_requirement(
        "webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam"
    )
    def test_cap_dropped_member_keeps_a_truthful_null(self):
        with _official_art_scope() as art:
            art.mount("hero.png")
            first = self._named_host("cap_first", "t_synth_portrait_cap_first")
            second = self._named_host("cap_second", "t_synth_portrait_cap_second")
            self.assertLess(int(first.pk), int(second.pk))

            # Render once at the real ceiling first (this also completes the
            # art module import outside the patch: the panel module snapshots
            # its bound at import time). Baseline: both members carry refs.
            baseline, _ = self._panels()
            baseline_first, _ = self._rows_for(baseline, first)
            baseline_second, baseline_second_target = self._rows_for(baseline, second)
            self.assertEqual(
                baseline_first["portrait_ref"], portrait_catalog_key(first.pk)
            )
            self.assertEqual(
                baseline_second["portrait_ref"], portrait_catalog_key(second.pk)
            )
            self.assertEqual(
                baseline_second_target["portrait_ref"], portrait_catalog_key(second.pk)
            )

            # One-entry catalog ceiling: the first member keeps its ref, the
            # cap-dropped second is a truthful null in both descriptor paths
            # (membership, not resolvability, owns the boundary).
            with patch("world.rules.art_view.MAX_PORTRAIT_CATALOG", 1):
                payload, art_panel = self._panels()
            first_entity, _ = self._rows_for(payload, first)
            second_entity, second_target = self._rows_for(payload, second)
            self.assertEqual(first_entity["portrait_ref"], portrait_catalog_key(first.pk))
            self.assertIsNone(second_entity["portrait_ref"])
            self.assertIsNone(second_target["portrait_ref"])
            self.assertNotIn(
                portrait_catalog_key(second.pk), art_panel["portrait_catalog"]
            )

    @covers_requirement(
        "webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam"
    )
    def test_silhouette_only_and_age_ineligible_keep_their_references(self):
        with _official_art_scope():
            # No image mounted anywhere: the named host resolves to no real
            # candidate, and the age-ineligible host is refused outright. Both
            # are ADMITTED to the view, so both keep their references while the
            # catalog entry truthfully carries no real candidate and no
            # generated subject key — only the attribute-selected terminal.
            silhouette_host = self._named_host("輪廓host", "t_synth_portrait_silhouette")
            age_host = self._named_host("年齡不符host", "t_synth_portrait_aged")
            # A malformed canonical age is what refuses the subject: an
            # in-range integer is eligible presentation data.
            age_host.db.age = "not-a-number"

            payload, art_panel = self._panels()
            for npc in (silhouette_host, age_host):
                entity, target = self._rows_for(payload, npc)
                self.assertEqual(entity["portrait_ref"], portrait_catalog_key(npc.pk))
                if target is not None:
                    self.assertEqual(target["portrait_ref"], portrait_catalog_key(npc.pk))
                entry = art_panel["portrait_catalog"][portrait_catalog_key(npc.pk)]["artwork"]
                self.assertEqual(
                    [a["type"] for a in entry["attempts"] if a["type"] == "image"], []
                )
                self.assertEqual(entry["terminal"]["kind"], "alpha_mask")
            # The named-policy host keeps its own subject key (its generation is
            # a real recorded fact about that subject), while the age-refused
            # host exposes NO generated subject key at all.
            self.assertEqual(
                art_panel["portrait_catalog"][portrait_catalog_key(silhouette_host.pk)][
                    "artwork"
                ]["generation_subject"],
                character_subject_for(silhouette_host).full(),
            )
            self.assertIsNone(
                art_panel["portrait_catalog"][portrait_catalog_key(age_host.pk)][
                    "artwork"
                ]["generation_subject"]
            )

    @covers_requirement(
        "webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam"
    )
    def test_possession_resolves_refs_without_art_writes(self):
        from world.rules.possession import enter_possession, release_possession

        with _official_art_scope() as art:
            art.mount("hero.png")
            puppet = self._named_host("附身傀儡", "t_synth_portrait_puppet")
            join_party(puppet, self.player)
            bystander = self._named_host("附身目擊者", "t_synth_portrait_witness")
            join_party(bystander, self.player)

            before = self._root_digests(art)
            enter_possession(self.player, puppet)
            try:
                registry = self._registry()
                with patch(
                    "web.webclient.presentation.registry.log_error"
                ) as mock_log:
                    payload = registry.render("exploration", _context(puppet))
                    mock_log.assert_not_called()
                self.assertTrue(payload["available"])
                # The controlled companion stays a catalog member beside the
                # owner's roster: the bystander row keeps its admitted ref.
                entity, target = self._rows_for(payload, bystander)
                self.assertEqual(
                    entity["portrait_ref"], portrait_catalog_key(bystander.pk)
                )
                self.assertEqual(
                    target["portrait_ref"], portrait_catalog_key(bystander.pk)
                )
            finally:
                release_possession(self.player, npc=puppet, reason="handback")
            # Read-only: nothing under either artwork root moved, and no
            # gallery record was created for a host that never had one (the
            # named official default presents without a record).
            self.assertEqual(before, self._root_digests(art))
            for npc in (puppet, bystander):
                self.assertIsNone(record_for(character_subject_for(npc), create=False))


if __name__ == "__main__":
    unittest.main()
