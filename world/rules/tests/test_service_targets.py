"""Exact selected-provider resolution (npc-targeted-service-flows).

Every service flow names its provider. These tests pin the admission seam that
turns that identity into one exact live, co-visible NPC and capability: two
same-class providers stay distinct, no room enumeration or fallback ever
participates, and the mutation path adds the actor-level authority (combat,
possession) the deterministic commands already enforce. Refusals write
nothing.
"""

from copy import deepcopy

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from typeclasses.components import GuildStaff, Merchant
from typeclasses.npcs import NPC

from world.rules.service_targets import (
    ServiceTargetError,
    ServiceTargetReason,
    require_service_mutation,
    require_service_provider,
    require_service_target,
    visible_room_entity,
)
from world.rules.tests.test_service_view._support import (
    FakeHost,
    FakeRoom,
    ServiceRegistryIsolation,
    actor,
    exam_reception,
    guild_staff,
    merchant,
    registration,
)

_TWO_STAFF = 101
_TWO_STAFF_SECOND = 102


def _reason(error):
    return error.exception.args[0]


def _state(*entities):
    """A comparable snapshot of every canonical surface these fakes carry."""
    snapshot = []
    for entity in entities:
        db = getattr(entity, "db", None)
        snapshot.append(
            (
                getattr(entity, "pk", None),
                getattr(entity, "location", None),
                getattr(entity, "visible", True),
                deepcopy(list(getattr(db, "inventory", []) or [])) if db else None,
                deepcopy(dict(getattr(db, "guild_registration", {}) or {})) if db else None,
                getattr(db, "wallet", None) if db else None,
                deepcopy(getattr(db, "active_combat", None)) if db else None,
            )
        )
    return snapshot


class ServiceTargetResolutionTests(ServiceRegistryIsolation):
    def _two_staff_room(self):
        first = FakeHost("clerk one", _TWO_STAFF, guild_staff(), location=None)
        second = FakeHost("clerk two", _TWO_STAFF_SECOND, guild_staff(), location=None)
        room = FakeRoom(first, second)
        return room, first, second

    def test_two_same_class_providers_resolve_to_the_selected_one(self):
        room, first, second = self._two_staff_room()
        player = actor(location=room)
        npc, component = require_service_target(player, second.pk, GuildStaff)
        self.assertIs(npc, second)
        self.assertIs(component, second.components.get(GuildStaff.name))
        npc, _ = require_service_target(player, first.pk, GuildStaff)
        self.assertIs(npc, first)

    def test_wrong_capability_never_substitutes_a_neighbouring_provider(self):
        staff = FakeHost("clerk", 11, guild_staff(), location=None)
        keeper = FakeHost("keeper", 12, merchant(), location=None)
        player = actor(location=FakeRoom(staff, keeper))
        with self.assertRaises(ServiceTargetError) as caught:
            require_service_target(player, staff.pk, Merchant)
        self.assertEqual(_reason(caught), ServiceTargetReason.WRONG_CAPABILITY)
        with self.assertRaises(ServiceTargetError):
            require_service_target(player, keeper.pk, GuildStaff)

    def test_unknown_hidden_and_departed_targets_reject(self):
        keeper = FakeHost("keeper", 21, merchant(), location=None)
        hidden = FakeHost("hidden keeper", 22, merchant(), location=None)
        departed = FakeHost("departed keeper", 23, merchant(), location=None)
        room = FakeRoom(keeper, hidden, hidden=())
        player = actor(location=room)
        # Present but not visible to this viewer.
        room.hidden = (hidden,)
        for identity in (999_999, hidden.pk, departed.pk):
            with self.subTest(identity=identity):
                with self.assertRaises(ServiceTargetError) as caught:
                    require_service_target(player, identity, Merchant)
                self.assertEqual(_reason(caught), ServiceTargetReason.UNKNOWN_TARGET)
        # The visible provider is still reachable: the refusals above never
        # poisoned the resolution of the room's real selection.
        self.assertIs(require_service_provider(player, keeper.pk), keeper)

    def test_malformed_identity_forms_reject_without_resolution(self):
        keeper = FakeHost("keeper", 31, merchant(), location=None)
        player = actor(location=FakeRoom(keeper))
        for identity in (True, False, 0, -1, 1.5, "31", 9_007_199_254_740_992):
            with self.subTest(identity=identity):
                self.assertIsNone(visible_room_entity(player, identity))
                with self.assertRaises(ServiceTargetError) as caught:
                    require_service_mutation(player, identity, Merchant)
                self.assertEqual(_reason(caught), ServiceTargetReason.UNKNOWN_TARGET)

    def test_failed_binding_rejects_as_malformed(self):
        keeper = FakeHost(
            "bound keeper",
            41,
            merchant(service_binding="place", anchor_room_id=None),
            location=None,
        )
        player = actor(location=FakeRoom(keeper))
        with self.assertRaises(ServiceTargetError) as caught:
            require_service_target(player, keeper.pk, Merchant)
        self.assertEqual(_reason(caught), ServiceTargetReason.MALFORMED_BINDING)

    def test_schedule_block_refuses_the_selected_provider_only(self):
        busy = FakeHost("busy keeper", 51, merchant(), location=None)
        free = FakeHost("free keeper", 52, merchant(), location=None)
        busy.db = type("Schedule", (), {"schedule_state": "busy"})()
        player = actor(location=FakeRoom(busy, free))
        with self.assertRaises(ServiceTargetError) as caught:
            require_service_target(player, busy.pk, Merchant)
        self.assertEqual(_reason(caught), ServiceTargetReason.SCHEDULE_BLOCKED)
        self.assertIs(require_service_target(player, free.pk, Merchant)[0], free)

    def test_reading_admits_any_supported_capability(self):
        counter = FakeHost("counter", 61, exam_reception(), location=None)
        player = actor(location=FakeRoom(counter), registration=registration())
        self.assertIs(require_service_provider(player, counter.pk), counter)


