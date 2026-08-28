"""Combat item-turn tests: round occupancy, rejection purity, rollback, compression.

Covers the session-level ``submit_player_item_use`` facade (one ordinary
initiative-ordered round, stable ``item_used`` event, zero-cost rejection, and
the outer-rollback journal restoration over a deleted mirror) plus the
compressed overwhelm turn (potion on the first player turn, ``basic_attack``
afterwards, and exactly one item-kind commanded-action marker).
"""

from tools.spec_traceability import covers_requirement

from types import SimpleNamespace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.rooms import Room
from world.lore.items import ITEM_REGISTRY
from world.rules.action import ActionRequest
from world.rules.clock import WorldClock
from world.rules.combat import (
    Battlefield,
    ItemUseRequest,
)
from world.rules.combat_session import (
    engage,
    read_session,
    submit_player_item_use,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.equipment import (
    materialize_registry_object,
    registry_key_for_object,
)
from world.rules.items import ItemUseReason, ItemUseResult
from world.rules.overwhelm import compress_event_logs, resolve_overwhelm
from world.rules.tests.combat_fixtures import BattlefieldIsolation, FakeEntity

from ._combat_session_helpers import _monster, _player


def _item_used_log(actor_key: str, item_key: str) -> EventLog:
    return EventLog(
        actor_key,
        item_key,
        (actor_key,),
        (
            EventEntry(
                "item_used",
                actor_key,
                actor_key,
                {
                    "item_key": item_key,
                    "effect_key": "self_heal",
                    "consumable": True,
                    "amount": 40,
                },
                "你使用了測試物品。",
            ),
        ),
        6,
    )


def _attack_log(actor_key: str, target_key: str, amount: int) -> EventLog:
    return EventLog(
        actor_key,
        "basic_attack",
        (target_key,),
        (
            EventEntry(
                "damage",
                actor_key,
                target_key,
                {"amount": amount},
                "{actor} 對 {target} 造成 {data[amount]} 點傷害。",
            ),
        ),
        6,
    )


class SessionItemTurnTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="item arena")
        self.player = _player("item duelist")
        self.player.location = self.room
        self.player.db.inventory = []
        self.player.db.equipment = None
        self.monster = _monster("goblin", hp=100, atk=0)
        self.monster.location = self.room

    def _hurt(self, missing: int) -> int:
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum - missing
        return maximum

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_item_use_drives_one_ordinary_round(self):
        maximum = self._hurt(20)
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
            patch("world.rules.combat_session.get_world_clock", return_value=clock),
        ):
            result = submit_player_item_use(self.player, "healing_potion")
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        item_entries = [
            entry
            for log in result["logs"]
            for entry in log.entries
            if entry.kind == "item_used"
        ]
        self.assertEqual(len(item_entries), 1)
        self.assertEqual(
            item_entries[0].data,
            {
                "item_key": "healing_potion",
                "effect_key": "self_heal",
                "consumable": True,
                "amount": 20,
            },
        )
        self.assertEqual(
            self.player.db.inventory.count("healing_potion"), 1
        )
        self.assertEqual(int(self.player.traits.hp.current), maximum)
        self.assertEqual(clock.tick, 0)
        monster_actions = [
            log
            for log in result["logs"]
            if log.entries and log.actor == self.monster.key
        ]
        self.assertEqual(len(monster_actions), 1)

    @covers_requirement(
        "item-use-resolution::item-use-preflight-is-side-effect-free-and-revalidates-current-conditions"
    )
    def test_rejected_item_use_consumes_no_round_or_state(self):
        engage(self.player, self.monster)
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum
        self.player.db.inventory = ["healing_potion"]
        clock = WorldClock()
        cases = (
            ("healing_potion", "hp_full"),
            ("mystery_key", "unknown_item"),
            ("plain_sword", "not_usable"),
        )
        for item_key, reason in cases:
            with self.subTest(item_key=item_key):
                with patch(
                    "world.rules.combat_session.get_world_clock",
                    return_value=clock,
                ):
                    result = submit_player_item_use(self.player, item_key)
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["reason"], reason)
                self.assertEqual(read_session(self.player).rounds_elapsed, 0)
                self.assertEqual(
                    self.player.db.inventory, ["healing_potion"]
                )
                self.assertEqual(int(self.player.traits.hp.current), maximum)
        self.assertEqual(clock.tick, 0)

    def test_unheld_item_rejects_before_initiative(self):
        engage(self.player, self.monster)
        self._hurt(20)
        self.player.db.inventory = ["meal"]
        result = submit_player_item_use(self.player, "healing_potion")
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], "item_not_held")
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_knockout_before_item_turn_skips_the_request(self):
        from dataclasses import replace

        from world.rules.combat_session import _persist

        self._hurt(20)
        self.player.db.inventory = ["healing_potion"]
        engage(self.player, self.monster)
        _persist(
            self.player,
            replace(read_session(self.player), knocked_out_ids=(self.player.pk,)),
        )
        result = submit_player_item_use(self.player, "healing_potion")
        # A player already knocked out settles as defeat; the skipped turn
        # must still leave the potion untouched and emit no item-use event.
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(
            self.player.db.inventory.count("healing_potion"), 1
        )
        item_logs = [
            entry
            for log in result.get("logs", ())
            for entry in log.entries
            if entry.kind == "item_used"
        ]
        self.assertEqual(item_logs, [])

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_mid_round_invalidation_consumes_the_round_without_consuming_the_item(self):
        self._hurt(20)
        self.player.db.inventory = ["healing_potion"]
        engage(self.player, self.monster)
        rejected = ItemUseResult(
            outcome="rejected", reason=ItemUseReason.UNKNOWN_EFFECT
        )
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
            patch(
                "world.rules.combat.resolve_item_use", return_value=rejected
            ),
        ):
            result = submit_player_item_use(self.player, "healing_potion")
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(self.player.db.inventory.count("healing_potion"), 1)
        self.assertEqual(
            int(self.player.traits.hp.current), int(self.player.traits.hp.max) - 20
        )

    @covers_requirement(
        "player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome"
    )
    def test_foe_overwhelming_verdict_keeps_per_round_item_agency(self):
        self._hurt(20)
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        engage(self.player, self.monster)
        foe_team = "foes"
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
            patch(
                "world.rules.combat_session.classify_overwhelm",
                return_value=foe_team,
            ),
        ):
            result = submit_player_item_use(self.player, "healing_potion")
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(self.player.db.inventory.count("healing_potion"), 1)
        self.assertEqual(
            len(
                [
                    entry
                    for log in result["logs"]
                    for entry in log.entries
                    if entry.kind == ("commanded_action")
                ]
            ),
            0,
        )

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_outer_rollback_restores_the_deleted_mirror_and_surfaces(self):
        self._hurt(20)
        self.player.db.inventory = ["healing_potion"]
        materialize_registry_object(self.player, "healing_potion")
        mirror_pk = next(
            obj.id
            for obj in self.player.contents
            if registry_key_for_object(obj) == "healing_potion"
        )
        hp_before = int(self.player.traits.hp.current)
        engage(self.player, self.monster)

        def boom(*args, **kwargs):
            raise RuntimeError("persist boom")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
            patch("world.rules.combat_session._persist", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_item_use(self.player, "healing_potion")
        self.assertEqual(
            self.player.db.inventory.count("healing_potion"), 1
        )
        self.assertEqual(int(self.player.traits.hp.current), hp_before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        self.assertIn(
            mirror_pk,
            [
                obj.id
                for obj in self.player.contents
                if registry_key_for_object(obj) == "healing_potion"
            ],
        )
        self.assertIsNotNone(read_session(self.player))

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_upkeep_failure_after_item_use_restores_everything(self):
        # The item mirror is deleted and HP written before upkeep runs; an
        # upkeep fault must roll the whole round back through the item
        # journals (fix-combat-settlement-recovery D1 extended by
        # add-inventory-item-actions D2).
        self._hurt(20)
        self.player.db.inventory = ["healing_potion"]
        materialize_registry_object(self.player, "healing_potion")
        mirror_pk = next(
            obj.id
            for obj in self.player.contents
            if registry_key_for_object(obj) == "healing_potion"
        )
        hp_before = int(self.player.traits.hp.current)
        engage(self.player, self.monster)

        def boom(*args, **kwargs):
            raise RuntimeError("upkeep boom")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
            patch("world.rules.combat._end_of_round_upkeep", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_item_use(self.player, "healing_potion")
        self.assertEqual(self.player.db.inventory.count("healing_potion"), 1)
        self.assertEqual(int(self.player.traits.hp.current), hp_before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        self.assertIn(
            mirror_pk,
            [
                obj.id
                for obj in self.player.contents
                if registry_key_for_object(obj) == "healing_potion"
            ],
        )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_terminal_settlement_failure_after_item_use_restores_everything(self):
        self._hurt(20)
        self.player.db.inventory = ["healing_potion"]
        materialize_registry_object(self.player, "healing_potion")
        mirror_pk = next(
            obj.id
            for obj in self.player.contents
            if registry_key_for_object(obj) == "healing_potion"
        )
        hp_before = int(self.player.traits.hp.current)
        engage(self.player, self.monster)

        def boom(*args, **kwargs):
            raise RuntimeError("settlement boom")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
            patch("world.rules.combat_session._continue_or_settle", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_item_use(self.player, "healing_potion")
        self.assertEqual(self.player.db.inventory.count("healing_potion"), 1)
        self.assertEqual(int(self.player.traits.hp.current), hp_before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        self.assertIn(
            mirror_pk,
            [
                obj.id
                for obj in self.player.contents
                if registry_key_for_object(obj) == "healing_potion"
            ],
        )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)


class CompressedItemTurnTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        attacker = FakeEntity(
            "elf",
            hp=10000,
            max_hp=10000,
            atk_phys=88,
            agility=92,
            defense=90,
            magic_level=250,
        )
        defender = FakeEntity("human", hp=120, atk_phys=8, agility=9, defense=7)
        self.attacker = attacker
        self.defender = defender
        self.field = Battlefield(
            {"elves": frozenset({"elf"}), "humans": frozenset({"human"})},
            {"elf": attacker, "human": defender},
        )

    @covers_requirement(
        "player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome"
    )
    def test_potion_resolves_first_turn_and_marks_exactly_one_item_marker(self):
        sentinel = object()
        journals: list[object] = []
        item_calls: list[ItemUseRequest] = []
        resolver_calls: list[ActionRequest] = []

        def item_resolver(request, *, in_combat):
            item_calls.append(request)
            return ItemUseResult(
                outcome="success",
                event_log=_item_used_log("elf", "healing_potion"),
                journal=sentinel,
            )

        def action_resolver(request):
            resolver_calls.append(request)
            self.defender.traits.hp.current = 0
            return SimpleNamespace(
                outcome="success",
                event_log=_attack_log("elf", "human", 120),
            )

        used_item = {"done": False}

        def provider(entity, battlefield):
            if entity.key != "elf":
                return None
            if not used_item["done"]:
                used_item["done"] = True
                return ItemUseRequest(actor=entity, item_key="healing_potion")
            return ActionRequest(
                actor=entity,
                skill_key="basic_attack",
                targets=[self.defender],
                context=None,
            )

        with (
            patch(
                "world.rules.overwhelm.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
            patch("world.rules.combat.roll_initiative", return_value=["elf"]),
            patch("world.rules.combat.resolve_item_use", side_effect=item_resolver),
            patch(
                "world.rules.combat.ActionResolver.resolve",
                side_effect=action_resolver,
            ),
            patch("world.rules.combat._end_of_round_upkeep", return_value={}),
            patch("world.rules.combat.settle_upkeep", return_value=[]),
        ):
            result = resolve_overwhelm(
                self.field,
                provider,
                max_rounds=12,
                commanded_actor="elf",
                commanded_action_kind="item",
                commanded_action_key="healing_potion",
                journal_sink=journals,
            )

        self.assertEqual(result.rounds_elapsed, 2)
        self.assertTrue(result.battle_over)
        self.assertEqual(len(item_calls), 1)
        self.assertTrue(item_calls[0].actor.key, "elf")
        self.assertEqual(len(resolver_calls), 1)
        self.assertEqual(resolver_calls[0].skill_key, "basic_attack")
        self.assertEqual(journals, [sentinel])
        markers = [
            entry
            for log in result.event_logs
            for entry in log.entries
            if entry.kind == "commanded_action"
        ]
        self.assertEqual(len(markers), 1)
        self.assertEqual(
            markers[0].data,
            {"item": ITEM_REGISTRY["healing_potion"].display_name_zh},
        )
        item_entries = [
            entry
            for log in result.event_logs
            for entry in log.entries
            if entry.kind == "item_used"
        ]
        self.assertEqual(len(item_entries), 1)

    def test_item_kind_marker_requires_an_item_used_entry(self):
        logs = (            EventLog(
                "elf",
                "healing_potion",
                ("elf",),
                (
                    EventEntry(
                        "damage",
                        "elf",
                        "elf",
                        {"amount": 1},
                        "{actor} 造成 {data[amount]} 點傷害。",
                    ),
                ),
                6,
            ),
        )

        marked = compress_event_logs(
            logs,
            "elves",
            "humans",
            1,
            commanded_actor="elf",
            commanded_action_kind="item",
            commanded_action_key="healing_potion",
            commanded_window=logs,
        )
        self.assertEqual(
            [
                entry.kind
                for log in marked
                for entry in log.entries
                if entry.kind == "commanded_action"
            ],
            [],
        )
