"""Automatic-settlement tests (change ``quest-auto-settlement``).

Covers the pure planner (task 2.x), the three write-path commits (task 3.x),
the ``quest_auto_settlement`` boundary event (task 4.1), rollback, cross-mode
ledger sharing, and the merit-free/no-host isolation rules (task 5.x). The
DEFEAT integration drives the real ``ActionResolver`` so the payout is proven
to commit atomically with the originating combat action.

``covers_requirement`` annotations for this change's own ``quest-auto-settlement``
requirements are intentionally withheld while the change is an active delta:
``tools.spec_traceability`` rejects unknown IDs, and the requirement IDs become
canonical only when the change archives and syncs into ``openspec/specs/``
(the same convention batches 1-4 followed). The cross-mode tests annotate the
already-canonical modified ``quest-reward-settlement`` requirement now.
Establishing tests for all four requirements carry their annotations as of the
archive-and-sync of this change.
"""

from dataclasses import replace
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.definitions import QUEST_DEFINITION_REGISTRY, QuestStage
from world.quests.runtime import (
    QuestState,
    accept_quest,
    fulfill_record,
    read_records,
    to_storage,
)
from world.quests.settlement import just_completed_records, plan_auto_settlement
from world.quests.transitions import (
    apply_quest_log_delta,
    apply_quest_log_replacement,
)

