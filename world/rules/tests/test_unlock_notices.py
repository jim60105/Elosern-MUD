"""Session-scoped party unlock marks, delivery, and the copied context snapshot.

Covers ``world/rules/unlock_notices.py`` and the delivery owners: a committed
practice grant names its learner, marks every session of the commander's
account, and writes no persistent state; clearing a member's dot keeps her
recent set; a reconnect starts empty; possession neither clears nor duplicates
the marks and still receives the line.

The added ``party-unlock-notices`` requirements' canonical IDs:

- ``party-unlock-notices::unlocks-mark-the-learner-as-unread-for-the-session``
- ``party-unlock-notices::opening-a-member-s-skills-clears-only-the-unread-mark``
- ``party-unlock-notices::unread-state-never-outlives-the-session``

Data-independent: every skill and race is a synthetic kit row.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat_session.rounds import _deliver_after_commit
from world.rules.party import join_party
from world.rules.possession import enter_possession
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    grant_skill_practice_xp,
    reset_practice_dedupe,
)
from world.rules.time_skip import render_skip_summary
from world.rules.unlock_notices import (
    PRACTICE_UNLOCK_EVENT,
    MemberUnlocks,
    UnlockNotice,
    deliver_unlocks,
    mark_unlocks_seen,
    notices_from_events,
    record_unlocks,
    unlock_flags,
)
from world.skills.registry import validate_prerequisite_graph
from web.webclient.presentation.ingress import build_presentation_context

from ._combat_session_helpers import (
    _race_key,
    live_skill_registry,
    open_synthetic_scope,
    synth_lineage_tree,
)
from .combat_fixtures import grant_lineage

TREE = synth_lineage_tree()
# The synthetic tree's sprout->branch edge: branch becomes usable at sprout
# level 3, so a grant at one XP below that level crosses it.
_PARENT = "t_tree_sprout"
_CHILD = "t_tree_branch"
_UNLOCK_LEVEL = 3


class _FakeSession:
    """A second connection's session stand-in: only ``ndb`` and ``msg``."""

    def __init__(self):
        self.ndb = SimpleNamespace()
        self.messages: list[str] = []

    def msg(self, text=None, **kwargs):
        self.messages.append(text)


