from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import WildernessGateExit
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import GridRoom, Room
from web.webclient.presentation.exploration import (
    EXPLORATION_SCHEMA_VERSION,
    MAX_DISPLAY_NAME_CODE_POINTS,
    validate_exploration,
)
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival

from ._support import _context



class WildernessExplorationPresenterTests(EvenniaTestCase):
    """Wilderness move rows advertise canonical arrival nodes (fix-wilderness-web-navigation)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        cls._north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()

    def setUp(self):
        self.room1 = create_object(Room, key="Room1")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.north_gate = GridRoom.objects.get(id=self._north_gate.id)
        self.gate = [
            exit_obj
            for exit_obj in self.north_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]

    def _render(self):
        return build_production_registry().render("exploration", _context(self.char1))

    @covers_requirement("webclient-exploration-menu::exploration-move-rows-advertise-canonical-destinations")
    def test_wilderness_move_rows_advertise_canonical_destinations(self):
        from typeclasses.rooms import TerrainRoom
        from world.maps.wilderness_destination import resolve_wilderness_destination

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        room = self.char1.location
        payload = self._render()
        self.assertTrue(payload["available"])
        rows = {row["label"]: row for row in payload["move"]}
        # Every provider-valid direction routes through the resolver. At the
        # north-gate approach (60, 103) the two directions facing the anchor
        # footprint (southeast/southwest) are refused steps and advertise no
        # row (wilderness-anchor-footprint).
        self.assertEqual(
            set(rows),
            {"north", "northeast", "east", "south", "west", "northwest"},
        )
        for direction, row in rows.items():
            expected = resolve_wilderness_destination(room, direction)
            self.assertIsNotNone(expected)
            self.assertEqual(row["destination"], expected, direction)
            self.assertTrue(row["enabled"])
            self.assertIsNone(row["disabled_reason"])
        # The gateway south row advertises the grid arrival node, not a wild cell.
        self.assertEqual(rows["south"]["destination"], "grid:capital_altoria:2:4")


class NPCTitlePanelRowsTests(BattlefieldIsolation, EvenniaTestCase):
    """Entity and interact rows carry 「姓名　稱號」; every other row is untouched.

    npc-title-identity-core D5: the swap is to the display-name SOURCE on the
    two character-row kinds only. Bounds, schema version, field sets, and the
    plain-key shared helper all stay as specified for
    ``webclient-exploration-menu``.
    """

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
        self.room1 = create_object(Room, key="南門廣場")
        self.player = create_object(PlayerCharacter, key="探索標題測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        record_arrival(self.player)

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        import world.rules.guild_config as guild_config

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offers)
        guild_config.CATALOG = self._catalog
        super().tearDown()

    def _render(self):
        return build_production_registry().render("exploration", _context(self.player))

    def _entity_rows(self, payload, pk):
        rows = [row for row in payload["look"]["entities"] if row["identity"] == pk]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def _interact_rows(self, payload, pk):
        return [row for row in payload["interact"] if row["identity"] == pk]

    @covers_requirement('npc-identity-titles::the-webclient-exploration-panel-renders-the-npc-full-identity-on-entity-and-interact-rows')
    def test_titled_npc_reads_with_title_on_both_row_kinds(self):
        npc = create_object(NPC, key="塞提斯", location=self.room1)
        npc.npc_title = "南門守衛"
        payload = self._render()
        self.assertTrue(payload["available"])
        pk = int(npc.pk)
        self.assertEqual(
            self._entity_rows(payload, pk)["display_name"], "塞提斯　南門守衛"
        )
        interact = self._interact_rows(payload, pk)
        self.assertTrue(interact)
        self.assertTrue(
            all(row["display_name"] == "塞提斯　南門守衛" for row in interact)
        )
        validate_exploration(payload)

    @covers_requirement('npc-identity-titles::the-webclient-exploration-panel-renders-the-npc-full-identity-on-entity-and-interact-rows')
    def test_non_entity_rows_keep_the_plain_key_source(self):
        from web.webclient.presentation.affordances import _bounded_display_name

        npc = create_object(NPC, key="塞提斯", location=self.room1)
        npc.npc_title = "南門守衛"
        monster = create_object(Monster, key="野狼", location=self.room1)
        coin = create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        destination = create_object(Room, key="南大道", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="北",
            location=self.room1,
            destination=destination,
        )
        payload = self._render()
        self.assertEqual(
            self._entity_rows(payload, int(monster.pk))["display_name"],
            _bounded_display_name(monster),
        )
        object_rows = [
            row
            for row in payload["look"]["objects"]
            if row["identity"] == int(coin.pk)
        ]
        self.assertEqual(object_rows[0]["display_name"], _bounded_display_name(coin))
        move_row = next(
            row for row in payload["move"] if row["exit_ref"] == str(int(exit_obj.id))
        )
        self.assertEqual(move_row["label"], _bounded_display_name(exit_obj))
        self.assertEqual(
            payload["look"]["room"]["display_name"], _bounded_display_name(self.room1)
        )
        validate_exploration(payload)

    @covers_requirement('npc-identity-titles::the-webclient-exploration-panel-renders-the-npc-full-identity-on-entity-and-interact-rows')
    def test_untitled_and_malformed_titles_keep_the_panel_available(self):
        untitled = create_object(NPC, key="布魯諾", location=self.room1)
        broken = create_object(NPC, key="米拉", location=self.room1)
        broken.db.npc_title = 123
        whitespace = create_object(NPC, key="老赫", location=self.room1)
        whitespace.db.npc_title = "   "
        markup = create_object(NPC, key="腐名", location=self.room1)
        markup.db.npc_title = "|r南門守衛|n"  # would emit Evennia markup
        ambiguous = create_object(NPC, key="含糊", location=self.room1)
        ambiguous.db.npc_title = "南門\u3000守衛"  # internal separator
        control = create_object(NPC, key="控制", location=self.room1)
        control.db.npc_title = "南門\x1b守衛"  # control character
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(
            self._entity_rows(payload, int(untitled.pk))["display_name"], "布魯諾"
        )
        self.assertEqual(
            self._entity_rows(payload, int(broken.pk))["display_name"], "米拉"
        )
        self.assertEqual(
            self._entity_rows(payload, int(whitespace.pk))["display_name"], "老赫"
        )
        for entity, plain in ((markup, "腐名"), (ambiguous, "含糊"), (control, "控制")):
            with self.subTest(plain=plain):
                row = self._entity_rows(payload, int(entity.pk))
                self.assertEqual(row["display_name"], plain)
                for interact in self._interact_rows(payload, int(entity.pk)):
                    self.assertNotIn("\u3000", interact["display_name"])
                    self.assertNotIn("|", interact["display_name"])
        validate_exploration(payload)

    @covers_requirement('npc-identity-titles::the-webclient-exploration-panel-renders-the-npc-full-identity-on-entity-and-interact-rows', 'npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity')
    def test_composed_bounds_hold_for_legal_and_overlong_titles(self):
        long_npc = create_object(NPC, key="長" * 64, location=self.room1)
        long_npc.npc_title = "守" * 32
        broken = create_object(NPC, key="毀" * 60, location=self.room1)
        broken.db.npc_title = "壞" * 200  # corrupt overlong storage title
        payload = self._render()
        composed = self._entity_rows(payload, int(long_npc.pk))["display_name"]
        self.assertEqual(len(composed), 64 + 1 + 32)
        self.assertLessEqual(len(composed), MAX_DISPLAY_NAME_CODE_POINTS)
        damaged = self._entity_rows(payload, int(broken.pk))["display_name"]
        self.assertEqual(len(damaged), MAX_DISPLAY_NAME_CODE_POINTS)
        for row in self._interact_rows(payload, int(broken.pk)):
            self.assertLessEqual(
                len(row["display_name"]), MAX_DISPLAY_NAME_CODE_POINTS
            )
        normalized = validate_exploration(payload)
        self.assertEqual(normalized["schema_version"], EXPLORATION_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
