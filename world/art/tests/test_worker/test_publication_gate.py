"""The art publication gate a world snapshot holds (gm-portal-s5-saves)."""

import threading
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from world.art import publication
from world.art import queue as art_queue
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.scheduler import ArtDrainScript
from world.art.store import ArtAssetStatus
from world.art.worker import _write_temp, drain, drain_synchronous

from ._support import WorkerStoreIsolation
from tools.spec_traceability import covers_requirement


def _gate_free_elsewhere() -> bool:
    """Whether another thread could take the gate right now."""
    result = []

    def probe():
        acquired = publication._gate.acquire(timeout=0.05)
        if acquired:
            publication._gate.release()
        result.append(acquired)

    thread = threading.Thread(target=probe)
    thread.start()
    thread.join()
    return result[0]


class PublicationGateTests(WorkerStoreIsolation):
    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history")
    def test_drains_and_scheduler_ticks_are_no_ops_while_paused(self):
        subject = self._subject()
        self._record(subject)
        with override_settings(ART_SCHEDULER_ENABLED=True), patch("world.art.worker.drain") as patched:
            script, errors = ArtDrainScript.create("art_drain_gate_test")
            self.assertEqual(errors, [])
            with publication.paused():
                script.at_repeat()
                patched.assert_not_called()
            script.at_repeat()
            patched.assert_called_once()
        with publication.paused():
            self.assertEqual(drain(4), 0)
            self.assertEqual(drain_synchronous(4), 0)
        self.assertEqual(self._record_for(subject).db.status, ArtAssetStatus.PENDING)
        self.assertFalse(publication.is_paused())

    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history")
    def test_the_settle_and_its_file_replace_run_inside_the_gate(self):
        subject = self._subject()
        self._record(subject)
        observed = []
        real_classic = art_queue.settle_generated
        real_gallery = art_queue.settle_gallery_generated

        def watch(real):
            def watching(*args, **kwargs):
                observed.append(_gate_free_elsewhere())
                return real(*args, **kwargs)

            return watching

        with (
            self._client(FakeSDWebUIClient()),
            patch("world.art.worker.settle_generated", side_effect=watch(real_classic)),
            patch("world.art.worker.settle_gallery_generated", side_effect=watch(real_gallery)),
        ):
            self.assertEqual(drain_synchronous(1), 1)
        self.assertEqual(observed, [False])
        self.assertEqual(self._record_for(subject).db.status, ArtAssetStatus.DONE)

    @covers_requirement("gm-save-management::consistent-snapshots-without-damaged-art-history")
    def test_a_store_write_waits_for_a_running_snapshot(self):
        written = []

        def run_writer():
            written.append(_write_temp("scene/t_synth_gate.png", b"bytes"))

        with publication.paused():
            writer = threading.Thread(target=run_writer)
            writer.start()
            writer.join(0.3)
            self.assertTrue(writer.is_alive())
            self.assertEqual([p for p in self.root.rglob("*") if p.is_file()], [])
        writer.join(10)
        self.assertEqual(len(written), 1)
        self.assertEqual(Path(written[0]).read_bytes(), b"bytes")

    def test_a_card_file_unlink_is_deferred_rather_than_freezing_behind_a_snapshot(self):
        from world.art import gallery
        from world.art.subjects import ArtSubject, ArtSubjectKind

        identity = "gallery/character/t_synth_gate/a.png"
        path = self.root / identity
        path.parent.mkdir(parents=True)
        path.write_bytes(b"card")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_synth_gate")
        held, release = threading.Event(), threading.Event()

        def snapshot():
            with publication.paused():
                held.set()
                release.wait(10)

        holder = threading.Thread(target=snapshot)
        holder.start()
        held.wait(5)
        try:
            with patch.object(gallery, "_SNAPSHOT_WAIT_SECONDS", 0.05), patch.object(gallery, "log_warn") as log_warn:
                gallery._delete_stored_file(subject, identity)
        finally:
            release.set()
            holder.join()
        self.assertEqual(path.read_bytes(), b"card")
        self.assertEqual(log_warn.call_args.args[0], "gallery_card_file_delete_deferred")
        gallery._delete_stored_file(subject, identity)
        self.assertFalse(path.exists())