class UnlockNoticeTests(EvenniaTest):
    """A commander, two companions, and the account's one live session."""

    def setUp(self):
        reset_practice_dedupe()
        open_synthetic_scope(
            self,
            "skills",
            "buffs",
            "elements",
            "sexual_acts",
            "races",
            "subraces",
            "static_tiers",
            extra={"skills": TREE},
        )
        validate_prerequisite_graph(live_skill_registry())
        super().setUp()
        self.commander = self.char1
        self.commander.race = _race_key()
        self.commander.apply_race_baseline()
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        for entity in (self.commander, self.aila, self.kahn):
            grant_lineage(entity, [_CHILD])
            self._freeze_regen(entity)
        self.session.data_out = MagicMock()

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room1, home=self.room1)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.mp.base = 20
        npc.traits.mp.current = 20
        npc.traits.magic_power.base = 30
        join_party(npc, self.commander)
        return npc

    def _freeze_regen(self, entity):
        for gauge_key in ("hp", "mp", "sp"):
            gauge = getattr(entity.traits, gauge_key, None)
            if gauge is not None:
                gauge.rate = 0

    def _near_edge(self, entity):
        proficiency = dict(entity.db.skill_proficiency or {})
        proficiency[_PARENT] = SKILL_PROFICIENCY_XP_PER_LEVEL * _UNLOCK_LEVEL - 1
        entity.db.skill_proficiency = proficiency

    def _unlock(self, entity):
        sink: list[UnlockNotice] = []
        self.assertTrue(
            grant_skill_practice_xp(entity, _PARENT, unlocks_out=sink)
        )
        return sink

    def _notice(self, member):
        return UnlockNotice(
            member.pk,
            member.key,
            _CHILD,
            f"{member.key} 學會了 {TREE[_CHILD].label}",
        )

    @covers_requirement(
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification",
        "party-unlock-notices::unlocks-mark-the-learner-as-unread-for-the-session",
    )
    def test_a_companion_unlock_names_the_companion_and_marks_her(self):
        self._near_edge(self.aila)
        sink = self._unlock(self.aila)
        self.assertEqual(len(sink), 1)
        notice = sink[0]
        self.assertEqual(notice.learner_id, self.aila.pk)
        self.assertEqual(notice.skill_key, _CHILD)
        self.assertEqual(
            notice.line, f"{self.aila.key} 學會了 {TREE[_CHILD].label}"
        )
        with self.captureOnCommitCallbacks(execute=True):
            deliver_unlocks(self.commander, sink)
        # One line, to the account's live session.
        self.session.data_out.assert_called_once_with(text=notice.line)
        self.assertEqual(
            unlock_flags(self.session)[self.aila.pk],
            MemberUnlocks(True, frozenset({_CHILD})),
        )

    @covers_requirement(
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification"
    )
    def test_the_commander_keeps_the_existing_unlock_line(self):
        self._near_edge(self.commander)
        sink = self._unlock(self.commander)
        self.assertEqual(
            [notice.line for notice in sink],
            [f"新技能可用：{TREE[_CHILD].label}"],
        )

    @covers_requirement(
        "party-unlock-notices::unlocks-mark-the-learner-as-unread-for-the-session"
    )
    def test_marks_land_on_every_session_of_the_account(self):
        second = _FakeSession()
        with patch.object(
            self.account.sessions, "all", return_value=[self.session, second]
        ):
            record_unlocks(self.commander, [self._notice(self.aila)])
        for session in (self.session, second):
            self.assertEqual(
                unlock_flags(session)[self.aila.pk],
                MemberUnlocks(True, frozenset({_CHILD})),
            )

    @covers_requirement(
        "party-unlock-notices::opening-a-member-s-skills-clears-only-the-unread-mark"
    )
    def test_clearing_keeps_the_recent_set(self):
        record_unlocks(self.commander, [self._notice(self.aila)])
        mark_unlocks_seen(self.session, self.aila.pk)
        self.assertEqual(
            unlock_flags(self.session)[self.aila.pk],
            MemberUnlocks(False, frozenset({_CHILD})),
        )

    @covers_requirement(
        "party-unlock-notices::unread-state-never-outlives-the-session"
    )
    def test_a_new_session_has_no_marks(self):
        record_unlocks(self.commander, [self._notice(self.aila)])
        self.assertTrue(unlock_flags(self.session)[self.aila.pk].unread)
        # A reconnect is a new session: ndb state never outlives the old one.
        self.assertEqual(dict(unlock_flags(_FakeSession())), {})

    @covers_requirement(
        "party-unlock-notices::unread-state-never-outlives-the-session"
    )
    def test_possession_keeps_the_marks(self):
        record_unlocks(self.commander, [self._notice(self.kahn)])
        enter_possession(self.commander, self.aila)
        self.assertIs(self.session.puppet, self.aila)
        self.assertEqual(
            unlock_flags(self.session)[self.kahn.pk],
            MemberUnlocks(True, frozenset({_CHILD})),
        )

    def test_delivery_during_possession_reaches_the_account(self):
        # The possessed commander body is unpuppeted, so its account link is
        # gone; the helper must resolve the account's sessions through the
        # possession mirror instead of messaging the body.
        enter_possession(self.commander, self.aila)
        notice = self._notice(self.aila)
        with self.captureOnCommitCallbacks(execute=True):
            deliver_unlocks(self.commander, [notice])
        self.session.data_out.assert_called_with(text=notice.line)
        self.assertEqual(
            unlock_flags(self.session)[self.aila.pk],
            MemberUnlocks(True, frozenset({_CHILD})),
        )

    @covers_requirement(
        "party-unlock-notices::unlocks-mark-the-learner-as-unread-for-the-session",
        "party-unlock-notices::unread-state-never-outlives-the-session",
    )
    def test_nothing_persistent_is_written(self):
        def attributes(entity):
            return {attr.key: attr.value for attr in entity.attributes.all()}

        before = (attributes(self.commander), attributes(self.aila))
        with self.captureOnCommitCallbacks(execute=True):
            deliver_unlocks(self.commander, [self._notice(self.aila)])
        self.assertEqual(
            (attributes(self.commander), attributes(self.aila)), before
        )

    @covers_requirement(
        "skill-lineage-panel::a-newly-usable-skill-pushes-one-derived-unlock-notification"
    )
    def test_booked_study_emits_one_unlock_event_and_the_summary_renders_it(self):
        self._near_edge(self.aila)
        self.aila.db.practice_booking = _PARENT
        events = WorldClock().advance(
            3600 * 5, AdvanceSource.SKIP, (self.commander, self.aila)
        )
        unlocks = [
            event for event in events if event.kind == PRACTICE_UNLOCK_EVENT
        ]
        self.assertEqual(len(unlocks), 1)
        self.assertEqual(unlocks[0].payload["learner_id"], self.aila.pk)
        self.assertEqual(unlocks[0].payload["skill_key"], _CHILD)
        self.assertIsNone(self.aila.db.practice_booking)
        notices = notices_from_events(events)
        self.assertEqual(len(notices), 1)
        self.assertEqual(
            notices[0].line,
            f"{self.aila.key} 學會了 {TREE[_CHILD].label}",
        )
        summary = render_skip_summary(3600 * 5, events)
        self.assertEqual(summary.count(notices[0].line), 1)
        # The summary already carried the line; the marks ride along silently.
        with self.captureOnCommitCallbacks(execute=True):
            deliver_unlocks(self.commander, notices, announce=False)
        self.session.data_out.assert_not_called()
        self.assertEqual(
            unlock_flags(self.session)[self.aila.pk],
            MemberUnlocks(True, frozenset({_CHILD})),
        )

    @covers_requirement(
        "party-unlock-notices::unlocks-mark-the-learner-as-unread-for-the-session"
    )
    def test_a_rolled_back_advance_emits_no_unlock_event_and_marks_nothing(self):
        self._near_edge(self.aila)
        self.aila.db.practice_booking = _PARENT
        skills_before = dict(self.aila.db.skills)
        proficiency_before = dict(self.aila.db.skill_proficiency)
        with patch(
            "world.rules.clock._settle_boundary_stages",
            side_effect=RuntimeError("injected"),
        ):
            with self.assertRaises(RuntimeError):
                WorldClock().advance(
                    3600 * 5, AdvanceSource.SKIP, (self.commander, self.aila)
                )
        # The advance restored the grant and the award; no owner ever saw the
        # event list, so no line and no mark exist.
        self.assertEqual(dict(self.aila.db.skills), skills_before)
        self.assertEqual(
            dict(self.aila.db.skill_proficiency), proficiency_before
        )
        self.assertEqual(dict(unlock_flags(self.session)), {})

    def test_combat_delivery_sends_one_line_and_records_the_mark(self):
        notice = self._notice(self.aila)
        with self.captureOnCommitCallbacks(execute=True):
            _deliver_after_commit(self.commander, (notice.line, notice))
        # The rendered string duplicates the notice's own line: exactly one
        # delivery, plus the mark.
        self.session.data_out.assert_called_once_with(text=notice.line)
        self.assertEqual(
            unlock_flags(self.session)[self.aila.pk],
            MemberUnlocks(True, frozenset({_CHILD})),
        )

    def test_possession_marks_every_session_of_the_account(self):
        enter_possession(self.commander, self.aila)
        second = _FakeSession()
        notice = self._notice(self.aila)
        with (
            patch.object(
                self.account.sessions,
                "all",
                return_value=[self.session, second],
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            deliver_unlocks(self.commander, [notice])
        for session in (self.session, second):
            self.assertEqual(
                unlock_flags(session)[self.aila.pk],
                MemberUnlocks(True, frozenset({_CHILD})),
            )
        self.assertEqual(second.messages, [notice.line])

    def test_an_enclosing_rollback_leaves_no_mark(self):
        from django.db import transaction

        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    deliver_unlocks(self.commander, [self._notice(self.aila)])
                    transaction.set_rollback(True)
            except Exception:  # observability: ignore R2: the test's own rollback is the assertion
                pass
        self.assertEqual(dict(unlock_flags(self.session)), {})
        self.session.data_out.assert_not_called()

    def test_combat_delivery_keeps_a_second_identical_line(self):
        notice = self._notice(self.aila)
        with self.captureOnCommitCallbacks(execute=True):
            _deliver_after_commit(
                self.commander, (notice.line, notice, notice.line)
            )
        # One occurrence is the notice's own staged line; the other is a
        # separately staged line that happens to read the same.
        self.assertEqual(self.session.data_out.call_count, 2)

    def test_the_context_snapshot_is_a_detached_immutable_copy(self):
        record_unlocks(self.commander, [self._notice(self.aila)])
        context = build_presentation_context(self.session, self.commander)
        self.assertEqual(
            context.unlocks[self.aila.pk],
            MemberUnlocks(True, frozenset({_CHILD})),
        )
        mark_unlocks_seen(self.session, self.aila.pk)
        self.assertTrue(context.unlocks[self.aila.pk].unread)
        with self.assertRaises(TypeError):
            context.unlocks[self.aila.pk] = MemberUnlocks(False, frozenset())
