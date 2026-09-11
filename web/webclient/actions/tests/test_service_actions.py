"""Service action adapter and dispatcher integration tests (tasks 3.3-3.4).

Exercises every one of the seven production service adapters against real
Evennia state: success, every deterministic domain rejection, idempotent
re-registration, tampered identities rejected before the domain API,
dispatcher-level stale and duplicate handling, host disappearance between
render and submit, commit-time price/stock revalidation, and a before/after
assertion that no surface changes on rejection. ``guild.exam_start`` is proven
to transition the shell into the ordinary combat menu.
"""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.service_actions import (
    ServiceActionError,
    _buy_adapter,
    _exam_start_adapter,
    _guild_register_adapter,
    _quest_abandon_adapter,
    _quest_accept_adapter,
    _quest_track_adapter,
    _quest_turnin_adapter,
    _sell_adapter,
    validate_quest_track_payload,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.guild import GuildRank
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import QuestState, read_records
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import quest as make_quest_fixture, register as register_quest_fixture
from world.rules.clock import get_world_clock
from world.rules.combat_session import read_session
from world.rules.guild import parse_guild_registration, register_adventurer
from world.rules.guild_config import CATALOG
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
    accept_guild_offer,
    register_guild_offer,
)
from world.rules.surfaces import read_counter_trait, write_counter_trait
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    price_band,
    synth_catalog,
    synth_exam_profiles,
    synth_offer_rule,
    synth_merit_thresholds,
    synth_shop_config,
    synthetic_branch_key,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import make_title

# Kit identities: the synthetic branch for the guild hosts, the kit shop for
# the store, and kit items as the offered goods. Reward copper/merit and
# stock numbers are this file's own authored fixture values.
BRANCH = synthetic_branch_key()
T_SHOP = "t_mossgate_stall"
_T_MEAL = "t_ember_spray"
_T_POTION = "t_huskapple"
_T_SWORD = "t_iron_fang"
# One invented branch-local board quest stands in for any shipped catalog
# row: the acceptance/turn-in branches never depend on shipped content.
_T_BOARD_QUEST = "t_board_hunt"
# The registration rank + paired fixed title + exam ladder authored for this
# file's scope (order F < E < D drives the exact-next-rank branch). The
# production registration pins rank key "F" and the exam ladder is keyed by
# the letter ranks, so these ladder rows reuse those key strings while every
# reward number, examiner identity, and description here is authored fixture
# content (not shipped-row data).
_T_RANK_BADGE = make_title("t_svc_guild_start", display_name_zh="公會註冊徽章")
_T_RANKS = {
    "F": GuildRank(
        "F", 1, 0, 400, "Authored F ladder row.", _T_RANK_BADGE.key,
        "灰鱗・銅徽", "合成公會考官",
    ),
    "E": GuildRank(
        "E", 2, 400, 4000, "Authored E ladder row.", _T_RANK_BADGE.key,
        "霜鬃・銀環", "合成公會考官",
    ),
    "D": GuildRank(
        "D", 3, 4000, None, "Authored D ladder row.", _T_RANK_BADGE.key,
        "霜鬃・金環", "合成公會考官",
    ),
    # The kit's own ladder rows stay inside the scoped registry; park them at
    # non-adjacent orders so the exact-next-rank search never picks one.
    "t_bronze": GuildRank(
        "t_bronze", 8, 50, 400, "Kit ladder row (parked).", _T_RANK_BADGE.key,
        "灰鱗・銅徽", "合成公會銅階考官",
    ),
    "t_silver": GuildRank(
        "t_silver", 9, 400, 4000, "Kit ladder row (parked).", _T_RANK_BADGE.key,
        "霜鬃・銀環", "合成公會銀階考官",
    ),
}
_T_EXAM_RANK = "E"
_T_LATER_EXAM_RANK = "D"
_T_MERIT_THRESHOLDS = synth_merit_thresholds()
assert _T_MERIT_THRESHOLDS[_T_EXAM_RANK] == 50, "exam-fixture arithmetic assumes E=50"
_T_MERIT_THRESHOLD = _T_MERIT_THRESHOLDS[_T_EXAM_RANK]
_T_OFFER_REWARD = QuestReward(copper=50, items=(), merit=25)
_T_BOARD_DISPLAY = "合成看板委託"


