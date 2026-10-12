"""Revisioned phase-transition tests (quest-scene-encounters 1.3/4.3).

Selection must be complete and deterministic, the revision monotonic, a stale
expected revision refused without a write, a fabricated result observation
refused, and truthful permitted information transfer recorded through the
narrative owner.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom
from world.quests import scene_store
from world.quests.encounter_activation import activate_scene_encounter
from world.quests.encounters import publish_scene_package
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

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
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

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
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

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
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

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
    def test_a_fabricated_reunion_observation_is_refused(self):
        # The guard on the ``reunion`` name was released by escort-rendezvous,
        # its owning change; a caller still cannot assert a reunion the
        # committed exclusive-result state does not hold.
        with self.assertRaises(StoryDialogueError):
            transition_story_dialogue(
                self.package_id,
                "daughter",
                expected_revision=0,
                provenance={"reunion": True},
                tick=7,
            )

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
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

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
    def test_transferring_a_roles_own_claim_is_a_no_op(self):
        self.assertFalse(
            transfer_story_knowledge(
                self.package_id, "daughter", "seeking", tick=9
            )
        )

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
    def test_a_committed_result_records_knowledge_and_advances_acknowledgment(self):
        from world.narrative.memory import get_owner_memories
        from world.quests import outcome_store
        from world.quests.story_dialogue import commit_reunion_participation

        outcome_store.mark_group_resolved(
            owner_id=1, package_id=self.package_id, group_id="reunion",
            resolution_source="s", winner_quest_id="q:1",
        )
        commit_reunion_participation(
            self.package_id, ("daughter",), group_id="reunion", winner_quest_id="q:1",
        )
        self.assertEqual(
            scene_store.get_dialogue_phase(
                self.package_id, "daughter"
            ).selected_phase,
            "acknowledgment",
        )
        daughter = scene_store.get_role_binding(self.package_id, "daughter").npc_id
        memories = get_owner_memories(owner_id=str(daughter))
        self.assertTrue(any(m.content.get("result") == "q:1" for m in memories))
        # A replay records nothing further and keeps the committed phase.
        commit_reunion_participation(
            self.package_id, ("daughter",), group_id="reunion", winner_quest_id="q:1",
        )
        self.assertEqual(
            scene_store.get_dialogue_phase(
                self.package_id, "daughter"
            ).selected_phase,
            "acknowledgment",
        )

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
    def test_the_closure_interaction_after_reunion_advances_to_everyday(self):
        from world.quests import outcome_store
        from world.quests.story_dialogue import commit_reunion_participation

        outcome_store.mark_group_resolved(
            owner_id=1, package_id=self.package_id, group_id="reunion",
            resolution_source="s", winner_quest_id="q:1",
        )
        commit_reunion_participation(
            self.package_id, ("daughter",), group_id="reunion", winner_quest_id="q:1",
        )
        # The subsequent authorized closure interaction advances to everyday.
        closed = transition_story_dialogue(
            self.package_id, "daughter", expected_revision=1,
            provenance={"closure": True}, tick=8,
        )
        self.assertEqual(closed.phase_id, "everyday")

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
    def test_result_knowledge_stays_private_to_the_participant(self):
        from world.narrative.memory import get_owner_memories
        from world.quests import outcome_store
        from world.quests.story_dialogue import commit_reunion_participation

        outcome_store.mark_group_resolved(
            owner_id=1, package_id=self.package_id, group_id="reunion",
            resolution_source="s", winner_quest_id="q:1",
        )
        commit_reunion_participation(
            self.package_id, ("daughter",), group_id="reunion", winner_quest_id="q:1",
        )
        # An actor that did not participate receives no result knowledge.
        outsider = create_object(PlayerCharacter, key="旁人")
        self.assertFalse(
            any(
                memory.content.get("result") == "q:1"
                for memory in get_owner_memories(owner_id=str(outsider.pk))
            )
        )

    @covers_requirement(
        "story-phase-dialogue::phase-selection-uses-committed-outcomes-and-permitted-role-knowledge"
    )
    def test_an_unknown_claim_is_refused(self):
        with self.assertRaises(StoryDialogueError):
            transfer_story_knowledge(
                self.package_id, "daughter", "no_such_claim", tick=9
            )