from tools.spec_traceability import covers_requirement
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    register_event_effect_planner,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.guild import (
    RewardClaim,
    RewardClaimError,
    parse_reward_claims,
    register_adventurer,
    turn_in_quest,
)
from world.rules.guild_offers import (
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.rules.quest_issuance import guild_issuer_key, npc_issuer_key
from world.rules.surfaces import attribute_snapshot, read_counter_trait
from world.rules.tests.combat_fixtures import grant_lineage
from world.quests.planner import quest_event_effect_planner

from ._fixtures import (
    AUTO_ISSUER_KEY,
    QuestRegistryIsolation,
    RegistryIsolationMixin,
    accept,
    accept_auto,
    acquire,
    defeat,
    quest,
    register,
)

ALTORIA_BRANCH = "guild_branch_altoria"


def _attach_staff(npc) -> None:
    npc.components.add(
        GuildStaff.create(npc, service_id="staff", branch_key=ALTORIA_BRANCH)
    )


def _offer(
    definition_key: str,
    copper: int = 50,
    merit: int = 0,
    items: tuple[str, ...] = (),
) -> GuildQuestOffer:
    return GuildQuestOffer(
        definition_key=definition_key,
        issuer_branch_key=ALTORIA_BRANCH,
        reward=QuestReward(
            copper=copper,
            items=tuple(ItemQuantity(key, 1) for key in items),
            merit=merit,
        ),
    )


def _wallet(actor) -> int:
    return int(actor.db.wallet or 0)


class AutoSettlementPlannerTests(QuestRegistryIsolation, EvenniaTest):
    """Task 5.1: the pure planner's contribution rules and no-write rule."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.definition = register(quest("auto_plan"))
        self.record = accept_auto(self.actor, self.definition)

    def _completed(self):
        return fulfill_record(self.record, self.definition)

    @covers_requirement("quest-auto-settlement::automatic-settlement-is-planned-by-a-pure-function")
    def test_auto_commission_contributes_registered_reward(self):
        plan = plan_auto_settlement(self.actor, [self._completed()])
        (entry,) = plan.entries
        self.assertEqual(entry.quest_id, self.record.quest_id)
        self.assertEqual(entry.issuer_key, AUTO_ISSUER_KEY)
        self.assertEqual(entry.copper, 25)
        self.assertEqual(entry.items, ())
        self.assertEqual(plan.claim_ids, (self.record.quest_id,))
        self.assertEqual(plan.wallet_delta, 25)

    def test_item_rewards_expand_repeated_keys(self):
        itemised = register(quest("auto_plan_items"))
        record = accept_auto(
            self.actor,
            itemised,
            reward=QuestReward(
                copper=5, items=(ItemQuantity("healing_potion", 2),), merit=0
            ),
        )
        completed = fulfill_record(record, QUEST_DEFINITION_REGISTRY[itemised.key])
        plan = plan_auto_settlement(self.actor, [completed])
        (entry,) = plan.entries
        self.assertEqual(entry.items, ("healing_potion", "healing_potion"))

    @covers_requirement("quest-auto-settlement::automatic-settlement-is-planned-by-a-pure-function")
    def test_counter_commission_contributes_nothing(self):
        counter = register(quest("counter_plan"))
        record = accept(self.actor, counter)
        completed = fulfill_record(record, QUEST_DEFINITION_REGISTRY[counter.key])
        self.assertEqual(plan_auto_settlement(self.actor, [completed]).entries, ())

    @covers_requirement("quest-auto-settlement::automatic-settlement-is-planned-by-a-pure-function")
    def test_already_claimed_contributes_nothing(self):
        self.actor.db.guild_reward_claims = [self.record.quest_id]
        self.assertEqual(plan_auto_settlement(self.actor, [self._completed()]).entries, ())

    @covers_requirement("quest-auto-settlement::automatic-settlement-is-planned-by-a-pure-function")
    def test_unresolvable_issuance_contributes_nothing_without_raising(self):
        ghost = replace(
            self.record, issuer_key=npc_issuer_key(content_key="ghost_issuer")
        )
        completed = fulfill_record(ghost, self.definition)
        self.assertEqual(plan_auto_settlement(self.actor, [completed]).entries, ())

    @covers_requirement("quest-auto-settlement::automatic-settlement-is-planned-by-a-pure-function")
    def test_planning_writes_nothing(self):
        completed = self._completed()
        before = {
            key: attribute_snapshot(self.actor, key)
            for key in ("wallet", "inventory", "quest_log", "guild_reward_claims")
        }
        plan_auto_settlement(self.actor, [completed])
        for key, snapshot in before.items():
            self.assertEqual(attribute_snapshot(self.actor, key), snapshot)


class ReplacementPathSettlementTests(QuestRegistryIsolation, EvenniaTest):
    """Task 3.1/5.2: settlement commits inside the replacement transaction."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.definition = register(
            quest("auto_reach", stages=(QuestStage(0, defeat(tier="low")),))
        )
        self.reward = QuestReward(
            copper=30, items=(ItemQuantity("healing_potion", 1),), merit=0
        )
        self.record = accept_auto(self.actor, self.definition, reward=self.reward)

    def _complete(self):
        completed = fulfill_record(self.record, self.definition)
        records = read_records(self.actor)
        apply_quest_log_replacement(
            self.actor,
            [
                completed if r.quest_id == self.record.quest_id else r
                for r in records
            ],
        )
        return completed

    @covers_requirement("quest-auto-settlement::automatic-settlement-commits-atomically-with-the-completing-transition")
    def test_completion_settles_record_wallet_inventory_and_claim_together(self):
        completed = self._complete()
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[completed.quest_id].state, QuestState.COMPLETED)
        self.assertEqual(_wallet(self.actor), 30)
        self.assertIn("healing_potion", self.actor.db.inventory)
        self.assertEqual(parse_reward_claims(self.actor), [completed.quest_id])

    @covers_requirement("quest-auto-settlement::automatic-settlement-commits-atomically-with-the-completing-transition")
    def test_settlement_failure_rolls_back_every_surface(self):
        with patch(
            "world.rules.guild.write_reward_claims",
            side_effect=RuntimeError("injected claim failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._complete()
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[self.record.quest_id].state, QuestState.IN_PROGRESS)
        self.assertEqual(_wallet(self.actor), 0)
        self.assertEqual(list(self.actor.db.inventory or []), [])
        self.assertEqual(parse_reward_claims(self.actor), [])

    @covers_requirement("quest-auto-settlement::automatic-settlement-commits-atomically-with-the-completing-transition")
    def test_chain_reward_completes_auto_acquire_quest(self):
        payer_reward = QuestReward(
            copper=10, items=(ItemQuantity("healing_potion", 2),), merit=0
        )
        payer = accept_auto(
            self.actor,
            register(
                quest("chain_payer", stages=(QuestStage(0, defeat(tier="low")),))
            ),
            reward=payer_reward,
        )
        target_definition = register(
            quest(
                "chain_target",
                stages=(QuestStage(0, acquire("healing_potion", 2)),),
            )
        )
        target = accept_auto(self.actor, target_definition)
        completed = fulfill_record(payer, QUEST_DEFINITION_REGISTRY[payer.definition_key])
        records = read_records(self.actor)
        apply_quest_log_replacement(
            self.actor,
            [
                completed if r.quest_id == payer.quest_id else r for r in records
            ],
        )
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[payer.quest_id].state, QuestState.COMPLETED)
        self.assertEqual(stored[target.quest_id].state, QuestState.COMPLETED)
        self.assertEqual(parse_reward_claims(self.actor), [payer.quest_id, target.quest_id])
        self.assertEqual(_wallet(self.actor), 35)
        self.assertEqual(self.actor.db.inventory.count("healing_potion"), 2)

    def test_chain_pays_each_link_once(self):
        payer_reward = QuestReward(
            copper=10, items=(ItemQuantity("healing_potion", 2),), merit=0
        )
        payer = accept_auto(
            self.actor,
            register(
                quest("link_payer", stages=(QuestStage(0, defeat(tier="low")),))
            ),
            reward=payer_reward,
        )
        middle_reward = QuestReward(
            copper=20, items=(ItemQuantity("rough_iron_ore", 1),), merit=0
        )
        middle = accept_auto(
            self.actor,
            register(
                quest(
                    "link_middle",
                    stages=(QuestStage(0, acquire("healing_potion", 2)),),
                )
            ),
            reward=middle_reward,
        )
        tail_definition = register(
            quest(
                "link_tail",
                stages=(QuestStage(0, acquire("rough_iron_ore", 1)),),
            )
        )
        tail = accept_auto(self.actor, tail_definition)
        completed = fulfill_record(payer, QUEST_DEFINITION_REGISTRY[payer.definition_key])
        records = read_records(self.actor)
        apply_quest_log_replacement(
            self.actor,
            [completed if r.quest_id == payer.quest_id else r for r in records],
        )
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(
            [stored[r.quest_id].state for r in (payer, middle, tail)],
            [QuestState.COMPLETED] * 3,
        )
        self.assertEqual(
            parse_reward_claims(self.actor),
            [payer.quest_id, middle.quest_id, tail.quest_id],
        )
        self.assertEqual(_wallet(self.actor), 55)
        self.assertEqual(self.actor.db.inventory.count("healing_potion"), 2)
        self.assertEqual(self.actor.db.inventory.count("rough_iron_ore"), 1)

    @covers_requirement("quest-auto-settlement::automatic-settlement-never-grants-merit-and-never-needs-a-host")
    def test_wilderness_completion_needs_no_host(self):
        from world.rules.service_view import resolve_local_service_host

        with patch(
            "world.rules.service_view.resolve_local_service_host",
            side_effect=AssertionError("host resolution attempted"),
        ):
            completed = self._complete()
        self.assertEqual(completed.state, QuestState.COMPLETED)
        self.assertEqual(_wallet(self.actor), 30)


