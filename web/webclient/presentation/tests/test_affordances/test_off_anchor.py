"""Honest off-anchor navigation entries (service-anchor D5 delta)."""
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    MAX_AFFORDANCES,
    MAX_CARDS,
    SUGGESTIBLE_ACTION_IDS,
    SURFACES,
    AffordanceView,
    default_cards,
    exploration_affordances,
    suggestible_candidates,
)
import unittest
from ._support import VocabularyTestCase, _player


class OffAnchorServiceEntryTests(VocabularyTestCase):
    """Honest off-anchor navigation entries (service-anchor D5 delta).

    The emission key stays the exact local host; the ENABLED state now
    consults the one read-only resolver: off_anchor / malformed_binding
    emit the same navigation shape disabled with the gate's fixed registry
    message, allowed (incl. person/unset defaults) is byte-identical to
    before, and an anchor room without the host emits nothing at all.
    """

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

    def _navigation(self, actor=None):
        return [
            entry
            for entry in exploration_affordances(actor or self.player)
            if entry.navigation
        ]

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_traveling_merchant_shows_disabled_beside_the_player(self):
        self._merchant(
            room=self.square, binding="place", anchor=self.anchor.pk
        )
        (entry,) = self._navigation()
        self.assertEqual(entry.surface, "shop")
        self.assertFalse(entry.enabled)
        self.assertEqual(
            entry.disabled_reason,
            ("service_unavailable", "他的服務不在這裡營業。"),
        )
        # The navigation shape is unchanged: no action fields appear.
        self.assertIsNone(entry.action_id)
        self.assertIsNone(entry.params)
        self.assertIsNone(entry.freeform)
        as_dict = entry.as_dict()
        self.assertEqual(
            as_dict["disabled_reason"],
            {
                "code": "service_unavailable",
                "message": "他的服務不在這裡營業。",
            },
        )

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_traveling_guild_staff_shows_disabled_too(self):
        # The guild half of the two-surface requirement: GuildStaff selects a
        # different component slot, so it gets its own off-anchor row.
        staff = create_object(NPC, key="行腳公會職員", location=self.square)
        component = GuildStaff.create(
            staff, service_id="silence_staff", branch_key="plaza_stall"
        )
        staff.components.add(component)
        component.service_binding = "place"
        component.anchor_room_id = self.anchor.pk
        (entry,) = self._navigation()
        self.assertEqual(entry.surface, "guild")
        self.assertFalse(entry.enabled)
        self.assertEqual(
            entry.disabled_reason,
            ("service_unavailable", "他的服務不在這裡營業。"),
        )

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_malformed_binding_disables_the_entry(self):
        self._merchant(room=self.square, binding="portable", anchor=None)
        (entry,) = self._navigation()
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason[0], "service_unavailable")

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_at_anchor_and_default_bindings_stay_enabled(self):
        with self.subTest("place-bound host at its anchor"):
            self._merchant(
                room=self.anchor, binding="place", anchor=self.anchor.pk
            )
            self.player.location = self.anchor
            (entry,) = self._navigation()
            self.assertTrue(entry.enabled)
            self.assertIsNone(entry.disabled_reason)
        with self.subTest("unset binding (hand-built default)"):
            self.player.location = self.square
            self._merchant(room=self.square, binding=None, anchor=None)
            (entry,) = self._navigation()
            self.assertTrue(entry.enabled)

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_darkened_anchor_room_emits_no_ghost_entry(self):
        # The merchant travels with the party; another character looking at
        # the empty storefront must see NO shop entry at all (D5 absence).
        self._merchant(
            room=self.square, binding="place", anchor=self.anchor.pk
        )
        watcher = _player(key="店面觀看者")
        watcher.location = self.anchor
        self.assertEqual(self._navigation(watcher), [])

    @covers_requirement(
        "exploration-affordances::navigation-entries-render-off-anchor-service-hosts-honestly"
    )
    def test_disabled_navigation_entry_never_suggests(self):
        self._merchant(
            room=self.square, binding="place", anchor=self.anchor.pk
        )
        vocabulary = exploration_affordances(self.player)
        self.assertEqual(
            [
                entry
                for entry in suggestible_candidates(vocabulary, actor=self.player)
                if entry.navigation
            ],
            [],
        )

if __name__ == "__main__":
    unittest.main()
