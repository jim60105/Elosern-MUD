"""Owner-committed quest completion evidence and notification.

Covers the ``commit-quest-deeds-before-notification`` contract: completion
PLANNING stays pure, the quest-transition writer finalizes the immutable fact
from the authoritative pre-completion bindings, and the owner notification
rides the enclosing transaction's ``on_commit`` with the canonical source
identity. A discarded plan, a rolled-back owner, an unchanged terminal
replacement or a replayed completion produces no fact and no notification.
"""

from contextlib import ExitStack
from dataclasses import replace
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom, Room
from world.narrative.models import NarrativeEvent
from world.narrative.events import record_narrative_event
from world.quests import runtime as quest_runtime
from world.quests.binding import bind_stage_runtime
from world.quests.catalog import register_catalog
from world.quests.definitions import (
    RELATIONSHIP_KINDS,
    EscortCompletion,
    QuestStage,
)
from world.quests.deliver import compute_deliver_replacement
from world.quests.runtime import (
    QuestState,
    fulfill_record,
    read_records,
    register_quest_completion_observer,
)
from world.quests.scene_store import bind_role, publish_package
from world.quests.transitions import (
    apply_quest_log_delta,
    apply_quest_log_replacement,
    pending_effects_for_transition,
    release_stage_binding,
    restore_quest_log,
    snapshot_quest_log,
)
from world.rules.clock import WorldClock
from world.rules.economy import buy
from world.rules.equipment import apply_inventory_plan, plan_inventory_delta
from world.rules.guild_offers import ItemQuantity, QuestReward
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
)
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS, synthetic_registries

from ._fixtures import (
    QuestRegistryIsolation,
    accept,
    accept_auto,
    acquire,
    bound_instance_locator,
    defeat,
    deliver,
    escort,
    quest,
    reach,
    register,
    stage_active_record,
)

#: Kit consumables: one purchase/ACQUIRE objective item and two reward items.
_T_BOUGHT = SYNTH_ITEMS["t_ember_spray"].key
_T_REWARD_ONE = SYNTH_ITEMS["t_iron_fang"].key
_T_REWARD_TWO = SYNTH_ITEMS["t_huskapple"].key


def _enter_scope(test, *logicals: str) -> None:
    stack = ExitStack()
    stack.enter_context(synthetic_registries(*logicals))
    test.addCleanup(stack.close)


