"""Restore requests in the live server and the startup result report."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from django.test import override_settings

from server.saves import restore, snapshot
from server.saves.layout import SaveIncompatible, SaveInProgress, atomic_write_json
from server.saves.tests._support import FUTURE_MIGRATION, TempWorld, fixed_metadata
from tools.spec_traceability import covers_requirement


class RestoreRequestTests(unittest.TestCase):
    def setUp(self):
        self.world = TempWorld()
        self.layout = self.world.layout
        quiet = mock.patch("server.saves.restore._say")
        quiet.start()
        self.addCleanup(quiet.stop)
        self.events = []

    def tearDown(self):
        self.world.cleanup()

    def create(self, kind="manual", label="slot"):
        return snapshot.create_snapshot(kind, label, layout=self.layout, metadata=fixed_metadata)

    def request(self, save_id, shutdown=None):
        def record_shutdown():
            self.events.append(("shutdown", self.layout.pending_marker.exists()))

        return snapshot.request_restore(
            save_id,
            layout=self.layout,
            schedule_shutdown=shutdown or record_shutdown,
            metadata=fixed_metadata,
            root=self.world.root,
        )

    @covers_requirement("gm-save-management::guarded-restore-request")
    def test_unknown_migration_is_refused_without_side_effects(self):
        target = self.create()
        self.world.add_migration(FUTURE_MIGRATION, db=self.layout.saved_db(target.id))
        with self.assertRaises(SaveIncompatible):
            self.request(target.id)
        self.assertFalse(self.layout.pending_marker.exists())
        self.assertEqual([s.id for s in snapshot.list_saves(layout=self.layout)], [target.id])
        self.assertEqual(self.events, [])

    @covers_requirement("gm-save-management::guarded-restore-request", "gm-save-management::save-operational-observability")
    def test_accepted_request_saves_first_then_marks_then_shuts_down(self):
        target = self.create()
        self.world.write_state("after the save")
        with mock.patch("server.saves.snapshot.log_info") as log_info:
            result = self.request(target.id)
        pre = snapshot.get_save(result["pre_restore_save"], layout=self.layout)
        self.assertEqual(pre.kind, "auto_restore")
        self.assertEqual(self.world.read_state(self.layout.saved_db(pre.id)), "after the save")
        self.assertEqual(self.layout.pending_marker.read_text().strip(), target.id)
        # Shutdown is scheduled only after the marker is durable.
        self.assertEqual(self.events, [("shutdown", True)])
        # The live database is untouched in-process.
        self.assertEqual(self.world.read_state(), "after the save")
        requested = [c for c in log_info.call_args_list if c.args[0] == "save_restore_requested"]
        self.assertEqual(
            requested[0].kwargs["context"],
            {"save": target.id, "kind": "manual", "pre_save": pre.id},
        )
        self.assertEqual(result, {"save": target.id, "pre_restore_save": pre.id, "shutdown": True})

    @covers_requirement("gm-save-management::guarded-restore-request")
    def test_failed_pre_save_writes_no_marker_and_does_not_shut_down(self):
        target = self.create()
        with mock.patch("server.saves.snapshot._backup_database", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.request(target.id)
        self.assertFalse(self.layout.pending_marker.exists())
        self.assertEqual(self.events, [])
        self.assertEqual(self.world.read_state(), "original")

    @covers_requirement("gm-save-management::guarded-restore-request")
    def test_failed_shutdown_scheduling_removes_the_marker(self):
        target = self.create()

        def broken():
            raise RuntimeError("reactor not running")

        with self.assertRaises(RuntimeError):
            self.request(target.id, shutdown=broken)
        self.assertFalse(self.layout.pending_marker.exists())

    @covers_requirement("gm-save-management::guarded-restore-request")
    def test_pending_restore_blocks_new_saves_and_second_requests(self):
        target = self.create()
        self.request(target.id)
        with self.assertRaises(SaveInProgress):
            self.create()
        with self.assertRaises(SaveInProgress):
            self.request(target.id)

    @override_settings(GM_AUTOSAVE_KEEP=2)
    @covers_requirement("gm-save-management::guarded-restore-request", "gm-save-management::retention-and-manual-deletion")
    def test_oldest_auto_restore_target_survives_and_retention_completes_after_startup(self):
        oldest, middle = self.create(kind="auto_restore"), self.create(kind="auto_restore")
        self.request(oldest.id)
        ids = {s.id for s in snapshot.list_saves(layout=self.layout)}
        self.assertIn(oldest.id, ids)
        self.assertEqual(len(ids), 3)
        # The pre-start tool restores the target; the archive stays available.
        self.assertEqual(restore.apply_pending(self.layout, self.world.root), restore.EXIT_OK)
        result = json.loads(self.layout.result_file.read_text())
        self.assertEqual((result["save"], result["outcome"]), (oldest.id, "restored"))
        self.assertTrue(snapshot.get_save(oldest.id, layout=self.layout))
        # Startup completes the deferred oldest-first pruning.
        with mock.patch("server.saves.snapshot.log_info"):
            snapshot.startup_report(layout=self.layout)
        remaining = [s.id for s in snapshot.list_saves(layout=self.layout)]
        self.assertEqual(len(remaining), 2)
        self.assertNotIn(oldest.id, remaining)
        self.assertIn(middle.id, remaining)


class StartupReportTests(unittest.TestCase):
    def setUp(self):
        self.world = TempWorld()
        self.layout = self.world.layout

    def tearDown(self):
        self.world.cleanup()

    def report(self):
        with mock.patch("server.saves.snapshot.log_info") as log_info, mock.patch(
            "server.saves.snapshot.log_warn"
        ) as log_warn:
            snapshot.startup_report(layout=self.layout)
        return log_info, log_warn

    @covers_requirement("gm-save-management::save-operational-observability", "gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_success_and_failure_results_become_events_once(self):
        payload = {"save": "20260101T000000-abcdef", "kind": "manual", "outcome": "restored", "reported": False}
        atomic_write_json(self.layout.result_file, payload)
        log_info, log_warn = self.report()
        log_info.assert_called_once_with("save_restored", context={"save": payload["save"], "kind": "manual"})
        log_warn.assert_not_called()
        self.assertEqual(snapshot.latest_restore_result(layout=self.layout)["outcome"], "restored")
        log_info, _ = self.report()
        log_info.assert_not_called()

        atomic_write_json(self.layout.result_file, {**payload, "outcome": "failed", "reason": "missing file", "reported": False})
        log_info, log_warn = self.report()
        log_warn.assert_called_once_with(
            "save_restore_failed",
            context={"save": payload["save"], "kind": "manual", "reason": "missing file"},
        )
        self.assertEqual(snapshot.latest_restore_result(layout=self.layout)["reason"], "missing file")

    def test_no_result_reports_nothing(self):
        log_info, log_warn = self.report()
        log_info.assert_not_called()
        log_warn.assert_not_called()
        self.assertIsNone(snapshot.latest_restore_result(layout=self.layout))
