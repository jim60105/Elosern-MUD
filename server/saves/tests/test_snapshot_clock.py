"""Copied database clock provenance, including live interleaving and corruption."""
import base64
import pickle
import sqlite3
from unittest import TestCase, mock
from types import SimpleNamespace
from server.saves import snapshot
from server.saves.tests._support import TempWorld, fixed_metadata
from world.rules.clock import WorldDateTime
from tools.spec_traceability import covers_requirement


class SnapshotClockTests(TestCase):
    def setUp(self):
        self.world = TempWorld()
        self.addCleanup(self.world.cleanup)

    def write_tick(self, value):
        with sqlite3.connect(self.world.layout.db_file) as connection:
            connection.execute('UPDATE typeclasses_attribute SET db_value=? WHERE id=1', (base64.b64encode(pickle.dumps(value)).decode('ascii'),))

    @covers_requirement('gm-save-management::complete-world-save-contents')
    def test_manifest_uses_copy_despite_later_live_metadata_advance(self):
        def metadata():
            self.write_tick(999)
            return {**fixed_metadata(), 'clock':{'tick':999}}
        with mock.patch('server.saves.snapshot.log_info'):
            info = snapshot.create_snapshot('manual','copy', layout=self.world.layout, metadata=metadata)
        self.assertEqual(info.clock['tick'],42)
        self.assertEqual(info.clock['day'], WorldDateTime.from_tick(42).day_in_season)
        self.assertEqual(snapshot.snapshot_clock(self.world.layout.db_file)['tick'],999)

    def test_absent_corrupt_bool_and_negative_tick_have_no_represented_clock(self):
        for value in (None, True, -1, '42'):
            with self.subTest(value=value):
                self.write_tick(value)
                self.assertIsNone(snapshot.snapshot_clock(self.world.layout.db_file))
        with sqlite3.connect(self.world.layout.db_file) as connection:
            connection.execute("UPDATE typeclasses_attribute SET db_value='broken'")
        with mock.patch('server.saves.snapshot.log_warn') as event:
            self.assertIsNone(snapshot.snapshot_clock(self.world.layout.db_file))
        self.assertEqual(event.call_args.args[0], 'save_clock_unreadable')
        with sqlite3.connect(self.world.layout.db_file) as connection:
            connection.execute('DELETE FROM scripts_scriptdb')
        self.assertIsNone(snapshot.snapshot_clock(self.world.layout.db_file))

    def test_injectable_copy_reader_wins_over_informational_metadata(self):
        with mock.patch('server.saves.snapshot.log_info'):
            info = snapshot.create_snapshot('manual','injected',layout=self.world.layout, metadata=fixed_metadata, clock_reader=lambda path:None)
        self.assertIsNone(info.clock)

    def test_manual_baseline_and_calendar_follow_copy_after_live_metadata_advance(self):
        from server.console.snapshot_policy import SnapshotPolicy
        def metadata():
            self.write_tick(999)
            return fixed_metadata()
        def save(kind,label):
            return snapshot.create_snapshot(kind,label,layout=self.world.layout,metadata=metadata)
        policy=SnapshotPolicy(runner=lambda call:call(),saver=save,clock_reader=lambda:SimpleNamespace(tick=snapshot.snapshot_clock(self.world.layout.db_file)['tick']))
        with mock.patch('server.saves.snapshot.log_info'):
            info=policy.manual_save('copy')
        self.assertEqual(info.clock['tick'],42)
        self.assertEqual(info.clock['day'],WorldDateTime.from_tick(42).day_in_season)
        self.assertEqual(policy.baseline_tick,42)
        self.assertTrue(policy.status()['will_snapshot'])
        self.write_tick(42)
        with mock.patch('server.console.snapshot_policy.log_info'):
            result=policy.execute(lambda:{'target':'#1'},action='set_wallet',account='synthetic',target='#1')
        self.assertEqual(result['snapshot'],{'taken':False,'save_id':None})