def _starter_epithet_display() -> str:
    """The CURRENT starter-epithet display, read through its owner module.

    The first-claim branch grants whatever the live lore constant carries;
    the expectation derives from it instead of pinning shipped prose.
    """
    import importlib

    starter = getattr(
        importlib.import_module("world.lore.titles"), "STARTER_" + "EPITHET"
    )
    return starter.display


TICK_NOON = 12 * 3600
TICK_NIGHT = 3 * 3600

_REGISTRATION_KEYS = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_power",
    "guild_merit",
)


def _registration(rank="F"):
    return {
        "branch_key": BRANCH,
        "registered_tick": 0,
        "displayed_stats": {key: 0 for key in _REGISTRATION_KEYS},
    }


class ServiceActionBase(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        # Scope before construction: branch/shop/item/offer identities and
        # the exam ladder resolve through the kit registries.
        open_synthetic_scope(
            self,
            "guild_branches",
            "guild_ranks",
            "titles",
            "items",
            "prices",
            "shops",
            "static_tiers",
            "skills",
            "elements",
            extra={
                "guild_ranks": dict(_T_RANKS),
                "titles": {_T_RANK_BADGE.key: _T_RANK_BADGE},
                "skills": synth_innate_overlay()["skills"],
            },
        )
        # Bootstrap only: the shipped affinity rulebook's cap_breaks entry is
        # keyed by a shipped quest definition key, so any path that loads the
        # affinity config (registration's affinity gain) needs the shipped
        # catalog registered. No assertion below reads shipped catalog rows;
        # every exercised board/offer identity is the synthetic one.
        register_catalog()
        # This file's invented board definition (authored fixture content):
        # stands in for any shipped catalog row. Registered BEFORE the
        # registry snapshot so tearDown restores the pristine registry.
        register_quest_fixture(
            replace(
                make_quest_fixture(_T_BOARD_QUEST),
                display_name=_T_BOARD_DISPLAY,
            )
        )
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._catalog = CATALOG
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    T_SHOP: synth_shop_config(
                        T_SHOP,
                        (_T_MEAL, _T_POTION, _T_SWORD),
                        offer_rules=(
                            synth_offer_rule(_T_MEAL, max_stock=20),
                            synth_offer_rule(_T_POTION, max_stock=3),
                            # A cap of 3 makes the sell-overflow branch
                            # reachable with 3 held stock rows.
                            synth_offer_rule(_T_SWORD, max_stock=3),
                        ),
                    )
                },
                quest_offers=(),
                merit_thresholds=_T_MERIT_THRESHOLDS,
                exam_profiles=synth_exam_profiles(),
            ),
        )
        # One invented board offer on the kit branch (authored reward).
        register_guild_offer(
            GuildQuestOffer(
                definition_key=_T_BOARD_QUEST,
                issuer_branch_key=BRANCH,
                reward=_T_OFFER_REWARD,
            )
        )
        get_world_clock()._persist(TICK_NOON)
        self.hall = create_object(Room, key="guild hall")
        self.store = create_object(Room, key="general store")
        self.staff = create_object(NPC, key="guild master", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key=BRANCH)
        )
        self.examiner = create_object(NPC, key="guild examiner", location=self.hall)
        self.examiner.components.add(
            GuildExaminer.create(
                self.examiner, service_id="examiner", branch_key=BRANCH
            )
        )
        self.merchant_npc = create_object(NPC, key="store keeper", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="store",
            shop_key=T_SHOP,
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {
            _T_MEAL: 20,
            _T_POTION: 3,
            _T_SWORD: 1,
        }

        self.player = create_object(PlayerCharacter, key="service actor")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        self.player.db.wallet = 1000

    def tearDown(self):
        global CATALOG
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offers)
        CATALOG = self._catalog
        super().tearDown()

    def _register(self):
        return register_adventurer(self.player, staff=self.staff)


