"""Behaviour tests for the dream-dispatch stage runner.

The runner is exercised against the real seams: the real confirmation
transaction, the real work record, the real director prepare/generate/settle
path and the real package publication. Only the model boundary is synthetic.
"""

import json
from unittest.mock import patch

from twisted.internet import defer

from world.narrative import dispatch
from world.narrative.attention import SOURCE_REQUEST
from world.narrative.dispatch_runner import RunResult, StageClients, run_next
from world.narrative.authoring import confirm_draft, save_draft
from world.narrative.models import CreativeRequest
from world.narrative.quest_beats import to_scene_package
from world.narrative.tests.test_story_director_beats import (
    StoryDirectorBeatsTestCase,
    _recorded,
)
from world.quests import scene_store
from world.quests.tests._compile_helpers import CompileRegistryIsolation
from world.quests.tests._fixtures import RegistryIsolationMixin  # noqa: F401
from world.rules.tests._combat_session_helpers import open_synthetic_scope

REQUIREMENTS = [
    {"kind": "place", "text": "南門"},
    {"kind": "new_character", "text": "一個女孩"},
    {"kind": "private_commission", "text": "帶她找媽媽"},
]


def _enabled(name):
    return True


class DispatchRunnerTests(CompileRegistryIsolation, StoryDirectorBeatsTestCase):
    """A queued executable direction runs to exactly one publication."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "items",
            "guild_branches",
            "archetypes",
            "anchors",
            "anchor_placements",
        )
        super().setUp()
        from world.ai.scenario_director import register_scenario_director
        from world.quests.tests._compile_helpers import _anchor_key
        from world.quests.tests._scene_package_fixtures import package as _package

        register_scenario_director()
        self.anchor = _anchor_key()
        self.room1.anchor_key = self.anchor
        self.owner.location = self.room1
        self.package_payload = _package()
        self.owner.guild_rank = self.package_payload["quest"]["rank"]

    # -- helpers -----------------------------------------------------------

    def _queued_work(self):
        draft = save_draft(
            owner_id=str(self.owner.pk),
            direction={
                "summary": "在南門遇見一個女孩，帶她找媽媽。",
                "kind": "new_story",
                "thread_id": None,
                "effects": [],
                "revisions": [],
                "requirements": list(REQUIREMENTS),
            },
            tick=self.now,
        )
        request = confirm_draft(
            draft_id=draft.draft_id, owner_id=str(self.owner.pk), tick=self.now
        )
        work = dispatch.find_by_submission(request.submission_key)
        self.assertIsNotNone(work)
        self.assertEqual(work.state, dispatch.STATE_QUEUED)
        return request, work

    def _extended_blueprint(self):
        extended = dict(self.package_payload["quest"])
        extended["display_name"] = self.package_payload["display_name"]
        for key in (
            "roles",
            "relationships",
            "knowledge",
            "encounters",
            "dialogue",
            "commissions",
            "outcome_groups",
        ):
            if key in self.package_payload:
                extended[key] = self.package_payload[key]
        return extended

    def _client(self, story_kind="quest_seed", extended=None):
        client = _recorded(story_kind)
        client.add_response(
            lambda descriptor: descriptor.schema_id == "scenario_director",
            json.dumps(extended or self._extended_blueprint(), ensure_ascii=False),
        )
        return client

    def _run(self, client, *, capability=_enabled, tick=None):
        return run_next(
            clients=StageClients(story=client, scenario=client),
            capability_enabled=capability,
            tick=self.now if tick is None else tick,
        ).result

    # -- the happy path ----------------------------------------------------

    def test_a_queued_executable_direction_runs_to_one_publication(self):
        request, work = self._queued_work()
        client = self._client()
        with self.captureOnCommitCallbacks(execute=True):
            result = self._run(client)
        self.assertEqual(result.outcome, "arranged")
        self.assertTrue(result.package_id)
        settled = dispatch.find_work(work.dispatch_id)
        self.assertEqual(settled.state, dispatch.STATE_ARRANGED)
        self.assertEqual(settled.package_id, result.package_id)
        self.assertEqual(settled.decision_id, settled.decision_id)
        self.assertEqual(settled.source_key, request.submission_key)
        published = scene_store.read_package(result.package_id)
        self.assertIsNotNone(published)
        self.assertEqual(
            published.payload["encounters"], self.package_payload["encounters"]
        )
        # Publication is an arrangement only: nothing was accepted or rewarded.
        from world.quests.runtime import read_records

        self.assertEqual(read_records(self.owner), [])
        # Both stages ran exactly once.
        self.assertEqual(len(client.calls), 2)

    def test_the_story_checkpoint_carries_the_captured_frame_and_proposal(self):
        _request, work = self._queued_work()
        client = self._client()
        self.assertEqual(self._run(client).outcome, "arranged")
        settled = dispatch.find_work(work.dispatch_id)
        checkpoint = settled.story_checkpoint
        self.assertTrue(checkpoint["context_frame"])
        self.assertEqual(checkpoint["proposal"]["kind"], "quest_seed")
        self.assertTrue(checkpoint["scene_required"])
        self.assertEqual(checkpoint["source"]["kind"], SOURCE_REQUEST)
        self.assertTrue(settled.scene_checkpoint["blueprint"])
        self.assertEqual(settled.scene_checkpoint["issuer_id"], "")

    # -- the refusal and failure paths -------------------------------------

    def test_prose_cannot_answer_an_executable_direction(self):
        _request, work = self._queued_work()
        client = self._client(story_kind="clue")
        self.assertEqual(self._run(client).outcome, "failed")
        settled = dispatch.find_work(work.dispatch_id)
        self.assertEqual(settled.state, dispatch.STATE_FAILED)
        self.assertEqual(
            settled.reason_code, dispatch.REASON_INSUFFICIENT_ARRANGEMENT
        )
        self.assertEqual(scene_store.list_packages(), [])

    def test_a_terminal_failure_is_never_rerolled(self):
        _request, work = self._queued_work()
        # No recorded response: the guardrail exhausts its budget and degrades.
        from world.ai.fake_client import FakeLLMClient

        client = FakeLLMClient()
        self.assertEqual(self._run(client).outcome, "failed")
        settled = dispatch.find_work(work.dispatch_id)
        # An error that escapes the guardrail is a bounded terminal reason, not
        # an unhandled callback and never a silent retry.
        self.assertEqual(settled.reason_code, dispatch.REASON_EXECUTION_FAILED)
        self.assertEqual(settled.state, dispatch.STATE_FAILED)
        calls = len(client.calls)
        # A later notification finds nothing eligible and calls no model again.
        self.assertEqual(self._run(client).outcome, "no_work")
        self.assertEqual(len(client.calls), calls)

    def test_a_publication_failure_leaves_no_orphan(self):
        _request, work = self._queued_work()
        client = self._client()
        with patch(
            "world.narrative.dispatch_runner.settle_decision",
            side_effect=RuntimeError("publication exploded"),
        ):
            result = self._run(client)
        self.assertEqual(result.outcome, "failed")
        settled = dispatch.find_work(work.dispatch_id)
        self.assertEqual(settled.state, dispatch.STATE_FAILED)
        self.assertEqual(
            settled.reason_code, dispatch.REASON_PUBLICATION_FAILED
        )
        self.assertEqual(scene_store.list_packages(), [])
        self.assertEqual(CreativeRequest.objects.count(), 1)

    def test_a_stale_source_is_reported_without_publication(self):
        _request, work = self._queued_work()
        dispatch.DreamDispatch.objects.filter(pk=work.pk).update(request_version=99)
        client = self._client()
        result = self._run(client)
        self.assertEqual(result.outcome, "failed")
        self.assertEqual(
            dispatch.find_work(work.dispatch_id).reason_code,
            dispatch.REASON_STALE_SOURCE,
        )
        self.assertEqual(scene_store.list_packages(), [])
        self.assertEqual(len(client.calls), 0)

    # -- waiting, deferral and recovery -----------------------------------

    def test_a_disabled_capability_waits_without_blocking_other_work(self):
        _first, first_work = self._queued_work()
        _second, second_work = self._queued_work()
        client = self._client()
        result = self._run(client, capability=lambda name: False)
        self.assertEqual(result.outcome, "no_work")
        self.assertEqual(len(client.calls), 0)
        # The pass did not stop at the first record: both are waiting, and the
        # waiting state is still reconsiderable.
        for work in (first_work, second_work):
            self.assertEqual(
                dispatch.find_work(work.dispatch_id).state,
                dispatch.STATE_WAITING_SERVICE,
            )
        self.assertEqual(
            [work.state for work in dispatch.next_considered()],
            [dispatch.STATE_WAITING_SERVICE, dispatch.STATE_WAITING_SERVICE],
        )
        # A later notification with the capability available runs the queue.
        self.assertEqual(self._run(client).outcome, "arranged")

    def test_a_superseded_claim_defers_instead_of_writing(self):
        _request, work = self._queued_work()
        client = self._client()
        # Claim elsewhere first: this pass' claim is the live one, so a stolen
        # token cannot be the runner's. Simulate the fence by clearing the row's
        # token between claim and checkpoint.
        original = dispatch.checkpoint_story

        def steal(work_row, token, **kwargs):
            dispatch.release_claim(work_row, token)
            return original(work_row, token, **kwargs)

        with patch(
            "world.narrative.dispatch_runner.dispatch.checkpoint_story",
            side_effect=steal,
        ):
            result = self._run(client)
        self.assertEqual(result.outcome, "deferred")
        settled = dispatch.find_work(work.dispatch_id)
        self.assertIsNone(settled.story_checkpoint)
        self.assertEqual(settled.state, dispatch.STATE_GENERATING_STORY)

    def test_a_missing_scene_capability_parks_at_that_stage_and_resumes(self):
        # The scene stage's capability is checked before the stage runs, and a
        # missing one parks the work at that stage with the story checkpoint
        # intact, instead of failing it or blocking the queue.
        _request, work = self._queued_work()
        client = self._client()
        result = self._run(client, capability=lambda name: name != "scenario_director")
        self.assertEqual(result.outcome, "waiting")
        self.assertEqual(result.stage, dispatch.STAGE_SCENE)
        parked = dispatch.find_work(work.dispatch_id)
        self.assertEqual(parked.state, dispatch.STATE_WAITING_SERVICE)
        self.assertEqual(parked.stage, dispatch.STAGE_SCENE)
        self.assertTrue(parked.story_checkpoint)
        self.assertIsNone(parked.scene_checkpoint)
        story_calls = len(client.calls)
        self.assertEqual(scene_store.list_packages(), [])

        # Configuration activation makes the stage available: the same work
        # resumes at the scene stage and regenerates only that stage.
        with self.captureOnCommitCallbacks(execute=True):
            resumed = self._run(client)
        self.assertEqual(resumed.outcome, "arranged")
        self.assertEqual(len(client.calls), story_calls + 1)
        settled = dispatch.find_work(work.dispatch_id)
        self.assertEqual(settled.state, dispatch.STATE_ARRANGED)
        self.assertIsNotNone(scene_store.read_package(settled.package_id))

    def test_an_interrupted_claim_is_fenced_and_resumes_under_one_source(self):
        _request, work = self._queued_work()
        client = self._client()
        # A previous process claimed the work and died mid-story: its claim is
        # fenced, and the resumed run reuses the saved checkpoint.
        claimed = dispatch.claim(work, process="previous-process", tick=self.now)
        self.assertIsNotNone(claimed)
        self.assertEqual(
            dispatch.recover_interrupted(process=dispatch.process_identity()),
            [work.dispatch_id],
        )
        self.assertEqual(
            dispatch.find_work(work.dispatch_id).state, dispatch.STATE_QUEUED
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self._run(client).outcome, "arranged")
        self.assertEqual(len(scene_store.list_packages()), 1)
        self.assertEqual(len(client.calls), 2)

    def test_no_work_leaves_the_pass_idle(self):
        client = self._client()
        result = self._run(client)
        self.assertEqual(result, RunResult("", "no_work", "", ""))
        self.assertEqual(len(client.calls), 0)
