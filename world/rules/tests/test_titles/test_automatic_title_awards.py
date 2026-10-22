"""Behavior tests for unified automatic built-in-title award results.

OpenSpec change: unify-automatic-title-award-results
Specs: openspec/changes/unify-automatic-title-award-results/specs/title-system/spec.md
"""

from copy import deepcopy
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.lore.titles import (
    FIXED_TITLE_REGISTRY,
    FixedTitleDef,
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.narrative.events import (
    get_committed_award_results,
    record_narrative_event,
)
from world.narrative.models import NarrativeEvent
from world.rules.titles import (
    AutomaticTitleAward,
    accept_epithet,
    award_automatic_title,
    award_first_quest_epithet,
    award_guild_rank_title,
    persist_nomination_ballot,
    read_title_state,
)
from world.tests.synthetic_data import SYNTH_STARTER_EPITHET


class AutomaticTitleAwardBehaviorTests(EvenniaTestCase):
    """Verify unified automatic built-in-title awards and replay/transaction semantics."""

    def setUp(self):
        super().setUp()
        self.char1 = create_object(PlayerCharacter, key="t_award_recipient_1")
        self.char2 = create_object(PlayerCharacter, key="t_award_recipient_2")
        self.starter_patcher = patch(
            "world.lore.titles.STARTER_EPITHET", SYNTH_STARTER_EPITHET
        )
        self.starter_patcher.start()
        self.addCleanup(self.starter_patcher.stop)

    @covers_requirement(
        "title-system::automatic-built-in-title-awards-report-occurrence-linked-grants"
    )
    def test_several_grants_retain_attribution(self):
        """Scenario: Several grants retain attribution.

        WHEN one occurrence grants several built-in titles to two recipients,
        THEN each new grant carries its source, recipient and title identity,
        including an automatically authored starter epithet.
        """
        source_id = "occurrence:multigrant:session:101"

        # char1 receives fixed title F and starter epithet
        award_1a, note_1a = award_guild_rank_title(
            self.char1, "F", source_id=source_id, tick=10
        )
        award_1b, note_1b = award_first_quest_epithet(
            self.char1, source_id=source_id, tick=10
        )

        # char2 receives fixed title F
        award_2, note_2 = award_guild_rank_title(
            self.char2, "F", source_id=source_id, tick=10
        )

        self.assertIsNotNone(award_1a)
        self.assertIsNotNone(award_1b)
        self.assertIsNotNone(award_2)

        self.assertEqual(award_1a.source_id, source_id)
        self.assertEqual(award_1a.recipient_id, str(self.char1.pk))
        self.assertEqual(award_1a.kind, "fixed")
        self.assertEqual(award_1a.title_id, "g_f_rank")

        self.assertEqual(award_1b.source_id, source_id)
        self.assertEqual(award_1b.recipient_id, str(self.char1.pk))
        self.assertEqual(award_1b.kind, "epithet")
        self.assertEqual(award_1b.title_id, SYNTH_STARTER_EPITHET.display)

        self.assertEqual(award_2.source_id, source_id)
        self.assertEqual(award_2.recipient_id, str(self.char2.pk))
        self.assertEqual(award_2.kind, "fixed")
        self.assertEqual(award_2.title_id, "g_f_rank")

        # Verify auto-equipped slots
        _, eq1 = read_title_state(self.char1)
        self.assertEqual(eq1["fixed"], "g_f_rank")
        self.assertEqual(eq1["epithet"], SYNTH_STARTER_EPITHET.display)

        _, eq2 = read_title_state(self.char2)
        self.assertEqual(eq2["fixed"], "g_f_rank")

    @covers_requirement(
        "title-system::automatic-built-in-title-awards-report-occurrence-linked-grants"
    )
    def test_existing_ownership_is_not_a_new_grant(self):
        """Scenario: Existing ownership is not a new grant.

        WHEN a new occurrence tries to grant an already-owned title,
        THEN that title contributes no award result.
        """
        source_1 = "occurrence:first:1"
        source_2 = "occurrence:second:2"

        award_first, _ = award_guild_rank_title(
            self.char1, "F", source_id=source_1, tick=20
        )
        self.assertIsNotNone(award_first)

        # Now try granting same title from a new, different occurrence
        award_dup, note_dup = award_guild_rank_title(
            self.char1, "F", source_id=source_2, tick=30
        )
        self.assertIsNone(award_dup)
        self.assertIsNone(note_dup)

    @covers_requirement(
        "title-system::automatic-built-in-title-awards-report-occurrence-linked-grants"
    )
    def test_future_producer_uses_the_contract(self):
        """Scenario: Future producer uses the contract.

        WHEN a synthetic future event grants a synthetic built-in title,
        THEN it produces the same result contract without nomination-specific
        event classifications.
        """
        source_id = "future:event:encounter:boss_down:1"
        synth_key = "t_synth_future_title"
        synth_def = FixedTitleDef(
            key=synth_key,
            display_name_zh="屠龍先鋒",
            category=TitleCategory.COMBAT,
            flavor_zh="擊破惡龍之首位冒險者。",
            hint_zh="在荒野遭遇中擊敗巨龍。",
            predicate=TitlePredicate(TitlePredicateFamily.QUEST_COMPLETED, quest_key="dummy"),
        )
        new_registry = dict(FIXED_TITLE_REGISTRY)
        new_registry[synth_key] = synth_def
        with patch("world.rules.titles.state.FIXED_TITLE_REGISTRY", new_registry), patch(
            "world.lore.titles.FIXED_TITLE_REGISTRY", new_registry
        ), patch(
            "world.rules.titles.awards.FIXED_TITLE_REGISTRY", new_registry
        ):
            award, note = award_automatic_title(
                self.char1,
                source_id=source_id,
                kind="fixed",
                title_id=synth_key,
                tick=50,
            )
            self.assertIsNotNone(award)
            self.assertEqual(award.source_id, source_id)
            self.assertEqual(award.recipient_id, str(self.char1.pk))
            self.assertEqual(award.kind, "fixed")
            self.assertEqual(award.title_id, synth_key)
            self.assertEqual(award.display_name, "屠龍先鋒")
            self.assertEqual(note, "獲得稱號：屠龍先鋒")

    @covers_requirement(
        "title-system::automatic-built-in-title-awards-report-occurrence-linked-grants"
    )
    def test_consent_is_separate(self):
        """Scenario: Consent is separate.

        WHEN a player accepts a generated epithet,
        THEN no automatic built-in-title award result is emitted.
        """
        self.assertTrue(
            persist_nomination_ballot(
                self.char1,
                [{"display": "風暴之眼", "basis": "在暴風雨中救出同伴。"}],
            )
        )
        accepted_display, newly_banked = accept_epithet(self.char1, 1)
        self.assertEqual(accepted_display, "風暴之眼")
        self.assertTrue(newly_banked)

        committed = get_committed_award_results("ballot:accept:1")
        self.assertIsNone(committed)

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_rollback_after_writes(self):
        """Scenario: Rollback after writes.

        WHEN a fault follows gameplay, title, award and narrative writes
        before outer commit,
        THEN all durable and cached gameplay/title state and related records
        return to their prior values.
        """
        from world.rules.surfaces import (
            restore_attribute_best_effort,
            snapshot_attributes,
        )

        source_id = "occurrence:atomic_failure:1"
        snapshots = snapshot_attributes(
            self.char1, ("title_collection", "title_equipped")
        )
        initial_collection, initial_equipped = read_title_state(self.char1)

        try:
            with transaction.atomic():
                award, _ = award_guild_rank_title(
                    self.char1, "F", source_id=source_id, tick=100
                )
                self.assertIsNotNone(award)
                record_narrative_event(
                    source_id=source_id,
                    event_type="test_encounter",
                    content={"outcome": "victory"},
                    participants=[str(self.char1.pk)],
                    tick=100,
                    award_results=[award],
                )
                raise RuntimeError("simulated database commit failure")
        except RuntimeError:
            restore_attribute_best_effort(
                self.char1, "title_collection", snapshots["title_collection"]
            )
            restore_attribute_best_effort(
                self.char1, "title_equipped", snapshots["title_equipped"]
            )

        self.assertIsNone(NarrativeEvent.objects.filter(source_id=source_id).first())
        self.assertIsNone(get_committed_award_results(source_id))

        current_collection, current_equipped = read_title_state(self.char1)
        self.assertEqual(current_collection, initial_collection)
        self.assertEqual(current_equipped, initial_equipped)

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay"
    )
    def test_replay_keeps_suppression_evidence(self):
        """Scenario: Replay keeps suppression evidence.

        WHEN the same committed source settles again after its title is already owned,
        THEN one source remains and its original nonempty award results are returned unchanged.
        """
        source_id = "occurrence:replay_source:999"

        with transaction.atomic():
            award, _ = award_guild_rank_title(
                self.char1, "F", source_id=source_id, tick=200
            )
            self.assertIsNotNone(award)
            record_narrative_event(
                source_id=source_id,
                event_type="test_settlement",
                content={"step": "first"},
                participants=[str(self.char1.pk)],
                tick=200,
                award_results=[award],
            )

        first_committed = get_committed_award_results(source_id)
        self.assertIsNotNone(first_committed)
        self.assertEqual(len(first_committed), 1)
        self.assertEqual(first_committed[0].title_id, "g_f_rank")

        replay_awards = get_committed_award_results(source_id)
        self.assertIsNotNone(replay_awards)
        self.assertEqual(len(replay_awards), 1)
        self.assertEqual(replay_awards[0].title_id, "g_f_rank")

        event, progress, created = record_narrative_event(
            source_id=source_id,
            event_type="test_settlement",
            content={"step": "replayed"},
            participants=[str(self.char1.pk)],
            tick=200,
            award_results=(),
        )
        self.assertFalse(created)
        raw_results = event.content.get("award_results")
        self.assertEqual(len(raw_results), 1)
        self.assertEqual(raw_results[0]["title_id"], "g_f_rank")

        self.assertEqual(NarrativeEvent.objects.filter(source_id=source_id).count(), 1)
