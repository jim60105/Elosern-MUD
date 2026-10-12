"""Tests for room-driven quest progress (tasks 7.1-7.6)."""

from typing import Any

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import (
    AnchorRoom,
    GridRoom,
    InstanceRoom,
    Room,
    TerrainRoom,
)
from world.quests import scene_store
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    QuestStage,
    QuestType,
)
from world.quests.room_observation import QuestObservableRoomMixin
from world.quests.runtime import QuestState, accept_quest, read_records, to_storage
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.rules.guild_offers import QuestReward
from world.rules.quest_issuance import (
    QuestIssuance,
    Settlement,
    provision_scoped_issuer,
    register_quest_issuance,
)


def _east_gate_xyz():
    """The capital's east gate room coordinate, probed from the live
    wilderness-entry registry (test-data gate: no authored coordinates)."""
    import importlib

    entries = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    ).values()
    entry = next(entry for entry in entries if entry.gate_for("w") is not None)
    gate = entry.gate_for("w")
    return (*gate.grid_xy, gate.z_map_key)
from world.rules.party import join_party

from ._fixtures import (
    QuestRegistryIsolation,
    accept,
    anchor_locator,
    bound_instance_locator,
    escort,
    grid_locator,
    live_anchor_placement_row,
    quest,
    reach,
    register,
)


class QuestRoomMroTests(unittest.TestCase):
    def test_mixin_adoption_and_wilderness_exclusion(self):
        self.assertIn(QuestObservableRoomMixin, GridRoom.__mro__)
        self.assertIn(QuestObservableRoomMixin, AnchorRoom.__mro__)
        self.assertIn(QuestObservableRoomMixin, InstanceRoom.__mro__)
        self.assertNotIn(QuestObservableRoomMixin, TerrainRoom.__mro__)
        self.assertNotIn(QuestObservableRoomMixin, Room.__mro__)


def reach_stage(destination, index: int = 0):
    return QuestStage(index, reach(destination))


def escort_stage(destination, index: int = 0, roles=("escortee",)):
    return QuestStage(index, escort(destination, protected_role_refs=tuple(roles)))


