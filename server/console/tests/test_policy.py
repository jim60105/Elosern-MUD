"""S6 tick provenance, handoff, contention, outcome and evidence contracts."""

from types import SimpleNamespace
from unittest import TestCase, mock
from server.console import execution, registry
from server.console.errors import ConsoleError
from server.console.snapshot_policy import SnapshotPolicy
from server.saves.layout import SaveInProgress


class PolicyTests(TestCase):
    def setUp(self):
        self.clock = SimpleNamespace(tick=12)
        self.saved = []
        self.handoffs = 0
        def runner(call):
            self.handoffs += 1
            return call()
        def saver(kind, label):
            self.assertFalse(execution.in_handoff())
            self.saved.append(kind)
            return SimpleNamespace(id=f"save-{len(self.saved)}", clock={"tick": self.clock.tick})
        self.policy = SnapshotPolicy(runner=runner, clock_reader=lambda: self.clock, saver=saver)
        self.events = mock.patch('server.console.snapshot_policy.log_info').start()
        self.addCleanup(mock.patch.stopall)

    def execute(self, operation=lambda: {'target': '#1'}):
        return self.policy.execute(operation, action='set_wallet', account='operator', target='#1', arguments='copper=4')

    def test_first_equal_changed_backward_and_restart(self):
        self.assertTrue(self.policy.status()['will_snapshot'])
        self.assertTrue(self.execute()['snapshot']['taken'])
        self.assertEqual(self.handoffs, 2)
        self.assertFalse(self.execute()['snapshot']['taken'])
        for tick in (18, 3):
            self.clock.tick = tick
            self.assertTrue(self.execute()['snapshot']['taken'])
        self.policy.baseline_tick = None
        self.assertTrue(self.execute()['snapshot']['taken'])
        self.assertEqual(self.saved, ['auto_intervention'] * 4)

    def test_own_advance_absorbed_but_player_after_backup_never_absorbed(self):
        def saver(kind, label):
            represented = self.clock.tick
            self.clock.tick += 5
            return SimpleNamespace(id='real-save', clock={'tick': represented})
        self.policy.saver = saver
        def advance():
            self.assertTrue(execution.in_handoff())
            self.clock.tick += 2
            return {'target': 'world'}
        result = self.execute(advance)
        self.assertEqual(self.policy.baseline_tick, 14)
        self.assertEqual(self.clock.tick, 19)
        self.assertTrue(self.policy.status()['will_snapshot'])
        self.assertEqual(result['snapshot']['save_id'], 'real-save')

    def test_failed_save_blocks_writer_preserves_baseline(self):
        self.policy.baseline_tick = 1
        writer = mock.Mock()
        self.policy.saver = mock.Mock(side_effect=OSError('disk'))
        with self.assertRaises(ConsoleError) as caught:
            self.execute(writer)
        self.assertEqual(caught.exception.code, 'snapshot_failed')
        self.assertFalse(caught.exception.snapshot['taken'])
        self.assertEqual(self.policy.baseline_tick, 1)
        writer.assert_not_called()
        self.assertEqual(self.events.call_args.kwargs['context']['outcome'], 'snapshot_failed')

    def test_domain_refusal_preserves_completed_save_and_baseline(self):
        with self.assertRaises(ConsoleError) as caught:
            self.execute(mock.Mock(side_effect=ConsoleError('invalid_argument')))
        self.assertTrue(caught.exception.snapshot['taken'])
        self.assertEqual(self.policy.baseline_tick, 12)
        self.assertEqual(self.events.call_args.kwargs['context']['outcome'], 'invalid_argument')

    def test_missing_saved_clock_fails_closed_and_missing_live_clock_creates_nothing(self):
        self.policy.saver = lambda *args: SimpleNamespace(id='save', clock=None)
        self.execute()
        self.assertIsNone(self.policy.baseline_tick)
        self.assertTrue(self.policy.status()['will_snapshot'])
        self.policy.clock_reader = lambda: None
        self.assertIsNone(self.policy.status()['tick'])
        with self.assertRaises(ConsoleError) as caught:
            self.execute()
        self.assertEqual(caught.exception.code, 'target_not_found')

    def test_manual_saved_tick_failure_and_equal_write(self):
        self.policy.manual_save('undo')
        self.assertEqual(self.policy.baseline_tick, 12)
        self.assertFalse(self.execute()['snapshot']['taken'])
        self.policy.saver = mock.Mock(side_effect=SaveInProgress('busy'))
        with self.assertRaises(SaveInProgress):
            self.policy.manual_save('refused')
        self.assertEqual(self.policy.baseline_tick, 12)
        self.policy.saver = lambda *args: SimpleNamespace(id='copy', clock={'tick': 10})
        self.policy.manual_save('copy')
        self.assertEqual(self.policy.baseline_tick, 10)
        self.assertTrue(self.policy.status()['will_snapshot'])

    def test_manual_manual_and_console_contention_refuse_without_queue(self):
        self.policy.baseline_tick = 7
        self.policy._lock.acquire()
        try:
            with self.assertRaises(SaveInProgress):
                self.policy.manual_save('second')
            with self.assertRaises(ConsoleError) as caught:
                self.execute()
            self.assertEqual(caught.exception.reason, 'console_in_progress')
            self.assertEqual(self.saved, [])
            self.assertEqual(self.policy.baseline_tick, 7)
        finally:
            self.policy._lock.release()

    def test_reentry_refuses_and_outcome_event_follows_operation(self):
        def operation():
            self.assertFalse(self.events.called)
            with self.assertRaises(ConsoleError):
                self.execute()
            with self.assertRaises(SaveInProgress):
                self.policy.manual_save('nested')
            return {'target': '#1'}
        self.execute(operation)
        self.assertEqual(self.events.call_args.kwargs['context']['outcome'], 'committed')

    @mock.patch('server.console.snapshot_policy.log_error')
    def test_unexpected_execution_failure_preserves_save_and_logs_exception(self, log):
        with self.assertRaises(ConsoleError) as caught:
            self.execute(mock.Mock(side_effect=RuntimeError('failure')))
        self.assertEqual(caught.exception.code, 'internal_error')
        self.assertTrue(caught.exception.snapshot['taken'])
        self.assertIsInstance(log.call_args.kwargs['exc'], RuntimeError)

    def test_scripted_player_mutation_cannot_interleave_with_compensation(self):
        inventory = ['initial']
        self.policy.baseline_tick = 12
        queued = []
        def runner(call):
            inventory.append('before')
            result = call()
            for change in queued:
                change()
            return result
        self.policy.runner = runner
        def operation():
            before = list(inventory)
            inventory.append('console')
            queued.append(lambda: inventory.append('after'))
            inventory[:] = before
            raise ConsoleError('invalid_argument')
        with self.assertRaises(ConsoleError):
            self.execute(operation)
        self.assertEqual(inventory, ['initial', 'before', 'after'])

    def test_inline_and_running_reactor_handoff_modes(self):
        from twisted.internet import reactor
        with mock.patch.object(reactor, 'running', False):
            self.assertEqual(execution.run_on_gameplay_thread(lambda: 4), 4)
        with mock.patch.object(reactor, 'running', True), mock.patch('twisted.python.threadable.isInIOThread', return_value=False), mock.patch('twisted.internet.threads.blockingCallFromThread', return_value=8) as handoff:
            call = lambda: 8
            self.assertEqual(execution.run_on_gameplay_thread(call), 8)
            handoff.assert_called_once_with(reactor, call)

    def test_closed_registry_exact_fields_and_safe_argument_summary(self):
        self.assertEqual(len(registry.VERBS), 14)
        self.assertEqual({entry[0] for entry in registry.VERBS.values()}, {'world.rules.gm', 'world.maps.gm', 'world.quests.gm', 'world.narrative.gm'})
        for name in ('eval', 'status', 'world.rules.gm.set_wallet', '__import__'):
            with self.assertRaises(ConsoleError) as caught:
                registry.validate_arguments(name, {})
            self.assertEqual(caught.exception.code, 'unknown_verb')
        with self.assertRaises(ConsoleError):
            registry.validate_arguments('set_wallet', {'target': '#1', 'copper': 2, 'extra': True})
        self.assertNotIn('secret', registry.argument_summary({'key': 'secret', 'copper': 4}))