class DeltaPathSettlementTests(QuestRegistryIsolation, EvenniaTest):
    """Task 3.2/5.2: settlement commits inside the delta caller's transaction."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.definition = register(
            quest("auto_delta", stages=(QuestStage(0, defeat(tier="low")),))
        )
        self.record = accept_auto(
            self.actor,
            self.definition,
            reward=QuestReward(
                copper=30, items=(ItemQuantity("healing_potion", 1),), merit=0
            ),
        )

    def _new_records(self):
        completed = fulfill_record(self.record, self.definition)
        records = read_records(self.actor)
        return [
            completed if r.quest_id == self.record.quest_id else r for r in records
        ]

    def _caller_snapshots(self):
        return {
            key: attribute_snapshot(self.actor, key)
            for key in ("wallet", "inventory", "guild_reward_claims", "quest_log")
        }

    @staticmethod
    def _caller_restore(actor, snapshots):
        from world.rules.surfaces import restore_attribute_best_effort

        for key, snapshot in snapshots.items():
            restore_attribute_best_effort(actor, key, snapshot)

    @covers_requirement("quest-auto-settlement::automatic-settlement-commits-atomically-with-the-completing-transition")
    def test_inventory_driven_completion_settles_inside_caller_transaction(self):
        new_records = self._new_records()
        snapshots = self._caller_snapshots()
        try:
            with transaction.atomic():
                apply_quest_log_delta(self.actor, new_records)
        except Exception:
            self._caller_restore(self.actor, snapshots)
            raise
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[self.record.quest_id].state, QuestState.COMPLETED)
        self.assertEqual(_wallet(self.actor), 30)
        self.assertIn("healing_potion", self.actor.db.inventory)
        self.assertEqual(parse_reward_claims(self.actor), [self.record.quest_id])

    def test_delta_settlement_failure_restores_settlement_surfaces(self):
        new_records = self._new_records()
        snapshots = self._caller_snapshots()
        with patch(
            "world.rules.guild.write_reward_claims",
            side_effect=RuntimeError("injected claim failure"),
        ):
            with self.assertRaises(RuntimeError), transaction.atomic():
                apply_quest_log_delta(self.actor, new_records)
        self._caller_restore(self.actor, snapshots)
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[self.record.quest_id].state, QuestState.IN_PROGRESS)
        self.assertEqual(_wallet(self.actor), 0)
        self.assertEqual(list(self.actor.db.inventory or []), [])
        self.assertEqual(parse_reward_claims(self.actor), [])

    def test_counter_completion_is_silent_on_the_delta_route(self):
        counter_definition = register(
            quest("silent_delta", stages=(QuestStage(0, defeat(tier="low")),))
        )
        record = accept(self.actor, counter_definition)
        completed = fulfill_record(
            record, QUEST_DEFINITION_REGISTRY[counter_definition.key]
        )
        new_records = [
            completed if r.quest_id == record.quest_id else r
            for r in read_records(self.actor)
        ]
        with (
            patch("world.quests.settlement.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            transaction.atomic(),
        ):
            apply_quest_log_delta(self.actor, new_records)
        self.assertEqual(info.call_args_list, [])


class DefeatActionSettlementTests(QuestRegistryIsolation, EvenniaTestCase):
    """Task 5.2: a DEFEAT completion settles with the committed action."""

    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        self.actor = create_object(PlayerCharacter, key="settlement actor")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        grant_lineage(self.actor, ["fire_ball"], ["fire_mastery"])
        self.definition = register(
            quest("auto_hunt", stages=(QuestStage(0, defeat(tier="low")),))
        )

    def _monster(self, key: str) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = 1
        return monster

    def _resolve(self, targets):
        field = Battlefield(
            {
                "party": frozenset({self.actor.key}),
                "foes": frozenset({targets[0].key}),
            },
            {self.actor.key: self.actor, targets[0].key: targets[0]},
        )
        request = ActionRequest(
            self.actor,
            "fire_ball",
            targets,
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    def test_defeat_completion_settles_with_the_action(self):
        self.record = accept_auto(
            self.actor,
            self.definition,
            reward=QuestReward(
                copper=30, items=(ItemQuantity("healing_potion", 1),), merit=0
            ),
        )
        monster = self._monster("settlement goblin")
        result = self._resolve([monster])
        self.assertEqual(result.outcome, "success")
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[self.record.quest_id].state, QuestState.COMPLETED)
        self.assertEqual(_wallet(self.actor), 30)
        self.assertIn("healing_potion", self.actor.db.inventory)
        self.assertEqual(parse_reward_claims(self.actor), [self.record.quest_id])

    def test_defeat_settlement_failure_rejects_the_action_and_restores(self):
        self.record = accept_auto(self.actor, self.definition)
        monster = self._monster("rollback goblin")
        with patch(
            "world.rules.guild.write_reward_claims",
            side_effect=RuntimeError("injected claim failure"),
        ):
            result = self._resolve([monster])
        self.assertEqual(result.outcome, "rejected")
        self.assertGreater(monster.traits.hp.current, 0)
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[self.record.quest_id].state, QuestState.IN_PROGRESS)
        self.assertEqual(_wallet(self.actor), 0)
        self.assertEqual(parse_reward_claims(self.actor), [])

    @covers_requirement("quest-auto-settlement::automatic-settlement-emits-its-own-boundary-event")
    def test_counter_defeat_completes_without_payout(self):
        record = accept(self.actor, self.definition)
        monster = self._monster("counter goblin")
        with (
            patch("world.quests.settlement.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = self._resolve([monster])
        self.assertEqual(result.outcome, "success")
        stored = {r.quest_id: r for r in read_records(self.actor)}
        self.assertEqual(stored[record.quest_id].state, QuestState.COMPLETED)
        self.assertEqual(_wallet(self.actor), 0)
        self.assertEqual(list(self.actor.db.inventory or []), [])
        self.assertEqual(parse_reward_claims(self.actor), [])
        self.assertEqual(info.call_args_list, [])


class GuildCrossModeSettlementTests(RegistryIsolationMixin, EvenniaTest):
    """Tasks 1.2/5.4: both settlement modes share one exactly-once ledger."""

    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.hall = create_object(Room, key="settlement hall")
        self.staff = create_object(NPC, key="settlement staff", location=self.hall)
        _attach_staff(self.staff)
        self.player = create_object(PlayerCharacter, key="settlement player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)

    def _complete(self, definition, record):
        completed = fulfill_record(record, definition)
        records = read_records(self.player)
        apply_quest_log_replacement(
            self.player,
            [completed if r.quest_id == record.quest_id else r for r in records],
        )
        return completed

    @covers_requirement("quest-reward-settlement::completed-guild-quests-may-be-claimed-exactly-once-per-quest-id")
    def test_counter_refuses_automatically_settled_quest(self):
        definition = register(
            quest("auto_guild_def", stages=(QuestStage(0, defeat(tier="low")),))
        )
        register_guild_offer(_offer(definition.key, copper=50, merit=5))
        record = accept_auto(self.player, definition)
        completed = self._complete(definition, record)
        self.assertEqual(parse_reward_claims(self.player), [completed.quest_id])
        before = (
            _wallet(self.player),
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.guild_reward_claims),
        )
        with self.assertRaises(RewardClaimError) as ctx:
            turn_in_quest(self.player, self.staff, completed.quest_id)
        self.assertEqual(ctx.exception.args[0], RewardClaim.ALREADY_CLAIMED)
        after = (
            _wallet(self.player),
            list(self.player.db.inventory or []),
            read_counter_trait(self.player, "guild_merit"),
            list(self.player.db.guild_reward_claims),
        )
        self.assertEqual(after, before)

    @covers_requirement("quest-auto-settlement::automatic-settlement-never-grants-merit-and-never-needs-a-host")
    def test_auto_settlement_writes_no_merit(self):
        definition = register(
            quest("merit_free", stages=(QuestStage(0, defeat(tier="low")),))
        )
        record = accept_auto(
            self.player,
            definition,
            reward=QuestReward(copper=10, items=(), merit=0),
        )
        completed = self._complete(definition, record)
        self.assertEqual(_wallet(self.player), 10)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 0)
        self.assertEqual(parse_reward_claims(self.player), [completed.quest_id])

    def test_both_modes_share_one_ledger(self):
        auto_definition = register(
            quest("ledger_auto", stages=(QuestStage(0, defeat(tier="low")),))
        )
        auto_record = accept_auto(self.player, auto_definition)
        auto_completed = self._complete(auto_definition, auto_record)
        counter_definition = register(
            quest("ledger_counter", stages=(QuestStage(0, defeat(tier="low")),))
        )
        register_guild_offer(_offer(counter_definition.key, copper=50, merit=5))
        counter_record = accept_quest(
            self.player, counter_definition.key, guild_issuer_key(ALTORIA_BRANCH)
        )
        counter_completed = self._complete(counter_definition, counter_record)
        result = turn_in_quest(self.player, self.staff, counter_completed.quest_id)
        self.assertEqual(result["copper"], 50)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 5)
        self.assertEqual(_wallet(self.player), 75)
        self.assertEqual(
            parse_reward_claims(self.player),
            [auto_completed.quest_id, counter_completed.quest_id],
        )

    @covers_requirement("quest-auto-settlement::automatic-settlement-commits-atomically-with-the-completing-transition")
    def test_counter_reward_completing_auto_acquire_keeps_both_claims(self):
        acquire_definition = register(
            quest(
                "cross_target",
                stages=(QuestStage(0, acquire("healing_potion", 1)),),
            )
        )
        acquire_record = accept_auto(
            self.player,
            acquire_definition,
            reward=QuestReward(copper=15, items=(), merit=0),
        )
        payer_definition = register(
            quest("cross_payer", stages=(QuestStage(0, defeat(tier="low")),))
        )
        register_guild_offer(
            _offer(payer_definition.key, copper=50, merit=0, items=("healing_potion",))
        )
        payer_record = accept_quest(
            self.player, payer_definition.key, guild_issuer_key(ALTORIA_BRANCH)
        )
        payer_completed = self._complete(payer_definition, payer_record)
        turn_in_quest(self.player, self.staff, payer_completed.quest_id)
        stored = {r.quest_id: r for r in read_records(self.player)}
        self.assertEqual(stored[acquire_record.quest_id].state, QuestState.COMPLETED)
        self.assertEqual(
            parse_reward_claims(self.player),
            [payer_completed.quest_id, acquire_record.quest_id],
        )
        self.assertEqual(_wallet(self.player), 65)
        self.assertIn("healing_potion", self.player.db.inventory)


class SettlementEventTests(QuestRegistryIsolation, EvenniaTest):
    """Task 4.1: one boundary event per payout; an empty plan is silent."""

    def _settlement_events(self, info):
        return [
            call.kwargs["context"]
            for call in info.call_args_list
            if call.args and call.args[0] == "quest_auto_settlement"
        ]

    @covers_requirement("quest-auto-settlement::automatic-settlement-emits-its-own-boundary-event")
    def test_payout_emits_one_event_per_settled_quest(self):
        actor = self.char1
        first = accept_auto(
            actor,
            register(quest("event_first", stages=(QuestStage(0, defeat(tier="low")),))),
        )
        second = accept_auto(
            actor,
            register(quest("event_second", stages=(QuestStage(0, defeat(tier="low")),))),
        )
        definition_registry = QUEST_DEFINITION_REGISTRY
        completed_first = fulfill_record(first, definition_registry[first.definition_key])
        completed_second = fulfill_record(second, definition_registry[second.definition_key])
        records = read_records(actor)
        new_records = [
            completed_first if r.quest_id == first.quest_id else r for r in records
        ]
        new_records = [
            completed_second if r.quest_id == second.quest_id else r
            for r in new_records
        ]
        with (
            patch("world.quests.settlement.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            apply_quest_log_replacement(actor, new_records)
        events = self._settlement_events(info)
        self.assertEqual(len(events), 2)
        self.assertEqual(
            [event["quest"] for event in events],
            [first.quest_id, second.quest_id],
        )
        self.assertEqual(events[0]["issuer"], AUTO_ISSUER_KEY)
        self.assertEqual(events[0]["char"], str(actor.pk))
        self.assertEqual(events[0]["copper"], 25)

    @covers_requirement("quest-auto-settlement::automatic-settlement-emits-its-own-boundary-event")
    def test_empty_plan_is_silent(self):
        actor = self.char1
        definition = register(
            quest("silent_counter", stages=(QuestStage(0, defeat(tier="low")),))
        )
        record = accept(actor, definition)
        completed = fulfill_record(record, QUEST_DEFINITION_REGISTRY[definition.key])
        records = read_records(actor)
        new_records = [
            completed if r.quest_id == record.quest_id else r for r in records
        ]
        with (
            patch("world.quests.settlement.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            apply_quest_log_replacement(actor, new_records)
        self.assertEqual(self._settlement_events(info), [])


class JustCompletedDiffTests(QuestRegistryIsolation, EvenniaTest):
    """The write-boundary diff reuses one notion of "just completed"."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.definition = register(quest("diff_probe"))
        self.record = accept_auto(self.actor, self.definition)

    def test_absent_old_entry_counts_as_just_completed(self):
        completed = fulfill_record(self.record, self.definition)
        self.assertEqual(just_completed_records([], [completed]), [completed])

    def test_already_completed_old_entry_is_skipped(self):
        completed = fulfill_record(self.record, self.definition)
        stored = to_storage(completed)
        self.assertEqual(just_completed_records([stored], [completed]), [])

    def test_malformed_old_entry_skips_the_whole_boundary(self):
        completed = fulfill_record(self.record, self.definition)
        self.assertEqual(
            just_completed_records([{"quest_id": "junk"}], [completed]), []
        )

    def test_duplicate_old_ids_skip_the_whole_boundary(self):
        completed = fulfill_record(self.record, self.definition)
        stored = to_storage(self.record)
        self.assertEqual(
            just_completed_records([stored, dict(stored)], [completed]), []
        )

    def test_duplicate_new_ids_skip_the_whole_boundary(self):
        completed = fulfill_record(self.record, self.definition)
        self.assertEqual(
            just_completed_records([], [completed, completed]), []
        )