class CompletionObserverRecorder:
    """Install one recording completion observer for the test's lifetime."""

    def record_completions(self) -> list:
        receipts: list = []
        patcher = patch.object(
            quest_runtime, "_QUEST_COMPLETION_OBSERVERS", [receipts.append]
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.receipts = receipts
        return receipts


def _completion_events():
    return NarrativeEvent.objects.filter(event_type="quest_completion")


def _event_for(actor, quest_id):
    return _completion_events().get(
        source_id=f"quest:{quest_id}:completion:{actor.pk}"
    )


class CompletionPlanningIsPureTests(
    QuestRegistryIsolation, CompletionObserverRecorder, EvenniaTest
):
    """A plan that predicts completion but never writes leaves no trace."""

    def setUp(self):
        super().setUp()
        _enter_scope(self, "items")
        self.record_completions()
        self.player = create_object(PlayerCharacter, key="planning player")
        self.room = create_object(Room, key="planning room")
        self.player.location = self.room

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_discarded_inventory_plan_produces_no_completion_evidence(self):
        definition = register(
            quest(
                "pure_inventory_plan",
                stages=(QuestStage(0, acquire(_T_BOUGHT, quantity=1)),),
            )
        )
        accept(self.player, definition)

        plan = plan_inventory_delta(self.player, additions=(_T_BOUGHT,))

        self.assertIsNotNone(plan.acquire)
        self.assertEqual(
            [record.state for record in plan.acquire[0]], [QuestState.COMPLETED]
        )
        self.assertEqual(self.receipts, [])
        self.assertFalse(_completion_events().exists())

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_discarded_delivery_plan_produces_no_completion_evidence(self):
        recipient = create_object(NPC, key="planning recipient", location=self.room)
        recipient.race = "human"
        recipient.apply_race_baseline()
        definition = register(
            quest(
                "pure_delivery_plan",
                stages=(QuestStage(0, deliver(_T_BOUGHT, quantity=1)),),
            )
        )
        record = accept(self.player, definition)
        bind_stage_runtime(self.player, record.quest_id, objective_targets=(recipient,))

        delivery = compute_deliver_replacement(self.player, recipient, _T_BOUGHT, 1)

        self.assertIsNotNone(delivery)
        self.assertEqual([item.state for item in delivery[0]], [QuestState.COMPLETED])
        self.assertEqual(self.receipts, [])
        self.assertFalse(_completion_events().exists())

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_discarded_action_plan_produces_no_completion_evidence(self):
        definition = register(
            quest("pure_action_plan", stages=(QuestStage(0, defeat()),))
        )
        record = accept(self.player, definition)
        completed = fulfill_record(record, definition)

        effects = pending_effects_for_transition(self.player, [completed])

        self.assertTrue(effects)
        self.assertEqual(self.receipts, [])
        self.assertFalse(_completion_events().exists())
        self.assertEqual(read_records(self.player)[0].state, QuestState.IN_PROGRESS)

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_partial_progress_produces_no_completion_evidence(self):
        definition = register(
            quest(
                "pure_partial_progress",
                stages=(QuestStage(0, acquire(_T_BOUGHT, quantity=3)),),
            )
        )
        accept(self.player, definition)

        apply_inventory_plan(
            plan_inventory_delta(self.player, additions=(_T_BOUGHT,))
        )

        self.assertEqual(read_records(self.player)[0].stage_progress, 1)
        self.assertEqual(self.receipts, [])
        self.assertFalse(_completion_events().exists())


class PurchaseCompletionBoundaryTests(
    QuestRegistryIsolation, CompletionObserverRecorder, EvenniaTest
):
    """The real purchase path notifies only after its own transaction commits."""

    def setUp(self):
        open_synthetic_scope(self, "items", "prices", "shops")
        super().setUp()
        register_catalog()
        shop_key = next(iter(SYNTH_SHOPS))
        offer = synth_offer_rule(_T_BOUGHT, max_stock=20)
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    shop_key: synth_shop_config(
                        shop_key, (_T_BOUGHT,), offer_rules=(offer,)
                    )
                }
            ),
        )
        self.record_completions()
        self.store = create_object(Room, key="completion store")
        self.merchant = create_object(NPC, key="completion keeper", location=self.store)
        component = Merchant.create(
            self.merchant, service_id="completion_merchant", shop_key=shop_key
        )
        self.merchant.components.add(component)
        component.merchant_stock = {_T_BOUGHT: 20}
        self.player = create_object(PlayerCharacter, key="completion buyer")
        self.player.location = self.store
        self.player.db.wallet = 1000
        self.definition = register(
            quest(
                "purchase_completion_quest",
                stages=(QuestStage(0, acquire(_T_BOUGHT, quantity=1)),),
            )
        )
        accept(self.player, self.definition)

    def _buy(self):
        return buy(self.player, self.merchant, _T_BOUGHT, 1, self.player.pk)

    def _open_clock(self):
        return patch(
            "world.rules.economy.get_world_clock", return_value=WorldClock(12 * 3600)
        )

    def _completed_source_id(self) -> str:
        record = read_records(self.player)[0]
        return f"quest:{record.quest_id}:completion:{self.player.pk}"

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_purchase_plan_notifies_nothing_before_the_transaction_opens(self):
        # ``buy`` computes exactly this replacement before it opens its atomic
        # block; predicting the completion must stay side-effect free.
        plan = plan_inventory_delta(self.player, additions=(_T_BOUGHT,))

        self.assertIsNotNone(plan.acquire)
        self.assertEqual(
            [record.state for record in plan.acquire[0]], [QuestState.COMPLETED]
        )
        self.assertEqual(self.receipts, [])
        self.assertFalse(_completion_events().exists())

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_first_purchase_completion_is_admitted_only_after_commit(self):
        with self._open_clock():
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                self._buy()
                # Inside the purchase's own transaction nothing is notified.
                self.assertEqual(self.receipts, [])

        self.assertTrue(_completion_events().exists())
        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)
        self.assertEqual(self.receipts, [])

        for callback in callbacks:
            callback()

        self.assertEqual(
            [receipt.source_id for receipt in self.receipts],
            [self._completed_source_id()],
        )
        self.assertEqual(self.receipts[0].objective["kind"], "acquire")
        self.assertEqual(self.receipts[0].awards, ())

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_late_purchase_failure_discards_evidence_and_notification(self):
        # The injected fault lands AFTER ``apply_quest_log_delta`` recorded the
        # completion evidence and BEFORE the purchase commits.
        with self._open_clock():
            with patch(
                "world.rules.economy.materialize_registry_object",
                side_effect=RuntimeError("injected"),
            ):
                with self.captureOnCommitCallbacks(execute=True):
                    with self.assertRaises(RuntimeError):
                        self._buy()

        self.assertEqual(self.receipts, [])
        self.assertFalse(_completion_events().exists())
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 0)
        self.assertEqual(list(self.player.db.inventory or []), [])
        self.assertEqual(self.player.db.wallet, 1000)


