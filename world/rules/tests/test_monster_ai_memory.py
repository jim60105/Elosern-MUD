"""Behavior tests for the per-session monster observation memory.

Every fixture here is file-local and synthetic: the entities are the shared
in-memory ``FakeEntity`` doubles (no database rows), and the integration case
builds one file-local synthetic damage skill rather than naming shipped
content.

The tests establish this slice's contracts: compact bounded records with a
three-round/128-record window and bounded recipients; immediate same-round
visibility through a transaction-local overlay that publishes only after the
outermost commit and discards on rollback; savepoint-local observations being
removed when a nested savepoint fails while the enclosing transaction
continues; commit-only terminal cleanup that supersedes every earlier
publication and keeps both history and recorded tuning when it rolls back; and
eligibility through the battlefield's current live membership and faction,
with session isolation, reconstruction retention and an empty restart.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.db import transaction

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster

from world.rules.action import ActionRequest
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    ExecutionScopeBase,
    run_round,
)
from world.rules.combat_session.observations import (
    MAX_RECORD_RECIPIENTS,
    MAX_RETAINED_RECORDS,
    MAX_RETAINED_ROUNDS,
    clear_session_memory,
    discard_session_memory,
    observe_action,
    project_observations,
    reconcile_session_memory,
    record_observation,
    session_observations,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.monster_ai.models import PublicObservation

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    open_synthetic_scope,
    synth_damage_skill,
)
from .combat_fixtures import FakeEntity

#: The single file-local synthetic damage row the integration case casts.
MEM_STRIKE = synth_damage_skill(
    "t_mem_strike",
    "記憶擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={},
)


class _CaughtSavepointFailure(Exception):
    """A savepoint failure the enclosing transaction catches and survives."""


def _observation(
    round_index: int,
    *,
    action="t_action",
    source="key:actor",
    recipients=("key:enemy",),
    statuses=("damage",),
    faction="monsters",
    magnitudes=(("key:enemy", -5.0),),
) -> PublicObservation:
    return PublicObservation(
        round_index=round_index,
        sequence=0,
        source_id=source,
        action_key=action,
        recipient_ids=tuple(recipients),
        statuses=tuple(statuses),
        source_faction=faction,
        magnitudes=tuple(magnitudes),
    )


def _field(actor, *others, actor_team="monsters", other_team="party") -> Battlefield:
    entities = (actor, *others)
    return Battlefield(
        {
            actor_team: frozenset({actor.key}),
            other_team: frozenset(other.key for other in others),
        },
        {entity.key: entity for entity in entities},
    )


class ObservationMemoryTests(EvenniaTestCase):
    """Compact bounded records and their transaction-safe lifetime."""

    def setUp(self):
        super().setUp()
        clear_session_memory()
        self.addCleanup(clear_session_memory)

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_the_window_keeps_the_most_recent_three_rounds(self):
        session = "hostile:1:0"
        with self.captureOnCommitCallbacks(execute=True):
            for round_index in range(1, 6):
                record_observation(session, _observation(round_index))
        self.assertEqual(
            [record.round_index for record in session_observations(session)],
            [3, 4, 5],
        )
        self.assertEqual(MAX_RETAINED_ROUNDS, 3)

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_the_window_keeps_at_most_the_record_capacity(self):
        session = "hostile:1:0"
        with patch("world.rules.combat_session.observations.log_info"), (
            self.captureOnCommitCallbacks(execute=True)
        ):
            for _ in range(MAX_RETAINED_RECORDS + 2):
                record_observation(session, _observation(1))
        committed = session_observations(session)
        self.assertEqual(len(committed), MAX_RETAINED_RECORDS)
        # The most recent records survive; the oldest two are evicted.
        self.assertEqual(committed[0].sequence, 2)

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_capacity_loss_is_traced(self):
        session = "hostile:1:0"
        with patch(
            "world.rules.combat_session.observations.log_info"
        ) as info, self.captureOnCommitCallbacks(execute=True):
            for _ in range(MAX_RETAINED_RECORDS + 1):
                record_observation(session, _observation(1))
        info.assert_called_once()
        self.assertEqual(info.call_args.args[0], "monster_ai_observation_evicted")

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_records_carry_no_entity_or_callback_reference(self):
        session = "hostile:1:0"
        with self.captureOnCommitCallbacks(execute=True):
            record_observation(session, _observation(1))
        record = session_observations(session)[0]
        for value in (
            record.source_id,
            record.action_key,
            *record.recipient_ids,
            *record.statuses,
            record.source_faction,
        ):
            self.assertIsInstance(value, str)
        for identity, magnitude in record.magnitudes:
            self.assertIsInstance(identity, str)
            self.assertIsInstance(magnitude, float)


class ObservationTransactionTests(EvenniaTestCase):
    """Same-round visibility, commit-only publication and rollback discards."""

    def setUp(self):
        super().setUp()
        clear_session_memory()
        self.addCleanup(clear_session_memory)
        self.actor = FakeEntity("actor")
        self.enemy = FakeEntity("enemy")
        self.field = _field(self.actor, self.enemy)

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_an_earlier_action_is_visible_before_the_commit(self):
        session = "hostile:1:0"
        with self.captureOnCommitCallbacks(execute=False):
            record_observation(
                session,
                _observation(1, source="key:actor", recipients=("key:enemy",)),
            )
            projected = project_observations(session, self.field)
        self.assertEqual([record.action_key for record in projected], ["t_action"])
        # Nothing is committed before the transaction ends.
        self.assertEqual(session_observations(session), ())

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_outer_rollback_discards_uncommitted_observations(self):
        session = "hostile:1:0"
        try:
            with transaction.atomic():
                record_observation(
                    session,
                    _observation(1, source="key:actor", recipients=("key:enemy",)),
                )
                raise _CaughtSavepointFailure
        except _CaughtSavepointFailure:
            pass
        reconcile_session_memory(session)
        self.assertEqual(session_observations(session), ())
        self.assertEqual(project_observations(session, self.field), ())

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_a_failed_savepoint_removes_only_its_own_observations(self):
        session = "hostile:1:0"
        with self.captureOnCommitCallbacks(execute=True):
            record_observation(
                session, _observation(1, action="t_before", source="key:actor")
            )
            try:
                with transaction.atomic():
                    record_observation(
                        session, _observation(1, action="t_inside", source="key:actor")
                    )
                    raise _CaughtSavepointFailure
            except _CaughtSavepointFailure:
                pass
            reconcile_session_memory(session)
            record_observation(
                session, _observation(1, action="t_after", source="key:actor")
            )
        actions = [record.action_key for record in session_observations(session)]
        self.assertIn("t_before", actions)
        self.assertIn("t_after", actions)
        self.assertNotIn("t_inside", actions)

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_a_failed_savepoint_last_before_commit_never_publishes(self):
        session = "hostile:1:0"
        with self.captureOnCommitCallbacks(execute=True):
            record_observation(
                session, _observation(1, action="t_before", source="key:actor")
            )
            try:
                with transaction.atomic():
                    record_observation(
                        session, _observation(1, action="t_inside", source="key:actor")
                    )
                    raise _CaughtSavepointFailure
            except _CaughtSavepointFailure:
                pass
            # Deliberately no reconciliation and no later memory call: the
            # survival marks of the failed savepoint's entry are never set.
        actions = [record.action_key for record in session_observations(session)]
        self.assertEqual(actions, ["t_before"])

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_a_reused_atomic_after_rollback_starts_a_fresh_journal(self):
        session = "hostile:1:0"
        reusable = transaction.atomic()
        try:
            with reusable:
                record_observation(
                    session, _observation(1, action="t_lost", source="key:actor")
                )
                raise _CaughtSavepointFailure
        except _CaughtSavepointFailure:
            pass
        with self.captureOnCommitCallbacks(execute=True):
            with reusable:
                record_observation(
                    session, _observation(1, action="t_fresh", source="key:actor")
                )
        actions = [record.action_key for record in session_observations(session)]
        self.assertEqual(actions, ["t_fresh"])

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_a_stale_publication_callback_cannot_duplicate_memory(self):
        session = "hostile:1:0"
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            record_observation(
                session,
                _observation(1, source="key:actor", recipients=("key:enemy",)),
            )
        for callback in callbacks:
            callback()
        committed = session_observations(session)
        for callback in callbacks:
            callback()
        self.assertEqual(session_observations(session), committed)

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_a_standalone_round_cannot_touch_shared_session_memory(self):
        self.assertFalse(
            record_observation(
                "", _observation(1, source="key:actor", recipients=("key:enemy",))
            )
        )
        self.assertEqual(project_observations("", self.field), ())


class ObservationTerminalTests(EvenniaTestCase):
    """Commit-only terminal cleanup that supersedes publication."""

    def setUp(self):
        super().setUp()
        clear_session_memory()
        self.addCleanup(clear_session_memory)
        self.actor = FakeEntity("actor")
        self.enemy = FakeEntity("enemy")
        self.field = _field(self.actor, self.enemy)

    def _publish(self, session, action="t_action"):
        with self.captureOnCommitCallbacks(execute=True):
            record_observation(
                session, _observation(1, action=action, source="key:actor")
            )

    @covers_requirement(
        "monster-ai-observation-memory::terminal-cleanup-supersedes-publication"
    )
    def test_terminal_cleanup_discards_memory_and_tuning_after_commit(self):
        session = "hostile:1:0"
        with patch(
            "world.rules.combat_session.observations.discard_session_ai_tuning"
        ) as drop, self.captureOnCommitCallbacks(execute=True):
            record_observation(session, _observation(1, source="key:actor"))
            discard_session_memory(session)
        drop.assert_called_once_with(session)
        self.assertEqual(session_observations(session), ())

    @covers_requirement(
        "monster-ai-observation-memory::terminal-cleanup-supersedes-publication"
    )
    def test_a_late_publication_cannot_recreate_terminated_memory(self):
        session = "hostile:1:0"
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            record_observation(session, _observation(1, source="key:actor"))
            discard_session_memory(session)
        for callback in callbacks:
            callback()
        self.assertEqual(session_observations(session), ())

    @covers_requirement(
        "monster-ai-observation-memory::terminal-cleanup-supersedes-publication"
    )
    def test_a_rolled_back_terminal_keeps_history_and_configuration(self):
        session = "hostile:1:0"
        self._publish(session, action="t_kept")
        with patch(
            "world.rules.combat_session.observations.discard_session_ai_tuning"
        ) as drop, self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    discard_session_memory(session)
                    raise _CaughtSavepointFailure
            except _CaughtSavepointFailure:
                pass
            reconcile_session_memory(session)
            record_observation(
                session, _observation(1, action="t_later", source="key:actor")
            )
        drop.assert_not_called()
        actions = [record.action_key for record in session_observations(session)]
        self.assertIn("t_kept", actions)
        self.assertIn("t_later", actions)

    @covers_requirement(
        "monster-ai-observation-memory::terminal-cleanup-supersedes-publication"
    )
    def test_a_failed_terminal_last_before_commit_keeps_history(self):
        session = "hostile:1:0"
        self._publish(session, action="t_kept")
        with patch(
            "world.rules.combat_session.observations.discard_session_ai_tuning"
        ) as drop, self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    discard_session_memory(session)
                    raise _CaughtSavepointFailure
            except _CaughtSavepointFailure:
                pass
            # No reconciliation and no later memory call: the failed terminal's
            # survival mark is never set, so it cannot delete the history.
        drop.assert_not_called()
        self.assertEqual(
            [record.action_key for record in session_observations(session)],
            ["t_kept"],
        )

    @covers_requirement(
        "monster-ai-observation-memory::terminal-cleanup-supersedes-publication"
    )
    def test_discard_outside_a_transaction_applies_immediately(self):
        session = "hostile:1:0"
        self._publish(session)
        detached = SimpleNamespace(in_atomic_block=False)
        with patch(
            "world.rules.combat_session.observations._connection",
            return_value=detached,
        ), patch(
            "world.rules.combat_session.observations.discard_session_ai_tuning"
        ) as drop:
            discard_session_memory(session)
        drop.assert_called_once_with(session)
        self.assertEqual(session_observations(session), ())


class ObservationEligibilityTests(EvenniaTestCase):
    """Eligibility through current live membership and faction."""

    def setUp(self):
        super().setUp()
        clear_session_memory()
        self.addCleanup(clear_session_memory)

    def _publish(self, session, **overrides):
        with self.captureOnCommitCallbacks(execute=True):
            record_observation(
                session,
                _observation(
                    1, source="key:actor", recipients=("key:enemy",), **overrides
                ),
            )

    @covers_requirement(
        "monster-ai-observation-memory::observation-access-follows-current-session-membership"
    )
    def test_sessions_cannot_read_each_other(self):
        with self.captureOnCommitCallbacks(execute=True):
            record_observation(
                "hostile:1:0", _observation(1, action="t_a", source="key:actor")
            )
            record_observation(
                "hostile:2:0", _observation(1, action="t_b", source="key:enemy")
            )
        self.assertEqual(
            [r.action_key for r in session_observations("hostile:1:0")], ["t_a"]
        )
        self.assertEqual(
            [r.action_key for r in session_observations("hostile:2:0")], ["t_b"]
        )

    @covers_requirement(
        "monster-ai-observation-memory::observation-access-follows-current-session-membership"
    )
    def test_reconstruction_preserves_committed_history(self):
        session = "hostile:1:0"
        self._publish(session)
        rebuilt = _field(FakeEntity("actor"), FakeEntity("enemy"))
        self.assertEqual(len(project_observations(session, rebuilt)), 1)

    @covers_requirement(
        "monster-ai-observation-memory::observation-access-follows-current-session-membership"
    )
    def test_stale_membership_and_faction_are_excluded(self):
        session = "hostile:1:0"
        self._publish(session)
        # The recipient disappeared: the fact survives, the stale target does not.
        projected = project_observations(session, _field(FakeEntity("actor")))
        self.assertEqual(len(projected), 1)
        self.assertEqual(projected[0].recipient_ids, ())
        self.assertEqual(projected[0].magnitudes, ())
        # The source changed faction: the fact is no longer eligible.
        changed = Battlefield(
            {
                "monsters": frozenset({"witness"}),
                "party": frozenset({"actor"}),
            },
            {
                "witness": FakeEntity("witness"),
                "actor": FakeEntity("actor"),
            },
        )
        self.assertEqual(project_observations(session, changed), ())
        # The source vanished entirely: nothing is eligible.
        self.assertEqual(project_observations(session, _field(FakeEntity("npc"))), ())

    @covers_requirement(
        "monster-ai-observation-memory::observation-access-follows-current-session-membership"
    )
    def test_a_restart_clears_history(self):
        session = "hostile:1:0"
        self._publish(session)
        clear_session_memory()
        self.assertEqual(session_observations(session), ())


class ObservationBoundaryExtractionTests(EvenniaTestCase):
    """Item and upkeep boundaries and bounded recipient summaries."""

    def setUp(self):
        super().setUp()
        clear_session_memory()
        self.addCleanup(clear_session_memory)

    def _observe(self, session, event_log, field, round_index=1):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertTrue(
                observe_action(
                    session,
                    round_index,
                    event_log,
                    roster=field.roster,
                    battlefield=field,
                )
            )

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_an_item_heal_is_a_positive_health_fact(self):
        actor = FakeEntity("actor")
        target = FakeEntity("target")
        field = _field(actor, target)
        # The production item pipeline emits ``item_used`` with the signed
        # gauge delta actually applied; a restoration carries a +amount and is
        # not sign-flipped like a skill's ``damage`` entry.
        log = EventLog(
            actor="actor",
            skill_key="t_tonic",
            targets=("target",),
            entries=(
                EventEntry(
                    "item_used",
                    "actor",
                    "target",
                    {"item_key": "t_tonic", "consumable": True, "stat": "hp", "amount": 7},
                    "",
                ),
            ),
            time_cost_seconds=0,
        )
        self._observe("hostile:1:0", log, field)
        record = session_observations("hostile:1:0")[0]
        self.assertEqual(record.action_key, "t_tonic")
        self.assertEqual(record.magnitudes, (("key:target", 7.0),))

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_an_item_status_fact_is_recorded_without_a_health_magnitude(self):
        actor = FakeEntity("actor")
        target = FakeEntity("target")
        field = _field(actor, target)
        log = EventLog(
            actor="actor",
            skill_key="t_charm",
            targets=("target",),
            entries=(
                EventEntry(
                    "item_used",
                    "actor",
                    "target",
                    {
                        "item_key": "t_charm",
                        "consumable": True,
                        "status_keys": ["t_blessing"],
                        "count": 1,
                    },
                    "",
                ),
            ),
            time_cost_seconds=0,
        )
        self._observe("hostile:1:0", log, field)
        record = session_observations("hostile:1:0")[0]
        self.assertEqual(record.statuses, ("t_blessing",))
        self.assertEqual(record.magnitudes, ())

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_an_upkeep_tick_is_a_negative_health_fact(self):
        actor = FakeEntity("actor")
        target = FakeEntity("target")
        field = _field(actor, target)
        log = EventLog(
            actor="actor",
            skill_key="combat_upkeep",
            targets=("target",),
            entries=(EventEntry("damage", "actor", "target", {"amount": 3}, ""),),
            time_cost_seconds=0,
        )
        self._observe("hostile:1:0", log, field)
        record = session_observations("hostile:1:0")[0]
        self.assertEqual(record.action_key, "combat_upkeep")
        self.assertEqual(record.magnitudes, (("key:target", -3.0),))

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_a_large_group_is_summarized_to_bounded_recipients(self):
        actor = FakeEntity("actor")
        others = [FakeEntity(f"target-{index}") for index in range(12)]
        field = _field(actor, *others)
        log = EventLog(
            actor="actor",
            skill_key="t_sweep",
            targets=tuple(other.key for other in others),
            entries=tuple(
                EventEntry("damage", "actor", other.key, {"amount": 2}, "")
                for other in others
            ),
            time_cost_seconds=0,
        )
        self._observe("hostile:1:0", log, field)
        record = session_observations("hostile:1:0")[0]
        self.assertEqual(len(record.recipient_ids), MAX_RECORD_RECIPIENTS)
        self.assertEqual(len(record.magnitudes), MAX_RECORD_RECIPIENTS)


class ObservationRoundIntegrationTests(EvenniaTestCase):
    """The production round loop records its settled actions."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            extra={"skills": {MEM_STRIKE.key: MEM_STRIKE}},
        )
        super().setUp()
        clear_session_memory()
        self.addCleanup(clear_session_memory)

    @covers_requirement(
        "monster-ai-observation-memory::resolved-observations-are-compact-and-bounded"
    )
    def test_run_round_records_the_settled_skill(self):
        monster = create_object(Monster, key="memory-monster")
        monster.threat_tier = "mid"
        monster.apply_monster_tier()
        monster.traits.hp.current = monster.traits.hp.max
        monster.traits.atk_phys.base = 200
        monster.traits.atk_phys.current = 200
        monster.db.skills = {"active": [MEM_STRIKE.key], "passive": []}
        target = create_object(PlayerCharacter, key="memory-target")
        target.race = "human"
        target.apply_race_baseline()
        field = Battlefield(
            {
                "monsters": frozenset({str(monster.key)}),
                "party": frozenset({str(target.key)}),
            },
            {str(monster.key): monster, str(target.key): target},
        )

        def provider(entity, battlefield):
            if entity.key != monster.key:
                return None
            return ActionRequest(
                actor=entity,
                skill_key=MEM_STRIKE.key,
                targets=[target],
                context=BattlefieldActionContext(battlefield),
            )

        with self.captureOnCommitCallbacks(execute=True):
            run_round(
                field,
                provider,
                decision_scope_base=ExecutionScopeBase("hostile:1:0", 1),
            )
        committed = session_observations("hostile:1:0")
        self.assertEqual([record.action_key for record in committed], [MEM_STRIKE.key])
        record = committed[0]
        self.assertEqual(record.source_faction, "monsters")
        self.assertEqual(record.round_index, 1)
        self.assertIn(f"dbref:{target.pk}", record.recipient_ids)
        self.assertTrue(any(magnitude < 0 for _, magnitude in record.magnitudes))

    @covers_requirement(
        "monster-ai-observation-memory::same-round-observations-remain-transaction-local"
    )
    def test_a_sessionless_round_records_nothing(self):
        actor = FakeEntity("actor")
        enemy = FakeEntity("enemy")
        field = _field(actor, enemy)

        def provider(entity, battlefield):
            return ActionRequest(
                actor=entity,
                skill_key=MEM_STRIKE.key,
                targets=[enemy],
                context=BattlefieldActionContext(battlefield),
            )

        with patch(
            "world.rules.combat.rounds.tick_buffs", return_value=()
        ), patch("world.rules.combat.rounds.decay_tick"), patch(
            "world.rules.combat.rounds.climax_settlement_action",
            return_value=None,
        ), self.captureOnCommitCallbacks(execute=True):
            run_round(field, provider)
        self.assertEqual(session_observations(""), ())
