"""Pure no-mutation service view tests (task 1.1).

Exercises the frozen services read model against deterministic fakes: per-class
host resolution (no/ambiguous/single/co-located), the unregistered summary,
board rank filtering, quest detail/deadline/reward rendering, shop open/closed
state at explicit world ticks, exact copper values, repeated-key inventory
aggregation, and surface isolation on corrupt records. No database is used; the
world-clock read is patched to a fixed tick and the immutable registries are
loaded exactly as the startup composition root does.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from world.lore.items import (
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)
from world.quests.catalog import register_catalog
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    register_quest_definition,
)
from world.quests.runtime import QuestRecord, QuestState, to_storage
from world.quests.tests._fixtures import TEST_ISSUER_KEY, register_catalog_once
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    a_live_monster_tier_key,
    install_synthetic_catalog,
    live_item_registry,
    live_monster_tier_keys,
    price_band,
    rank_reward_band,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
    synthetic_branch_key,
)
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_SHOPS,
)

# The shipped affinity rulebook cross-references one catalog quest by key, so
# the affinity-config loader needs the catalog definitions present in-process.
# Registered at import (no synthetic scope is open yet).
register_catalog_once()

# The services panel is exercised on kit rows only: the guild branch is the
# kit synthetic branch, the store is one synthetic shop config over kit
# items, and every asserted number below is authored by this file.
BRANCH = synthetic_branch_key()
T_SHOP = next(iter(SYNTH_SHOPS))
T_SPRAY = SYNTH_ITEMS["t_ember_spray"].key
T_FANG = SYNTH_ITEMS["t_iron_fang"].key
T_APPLE = SYNTH_ITEMS["t_huskapple"].key
# The unsellable kit row (exercises the sellable filter's negative path).
T_PASS = SYNTH_ITEMS["t_wayfarer_pass"].key
# The kit's slotted weapon: equip-toggle rows need real equipment slots.
T_KNIFE = SYNTH_ITEMS["t_thorn_knife"].key
# F/E ladder letters are production rank-ladder identifiers (never flagged
# tokens); board quests ride them with rewards inside the live rank bands.
BOARD_QUEST = "services_board_quest"
BOARD_QUEST_DISPLAY = "測試看板委託"
E_QUEST = "services_e_quest"


def _buy_copper(item_key: str) -> int:
    """The synthetic offer's buy price (mirrors synth_offer_rule derivation)."""
    floor, ceiling = price_band(item_key)
    buy = floor + 2
    if ceiling is not None and buy > ceiling:
        buy = ceiling
    return buy


def _sell_copper(item_key: str) -> int:
    return price_band(item_key)[0]


def _shop_config():
    """Built inside the scope: offer rules read live price bands."""
    return synth_shop_config(
        T_SHOP,
        (T_SPRAY, T_FANG, T_APPLE),
        offer_rules=(
            synth_offer_rule(T_SPRAY, max_stock=20),
            synth_offer_rule(T_FANG, max_stock=3),
            synth_offer_rule(T_APPLE, max_stock=20),
        ),
    )
from world.rules.service_view import (
    ACTION_ACCEPT,
    ACTION_BUY,
    ACTION_REGISTER,
    ACTION_SELL,
    ServicesViewError,
    build_services_view,
)

TICK_NOON = 12 * 3600
TICK_NIGHT = 3 * 3600  # before 08:00 opening

_REGISTRATION_TRAIT_KEYS = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_power",
    "guild_merit",
)


class FakeComponent:
    """One service component fake exposing name, slot, and service fields."""

    def __init__(self, name, **fields):
        self.name = name
        self.slot = name
        for key, value in fields.items():
            setattr(self, key, value)


class FakeComponents:
    def __init__(self, *components):
        self._by_name = {component.name: component for component in components}

    def has(self, name):
        return name in self._by_name

    def get(self, slot):
        return self._by_name.get(slot)


class FakeHost:
    def __init__(self, key, pk, *components, location=None):
        self.key = key
        self.pk = pk
        self.components = FakeComponents(*components)
        self.location = location


class FakeRoom:
    def __init__(self, *contents):
        self.contents = list(contents)


class FakeAttributes:
    def __init__(self, traits=None):
        self._store = {}
        if traits is not None:
            self._store[("traits", "traits")] = traits

    def get(self, key, default=None, category=None):
        return self._store.get((key, category), default)


