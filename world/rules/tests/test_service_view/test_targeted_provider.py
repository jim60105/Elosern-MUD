"""Selected-provider services reads (npc-targeted-service-flows).

``build_services_view(actor, provider_id=...)`` resolves every surface on the
one selected NPC: its capabilities become the sections, a capability it lacks
stays null (never borrowed from a co-located NPC), and the read writes
nothing. Untargeted discovery keeps its room-wide behaviour, ambiguity
included.
"""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.rules.service_view import build_services_view
from world.rules.tests.test_service_view._support import (
    BOARD_QUEST,
    FakeHost,
    FakeRoom,
    ServiceRegistryIsolation,
    TICK_NOON,
    actor,
    exam_reception,
    guild_staff,
    merchant,
    quest_record,
    registration,
)

_FIRST_STAFF = 201
_SECOND_STAFF = 202
_RECEPTION = 203
_MERCHANT = 204


def _snapshot(player, room):
    return (
        deepcopy(list(player.db.inventory or [])),
        deepcopy(list(player.db.quest_log or [])),
        deepcopy(dict(player.db.guild_registration or {})),
        player.db.wallet,
        getattr(player, "guild_rank", None),
        deepcopy(getattr(player.db, "active_combat", None)),
        [member.pk for member in room.contents],
    )


def _build(player, provider_id=None):
    with patch(
        "world.rules.service_view.read_world_clock",
        return_value=SimpleNamespace(tick=TICK_NOON),
    ):
        return build_services_view(player, provider_id=provider_id)


class TargetedReadTests(ServiceRegistryIsolation):
    def _guild_room(self):
        first = FakeHost("clerk one", _FIRST_STAFF, guild_staff(), location=None)
        second = FakeHost("clerk two", _SECOND_STAFF, guild_staff(), location=None)
        counter = FakeHost("counter", _RECEPTION, exam_reception(), location=None)
        keeper = FakeHost("keeper", _MERCHANT, merchant(), location=None)
        return FakeRoom(first, second, counter, keeper), first, second, counter, keeper

    @covers_requirement(
        "webclient-service-menus::service-presentation-resolves-hosts-per-service-class-and-a-stable-player-summary"
    )
    def test_two_same_class_providers_resolve_to_the_selected_one(self):
        room, first, second, _counter, _keeper = self._guild_room()
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
        )
        # Untargeted discovery keeps its documented ambiguity.
        untargeted = _build(player)
        self.assertIsNone(untargeted.guild)
        self.assertEqual(untargeted.guild_unavailable_reason, "ambiguous_service_host")
        # Each selection reads exactly itself.
        for host in (first, second):
            view = _build(player, host.pk)
            self.assertEqual(view.guild.provider_id, int(host.pk))
            self.assertEqual(view.host.identity, str(int(host.pk)))
            self.assertIsNone(view.rank)
            self.assertIsNone(view.shop)
            self.assertEqual(view.pagination.board_total, len(view.guild.board))
            self.assertEqual(view.pagination.quest_total, len(view.guild.quests))

    @covers_requirement(
        "webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination"
    )
    def test_a_reception_only_provider_ships_the_rank_surface_alone(self):
        room, _first, _second, counter, _keeper = self._guild_room()
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            merit=50,
        )
        view = _build(player, counter.pk)
        self.assertIsNone(view.guild)
        self.assertIsNotNone(view.rank)
        self.assertEqual(view.rank.provider_id, int(counter.pk))
        self.assertEqual(view.rank.next_rank, "E")
        self.assertIsNone(view.shop)
        self.assertEqual(
            (view.pagination.board_total, view.pagination.quest_total), (0, 0)
        )

    def test_a_merchant_read_leaves_the_co_located_guild_surfaces_null(self):
        room, _first, _second, _counter, keeper = self._guild_room()
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
        )
        view = _build(player, keeper.pk)
        self.assertIsNone(view.guild)
        self.assertIsNone(view.rank)
        self.assertIsNotNone(view.shop)
        self.assertEqual(view.shop.provider_id, int(keeper.pk))
        self.assertEqual(view.shop.member_id, int(player.pk))
        self.assertEqual(view.pagination.stock_total, len(view.shop.stock))
        self.assertEqual((view.pagination.board_total, view.pagination.quest_total), (0, 0))

    def test_the_selected_provider_is_not_authority_for_another_surface(self):
        # A reception selection cannot borrow the staff clerk's guild board,
        # even though that clerk stands in the same room.
        room, _first, _second, counter, keeper = self._guild_room()
        player = actor(location=room, registration=registration(), guild_rank="F")
        reception_view = _build(player, counter.pk)
        self.assertIsNone(reception_view.guild)
        merchant_view = _build(player, keeper.pk)
        self.assertIsNone(merchant_view.guild)
        self.assertIsNone(merchant_view.rank)

    @covers_requirement(
        "webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel"
    )
    def test_a_targeted_read_writes_nothing(self):
        room, first, _second, counter, keeper = self._guild_room()
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
            inventory=["t_item"],
            wallet=500,
        )
        before = _snapshot(player, room)
        for provider_id in (first.pk, counter.pk, keeper.pk):
            _build(player, provider_id)
        self.assertEqual(_snapshot(player, room), before)

    def test_an_unusable_selection_raises_instead_of_substituting(self):
        from world.rules.service_targets import ServiceTargetError

        room, _first, _second, _counter, _keeper = self._guild_room()
        player = actor(location=room)
        for provider_id in (999_999, 0, True):
            with self.subTest(provider_id=provider_id):
                with self.assertRaises(ServiceTargetError):
                    _build(player, provider_id)

    def test_untargeted_discovery_still_resolves_a_single_provider(self):
        staff = FakeHost("clerk", _FIRST_STAFF, guild_staff(), location=None)
        room = FakeRoom(staff)
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
        )
        view = _build(player)
        self.assertEqual(view.guild.provider_id, int(staff.pk))
        self.assertTrue(view.guild.branch_label.strip())
        self.assertEqual(
            [row.quest_id for row in view.guild.quests], [f"{BOARD_QUEST}:1"]
        )
