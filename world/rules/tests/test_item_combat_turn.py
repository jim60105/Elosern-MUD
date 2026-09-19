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
from typeclasses.npcs import NPC
from world.lore.items import ItemUseMechanics
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
)
from world.rules.action import ActionRequest
from world.rules.clock import WorldClock
from world.rules.combat import (
    Battlefield,
    ItemUseRequest,
)
from world.rules.combat_session import (
    engage,
    engage_group,
    read_session,
    submit_player_item_use,
    submit_opening_action,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.equipment import (
    materialize_registry_object,
    registry_key_for_object,
)
from world.rules.items import ItemUseReason, ItemUseResult
from world.rules.overwhelm import compress_event_logs, resolve_overwhelm
from world.rules.buffs import apply_buff, entity_active_buffs
from world.rules.party import join_party
from world.rules.tests.combat_fixtures import BattlefieldIsolation, FakeEntity

from world.tests.synthetic_data import SYNTH_ITEMS, make_item

from ._combat_session_helpers import (
    _race_key,
    _monster,
    _player,
    live_item_effect_profiles,
    live_item_registry,
    open_synthetic_scope,
)

_TONIC_KEY = "t_ember_spray"  # kit SELF_HEAL consumable, combat-allowed
_FANG_KEY = "t_iron_fang"  # kit weapon: registered, not usable
_MANA_KEY = "t_mist_vial"
_ATTACK_SKILL_KEY = "t_ember_burst"  # flows through mocked resolvers only
_PEACE_KEY = "t_calm_balm"

_PEACE_ITEM = make_item(
    _PEACE_KEY,
    display_name_zh="合成靜心香膏",
    price_table_key="t_mossmeals",
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=False),
)
_PEACE_PROFILE = ItemEffectProfile(
    effects=(GaugeAdjustEffect(stat=ItemStat.HP, amount=20),)
)

_MANA_VIAL = make_item(
    _MANA_KEY,
    display_name_zh="合成法力藥劑",
    price_table_key="t_mossmeals",
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=True),
)