def guild_staff(**fields):
    return FakeComponent(GuildStaff.name, branch_key=BRANCH, **fields)


def guild_examiner(**fields):
    return FakeComponent(GuildExaminer.name, branch_key=BRANCH, **fields)


def merchant(**fields):
    fields.setdefault("shop_key", T_SHOP)
    fields.setdefault(
        "merchant_stock",
        {T_APPLE: 20, T_SPRAY: 3, T_FANG: 1},
    )
    return FakeComponent(Merchant.name, **fields)


def actor(
    *,
    pk=1,
    key="player",
    location=None,
    wallet=1000,
    inventory=None,
    quest_log=None,
    registration=None,
    claims=None,
    equipment=None,
    merit=0,
    guild_rank=None,
    hp_current=None,
    hp_maximum=100,
):
    traits = {
        "guild_merit": {
            "base": merit,
            "current": merit,
            "min": 0,
            "max": None,
            "trait_type": "counter",
        }
    }
    if hp_current is not None:
        traits["hp"] = {
            "base": hp_maximum,
            "mod": 0,
            "mult": 1,
            "current": hp_current,
            "trait_type": "gauge",
        }
    return SimpleNamespace(
        pk=pk,
        key=key,
        location=location,
        guild_rank=guild_rank,
        attributes=FakeAttributes(traits=traits),
        db=SimpleNamespace(
            wallet=wallet,
            inventory=list(inventory or []),
            quest_log=list(quest_log or []),
            guild_registration=registration,
            guild_reward_claims=list(claims or []),
            equipment=equipment,
            active_combat=None,
            disguised_stats=None,
        ),
    )


def registration(**overrides):
    record = {
        "branch_key": BRANCH,
        "registered_tick": 0,
        "displayed_stats": {key: 0 for key in _REGISTRATION_TRAIT_KEYS},
    }
    record.update(overrides)
    return record


def quest_record(quest_id=None, state=QuestState.IN_PROGRESS, progress=0):
    record = QuestRecord(
        quest_id=quest_id or f"{BOARD_QUEST}:1",
        definition_key=BOARD_QUEST,
        issuer_key=TEST_ISSUER_KEY,
        state=state,
        stage_index=0,
        stage_progress=progress,
        deadline_tick=None,
        accepted_tick=0,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
        failure_reason=None if state is not QuestState.FAILED else "abandoned",
    )
    return to_storage(record)


class ServiceRegistryIsolation(unittest.TestCase):
    def setUp(self):
        # Scope before construction: shop/item/tier identities resolve against
        # kit rows. The rank ladder stays shipped so the F→E→S progression
        # asserted below is the real production ladder.
        open_synthetic_scope(
            self, "items", "prices", "shops", "monster_tiers", "guild_branches"
        )
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        install_synthetic_catalog(
            self, synth_catalog(shop_configs={T_SHOP: _shop_config()})
        )
        # Two invented board quests (F and E ladder ranks) with rewards inside
        # the live rank bands; the F quest is this suite's default log row.
        self.board_reward = QuestReward(
            copper=rank_reward_band("F")[0],
            items=(ItemQuantity(T_SPRAY, 2),),
            merit=25,
        )
        register_quest_definition(
            QuestDefinition(
                key=BOARD_QUEST,
                display_name=BOARD_QUEST_DISPLAY,
                quest_type=QuestType.DEFEAT,
                rank="F",
                stages=(
                    QuestStage(
                        index=0,
                        objective=QuestObjective(
                            kind=ObjectiveKind.DEFEAT,
                            quantity=2,
                            monster_tier=a_live_monster_tier_key(),
                        ),
                    ),
                ),
                deadline_hours=None,
            )
        )
        register_guild_offer(
            GuildQuestOffer(
                definition_key=BOARD_QUEST,
                issuer_branch_key=BRANCH,
                reward=self.board_reward,
            )
        )

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offers)
        super().tearDown()