class EscortOfferMixin:
    """Accept a synthetic ESCORT definition through its own published offer.

    Room arrival advances a REACH stage on its own, but an ESCORT stage is
    decided by the settled escort pass over the exact protected bindings an
    acceptance committed. An escort test therefore publishes a real offer,
    binds its roles and accepts through the deterministic owner instead of
    staging a record nothing would ever evaluate.
    """

    def _protected(self, key: str, location: Any = None) -> NPC:
        npc = create_object(
            NPC, key=key, location=self.room1 if location is None else location
        )
        npc.race = "human"
        npc.apply_race_baseline()
        return npc

    def _accept_escort(self, definition, protected, *, package_id: str):
        """Publish ``definition``'s offer bound to ``protected`` and accept it."""
        objective = definition.stages[0].objective
        issuer = create_object(NPC, key=f"{package_id} issuer", location=self.room1)
        issuer.race = "human"
        issuer.apply_race_baseline()
        content_key = f"{package_id}_issuer"
        issuer_key = provision_scoped_issuer(issuer, content_key=content_key)
        register_quest_issuance(
            QuestIssuance(
                definition_key=definition.key,
                issuer_key=issuer_key,
                reward=QuestReward(copper=1, items=(), merit=0),
                settlement=Settlement.AUTO,
            )
        )
        package, _ = scene_store.publish_package(
            package_id=package_id,
            source_id=None,
            owner_id="fixture",
            payload={
                "roles": [
                    {"role_id": role}
                    for role in ("issuer", *objective.protected_role_refs)
                ],
                "commissions": [
                    {"role_id": "issuer", "issuer_content_key": content_key}
                ],
                "dialogue": [
                    {
                        "role_id": "issuer",
                        "phases": [
                            {
                                "phase_id": "offer",
                                "topics": [
                                    {
                                        "keyword": "escort",
                                        "effect_verb": "offer_commission",
                                        "effect_reference": definition.key,
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "outcome_groups": [],
            },
        )
        scene_store.bind_role(package, "issuer", issuer.pk)
        for role, actor in zip(objective.protected_role_refs, protected):
            scene_store.bind_role(package, role, actor.pk)
        scene_store.ensure_commission_grant(
            package, "issuer", definition.key, issuer_key=issuer_key
        )
        scene_store.assign_grant_actor(package, "issuer", definition.key, issuer.pk)
        scene_store.set_grant_registered(package, "issuer", definition.key, True)
        scene_store.set_dialogue_phase(package, "issuer", "offer")
        return accept_quest(self.player, definition.key, issuer_key)


class RoomArrivalProgressTests(EscortOfferMixin, QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        self.player = create_object(PlayerCharacter, key="room-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1

    def _anchor(self) -> AnchorRoom:
        room = AnchorRoom.objects.filter(db_key="中央廣場").first()
        self.assertIsInstance(room, AnchorRoom)
        return room

    def _grid_room(self, x: int = 1, y: int = 1) -> GridRoom:
        # The city map key comes from the same placement row the locators use.
        room = GridRoom.objects.filter_xyz(xyz=(x, y, live_anchor_placement_row().zcoord)).first()
        self.assertIsNotNone(room)
        return room

    def _companion(self, key: str, room: Any) -> NPC:
        """Bind ``key`` to the player and place it in ``room`` (co-presence)."""
        npc = create_object(NPC, key=key, location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        npc.move_to(room, quiet=True)
        self.assertIs(npc.location, room)
        return npc

    def _enter(self, room):
        self.player.move_to(room, quiet=True)
        self.assertIs(self.player.location, room)

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    def test_anchor_arrival_completes_matching_reach_stage(self):
        definition = register(
            quest(
                "reach_anchor_arrival",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        record = accept(self.player, definition.key)
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        self._companion("同伴", self._anchor())
        self._enter(self._anchor())
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["quest_id"], record.quest_id)

    def test_player_alone_cannot_advance_arrival(self):
        definition = register(
            quest(
                "reach_solo_never",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        accept(self.player, definition.key)
        self._enter(self._anchor())
        self.assertEqual(self._records()[0]["state"], "in_progress")

    @covers_requirement("quest-progress-tracking::room-arrival-drives-reach-and-escort-through-supported-persistent-room-hooks")
    def test_grid_arrival_uses_exact_xyz_identity(self):
        definition = register(
            quest(
                "reach_grid_xyz",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(grid_locator(1, 1)),),
            )
        )
        record = accept(self.player, definition.key)
        self._companion("同伴", self._grid_room(1, 1))
        self._enter(self._grid_room(1, 1))
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["quest_id"], record.quest_id)

    def test_bound_instance_arrival_uses_accepted_record(self):
        definition = register(
            quest(
                "reach_bound_instance",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(bound_instance_locator()),),
            )
        )
        record = accept(self.player, definition.key)
        room = create_object(InstanceRoom, key="instance-arrival")
        bind_stage_runtime(self.player, record.quest_id, room=room)
        self._companion("同伴", room)
        self._enter(room)
        self.assertEqual(self._records()[0]["state"], "completed")

    def test_escort_requires_all_protected_entities_alive_and_present(self):
        definition = register(
            quest(
                "escort_presence",
                quest_type=QuestType.ESCORT,
                stages=(escort_stage(anchor_locator(), roles=("first", "second")),),
            )
        )
        first = self._protected("first")
        second = self._protected("second")
        record = self._accept_escort(
            definition, (first, second), package_id="escort_presence_package"
        )
        anchor = self._anchor()
        first.move_to(anchor, quiet=True)
        self.assertIs(first.location, anchor)
        self.assertEqual(self._records()[0]["state"], "in_progress")
        second.move_to(anchor, quiet=True)
        self.assertIs(second.location, anchor)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["quest_id"], record.quest_id)

    def test_escort_with_dead_protected_entity_does_not_complete(self):
        definition = register(
            quest(
                "escort_dead",
                quest_type=QuestType.ESCORT,
                stages=(escort_stage(anchor_locator()),),
            )
        )
        guard = self._protected("dead-guard")
        record = self._accept_escort(
            definition, (guard,), package_id="escort_dead_package"
        )
        anchor = self._anchor()
        guard.traits.hp._data["current"] = 0
        guard.move_to(anchor, quiet=True)
        self.assertIs(guard.location, anchor)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "in_progress")
        self.assertEqual(stored["quest_id"], record.quest_id)

    def test_instance_interaction_behavior_remains_intact(self):
        definition = register(
            quest(
                "reach_instance_behavior",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(bound_instance_locator()),),
            )
        )
        record = accept(self.player, definition.key)
        room = create_object(InstanceRoom, key="interaction-room")
        bind_stage_runtime(self.player, record.quest_id, room=room)
        self._companion("同伴", room)
        self._enter(room)
        self.assertTrue(room.db.interacted)
        self.assertEqual(self._records()[0]["state"], "completed")

    def test_multiple_matching_quests_each_transition_once_per_hook(self):
        first = register(
            quest(
                "reach_multi_one",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        second = register(
            quest(
                "reach_multi_two",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        accept(self.player, first.key)
        accept(self.player, second.key)
        self._companion("同伴", self._anchor())
        self._enter(self._anchor())
        states = {entry["definition_key"]: entry["state"] for entry in self._records()}
        self.assertEqual(states[first.key], "completed")
        self.assertEqual(states[second.key], "completed")

    def test_terminal_records_are_ignored_by_arrival(self):
        definition = register(
            quest(
                "reach_terminal",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        record = accept(self.player, definition.key)
        self._companion("同伴", self._anchor())
        self._enter(self._anchor())
        self.assertEqual(self._records()[0]["state"], "completed")
        self.player.move_to(self.room1, quiet=True)
        self._enter(self._anchor())
        self.assertEqual(self._records()[0]["state"], "completed")

    def test_one_arrival_event_advances_exactly_one_stage(self):
        definition = register(
            quest(
                "reach_two_stages",
                quest_type=QuestType.EXPLORE,
                stages=(
                    reach_stage(anchor_locator(), 0),
                    reach_stage(anchor_locator(), 1),
                ),
            )
        )
        accept(self.player, definition.key)
        self._companion("同伴", self._anchor())
        self._enter(self._anchor())
        stored = self._records()[0]
        self.assertEqual(stored["state"], "in_progress")
        self.assertEqual(stored["stage_index"], 1)
        self.assertEqual(stored["stage_progress"], 0)
        self.player.move_to(self.room1, quiet=True)
        self._enter(self._anchor())
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["stage_index"], 1)

    @covers_requirement("quest-progress-tracking::arrival-observation-advances-at-most-one-per-event-and-never-exceeds-quantity")
    def test_arrival_advances_at_most_one_per_event_and_never_over_fills(self):
        definition = quest(
            "reach_quantity_two_slipped",
            quest_type=QuestType.EXPLORE,
            stages=(QuestStage(0, reach(anchor_locator(), quantity=2)),),
        )
        QUEST_DEFINITION_REGISTRY[definition.key] = definition
        accept(self.player, definition.key)
        self._companion("同伴", self._anchor())
        self._enter(self._anchor())
        stored = self._records()[0]
        self.assertEqual(stored["state"], "in_progress")
        self.assertEqual(stored["stage_progress"], 1)
        self.player.move_to(self.room1, quiet=True)
        self._enter(self._anchor())
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["stage_progress"], 2)
        self.player.move_to(self.room1, quiet=True)
        self._enter(self._anchor())
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["stage_progress"], 2)


class PartyArrivalProgressTests(EscortOfferMixin, QuestRegistryIsolation, EvenniaTest):
    """Real exit traversal with companion follow (party-quest task 2.4).

    The player's own arrival observation runs before the follow moves, so a
    companion arriving *with* the player only becomes visible to the quest
    observer through the post-follow re-run; a companion already in the
    destination is visible to the first observation alone.
    """

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        self.room1.key = "Room1"
        self.room1.save()
        self.anchor = self._anchor()
        self.door = create_object(
            Exit, key="door", location=self.room1, destination=self.anchor
        )
        self.player = create_object(PlayerCharacter, key="party-arrival-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1

    def _anchor(self) -> AnchorRoom:
        room = AnchorRoom.objects.filter(db_key="中央廣場").first()
        self.assertIsInstance(room, AnchorRoom)
        return room

    def _companion(self, key: str) -> NPC:
        npc = create_object(NPC, key=key, location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        return npc

    def _enter(self, room):
        self.player.move_to(room, quiet=True)
        self.assertIs(self.player.location, room)

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::room-arrival-drives-reach-and-escort-through-supported-persistent-room-hooks")
    def test_arrival_with_followed_companion_advances_reach_once(self):
        definition = register(
            quest(
                "reach_follow_arrival",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        accept(self.player, definition.key)
        self._companion("跟隨者")
        self.door.at_traverse(self.player, self.anchor)
        self.assertIs(self.player.location, self.anchor)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["stage_progress"], 1)

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    def test_companion_already_in_destination_advances_without_rerun(self):
        definition = register(
            quest(
                "reach_waiting_arrival",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        accept(self.player, definition.key)
        companion = self._companion("等候者")
        companion.move_to(self.anchor, quiet=True)
        self.door.at_traverse(self.player, self.anchor)
        self.assertEqual(self._records()[0]["state"], "completed")

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::room-arrival-drives-reach-and-escort-through-supported-persistent-room-hooks")
    def test_repeated_observation_never_advances_a_stage_twice(self):
        definition = register(
            quest(
                "reach_idempotent",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        accept(self.player, definition.key)
        self._companion("往返者")
        self.door.at_traverse(self.player, self.anchor)
        first = self._records()[0]
        self.assertEqual(first["state"], "completed")
        back = create_object(Exit, key="back", location=self.anchor, destination=self.room1)
        back.at_traverse(self.player, self.room1)
        self.door.at_traverse(self.player, self.anchor)
        self.assertEqual(self._records()[0], first)
        self.assertEqual(self._records()[0]["state"], "completed")

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::room-arrival-drives-reach-and-escort-through-supported-persistent-room-hooks")
    def test_escort_missing_protected_entity_stays_unchanged(self):
        definition = register(
            quest(
                "escort_missing",
                quest_type=QuestType.ESCORT,
                stages=(escort_stage(anchor_locator()),),
            )
        )
        guard = self._protected("stay-guard")
        record = self._accept_escort(
            definition, (guard,), package_id="escort_missing_package"
        )
        # The accepted protected actor leaves the follower's own source room,
        # so the traversal cannot carry it along: the destination waits for it.
        guard.move_to(self.room2, quiet=True)
        self._companion("跟隨者")
        self.door.at_traverse(self.player, self.anchor)
        self.assertEqual(self._records()[0]["state"], "in_progress")
        guard.move_to(self.anchor, quiet=True)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["quest_id"], record.quest_id)

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    def test_escort_dead_protected_entity_stays_unchanged(self):
        definition = register(
            quest(
                "escort_dead_traversal",
                quest_type=QuestType.ESCORT,
                stages=(escort_stage(anchor_locator()),),
            )
        )
        guard = self._protected("dead-traversal-guard")
        self._accept_escort(
            definition, (guard,), package_id="escort_dead_traversal_package"
        )
        guard.traits.hp._data["current"] = 0
        guard.move_to(self.anchor, quiet=True)
        self._companion("跟隨者")
        self.door.at_traverse(self.player, self.anchor)
        self.assertEqual(self._records()[0]["state"], "in_progress")

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::arrival-observation-advances-at-most-one-per-event-and-never-exceeds-quantity")
    def test_follow_rerun_never_double_advances_the_same_arrival(self):
        definition = quest(
            "reach_quantity_two_follow",
            quest_type=QuestType.EXPLORE,
            stages=(QuestStage(0, reach(anchor_locator(), quantity=2)),),
        )
        QUEST_DEFINITION_REGISTRY[definition.key] = definition
        accept(self.player, definition.key)
        waiting = self._companion("等候者")
        waiting.move_to(self.anchor, quiet=True)
        self._companion("跟隨者")
        self.door.at_traverse(self.player, self.anchor)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "in_progress")
        self.assertEqual(stored["stage_progress"], 1)
        back = create_object(
            Exit, key="back", location=self.anchor, destination=self.room1
        )
        back.at_traverse(self.player, self.room1)
        self.door.at_traverse(self.player, self.anchor)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["stage_progress"], 2)


class WildernessObservationExclusionTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=_east_gate_xyz()).first()
        self.gate = [e for e in self.east_gate.exits if e.key == "荒野"][0]

    def _step(self, direction: str):
        exit_obj = [e for e in self.char1.location.exits if e.key == direction][0]
        exit_obj.at_traverse(self.char1, self.char1.location)

    @covers_requirement("quest-progress-tracking::wilderness-rooms-do-not-advertise-an-arrival-hook-that-normal-traversal-bypasses")
    def test_wilderness_entry_and_step_do_not_invoke_observation(self):
        with patch(
            "world.quests.room_observation.observe_room_entry",
        ) as observer:
            self.gate.at_traverse(self.char1, self.east_gate)
            self.assertIsInstance(self.char1.location, TerrainRoom)
            self._step("east")
        observer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
