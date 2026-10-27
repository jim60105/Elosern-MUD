"""Honest off-anchor service entries (service-anchor D5, schema 5).

The coarse guild/shop navigation rows are gone: a service host's own
``services`` projection carries the paused entry, with the shared gate's fixed
reason, in the host's place. A host standing in another room is not an interact
target at all, so its storefront shows no entry for a watcher there.
"""
from typeclasses.components import GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.npc_services import STATE_READY, project_npc_services

import unittest
from ._support import VocabularyTestCase, _player


class OffAnchorServiceEntryTests(VocabularyTestCase):
    """The derived service entry answers off-anchor hosts honestly."""

    def setUp(self):
        super().setUp()
        self.anchor = create_object(Room, key="店面")
        self.square = create_object(Room, key="廣場")
        self.player = _player()
        self.player.location = self.square

    def _merchant(self, *, room, binding, anchor):
        merchant = create_object(NPC, key="行腳商人", location=room)
        component = Merchant.create(
            merchant, service_id="silence_shop", branch_key="plaza_stall"
        )
        merchant.components.add(component)
        component.service_binding = binding
        component.anchor_room_id = anchor
        return merchant

    def _services(self, host, actor=None):
        return project_npc_services(actor or self.player, actor or self.player, host)

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_traveling_merchant_shows_a_disabled_shop_entry(self):
        merchant = self._merchant(
            room=self.square, binding="place", anchor=self.anchor.pk
        )
        services = self._services(merchant)
        self.assertEqual(services.state, STATE_READY)
        (entry,) = services.entries
        self.assertEqual(entry.key, "shop")
        self.assertEqual(entry.route.section, "shop")
        self.assertEqual(entry.route.npc_id, int(merchant.pk))
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason.code, "off_anchor")
        self.assertEqual(entry.disabled_reason.message, "他的服務不在這裡營業。")
        self.assertEqual(
            entry.as_dict()["disabled_reason"],
            {"code": "off_anchor", "message": "他的服務不在這裡營業。"},
        )

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_traveling_guild_staff_shows_disabled_guild_entries(self):
        staff = create_object(NPC, key="行腳公會職員", location=self.square)
        component = GuildStaff.create(
            staff, service_id="silence_staff", branch_key="plaza_stall"
        )
        staff.components.add(component)
        component.service_binding = "place"
        component.anchor_room_id = self.anchor.pk
        services = self._services(staff)
        self.assertEqual(
            [entry.key for entry in services.entries],
            ["guild.register", "guild.board", "guild.report"],
        )
        for entry in services.entries:
            self.assertFalse(entry.enabled)
            self.assertEqual(entry.disabled_reason.code, "off_anchor")

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_malformed_binding_disables_the_entry(self):
        merchant = self._merchant(room=self.square, binding="portable", anchor=None)
        (entry,) = self._services(merchant).entries
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason.code, "malformed_binding")

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_possessed_actor_keeps_the_ordinary_merchant_gate(self):
        # Possession changes neither the merchant's enabled state nor its
        # fixed off-anchor reason.
        self.player.db.possessed_by = 1
        merchant = self._merchant(
            room=self.square, binding="place", anchor=self.anchor.pk
        )
        (entry,) = self._services(merchant).entries
        self.assertEqual(entry.key, "shop")
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason.code, "off_anchor")

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_at_anchor_binding_stays_enabled(self):
        with self.subTest("place-bound host at its anchor"):
            merchant = self._merchant(
                room=self.anchor, binding="place", anchor=self.anchor.pk
            )
            self.player.location = self.anchor
            (entry,) = self._services(merchant).entries
            self.assertTrue(entry.enabled)
            self.assertIsNone(entry.disabled_reason)
        with self.subTest("unset binding is the gate's malformed verdict"):
            # The gate fails closed on a component without a persisted
            # binding, so a hand-built host with no binding is disabled with
            # its own fixed reason.
            self.player.location = self.square
            merchant = self._merchant(room=self.square, binding=None, anchor=None)
            (entry,) = self._services(merchant).entries
            self.assertFalse(entry.enabled)
            self.assertEqual(entry.disabled_reason.code, "malformed_binding")

if __name__ == "__main__":
    unittest.main()
