"""Ledger lifecycle suite for ``world/rules/church.py`` (the sole writer).

Pins the ``db.church`` contract of the ``church-ordination`` delta: lazy
creation by the first church-rules write, persistence, the clock-day reset of
the ``daily`` counters (the ``climax_today`` pattern), the single-writer
boundary (no command/typeclass/AI/presentation module assigns ``db.church``),
and merit's non-currency property (no wallet path accepts it — a merit-rich
zero-wallet character is still refused at the shop counter, and church
primitives never touch ``db.wallet``).
"""

from tools.spec_traceability import covers_requirement

from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules import church
from world.rules.church import ChurchLedgerError, build_initial_arousal_baseline
from world.rules.clock import CLOCK_YAML, WorldClock
from world.rules.economy import TradeError, TradeReason, buy
from world.rules.wallet import read_wallet
from world.lore.sexual_vocab import AROUSAL_LEVELS

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]

REPO_ROOT = Path(__file__).resolve().parents[3]


def _clock(tick: int) -> WorldClock:
    return WorldClock(tick)


class ChurchLedgerLifecycleTests(EvenniaTestCase):
    """Lazy creation, reads, writes, and day-boundary reset."""

    def _operator(self):
        char = create_object(PlayerCharacter, key="t_ledger_operator")
        char.race = "human"
        char.apply_race_baseline()
        return char

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_lazy_creation_materializes_no_ledger_before_the_first_write(self):
        char = self._operator()
        self.assertIsNone(getattr(char.db, "church", None))
        self.assertEqual(church.merit(char), 0)
        self.assertEqual(church.enrolled_tick(char), 0)
        self.assertEqual(church.redeemed_keys(char), ())
        self.assertIsNone(church.daily(char))
        self.assertIsNone(getattr(char.db, "church", None))
        # The first church-rules write materializes the full ledger shape.
        with patch("world.rules.church.read_world_clock", return_value=_clock(0)):
            church.add_merit(char, 5)
        ledger = church.read_ledger(char)
        self.assertEqual(
            ledger,
            {
                "merit": 5,
                "enrolled_tick": 0,
                "redeemed": [],
                "blessing_last_tick": None,
                "daily": {"day": 0, "pray": 0},
            },
        )

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_the_ledger_is_per_character_and_survives_a_store_load_cycle(self):
        char = self._operator()
        other = self._operator()
        with patch("world.rules.church.read_world_clock", return_value=_clock(0)):
            church.add_merit(char, 10)
        self.assertIsNone(getattr(other.db, "church", None))
        self.assertEqual(church.merit(other), 0)
        # A re-fetch sees the committed attribute value, not a local copy.
        reloaded = PlayerCharacter.objects.get(pk=char.pk)
        self.assertEqual(church.merit(reloaded), 10)

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_merit_accrual_and_redemption_primitives_are_the_sanctioned_writes(self):
        char = self._operator()
        with patch("world.rules.church.read_world_clock", return_value=_clock(0)):
            church.add_merit(char, 40)
            church.add_merit(char, 10)
            self.assertEqual(church.merit(char), 50)
            self.assertEqual(church.subtract_merit(char, 15), 35)
        with self.assertRaisesRegex(ChurchLedgerError, "insufficient"):
            church.subtract_merit(char, 100)
        self.assertEqual(church.merit(char), 35)
        for bad in (True, -1, 1.5, "5"):
            with self.subTest(delta=bad), self.assertRaises(ChurchLedgerError):
                church.add_merit(char, bad)

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_redemption_records_are_append_only_and_one_shot(self):
        char = self._operator()
        with patch("world.rules.church.read_world_clock", return_value=_clock(0)):
            church.record_redemption(char, "t_redeemed_skill")
            self.assertEqual(church.redeemed_keys(char), ("t_redeemed_skill",))
            with self.assertRaisesRegex(ChurchLedgerError, "already redeemed"):
                church.record_redemption(char, "t_redeemed_skill")
            self.assertEqual(church.redeemed_keys(char), ("t_redeemed_skill",))

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_daily_counters_reset_across_a_clock_day_boundary(self):
        char = self._operator()
        char.db.church = {
            "merit": 30,
            "enrolled_tick": 0,
            "redeemed": [],
            "daily": {"day": 0, "pray": 2},
        }
        # Same day: no reset, counters preserved.
        with patch("world.rules.church.read_world_clock", return_value=_clock(5)):
            church.ensure_daily_reset(char)
        self.assertEqual(church.daily(char), {"day": 0, "pray": 2})
        # Next day: counters zero and the new day stamped; merit preserved.
        with patch(
            "world.rules.church.read_world_clock",
            return_value=_clock(3 * _DAY_SECONDS + 5),
        ):
            church.ensure_daily_reset(char)
        self.assertEqual(church.daily(char), {"day": 3, "pray": 0})
        self.assertEqual(church.merit(char), 30)
        # A character who never touched the church is untouched by the reset.
        fresh = self._operator()
        church.ensure_daily_reset(fresh)
        self.assertIsNone(getattr(fresh.db, "church", None))

    def test_initial_arousal_baseline_validates_the_vocabulary(self):
        raised = AROUSAL_LEVELS[1]
        baseline = build_initial_arousal_baseline(raised)
        self.assertEqual(baseline["arousal"], raised)
        self.assertIs(baseline["virgin"], True)
        with self.assertRaises(ChurchLedgerError):
            build_initial_arousal_baseline("t_not_an_arousal_level")


