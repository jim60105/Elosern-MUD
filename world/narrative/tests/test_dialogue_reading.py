"""Behavior test: narrative-owned authored-dialogue reading state.

Pins the exact Attribute schema and its storage discipline (Shared contract
v2): stable owner/host/topic keys, whole-shape initialization, monotonic
revision, fresh containers, idempotent duplicate completion, save/reload,
generated package-role isolation and a rollback that leaves no stale in-process
completion. ``reading_for`` never creates storage.
"""

from __future__ import annotations

from django.db import transaction

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.lore.dialogue.codec import make_generated_host_key, make_static_host_key
from world.narrative.dialogue_reading import (
    MAX_PENDING_BATCH_TOPICS,
    READING_ATTRIBUTE,
    READING_SCHEMA_VERSION,
    STATUS_ALREADY_SAVED,
    STATUS_SAVED,
    completed_topic_ids,
    read_reading,
    reading_for,
    reading_revision,
    record_completion,
)

_STATIC_HOST = make_static_host_key("t_reading_keeper")
_OTHER_HOST = make_static_host_key("t_reading_other")
_PACKAGE_A_ROLE = make_generated_host_key("pkg_alpha", "keeper")
_PACKAGE_B_ROLE = make_generated_host_key("pkg_beta", "keeper")
_LOCAL_TOPIC = "phase_1.open"
_TOPIC_A = f"t_reading_keeper.topic_01"
_TOPIC_B = f"t_reading_keeper.topic_02"


