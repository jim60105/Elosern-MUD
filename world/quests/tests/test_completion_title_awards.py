"""Quest-owned quest-completed title awards, replay and enclosing rollback.

Covers the ``associate-quest-completion-title-awards`` contract: a completing
quest settles its quest-completed fixed titles through the unified automatic
award entry point under the completion occurrence's own source, before the
immutable fact is committed; a replayed occurrence returns its original results
without reevaluation; and every enclosing completion owner (purchase,
inventory, delivery, arrival/automatic-chain replacement and action) restores
the title collection and equipped record together with gameplay state.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.titles import (
    FixedTitleDef,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.narrative.events import get_committed_award_results, record_narrative_event
from world.narrative.models import NarrativeEvent, ProjectionProgress
from world.quests import runtime as quest_runtime
from world.quests import transitions as quest_transitions
from world.quests.binding import bind_stage_runtime
from world.quests.catalog import register_catalog
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, fulfill_record, read_records
from world.quests.transitions import (
    apply_quest_log_replacement,
    pending_effects_for_transition,
)
from world.rules.action import CommitFailed, PendingEffect, _commit
from world.rules.clock import WorldClock
from world.rules.economy import buy
from world.rules.equipment import apply_inventory_plan, plan_inventory_delta
from world.rules.guild_offers import ItemQuantity, QuestReward
from world.rules.npc_intents import _transfer_items
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
)
from world.rules.titles import banked_fixed_keys, read_title_state
from world.rules.titles.awards import AutomaticTitleAward
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

from ._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire,
    defeat,
    deliver,
    quest,
    register,
)

#: The one synthetic quest definition whose completion the synthetic rows key on.
_QUEST_KEY = "t_completion_award_quest"
_T_DEED = "t_completed_deed"
_T_DEED_PAIR = "t_completed_deed_pair"
_T_BOUGHT = SYNTH_ITEMS["t_ember_spray"].key
_T_REWARD_ONE = SYNTH_ITEMS["t_iron_fang"].key


def _quest_title_rows() -> dict:
    """Two synthetic quest-completed rows keyed to the completion definition."""
    return {
        key: FixedTitleDef(
            key=key,
            display_name_zh=display,
            category=TitleCategory.EXPLORE,
            flavor_zh="你把那樁委託收在身後。",
            hint_zh="完成指定的具名委託即可獲得。",
            predicate=TitlePredicate(
                family=TitlePredicateFamily.QUEST_COMPLETED,
                quest_key=_QUEST_KEY,
            ),
        )
        for key, display in ((_T_DEED, "委託留名"), (_T_DEED_PAIR, "委託雙名"))
    }


def _open_scope(test, *logicals: str) -> None:
    """Enter one synthetic scope carrying the completion title rows."""
    open_synthetic_scope(test, *logicals, extra={"titles": _quest_title_rows()})


class CompletionAwardRecorder:
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


class CompletionTitleSettlementTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """The quest owner settles completion titles under the occurrence source."""

    def setUp(self):
        _open_scope(self, "titles")
        super().setUp()
        self.record_completions()
        self.player = self.char1
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, defeat()),))
        )
        self.record = accept(self.player, self.definition)

    def _source_id(self, record) -> str:
        return f"quest:{record.quest_id}:completion:{self.player.pk}"

    def _complete(self, record) -> str:
        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                self.player, [fulfill_record(record, self.definition)]
            )
        return self._source_id(record)

    @covers_requirement(
        "title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction"
    )
    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    @covers_requirement(
        "title-system::quest-completion-awards-use-completion-occurrence-attribution"
    )
    def test_completion_finalizes_every_grant_before_the_immutable_fact(self):
        # Warm both caches first: the settlement must write through the same
        # attributes the post-commit read sees.
        read_title_state(self.player)
        source_id = self._complete(self.record)

        event = NarrativeEvent.objects.get(source_id=source_id)
        raw_results = event.content["award_results"]
        self.assertEqual(
            sorted(item["title_id"] for item in raw_results),
            [_T_DEED, _T_DEED_PAIR],
        )
        self.assertEqual(
            {item["source_id"] for item in raw_results}, {source_id}
        )
        self.assertEqual(
            {item["recipient_id"] for item in raw_results},
            {str(self.player.pk)},
        )
        self.assertEqual(
            sorted(banked_fixed_keys(self.player)), [_T_DEED, _T_DEED_PAIR]
        )

        # The receipt the owner forwards already carries those finalized
        # results, so the unchanged generic award check suppresses the
        # occurrence's immediate nomination.
        self.assertEqual(len(self.receipts), 1)
        receipt = self.receipts[0]
        self.assertEqual(receipt.source_id, source_id)
        self.assertEqual(
            sorted(award.title_id for award in receipt.awards),
            [_T_DEED, _T_DEED_PAIR],
        )
        self.assertEqual(
            {award.source_id for award in receipt.awards}, {source_id}
        )

    @covers_requirement(
        "title-system::automatic-built-in-title-awards-report-occurrence-linked-grants"
    )
    @covers_requirement(
        "title-system::quest-completion-awards-use-completion-occurrence-attribution"
    )
    def test_a_new_occurrence_meeting_owned_titles_grants_nothing(self):
        self._complete(self.record)
        before = read_title_state(self.player)

        second = accept(self.player, self.definition)
        source_two = self._complete(second)

        self.assertEqual(
            NarrativeEvent.objects.get(source_id=source_two).content["award_results"],
            [],
        )
        self.assertEqual(read_title_state(self.player), before)
        self.assertEqual(
            sorted(banked_fixed_keys(self.player)), [_T_DEED, _T_DEED_PAIR]
        )
        self.assertEqual(self.receipts[-1].awards, ())

    @covers_requirement(
        "title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction"
    )
    def test_a_live_completion_pushes_one_grant_notification_per_title(self):
        pushed: list = []
        with patch.object(self.player, "msg", side_effect=pushed.append):
            self._complete(self.record)
        self.assertEqual(
            sorted(pushed),
            ["獲得稱號：委託留名", "獲得稱號：委託雙名"],
        )

        # A replay of the same committed occurrence pushes nothing again.
        pushed.clear()
        with patch.object(self.player, "msg", side_effect=pushed.append):
            with self.captureOnCommitCallbacks(execute=True):
                apply_quest_log_replacement(
                    self.player, [fulfill_record(self.record, self.definition)]
                )
        self.assertEqual(pushed, [])

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_a_replayed_completion_returns_its_original_results(self):
        source_id = self._source_id(self.record)
        original = AutomaticTitleAward(
            source_id=source_id,
            recipient_id=str(self.player.pk),
            kind="fixed",
            title_id="t_original_deed",
            granted_tick=5,
            display_name="原事蹟",
        )
        record_narrative_event(
            source_id=source_id,
            event_type="quest_completion",
            content={
                "location": {"id": "", "label": ""},
                "quest_id": self.record.quest_id,
                "definition_key": self.definition.key,
                "completed_objective": {"kind": "defeat", "quantity": 1},
                "outcome": "completed",
            },
            participants=[self.player.pk],
            tick=0,
            award_results=[original],
        )

        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                self.player, [fulfill_record(self.record, self.definition)]
            )

        # No reevaluation: the owned-title rows never ran, so neither truth was
        # banked by the replay, and no second notification was admitted.
        self.assertEqual(banked_fixed_keys(self.player), ())
        self.assertEqual(self.receipts, [])
        self.assertEqual(NarrativeEvent.objects.filter(source_id=source_id).count(), 1)
        committed = get_committed_award_results(source_id)
        self.assertIsNotNone(committed)
        self.assertEqual([award.title_id for award in committed], ["t_original_deed"])
        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)


class CompletionTitleSuppressionScopeTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """Suppression is recipient-specific and local to the awarded occurrence."""

    def setUp(self):
        _open_scope(self, "titles")
        super().setUp()
        self.record_completions()
        self.player = self.char1
        self.other = create_object(PlayerCharacter, key="completion other")
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, defeat()),))
        )

    def _complete(self, actor) -> str:
        record = accept(actor, self.definition)
        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                actor, [fulfill_record(record, self.definition)]
            )
        return f"quest:{record.quest_id}:completion:{actor.pk}"

    @covers_requirement(
        "title-system::immediate-source-suppression-uses-automatic-award-results"
    )
    @covers_requirement(
        "title-system::quest-completion-awards-use-completion-occurrence-attribution"
    )
    def test_another_recipient_s_award_does_not_suppress_the_player(self):
        from server import title_nomination_service as service

        source_other = self._complete(self.other)
        other_awards = get_committed_award_results(source_other)
        self.assertTrue(other_awards)
        self.assertTrue(
            service._check_source_award_suppression(
                str(self.other.pk), award_results=other_awards
            )
        )
        self.assertFalse(
            service._check_source_award_suppression(
                str(self.player.pk), award_results=other_awards
            )
        )

    @covers_requirement(
        "title-system::immediate-source-suppression-uses-automatic-award-results"
    )
    def test_an_occurrence_with_no_new_grant_does_not_suppress(self):
        from server import title_nomination_service as service

        self._complete(self.player)
        second = accept(self.player, self.definition)
        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                self.player, [fulfill_record(second, self.definition)]
            )
        source_two = f"quest:{second.quest_id}:completion:{self.player.pk}"
        self.assertEqual(get_committed_award_results(source_two), ())
        self.assertFalse(
            service._check_source_award_suppression(
                str(self.player.pk), award_results=()
            )
        )


class PurchaseCompletionTitleRollbackTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """A purchase failing after the inner writer restores the title surfaces."""

    def setUp(self):
        _open_scope(self, "items", "prices", "shops", "titles")
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
        self.store = create_object(Room, key="completion title store")
        self.merchant = create_object(
            NPC, key="completion title keeper", location=self.store
        )
        component = Merchant.create(
            self.merchant, service_id="completion_title_merchant", shop_key=shop_key
        )
        self.merchant.components.add(component)
        component.merchant_stock = {_T_BOUGHT: 20}
        self.player = create_object(PlayerCharacter, key="completion title buyer")
        self.player.location = self.store
        self.player.db.wallet = 1000
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, acquire(_T_BOUGHT)),))
        )
        self.record = accept(self.player, self.definition)
        self.source_id = (
            f"quest:{self.record.quest_id}:completion:{self.player.pk}"
        )

    def _open_clock(self):
        return patch(
            "world.rules.economy.get_world_clock", return_value=WorldClock(12 * 3600)
        )

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_a_late_purchase_failure_restores_gameplay_titles_and_evidence(self):
        # Warm every cache the settlement will write through.
        read_records(self.player)
        read_title_state(self.player)
        real = quest_transitions._settle_quest_completion_events
        granted_inside: list = []

        def recording_settlement(actor, old_entries, completed):
            real(actor, old_entries, completed)
            granted_inside.append(banked_fixed_keys(actor))

        with self._open_clock():
            with patch(
                "world.quests.transitions._settle_quest_completion_events",
                side_effect=recording_settlement,
            ):
                with patch(
                    "world.rules.economy.materialize_registry_object",
                    side_effect=RuntimeError("injected after the quest writer"),
                ):
                    with self.captureOnCommitCallbacks(execute=True):
                        with self.assertRaises(RuntimeError):
                            buy(
                                self.player,
                                self.merchant,
                                _T_BOUGHT,
                                1,
                                self.player.pk,
                            )

        # The inner completion really banked both titles before the failure.
        self.assertTrue(granted_inside)
        self.assertIn(_T_DEED, granted_inside[0])
        self.assertEqual(self.receipts, [])
        self.assertEqual(read_records(self.player)[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(list(self.player.db.inventory or []), [])
        self.assertEqual(self.player.db.wallet, 1000)
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.player.attributes.has("title_collection"))
        self.assertFalse(self.player.attributes.has("title_equipped"))
        self.assertIsNone(get_committed_award_results(self.source_id))
        self.assertFalse(
            NarrativeEvent.objects.filter(event_type="quest_completion").exists()
        )
        self.assertFalse(
            ProjectionProgress.objects.filter(source_id=self.source_id).exists()
        )


class InventoryCompletionTitleRollbackTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """The direct inventory plan restores the completion's title grants."""

    def setUp(self):
        _open_scope(self, "items", "titles")
        super().setUp()
        self.record_completions()
        self.player = self.char1
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, acquire(_T_BOUGHT)),))
        )
        self.record = accept(self.player, self.definition)

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_a_late_plan_failure_restores_the_title_surfaces(self):
        read_title_state(self.player)

        real = quest_transitions.apply_quest_log_delta
        granted_inside: list = []

        def failing_delta(actor, records, pins=()):
            real(actor, records, pins)
            granted_inside.append(banked_fixed_keys(actor))
            raise RuntimeError("injected after the quest writer")

        with patch(
            "world.quests.transitions.apply_quest_log_delta", side_effect=failing_delta
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    apply_inventory_plan(
                        plan_inventory_delta(self.player, additions=(_T_BOUGHT,))
                    )

        self.assertTrue(granted_inside)
        self.assertIn(_T_DEED, granted_inside[0])
        self.assertEqual(self.receipts, [])
        self.assertEqual(read_records(self.player)[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(list(self.player.db.inventory or []), [])
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.player.attributes.has("title_collection"))
        self.assertFalse(NarrativeEvent.objects.exists())


class DeliveryCompletionTitleRollbackTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """A transfer failing after the DELIVER writer restores title surfaces."""

    def setUp(self):
        _open_scope(self, "items", "titles")
        super().setUp()
        self.record_completions()
        self.room = create_object(Room, key="completion title delivery room")
        self.player = create_object(PlayerCharacter, key="completion title giver")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.recipient = create_object(
            NPC, key="completion title recipient", location=self.room
        )
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, deliver(_T_BOUGHT)),))
        )
        self.record = accept(self.player, self.definition)
        bind_stage_runtime(
            self.player,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )
        self.player.db.inventory = [_T_BOUGHT]

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_a_late_transfer_failure_restores_gameplay_and_title_state(self):
        read_title_state(self.player)
        granted_inside: list = []

        def failing_events(*args, **kwargs):
            granted_inside.append(banked_fixed_keys(self.player))
            raise RuntimeError("injected after the quest writer")

        with patch(
            "world.quests.deliver.schedule_delivery_events",
            side_effect=failing_events,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                outcome = _transfer_items(self.player, self.recipient, _T_BOUGHT, 1)

        self.assertTrue(granted_inside)
        self.assertIn(_T_DEED, granted_inside[0])
        self.assertFalse(outcome.applied)
        self.assertEqual(self.receipts, [])
        self.assertEqual(read_records(self.player)[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(list(self.player.db.inventory or []), [_T_BOUGHT])
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.player.attributes.has("title_collection"))
        self.assertFalse(
            NarrativeEvent.objects.filter(event_type="quest_completion").exists()
        )


class ReplacementCompletionTitleRollbackTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """Arrival and automatic-chain completions share the replacement writer."""

    def setUp(self):
        _open_scope(self, "titles")
        super().setUp()
        self.record_completions()
        self.player = self.char1
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, defeat()),))
        )
        self.record = accept(self.player, self.definition)

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_a_failure_after_the_settlement_restores_the_grant(self):
        real = quest_transitions._settle_quest_completion_events
        granted_inside: list = []

        def failing_settlement(actor, old_entries, completed):
            real(actor, old_entries, completed)
            granted_inside.append(banked_fixed_keys(actor))
            raise RuntimeError("injected after the settlement")

        with patch(
            "world.quests.transitions._settle_quest_completion_events",
            side_effect=failing_settlement,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    apply_quest_log_replacement(
                        self.player, [fulfill_record(self.record, self.definition)]
                    )

        # The settlement really wrote both titles before the failure...
        self.assertTrue(granted_inside)
        self.assertIn(_T_DEED, granted_inside[0])
        self.assertIn(_T_DEED_PAIR, granted_inside[0])
        # ...and the writer's own snapshot/restore returned them.
        self.assertEqual(self.receipts, [])
        self.assertEqual(read_records(self.player)[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.player.attributes.has("title_collection"))
        self.assertFalse(NarrativeEvent.objects.exists())


class ActionCompletionTitleRollbackTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """The action commit point owns the completion's title surfaces."""

    def setUp(self):
        _open_scope(self, "titles")
        super().setUp()
        self.record_completions()
        self.player = self.char1
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, defeat()),))
        )
        self.record = accept(self.player, self.definition)

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_a_failed_action_commit_restores_the_titles(self):
        effects = pending_effects_for_transition(
            self.player, [fulfill_record(self.record, self.definition)]
        )
        self.assertEqual(effects[0].surfaces, frozenset({"quest_log", "titles"}))
        real = quest_transitions._settle_quest_completion_events
        granted_inside: list = []

        def recording_settlement(actor, old_entries, completed):
            real(actor, old_entries, completed)
            granted_inside.append(banked_fixed_keys(actor))

        raising = PendingEffect(
            self.player,
            "injected failure",
            frozenset({"quest_log"}),
            lambda: (_ for _ in ()).throw(RuntimeError("injected")),
        )
        with patch(
            "world.quests.transitions._settle_quest_completion_events",
            side_effect=recording_settlement,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(CommitFailed):
                    _commit(
                        [effects[0], raising],
                        char="tester",
                        action="probe_action",
                    )

        self.assertTrue(granted_inside)
        self.assertIn(_T_DEED, granted_inside[0])
        self.assertEqual(self.receipts, [])
        self.assertEqual(read_records(self.player)[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(NarrativeEvent.objects.exists())


class MovementCompletionTitleRollbackTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """The movement owner's compensation covers an arrival completion's titles."""

    def setUp(self):
        _open_scope(self, "titles")
        super().setUp()
        self.record_completions()
        self.player = self.char1
        self.source_room = create_object(Room, key="movement title source")
        self.destination = create_object(Room, key="movement title destination")
        self.player.location = self.source_room
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, defeat()),))
        )
        self.record = accept(self.player, self.definition)

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_compensation_restores_the_arrival_completion_titles(self):
        from world.rules.movement_settlement import (
            _compensate,
            _snapshot_movement_state,
        )

        before = read_title_state(self.player)
        snapshot = _snapshot_movement_state(
            self.player,
            self.source_room,
            destination=self.destination,
            wilderness_coordinates=None,
            wilderness_source_coordinates=None,
        )
        # The arrival observation's own writer really banks both titles...
        with self.captureOnCommitCallbacks(execute=False):
            apply_quest_log_replacement(
                self.player, [fulfill_record(self.record, self.definition)]
            )
        self.assertEqual(
            sorted(banked_fixed_keys(self.player)), [_T_DEED, _T_DEED_PAIR]
        )
        # ...and a later movement failure compensates every owned surface,
        # including the title collection and equipped record.
        _compensate(snapshot)
        self.assertEqual(read_title_state(self.player), before)
        self.assertFalse(self.player.attributes.has("title_collection"))
        self.assertFalse(self.player.attributes.has("title_equipped"))


class ChainCompletionTitleTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """An automatic reward chain attributes each completion to its own source."""

    def setUp(self):
        self.payer_title = "t_chain_payer_deed"
        self.target_title = "t_chain_target_deed"
        rows = {
            self.payer_title: FixedTitleDef(
                self.payer_title,
                "委託首環",
                TitleCategory.EXPLORE,
                "第一環在你手中鬆開。",
                "完成自動結算鏈的第一樁委託。",
                TitlePredicate(
                    family=TitlePredicateFamily.QUEST_COMPLETED,
                    quest_key="chain_title_payer",
                ),
            ),
            self.target_title: FixedTitleDef(
                self.target_title,
                "委託次環",
                TitleCategory.EXPLORE,
                "第二環接著落下。",
                "完成自動結算鏈接續的委託。",
                TitlePredicate(
                    family=TitlePredicateFamily.QUEST_COMPLETED,
                    quest_key="chain_title_target",
                ),
            ),
        }
        open_synthetic_scope(
            self, "items", "titles", extra={"titles": _quest_title_rows() | rows}
        )
        super().setUp()
        from world.quests.tests._fixtures import accept_auto

        self.record_completions()
        self.player = self.char1
        self.payer = register(
            quest(
                "chain_title_payer",
                stages=(QuestStage(0, acquire(_T_BOUGHT)),),
            )
        )
        self.target = register(
            quest(
                "chain_title_target",
                stages=(QuestStage(0, acquire(_T_REWARD_ONE)),),
            )
        )
        reward = QuestReward(
            copper=0,
            items=(ItemQuantity(item_key=_T_REWARD_ONE, quantity=1),),
            merit=0,
        )
        self.payer_record = accept_auto(self.player, self.payer, reward)
        self.target_record = accept(self.player, self.target)

    def _source(self, record) -> str:
        return f"quest:{record.quest_id}:completion:{self.player.pk}"

    @covers_requirement(
        "title-system::automatic-built-in-title-awards-report-occurrence-linked-grants"
    )
    def test_both_chain_completions_attribute_their_own_titles(self):
        with self.captureOnCommitCallbacks(execute=True):
            apply_inventory_plan(
                plan_inventory_delta(self.player, additions=(_T_BOUGHT,))
            )

        payer_event = NarrativeEvent.objects.get(
            source_id=self._source(self.payer_record)
        )
        target_event = NarrativeEvent.objects.get(
            source_id=self._source(self.target_record)
        )
        self.assertEqual(
            [item["title_id"] for item in payer_event.content["award_results"]],
            [self.payer_title],
        )
        self.assertEqual(
            [item["title_id"] for item in target_event.content["award_results"]],
            [self.target_title],
        )
        self.assertEqual(
            sorted(banked_fixed_keys(self.player)),
            sorted([self.payer_title, self.target_title]),
        )

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_a_late_chain_failure_restores_both_completion_grants(self):
        read_title_state(self.player)
        real = quest_transitions._settle_quest_completion_events
        calls: list = []

        def failing_settlement(actor, old_entries, completed):
            real(actor, old_entries, completed)
            calls.append(banked_fixed_keys(actor))
            if len(calls) == 2:
                raise RuntimeError("injected after the chain settlement")

        with patch(
            "world.quests.transitions._settle_quest_completion_events",
            side_effect=failing_settlement,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    apply_inventory_plan(
                        plan_inventory_delta(self.player, additions=(_T_BOUGHT,))
                    )

        self.assertEqual(len(calls), 2)
        self.assertEqual(
            sorted(calls[1]), sorted([self.payer_title, self.target_title])
        )
        states = {
            record.definition_key: record.state for record in read_records(self.player)
        }
        self.assertEqual(states[self.payer.key], QuestState.IN_PROGRESS)
        self.assertEqual(states[self.target.key], QuestState.IN_PROGRESS)
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.player.attributes.has("title_collection"))
        self.assertFalse(
            NarrativeEvent.objects.filter(event_type="quest_completion").exists()
        )