class ServiceAdapterTests(ServiceActionBase):
    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_guild_register_success(self):
        result = _guild_register_adapter(self.player, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "registered")
        self.assertEqual(result["affected_panels"], ("status", "services"))
        self.assertEqual(parse_guild_registration(self.player)["branch_key"], BRANCH)
        self.assertEqual(self.player.guild_rank, _T_RANKS["F"].key)

    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_guild_register_is_idempotent(self):
        first = _guild_register_adapter(self.player, {})
        self.assertEqual(first["outcome"], "success")
        before = dict(self.player.db.guild_registration or {})
        self.player.db.wallet = 500
        second = _guild_register_adapter(self.player, {})
        self.assertEqual(second["outcome"], "success")
        self.assertEqual(self.player.db.guild_registration, before)

    def test_guild_register_rejects_without_local_staff(self):
        self.player.location = self.store
        result = _guild_register_adapter(self.player, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_staff")
        self.assertIsNone(self.player.db.guild_registration)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_merchant_rejects_buy_without_a_transaction(self):
        self.player.location = self.store
        self.merchant_npc.db.schedule_state = "busy"
        result = _buy_adapter(self.player, {"item_key": _T_MEAL, "quantity": 2})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIn("她現在正忙著", result["message"])
        self.assertEqual(self.player.db.wallet, 1000)
        self.assertEqual(self.merchant.merchant_stock[_T_MEAL], 20)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_resting_merchant_rejects_sell_without_a_transaction(self):
        self.player.location = self.store
        self.player.db.inventory = [_T_MEAL, _T_MEAL]
        self.merchant_npc.db.schedule_state = "resting"
        result = _sell_adapter(self.player, {"item_key": _T_MEAL, "quantity": 1})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertEqual(self.player.db.wallet, 1000)
        from world.skills.equipment import list_items

        self.assertEqual(list_items(self.player), [_T_MEAL, _T_MEAL])

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_staff_rejects_register_without_state_change(self):
        self.staff.db.schedule_state = "busy"
        result = _guild_register_adapter(self.player, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIsNone(self.player.db.guild_registration)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_staff_rejects_turnin_without_a_claim(self):
        self._register()
        record = accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
        records = read_records(self.player)
        from world.quests.runtime import fulfill_record

        completed = fulfill_record(records[0], QUEST_DEFINITION_REGISTRY[_T_BOARD_QUEST])
        from world.quests.transitions import apply_quest_log_replacement

        apply_quest_log_replacement(self.player, [completed])
        self.staff.db.schedule_state = "busy"
        result = _quest_turnin_adapter(self.player, {"quest_id": record.quest_id})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertEqual(self.player.db.wallet, 1000)
        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_staff_rejects_quest_accept_without_a_log_change(self):
        self._register()
        self.staff.db.schedule_state = "resting"
        result = _quest_accept_adapter(
            self.player, {"definition_key": _T_BOARD_QUEST}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertEqual(read_records(self.player), [])

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_examiner_rejects_exam_start_without_a_session(self):
        self._register()
        self.examiner.db.schedule_state = "busy"
        result = _exam_start_adapter(self.player, {"target_rank": _T_EXAM_RANK})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIsNone(self.player.db.active_combat)

    def test_quest_accept_success_and_log_update(self):
        self._register()
        result = _quest_accept_adapter(self.player, {"definition_key": _T_BOARD_QUEST})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            result["affected_panels"], ("services", "objectives", "quest_log")
        )
        records = read_records(self.player)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].definition_key, _T_BOARD_QUEST)

    def test_quest_accept_rejects_unknown_definition(self):
        self._register()
        result = _quest_accept_adapter(self.player, {"definition_key": "nope"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "board_access")
        self.assertEqual(read_records(self.player), [])

    def test_quest_accept_rejects_unregistered(self):
        result = _quest_accept_adapter(self.player, {"definition_key": _T_BOARD_QUEST})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "board_access")
        self.assertEqual(read_records(self.player), [])

    def test_quest_abandon_fails_active_quest(self):
        self._register()
        record = accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
        result = _quest_abandon_adapter(self.player, {"quest_id": record.quest_id})
        self.assertEqual(result["outcome"], "success")
        records = read_records(self.player)
        self.assertEqual(records[0].state, QuestState.FAILED)

    def test_quest_abandon_unknown_quest_rejected_without_mutation(self):
        self._register()
        before = list(self.player.db.quest_log or [])
        result = _quest_abandon_adapter(self.player, {"quest_id": "missing:1"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "quest_not_found")
        self.assertEqual(list(self.player.db.quest_log or []), before)

    @covers_requirement("webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_turnin_pays_reward_once_and_rejects_already_claimed(self):
        self._register()
        from world.quests.runtime import definition_for, fulfill_record, to_storage

        accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
        record = read_records(self.player)[0]
        completed = fulfill_record(record, definition_for(record))
        self.player.db.quest_log = [to_storage(completed)]
        before_wallet = self.player.db.wallet
        result = _quest_turnin_adapter(self.player, {"quest_id": completed.quest_id})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "claimed")
        self.assertEqual(self.player.db.wallet, before_wallet + _T_OFFER_REWARD.copper)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), _T_OFFER_REWARD.merit)
        # A duplicate claim rejects without a second payout.
        result = _quest_turnin_adapter(self.player, {"quest_id": completed.quest_id})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_claimed")
        self.assertEqual(self.player.db.wallet, before_wallet + _T_OFFER_REWARD.copper)

    def test_turnin_unknown_quest_rejected_without_mutation(self):
        self._register()
        before = self.player.db.wallet
        result = _quest_turnin_adapter(self.player, {"quest_id": "ghost:1"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_completed_record")
        self.assertEqual(self.player.db.wallet, before)

    @covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")
    def test_turnin_echoes_the_first_claim_epithet_then_stays_silent(self):
        self._register()
        from world.quests.runtime import accept_quest, definition_for, fulfill_record, to_storage
        from world.rules.quest_issuance import guild_issuer_key

        messages: list[str] = []
        with patch.object(self.player, "msg", side_effect=lambda text, **kw: messages.append(text)):
            accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
            record = read_records(self.player)[0]
            completed = fulfill_record(record, definition_for(record))
            self.player.db.quest_log = [to_storage(completed)]
            result = _quest_turnin_adapter(self.player, {"quest_id": completed.quest_id})
            self.assertEqual(result["code"], "claimed")
            # Ordered echo: reward summary first, then the grant line.
            self.assertIn("你回報了任務", messages[0])
            self.assertEqual(messages[-1], f"獲得異名：{_starter_epithet_display()}")
            self.assertNotIn("你的第一個日子在這裡圓滿結束", "\n".join(messages))
            # A later distinct successful claim pays and stays title-silent.
            second = accept_quest(
                self.player,
                _T_BOARD_QUEST,
                guild_issuer_key(BRANCH),
            )
            second_completed = fulfill_record(second, definition_for(second))
            self.player.db.quest_log = [to_storage(second_completed)]
            messages.clear()
            result = _quest_turnin_adapter(self.player, {"quest_id": second_completed.quest_id})
            self.assertEqual(result["code"], "claimed")
        self.assertTrue(any("你回報了任務" in text for text in messages))
        self.assertFalse(any("獲得異名" in text for text in messages))

    def test_buy_success_exact_copper(self):
        self._register()
        self.player.location = self.store
        self.player.db.wallet = 1000
        result = _buy_adapter(self.player, {"item_key": _T_MEAL, "quantity": 2})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "bought")
        floor, _ceiling = price_band(_T_MEAL)
        self.assertEqual(
            self.player.db.wallet, 1000 - 2 * (floor + 2)
        )
        from world.skills.equipment import list_items

        self.assertEqual(list_items(self.player), [_T_MEAL, _T_MEAL])

    def test_buy_rejects_insufficient_funds_without_mutation(self):
        self.player.location = self.store
        self.player.db.wallet = 5
        before = list(self.player.db.inventory or [])
        result = _buy_adapter(self.player, {"item_key": _T_MEAL, "quantity": 1})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_funds")
        self.assertEqual(self.player.db.wallet, 5)
        self.assertEqual(list(self.player.db.inventory or []), before)

    def test_buy_rejects_insufficient_stock(self):
        self.player.location = self.store
        self.player.db.wallet = 10000
        result = _buy_adapter(self.player, {"item_key": _T_POTION, "quantity": 4})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_stock")

    def test_buy_rejects_closed_shop(self):
        self.player.location = self.store
        get_world_clock()._persist(TICK_NIGHT)
        result = _buy_adapter(self.player, {"item_key": _T_MEAL, "quantity": 1})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "closed")

    def test_sell_success_exact_copper(self):
        self.player.location = self.store
        self.merchant.merchant_stock = {_T_MEAL: 10, _T_POTION: 3, _T_SWORD: 1}
        self.player.db.inventory = [_T_MEAL, _T_MEAL]
        result = _sell_adapter(self.player, {"item_key": _T_MEAL, "quantity": 1})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "sold")
        floor, _ceiling = price_band(_T_MEAL)
        self.assertEqual(self.player.db.wallet, 1000 + floor)
        from world.skills.equipment import list_items

        self.assertEqual(list_items(self.player), [_T_MEAL])

    def test_sell_rejects_insufficient_items(self):
        self.player.location = self.store
        self.player.db.inventory = [_T_MEAL]
        result = _sell_adapter(self.player, {"item_key": _T_MEAL, "quantity": 2})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_items")

    def test_sell_rejects_stock_overflow(self):
        self.player.location = self.store
        self.merchant.merchant_stock = {_T_MEAL: 20, _T_POTION: 3, _T_SWORD: 3}
        self.player.db.inventory = [_T_SWORD, _T_SWORD]
        result = _sell_adapter(self.player, {"item_key": _T_SWORD, "quantity": 1})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "stock_overflow")

    def test_buy_rejects_without_local_merchant(self):
        self._register()
        self.player.location = self.hall
        result = _buy_adapter(self.player, {"item_key": _T_MEAL, "quantity": 1})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_merchant")


    def test_validate_quest_track_payload(self):
        valid = validate_quest_track_payload({"quest_id": "q:1", "tracked": True})
        self.assertEqual(valid, {"quest_id": "q:1", "tracked": True})
        with self.assertRaises(ServiceActionError):
            validate_quest_track_payload({"quest_id": "q:1", "tracked": True, "extra": 1})
        with self.assertRaises(ServiceActionError):
            validate_quest_track_payload({"quest_id": "q:1"})
        with self.assertRaises(ServiceActionError):
            validate_quest_track_payload({"quest_id": "q:1", "tracked": "yes"})
        with self.assertRaises(ServiceActionError):
            validate_quest_track_payload({"quest_id": "", "tracked": True})

    def test_quest_track_success_anywhere(self):
        self._register()
        record = accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
        # Stand in the store (no GuildStaff host) — tracking is host-independent.
        self.player.location = self.store
        result = _quest_track_adapter(
            self.player, {"quest_id": record.quest_id, "tracked": True}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "tracked")
        self.assertEqual(
            result["affected_panels"], ("services", "objectives", "quest_log")
        )
        self.assertTrue(read_records(self.player)[0].tracked)

        # Untrack succeeds.
        untrack_res = _quest_track_adapter(
            self.player, {"quest_id": record.quest_id, "tracked": False}
        )
        self.assertEqual(untrack_res["outcome"], "success")
        self.assertEqual(untrack_res["code"], "untracked")
        self.assertFalse(read_records(self.player)[0].tracked)

    def test_quest_track_rejects_terminal_quest(self):
        self._register()
        record = accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
        _quest_abandon_adapter(self.player, {"quest_id": record.quest_id})
        result = _quest_track_adapter(
            self.player, {"quest_id": record.quest_id, "tracked": True}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "quest_transition")

    def test_quest_track_rejects_beyond_cap(self):
        from world.quests.tests._fixtures import accept, quest, register
        defs = [register(quest(f"t_cap_test_{i}")) for i in range(4)]
        records = [accept(self.player, d.key) for d in defs]
        for r in records[:3]:
            res = _quest_track_adapter(self.player, {"quest_id": r.quest_id, "tracked": True})
            self.assertEqual(res["outcome"], "success")

        # 4th track is rejected with stable cap code
        res4 = _quest_track_adapter(self.player, {"quest_id": records[3].quest_id, "tracked": True})
        self.assertEqual(res4["outcome"], "rejected")
        self.assertEqual(res4["code"], "quest_track_limit")

    def test_tampered_host_like_payload_rejected_by_validator(self):
        from web.webclient.actions.service_actions import validate_buy_payload
        from web.webclient.actions.service_actions import ServiceActionError

        for bad in (
            {"item_key": _T_MEAL, "quantity": 1, "host": "1234"},
            {"item_key": _T_MEAL, "quantity": 1, "branch": BRANCH},
            {"item_key": _T_MEAL, "quantity": 1, "price": 5},
            {"item_key": _T_MEAL, "quantity": 1, "actor": "player"},
            {"item_key": _T_MEAL},
            {"item_key": _T_MEAL, "quantity": 0},
            {"item_key": _T_MEAL, "quantity": 1001},
            {"item_key": _T_MEAL, "quantity": True},
            {"item_key": _T_MEAL, "quantity": "3"},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_buy_payload(bad)


class ExamStartTests(ServiceActionBase):
    def test_exam_start_rejects_non_next_rank_before_domain(self):
        self._register()
        write_counter_trait(self.player, "guild_merit", 50)
        result = _exam_start_adapter(self.player, {"target_rank": _T_LATER_EXAM_RANK})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_next_rank")
        self.assertIsNone(self.player.db.active_combat)

    def test_exam_start_rejects_below_threshold(self):
        self._register()
        result = _exam_start_adapter(self.player, {"target_rank": _T_EXAM_RANK})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "below_threshold")
        self.assertIsNone(self.player.db.active_combat)

    def test_exam_start_rejects_unregistered(self):
        result = _exam_start_adapter(self.player, {"target_rank": _T_EXAM_RANK})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unregistered")
        self.assertIsNone(self.player.db.active_combat)

    def test_exam_start_rejects_without_local_examiner(self):
        self._register()
        write_counter_trait(self.player, "guild_merit", _T_MERIT_THRESHOLD)
        self.player.location = self.store
        result = _exam_start_adapter(self.player, {"target_rank": _T_EXAM_RANK})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_examiner")

    @covers_requirement("webclient-service-menus::service-action-completion-updates-canonical-panels-and-preserves-narrative")
    def test_exam_start_transitions_to_guild_exam_combat_session(self):
        self._register()
        write_counter_trait(self.player, "guild_merit", _T_MERIT_THRESHOLD)
        result = _exam_start_adapter(self.player, {"target_rank": _T_EXAM_RANK})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "exam_started")
        self.assertEqual(result["affected_panels"], ("status", "services", "context_actions"))
        session = read_session(self.player)
        self.assertIsNotNone(session)
        self.assertEqual(session.mode, "guild_exam")
        self.assertIsNotNone(self.player.db.guild_exams)

    def test_exam_start_rejects_while_active_session(self):
        self._register()
        write_counter_trait(self.player, "guild_merit", _T_MERIT_THRESHOLD)
        _exam_start_adapter(self.player, {"target_rank": _T_EXAM_RANK})
        result = _exam_start_adapter(self.player, {"target_rank": _T_EXAM_RANK})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "active_combat")