class HostResolutionTests(ServiceRegistryIsolation):
    def _staff_room(self):
        staff = FakeHost("公會長", 10, guild_staff(), guild_examiner(), location=None)
        room = FakeRoom(staff)
        staff.location = room
        return room, staff

    @covers_requirement("webclient-service-menus::service-presentation-resolves-hosts-per-service-class-and-a-stable-player-summary")
    def test_guild_hall_resolves_one_guild_host_and_names_it(self):
        room, staff = self._staff_room()
        self._staff_room()
        player = actor(location=room, registration=registration())
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNotNone(view.host)
        self.assertEqual(view.host.identity, "10")
        self.assertEqual(view.host.display_name, "公會長")
        self.assertIsNotNone(view.guild)
        self.assertIsNotNone(view.guild.rank)
        self.assertIsNone(view.shop)

    def test_general_store_resolves_one_merchant_and_names_it(self):
        store = FakeHost("合成行商", 11, merchant(), location=None)
        room = FakeRoom(store)
        store.location = room
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNotNone(view.host)
        self.assertEqual(view.host.identity, "11")
        self.assertIsNone(view.guild)
        self.assertIsNotNone(view.shop)

    @covers_requirement('npc-identity-titles::compact-presentation-rows-keep-the-plain-npc-name')
    def test_titled_host_rows_stay_plain_key(self):
        # npc-title-identity-core compact-row pin: guild and shop host rows
        # render the plain key even when the host entity carries a title.
        staff = FakeHost("公會長", 10, guild_staff(), location=None)
        staff.npc_title = "白銀之手會長"
        staff_room = FakeRoom(staff)
        staff.location = staff_room
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            guild_view = build_services_view(
                actor(location=staff_room, registration=registration())
            )
        self.assertIsNotNone(guild_view.host)
        self.assertEqual(guild_view.host.display_name, "公會長")
        self.assertNotIn("\u3000", guild_view.host.display_name)

        store = FakeHost("合成行商", 11, merchant(), location=None)
        store.npc_title = "南門行商"
        store_room = FakeRoom(store)
        store.location = store_room
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            shop_view = build_services_view(
                actor(location=store_room, wallet=1000)
            )
        self.assertIsNotNone(shop_view.host)
        self.assertEqual(shop_view.host.display_name, "合成行商")
        self.assertNotIn("\u3000", shop_view.host.display_name)

    @covers_requirement("webclient-service-menus::service-presentation-resolves-hosts-per-service-class-and-a-stable-player-summary")
    def test_ambiguous_guild_hosts_close_only_the_guild_surface(self):
        room = FakeRoom(
            FakeHost("a", 1, guild_staff(), location=None),
            FakeHost("b", 2, guild_staff(), location=None),
            FakeHost("shop", 3, merchant(), location=None),
        )
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "ambiguous_service_host")
        self.assertIsNotNone(view.shop)

    def test_no_host_closes_only_the_affected_surface(self):
        room = FakeRoom()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.host)
        self.assertIsNone(view.guild)
        self.assertIsNone(view.shop)
        self.assertIsNotNone(view.inventory)
        self.assertEqual(view.guild_unavailable_reason, "no_local_service_host")

    def test_co_located_guild_and_merchant_stay_independent(self):
        guild_host = FakeHost("a", 1, guild_staff(), location=None)
        merchant_host = FakeHost("b", 2, merchant(), location=None)
        room = FakeRoom(guild_host, merchant_host)
        guild_host.location = room
        merchant_host.location = room
        player = actor(location=room, wallet=1000, registration=registration())
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNotNone(view.guild)
        self.assertIsNotNone(view.shop)
        self.assertEqual(view.host.identity, "1")


class PlayerSummaryTests(ServiceRegistryIsolation):
    def test_unregistered_summary_is_honest(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertFalse(view.player.guild_registered)
        self.assertIsNone(view.player.guild_rank)
        self.assertEqual(view.player.wallet, 500)
        self.assertEqual(view.player.guild_merit, 0)
        self.assertIsNone(view.player.next_rank)
        self.assertIsNone(view.player.next_threshold)
        register = view.guild.registration.register
        self.assertEqual(register.action_id, ACTION_REGISTER)
        self.assertTrue(register.enabled)
        self.assertEqual(view.guild.board, ())

    def test_registered_summary_reports_rank_and_merit(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500, registration=registration(), merit=60, guild_rank="F")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertTrue(view.player.guild_registered)
        self.assertEqual(view.player.guild_rank, "F")
        self.assertEqual(view.player.guild_merit, 60)
        self.assertEqual(view.player.next_rank, "E")
        self.assertEqual(view.player.next_threshold, 50)
        self.assertFalse(view.guild.registration.register.enabled)

    def test_top_rank_summary_reports_no_next_rank(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500, registration=registration(), merit=999999, guild_rank="S")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.player.next_rank)
        self.assertIsNone(view.player.next_threshold)

    def test_disguised_elf_does_not_distort_the_summary(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500, registration=registration(), merit=0, guild_rank="F")
        player.db.disguised_stats = {"atk_phys": 60, "magic_power": 30}
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertEqual(view.player.guild_rank, "F")
        self.assertEqual(view.player.guild_merit, 0)
        self.assertEqual(view.player.next_rank, "E")
        self.assertEqual(view.player.next_threshold, 50)

    def test_negative_wallet_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=-1)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_missing_world_clock_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500)
        with patch("world.rules.service_view.read_world_clock", return_value=None):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)


