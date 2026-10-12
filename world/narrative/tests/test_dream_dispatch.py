"""Behavior tests for durable dream-dispatch work records.

Everything here is deterministic and offline: synthetic actors, a fixed clock,
no model or image service, and no fabricated success. The tests exercise the
real confirmation transaction, the real work-record state machine and the real
fencing/recovery path; the model boundary is never reached, which is exactly the
claim ("confirmation and work management never advance the clock or await a
model") that must be proved rather than asserted.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from world.narrative import dispatch
from world.narrative.authoring import (
    DirectionValidationError,
    confirm_draft,
    requirement_version_for,
    reviewed_version_matches,
    save_draft,
    stamp_shown_requirements,
    validate_direction,
)
from world.narrative.models import DreamDispatch
from world.rules.clock import get_world_clock


def new_story_direction(**overrides):
    """A complete, valid new-story direction; overrides replace whole fields."""
    direction = {
        "summary": "合成夢境方向：在南門遇見一個女孩，帶她找媽媽。",
        "themes": ["合成主題"],
        "atmosphere": ["合成氛圍"],
        "participants": [],
        "emphasis": ["合成重點"],
        "exclusions": [],
        "kind": "new_story",
        "thread_id": None,
        "effects": [],
        "revisions": [],
    }
    direction.update(overrides)
    return direction


class DreamDispatchTestCase(EvenniaTest):
    """A synthetic owner, a fixed clock and a registered pump probe."""

    def setUp(self):
        super().setUp()
        self.owner = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="Synthetic dispatch owner",
            location=self.room1,
        )
        self.clock = get_world_clock()
        self.clock._persist(100)
        self.clock.tick = 100
        self.hints: list[str] = []
        dispatch.register_pump(lambda: self.hints.append("hint"))
        self.addCleanup(dispatch.register_pump, None)

    @property
    def owner_id(self) -> str:
        return str(self.owner.pk)

    def _draft(self, **overrides):
        return save_draft(
            owner_id=self.owner_id,
            direction=new_story_direction(**overrides),
            tick=100,
        )

    def _confirm(self, draft):
        with self.captureOnCommitCallbacks(execute=True):
            return confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)


class WorkIdentityTests(DreamDispatchTestCase):
    def test_one_work_record_per_confirmed_version(self):
        draft = self._draft()
        request = self._confirm(draft)
        works = list(DreamDispatch.objects.all())
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0].submission_key, request.submission_key)
        self.assertEqual(works[0].state, dispatch.STATE_QUEUED)
        self.assertEqual(works[0].owner_id, self.owner_id)
        self.assertEqual(works[0].dispatch_id, dispatch.dispatch_id_for(request.submission_key))

        # A duplicate confirmation replays the same request and never adds work.
        again = self._confirm(draft)
        self.assertEqual(again.pk, request.pk)
        self.assertEqual(DreamDispatch.objects.count(), 1)

        # A separately confirmed, edited version is a distinct source and work.
        draft = save_draft(
            owner_id=self.owner_id,
            direction=new_story_direction(summary="合成第二版方向：在北門遇見一個商人。"),
            tick=100,
            draft_id=draft.draft_id,
        )
        second = self._confirm(draft)
        self.assertNotEqual(second.submission_key, request.submission_key)
        self.assertEqual(DreamDispatch.objects.count(), 2)
        keys = {work.submission_key for work in DreamDispatch.objects.all()}
        self.assertEqual(keys, {request.submission_key, second.submission_key})

    def test_confirmation_hint_fires_only_after_commit(self):
        draft = self._draft()
        with self.captureOnCommitCallbacks(execute=True):
            confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
            # The hint is a committed wake-up: the callback is registered, but
            # the pump has not been woken while the transaction is still open.
            self.assertEqual(self.hints, [])
        # It fires exactly once, on commit.
        self.assertEqual(self.hints, ["hint"])

    def test_lost_hint_leaves_queued_work_discoverable(self):
        dispatch.register_pump(None)
        draft = self._draft()
        with self.captureOnCommitCallbacks(execute=True):
            request = confirm_draft(
                draft_id=draft.draft_id, owner_id=self.owner_id, tick=100
            )
        self.assertFalse(dispatch.pump_registered())
        # No hint was delivered, yet startup finds the saved queued work.
        considered = dispatch.next_considered()
        self.assertEqual([work.submission_key for work in considered], [request.submission_key])

    def test_confirmation_never_advances_the_clock(self):
        before = int(get_world_clock().tick)
        draft = self._draft()
        self._confirm(draft)
        self.assertEqual(int(get_world_clock().tick), before)


class ClaimAndFenceTests(DreamDispatchTestCase):
    def setUp(self):
        super().setUp()
        self.draft = self._draft()
        self.request = self._confirm(self.draft)
        self.work = dispatch.find_by_submission(self.request.submission_key)

    def test_pending_stage_sequence_follows_checkpoints(self):
        self.assertEqual(dispatch.pending_stage(self.work), dispatch.STAGE_STORY)
        self.assertEqual(dispatch.required_capability(self.work), dispatch.CAPABILITY_STORY)

        claimed = dispatch.claim(self.work, process="p1")
        row, token = claimed
        self.assertEqual(row.state, dispatch.STATE_GENERATING_STORY)
        self.assertEqual(int(row.attempts), 1)

        self.assertTrue(
            dispatch.checkpoint_story(
                row,
                token,
                checkpoint={
                    "snapshot_id": "snap",
                    "scene_required": True,
                    "proposal": {"kind": "quest_seed"},
                },
                tick=100,
            )
        )
        row.refresh_from_db()
        self.assertEqual(row.state, dispatch.STATE_GENERATING_SCENE)
        self.assertEqual(row.stage, dispatch.STAGE_SCENE)

        self.assertTrue(
            dispatch.checkpoint_scene(row, token, checkpoint={"context": {}, "blueprint": {}})
        )
        row.refresh_from_db()
        self.assertEqual(row.stage, dispatch.STAGE_PUBLISH)
        self.assertEqual(dispatch.required_capability(row), None)

    def test_non_scene_story_checkpoint_goes_straight_to_publication(self):
        _, token = dispatch.claim(self.work, process="p1")
        self.assertTrue(
            dispatch.checkpoint_story(
                self.work,
                token,
                checkpoint={"snapshot_id": "snap", "scene_required": False},
            )
        )
        self.work.refresh_from_db()
        self.assertEqual(self.work.stage, dispatch.STAGE_PUBLISH)

    def test_stale_token_cannot_checkpoint_or_settle(self):
        _, first = dispatch.claim(self.work, process="p1")
        _, second = dispatch.claim(self.work, process="p1")
        self.assertNotEqual(first, second)
        self.assertFalse(
            dispatch.checkpoint_story(
                self.work, first, checkpoint={"snapshot_id": "old", "scene_required": False}
            )
        )
        self.assertFalse(
            dispatch.mark_failed(self.work, first, dispatch.REASON_EXECUTION_FAILED)
        )
        self.work.refresh_from_db()
        self.assertIsNone(self.work.story_checkpoint)
        self.assertEqual(self.work.state, dispatch.STATE_GENERATING_STORY)
        self.assertTrue(
            dispatch.checkpoint_story(
                self.work, second, checkpoint={"snapshot_id": "new", "scene_required": False}
            )
        )

    def test_arranged_requires_durable_references_and_is_terminal(self):
        _, token = dispatch.claim(self.work, process="p1")
        dispatch.checkpoint_story(
            self.work, token, checkpoint={"snapshot_id": "snap", "scene_required": False}
        )
        self.assertTrue(
            dispatch.mark_arranged(
                self.work,
                token,
                decision_id="dec_1",
                thread_id="story:1",
                beat_id="beat:dec_1",
                package_id="",
                tick=100,
            )
        )
        self.work.refresh_from_db()
        self.assertEqual(self.work.state, dispatch.STATE_ARRANGED)
        self.assertEqual(self.work.decision_id, "dec_1")
        self.assertEqual(dispatch.pending_stage(self.work), None)
        self.assertEqual(dispatch.claim(self.work, process="p1"), None)
        self.assertEqual(dispatch.next_considered(), [])

    def test_terminal_failure_is_not_rerolled(self):
        _, token = dispatch.claim(self.work, process="p1")
        self.assertTrue(
            dispatch.mark_failed(self.work, token, dispatch.REASON_INVALID_OUTPUT)
        )
        self.work.refresh_from_db()
        self.assertEqual(self.work.state, dispatch.STATE_FAILED)
        self.assertEqual(self.work.reason_code, dispatch.REASON_INVALID_OUTPUT)
        self.assertEqual(dispatch.claim(self.work, process="p1"), None)
        # A later pump pass cannot silently regenerate the same source.
        self.assertEqual(dispatch.next_considered(), [])

    def test_unknown_reason_is_bounded_to_a_known_code(self):
        _, token = dispatch.claim(self.work, process="p1")
        self.assertTrue(dispatch.mark_failed(self.work, token, "<script>"))
        self.work.refresh_from_db()
        self.assertEqual(self.work.reason_code, dispatch.REASON_EXECUTION_FAILED)

    def test_waiting_does_not_block_other_eligible_work(self):
        other_draft = save_draft(
            owner_id=self.owner_id,
            direction=new_story_direction(summary="合成其他方向：在碼頭遇見一位船夫。"),
            tick=100,
        )
        other = dispatch.find_by_submission(self._confirm(other_draft).submission_key)
        self.assertTrue(dispatch.mark_waiting(self.work, tick=100))
        self.work.refresh_from_db()
        self.assertEqual(self.work.state, dispatch.STATE_WAITING_SERVICE)
        # The waiting record is still considered (so a later notification can
        # re-evaluate it) and its later sibling was never blocked.
        considered = [work.dispatch_id for work in dispatch.next_considered()]
        self.assertEqual(considered, [self.work.dispatch_id, other.dispatch_id])
        self.assertEqual(dispatch.consider_waiting(), 1)
        self.work.refresh_from_db()
        self.assertEqual(self.work.state, dispatch.STATE_QUEUED)


class RecoveryTests(DreamDispatchTestCase):
    def setUp(self):
        super().setUp()
        self.draft = self._draft()
        self.request = self._confirm(self.draft)
        self.work = dispatch.find_by_submission(self.request.submission_key)

    def test_recovery_fences_a_previous_process_claim(self):
        _, stale_token = dispatch.claim(self.work, process="previous-process")
        self.assertEqual(dispatch.recover_interrupted(process="current-process"), [self.work.dispatch_id])
        self.work.refresh_from_db()
        self.assertEqual(self.work.state, dispatch.STATE_QUEUED)
        self.assertEqual(self.work.execution_token, "")
        self.assertEqual(self.work.claimed_by, "current-process")
        # The interrupted execution's late callback mutates nothing.
        self.assertFalse(
            dispatch.checkpoint_story(
                self.work, stale_token, checkpoint={"snapshot_id": "late"}
            )
        )
        self.work.refresh_from_db()
        self.assertIsNone(self.work.story_checkpoint)

    def test_recovery_reuses_saved_checkpoints(self):
        _, token = dispatch.claim(self.work, process="previous-process")
        dispatch.checkpoint_story(
            self.work,
            token,
            checkpoint={"snapshot_id": "kept", "scene_required": True},
            tick=100,
        )
        dispatch.recover_interrupted(process="current-process")
        self.work.refresh_from_db()
        self.assertEqual(self.work.story_checkpoint["snapshot_id"], "kept")
        # Only the still-uncommitted stage remains to run.
        self.assertEqual(dispatch.pending_stage(self.work), dispatch.STAGE_SCENE)

    def test_a_live_claim_is_never_recovered(self):
        _, token = dispatch.claim(self.work, process=dispatch.process_identity())
        self.assertEqual(dispatch.recover_interrupted(), [])
        self.work.refresh_from_db()
        self.assertEqual(self.work.state, dispatch.STATE_GENERATING_STORY)
        self.assertEqual(self.work.execution_token, token)

    def test_shutdown_invalidates_unfinished_callback_ownership(self):
        _, token = dispatch.claim(self.work, process=dispatch.process_identity())
        self.assertEqual(dispatch.fence_all(), 1)
        self.work.refresh_from_db()
        self.assertEqual(self.work.execution_token, "")
        self.assertFalse(dispatch.mark_arranged(
            self.work, token, decision_id="d", thread_id="t", beat_id="b"
        ))


class PersistenceTests(DreamDispatchTestCase):
    """The work row is the authoritative state across a process boundary."""

    def test_the_session_path_refuses_an_unreviewed_requirement_change(self):
        # A caller that bypasses the surface gate cannot replace a draft's shown
        # requirements with a summary and silently drop them.
        from world.narrative import dream_session as lifecycle
        from world.narrative.authoring import DirectionValidationError, get_draft
        from world.narrative.dream_session import get_session
        from world.narrative.models import CreativeRequest

        requirements = [{"kind": "place", "text": "南門"}]
        session = lifecycle.open_session(self.owner_id, tick=100)
        lifecycle.preserve_draft(
            session.session_id,
            self.owner_id,
            {
                "kind": "new_story",
                "summary": "合成方向",
                "requirements": requirements,
            },
            tick=100,
        )
        handle = get_session(session.session_id, self.owner_id).draft_id
        shown = get_draft(handle, self.owner_id).direction["requirement_version"]
        self.assertTrue(shown)

        with self.assertRaises(DirectionValidationError) as failure:
            lifecycle.confirm_session(
                session.session_id,
                self.owner_id,
                direction={"kind": "new_story", "summary": "改了摘要"},
                tick=100,
            )
        self.assertIn("stale_requirements", failure.exception.reason_codes)
        self.assertEqual(CreativeRequest.objects.count(), 0)
        self.assertEqual(DreamDispatch.objects.count(), 0)
        # The shown version is untouched, and reviewing exactly it confirms.
        self.assertEqual(
            get_draft(handle, self.owner_id).direction["requirements"], requirements
        )
        with self.captureOnCommitCallbacks(execute=True):
            lifecycle.confirm_session(
                session.session_id,
                self.owner_id,
                direction={
                    "kind": "new_story",
                    "summary": "合成方向",
                    "requirements": requirements,
                    "requirement_version": shown,
                },
                tick=100,
            )
        self.assertEqual(DreamDispatch.objects.count(), 1)

    def test_session_confirmation_commits_request_work_and_closure_together(self):
        # The delta's "work persistence fails" scenario on the session path: a
        # closure that fails after the request was written must leave no
        # confirmed request, no work record, an open session and no pump hint.
        from unittest.mock import patch

        from world.narrative import dream_session as lifecycle
        from world.narrative.dream_session import STATE_OPEN, get_session
        from world.narrative.models import CreativeRequest

        session = lifecycle.open_session(self.owner_id, tick=100)
        lifecycle.preserve_draft(
            session.session_id,
            self.owner_id,
            {"kind": "new_story", "summary": "合成方向"},
            tick=100,
        )
        with patch(
            "world.narrative.dream_session._locked_session",
            side_effect=RuntimeError("synthetic closure failure"),
        ):
            with self.assertRaises(RuntimeError):
                with self.captureOnCommitCallbacks(execute=True):
                    lifecycle.confirm_session(
                        session.session_id, self.owner_id, tick=100
                    )
        self.assertEqual(CreativeRequest.objects.count(), 0)
        self.assertEqual(DreamDispatch.objects.count(), 0)
        self.assertEqual(
            get_session(session.session_id, self.owner_id).state, STATE_OPEN
        )
        self.assertEqual(self.hints, [])

    def test_saved_reload_preserves_state_stage_token_and_checkpoints(self):
        draft = self._draft()
        request = self._confirm(draft)
        work = dispatch.find_by_submission(request.submission_key)
        _, token = dispatch.claim(work, process="p1", tick=100)
        dispatch.checkpoint_story(
            work,
            token,
            checkpoint={"snapshot_id": "kept", "scene_required": True, "proposal": {}},
            tick=100,
        )

        # A fresh ORM instance from a fresh query is what a restarted process
        # sees: identity, state, stage, fence and checkpoint all survive.
        reloaded = dispatch.find_by_submission(request.submission_key)
        self.assertNotEqual(reloaded.pk, None)
        self.assertEqual(reloaded.dispatch_id, work.dispatch_id)
        self.assertEqual(reloaded.state, dispatch.STATE_GENERATING_SCENE)
        self.assertEqual(reloaded.stage, dispatch.STAGE_SCENE)
        self.assertEqual(reloaded.execution_token, token)
        self.assertEqual(reloaded.claimed_by, "p1")
        self.assertEqual(reloaded.story_checkpoint["snapshot_id"], "kept")
        self.assertEqual(reloaded.request_version, int(request.version))
        self.assertEqual(reloaded.source_key, request.submission_key)

    def test_startup_creates_no_work_for_a_request_without_one(self):
        draft = self._draft()
        request = self._confirm(draft)
        work = dispatch.find_by_submission(request.submission_key)
        # Simulate a durable request that carries no work record at all.
        work.delete()
        self.assertEqual(dispatch.recover_interrupted(), [])
        self.assertEqual(dispatch.next_considered(), [])
        # No legacy scanner turned the historical request into new work.
        self.assertEqual(DreamDispatch.objects.count(), 0)

class StatusMessageTests(DreamDispatchTestCase):
    """Every durable state and reason says something distinct and truthful."""

    def setUp(self):
        super().setUp()
        self._counter = 0

    def _work(self, **overrides):
        self._counter += 1
        key = f"synthetic-status:{self._counter}"
        defaults = {
            "dispatch_id": dispatch.dispatch_id_for(key),
            "submission_key": key,
            "owner_id": self.owner_id,
        }
        defaults.update(overrides)
        return DreamDispatch.objects.create(**defaults)

    def test_no_work_says_nothing(self):
        from world.narrative import dispatch_status

        self.assertEqual(dispatch_status.status_message(None), "")
        self.assertEqual(dispatch_status.owner_message(self.owner_id), "")

    def test_preparing_waiting_and_arranged_are_distinct(self):
        from world.narrative import dispatch_status

        preparing = dispatch_status.status_message(
            self._work(state=dispatch.STATE_QUEUED)
        )
        waiting = dispatch_status.status_message(
            self._work(state=dispatch.STATE_WAITING_SERVICE)
        )
        arranged = dispatch_status.status_message(
            self._work(state=dispatch.STATE_ARRANGED)
        )
        self.assertEqual(len({preparing, waiting, arranged}), 3)
        # Only a durable arranged record may claim an executable arrangement,
        # and even then it claims nothing about the encounter itself.
        self.assertIn("成局", preparing)
        self.assertIn("服務", waiting)
        self.assertIn("安排", arranged)

    def test_each_terminal_reason_has_its_own_actionable_message(self):
        from world.narrative import dispatch_status

        reasons = sorted(dispatch.REASONS - {dispatch.REASON_NO_CAPABILITY})
        messages = {
            reason: dispatch_status.status_message(
                self._work(state=dispatch.STATE_FAILED, reason_code=reason)
            )
            for reason in reasons
        }
        self.assertNotIn("", messages.values())
        self.assertEqual(len(set(messages.values())), len(messages))
        for reason, message in messages.items():
            with self.subTest(reason=reason):
                # Spoiler safety: no role, place or outcome is disclosed and no
                # message claims a completed encounter.
                self.assertNotIn("女神", message)
                self.assertNotIn("女孩", message)
                self.assertIn("夢境方向", message)
        # An unknown code never renders raw or empty: it falls back to a bounded
        # message rather than leaking the reason code to the player.
        self.assertEqual(
            dispatch_status.status_message(
                self._work(state=dispatch.STATE_FAILED, reason_code="<script>")
            ),
            dispatch_status.MESSAGE_FAILED,
        )

    def test_delivery_uses_the_current_actor_and_reports_nothing_when_empty(self):
        from unittest.mock import Mock

        from world.narrative import dispatch_status

        silent = create_object("typeclasses.characters.PlayerCharacter", key="Quiet owner")
        silent.msg = Mock()
        self.assertEqual(dispatch_status.deliver_status(silent), "")
        silent.msg.assert_not_called()

        self._work(state=dispatch.STATE_QUEUED)
        self.owner.msg = Mock()
        delivered = dispatch_status.deliver_status(self.owner)
        self.assertIn("準備中", delivered)
        self.owner.msg.assert_called_once_with(delivered)


class RequirementsContractTests(DreamDispatchTestCase):
    def test_bounded_requirements_are_normalized_and_versioned(self):
        direction = new_story_direction(
            requirements=[
                {"kind": "place", "text": "南門"},
                {"kind": "new_character", "text": "一個女孩"},
                {"kind": "private_commission", "text": "帶她找媽媽"},
            ],
            requirement_version="draft:v1",
        )
        result = validate_direction(direction, owner_id=self.owner_id)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.direction["requirements"]), 3)
        self.assertEqual(result.direction["requirement_version"], "draft:v1")

    def test_requirements_reject_unknown_kind_shape_and_length(self):
        bad_rows = [
            [{"kind": "explode", "text": "南門"}],
            [{"kind": "place", "text": "南門", "extra": "x"}],
            [{"kind": "place", "text": " "}],
            [{"kind": "place", "text": "長" * 201}],
            [{"kind": "place"}] * 9,
        ]
        for rows in bad_rows:
            with self.subTest(rows=rows):
                result = validate_direction(
                    new_story_direction(requirements=rows, requirement_version="draft:v1"),
                    owner_id=self.owner_id,
                )
                self.assertFalse(result.valid)
                self.assertIn("malformed_requirements", result.reason_codes)

    def test_requirements_without_a_version_are_malformed(self):
        result = validate_direction(
            new_story_direction(
                requirements=[{"kind": "place", "text": "南門"}],
                requirement_version=None,
            ),
            owner_id=self.owner_id,
        )
        self.assertFalse(result.valid)
        self.assertIn("malformed_requirements", result.reason_codes)

    def test_requirement_version_is_deterministic_per_shown_version(self):
        draft = self._draft()
        first = requirement_version_for(draft.draft_id, 1)
        self.assertEqual(first, requirement_version_for(draft.draft_id, 1))
        self.assertNotEqual(first, requirement_version_for(draft.draft_id, 2))

    def test_the_longest_legal_version_identity_fits_the_client_bound(self):
        from world.narrative.authoring import MAX_REQUIREMENT_VERSION_LENGTH

        # A session draft's handle is ``dream:<session_id>`` (at most 64 + 6
        # characters), so this is the longest published identity any client can
        # receive; the browser mirror validates the same bound and must never be
        # tighter than the server's own accept bound.
        longest = requirement_version_for("dream:" + "s" * 64, 999999)
        self.assertLessEqual(len(longest), MAX_REQUIREMENT_VERSION_LENGTH)

    def test_the_store_refuses_malformed_rows_and_stores_normalized_ones(self):
        # The store is the one writer of a shown requirement set, and every
        # client renders and echoes those rows back: a malformed row must never
        # be persisted, because no valid panel payload could carry it.
        from world.narrative.models import AuthoringDraft

        for rows in (
            [{"kind": "explode", "text": "南門"}],
            [{"kind": "place", "text": "南門", "extra": "x"}],
            [{"kind": "place", "text": "長" * 201}],
            [{"kind": "place"}],
            [{"kind": "place", "text": "南門"}] * 9,
        ):
            with self.subTest(rows=rows):
                with self.assertRaises(DirectionValidationError) as failure:
                    save_draft(
                        owner_id=self.owner_id,
                        direction=new_story_direction(requirements=rows),
                        tick=100,
                    )
                self.assertIn("malformed_requirements", failure.exception.reason_codes)
        self.assertEqual(AuthoringDraft.objects.count(), 0)

        draft = save_draft(
            owner_id=self.owner_id,
            direction=new_story_direction(
                requirements=[{"kind": "place", "text": "  南門  "}]
            ),
            tick=100,
        )
        self.assertEqual(
            draft.direction["requirements"], [{"kind": "place", "text": "南門"}]
        )


class ShownRequirementTests(DreamDispatchTestCase):
    """Only what the surface actually showed can be frozen at confirmation."""

    def test_the_collaborator_vocabulary_is_the_authoring_contract(self):
        # ``world/ai`` may not import the authoring writer, so the two closed
        # vocabularies are pinned equal here instead: a drift would let the
        # collaborator propose a requirement kind that confirmation can never
        # freeze, silently turning every such direction into a stale review.
        from world.ai import dream as collaborator
        from world.narrative import authoring

        self.assertEqual(
            tuple(sorted(collaborator.REQUIREMENT_KINDS)),
            tuple(sorted(authoring.REQUIREMENT_KINDS)),
        )
        self.assertEqual(collaborator.MAX_REQUIREMENTS, authoring.MAX_REQUIREMENTS)
        self.assertEqual(
            collaborator.MAX_REQUIREMENT_TEXT, authoring.MAX_REQUIREMENT_TEXT
        )

    def _requirement_draft(self):
        return save_draft(
            owner_id=self.owner_id,
            direction=new_story_direction(
                requirements=[{"kind": "place", "text": "南門"}]
            ),
            tick=100,
        )

    def test_stamping_records_the_shown_version_without_advancing_it(self):
        draft = self._requirement_draft()
        # Persisting the version already stamped its identity: a requirement
        # set that was written is one a player can be shown and review.
        self.assertEqual(
            draft.direction["requirement_version"],
            requirement_version_for(draft.draft_id, 1),
        )
        stamped = stamp_shown_requirements(draft)
        self.assertEqual(int(stamped.revision), 1)
        self.assertEqual(
            stamped.direction["requirement_version"],
            requirement_version_for(draft.draft_id, 1),
        )
        # Re-presenting the same shown version is idempotent: no new review.
        again = stamp_shown_requirements(stamped)
        self.assertEqual(int(again.revision), 1)
        self.assertEqual(
            again.direction["requirement_version"],
            stamped.direction["requirement_version"],
        )

    def test_stamping_fills_a_record_written_before_the_contract(self):
        # Defence in depth for a stored requirement set whose identity is
        # absent: re-presenting it fills the identity in place, still without
        # advancing the version.
        draft = self._requirement_draft()
        draft.direction = {**draft.direction, "requirement_version": None}
        draft.save(update_fields=["direction"])
        filled = stamp_shown_requirements(draft)
        self.assertEqual(int(filled.revision), 1)
        self.assertEqual(
            filled.direction["requirement_version"],
            requirement_version_for(draft.draft_id, 1),
        )

    def test_stamping_leaves_a_requirement_free_draft_untouched(self):
        draft = self._draft()
        self.assertIs(stamp_shown_requirements(draft), draft)
        self.assertIsNone(draft.direction.get("requirement_version"))

    def test_saving_a_requirement_bearing_draft_stamps_it_and_stays_idempotent(self):
        direction = new_story_direction(
            requirements=[{"kind": "place", "text": "南門"}]
        )
        draft = save_draft(owner_id=self.owner_id, direction=direction, tick=100)
        self.assertEqual(
            draft.direction["requirement_version"],
            requirement_version_for(draft.draft_id, 1),
        )
        self.assertTrue(
            validate_direction(draft.direction, owner_id=self.owner_id).valid
        )
        # An identical re-save stays the documented no-op, identity included.
        again = save_draft(
            owner_id=self.owner_id,
            direction=direction,
            tick=100,
            draft_id=draft.draft_id,
        )
        self.assertEqual(int(again.revision), 1)
        self.assertEqual(
            again.direction["requirement_version"],
            requirement_version_for(draft.draft_id, 1),
        )
        # A real edit is a genuinely new, separately reviewed version.
        edited = save_draft(
            owner_id=self.owner_id,
            direction=new_story_direction(
                requirements=[{"kind": "place", "text": "北門"}]
            ),
            tick=100,
            draft_id=draft.draft_id,
        )
        self.assertEqual(int(edited.revision), 2)
        self.assertEqual(
            edited.direction["requirement_version"],
            requirement_version_for(draft.draft_id, 2),
        )
        # And that version confirms through the real confirmation transaction.
        with self.captureOnCommitCallbacks(execute=True):
            request = confirm_draft(
                draft_id=draft.draft_id, owner_id=self.owner_id, tick=100
            )
        self.assertEqual(int(request.version), 2)
        self.assertEqual(DreamDispatch.objects.count(), 1)

    def test_review_match_requires_the_exact_shown_version(self):
        draft = stamp_shown_requirements(self._requirement_draft())
        rows = draft.direction["requirements"]
        identity = draft.direction["requirement_version"]
        shown_summary = draft.direction["summary"]
        self.assertTrue(
            reviewed_version_matches(
                {
                    "summary": shown_summary,
                    "requirements": rows,
                    "requirement_version": identity,
                },
                draft=draft,
            )
        )
        # A different identity, different rows, a different direction (the
        # review is bound to the version that was shown, summary included), or a
        # submission that reviewed nothing all refuse; so does requirements the
        # server never showed.
        for rejected in (
            {
                "summary": shown_summary,
                "requirements": rows,
                "requirement_version": "other:v9",
            },
            {
                "summary": shown_summary,
                "requirements": [{"kind": "place", "text": "北門"}],
                "requirement_version": identity,
            },
            {
                "summary": "改了摘要",
                "requirements": rows,
                "requirement_version": identity,
            },
            {"kind": "new_story", "summary": "改了摘要"},
        ):
            with self.subTest(rejected=rejected):
                self.assertFalse(reviewed_version_matches(rejected, draft=draft))
        plain = self._draft()
        self.assertTrue(
            reviewed_version_matches(
                {"kind": "new_story", "summary": "無需求"}, draft=plain
            )
        )
        self.assertFalse(
            reviewed_version_matches(
                {
                    "requirements": [{"kind": "place", "text": "南門"}],
                    "requirement_version": "draft:v1",
                },
                draft=plain,
            )
        )


class UnreviewedRequirementsTests(DreamDispatchTestCase):
    def test_confirmation_refuses_a_stored_requirement_set_without_a_review(self):
        draft = self._draft()
        # The store always stamps a version it persists, so the only way a
        # requirement-bearing record lacks a review is a row written before
        # this contract existed; confirmation must refuse it, never freeze it.
        draft.direction = new_story_direction(
            requirements=[{"kind": "place", "text": "南門"}],
            requirement_version="other-draft:v9",
        )
        draft.save(update_fields=["direction"])
        with self.assertRaises(DirectionValidationError) as failure:
            with self.captureOnCommitCallbacks(execute=True):
                confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        self.assertIn("stale_requirements", failure.exception.reason_codes)
        self.assertEqual(DreamDispatch.objects.count(), 0)
        # A requirement set with no review identity at all is refused one gate
        # earlier, as malformed rather than as stale.
        draft.direction = new_story_direction(
            requirements=[{"kind": "place", "text": "南門"}],
            requirement_version=None,
        )
        draft.save(update_fields=["direction"])
        with self.assertRaises(DirectionValidationError) as malformed:
            confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        self.assertIn("malformed_requirements", malformed.exception.reason_codes)
        self.assertEqual(DreamDispatch.objects.count(), 0)

    def test_confirmation_accepts_the_shown_requirements(self):
        draft = self._draft()
        reviewed = new_story_direction(
            requirements=[{"kind": "place", "text": "南門"}],
            requirement_version=requirement_version_for(draft.draft_id, 2),
        )
        save_draft(owner_id=self.owner_id, direction=reviewed, tick=100, draft_id=draft.draft_id)
        self.assertEqual(int(confirm_draft(
            draft_id=draft.draft_id, owner_id=self.owner_id, tick=100
        ).version), 2)
        self.assertEqual(DreamDispatch.objects.count(), 1)


class DispatchEventTests(DreamDispatchTestCase):
    """Boundary events carry business identity, never player prose.

    Owns the dispatch half of the ``observability-logging`` delta's added
    "Dream dispatch and activation emit correlated boundary events": the
    canonical requirement id is attached when that delta syncs at archive.
    """

    def _capture(self, action):
        """Run ``action`` with the module's facade bindings captured."""
        info: list[tuple[str, dict]] = []
        warn: list[tuple[str, dict]] = []

        def recorder(bucket):
            def record(event, *, context=None, exc=None):
                bucket.append((event, dict(context or {})))

            return record

        with patch.object(dispatch, "log_info", side_effect=recorder(info)), patch.object(
            dispatch, "log_warn", side_effect=recorder(warn)
        ), self.captureOnCommitCallbacks(execute=True):
            result = action()
        return result, info, warn

    def _only(self, info, event):
        self.assertEqual([name for name, _ in info], [event])
        return dict(info)[event]

    def test_confirmation_claim_wait_and_failure_name_the_same_work(self):
        draft = self._draft()
        request, info, warn = self._capture(
            lambda: confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        )
        work = dispatch.find_by_submission(request.submission_key)
        self.assertEqual(warn, [])
        confirmed = self._only(info, "dream_dispatch_confirmed")
        self.assertEqual(confirmed["dispatch"], work.dispatch_id)
        self.assertEqual(confirmed["request"], request.submission_key)
        self.assertEqual(confirmed["owner"], self.owner_id)
        self.assertEqual(confirmed["version"], int(request.version))
        self.assertEqual(confirmed["work_state"], dispatch.STATE_QUEUED)
        self.assertEqual(confirmed["tick"], 100)

        claimed_result, info, _ = self._capture(
            lambda: dispatch.claim(work, process="p1", tick=101)
        )
        claimed, token = claimed_result
        self.assertTrue(token)
        claim_event = self._only(info, "dream_dispatch_claimed")
        self.assertEqual(claim_event["dispatch"], work.dispatch_id)
        self.assertEqual(claim_event["owner"], self.owner_id)
        self.assertEqual(claim_event["stage"], dispatch.STAGE_STORY)
        self.assertEqual(claim_event["process"], "p1")
        self.assertEqual(claim_event["attempt"], 1)
        self.assertEqual(claim_event["tick"], 101)

        _, info, _ = self._capture(
            lambda: dispatch.mark_waiting(
                claimed, dispatch.REASON_NO_CAPABILITY, tick=102, process="p1"
            )
        )
        waiting = self._only(info, "dream_dispatch_waiting")
        self.assertEqual(waiting["dispatch"], work.dispatch_id)
        self.assertEqual(waiting["reason"], dispatch.REASON_NO_CAPABILITY)
        self.assertEqual(waiting["stage"], dispatch.STAGE_STORY)
        self.assertEqual(waiting["work_state"], dispatch.STATE_WAITING_SERVICE)

        # Reconsideration re-arms the same work, and the failure that follows
        # keeps the same durable identity.
        dispatch.consider_waiting(process="p2")
        claimed_result, info, _ = self._capture(
            lambda: dispatch.claim(dispatch.find_work(work.dispatch_id), process="p2", tick=103)
        )
        claimed, token = claimed_result
        self.assertEqual(self._only(info, "dream_dispatch_claimed")["attempt"], 2)
        _, info, _ = self._capture(
            lambda: dispatch.mark_failed(
                claimed, token, dispatch.REASON_EXECUTION_FAILED, tick=104, process="p2"
            )
        )
        failed = self._only(info, "dream_dispatch_failed")
        self.assertEqual(failed["dispatch"], work.dispatch_id)
        self.assertEqual(failed["owner"], self.owner_id)
        self.assertEqual(failed["reason"], dispatch.REASON_EXECUTION_FAILED)
        self.assertEqual(failed["work_state"], dispatch.STATE_FAILED)

    def test_publication_and_recovery_events_carry_their_references(self):
        draft = self._draft()
        request = self._confirm(draft)
        work = dispatch.find_by_submission(request.submission_key)
        claimed, token = dispatch.claim(work, process="p1", tick=101)
        _, info, _ = self._capture(
            lambda: dispatch.mark_arranged(
                claimed,
                token,
                decision_id="decision:synthetic",
                thread_id="thread:synthetic",
                beat_id="beat:synthetic",
                package_id="package:synthetic",
                tick=110,
                process="p1",
            )
        )
        published = self._only(info, "dream_dispatch_published")
        self.assertEqual(published["dispatch"], work.dispatch_id)
        self.assertEqual(published["owner"], self.owner_id)
        self.assertEqual(published["decision"], "decision:synthetic")
        self.assertEqual(published["thread_id"], "thread:synthetic")
        self.assertEqual(published["beat_id"], "beat:synthetic")
        self.assertEqual(published["package"], "package:synthetic")
        self.assertEqual(published["work_state"], dispatch.STATE_ARRANGED)

        # A second work left claimed by a previous process is recoverable: the
        # recovery event reports the invalidated claim, not a replay.
        other = confirm_draft(
            draft_id=self._draft(summary="合成第二版方向：在北門遇見一個商人。").draft_id,
            owner_id=self.owner_id,
            tick=100,
        )
        claimed, _ = dispatch.claim(
            dispatch.find_by_submission(other.submission_key), process="p1", tick=101
        )
        recovered, info, _ = self._capture(
            lambda: dispatch.recover_interrupted(process="p2", tick=120)
        )
        self.assertEqual(recovered, [claimed.dispatch_id])
        recovery = self._only(info, "dream_dispatch_recovered")
        self.assertEqual(recovery["dispatch"], claimed.dispatch_id)
        self.assertEqual(recovery["owner"], self.owner_id)
        self.assertEqual(recovery["work_state"], dispatch.STATE_QUEUED)
        self.assertEqual(recovery["previous_token"], True)
        self.assertEqual(recovery["process"], "p2")

    def test_a_rolled_back_confirmation_announces_nothing(self):
        draft = self._draft()
        info: list[tuple[str, dict]] = []

        def record(event, *, context=None, exc=None):
            info.append((event, dict(context or {})))

        with patch.object(dispatch, "log_info", side_effect=record):
            with transaction.atomic():
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    confirm_draft(
                        draft_id=draft.draft_id, owner_id=self.owner_id, tick=100
                    )
                self.assertNotEqual(callbacks, [])
                transaction.set_rollback(True)
        self.assertEqual(info, [])
        self.assertEqual(DreamDispatch.objects.count(), 0)

    def test_dispatch_events_never_carry_the_direction_summary(self):
        draft = self._draft()
        summary = draft.direction["summary"]
        request, info, warn = self._capture(
            lambda: confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        )
        work = dispatch.find_by_submission(request.submission_key)
        _, more, _ = self._capture(
            lambda: dispatch.mark_waiting(work, dispatch.REASON_NO_CAPABILITY, tick=101)
        )
        self.assertTrue(info and more)
        for event, context in (*info, *more, *warn):
            serialized = json.dumps(context, ensure_ascii=False)
            self.assertNotIn(summary, serialized, event)
            for key, value in context.items():
                self.assertIsInstance(value, (str, int, bool), f"{event}.{key}")
                if isinstance(value, str):
                    self.assertLessEqual(len(value), 128, f"{event}.{key}")
