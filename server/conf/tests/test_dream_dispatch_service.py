"""The dream-dispatch pump's lifecycle: single flight, recovery, fencing.

The pump is driven directly (not through the reactor), and its pass is stubbed
wherever a real generation would need a transport, so these tests assert the
lifecycle contract itself: one generation at a time, interrupted claims resumed,
waiting work reconsidered and shutdown fencing durable.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from twisted.internet import defer

from tools.spec_traceability import covers_requirement

from server import dream_dispatch_service as pump
from world.narrative import dispatch


class DreamDispatchPumpTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        pump.reset_pump_state()
        dispatch.register_pump(None)
        self.addCleanup(pump.reset_pump_state)
        self.addCleanup(pump.stop_pump)
        self.addCleanup(dispatch.register_pump, None)

    def _idle_pass(self):
        """A pass that runs nothing: the lifecycle without a transport."""
        return defer.succeed(None)

    def test_start_is_idempotent_and_owns_the_hint(self):
        with patch.object(pump, "_drain", side_effect=self._idle_pass):
            self.assertTrue(pump.start_pump())
            # Idempotent, and never a ``False`` return: the startup step
            # wrapper reads ``False`` as a tolerated skip.
            self.assertIsNone(pump.start_pump())
        self.assertTrue(dispatch.pump_registered())
        self.assertTrue(pump.stop_pump())
        self.assertFalse(dispatch.pump_registered())

    @covers_requirement(
        "dream-story-dispatch::one-server-owned-pump-processes-eligible-work-in-confirmation-order"
    )
    def test_only_one_pass_runs_at_a_time(self):
        passes = []
        first = defer.Deferred()

        def drain():
            passes.append("pass")
            return first if len(passes) == 1 else self._idle_pass()

        with patch.object(pump, "_drain", side_effect=drain):
            pump.start_pump()
            self.assertEqual(len(passes), 1)
            # A notification while a pass is in flight is remembered, not run.
            pump.kick()
            pump.kick()
            self.assertEqual(len(passes), 1)
            self.assertTrue(pump.pump_state()["in_flight"])
            self.assertTrue(pump.pump_state()["pending"])
            # Completing the in-flight pass runs exactly one more pass.
            first.callback(None)
            self.assertEqual(len(passes), 2)

    def test_stop_fences_outstanding_claims(self):
        draft_id = "synthetic-pump-owner"
        # A queued work record owned by this test, claimed by this process.
        from world.narrative.authoring import confirm_draft, save_draft

        draft = save_draft(
            owner_id=draft_id,
            direction={"kind": "new_story", "summary": "合成方向"},
            tick=0,
        )
        request = confirm_draft(draft_id=draft.draft_id, owner_id=draft_id, tick=0)
        work = dispatch.find_by_submission(request.submission_key)
        claimed = dispatch.claim(work, process=dispatch.process_identity())
        self.assertIsNotNone(claimed)

        with patch.object(pump, "_drain", side_effect=self._idle_pass):
            pump.start_pump()
        pump.stop_pump()
        self.assertEqual(dispatch.find_work(work.dispatch_id).execution_token, "")
        self.assertIn(work.dispatch_id, [item.dispatch_id for item in dispatch.next_considered()])

    def test_start_recovers_an_interrupted_claim_and_reconsiders_waiting_work(self):
        from world.narrative.authoring import confirm_draft, save_draft

        draft = save_draft(
            owner_id="synthetic-recover-owner",
            direction={"kind": "new_story", "summary": "合成方向"},
            tick=0,
        )
        request = confirm_draft(
            draft_id=draft.draft_id, owner_id="synthetic-recover-owner", tick=0
        )
        work = dispatch.find_by_submission(request.submission_key)
        dispatch.claim(work, process="previous-process")
        dispatch.mark_waiting(work)

        with patch.object(pump, "_drain", side_effect=self._idle_pass):
            pump.start_pump()
        resumed = dispatch.find_work(work.dispatch_id)
        self.assertEqual(resumed.state, dispatch.STATE_QUEUED)
        self.assertEqual(resumed.claimed_by, dispatch.process_identity())
        pump.stop_pump()