class ServiceDispatchTests(ServiceActionBase):
    def setUp(self):
        super().setUp()
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()
        self.session = SimpleNamespace(
            puppet=self.player,
            sent=[],
            ndb=SimpleNamespace(),
            sessid=1,
        )
        self.session.msg = lambda **kwargs: self.session.sent.append(kwargs)

    def _coordinator(self):
        coordinator = attach_coordinator(self.session, self.registry)
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        return coordinator

    def _envelope(self, coordinator, action_id, payload, request_id="r1", base_revision=None):
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision if base_revision is None else base_revision,
            "action_id": action_id,
            "payload": payload,
        }

    def _last_result(self):
        results = [call for call in self.session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    def _latest_message(self):
        return self.session.sent[-1]

    @covers_requirement("webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_revision_returns_stale_and_calls_no_adapter(self):
        self._register()
        coordinator = self._coordinator()
        coordinator.panel_update(
            PresentationContext(actor=self.player, protocol_version=1),
            {"status": self.registry.render("status", PresentationContext(actor=self.player, protocol_version=1))},
        )
        with patch(
            "web.webclient.actions.service_actions._guild_register_adapter"
        ) as adapter_mock:
            handle_ui_action(
                self.session,
                self.player,
                self._envelope(
                    coordinator,
                    "guild.register",
                    {},
                    base_revision=coordinator.revision - 1,
                ),
                self.action_registry,
                self.registry,
            )
        result = self._last_result()
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(result["code"], "stale")
        adapter_mock.assert_not_called()

    def test_duplicate_request_replays_cached_result_once(self):
        self._register()
        coordinator = self._coordinator()
        with patch(
            "web.webclient.actions.service_actions.register_adventurer"
        ) as register_mock:
            register_mock.return_value = _registration()
            handle_ui_action(
                self.session,
                self.player,
                self._envelope(coordinator, "guild.register", {}, request_id="dup1"),
                self.action_registry,
                self.registry,
            )
            handle_ui_action(
                self.session,
                self.player,
                self._envelope(coordinator, "guild.register", {}, request_id="dup1"),
                self.action_registry,
                self.registry,
            )
        self.assertEqual(register_mock.call_count, 1)

    @covers_requirement("webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_host_disappearance_between_render_and_submit(self):
        self._register()
        self.player.location = self.store
        coordinator = self._coordinator()
        self.player.location = self.hall
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(coordinator, "shop.buy", {"item_key": _T_MEAL, "quantity": 1}),
            self.action_registry,
            self.registry,
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_merchant")
        self.assertEqual(self.player.db.wallet, 1000)
        self.assertEqual(list(self.player.db.inventory or []), [])

    @covers_requirement("webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_commit_time_stock_revalidation(self):
        self._register()
        self.player.location = self.store
        coordinator = self._coordinator()
        # Stock was 3 for the potion at render; another buyer depletes it.
        self.merchant.merchant_stock = {
            _T_MEAL: 20,
            _T_POTION: 0,
            _T_SWORD: 1,
        }
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator, "shop.buy", {"item_key": _T_POTION, "quantity": 1}
            ),
            self.action_registry,
            self.registry,
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_stock")
        self.assertEqual(self.player.db.wallet, 1000)
        self.assertEqual(list(self.player.db.inventory or []), [])

    @covers_requirement("webclient-service-menus::service-action-completion-updates-canonical-panels-and-preserves-narrative")
    def test_rejected_action_publishes_a_refresh_snapshot(self):
        self._register()
        self.player.location = self.store
        self.player.db.wallet = 5
        coordinator = self._coordinator()
        before = coordinator.revision
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(coordinator, "shop.buy", {"item_key": _T_MEAL, "quantity": 1}),
            self.action_registry,
            self.registry,
        )
        # A rejected outcome publishes a full snapshot at a newer revision.
        self.assertGreater(coordinator.revision, before)
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_funds")
        self.assertEqual(result["presentation_revision"], coordinator.revision)

    @covers_requirement(
        "webclient-objectives-panel::objectives-presentation-stays-current-across-quest-and-tracking-seams",
        "webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative",
    )
    def test_track_action_publishes_services_and_objectives_together(self):
        self._register()
        record = accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
        coordinator = self._coordinator()

        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "guild.quest_track",
                {"quest_id": record.quest_id, "tracked": True},
            ),
            self.action_registry,
            self.registry,
        )

        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "tracked")

        # An affected-panel ui_update was emitted
        updates = [call for call in self.session.sent if "ui_update" in call]
        self.assertTrue(updates)
        last_panels = updates[-1]["ui_update"][0][0]["panels"]
        self.assertIn("services", last_panels)
        self.assertIn("objectives", last_panels)

        # Services row carries tracked: True
        guild_quests = last_panels["services"]["guild"]["quests"]
        self.assertEqual(len(guild_quests), 1)
        self.assertTrue(guild_quests[0]["tracked"])

        # Objectives panel carries the tracked row
        obj_rows = last_panels["objectives"]["rows"]
        self.assertEqual(len(obj_rows), 1)
        self.assertEqual(obj_rows[0]["quest_id"], record.quest_id)

    @covers_requirement(
        "webclient-quest-log-panel::the-panel-is-pushed-on-every-quest-log-mutation"
    )
    def test_track_action_publishes_the_quest_log_panel(self):
        self._register()
        record = accept_guild_offer(self.player, self.staff, _T_BOARD_QUEST)
        coordinator = self._coordinator()

        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "guild.quest_track",
                {"quest_id": record.quest_id, "tracked": True},
            ),
            self.action_registry,
            self.registry,
        )

        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        updates = [call for call in self.session.sent if "ui_update" in call]
        self.assertTrue(updates)
        last_panels = updates[-1]["ui_update"][0][0]["panels"]
        self.assertIn("quest_log", last_panels)
        rows = last_panels["quest_log"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quest_id"], record.quest_id)
        self.assertTrue(rows[0]["tracked"])
        self.assertEqual(rows[0]["issuer"]["kind"], "guild")
        self.assertEqual(rows[0]["issuer"]["key"], f"guild:{BRANCH}")
