from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import GridRoom, Room
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import record_arrival
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_GUILD_BRANCH_KEY

from ._support import T_DIALOGUE_KEY, _context



class OffAnchorNavigationPanelTests(BattlefieldIsolation, EvenniaTestCase):
    """The v1 panel serializer carries the disabled navigate descriptor.

    The shared emitter's off-anchor disabled state flows through the
    version-1 descriptor shape untouched (kind navigate, enabled false,
    the gate's fixed registry message) — the presenter needed no edits.
    """

    def setUp(self):
        super().setUp()
        self.anchor = create_object(Room, key="店面")
        self.square = create_object(Room, key="廣場")
        self.player = create_object(PlayerCharacter, key="門面測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.square
        self.merchant = create_object(NPC, key="行腳商人", location=self.square)
        component = Merchant.create(
            self.merchant, service_id="silence_shop", branch_key="plaza_stall"
        )
        self.merchant.components.add(component)
        component.service_binding = "place"
        component.anchor_room_id = self.anchor.pk

    def _navigate_entries(self):
        payload = build_production_registry().render("exploration", _context(self.player))
        target = next(
            t for t in payload["interact"] if t["identity"] == int(self.merchant.pk)
        )
        return [a for a in target["affordances"] if a["kind"] == "navigate"]

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_off_anchor_merchant_serializes_disabled_navigate_entry(self):
        (entry,) = self._navigate_entries()
        self.assertEqual(entry["surface"], "shop")
        self.assertFalse(entry["enabled"])
        self.assertEqual(
            entry["disabled_reason"],
            {
                "code": "service_unavailable",
                "message": "他的服務不在這裡營業。",
            },
        )
        self.assertNotIn("action_id", entry)

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_anchor_room_without_the_host_carries_no_entry(self):
        watcher = create_object(PlayerCharacter, key="店面觀看者")
        watcher.race = "human"
        watcher.apply_race_baseline()
        watcher.location = self.anchor
        payload = build_production_registry().render("exploration", _context(watcher))
        self.assertEqual(
            [
                a
                for target in payload["interact"]
                for a in target["affordances"]
                if a["kind"] == "navigate"
            ],
            [],
        )


class ExplorationByteStabilityTests(BattlefieldIsolation, EvenniaTestCase):
    """The v1 payload is byte-stable while the panel delegates to the shared vocabulary.

    Pins the pre-refactor expected descriptor shapes for one rule-table fixture
    room (scripted host, generative NPC, plain NPC, monster, objects, enabled
    and locked exits) — same dicts, same order — and asserts the idle-baseline
    entries never appear in the v1 payload.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from world.quests.catalog import register_catalog
        from world.rules.guild_config import (
            CATALOG,
            load_catalog_into_cache,
            register_catalog_offers,
        )

        cls._registry_items = None
        get_world_clock()
        sync_grid()
        register_catalog()
        catalog = load_catalog_into_cache()
        register_catalog_offers(catalog)

    def setUp(self):
        from evennia.objects.objects import DefaultObject

        # The scripted-host fixture renders its keyword pool from the live
        # dialogue table: build the room on the kit-authored dialogue row.
        open_synthetic_scope(self, "dialogue")
        self.room1 = create_object(Room, key="南門")
        self.player = create_object(PlayerCharacter, key="穩定測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        record_arrival(self.player)
        self.destination = create_object(Room, key="北大道", location=None)
        self.exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="東",
            location=self.room1,
            destination=self.destination,
        )
        self.secret = create_object(Room, key="密室", location=None)
        self.locked_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="西",
            location=self.room1,
            destination=self.secret,
        )
        self.locked_exit.locks.add("traverse:false()")
        self.host = create_object(NPC, key="公會職員", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=T_DIALOGUE_KEY)
        )
        self.bard = create_object(LLMNPC, key="吟遊詩人", location=self.room1)
        self.passerby = create_object(NPC, key="路人", location=self.room1)
        self.goblin = create_object(Monster, key="哥布林", location=self.room1)
        self.goblin.threat_tier = "low"
        self.goblin.apply_monster_tier("floor")
        self.box = create_object(DefaultObject, key="木箱", location=self.room1)

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        if self._registry_items is not None:
            import world.rules.guild_config as guild_config

            QUEST_DEFINITION_REGISTRY.clear()
            QUEST_DEFINITION_REGISTRY.update(self._registry_items)
            GUILD_OFFER_REGISTRY.clear()
            GUILD_OFFER_REGISTRY.update(self._offers)
            guild_config.CATALOG = self._catalog
        super().tearDown()

    def _render(self):
        return build_production_registry().render("exploration", _context(self.player))

    def test_rule_table_fixture_payload_is_byte_identical_to_v2(self):
        payload = self._render()
        self.assertEqual(
            payload,
            {
                "schema_version": 2,
                "available": True,
                "kind": "exploration",
                "move": [
                    {
                        "exit_ref": str(int(self.exit_obj.id)),
                        "label": "東",
                        "destination": f"room:{int(self.destination.pk)}",
                        "enabled": True,
                        "disabled_reason": None,
                    },
                    {
                        "exit_ref": str(int(self.locked_exit.id)),
                        "label": "西",
                        "destination": f"room:{int(self.secret.pk)}",
                        "enabled": False,
                        "disabled_reason": {
                            "code": "locked",
                            "message": "此出口目前無法通行。",
                        },
                    },
                ],
                "look": {
                    "room": {
                        "identity": int(self.room1.pk),
                        "display_name": "南門",
                        "room": True,
                    },
                    "entities": [
                        {
                            "identity": int(self.host.pk),
                            "display_name": "公會職員",
                            "kind": "npc",
                            "portrait_ref": None,
                        },
                        {
                            "identity": int(self.bard.pk),
                            "display_name": "吟遊詩人",
                            "kind": "npc",
                            "portrait_ref": None,
                        },
                        {
                            "identity": int(self.passerby.pk),
                            "display_name": "路人",
                            "kind": "npc",
                            "portrait_ref": None,
                        },
                        {
                            "identity": int(self.goblin.pk),
                            "display_name": "哥布林",
                            "kind": "monster",
                            "portrait_ref": None,
                        },
                    ],
                    "objects": [
                        {"identity": int(self.box.pk), "display_name": "木箱"}
                    ],
                },
                "interact": [
                    {
                        "identity": int(self.host.pk),
                        "display_name": "公會職員",
                        "portrait_ref": None,
                        "affordances": [
                            {
                                "kind": "action",
                                "action_id": "explore.talk_scripted",
                                "label": "交談",
                                "enabled": True,
                                "disabled_reason": None,
                            }
                        ],
                        "keywords": [
                            *(
                                {"keyword_id": response.keyword, "label": response.keyword}
                                for response in SYNTH_DIALOGUE[T_DIALOGUE_KEY].responses
                            )
                        ],
                    },
                    {
                        "identity": int(self.bard.pk),
                        "display_name": "吟遊詩人",
                        "portrait_ref": None,
                        "affordances": [
                            {
                                "kind": "action",
                                "action_id": "explore.talk_freeform",
                                "label": "自由交談",
                                "enabled": True,
                                "disabled_reason": None,
                            },
                            {
                                "kind": "action",
                                "action_id": "explore.party_invite",
                                "label": "邀請",
                                "enabled": True,
                                "disabled_reason": None,
                            },
                        ],
                    },
                    {
                        "identity": int(self.passerby.pk),
                        "display_name": "路人",
                        "portrait_ref": None,
                        "affordances": [],
                    },
                    {
                        "identity": int(self.goblin.pk),
                        "display_name": "哥布林",
                        "portrait_ref": None,
                        "affordances": [
                            {
                                "kind": "action",
                                "action_id": "explore.engage",
                                "label": "戰鬥",
                                "enabled": True,
                                "disabled_reason": None,
                            }
                        ],
                    },
                ],
                "character": {"available": True},
                "quests": {"available": True},
                "inventory": {"available": True},
            },
        )

    def test_idle_baseline_entries_never_appear_in_the_v1_payload(self):
        payload = self._render()
        action_ids = {
            affordance.get("action_id")
            for target in payload["interact"]
            for affordance in target["affordances"]
            if affordance.get("action_id") is not None
        }
        self.assertNotIn("explore.wait", action_ids)
        self.assertNotIn("explore.look", action_ids)
        self.assertEqual(
            action_ids,
            {"explore.talk_scripted", "explore.talk_freeform", "explore.party_invite", "explore.engage"},
        )
        # The same room's vocabulary does carry the baseline room-look entry,
        # so the exclusion is a v1 serialization property, not an empty room.
        from web.webclient.presentation.affordances import exploration_affordances

        vocabulary = exploration_affordances(self.player)
        self.assertTrue(
            any(
                not entry.navigation
                and entry.action_id == "explore.look"
                and entry.params == {"room": True}
                for entry in vocabulary
            )
        )


if __name__ == "__main__":
    unittest.main()