class ChurchMeritWalletIsolationTests(EvenniaTest):
    """Merit is readable only by church rules — never money (delta scenario)."""

    def setUp(self):
        from world.rules.tests._combat_session_helpers import open_synthetic_scope
        from world.rules.tests._guild_service_probes import (
            install_synthetic_catalog,
            synth_catalog,
            synth_offer_rule,
            synth_shop_config,
        )
        from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS
        from world.quests.catalog import register_catalog

        # Scope before construction: the shop registries must resolve kit
        # rows while the catalog and trade-side lookups build.
        open_synthetic_scope(self, "items", "prices", "shops")
        super().setUp()
        register_catalog()
        shop_key = next(iter(SYNTH_SHOPS))
        item_key = SYNTH_ITEMS["t_huskapple"].key
        offer = synth_offer_rule(item_key, max_stock=20)
        install_synthetic_catalog(
            self,
            synth_catalog(shop_configs={shop_key: synth_shop_config(shop_key, (item_key,), offer_rules=(offer,))}),
        )
        self._shop_key = shop_key
        self._item_key = item_key
        self.store = create_object(Room, key="t_ledger_store")
        self.merchant_npc = create_object(NPC, key="t_ledger_keeper", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc, service_id="t_ledger_merchant", shop_key=shop_key
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {item_key: 20}
        self.player = self.char1
        self.player.db.wallet = 0
        self.player.location = self.store

    def _open_clock(self, hour=12):
        return WorldClock(hour * 3600)

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_merit_rich_zero_wallet_is_still_refused_at_the_counter(self):
        # The character holds substantial church merit but zero copper: the
        # shop counter sees only db.wallet and refuses with insufficient
        # funds, leaving wallet, ledger, stock, and inventory untouched.
        with patch("world.rules.church.read_world_clock", return_value=_clock(0)):
            church.add_merit(self.player, 5000)
        before = church.read_ledger(self.player)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as caught:
                buy(self.player, self.merchant_npc, self._item_key, 1)
        self.assertEqual(caught.exception.args[0], TradeReason.INSUFFICIENT_FUNDS)
        self.assertEqual(self.player.db.wallet, 0)
        self.assertEqual(church.read_ledger(self.player), before)
        self.assertEqual(self.merchant.merchant_stock, {self._item_key: 20})
        self.assertEqual(list(self.player.db.inventory or []), [])
        # The wallet reader ignores db.church entirely: the same wallet value
        # reads identically with or without a ledger in place.
        self.assertEqual(read_wallet(self.player, ValueError), 0)

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_church_primitives_never_touch_the_wallet(self):
        self.player.db.wallet = 77
        with patch("world.rules.church.read_world_clock", return_value=_clock(0)):
            church.add_merit(self.player, 10)
            church.subtract_merit(self.player, 4)
            church.record_redemption(self.player, "t_redeemed")
        self.assertIsNotNone(church.read_ledger(self.player))
        self.assertEqual(self.player.db.wallet, 77)


class ChurchSingleWriterAuditTests(EvenniaTestCase):
    """The grep-enforceable single-writer boundary over real sources."""

    @covers_requirement(
        "church-ordination::the-merit-ledger-is-persisted-character-state-with-a-single-writer"
    )
    def test_no_non_test_module_assigns_any_db_church_field(self):
        offenders: list[str] = []
        for prefix in ("commands", "server", "typeclasses", "world", "web"):
            for path in (REPO_ROOT / prefix).rglob("*.py"):
                rel = path.relative_to(REPO_ROOT).as_posix()
                if "/tests/" in rel or rel.startswith("web/webclient"):
                    continue
                if "db.church" in path.read_text(encoding="utf-8"):
                    offenders.append(rel)
        self.assertEqual(
            offenders,
            ["world/rules/church.py"],
            "db.church may only be written by the sole-writer module",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()