class ServiceTargetAuthorityTests(ServiceRegistryIsolation):
    def _combat_record(self):
        return {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 1,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
            "engagement_id": "hostile:1:0:1",
            "round_revision": 0,
            "draft_version": 0,
            "draft_entries": {},
            "confirmed_actors": [],
        }

    def test_combat_refuses_every_provider_mutation_but_not_the_read(self):
        keeper = FakeHost("keeper", 71, merchant(), location=None)
        player = actor(location=FakeRoom(keeper), inventory=["t_item"])
        player.db.active_combat = self._combat_record()
        before = _state(player, keeper)
        with self.assertRaises(ServiceTargetError) as caught:
            require_service_mutation(player, keeper.pk, Merchant)
        self.assertEqual(_reason(caught), ServiceTargetReason.ACTIVE_COMBAT)
        # Identity admission alone still answers: only the write is refused.
        self.assertIs(require_service_provider(player, keeper.pk), keeper)
        self.assertEqual(_state(player, keeper), before)

    def test_a_possessed_body_reaches_only_the_merchant_counters(self):
        keeper = FakeHost("keeper", 81, merchant(), location=None)
        clerk = FakeHost("clerk", 82, guild_staff(), location=None)
        player = actor(location=FakeRoom(keeper, clerk), registration=registration())
        player.db.possessed_by = 5
        before = _state(player, keeper, clerk)
        with self.assertRaises(ServiceTargetError) as caught:
            require_service_mutation(player, clerk.pk, GuildStaff)
        self.assertEqual(_reason(caught), ServiceTargetReason.POSSESSED)
        self.assertIs(require_service_mutation(player, keeper.pk, Merchant)[0], keeper)
        self.assertEqual(_state(player, keeper, clerk), before)

    @covers_requirement(
        "webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative"
    )
    def test_every_refusal_writes_nothing(self):
        keeper = FakeHost("keeper", 91, merchant(), location=None)
        hidden = FakeHost("hidden", 92, merchant(), location=None)
        player = actor(location=FakeRoom(keeper, hidden, hidden=(hidden,)), wallet=500)
        player.db.possessed_by = 7
        before = _state(player, keeper, hidden)
        for identity in (hidden.pk, 999_999, True, 0):
            with self.subTest(identity=identity):
                with self.assertRaises(ServiceTargetError):
                    require_service_mutation(player, identity, Merchant)
        self.assertEqual(_state(player, keeper, hidden), before)


class ServiceTargetAnchorTests(EvenniaTest):
    """A place-bound provider standing away from its anchor refuses service.

    The exact-target resolver delegates the binding question to the shared
    service gate, whose anchor lookup needs a real ``Room`` row, so this slice
    runs on real objects instead of the package's synthetic fakes.
    """

    def _keeper(self, room, anchor_room):
        keeper = create_object(NPC, key="travelling keeper", location=room)
        component = Merchant.create(
            keeper, service_id="store", shop_key="t_off_anchor_shop"
        )
        component.service_binding = "place"
        component.anchor_room_id = anchor_room.pk
        keeper.components.add(component)
        return keeper

    def test_an_off_anchor_provider_is_refused_and_the_anchor_room_serves(self):
        self.char1.location = self.room1
        keeper = self._keeper(self.room1, self.room2)
        with self.assertRaises(ServiceTargetError) as caught:
            require_service_target(self.char1, keeper.pk, Merchant)
        self.assertEqual(_reason(caught), ServiceTargetReason.OFF_ANCHOR)
        # Standing in the anchor room is the only accepted position for a
        # place-bound provider: the same NPC then resolves normally.
        keeper.location = self.room2
        self.char1.location = self.room2
        self.assertIs(require_service_target(self.char1, keeper.pk, Merchant)[0], keeper)
