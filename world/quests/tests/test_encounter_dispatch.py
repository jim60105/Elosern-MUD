"""Production encounter eligibility and activation boundary tests.

The boundary must activate every published encounter whose declared locator
covers the actor's authoritative position, be indexed by owner, resolve the
original owner for a lawfully possessed actor, stay independent of acceptance,
and never raise into the movement/arrival hook that called it.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, Room
from world.quests import scene_store
from world.quests.encounter_dispatch import (
    activate_for_move,
    activate_pending_encounters,
    pending_encounters,
    resolve_exploring_owner,
    sync_connected_owners,
)
from world.quests.encounters import publish_scene_package
from world.quests.escort_events import escort_event_boundary
from world.quests.tests._compile_helpers import _anchor_key
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.quests.tests._scene_package_fixtures import package as _package


class EncounterDispatchTestBase(RegistryIsolationMixin, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="訪客")
        self.room = create_object(AnchorRoom, key="南門")
        self.room.db.anchor_key = _anchor_key()
        self.elsewhere = create_object(Room, key="別處")
        self.published = publish_scene_package(
            _package(), owner=str(self.player.pk)
        )
        self.package_id = self.published.package_id


class EligibilityTests(EncounterDispatchTestBase):
    def test_both_declared_encounters_are_eligible_at_the_anchor(self):
        eligible = pending_encounters(self.player, room=self.room)
        self.assertEqual(
            {scene_id for _, scene_id in eligible}, {"south_gate", "market"}
        )
        for package_id, _ in eligible:
            self.assertEqual(package_id, self.package_id)

    def test_a_non_matching_position_is_not_eligible(self):
        self.assertEqual(pending_encounters(self.player, room=self.elsewhere), ())

    def test_lookup_is_scoped_to_the_owning_player(self):
        other = create_object(PlayerCharacter, key="他人")
        self.assertEqual(pending_encounters(other, room=self.room), ())

    def test_a_declared_prerequisite_fact_filter_excludes_unrelated_scenes(self):
        self.assertEqual(
            pending_encounters(self.player, room=self.room, prerequisite_fact="closure"),
            (),
        )

    def test_an_already_activated_scene_is_no_longer_pending(self):
        activate_pending_encounters(self.player, room=self.room, tick=5)
        self.assertEqual(pending_encounters(self.player, room=self.room), ())


class ActivationTests(EncounterDispatchTestBase):
    def test_post_publication_activation_at_the_current_position(self):
        activations = activate_pending_encounters(self.player, room=self.room, tick=5)
        self.assertEqual(
            {activation.scene_id for activation in activations},
            {"south_gate", "market"},
        )
        for activation in activations:
            self.assertTrue(activation.activated)
            self.assertTrue(activation.created)
        binding = scene_store.get_role_binding(self.package_id, "daughter")
        self.assertIsNotNone(binding)
        row = scene_store.get_encounter(self.package_id, "south_gate", self.player.pk)
        self.assertIsNotNone(row)
        self.assertEqual(row.state, scene_store.ENCOUNTER_ACTIVATED)
        # Publication alone never accepted a commission for this player.
        from world.quests.runtime import read_records

        self.assertEqual(read_records(self.player), [])

    def test_repeat_entry_activates_once(self):
        first = activate_pending_encounters(self.player, room=self.room, tick=5)
        second = activate_pending_encounters(self.player, room=self.room, tick=6)
        self.assertEqual(len(first), 2)
        self.assertEqual(second, ())
        binding = scene_store.get_role_binding(self.package_id, "daughter")
        again = scene_store.get_role_binding(self.package_id, "daughter")
        self.assertEqual(binding.npc_id, again.npc_id)

    def test_wrong_position_writes_nothing(self):
        self.assertEqual(
            activate_pending_encounters(self.player, room=self.elsewhere, tick=5), ()
        )
        self.assertEqual(scene_store.list_role_bindings(self.package_id), [])
        self.assertIsNone(
            scene_store.get_encounter(self.package_id, "south_gate", self.player.pk)
        )

    def test_a_refused_activation_never_raises_into_the_caller(self):
        with patch(
            "world.quests.encounter_dispatch.activate_scene_encounter",
            side_effect=RuntimeError("store exploded"),
        ) as call:
            self.assertEqual(
                activate_pending_encounters(self.player, room=self.room, tick=5), ()
            )
        # One candidate's failure never stops the remaining eligible scenes:
        # both declared encounters were attempted, each in its own savepoint.
        self.assertEqual(call.call_count, 2)
        # Nothing was committed and the package store is still usable.
        self.assertEqual(scene_store.list_role_bindings(self.package_id), [])
        self.assertEqual(
            scene_store.packages_for_owner(str(self.player.pk))[0].package_id,
            self.package_id,
        )

    def test_instance_layer_encounter_activates_from_the_origin_room(self):
        from typeclasses.rooms import InstanceRoom

        payload = _package()
        payload["source_id"] = "synthetic-instance-source"
        payload["encounters"][0]["locator"] = {"layer": "instance"}
        published = publish_scene_package(payload, owner=str(self.player.pk))
        origin = create_object(Room, key="村口")
        activations = activate_pending_encounters(self.player, room=origin, tick=11)
        self.assertEqual(
            [activation.scene_id for activation in activations], ["south_gate"]
        )
        self.assertTrue(activations[0].activated)
        # The one instance room the activation created is the recorded locator.
        self.assertEqual(InstanceRoom.objects.all().count(), 1)
        row = scene_store.get_encounter(published.package_id, "south_gate", self.player.pk)
        self.assertEqual(row.state, scene_store.ENCOUNTER_ACTIVATED)
        self.assertEqual(row.room_id, activations[0].room_id)

    def test_possessed_exploration_keeps_the_original_owner(self):
        companion = create_object(NPC, key="同伴", location=self.room)
        companion.db.possessed_by = int(self.player.pk)
        self.assertIs(resolve_exploring_owner(companion), self.player)
        activations = activate_pending_encounters(companion, room=self.room, tick=7)
        self.assertTrue(activations)
        # Ownership remains the original player: the runtime identity is theirs.
        row = scene_store.get_encounter(self.package_id, "south_gate", self.player.pk)
        self.assertIsNotNone(row)
        self.assertEqual(row.state, scene_store.ENCOUNTER_ACTIVATED)
        self.assertIsNone(
            scene_store.get_encounter(self.package_id, "south_gate", companion.pk)
        )

    def test_an_unresolvable_actor_activates_nothing(self):
        stray = create_object(NPC, key="無主者", location=self.room)
        self.assertIsNone(resolve_exploring_owner(stray))
        self.assertEqual(activate_pending_encounters(stray, room=self.room, tick=5), ())


class StatusSyncTests(EncounterDispatchTestBase):
    """Reconnect and startup synchronize the owner's actual current position."""

    def test_startup_syncs_every_connected_owner(self):
        self.player.location = self.room
        activated = sync_connected_owners(tick=13, characters=[self.player])
        self.assertEqual(
            {activation.scene_id for activation in activated}, {"south_gate", "market"}
        )
        row = scene_store.get_encounter(self.package_id, "south_gate", self.player.pk)
        self.assertEqual(row.state, scene_store.ENCOUNTER_ACTIVATED)

    def test_startup_sync_activates_nothing_for_an_unrelated_position(self):
        self.player.location = self.elsewhere
        self.assertEqual(
            sync_connected_owners(tick=13, characters=[self.player]), ()
        )
        self.assertEqual(scene_store.list_role_bindings(self.package_id), [])

    def test_startup_sync_delivers_the_latest_durable_status(self):
        from unittest.mock import Mock

        from world.narrative.models import DreamDispatch

        DreamDispatch.objects.create(
            dispatch_id="dispatch:synthetic-status",
            submission_key="synthetic-status:v1",
            owner_id=str(self.player.pk),
            state="queued",
        )
        self.player.msg = Mock()
        sync_connected_owners(tick=13, characters=[self.player])
        sent = [call.args[0] for call in self.player.msg.call_args_list]
        self.assertTrue(any("準備中" in message for message in sent), sent)

    def test_startup_sync_with_no_connected_owner_activates_nothing(self):
        self.assertEqual(sync_connected_owners(tick=13, characters=[]), ())


class MoveHookTests(EncounterDispatchTestBase):
    def test_move_hook_activates_outside_the_movement_boundary(self):
        self.player.location = self.room
        activations = activate_for_move(self.player, tick=9)
        self.assertTrue(activations)

    def test_move_hook_is_skipped_inside_the_settled_movement_boundary(self):
        # The enclosing boundary activates once, after the movement settles and
        # the clock is charged: a second mid-traversal pass would settle at the
        # wrong tick and must not run.
        with escort_event_boundary((self.player,)):
            self.assertEqual(activate_for_move(self.player, tick=3), ())
        self.assertEqual(scene_store.list_role_bindings(self.package_id), [])