class BoardFilteringTests(ServiceRegistryIsolation):
    def _register_e_quest(self):
        definition = QuestDefinition(
            key=E_QUEST,
            display_name="測試E級任務",
            quest_type=QuestType.DEFEAT,
            rank="E",
            stages=(
                QuestStage(
                    index=0,
                    objective=QuestObjective(
                        kind=ObjectiveKind.DEFEAT,
                        quantity=1,
                        monster_tier=a_live_monster_tier_key(),
                    ),
                ),
            ),
            deadline_hours=None,
        )
        register_quest_definition(definition)
        register_guild_offer(
            GuildQuestOffer(
                definition_key=E_QUEST,
                issuer_branch_key=BRANCH,
                reward=QuestReward(
                    copper=rank_reward_band("E")[0], items=(), merit=50
                ),
            )
        )

    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_f_member_sees_only_rank_eligible_board_offers(self):
        self._register_e_quest()
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        keys = [row.definition_key for row in view.guild.board]
        self.assertEqual(keys, [BOARD_QUEST])

    def test_e_member_sees_both_offers_in_rank_key_order(self):
        self._register_e_quest()
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="E")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        keys = [row.definition_key for row in view.guild.board]
        self.assertEqual(keys, [BOARD_QUEST, E_QUEST])
        accept = view.guild.board[0].accept
        self.assertEqual(accept.action_id, ACTION_ACCEPT)
        self.assertTrue(accept.enabled)

    def test_active_record_disables_its_board_accept(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        accept = view.guild.board[0].accept
        self.assertFalse(accept.enabled)
        self.assertEqual(accept.reason_code, "quest_already_active")


class QuestRenderingTests(ServiceRegistryIsolation):
    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_quest_row_carries_full_server_rendered_detail(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        row = view.guild.quests[0]
        self.assertEqual(row.quest_id, f"{BOARD_QUEST}:1")
        self.assertEqual(row.state, "in_progress")
        self.assertEqual(row.stage_index, 0)
        self.assertEqual(row.stage_progress, 0)
        self.assertTrue(row.objective_summary)
        self.assertIsNone(row.deadline_line)
        self.assertTrue(row.detail.startswith(f"{BOARD_QUEST_DISPLAY}\n狀態："))
        self.assertIn("目標：討伐 2 隻", row.detail)
        self.assertIn(
            "獎勵：銅 "
            f"{self.board_reward.copper}、功績 {self.board_reward.merit}、"
            f"{SYNTH_ITEMS['t_ember_spray'].display_name_zh} × 2",
            row.detail,
        )
        self.assertTrue(row.abandon.enabled)
        self.assertFalse(row.turnin.enabled)

    def test_completed_quest_enables_turnin_until_claimed(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        completed = quest_record(state=QuestState.COMPLETED, progress=1)
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[completed],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        row = view.guild.quests[0]
        self.assertFalse(row.abandon.enabled)
        self.assertTrue(row.turnin.enabled)

        claimed = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[completed],
            claims=[f"{BOARD_QUEST}:1"],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(claimed)
        row = view.guild.quests[0]
        self.assertFalse(row.turnin.enabled)
        self.assertEqual(row.turnin.reason_code, "already_claimed")

    def test_deadline_line_renders_when_set(self):
        record = QuestRecord(
            quest_id="deadline:1",
            definition_key=BOARD_QUEST,
            issuer_key=TEST_ISSUER_KEY,
            state=QuestState.IN_PROGRESS,
            stage_index=0,
            stage_progress=0,
            deadline_tick=TICK_NOON + 3 * 3600,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
        )
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[to_storage(record)],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertEqual(view.guild.quests[0].deadline_line, "期限：剩餘 3 小時")

    def test_exam_eligibility_shows_exact_next_rank_only(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F", merit=50)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rank = view.guild.rank
        self.assertIsNotNone(rank)
        self.assertEqual(rank.rank, "F")
        self.assertEqual(rank.next_rank, "E")
        self.assertEqual(rank.next_threshold, 50)
        self.assertTrue(rank.eligible)
        self.assertTrue(rank.exam_start.enabled)

    def test_exam_start_disabled_below_threshold(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F", merit=49)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rank = view.guild.rank
        self.assertFalse(rank.eligible)
        self.assertFalse(rank.exam_start.enabled)
        self.assertEqual(rank.exam_start.reason_code, "below_threshold")

    def test_rank_surface_absent_without_examiner(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild.rank)


class ShopTests(ServiceRegistryIsolation):
    def _shop_room(self):
        store = FakeHost("合成行商", 1, merchant(), location=None)
        room = FakeRoom(store)
        store.location = room
        return room

    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_open_shop_reports_exact_integer_copper_and_stock(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        shop = view.shop
        self.assertTrue(shop.open)
        rows = {row.item_key: row for row in shop.stock}
        self.assertEqual(rows[T_APPLE].buy_copper, _buy_copper(T_APPLE))
        self.assertEqual(rows[T_APPLE].sell_copper, _sell_copper(T_APPLE))
        self.assertEqual(rows[T_APPLE].stock, 20)
        self.assertEqual(rows[T_APPLE].max_stock, 20)
        self.assertEqual(rows[T_SPRAY].stock, 3)
        self.assertTrue(rows[T_APPLE].buy.enabled)

    def test_closed_shop_disables_purchases_but_renders_stock(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NIGHT),
        ):
            view = build_services_view(player)
        shop = view.shop
        self.assertFalse(shop.open)
        self.assertEqual(len(shop.stock), 3)
        for row in shop.stock:
            self.assertFalse(row.buy.enabled)
            self.assertEqual(row.buy.reason_code, "closed")

    def test_quantity_descriptor_advertises_bounded_maximum(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.shop.stock}
        quantity_min = rows[T_SPRAY].buy.quantity_min
        quantity_max = rows[T_SPRAY].buy.quantity_max
        self.assertEqual(quantity_min, 1)
        self.assertLessEqual(quantity_max, 3)
        self.assertLessEqual(quantity_max, 1000)

    def test_insufficient_funds_disables_buy(self):
        room = self._shop_room()
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.shop.stock}
        self.assertFalse(rows[T_SPRAY].buy.enabled)
        self.assertEqual(rows[T_SPRAY].buy.reason_code, "insufficient_funds")

    def test_sellable_rows_aggregate_held_items(self):
        room = FakeRoom(
            FakeHost(
                "合成行商",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        player = actor(location=room, wallet=1000, inventory=[T_APPLE, T_APPLE, T_FANG])
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        sellable = {row.item_key: row for row in view.shop.sellable}
        self.assertEqual(sellable[T_APPLE].held, 2)
        self.assertEqual(sellable[T_APPLE].sell_copper, _sell_copper(T_APPLE))
        self.assertTrue(sellable[T_APPLE].sell.enabled)
        self.assertEqual(sellable[T_FANG].sell.enabled, True)


class InventoryTests(ServiceRegistryIsolation):
    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_repeated_key_inventory_aggregates_and_marks_equipped(self):
        room = FakeRoom()
        equipment = {
            "weapon_main": T_KNIFE,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        player = actor(
            location=room,
            wallet=42,
            inventory=[T_SPRAY, T_APPLE, T_KNIFE, T_SPRAY],
            equipment=equipment,
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.inventory.rows}
        self.assertEqual(rows[T_SPRAY].held, 2)
        self.assertEqual(rows[T_SPRAY].equipped, False)
        self.assertEqual(rows[T_APPLE].held, 1)
        self.assertEqual(rows[T_KNIFE].equipped, True)
        self.assertEqual(view.inventory.wallet, 42)
        self.assertEqual(view.player.wallet, 42)

    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_registered_inventory_key_projects_registry_presentation(self):
        room = FakeRoom()
        player = actor(
            location=room,
            wallet=42,
            inventory=[T_SPRAY, T_SPRAY, "mystery_relic"],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.inventory.rows}
        self.assertEqual(
            rows[T_SPRAY].presentation,
            live_item_registry()[T_SPRAY].presentation,
        )
        self.assertEqual(rows[T_SPRAY].held, 2)
        self.assertIsNone(rows["mystery_relic"].presentation)
        self.assertEqual(rows["mystery_relic"].display_name, "mystery_relic")


class SurfaceIsolationTests(ServiceRegistryIsolation):
    def test_corrupt_quest_log_degrades_only_the_guild_surface(self):
        room = FakeRoom(
            FakeHost("g", 1, guild_staff(), location=None),
            FakeHost("m", 2, merchant(), location=None),
        )
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(),
            quest_log=[{"quest_id": "broken", "definition_key": "nope"}],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "malformed_quest_log")
        self.assertIsNotNone(view.shop)
        self.assertIsNotNone(view.inventory)
        self.assertEqual(view.pagination.board_total, 0)
        self.assertEqual(view.pagination.stock_total, 3)

    def test_malformed_merchant_stock_degrades_only_the_shop_surface(self):
        room = FakeRoom(
            FakeHost("g", 1, guild_staff(), location=None),
            FakeHost("m", 2, merchant(merchant_stock={"nope": 5}), location=None),
        )
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(),
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "malformed_stock")
        self.assertIsNotNone(view.guild)
        self.assertIsNotNone(view.inventory)

    def test_corrupt_registration_degrades_the_guild_surface(self):
        room = FakeRoom(FakeHost("g", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(displayed_stats={"hp": 0}),
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "guild_data_error")
        self.assertFalse(view.player.guild_registered)

    def test_pagination_totals_match_shipped_rows_and_null_surfaces(self):
        room = FakeRoom(
            FakeHost("g", 1, guild_staff(), location=None),
            FakeHost("m", 2, merchant(), location=None),
        )
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
            inventory=[T_APPLE, T_APPLE],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertEqual(view.pagination.board_total, 1)
        self.assertEqual(view.pagination.quest_total, 1)
        self.assertEqual(view.pagination.stock_total, 3)
        self.assertEqual(view.pagination.sellable_total, 1)
        self.assertEqual(view.pagination.inventory_total, 1)


class MeritAndRankEdgeTests(ServiceRegistryIsolation):
    def test_missing_trait_storage_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5)
        player.attributes = FakeAttributes(traits=None)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_malformed_guild_merit_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5)
        player.attributes = FakeAttributes(
            traits={"guild_merit": {"base": -3, "current": -3}}
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_non_mapping_guild_merit_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5)
        player.attributes = FakeAttributes(traits={"guild_merit": "broken"})
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_malformed_guild_rank_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5, registration=registration(), guild_rank="Z")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_top_rank_exam_start_reports_settled(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, wallet=5, registration=registration(), guild_rank="S", merit=999999)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rank = view.guild.rank
        self.assertFalse(rank.eligible)
        self.assertIsNone(rank.next_rank)
        self.assertEqual(rank.exam_start.reason_code, "already_settled")

    def test_active_session_blanks_remote_surfaces(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, wallet=5, registration=registration(), guild_rank="F", merit=50)
        player.db.active_combat = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 1,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertIsNone(view.shop)
        self.assertIsNone(view.host)
        self.assertIsNotNone(view.player)
        self.assertIsNotNone(view.inventory)


class GuildCorruptionEdgeTests(ServiceRegistryIsolation):
    def test_corrupt_registration_makes_guild_surface_unavailable(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=5,
            registration=registration(displayed_stats={"hp": 0}),
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "guild_data_error")

    def test_malformed_reward_claims_degrades_the_guild_surface(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=5,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
            claims="not-a-list",
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "malformed_quest_log")

    def test_unregistered_quest_rows_render_without_reward_section(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=5,
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        # An unregistered actor sees a guild surface with no board and the
        # quest row rendering without the reward line.
        self.assertEqual(view.guild.board, ())
        row = view.guild.quests[0]
        self.assertNotIn("獎勵：", row.detail)


class ShopEdgeTests(ServiceRegistryIsolation):
    def test_merchant_host_without_component_closes_shop(self):
        room = FakeRoom(FakeHost("m", 1, location=None))
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "no_local_service_host")

    def test_merchant_component_missing_closes_shop(self):
        # A host whose component lookup returns None even though its name is
        # advertised is treated as no merchant.
        class BrokenComponents(FakeComponents):
            def has(self, name):
                return name == Merchant.name

            def get(self, slot):
                return None

        room = FakeRoom(FakeHost("m", 1, location=None))
        room.contents[0].components = BrokenComponents()
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "no_merchant")

    def test_unknown_shop_key_closes_shop(self):
        room = FakeRoom(FakeHost("m", 1, merchant(shop_key="unknown_shop"), location=None))
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "unknown_shop")

    def test_sellable_excludes_unsellable_and_unoffered_items(self):
        room = FakeRoom(
            FakeHost(
                "m",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        # T_APPLE/T_SPRAY are sellable and offered; T_PASS is a held registry
        # item that is unsellable; a made-up key is neither.
        player = actor(
            location=room,
            wallet=5,
            inventory=[
                T_APPLE,
                T_SPRAY,
                T_PASS,
                "made_up_item",
                "made_up_item",
            ],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        keys = {row.item_key for row in view.shop.sellable}
        self.assertEqual(keys, {T_APPLE, T_SPRAY})
        self.assertNotIn("made_up_item", keys)
        self.assertNotIn(T_PASS, keys)

    def test_closed_sell_and_insufficient_items_reasons(self):
        room = FakeRoom(
            FakeHost(
                "m",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        player = actor(location=room, wallet=5, inventory=[T_APPLE])
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NIGHT),
        ):
            view = build_services_view(player)
        sellable = {row.item_key: row for row in view.shop.sellable}
        self.assertEqual(sellable[T_APPLE].sell.reason_code, "closed")

        open_room = FakeRoom(
            FakeHost(
                "m",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        player2 = actor(location=open_room, wallet=5, inventory=[T_FANG, T_FANG, T_FANG])
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player2)
        # The fang rule caps stock at 3 with 1 left; held 3 sells are capped at
        # 2 before overflow, so the enabled sell advertises min(held, cap)=2.
        sellable = {row.item_key: row for row in view.shop.sellable}
        self.assertTrue(sellable[T_FANG].sell.enabled)
        self.assertEqual(sellable[T_FANG].sell.quantity_max, 2)

    def test_malformed_equipment_degrades_inventory(self):
        room = FakeRoom()
        player = actor(location=room, wallet=5, inventory=[T_APPLE], equipment="corrupt")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.inventory)
        self.assertEqual(view.inventory_unavailable_reason, "malformed_equipment")

    def test_accessories_not_a_list_fails_closed_unavailable(self):
        # The services rows normalize through the shared fail-closed
        # equipment layer (add-inventory-item-actions rubber-duck fix): a
        # malformed accessories value is never partially trusted — the
        # inventory section is unavailable, not partially equipped.
        room = FakeRoom()
        player = actor(
            location=room,
            wallet=5,
            inventory=[T_KNIFE],
            equipment={
                "weapon_main": T_KNIFE,
                "weapon_off": None,
                "armor": None,
                "accessories": "corrupt",
            },
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.inventory)
        self.assertEqual(view.inventory_unavailable_reason, "malformed_equipment")

    def test_cross_slot_duplicate_fails_closed_unavailable(self):
        # One key stored in two slots is malformed for the shared equipment
        # layer, so the panel never publishes a partial equipped truth.
        room = FakeRoom()
        player = actor(
            location=room,
            wallet=5,
            inventory=[T_KNIFE],
            equipment={
                "weapon_main": T_KNIFE,
                "weapon_off": None,
                "armor": None,
                "accessories": [T_KNIFE],
            },
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.inventory)
        self.assertEqual(view.inventory_unavailable_reason, "malformed_equipment")


class InventoryRowActionTests(ServiceRegistryIsolation):
    """Personal-item descriptors derived by the shared preflight APIs."""

    def _build(self, player):
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            return build_services_view(player)

    def _rows(self, view):
        return {row.item_key: row for row in view.inventory.rows}

    def test_injured_usable_row_carries_enabled_use_descriptor(self):
        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY],
            hp_current=50,
        )
        row = self._rows(self._build(player))[T_SPRAY]
        self.assertIsNotNone(row.action)
        self.assertEqual(row.action.action_id, "inventory.use")
        self.assertEqual(row.action.label, "使用")
        self.assertTrue(row.action.enabled)
        self.assertIsNone(row.action.reason_code)

    def test_full_hp_use_disabled_with_stable_reason(self):
        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY],
            hp_current=100,
        )
        row = self._rows(self._build(player))[T_SPRAY]
        self.assertFalse(row.action.enabled)
        self.assertEqual(row.action.reason_code, "hp_full")
        self.assertEqual(
            row.action.reason_message,
            "你的體力已經全滿。",
        )

    def test_unknown_and_inspect_only_rows_have_null_actions(self):
        player = actor(
            location=FakeRoom(),
            inventory=["mystery_relic", T_APPLE],
            hp_current=50,
        )
        rows = self._rows(self._build(player))
        self.assertIsNone(rows["mystery_relic"].action)
        self.assertIsNone(rows["mystery_relic"].presentation)
        self.assertIsNone(rows[T_APPLE].action)
        self.assertIsNotNone(rows[T_APPLE].presentation)

    def test_equipment_toggle_descriptor_tracks_equipped_state(self):
        equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        player = actor(
            location=FakeRoom(),
            inventory=[T_KNIFE],
            equipment=dict(equipment),
            hp_current=100,
        )
        row = self._rows(self._build(player))[T_KNIFE]
        self.assertEqual(row.action.action_id, "inventory.toggle_equip")
        self.assertEqual(row.action.label, "裝備")
        self.assertTrue(row.action.enabled)

        player.db.equipment = {**equipment, "weapon_main": T_KNIFE}
        row = self._rows(self._build(player))[T_KNIFE]
        self.assertTrue(row.equipped)
        self.assertEqual(row.action.label, "卸下")
        self.assertTrue(row.action.enabled)

    def test_sixth_accessory_disabled_and_equipped_rows_stay_enabled(self):
        from world.skills.equipment import EquipmentSlot

        registry = live_item_registry()
        for index in range(6):
            registry[f"ring_{index}"] = ItemDefinition(
                key=f"ring_{index}",
                display_name_zh="測試戒指",
                price_table_key="ring_0",
                sellable=False,
                presentation=ItemPresentation(
                    kind=ItemKind.ACCESSORY,
                    icon_key=ItemIconKey.ACCESSORY,
                    rarity=ItemRarity.COMMON,
                    summary_zh="測試用的飾品。",
                ),
                equipment_slot=EquipmentSlot.ACCESSORY,
                modifier_key=EquipmentModifierKey.PROTECTIVE_RING,
            )
        player = actor(
            location=FakeRoom(),
            inventory=[f"ring_{index}" for index in range(6)],
            equipment={
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [f"ring_{index}" for index in range(5)],
            },
            hp_current=100,
        )
        rows = self._rows(self._build(player))
        for index in range(5):
            row = rows[f"ring_{index}"]
            self.assertTrue(row.equipped)
            self.assertTrue(row.action.enabled)
            self.assertEqual(row.action.label, "卸下")
        overflow = rows["ring_5"]
        self.assertFalse(overflow.action.enabled)
        self.assertEqual(overflow.action.reason_code, "accessory_slots_full")
        self.assertIn("飾品欄", overflow.action.reason_message)

    def test_combat_view_keeps_personal_use_descriptor_available(self):
        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY],
            hp_current=50,
        )
        player.db.active_combat = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 1,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        view = self._build(player)
        self.assertIsNone(view.guild)
        row = self._rows(view)[T_SPRAY]
        self.assertTrue(row.action.enabled)

    def test_descriptor_derivation_mutates_nothing(self):
        from copy import deepcopy

        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY, T_KNIFE, "mystery_relic"],
            equipment={
                "weapon_main": T_KNIFE,
                "weapon_off": None,
                "armor": None,
                "accessories": [],
            },
            hp_current=50,
        )
        before_db = deepcopy(vars(player.db))
        before_traits = deepcopy(player.attributes._store)
        self._build(player)
        self.assertEqual(vars(player.db), before_db)
        self.assertEqual(player.attributes._store, before_traits)


if __name__ == "__main__":
    unittest.main()