class CompletionSnapshotTests(
    QuestRegistryIsolation, CompletionObserverRecorder, EvenniaTest
):
    """The fact keeps the satisfied objective's destination and bound roles."""

    def setUp(self):
        super().setUp()
        _enter_scope(self, "items")
        self.record_completions()
        self.player = self.char1

    def _complete(self, record, definition, pins=()):
        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                self.player, [fulfill_record(record, definition)], pins
            )
        return _event_for(self.player, record.quest_id)

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_reach_completion_retains_destination_and_bound_identities(self):
        instance = create_object(InstanceRoom, key="reach destination")
        definition = register(
            quest(
                "snapshot_reach",
                stages=(
                    QuestStage(0, reach(bound_instance_locator(), quantity=1)),
                ),
            )
        )
        record = accept(self.player, definition)
        bound = bind_stage_runtime(self.player, record.quest_id, room=instance)

        event = self._complete(
            bound, definition, release_stage_binding(self.player, record)
        )

        objective = event.content["completed_objective"]
        self.assertEqual(objective["stage_index"], 0)
        self.assertEqual(objective["destination_room_id"], instance.pk)
        self.assertEqual(objective["destination"]["kind"], "bound_instance")
        self.assertEqual(objective["bound_identities"], [])

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_delivery_completion_retains_the_bound_recipient(self):
        recipient = create_object(NPC, key="snapshot recipient", location=self.room1)
        recipient.race = "human"
        recipient.apply_race_baseline()
        definition = register(
            quest(
                "snapshot_delivery",
                stages=(QuestStage(0, deliver(_T_BOUGHT, quantity=1)),),
            )
        )
        record = accept(self.player, definition)
        bound = bind_stage_runtime(
            self.player, record.quest_id, objective_targets=(recipient,)
        )

        event = self._complete(bound, definition)

        self.assertEqual(
            event.content["completed_objective"]["bound_identities"],
            [
                {
                    "role": "recipient",
                    "identity": recipient.pk,
                    "label": recipient.db_key,
                }
            ],
        )

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_escort_completion_retains_protected_roles_and_relation(self):
        protected = create_object(NPC, key="snapshot protected", location=self.room1)
        meeting = create_object(NPC, key="snapshot meeting", location=self.room1)
        for actor in (protected, meeting):
            actor.race = "human"
            actor.apply_race_baseline()
        package, _ = publish_package(
            package_id="snapshot_package",
            source_id=None,
            owner_id="fixture",
            payload={"roles": [{"role_id": "protected"}, {"role_id": "meeting"}]},
        )
        bind_role(package, "protected", protected.pk)
        bind_role(package, "meeting", meeting.pk)
        definition = register(
            quest(
                "snapshot_escort",
                stages=(
                    QuestStage(
                        0,
                        escort(
                            completion=EscortCompletion.RENDEZVOUS,
                            protected_role_refs=("protected",),
                            meeting_role_refs=("meeting",),
                            relation=(RELATIONSHIP_KINDS[0], "protected", "meeting"),
                        ),
                    ),
                ),
            )
        )
        staged = replace(
            stage_active_record(self.player, definition),
            package_id=package.package_id,
            protected_entity_ids=(protected.pk,),
            protected_roles=(("protected", protected.pk),),
        )
        apply_quest_log_replacement(self.player, [staged])

        event = self._complete(staged, definition)

        objective = event.content["completed_objective"]
        self.assertEqual(objective["completion"], "rendezvous")
        self.assertEqual(objective["protected_role_refs"], ["protected"])
        self.assertEqual(objective["meeting_role_refs"], ["meeting"])
        self.assertEqual(
            objective["relation"], [RELATIONSHIP_KINDS[0], "protected", "meeting"]
        )
        self.assertEqual(
            objective["bound_identities"],
            [
                {
                    "role": "protected",
                    "identity": protected.pk,
                    "label": protected.db_key,
                },
                {
                    "role": "meeting:meeting",
                    "identity": meeting.pk,
                    "label": meeting.db_key,
                },
            ],
        )


