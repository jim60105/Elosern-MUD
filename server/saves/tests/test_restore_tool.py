"""The standard-library pre-start restore tool and both launchers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from server.saves import restore, snapshot
from server.saves.tests._support import FUTURE_MIGRATION, TempWorld, fixed_metadata
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]


class RestoreToolTests(unittest.TestCase):
    def setUp(self):
        self.world = TempWorld()
        self.layout = self.world.layout
        quiet = mock.patch("server.saves.restore._say")
        quiet.start()
        self.addCleanup(quiet.stop)
        self.world.art("scene/forest.webp", b"forest-saved")
        self.world.art("gallery/character/hero/a.png", b"hero-saved")
        with mock.patch("server.saves.snapshot.log_info"):
            self.save = snapshot.create_snapshot("manual", "slot", layout=self.layout, metadata=fixed_metadata)
        # Change the live world after the save.
        self.world.write_state("current")
        self.world.art("scene/forest.webp", b"forest-current")
        (self.layout.art_root / "gallery/character/hero/a.png").unlink()
        self.world.art("scene/new.webp", b"new-current")
        (self.layout.db_file.parent / "evennia.db3-journal").write_bytes(b"stale journal")

    def tearDown(self):
        self.world.cleanup()

    def stage(self, save_id=None):
        self.layout.pending_marker.write_text((save_id or self.save.id) + "\n")

    def apply(self):
        return restore.apply_pending(self.layout, self.world.root)

    def result(self):
        return json.loads(self.layout.result_file.read_text())

    def assert_current_world_intact(self):
        # Checked before SQLite opens the database (it discards a non-hot journal).
        self.assertEqual((self.layout.db_file.parent / "evennia.db3-journal").read_bytes(), b"stale journal")
        self.assertEqual(self.world.read_state(), "current")
        self.assertEqual((self.layout.art_root / "scene/forest.webp").read_bytes(), b"forest-current")
        self.assertEqual((self.layout.art_root / "scene/new.webp").read_bytes(), b"new-current")
        self.assertFalse((self.layout.art_root / "gallery/character/hero/a.png").exists())

    def assert_archive_intact(self):
        self.assertEqual(self.world.read_state(self.layout.saved_db(self.save.id)), "original")
        art = self.layout.art_dir(self.save.id)
        self.assertEqual((art / "scene/forest.webp").read_bytes(), b"forest-saved")
        self.assertEqual((art / "gallery/character/hero/a.png").read_bytes(), b"hero-saved")

    def assert_no_work_dirs(self):
        for base in (self.layout.db_file.parent, self.layout.art_root):
            self.assertFalse((base / ".restore-staging").exists())
            self.assertFalse((base / ".restore-aside").exists())

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_no_marker_changes_nothing(self):
        self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assert_current_world_intact()
        self.assertFalse(self.layout.result_file.exists())

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_success_installs_the_save_and_keeps_every_archive(self):
        self.stage()
        self.assertEqual(self.apply(), restore.EXIT_OK)
        # A stale journal never pairs with the installed database.
        self.assertFalse((self.layout.db_file.parent / "evennia.db3-journal").exists())
        self.assertEqual(self.world.read_state(), "original")
        art = self.layout.art_root
        self.assertEqual((art / "scene/forest.webp").read_bytes(), b"forest-saved")
        self.assertEqual((art / "gallery/character/hero/a.png").read_bytes(), b"hero-saved")
        self.assertFalse((art / "scene/new.webp").exists())
        # The installed files are independent copies, not links into the archive.
        self.assertNotEqual(
            os.stat(art / "scene/forest.webp").st_ino,
            os.stat(self.layout.art_dir(self.save.id) / "scene/forest.webp").st_ino,
        )
        self.assertFalse(self.layout.pending_marker.exists())
        self.assert_archive_intact()
        self.assert_no_work_dirs()
        self.assertTrue((art / ".saves").is_dir())
        self.assertEqual(self.result()["outcome"], "restored")
        self.assertEqual(self.result()["save"], self.save.id)
        self.assertEqual(self.result()["kind"], "manual")

    def assert_failed_cleanly(self, status=restore.EXIT_OK):
        self.assertEqual(self.apply(), status)
        self.assert_current_world_intact()
        self.assert_archive_intact()
        self.assertFalse(self.layout.pending_marker.exists())
        self.assert_no_work_dirs()
        self.assertEqual(self.result()["outcome"], "failed")
        self.assertTrue(self.result()["reason"])

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_missing_file_fails_before_touching_the_live_world(self):
        (self.layout.art_dir(self.save.id) / "scene/forest.webp").unlink()
        self.stage()
        self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assert_current_world_intact()
        self.assertFalse(self.layout.pending_marker.exists())
        self.assert_no_work_dirs()
        self.assertEqual(self.result()["outcome"], "failed")

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_missing_file_reason(self):
        (self.layout.art_dir(self.save.id) / "gallery/character/hero/a.png").unlink()
        self.stage()
        self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assertIn("missing file", self.result()["reason"])
        self.assert_current_world_intact()

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_corrupt_manifest_fails_cleanly(self):
        self.layout.manifest_path(self.save.id).write_text("{not json")
        self.stage()
        self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assertIn("manifest", self.result()["reason"])
        self.assert_current_world_intact()
        self.assertFalse(self.layout.pending_marker.exists())

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_unknown_migration_fails_cleanly(self):
        self.world.add_migration(FUTURE_MIGRATION, db=self.layout.saved_db(self.save.id))
        manifest = json.loads(self.layout.manifest_path(self.save.id).read_text())
        manifest["files"]["db"]["size"] = self.layout.saved_db(self.save.id).stat().st_size
        self.layout.manifest_path(self.save.id).write_text(json.dumps(manifest))
        self.stage()
        self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assertIn("save_incompatible", self.result()["reason"])
        self.assert_current_world_intact()

    def test_malformed_marker_fails_cleanly(self):
        self.stage("../../etc/passwd")
        self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assert_current_world_intact()
        self.assertFalse(self.layout.pending_marker.exists())

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_failure_after_one_half_is_replaced_rolls_both_back(self):
        self.stage()

        def half_way(swap):
            first = sorted(os.listdir(swap.art_staging))[0]
            os.rename(swap.art_staging / first, swap.layout.art_root / first)
            swap.installed_art.append(first)
            raise OSError("volume vanished")

        with mock.patch("server.saves.restore.install_art", side_effect=half_way):
            self.assert_failed_cleanly()
        self.assertIn("volume vanished", self.result()["reason"])

    def test_failed_rollback_stops_startup_and_keeps_the_originals(self):
        self.stage()
        with mock.patch("server.saves.restore.install_art", side_effect=OSError("boom")), mock.patch.object(
            restore.Swap, "rollback", side_effect=restore.RollbackFailed("read-only volume")
        ):
            self.assertEqual(self.apply(), restore.EXIT_UNSAFE)
        self.assertEqual(self.result()["rollback"], "failed")
        self.assertTrue((self.layout.art_root / ".restore-aside").is_dir())

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_a_failed_rollback_keeps_stopping_every_later_start(self):
        self.stage()
        with mock.patch("server.saves.restore.install_art", side_effect=OSError("boom")), mock.patch.object(
            restore.Swap, "rollback", side_effect=restore.RollbackFailed("read-only volume")
        ):
            self.assertEqual(self.apply(), restore.EXIT_UNSAFE)
        self.assertFalse(self.layout.pending_marker.exists())
        # No marker any more, but the originals still sit aside: never start.
        self.assertEqual(self.apply(), restore.EXIT_UNSAFE)
        self.assertEqual(self.apply(), restore.EXIT_UNSAFE)

    def test_a_cleanup_failure_after_a_committed_swap_still_starts(self):
        self.stage()
        real_rmtree = restore._rmtree

        def stubborn(path):
            if path.name == ".restore-aside" and path.parent == self.layout.art_root:
                raise OSError("busy")
            return real_rmtree(path)

        with mock.patch("server.saves.restore._rmtree", side_effect=stubborn):
            self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assertEqual(self.result()["outcome"], "restored")
        self.assertFalse(self.layout.pending_marker.exists())
        self.assertFalse((self.layout.art_root / ".restore-aside").exists())
        kept = [p.name for p in self.layout.art_root.iterdir() if p.name.startswith(".restore-done-")]
        self.assertEqual(len(kept), 1)
        self.assertEqual(self.apply(), restore.EXIT_OK)

    def test_only_manifest_listed_art_is_installed(self):
        (self.layout.art_dir(self.save.id) / "scene/stray.webp").write_bytes(b"stray")
        os.symlink("/etc/hostname", self.layout.art_dir(self.save.id) / "scene/link.webp")
        self.stage()
        self.assertEqual(self.apply(), restore.EXIT_OK)
        self.assertFalse((self.layout.art_root / "scene/stray.webp").exists())
        self.assertFalse((self.layout.art_root / "scene/link.webp").is_symlink())
        self.assertEqual((self.layout.art_root / "scene/forest.webp").read_bytes(), b"forest-saved")

    def test_stale_aside_from_an_interrupted_run_stops_startup(self):
        (self.layout.art_root / ".restore-aside").mkdir()
        self.stage()
        self.assertEqual(self.apply(), restore.EXIT_UNSAFE)
        self.assert_current_world_intact()

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result", "gm-save-management::save-operational-observability")
    def test_tool_runs_without_django_evennia_or_the_facade(self):
        self.stage()
        blocker = (
            "import sys, runpy\n"
            "class Block:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name.split('.')[0] in {'django', 'evennia', 'twisted'} or name.startswith('world.observability'):\n"
            "            raise ImportError('blocked: ' + name)\n"
            "        return None\n"
            "sys.meta_path.insert(0, Block())\n"
            "sys.argv = ['restore', '--apply-pending', '--project-root', sys.argv[1]]\n"
            "runpy.run_module('server.saves.restore', run_name='__main__')\n"
        )
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        completed = subprocess.run(
            [sys.executable, "-c", blocker, str(self.world.root)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(f"restored save {self.save.id}", completed.stdout)
        self.assertEqual(self.world.read_state(), "original")


class LauncherContractTests(unittest.TestCase):
    def commands(self, relative):
        lines = (REPO_ROOT / relative).read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]

    def assert_restore_precedes_migrate(self, relative, restore_line, migrate_line):
        commands = self.commands(relative)
        self.assertIn(restore_line, commands)
        self.assertIn(migrate_line, commands)
        self.assertLess(commands.index(restore_line), commands.index(migrate_line))

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_serve_script_applies_pending_restore_before_migrate(self):
        self.assert_restore_precedes_migrate(
            "scripts/serve.sh",
            "uv run --locked python -m server.saves.restore --apply-pending",
            "uv run --locked evennia migrate --noinput",
        )

    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_container_entrypoint_applies_pending_restore_before_migrate(self):
        self.assert_restore_precedes_migrate(
            "docker-entrypoint.sh",
            "python -m server.saves.restore --apply-pending",
            "evennia migrate --noinput",
        )
        self.assertIn("set -eu", self.commands("docker-entrypoint.sh"))
