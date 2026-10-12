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
    def test_activation_refreshes_the_owner_projections_after_commit(self):
        from unittest.mock import patch

        with patch(
            "typeclasses.characters._schedule_projection_refresh_after_activation"
        ) as refresh:
            with self.captureOnCommitCallbacks(execute=True):
                activations = activate_pending_encounters(
                    self.player, room=self.room, tick=5
                )
        self.assertTrue(activations)
        # Post-commit only, and for the owner the activation belongs to.
        refresh.assert_called_once()
        self.assertIs(refresh.call_args.args[0], self.player)

    def test_a_refused_activation_refreshes_no_projection(self):
        from unittest.mock import patch

        with patch(
            "typeclasses.characters._schedule_projection_refresh_after_activation"
        ) as refresh:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(
                    activate_pending_encounters(
                        self.player, room=self.elsewhere, tick=5
                    ),
                    (),
                )
        refresh.assert_not_called()

    def _puppet_owner(self):
        """Give the fixture player a live account, as a puppeted owner has."""
        from evennia.utils.create import create_account

        self.player.account = create_account(
            "投影測試", email="projection@example.test", password="testpassword"
        )
        return self.player

    def test_the_committed_refresh_pushes_every_live_watcher_session(self):
        """The body, not the call site: the watcher pairs reach the push.

        ``watchers_for`` returns ``(session, epoch)`` pairs while the snapshot
        push takes the session, so a pair passed through unpacked would refresh
        nothing and leave a freshly activated occupant invisible until some
        unrelated trigger happened to run.
        """
        from typeclasses.characters import (
            _schedule_projection_refresh_after_activation,
        )

        session = object()
        watchers = ((session, "epoch-7"),)
        self._puppet_owner()
        with patch(
            "web.webclient.presentation.watchers.watchers_for", return_value=watchers
        ) as watchers_for, patch(
            "server.option_proposal_service.schedule_action_options"
        ) as schedule, patch(
            "web.webclient.presentation.ingress.refresh_after_command"
        ) as refresh:
            _schedule_projection_refresh_after_activation(self.player)
        watchers_for.assert_called_once_with(self.player)
        schedule.assert_called_once_with(self.player, watchers=watchers)
        refresh.assert_called_once_with(session, self.player)

    def test_an_offline_or_non_player_owner_refreshes_no_projection(self):
        from typeclasses.characters import (
            _schedule_projection_refresh_after_activation,
        )

        with patch("web.webclient.presentation.watchers.watchers_for") as watchers_for:
            _schedule_projection_refresh_after_activation(
                create_object(NPC, key="路人")
            )
            watchers_for.assert_not_called()
        # A player character with no live session keeps its durable state for
        # the reconnect sync instead of pushing into a session that is gone.
        self.player.account = None
        with patch("web.webclient.presentation.watchers.watchers_for") as watchers_for:
            _schedule_projection_refresh_after_activation(self.player)
            watchers_for.assert_not_called()

    def test_a_failing_refresh_is_a_bounded_diagnostic_and_never_raises(self):
        from typeclasses.characters import (
            _schedule_projection_refresh_after_activation,
        )

        self._puppet_owner()
        with patch(
            "web.webclient.presentation.watchers.watchers_for",
            side_effect=RuntimeError("no session handler"),
        ), patch("typeclasses.characters.log_warn") as warn:
            _schedule_projection_refresh_after_activation(self.player)
        self.assertEqual(
            warn.call_args.args[0], "scene_activation_projection_refresh_failed"
        )

    def test_a_lost_definition_view_is_restored_before_activation(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.quests.encounters import ensure_package_views

        key = self.published.definition_key
        # Simulate the divergence this recovery exists for: the durable package
        # survives while the process-local registry lost its view.
        self.assertIsNotNone(QUEST_DEFINITION_REGISTRY.pop(key, None))
        self.assertTrue(ensure_package_views(self.package_id))
        self.assertIn(key, QUEST_DEFINITION_REGISTRY)
        # Idempotent once registered, and an unknown package is not a target.
        self.assertFalse(ensure_package_views(self.package_id))
        self.assertFalse(ensure_package_views("synthetic-unknown-package"))
        # The activation boundary repairs it by itself, without a caller flag.
        QUEST_DEFINITION_REGISTRY.pop(key, None)
        activations = activate_pending_encounters(self.player, room=self.room, tick=5)
        self.assertTrue(activations)
        self.assertIn(key, QUEST_DEFINITION_REGISTRY)

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

    def test_each_activation_announces_the_owner_package_scene_and_room(self):
        """Owns the activation half of the observability delta's added
        correlated-boundary-event requirement; its canonical id is attached
        when that delta syncs at archive."""
        info: list[tuple[str, dict]] = []

        def record(event, *, context=None, exc=None):
            info.append((event, dict(context or {})))

        with patch(
            "world.quests.encounter_dispatch.log_info", side_effect=record
        ):
            with self.captureOnCommitCallbacks(execute=True):
                activations = activate_pending_encounters(
                    self.player, room=self.room, tick=5
                )
        self.assertEqual(len(info), len(activations))
        for (event, context), activation in zip(
            sorted(info, key=lambda item: item[1]["scene"]),
            sorted(activations, key=lambda item: item.scene_id),
        ):
            self.assertEqual(event, "scene_encounter_activated_from_boundary")
            self.assertEqual(context["char"], str(self.player.pk))
            self.assertEqual(context["package"], self.package_id)
            self.assertEqual(context["scene"], activation.scene_id)
            self.assertEqual(context["room"], str(self.room.pk))
            self.assertEqual(context["tick"], "5")

    def test_a_failed_scene_is_reported_as_a_bounded_diagnostic(self):
        warn: list[tuple[str, dict]] = []

        def record(event, *, context=None, exc=None):
            warn.append((event, dict(context or {})))

        with patch(
            "world.quests.encounter_dispatch.activate_scene_encounter",
            side_effect=RuntimeError("store exploded"),
        ), patch("world.quests.encounter_dispatch.log_warn", side_effect=record):
            self.assertEqual(
                activate_pending_encounters(self.player, room=self.room, tick=5), ()
            )
        self.assertEqual(
            [event for event, _ in warn],
            ["scene_encounter_activation_failed", "scene_encounter_activation_failed"],
        )
        for _, context in warn:
            self.assertEqual(context["char"], str(self.player.pk))
            self.assertEqual(context["package"], self.package_id)
            self.assertIn(context["scene"], {"south_gate", "market"})
            self.assertEqual(context["tick"], "5")

    def test_a_rolled_back_activation_schedules_no_projection_refresh(self):
        """A compensated activation publishes no new occupant.

        The refresh is registered through ``on_commit``, so a failed activation
        write rolls the registration back with it and the player's window keeps
        the authoritative prior state.
        """
        with patch(
            "world.quests.encounter_dispatch.activate_scene_encounter",
            side_effect=RuntimeError("store exploded"),
        ), patch(
            "typeclasses.characters._schedule_projection_refresh_after_activation"
        ) as refresh:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(
                    activate_pending_encounters(self.player, room=self.room, tick=5), ()
                )
        refresh.assert_not_called()

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


class SettledTraversalOrderingTests(EncounterDispatchTestBase):
    """The meeting role exists before the receipt's final evaluation runs.

    A settled traversal activates the published encounters its new position
    reaches inside the movement receipt, and the receipt's trailing escort/
    outcome evaluation must then observe the materialized role: the ordering is
    the whole point of activating there rather than after the receipt.
    """

    def test_a_settled_traversal_materializes_the_role_before_the_final_evaluation(self):
        import world.quests.escort_events as escort_events
        from typeclasses.exits import Exit

        self.player.location = self.elsewhere
        exit_obj = create_object(
            Exit, key="門", location=self.elsewhere, destination=self.room
        )
        observed: list[bool] = []
        real_evaluation = escort_events.evaluate_escort_event

        def observe(*args, **kwargs):
            observed.append(
                scene_store.get_role_binding(self.package_id, "daughter") is not None
            )
            return real_evaluation(*args, **kwargs)

        with patch.object(
            escort_events, "evaluate_escort_event", side_effect=observe
        ):
            with self.captureOnCommitCallbacks(execute=True):
                # The plain-exit lineage returns ``None`` on both branches; the
                # settled location is the success signal.
                exit_obj.at_traverse(self.player, self.room)
        self.assertEqual(self.player.location.pk, self.room.pk)
        # The receipt evaluated once, and by then the declared meeting role was
        # already real at the encountered place.
        self.assertTrue(observed, "the settled receipt ran its final evaluation")
        self.assertEqual(set(observed), {True})
        self.assertEqual(self.player.location.pk, self.room.pk)
        binding = scene_store.get_role_binding(self.package_id, "daughter")
        self.assertIsNotNone(binding)
        # A repeat observation cannot advance a second stage or duplicate the
        # resolution: the same identical pass leaves the binding untouched.
        self.assertEqual(
            scene_store.get_role_binding(self.package_id, "daughter").npc_id,
            binding.npc_id,
        )


class PrerequisiteTriggerTests(EncounterDispatchTestBase):
    """A committed phase moves a declared prerequisite and re-evaluates it."""

    def setUp(self):
        super().setUp()
        self.player.location = self.room
        # Retire the inherited prerequisite-free package so this test observes
        # only the encounters it declares prerequisites for.
        self.assertTrue(scene_store.cancel_package(self.published.package_id))
        payload = _package()
        payload["source_id"] = "synthetic-prerequisite-source"
        for encounter in payload["encounters"]:
            encounter["prerequisites"] = [{"closure": True}]
        self.published = publish_scene_package(payload, owner=str(self.player.pk))
        self.package_id = self.published.package_id
        # Seed the role's committed phase, as materialization would; the
        # transition below advances it to the closure-backed phase.
        scene_store.set_dialogue_phase(
            scene_store.read_package(self.package_id), "daughter", "searching", tick=1
        )

    def test_a_committed_closure_reaches_the_encounters_that_declared_it(self):
        from world.quests.story_dialogue import transition_story_dialogue

        # With the prerequisite unmet and the player already at the locator,
        # nothing activates and no encounter row is written.
        self.assertEqual(
            activate_pending_encounters(self.player, room=self.room, tick=5), ()
        )
        self.assertIsNone(
            scene_store.get_encounter(self.package_id, "south_gate", self.player.pk)
        )
        with self.captureOnCommitCallbacks(execute=True):
            transition = transition_story_dialogue(
                self.package_id,
                "daughter",
                expected_revision=0,
                provenance={"closure": True},
                tick=7,
            )
        self.assertTrue(transition.changed)
        self.assertEqual(transition.phase_id, "everyday")
        # The commit that moved the fact activated exactly the encounters that
        # declared it, without the player re-entering.
        for scene_id in ("south_gate", "market"):
            row = scene_store.get_encounter(
                self.package_id, scene_id, self.player.pk
            )
            self.assertIsNotNone(row, scene_id)
            self.assertEqual(row.state, scene_store.ENCOUNTER_ACTIVATED, scene_id)


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