class CompletionChainSnapshotTests(
    QuestRegistryIsolation, CompletionObserverRecorder, EvenniaTest
):
    """An automatic chain names the FINAL satisfied stage of every completion."""

    def setUp(self):
        super().setUp()
        _enter_scope(self, "items")
        self.record_completions()
        self.player = self.char1

    def _auto_reward(self, *item_keys):
        return QuestReward(
            copper=0,
            items=tuple(ItemQuantity(item_key=key, quantity=1) for key in item_keys),
            merit=0,
        )

    @covers_requirement(
        "narrative-events::completed-quest-and-passed-examination-facts-are-durable"
    )
    def test_chain_completion_names_its_final_satisfied_stage(self):
        payer_one = register(
            quest("chain_payer_one", stages=(QuestStage(0, acquire(_T_BOUGHT)),))
        )
        payer_two = register(
            quest("chain_payer_two", stages=(QuestStage(0, acquire(_T_BOUGHT)),))
        )
        staged = register(
            quest(
                "chain_staged",
                stages=(
                    QuestStage(0, acquire(_T_REWARD_ONE, quantity=1)),
                    QuestStage(1, acquire(_T_REWARD_TWO, quantity=1)),
                ),
            )
        )
        first = accept_auto(self.player, payer_one, self._auto_reward(_T_REWARD_ONE))
        second = accept_auto(self.player, payer_two, self._auto_reward(_T_REWARD_TWO))
        staged_record = accept(self.player, staged)

        records = list(read_records(self.player))
        by_key = lambda definition: next(  # noqa: E731
            record
            for record in records
            if record.definition_key == definition.key
        )
        new_records = [
            fulfill_record(by_key(payer_one), payer_one)
            if record.quest_id == first.quest_id
            else fulfill_record(by_key(payer_two), payer_two)
            if record.quest_id == second.quest_id
            else record
            for record in records
        ]

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            apply_quest_log_replacement(self.player, new_records)
            self.assertEqual(self.receipts, [])

        # Only the two payers and the staged quest actually completed; the
        # staged quest's chain completion names stage 1, its final objective.
        objective = _event_for(self.player, staged_record.quest_id).content[
            "completed_objective"
        ]
        self.assertEqual(objective["stage_index"], 1)
        self.assertEqual(objective["item_key"], _T_REWARD_TWO)

        for callback in callbacks:
            callback()

        self.assertEqual(
            sorted(receipt.quest_id for receipt in self.receipts),
            sorted([first.quest_id, second.quest_id, staged_record.quest_id]),
        )
        self.assertEqual(_completion_events().count(), 3)