class CompletionTitleNominationTests(
    QuestRegistryIsolation, CompletionAwardRecorder, EvenniaTest
):
    """The unchanged nomination service suppresses only the awarded occurrence."""

    def setUp(self):
        from server import title_nomination_service as service

        _open_scope(self, "titles")
        super().setUp()
        self.service = service
        self.saved_observers = list(quest_runtime._QUEST_COMPLETION_OBSERVERS)
        self.addCleanup(
            lambda: quest_runtime._QUEST_COMPLETION_OBSERVERS.__setitem__(
                slice(None), self.saved_observers
            )
        )
        self.addCleanup(service.reset_nomination_triggers_for_tests)
        service.reset_nomination_triggers_for_tests()
        self.record_completions()
        quest_runtime.register_quest_completion_observer(service._on_quest_completion)
        self.player = self.char1
        self.definition = register(
            quest(_QUEST_KEY, stages=(QuestStage(0, defeat()),))
        )
        self.record = accept(self.player, self.definition)

    def _complete(self) -> str:
        with self.captureOnCommitCallbacks(execute=True):
            apply_quest_log_replacement(
                self.player, [fulfill_record(self.record, self.definition)]
            )
        return f"quest:{self.record.quest_id}:completion:{self.player.pk}"

    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    @covers_requirement(
        "title-system::immediate-source-suppression-uses-automatic-award-results"
    )
    @covers_requirement(
        "title-system::quest-completion-awards-use-completion-occurrence-attribution"
    )
    def test_the_committed_envelope_suppresses_its_own_trigger(self):
        source_id = self._complete()
        receipt = self.receipts[0]
        self.assertEqual(receipt.source_id, source_id)
        self.assertTrue(receipt.awards)

        # Replaying the owner's own notification is suppressed before any
        # context is built or a client consulted: the service is unchanged.
        with patch.object(self.service, "_build_context") as build:
            with patch.object(self.service, "_build_nomination_client") as client:
                admitted = self.service.schedule_epithet_nomination(
                    self.player,
                    source_id=source_id,
                    award_results=receipt.awards,
                    occurrence_id=source_id,
                    trigger="quest_completion",
                )
        self.assertIsNone(admitted)
        build.assert_not_called()
        client.assert_not_called()

    @covers_requirement(
        "title-system::quest-nomination-observes-the-committed-completion-owner"
    )
    def test_the_deed_stays_usable_for_a_later_rest_point(self):
        source_id = self._complete()

        # One committed fact, read back fresh, carrying the finalized results.
        self.assertEqual(NarrativeEvent.objects.filter(source_id=source_id).count(), 1)
        committed = get_committed_award_results(source_id)
        self.assertEqual(
            sorted(award.title_id for award in committed), [_T_DEED, _T_DEED_PAIR]
        )
        self.assertEqual(
            {award.recipient_id for award in committed}, {str(self.player.pk)}
        )

        # The suppression is local to that occurrence: a later rest point can
        # still cite the completion deed, and no ballot was created by it.
        committed_tick = NarrativeEvent.objects.get(source_id=source_id).tick
        context = self.service._build_context(
            self.player, frozen_tick=committed_tick
        )
        self.assertEqual(context.frozen_tick, committed_tick)
        self.assertIn(source_id, context.supplied_source_ids)
        self.assertIn(self.definition.key, context.recent_deeds_json)
        from world.rules import titles as title_rules

        self.assertEqual(title_rules.safe_pending_ballot(self.player), ())

    def tearDown(self):
        self.service.reset_nomination_triggers_for_tests()
        super().tearDown()
