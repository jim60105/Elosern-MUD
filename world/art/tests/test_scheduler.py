"""Tests for the periodic art drain scheduler Script."""

from unittest.mock import patch

from django.test import override_settings

from evennia.utils.test_resources import EvenniaTestCase

from world.art.queue import ensure
from world.art.scheduler import ArtDrainScript
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _scene(key):
    return ArtSubject(ArtSubjectKind.SCENE, key)


class ArtSchedulerTests(EvenniaTestCase):
    def _seed(self, *keys):
        for key in keys:
            ensure(_scene(key), f"desc-{key}")

    @covers_requirement("art-queue-worker::the-scheduler-is-settings-configurable-and-disableable")
    def test_disabled_scheduler_never_drains(self):
        self._seed("forest_path", "tavern_interior")
        with (
            override_settings(ART_SCHEDULER_ENABLED=False),
            patch("world.art.worker.drain") as drain,
        ):
            script, errors = ArtDrainScript.create("art_drain_test")
            self.assertEqual(errors, [])
            script.at_repeat()
        drain.assert_not_called()
        pending = [
            record
            for record in ArtAssetRecord.objects.all()
            if record.db.status == ArtAssetStatus.PENDING
        ]
        self.assertEqual(len(pending), 2)

    @covers_requirement("art-queue-worker::the-scheduler-is-settings-configurable-and-disableable")
    def test_enabled_scheduler_drains_up_to_its_limit(self):
        self._seed("forest_path", "tavern_interior", "city_street")
        with (
            override_settings(ART_SCHEDULER_ENABLED=True, ART_SCHEDULER_LIMIT=2),
            patch("world.art.worker.drain") as drain,
        ):
            script, errors = ArtDrainScript.create("art_drain_test")
            self.assertEqual(errors, [])
            script.at_repeat()
        drain.assert_called_once_with(2)

    def test_script_reads_the_interval_from_settings(self):
        with override_settings(ART_SCHEDULER_INTERVAL_SECONDS=17):
            script, errors = ArtDrainScript.create("art_drain_test")
            self.assertEqual(errors, [])
        self.assertEqual(script.interval, 17)
        self.assertTrue(script.start_delay)


if __name__ == "__main__":
    import unittest

    unittest.main()
