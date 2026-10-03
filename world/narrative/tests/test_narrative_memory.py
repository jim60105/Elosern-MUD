"""Tests for owner-scoped memory records, append-only revisions, and idempotent projection."""

from unittest.mock import patch
from django.db import IntegrityError, transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.narrative.events import record_narrative_event
from world.narrative.memory import (
    NarrativeMemoryImmutabilityError,
    NarrativeMemoryPermissionError,
    get_owner_generation,
    get_owner_memories,
    process_pending_narrative_memory_projections,
    project_narrative_event_to_memories,
    record_memory,
    revise_memory,
    supersede_memory,
)
from world.narrative.models import (
    MemoryRecord,
    MemoryRevision,
    NarrativeEvent,
    OwnerMemoryGeneration,
    ProjectionProgress,
)


class NarrativeOwnerMemoryTests(EvenniaTestCase):
    """Test owner cognition persistence, revisions, access views, and projection."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="MemoryTestRoom")
        self.player = create_object(PlayerCharacter, key="MemoryPlayer", location=self.room)
        self.observer_npc = create_object(NPC, key="ObserverNPC", location=self.room)
        self.uninformed_npc = create_object(NPC, key="UninformedNPC", location=self.room)

    def test_record_memory_basic_and_immutability(self):
        """Owner cognition preserves immutable content and provenance."""
        record, revision, created = record_memory(
            owner_id=str(self.player.pk),
            content={"summary": "Saw an ancient statue in the ruins"},
            tick=100,
            category="observation",
            tier="working",
            salience=2,
            knowledge_scope="witnessed",
            confidence=1.0,
            subjects=["ancient_statue"],
            source_id="test_source_1",
        )
        self.assertTrue(created)
        self.assertEqual(record.owner_id, str(self.player.pk))
        self.assertEqual(record.content["summary"], "Saw an ancient statue in the ruins")
        self.assertEqual(revision.revision_number, 1)
        self.assertEqual(revision.availability, "active")
        self.assertEqual(get_owner_generation(str(self.player.pk)), 1)

        # Verify attempting to mutate immutable fields raises ValueError
        record.content = {"summary": "Altered memory text"}
        with self.assertRaises(ValueError):
            record.save()

    def test_revisions_and_supersession(self):
        """Scenario: Supersession changes normal results.

        WHEN a record is superseded
        THEN normal access excludes it, historical access preserves provenance, and owner generation increases.
        """
        owner = str(self.player.pk)
        rec1, rev1, _ = record_memory(
            owner_id=owner,
            content={"belief": "The castle north is abandoned"},
            tick=10,
            category="belief",
            knowledge_scope="inferred",
        )
        gen_after_create = get_owner_generation(owner)
        self.assertEqual(gen_after_create, 1)

        rec2, rev2, _ = record_memory(
            owner_id=owner,
            content={"belief": "The castle north is inhabited by bandits"},
            tick=20,
            category="belief",
            knowledge_scope="witnessed",
        )
        self.assertEqual(get_owner_generation(owner), 2)

        # Supersede rec1 with rec2
        supersede_memory(old_record=rec1, new_record=rec2)

        gen_after_supersede = get_owner_generation(owner)
        self.assertGreater(gen_after_supersede, 2)

        # Normal access excludes superseded record
        normal_views = get_owner_memories(owner_id=owner, requester_id=owner)
        normal_ids = [v.id for v in normal_views]
        self.assertNotIn(rec1.id, normal_ids)
        self.assertIn(rec2.id, normal_ids)

        # Historical access includes superseded record with preserved provenance
        historical_views = get_owner_memories(
            owner_id=owner,
            requester_id=owner,
            include_superseded=True,
        )
        hist_ids = [v.id for v in historical_views]
        self.assertIn(rec1.id, hist_ids)
        self.assertIn(rec2.id, hist_ids)

        # Original content is untouched
        rec1_view = next(v for v in historical_views if v.id == rec1.id)
        self.assertEqual(rec1_view.content["belief"], "The castle north is abandoned")
        self.assertEqual(rec1_view.availability, "superseded")
        self.assertEqual(rec1_view.knowledge_scope, "inferred")

    def test_permission_and_privacy_boundaries(self):
        """Access distinguishes knowledge scopes and excludes private authoring or other owners' private cognition."""
        owner = str(self.observer_npc.pk)
        other = str(self.uninformed_npc.pk)

        # Private memory of observer
        record_memory(
            owner_id=owner,
            content={"secret": "Observer's private thought"},
            category="observation",
            knowledge_scope="witnessed",
        )

        # Public memory of observer
        record_memory(
            owner_id=owner,
            content={"notice": "Town hall announcement"},
            category="observation",
            knowledge_scope="public",
        )

        # Private authoring draft record
        record_memory(
            owner_id=owner,
            content={"draft": "Unconfirmed dream direction"},
            category="private_authoring",
            knowledge_scope="inferred",
        )

        # Requester is observer themselves: sees private + public, excludes authoring
        views_self = get_owner_memories(owner_id=owner, requester_id=owner)
        self.assertEqual(len(views_self), 2)
        categories = {v.category for v in views_self}
        self.assertNotIn("private_authoring", categories)

        # Requester is another character: cannot see private cognition
        views_other = get_owner_memories(owner_id=owner, requester_id=other)
        self.assertEqual(len(views_other), 0)

        # Public scope query across owners
        views_public = get_owner_memories(owner_id=owner, requester_id=other, scope="public")
        self.assertEqual(len(views_public), 1)
        self.assertEqual(views_public[0].content["notice"], "Town hall announcement")

    def test_scenario_only_an_observer_learns_protection(self):
        """Scenario: Only an observer learns protection.

        WHEN one synthetic NPC witnesses protection and another does not
        THEN only the eligible observer gains witnessed memory.
        """
        source_id = "encounter:sess_prot_1:settlement:1"
        event, progress, _ = record_narrative_event(
            source_id=source_id,
            event_type="encounter_protection",
            content={
                "encounter_outcome": "victory",
                "protected_keys": [self.observer_npc.key],
                "mode": "hostile",
                "rounds_elapsed": 2,
            },
            participants=[str(self.player.pk), str(self.observer_npc.pk)],
            location=str(self.room.pk),
            tick=50,
            visibility="public",
            salience=2,
            projector_version=1,
        )

        project_narrative_event_to_memories(event, projector_version=1)

        # Observer NPC has witnessed memory
        obs_memories = get_owner_memories(
            owner_id=str(self.observer_npc.pk),
            requester_id=str(self.observer_npc.pk),
        )
        self.assertEqual(len(obs_memories), 1)
        self.assertEqual(obs_memories[0].knowledge_scope, "witnessed")
        self.assertEqual(obs_memories[0].category, "encounter")
        self.assertEqual(obs_memories[0].source_id, source_id)

        # Player participant also has witnessed memory
        player_memories = get_owner_memories(
            owner_id=str(self.player.pk),
            requester_id=str(self.player.pk),
        )
        self.assertEqual(len(player_memories), 1)
        self.assertEqual(player_memories[0].knowledge_scope, "witnessed")

        # Uninformed NPC was not a participant; gains no memory
        uninformed_memories = get_owner_memories(
            owner_id=str(self.uninformed_npc.pk),
            requester_id=str(self.uninformed_npc.pk),
        )
        self.assertEqual(len(uninformed_memories), 0)

    def test_scenario_claim_is_not_fact(self):
        """Scenario: Claim is not fact.

        WHEN a source claims a dragon exists without authoritative evidence
        THEN the memory records being told the claim and creates no dragon.
        """
        source_id = "claim:letter:dragon_in_cave:1"
        event, progress, _ = record_narrative_event(
            source_id=source_id,
            event_type="claim_receipt",
            content={
                "claimant": "OldTraveler",
                "statement": "A great red dragon slumbers in the northern caldera",
                "recipients": [str(self.player.pk)],
            },
            participants=[str(self.player.pk)],
            tick=120,
            visibility="private",
            salience=2,
            projector_version=1,
        )

        project_narrative_event_to_memories(event, projector_version=1)

        # Player has told memory
        player_mems = get_owner_memories(
            owner_id=str(self.player.pk),
            requester_id=str(self.player.pk),
        )
        self.assertEqual(len(player_mems), 1)
        mem = player_mems[0]
        self.assertEqual(mem.knowledge_scope, "told")
        self.assertEqual(mem.category, "claim")
        self.assertIn("Told by OldTraveler", mem.content["summary"])

        # No dragon object or world entity was created in the room or database
        from typeclasses.characters import Character
        self.assertFalse(Character.objects.filter(db_key__icontains="dragon").exists())

    def test_scenario_restart_after_failed_projection(self):
        """Scenario: Restart after failed projection.

        WHEN projection fails before its transaction commits and restarts
        THEN progress stays pending and success creates one record per eligible owner/source.
        """
        source_id = "encounter:restart_fail_sess:round:1"
        event, progress, _ = record_narrative_event(
            source_id=source_id,
            event_type="encounter_protection",
            content={"encounter_outcome": "victory"},
            participants=[str(self.player.pk)],
            tick=200,
            projector_version=1,
        )
        self.assertEqual(progress.status, "pending")

        # Simulate a crash during projection: transaction rolls back
        try:
            with transaction.atomic():
                # Call record_memory then fail
                record_memory(
                    owner_id=str(self.player.pk),
                    content={"test": 1},
                    source_id=source_id,
                    projector_version=1,
                )
                raise RuntimeError("Simulated mid-flight crash/restart")
        except RuntimeError:
            pass

        # Progress should still be pending and zero records committed
        progress.refresh_from_db()
        self.assertEqual(progress.status, "pending")
        self.assertEqual(
            MemoryRecord.objects.filter(source_id=source_id, projector_version=1).count(),
            0,
        )

        # Restart runner scans and processes pending projections
        processed = process_pending_narrative_memory_projections(projector_version=1)
        self.assertGreaterEqual(processed, 1)

        progress.refresh_from_db()
        self.assertEqual(progress.status, "completed")
        self.assertEqual(
            MemoryRecord.objects.filter(source_id=source_id, projector_version=1).count(),
            1,
        )

        # Reprocessing again produces no duplicate records
        processed_again = process_pending_narrative_memory_projections(projector_version=1)
        self.assertEqual(processed_again, 0)
        self.assertEqual(
            MemoryRecord.objects.filter(source_id=source_id, projector_version=1).count(),
            1,
        )