class CompletionReplayTests(
    QuestRegistryIsolation, CompletionObserverRecorder, EvenniaTest
):
    """An unchanged terminal record or a replayed completion is inert."""

    def setUp(self):
        super().setUp()
        self.record_completions()
        self.player = self.char1
        self.definition = register(
            quest("replay_target", stages=(QuestStage(0, defeat()),))
        )
        self.record = accept(self.player, self.definition)

    def _complete_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                self.player, [fulfill_record(self.record, self.definition)]
            )
        return read_records(self.player)[0]

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_unchanged_terminal_replacement_is_inert(self):
        completed = self._complete_once()
        self.assertEqual(len(self.receipts), 1)

        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(self.player, [completed])

        self.assertEqual(len(self.receipts), 1)
        self.assertEqual(_completion_events().count(), 1)

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_replayed_completion_notification_is_inert(self):
        # The durable fact already exists for this source identity: the writer
        # must treat its own fresh completion transition as a replay
        # (``created`` is False) and register no notification for it.
        source_id = f"quest:{self.record.quest_id}:completion:{self.player.pk}"
        record_narrative_event(
            source_id=source_id,
            event_type="quest_completion",
            content={
                "location": {"id": "", "label": ""},
                "quest_id": self.record.quest_id,
                "definition_key": self.record.definition_key,
                "completed_objective": {"kind": "defeat", "quantity": 1},
                "outcome": "completed",
            },
            participants=[self.player.pk],
            tick=0,
        )

        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                self.player, [fulfill_record(self.record, self.definition)]
            )

        self.assertEqual(self.receipts, [])
        self.assertEqual(_completion_events().count(), 1)
        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    def test_failing_projection_never_swallows_the_owner_notification(self):
        # The memory projection is a recoverable post-commit side effect: its
        # failure must leave the completion fact and its notification intact,
        # and must never re-enter the writer's rollback compensation.
        with patch(
            "world.narrative.memory.project_narrative_event_to_memories",
            side_effect=RuntimeError("projection boom"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                apply_quest_log_replacement(
                    self.player, [fulfill_record(self.record, self.definition)]
                )

        self.assertEqual(len(self.receipts), 1)
        self.assertEqual(_completion_events().count(), 1)
        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)


class CompletionObserverContractTests(EvenniaTest):
    """The owner dispatch seam keeps its registration and isolation contract."""

    def setUp(self):
        super().setUp()
        self.saved = list(quest_runtime._QUEST_COMPLETION_OBSERVERS)
        self.addCleanup(
            lambda: quest_runtime._QUEST_COMPLETION_OBSERVERS.__setitem__(
                slice(None), self.saved
            )
        )

    def _receipt(self, quest_id="isolation"):
        from world.quests.runtime import QuestCompletionReceipt

        return QuestCompletionReceipt(
            source_id=f"quest:{quest_id}:completion:1",
            actor=self.char1,
            actor_id=int(self.char1.pk),
            quest_id=quest_id,
            definition_key="isolation",
            issuer_key="npc:test_commission",
            objective={"kind": "defeat", "quantity": 1},
            awards=(),
        )

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    def test_registration_is_idempotent(self):
        observer = lambda *args: None  # noqa: E731
        register_quest_completion_observer(observer)
        register_quest_completion_observer(observer)
        self.assertEqual(quest_runtime._QUEST_COMPLETION_OBSERVERS.count(observer), 1)

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    def test_a_raising_observer_never_blocks_the_next_one(self):
        seen = []

        def explode(receipt):
            raise RuntimeError("observer boom")

        register_quest_completion_observer(explode)
        register_quest_completion_observer(seen.append)

        quest_runtime.dispatch_quest_completion(self._receipt())

        self.assertEqual([receipt.quest_id for receipt in seen], ["isolation"])


class CompletionOuterOwnerTests(
    QuestRegistryIsolation, CompletionObserverRecorder, EvenniaTest
):
    """An inner completion waits for — and dies with — the outer owner."""

    def setUp(self):
        super().setUp()
        _enter_scope(self, "items")
        self.record_completions()
        self.player = self.char1
        self.definition = register(
            quest("outer_owner", stages=(QuestStage(0, acquire(_T_BOUGHT)),))
        )
        accept(self.player, self.definition)

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_inner_completion_waits_for_the_outer_commit(self):
        plan = plan_inventory_delta(self.player, additions=(_T_BOUGHT,))
        self.assertIsNotNone(plan.acquire)

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with transaction.atomic():
                self.player.db.inventory = list(plan.after)
                apply_quest_log_delta(self.player, list(plan.acquire[0]))
                # Still inside the outer owner: nothing dispatched, no attempt.
                self.assertEqual(self.receipts, [])
            self.assertEqual(self.receipts, [])

        self.assertTrue(_completion_events().exists())
        for callback in callbacks:
            callback()
        self.assertEqual(len(self.receipts), 1)

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_outer_rollback_discards_the_pending_completion(self):
        plan = plan_inventory_delta(self.player, additions=(_T_BOUGHT,))
        self.assertIsNotNone(plan.acquire)
        # ``apply_quest_log_delta`` performs no snapshot/restore of its own: the
        # caller owns the surface restore (its documented contract). This test
        # stands in for that caller so the gameplay-state assertion is real.
        snapshot = snapshot_quest_log(self.player)

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    apply_quest_log_delta(self.player, list(plan.acquire[0]))
                    raise RuntimeError("injected after the quest writer")
        restore_quest_log(self.player, snapshot)

        self.assertEqual(self.receipts, [])
        self.assertFalse(_completion_events().exists())
        self.assertEqual(read_records(self.player)[0].state, QuestState.IN_PROGRESS)


class CompletionNominationEnvelopeTests(
    QuestRegistryIsolation, CompletionObserverRecorder, EvenniaTest
):
    """The committed owner envelope is what the nomination service cites."""

    def setUp(self):
        super().setUp()
        from server import title_nomination_service as service

        self.service = service
        self.player = self.char1
        self.saved = list(quest_runtime._QUEST_COMPLETION_OBSERVERS)
        self.addCleanup(
            lambda: quest_runtime._QUEST_COMPLETION_OBSERVERS.__setitem__(
                slice(None), self.saved
            )
        )
        self.addCleanup(service.reset_nomination_triggers_for_tests)
        service.reset_nomination_triggers_for_tests()
        quest_runtime.register_quest_completion_observer(service._on_quest_completion)
        self.definition = register(
            quest("nomination_envelope", stages=(QuestStage(0, defeat()),))
        )
        self.record = accept(self.player, self.definition)

    @covers_requirement(
        "title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled"
    )
    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_committed_envelope_drives_the_nomination_service(self):
        with patch.object(self.service, "schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                apply_quest_log_replacement(
                    self.player, [fulfill_record(self.record, self.definition)]
                )

        schedule.assert_called_once()
        self.assertIs(schedule.call_args.args[0], self.player)
        source_id = schedule.call_args.kwargs["source_id"]
        self.assertEqual(
            source_id,
            f"quest:{self.record.quest_id}:completion:{self.player.pk}",
        )
        self.assertEqual(schedule.call_args.kwargs["occurrence_id"], source_id)

        # The rendered nomination context can cite that committed completion.
        committed_tick = NarrativeEvent.objects.get(source_id=source_id).tick
        context = self.service._build_context(
            self.player, frozen_tick=committed_tick
        )
        self.assertIn(source_id, context.supplied_source_ids)
        self.assertIn(self.record.definition_key, context.recent_deeds_json)