class DialogueReadingStorageTests(EvenniaTest):
    """The pure reader and the guarded-merge completion writer."""

    def setUp(self) -> None:
        super().setUp()
        self.player = create_object(PlayerCharacter, key="reading player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1

    def _complete(self, *, host_key: str = _STATIC_HOST, topic: str = _TOPIC_A):
        return record_completion(self.player, host_key=host_key, topic_id=topic)

    def _stored(self) -> dict:
        return self.player.attributes.get(READING_ATTRIBUTE)

    def test_reading_for_never_creates_storage(self):
        self.assertIsNone(reading_for(self.player, _STATIC_HOST))
        self.assertEqual(reading_revision(self.player), 0)
        self.assertEqual(completed_topic_ids(self.player, _STATIC_HOST), ())
        self.assertIsNone(self._stored())

    def test_first_completion_creates_the_whole_contract_shape(self):
        outcome = self._complete()
        self.assertEqual(outcome.status, STATUS_SAVED)
        self.assertEqual(outcome.reading_revision, 1)
        raw = self._stored()
        self.assertEqual(set(raw), {"schema_version", "revision", "hosts"})
        self.assertEqual(raw["schema_version"], READING_SCHEMA_VERSION)
        self.assertEqual(raw["revision"], 1)
        host = raw["hosts"][_STATIC_HOST]
        self.assertEqual(set(host), {"initialized", "topics", "pending_batch"})
        # Observation (ever_open/announced) belongs to the notification slice:
        # a reading-only write leaves them false and the batch null.
        self.assertIs(host["initialized"], False)
        self.assertIsNone(host["pending_batch"])
        self.assertEqual(
            host["topics"][_TOPIC_A],
            {"completed": True, "ever_open": False, "announced": False},
        )
        reading = reading_for(self.player, _STATIC_HOST)
        self.assertEqual(reading.completed_topic_ids(), (_TOPIC_A,))
        self.assertFalse(reading.is_completed(_TOPIC_B))

    @covers_requirement(
        "authored-dialogue-reading::"
        "formal-reading-is-persistent-owner-shared-narrative-state"
    )
    def test_revision_increments_only_on_change(self):
        self._complete()
        duplicate = self._complete()
        self.assertEqual(duplicate.status, STATUS_ALREADY_SAVED)
        self.assertEqual(duplicate.reading_revision, 1)
        second = self._complete(topic=_TOPIC_B)
        self.assertEqual(second.status, STATUS_SAVED)
        self.assertEqual(second.reading_revision, 2)
        self.assertEqual(
            completed_topic_ids(self.player, _STATIC_HOST), (_TOPIC_A, _TOPIC_B)
        )

    def test_hosts_are_independent_under_one_owner(self):
        self._complete()
        self._complete(host_key=_OTHER_HOST, topic="t_reading_other.topic_01")
        self.assertEqual(
            completed_topic_ids(self.player, _STATIC_HOST), (_TOPIC_A,)
        )
        self.assertEqual(
            completed_topic_ids(self.player, _OTHER_HOST),
            ("t_reading_other.topic_01",),
        )
        self.assertEqual(reading_revision(self.player), 2)

    def test_owners_are_independent(self):
        other = create_object(PlayerCharacter, key="reading other")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.room1
        self._complete()
        self.assertEqual(completed_topic_ids(other, _STATIC_HOST), ())
        self.assertEqual(reading_revision(other), 0)

    @covers_requirement(
        "authored-dialogue-reading::"
        "generated-reading-persists-by-logical-package-role-identity"
    )
    def test_equal_local_ids_in_different_package_roles_stay_separate(self):
        self._complete(host_key=_PACKAGE_A_ROLE, topic=_LOCAL_TOPIC)
        self.assertEqual(
            completed_topic_ids(self.player, _PACKAGE_A_ROLE), (_LOCAL_TOPIC,)
        )
        self.assertEqual(completed_topic_ids(self.player, _PACKAGE_B_ROLE), ())
        self._complete(host_key=_PACKAGE_B_ROLE, topic=_LOCAL_TOPIC)
        self.assertEqual(
            completed_topic_ids(self.player, _PACKAGE_B_ROLE), (_LOCAL_TOPIC,)
        )
        self.assertEqual(reading_revision(self.player), 2)

    def test_two_connection_merges_accumulate_one_revision_per_change(self):
        # Two connections acknowledge different topics; each merge reads the
        # persisted row under the guarded lock, so neither loses the other.
        first = self._complete(topic=_TOPIC_A)
        second = self._complete(topic=_TOPIC_B)
        self.assertEqual((first.reading_revision, second.reading_revision), (1, 2))
        self.assertEqual(
            set(completed_topic_ids(self.player, _STATIC_HOST)),
            {_TOPIC_A, _TOPIC_B},
        )

    @covers_requirement(
        "authored-dialogue-reading::"
        "generated-reading-persists-by-logical-package-role-identity"
    )
    def test_save_reload_and_rematerialized_owner_keep_reading(self):
        self._complete()
        self.player.attributes.reset_cache()
        reloaded = ObjectDB.objects.get(id=self.player.pk)
        self.assertEqual(completed_topic_ids(reloaded, _STATIC_HOST), (_TOPIC_A,))
        reading = reading_for(reloaded, _STATIC_HOST)
        self.assertTrue(reading.is_completed(_TOPIC_A))
        self.assertEqual(read_reading(reloaded).revision, 1)

    @covers_requirement(
        "authored-dialogue-reading::"
        "generated-reading-persists-by-logical-package-role-identity"
    )
    def test_phase_return_keeps_completion(self):
        phase_topic = "g-phase.topic_01"
        self._complete(host_key=_PACKAGE_A_ROLE, topic=phase_topic)
        # A phase change retires session receipts elsewhere; the same phase
        # returning re-reads the same logical host/topic row unchanged.
        self.player.attributes.reset_cache()
        reloaded = ObjectDB.objects.get(id=self.player.pk)
        self.assertEqual(
            completed_topic_ids(reloaded, _PACKAGE_A_ROLE), (phase_topic,)
        )
        again = record_completion(
            reloaded, host_key=_PACKAGE_A_ROLE, topic_id=phase_topic
        )
        self.assertEqual(again.status, STATUS_ALREADY_SAVED)

    def test_outer_rollback_leaves_no_stale_completion(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self._complete()
                raise RuntimeError("owning write rolled back")
        self.assertIsNone(reading_for(self.player, _STATIC_HOST))
        self.assertIsNone(self._stored())

    def test_corrupt_record_reads_empty_and_a_write_rebuilds_it(self):
        self.player.attributes.add(READING_ATTRIBUTE, {"schema_version": 99})
        self.assertEqual(reading_revision(self.player), 0)
        self.assertIsNone(reading_for(self.player, _STATIC_HOST))
        outcome = self._complete()
        self.assertEqual(outcome.status, STATUS_SAVED)
        self.assertEqual(outcome.reading_revision, 1)
        self.assertEqual(
            completed_topic_ids(self.player, _STATIC_HOST), (_TOPIC_A,)
        )

    def test_unsaved_owner_is_refused(self):
        with self.assertRaises(ValueError):
            record_completion(object(), host_key=_STATIC_HOST, topic_id=_TOPIC_A)

    def test_pending_batch_bound_is_part_of_the_schema(self):
        self.assertGreaterEqual(MAX_PENDING_BATCH_TOPICS, 1)
        self._complete()
        self.assertIsNone(self._stored()["hosts"][_STATIC_HOST]["pending_batch"])
