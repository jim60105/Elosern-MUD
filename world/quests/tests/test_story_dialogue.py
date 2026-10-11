"""Revisioned phase-transition tests (quest-scene-encounters 1.3/4.3).

Selection must be complete and deterministic, the revision monotonic, a stale
expected revision refused without a write, guarded escort/reunion observations
refused, and truthful permitted information transfer recorded through the
narrative owner.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom
from world.quests import scene_store
from world.quests.encounter_activation import activate_scene_encounter
from world.quests.encounters import publish_scene_package
from world.quests.phases import PhaseConditionError
from world.quests.story_dialogue import (
    StalePhaseRevision,
    StoryDialogueError,
    transfer_story_knowledge,
    transition_story_dialogue,
)
from world.quests.tests._compile_helpers import _anchor_key
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.quests.tests._scene_package_fixtures import package as _package


class StoryDialogueTransitionTests(RegistryIsolationMixin, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="訪客")
        self.room = create_object(AnchorRoom, key="南門")
        self.room.db.anchor_key = _anchor_key()
        self.published = publish_scene_package(_package(), owner="tester")
        self.package_id = self.published.package_id
        activate_scene_encounter(
            self.player, self.package_id, "south_gate", room=self.room, tick=5
        )

    def test_a_committed_closure_selects_the_everyday_phase(self):
        result = transition_story_dialogue(
            self.package_id,
            "daughter",
            expected_revision=0,
            provenance={"closure": True},
            tick=7,
        )
        self.assertTrue(result.changed)
        self.assertEqual(result.phase_id, "everyday")
        self.assertEqual(result.revision, 1)
        runtime = scene_store.get_dialogue_phase(self.package_id, "daughter")
        self.assertEqual(runtime.selected_phase, "everyday")
        self.assertEqual(runtime.revision, 1)

    def test_a_stale_expected_revision_is_refused_without_a_write(self):
        transition_story_dialogue(
            self.package_id,
            "daughter",
            expected_revision=0,
            provenance={"closure": True},
            tick=7,
        )
        with self.assertRaises(StalePhaseRevision):
            transition_story_dialogue(
                self.package_id,
                "daughter",
                expected_revision=0,
                provenance={"abandoned": True},
                tick=8,
            )
        runtime = scene_store.get_dialogue_phase(self.package_id, "daughter")
        self.assertEqual(runtime.selected_phase, "everyday")
        self.assertEqual(runtime.revision, 1)

    def test_reselecting_the_current_phase_is_a_no_op(self):
        result = transition_story_dialogue(
            self.package_id,
            "daughter",
            expected_revision=0,
            provenance={},
            tick=7,
        )
        self.assertFalse(result.changed)
        self.assertEqual(result.phase_id, "searching")
        self.assertEqual(result.revision, 0)

    def test_a_guarded_reunion_observation_is_refused(self):
        with self.assertRaises(PhaseConditionError):
            transition_story_dialogue(
                self.package_id,
                "daughter",
                expected_revision=0,
                provenance={"reunion": True},
                tick=7,
            )

    def test_truthful_information_transfer_records_permitted_knowledge(self):
        from world.narrative.memory import get_owner_memories

        daughter = scene_store.get_role_binding(self.package_id, "daughter").npc_id
        self.assertTrue(
            transfer_story_knowledge(
                self.package_id, "daughter", "separation", tick=9
            )
        )
        memories = get_owner_memories(owner_id=str(daughter))
        self.assertTrue(
            any(
                memory.content.get("claim_id") == "separation"
                for memory in memories
            )
        )

    def test_transferring_a_roles_own_claim_is_a_no_op(self):
        self.assertFalse(
            transfer_story_knowledge(
                self.package_id, "daughter", "seeking", tick=9
            )
        )

    def test_an_unknown_claim_is_refused(self):
        with self.assertRaises(StoryDialogueError):
            transfer_story_knowledge(
                self.package_id, "daughter", "no_such_claim", tick=9
            )