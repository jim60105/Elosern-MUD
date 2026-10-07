"""Snapshot creation, listing, retention, deletion, and archives (temporary files)."""

from __future__ import annotations

import io
import json
import os
import sqlite3
import tarfile
import threading
import time
import unittest
from unittest import mock

from django.test import override_settings

from server.saves import snapshot
from server.saves.layout import (
    InvalidSaveId,
    SaveDeleteForbidden,
    SaveInProgress,
    SaveNotFound,
    iter_complete_ids,
)
from server.saves.tests._support import TempWorld, fixed_metadata
from world.art import publication
from tools.spec_traceability import covers_requirement


class SnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self.world = TempWorld()
        self.layout = self.world.layout

    def tearDown(self):
        self.world.cleanup()

    def create(self, kind="manual", label="before the fight", **kwargs):
        return snapshot.create_snapshot(kind, label, layout=self.layout, metadata=fixed_metadata, **kwargs)


class CreateSnapshotTests(SnapshotTestCase):
    @covers_requirement("gm-save-management::complete-world-save-contents")
    def test_manifest_contents_and_exclusions(self):
        self.world.art("scene/forest.webp", b"forest-bytes")
        self.world.art("gallery/character/hero/a.png", b"hero-bytes")
        self.world.art(".saves/20200101T000000-abcdef/scene/old.webp", b"nested-archive")
        self.world.art("scene/.forest.webp.k3j.tmp", b"half-written")
        info = self.create()
        manifest = json.loads(self.layout.manifest_path(info.id).read_text())
        for key in ("id", "label", "kind", "created_at", "clock", "players", "migrations", "file_count", "size_bytes"):
            self.assertIn(key, manifest)
        self.assertEqual(manifest["label"], "before the fight")
        self.assertEqual(manifest["kind"], "manual")
        self.assertEqual(manifest["clock"]["tick"], 42)
        self.assertEqual(manifest["players"], [{"name": "Tester", "location": "room-a"}])
        self.assertEqual(manifest["migrations"], {"fake": "0001_initial"})
        saved = sorted(entry["path"] for entry in manifest["files"]["art"])
        self.assertEqual(saved, ["gallery/character/hero/a.png", "scene/forest.webp"])
        self.assertEqual(manifest["file_count"], 3)
        db_size = self.layout.saved_db(info.id).stat().st_size
        self.assertEqual(manifest["size_bytes"], db_size + len(b"forest-bytes") + len(b"hero-bytes"))
        art_dir = self.layout.art_dir(info.id)
        self.assertEqual((art_dir / "scene/forest.webp").read_bytes(), b"forest-bytes")
        self.assertFalse((art_dir / ".saves").exists())
        self.assertFalse((art_dir / "scene/.forest.webp.k3j.tmp").exists())
        self.assertEqual(self.world.read_state(self.layout.saved_db(info.id)), "original")
        self.assertEqual([s.id for s in snapshot.list_saves(layout=self.layout)], [info.id])

    @covers_requirement("gm-save-management::complete-world-save-contents")
    def test_label_is_normalized_and_clamped(self):
        info = self.create(label="  two\nlines\t" + "x" * 200)
        self.assertTrue(info.label.startswith("two lines "))
        self.assertEqual(len(info.label), 80)

    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history")
    def test_online_backup_is_consistent_while_writes_occur(self):
        stop = threading.Event()
        errors = []

        def writer():
            counter = 0
            while not stop.is_set():
                counter += 1
                try:
                    connection = sqlite3.connect(self.layout.db_file, timeout=30)
                    with connection:
                        connection.execute("INSERT INTO world VALUES (?, ?)", (f"k{counter}", "v" * 512))
                    connection.close()
                except sqlite3.Error as error:  # pragma: no cover - surfaced through the assertion
                    errors.append(error)

        thread = threading.Thread(target=writer)
        thread.start()
        try:
            time.sleep(0.05)
            info = self.create()
        finally:
            stop.set()
            thread.join()
        self.assertEqual(errors, [])
        connection = sqlite3.connect(self.layout.saved_db(info.id))
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertGreaterEqual(connection.execute("SELECT COUNT(*) FROM world").fetchone()[0], 1)
        finally:
            connection.close()

    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history")
    def test_link_failure_falls_back_to_copy_and_saved_bytes_survive_replacement(self):
        forest = self.world.art("scene/forest.webp", b"forest-v1")
        hero = self.world.art("portrait/character/hero.webp", b"hero-v1")
        real_link = os.link

        def flaky_link(src, dst, *args, **kwargs):
            if str(src).endswith("hero.webp"):
                raise OSError("cross-device link")
            return real_link(src, dst, *args, **kwargs)

        with mock.patch("server.saves.snapshot.os.link", side_effect=flaky_link):
            info = self.create()
        art_dir = self.layout.art_dir(info.id)
        self.assertEqual(os.stat(art_dir / "scene/forest.webp").st_ino, os.stat(forest).st_ino)
        self.assertNotEqual(os.stat(art_dir / "portrait/character/hero.webp").st_ino, os.stat(hero).st_ino)
        # Later writers replace atomically or delete; saved bytes never change.
        replacement = forest.with_name(".forest.webp.x.tmp")
        replacement.write_bytes(b"forest-v2")
        os.replace(replacement, forest)
        hero.unlink()
        self.assertEqual((art_dir / "scene/forest.webp").read_bytes(), b"forest-v1")
        self.assertEqual((art_dir / "portrait/character/hero.webp").read_bytes(), b"hero-v1")

    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history")
    def test_art_publication_is_held_during_the_snapshot(self):
        self.world.art("scene/forest.webp", b"forest")
        observed = {}
        real_mirror = snapshot._mirror_art

        def mirror(*args):
            observed["paused"] = publication.is_paused()
            acquired = []
            worker = threading.Thread(target=lambda: acquired.append(publication._gate.acquire(timeout=0.05)))
            worker.start()
            worker.join()
            observed["writer_blocked"] = acquired == [False]
            return real_mirror(*args)

        with mock.patch("server.saves.snapshot._mirror_art", side_effect=mirror):
            self.create()
        self.assertTrue(observed["paused"])
        self.assertTrue(observed["writer_blocked"])
        self.assertFalse(publication.is_paused())

    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history")
    def test_concurrent_snapshot_is_refused(self):
        entered = threading.Event()
        release = threading.Event()
        real_backup = snapshot._backup_database

        def slow_backup(*args):
            entered.set()
            release.wait(5)
            return real_backup(*args)

        results = []
        with mock.patch("server.saves.snapshot._backup_database", side_effect=slow_backup):
            first = threading.Thread(target=lambda: results.append(self.create(label="first")))
            first.start()
            entered.wait(5)
            with self.assertRaises(SaveInProgress):
                self.create(label="second")
            release.set()
            first.join()
        self.assertEqual(len(results), 1)
        self.assertEqual(len(list(iter_complete_ids(self.layout))), 1)

    def assert_clean_failure(self):
        self.assertEqual(list(iter_complete_ids(self.layout)), [])
        self.assertEqual(snapshot.list_saves(layout=self.layout), [])
        leftovers = [p.name for p in self.layout.saves_root.iterdir()]
        self.assertEqual(leftovers, [])
        self.assertEqual([p.name for p in self.layout.art_saves_root.iterdir()], [])
        self.assertFalse(publication.is_paused())
        self.assertTrue(publication._gate.acquire(blocking=False))
        publication._gate.release()

    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history", "gm-save-management::save-operational-observability")
    def test_failure_at_each_stage_leaves_no_half_save_and_resumes_drain(self):
        self.world.art("scene/forest.webp", b"forest")
        real_rename = os.rename
        stages = {
            "backup": mock.patch("server.saves.snapshot._backup_database", side_effect=OSError("disk")),
            "mirror": mock.patch("server.saves.snapshot._mirror_art", side_effect=OSError("disk")),
            "manifest": mock.patch("server.saves.snapshot.atomic_write_json", side_effect=OSError("disk")),
            "first rename": mock.patch(
                "server.saves.snapshot.os.rename", side_effect=OSError("rename")
            ),
        }
        calls = {"n": 0}

        def second_rename_fails(src, dst):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("second rename")
            return real_rename(src, dst)

        stages["second rename"] = mock.patch("server.saves.snapshot.os.rename", side_effect=second_rename_fails)
        for stage, patcher in stages.items():
            with self.subTest(stage=stage):
                calls["n"] = 0
                with patcher, mock.patch("server.saves.snapshot.log_error") as log_error:
                    with self.assertRaises(OSError):
                        self.create()
                self.assertEqual(log_error.call_args.args[0], "save_failed")
                self.assertEqual(log_error.call_args.kwargs["context"]["kind"], "manual")
                self.assert_clean_failure()