# The rulebook-side half of the scoped row (settlement resolves by item key).
_MANA_VIAL_PROFILE = ItemEffectProfile(
    effects=(GaugeAdjustEffect(stat=ItemStat.MP, amount=40),)
)


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
                    "consumable": True,
                    "stat": "hp",
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
        _ATTACK_SKILL_KEY,
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
        open_synthetic_scope(
            self,
            "items",
            extra={
                "items": {_MANA_KEY: _MANA_VIAL, _PEACE_KEY: _PEACE_ITEM},
                "item_effect_profiles": {
                    _MANA_KEY: _MANA_VIAL_PROFILE,
                    _PEACE_KEY: _PEACE_PROFILE,
                },
            },
        )
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
        self.player.db.inventory = [_TONIC_KEY, _TONIC_KEY]
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat_session.settlement.get_world_clock", return_value=clock),
        ):
            result = submit_player_item_use(self.player, _TONIC_KEY)
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
                "item_key": _TONIC_KEY,
                "consumable": True,
                "stat": "hp",
                "amount": 20,
            },
        )
        self.assertEqual(
            self.player.db.inventory.count(_TONIC_KEY), 1
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
        self.player.db.inventory = [_TONIC_KEY, _MANA_KEY]
        clock = WorldClock()
        cases = (
            (_TONIC_KEY, "hp_full"),
            (_MANA_KEY, "mp_full"),
            ("mystery_key", "unknown_item"),
            (_FANG_KEY, "not_usable"),
        )
        for item_key, reason in cases:
            with self.subTest(item_key=item_key):
                with patch(
                    "world.rules.combat_session.settlement.get_world_clock",
                    return_value=clock,
                ):
                    result = submit_player_item_use(self.player, item_key)
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["reason"], reason)
                self.assertEqual(read_session(self.player).rounds_elapsed, 0)
                self.assertEqual(
                    self.player.db.inventory, [_TONIC_KEY, _MANA_KEY]
                )
                self.assertEqual(int(self.player.traits.hp.current), maximum)
        self.assertEqual(clock.tick, 0)

    @covers_requirement(
        "lore-item-catalog::an-item-barred-from-combat-is-refused-at-submission"
    )
    def test_combat_barred_item_refused_at_combat_submission(self):
        engage(self.player, self.monster)
        self._hurt(20)
        hp_before = int(self.player.traits.hp.current)
        self.player.db.inventory = [_PEACE_KEY]
        clock = WorldClock()
        with patch(
            "world.rules.combat_session.settlement.get_world_clock",
            return_value=clock,
        ):
            result = submit_player_item_use(self.player, _PEACE_KEY)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], "combat_not_allowed")
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(self.player.db.inventory, [_PEACE_KEY])
        self.assertEqual(int(self.player.traits.hp.current), hp_before)
        self.assertEqual(clock.tick, 0)

    def test_unheld_item_rejects_before_initiative(self):
        engage(self.player, self.monster)
        self._hurt(20)
        self.player.db.inventory = ["meal"]
        result = submit_player_item_use(self.player, _TONIC_KEY)
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
        self.player.db.inventory = [_TONIC_KEY]
        engage(self.player, self.monster)
        _persist(
            self.player,
            replace(read_session(self.player), knocked_out_ids=(self.player.pk,)),
        )
        result = submit_player_item_use(self.player, _TONIC_KEY)
        # A player already knocked out settles as defeat; the skipped turn
        # must still leave the potion untouched and emit no item-use event.
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(
            self.player.db.inventory.count(_TONIC_KEY), 1
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
        self.player.db.inventory = [_TONIC_KEY]
        engage(self.player, self.monster)
        rejected = ItemUseResult(
            outcome="rejected", reason=ItemUseReason.UNKNOWN_EFFECT
        )
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch(
                "world.rules.combat.resolve_item_use", return_value=rejected
            ),
        ):
            result = submit_player_item_use(self.player, _TONIC_KEY)
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(self.player.db.inventory.count(_TONIC_KEY), 1)
        self.assertEqual(
            int(self.player.traits.hp.current), int(self.player.traits.hp.max) - 20
        )

    @covers_requirement(
        "player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome"
    )
    def test_foe_overwhelming_verdict_keeps_per_round_item_agency(self):
        self._hurt(20)
        self.player.db.inventory = [_TONIC_KEY, _TONIC_KEY]
        engage(self.player, self.monster)
        foe_team = "foes"
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch(
                "world.rules.combat_session.rounds.classify_overwhelm",
                return_value=foe_team,
            ),
        ):
            result = submit_player_item_use(self.player, _TONIC_KEY)
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(self.player.db.inventory.count(_TONIC_KEY), 1)
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
        "player-combat-session::one-submission-inside-an-active-session-is-one-ordinary-round-by-default-and-structurally"
    )
    def test_player_overwhelming_verdict_item_use_never_compresses(self):
        # combat-session-opening-dispatch 5.2: an item submission under a
        # PLAYER-direction verdict also resolves exactly one ordinary round;
        # items lost the compression branch outright (D-5), so the resolver
        # must never be reached.
        self._hurt(20)
        self.player.db.inventory = [_TONIC_KEY, _TONIC_KEY]
        engage(self.player, self.monster)
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch(
                "world.rules.combat_session.rounds.classify_overwhelm",
                return_value="party",
            ),
            patch(
                "world.rules.combat_session.rounds.resolve_overwhelm",
                side_effect=AssertionError(
                    "an item submission must never dispatch compression"
                ),
            ) as resolver,
        ):
            result = submit_player_item_use(self.player, _TONIC_KEY)
        resolver.assert_not_called()
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(self.player.db.inventory.count(_TONIC_KEY), 1)

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_outer_rollback_restores_the_deleted_mirror_and_surfaces(self):
        self._hurt(20)
        self.player.db.inventory = [_TONIC_KEY]
        materialize_registry_object(self.player, _TONIC_KEY)
        mirror_pk = next(
            obj.id
            for obj in self.player.contents
            if registry_key_for_object(obj) == _TONIC_KEY
        )
        hp_before = int(self.player.traits.hp.current)
        engage(self.player, self.monster)

        def boom(*args, **kwargs):
            raise RuntimeError("persist boom")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat_session.rounds._persist", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_item_use(self.player, _TONIC_KEY)
        self.assertEqual(
            self.player.db.inventory.count(_TONIC_KEY), 1
        )
        self.assertEqual(int(self.player.traits.hp.current), hp_before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        self.assertIn(
            mirror_pk,
            [
                obj.id
                for obj in self.player.contents
                if registry_key_for_object(obj) == _TONIC_KEY
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
        self.player.db.inventory = [_TONIC_KEY]
        materialize_registry_object(self.player, _TONIC_KEY)
        mirror_pk = next(
            obj.id
            for obj in self.player.contents
            if registry_key_for_object(obj) == _TONIC_KEY
        )
        hp_before = int(self.player.traits.hp.current)
        engage(self.player, self.monster)

        def boom(*args, **kwargs):
            raise RuntimeError("upkeep boom")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat._end_of_round_upkeep", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_item_use(self.player, _TONIC_KEY)
        self.assertEqual(self.player.db.inventory.count(_TONIC_KEY), 1)
        self.assertEqual(int(self.player.traits.hp.current), hp_before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        self.assertIn(
            mirror_pk,
            [
                obj.id
                for obj in self.player.contents
                if registry_key_for_object(obj) == _TONIC_KEY
            ],
        )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_terminal_settlement_failure_after_item_use_restores_everything(self):
        self._hurt(20)
        self.player.db.inventory = [_TONIC_KEY]
        materialize_registry_object(self.player, _TONIC_KEY)
        mirror_pk = next(
            obj.id
            for obj in self.player.contents
            if registry_key_for_object(obj) == _TONIC_KEY
        )
        hp_before = int(self.player.traits.hp.current)
        engage(self.player, self.monster)

        def boom(*args, **kwargs):
            raise RuntimeError("settlement boom")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat_session.rounds._continue_or_settle", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_item_use(self.player, _TONIC_KEY)
        self.assertEqual(self.player.db.inventory.count(_TONIC_KEY), 1)
        self.assertEqual(int(self.player.traits.hp.current), hp_before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        self.assertIn(
            mirror_pk,
            [
                obj.id
                for obj in self.player.contents
                if registry_key_for_object(obj) == _TONIC_KEY
            ],
        )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)


class SessionItemMultiTargetRollbackTests(BattlefieldIsolation, EvenniaTest):
    """Design 5.8: the per-target journal rolls back every touched entity."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "items",
            extra={
                "items": {_MANA_KEY: _MANA_VIAL},
                "item_effect_profiles": {_MANA_KEY: _MANA_VIAL_PROFILE},
            },
        )
        self.room = create_object(Room, key="multi item arena")
        self.player = _player("multi duelist")
        self.player.location = self.room
        self.player.db.inventory = []
        self.player.db.equipment = None
        self.companion = create_object(NPC, key="multi companion")
        self.companion.race = _race_key()
        self.companion.apply_race_baseline()
        self.companion.location = self.room
        join_party(self.companion, self.player)
        self.monster = _monster("troll", hp=10000, atk=0)
        self.monster.location = self.room
        # ALL-scoped profile: one HP+40 step and one pleasure+30 step per
        # present entity. The actor sits at full HP (its HP step is
        # ineffective and skipped); the companion is hurt so its HP step
        # lands, and its pleasure sits mid-band so its pleasure step lands
        # through the memoized handler.
        live_item_effect_profiles()[_MANA_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.ALL
                ),
                GaugeAdjustEffect(
                    stat=ItemStat.PLEASURE, amount=30, scope=ItemTargetScope.ALL
                ),
            )
        )

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_upkeep_fault_restores_actor_and_companion_surfaces(self):
        # The shipped injection pattern (patch a post-settlement seam inside
        # the round with RuntimeError) extended across every target surface:
        # the ALL-scoped use writes traits, buffs, and the sexual handler of
        # both the actor and the companion, deletes the actor's mirror, and
        # then an injected upkeep fault must walk every captured entity back.
        self.player.traits.hp.current = int(self.player.traits.hp.max)
        self.companion.traits.hp.current = 50
        self.companion.sexual.pleasure.base = 10
        apply_buff(self.player, "poisoned")
        apply_buff(self.companion, "poisoned")
        self.player.db.inventory = [_MANA_KEY]
        materialize_registry_object(self.player, _MANA_KEY)
        mirror_pk = next(
            obj.id
            for obj in self.player.contents
            if registry_key_for_object(obj) == _MANA_KEY
        )
        engage(self.player, self.monster)
        # Touch the companion's handler pre-use so its in-process cache is
        # live across the settlement: a restore that skipped the per-target
        # cache drop would roll back stored sexual state while a stale
        # companion.sexual handler still reported the rolled-back gain.
        self.assertEqual(int(self.companion.sexual.pleasure.base), 10)
        companion_hp_before = int(self.companion.traits.hp.current)

        def boom(*args, **kwargs):
            raise RuntimeError("upkeep boom")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat._end_of_round_upkeep", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_item_use(self.player, _MANA_KEY)
        # Actor surfaces: inventory unit, buffs, deleted mirror instance.
        self.assertEqual(self.player.db.inventory.count(_MANA_KEY), 1)
        self.assertEqual(entity_active_buffs(self.player), {"poisoned"})
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        self.assertIn(
            mirror_pk,
            [
                obj.id
                for obj in self.player.contents
                if registry_key_for_object(obj) == _MANA_KEY
            ],
        )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        # Companion surfaces: traits, buffs, and the sexual state restored
        # through a live handler re-read (the per-target cache drop).
        self.assertEqual(
            int(self.companion.traits.hp.current), companion_hp_before
        )
        self.assertEqual(entity_active_buffs(self.companion), {"poisoned"})
        self.assertEqual(int(self.companion.sexual.pleasure.base), 10)

    @covers_requirement(
        "item-use-resolution::combat-item-use-occupies-one-initiative-ordered-round"
    )
    def test_four_target_item_still_consumes_exactly_one_round(self):
        # Delta: "A four-target item still consumes one round" — player,
        # companion, and two foes all take the ALL-scoped step within one
        # initiative position; the round count moves by one and the clock
        # gains no separate item-use time.
        from world.rules.clock import WorldClock

        live_item_effect_profiles()[_MANA_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.ALL
                ),
            )
        )
        second = _monster("cave bear", hp=100, atk=0)
        second.location = self.room
        self.player.traits.hp.current = int(self.player.traits.hp.max) - 30
        self.companion.traits.hp.current = int(self.companion.traits.hp.max) - 50
        self.monster.traits.hp.current = 60
        second.traits.hp.current = 60
        self.player.db.inventory = [_MANA_KEY, _MANA_KEY]
        engage_group(self.player, [self.monster, second])
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat_session.settlement.get_world_clock", return_value=clock),
            # The troll sits below its archetype's flee boundary and acts
            # before the player, so its turn always attempts to flee; pin the
            # disengage seam to a failing roll (1 + agility < 51 + pursuer) so
            # the ALL scope stays four-targeted regardless of shard order.
            patch("world.rules.disengage.roll_d100", return_value=1),
        ):
            result = submit_player_item_use(self.player, _MANA_KEY)
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(clock.tick, 0)
        item_entries = [
            entry
            for log in result["logs"]
            for entry in log.entries
            if entry.kind == "item_used"
        ]
        self.assertEqual(
            sorted(entry.target for entry in item_entries),
            sorted(
                [
                    self.player.key,
                    self.companion.key,
                    self.monster.key,
                    second.key,
                ]
            ),
        )
        # Consumption never scales with target count: two carried, one left.
        self.assertEqual(self.player.db.inventory.count(_MANA_KEY), 1)
        self.assertEqual(int(self.player.traits.hp.current), int(self.player.traits.hp.max))
        self.assertEqual(
            int(self.companion.traits.hp.current),
            int(self.companion.traits.hp.max) - 10,
        )
        self.assertEqual(int(self.monster.traits.hp.current), 100)
        self.assertEqual(int(second.traits.hp.current), 100)


class CompressedItemTurnTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "items")
        attacker = FakeEntity(
            "elf",
            hp=10000,
            max_hp=10000,
            atk_phys=88,
            agility=92,
            defense=90,
            magic_power=250,
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

        def item_resolver(request, *, in_combat, context):
            item_calls.append((request, context))
            return ItemUseResult(
                outcome="success",
                event_log=_item_used_log("elf", _TONIC_KEY),
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
                return ItemUseRequest(actor=entity, item_key=_TONIC_KEY)
            return ActionRequest(
                actor=entity,
                skill_key=_ATTACK_SKILL_KEY,
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
                commanded_action_key=_TONIC_KEY,
                journal_sink=journals,
            )

        self.assertEqual(result.rounds_elapsed, 2)
        self.assertTrue(result.battle_over)
        self.assertEqual(len(item_calls), 1)
        request, supplied_context = item_calls[0]
        self.assertTrue(request.actor.key, "elf")
        # Task 5.1: the round's item branch supplies the battlefield as the
        # action context, so single and group scopes resolve through the
        # same roster validators a skill's targets pass.
        self.assertIs(supplied_context.battlefield, self.field)
        self.assertEqual(len(resolver_calls), 1)
        self.assertEqual(resolver_calls[0].skill_key, _ATTACK_SKILL_KEY)
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
            {"item": live_item_registry()[_TONIC_KEY].display_name_zh},
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
                _TONIC_KEY,
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
            commanded_action_key=_TONIC_KEY,
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