class RetentionAndDeletionTests(SnapshotTestCase):
    @covers_requirement("gm-save-management::retention-and-manual-deletion")
    def test_default_retention_keeps_the_newest_ten(self):
        ids = [self.create(kind="auto_restore").id for _ in range(11)]
        remaining = [s.id for s in snapshot.list_saves(layout=self.layout)]
        self.assertEqual(sorted(remaining), sorted(ids[1:]))
        self.assertFalse(self.layout.art_dir(ids[0]).exists())

    @override_settings(GM_AUTOSAVE_KEEP=2)
    @covers_requirement("gm-save-management::retention-and-manual-deletion", "gm-save-management::save-operational-observability")
    def test_retention_is_per_automatic_kind_and_spares_manual_saves(self):
        manual = [self.create().id for _ in range(3)]
        intervention = [self.create(kind="auto_intervention").id for _ in range(2)]
        restore = [self.create(kind="auto_restore").id for _ in range(3)]
        with mock.patch("server.saves.snapshot.log_info") as log_info:
            restore.append(self.create(kind="auto_restore").id)
        remaining = {s.id for s in snapshot.list_saves(layout=self.layout)}
        self.assertEqual(remaining, set(manual) | set(intervention) | set(restore[-2:]))
        for gone in restore[:2]:
            self.assertFalse(self.layout.db_dir(gone).exists())
            self.assertFalse(self.layout.art_dir(gone).exists())
        deleted = [c for c in log_info.call_args_list if c.args[0] == "save_deleted"]
        self.assertEqual(deleted[0].kwargs["context"], {"save": restore[1], "kind": "auto_restore", "reason": "retention"})

    @covers_requirement("gm-save-management::retention-and-manual-deletion", "gm-save-management::save-operational-observability")
    def test_manual_deletion_and_automatic_refusal(self):
        manual = self.create()
        automatic = self.create(kind="auto_restore")
        with mock.patch("server.saves.snapshot.log_info") as log_info:
            snapshot.delete_save(manual.id, layout=self.layout)
        log_info.assert_called_once_with("save_deleted", context={"save": manual.id, "kind": "manual", "reason": "manual"})
        self.assertFalse(self.layout.db_dir(manual.id).exists())
        self.assertFalse(self.layout.art_dir(manual.id).exists())
        with self.assertRaises(SaveDeleteForbidden):
            snapshot.delete_save(automatic.id, layout=self.layout)
        self.assertTrue(self.layout.db_dir(automatic.id).exists())

    @covers_requirement("gm-save-management::complete-world-save-contents")
    def test_invalid_and_absent_ids(self):
        for bad in ("../../etc", "2020", "20200101T000000-ABCDEF", "", None):
            with self.subTest(bad=bad), mock.patch("server.saves.layout.Path.exists") as exists:
                with self.assertRaises(InvalidSaveId):
                    snapshot.delete_save(bad, layout=self.layout)
                exists.assert_not_called()
        with self.assertRaises(SaveNotFound):
            snapshot.delete_save("20200101T000000-abcdef", layout=self.layout)
        with self.assertRaises(SaveNotFound):
            snapshot.plan_archive("20200101T000000-abcdef", layout=self.layout)

    @covers_requirement("gm-save-management::complete-world-save-contents")
    def test_incomplete_pairs_are_not_listed(self):
        info = self.create()
        import shutil

        shutil.rmtree(self.layout.art_dir(info.id))
        self.assertEqual(snapshot.list_saves(layout=self.layout), [])
        (self.layout.saves_root / "20200101T000000-abcdef.partial").mkdir()
        self.assertEqual(snapshot.list_saves(layout=self.layout), [])


class ArchiveTests(SnapshotTestCase):
    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download")
    def test_archive_streams_database_manifest_and_art(self):
        self.world.art("scene/forest.webp", b"forest")
        self.world.art("gallery/character/" + "長名" * 40 + "/a.png", b"long-name")
        info = self.create()
        plan = snapshot.plan_archive(info.id, layout=self.layout)
        chunks = list(snapshot.iter_archive(plan))
        body = b"".join(chunks)
        self.assertEqual(len(body), plan.length)
        self.assertTrue(all(len(chunk) <= 64 * 1024 for chunk in chunks))
        with tarfile.open(fileobj=io.BytesIO(body), mode="r:") as archive:
            names = sorted(archive.getnames())
            self.assertIn(f"{info.id}/manifest.json", names)
            self.assertIn(f"{info.id}/evennia.db3", names)
            self.assertEqual(archive.extractfile(f"{info.id}/art/scene/forest.webp").read(), b"forest")
            self.assertEqual(len(names), 4)
            self.assertFalse(any("/.saves/" in name for name in names))
        self.assertEqual(plan.filename, f"elosern-save-{info.id}.tar")
