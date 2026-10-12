"""Pure exact-identity escort completion predicates (escort-rendezvous 3.3).

Every case exercises the predicate layer alone: no movement hook, no schedule,
no settlement. The scorers are the record's retained exact protected bindings
and the caller's resolution of the definition's meeting roles, so an impostor,
a dead actor, a missing role, a wrong relation, a different ordinary location,
a bound instance, and a recycled wilderness room object are each decided by
identity rather than by proximity.
"""

import unittest
from dataclasses import replace
from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, InstanceRoom, Room, TerrainRoom

from world.quests.definitions import EscortCompletion, QuestStage, QuestType
from world.quests.escort import (
    EscortPredicateError,
    PositionKey,
    authoritative_position,
    destination_satisfied,
    escort_objective,
    is_living,
    locator_matches,
    rendezvous_satisfied,
    resolve_protected_actors,
)
from world.quests.runtime import QuestState

from ._fixtures import (
    QuestRegistryIsolation,
    stage_active_record,
    anchor_locator,
    bound_instance_locator,
    escort,
    quest,
    register,
)


class EscortPredicateTests(QuestRegistryIsolation, EvenniaTest):
    """The two closed escort predicates over exact published identities."""

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="旅人")
        self.room = create_object(AnchorRoom, key="南門")
        self.room.db.anchor_key = anchor_locator().anchor_key
        self.other = create_object(AnchorRoom, key="北門")
        self.other.db.anchor_key = "a-different-anchor-key"
        self.player.move_to(self.room, quiet=True)
        self.destination_def = register(
            quest(
                "predicate_destination",
                quest_type=QuestType.ESCORT,
                stages=(QuestStage(0, escort(anchor_locator())),),
            )
        )
        self.rendezvous_def = register(
            quest(
                "predicate_rendezvous",
                quest_type=QuestType.ESCORT,
                stages=(
                    QuestStage(
                        0,
                        escort(
                            None,
                            completion=EscortCompletion.RENDEZVOUS,
                            protected_role_refs=("daughter",),
                            meeting_role_refs=("mother",),
                            relation=("parent_child", "mother", "daughter"),
                        ),
                    ),
                ),
            )
        )

    def _npc(self, key: str, room=None) -> NPC:
        npc = create_object(NPC, key=key)
        # The stored trait handler is what makes the actor a living entity, so
        # every synthetic participant gets a race baseline like the shipped
        # companions do.
        npc.race = "human"
        npc.apply_race_baseline()
        if room is not None:
            npc.move_to(room, quiet=True)
        return npc

    def _bind(self, definition, pairs):
        record = stage_active_record(self.player, definition.key)
        return replace(record, protected_roles=tuple(pairs))

    def _destination_record(self, npc):
        return self._bind(self.destination_def, (("escortee", npc.pk),))

    def _rendezvous_record(self, daughter):
        return self._bind(self.rendezvous_def, (("daughter", daughter.pk),))

    def test_position_identity_is_authoritative_and_distinct(self):
        daughter = self._npc("daughter", self.room)
        neighbour = self._npc("neighbour", self.room)
        self.assertEqual(
            authoritative_position(daughter),
            authoritative_position(neighbour),
        )
        # Two rooms are two positions; a homeless actor has none.
        self.assertNotEqual(
            authoritative_position(daughter),
            authoritative_position(self._npc("elsewhere", self.other)),
        )
        self.assertIsNone(authoritative_position(create_object(NPC, key="homeless")))

    def test_destination_waits_for_the_last_protected_actor(self):
        guarded = self._npc("escortee", self.other)
        record = self._destination_record(guarded)
        self.assertFalse(destination_satisfied(record, self.destination_def, self.room))
        guarded.move_to(self.room, quiet=True)
        self.assertTrue(destination_satisfied(record, self.destination_def, self.room))

    def test_destination_rejects_impostors_dead_and_missing_actors(self):
        real = self._npc("escortee", self.other)
        record = self._destination_record(real)
        # A same-name impostor at the destination never substitutes.
        self._npc("escortee", self.room)
        self.assertFalse(destination_satisfied(record, self.destination_def, self.room))
        # The exact actor dead at the destination is not alive.
        real.move_to(self.room, quiet=True)
        real.traits.hp._data["current"] = 0
        self.assertFalse(destination_satisfied(record, self.destination_def, self.room))
        # A deleted exact actor is missing rather than replaced.
        real.traits.hp._data["current"] = 1
        real.delete()
        self.assertEqual(resolve_protected_actors(record), ())
        self.assertFalse(destination_satisfied(record, self.destination_def, self.room))
        # A record with no retained protected binding is never satisfied.
        empty = replace(record, protected_roles=())
        self.assertFalse(destination_satisfied(empty, self.destination_def, self.room))

    def test_destination_locator_separates_permanent_rooms_from_bound_instances(self):
        guarded = self._npc("escortee", self.room)
        permanent = self._destination_record(guarded)
        self.assertTrue(locator_matches(self.room, anchor_locator(), None))
        instance_def = register(
            quest(
                "predicate_instance",
                quest_type=QuestType.ESCORT,
                stages=(QuestStage(0, escort(bound_instance_locator())),),
            )
        )
        instance = create_object(InstanceRoom, key="綁定場景")
        guarded.move_to(instance, quiet=True)
        bound = replace(
            stage_active_record(self.player, instance_def.key),
            protected_roles=(("escortee", guarded.pk),),
            stage_room_id=instance.pk,
        )
        self.assertTrue(destination_satisfied(bound, instance_def, instance))
        # A bound-instance record never matches a permanent room, and the
        # permanent record never matches an unpinned room.
        self.assertFalse(destination_satisfied(bound, instance_def, self.room))
        self.assertFalse(
            locator_matches(self.room, bound_instance_locator(), None)
        )
        # The stage pin, not the locator, is what identifies the instance.
        self.assertFalse(
            destination_satisfied(permanent, self.destination_def, self.other)
        )

    def test_rendezvous_holds_at_two_different_ordinary_locations(self):
        daughter = self._npc("daughter")
        mother = self._npc("mother")
        record = self._rendezvous_record(daughter)
        for room in (self.room, self.other):
            with self.subTest(room=room.key):
                daughter.move_to(room, quiet=True)
                mother.move_to(room, quiet=True)
                self.assertTrue(
                    rendezvous_satisfied(record, self.rendezvous_def, (mother,))
                )
                # Separation at two positions is not a reunion.
                mother.move_to(
                    self.other if room is self.room else self.room, quiet=True
                )
                self.assertFalse(
                    rendezvous_satisfied(record, self.rendezvous_def, (mother,))
                )

    def test_rendezvous_ignores_the_original_player_body(self):
        daughter = self._npc("daughter", self.other)
        mother = self._npc("mother", self.other)
        record = self._rendezvous_record(daughter)
        # The player's own body stays in the anchor room: escort is satisfied
        # by the physical actors alone.
        self.assertNotEqual(self.player.location, self.other)
        self.assertTrue(rendezvous_satisfied(record, self.rendezvous_def, (mother,)))

    def test_rendezvous_rejects_dead_missing_and_replaced_roles(self):
        daughter = self._npc("daughter", self.room)
        mother = self._npc("mother", self.room)
        record = self._rendezvous_record(daughter)
        self.assertFalse(rendezvous_satisfied(record, self.rendezvous_def, ()))
        self.assertFalse(
            rendezvous_satisfied(record, self.rendezvous_def, (mother, mother))
        )
        mother.traits.hp._data["current"] = 0
        self.assertFalse(rendezvous_satisfied(record, self.rendezvous_def, (mother,)))
        mother.traits.hp._data["current"] = 1
        # A deleted participant is missing, never substituted.
        mother.delete()
        self.assertFalse(rendezvous_satisfied(record, self.rendezvous_def, (mother,)))
        # The protected actor's own absence fails the predicate too.
        daughter.delete()
        self.assertFalse(
            rendezvous_satisfied(record, self.rendezvous_def, (self._npc("mother2"),))
        )

    def test_rendezvous_relation_needs_two_distinct_exact_endpoint_actors(self):
        daughter = self._npc("daughter", self.room)
        mother = self._npc("mother", self.room)
        record = self._rendezvous_record(daughter)
        # One actor cannot stand in for both endpoints of the relation.
        self.assertFalse(
            rendezvous_satisfied(record, self.rendezvous_def, (daughter,))
        )
        # A relation whose endpoints are not the declared roles is refused.
        broken = replace(
            self.rendezvous_def,
            stages=(
                QuestStage(
                    0,
                    escort(
                        None,
                        completion=EscortCompletion.RENDEZVOUS,
                        protected_role_refs=("daughter",),
                        meeting_role_refs=("mother",),
                        relation=("parent_child", "mother", "stranger"),
                    ),
                ),
            ),
        )
        self.assertFalse(rendezvous_satisfied(record, broken, (mother,)))

    def test_rendezvous_is_separated_by_wilderness_coordinates_and_provider(self):
        daughter = self._npc("daughter")
        mother = self._npc("mother")
        record = self._rendezvous_record(daughter)
        # Two plain rooms carrying the wilderness identity the terrain layer
        # supplies (provider name plus live coordinates), so no contrib hook
        # machinery is involved in the predicate's own decision.
        first = create_object(Room, key="荒野甲")
        first.wilderness = SimpleNamespace(
            name="elosern", itemcoordinates={daughter: (5, 5), mother: (5, 5)}
        )
        first.coordinates = (5, 5)
        second = create_object(Room, key="荒野乙")
        second.wilderness = SimpleNamespace(
            name="elsewhere", itemcoordinates={mother: (5, 5)}
        )
        second.coordinates = (5, 5)
        daughter.move_to(first, quiet=True)
        mother.move_to(first, quiet=True)
        self.assertTrue(rendezvous_satisfied(record, self.rendezvous_def, (mother,)))
        # The SAME recycled room object with different REGISTERED coordinates
        # is two positions: the shared room object proves nothing.
        first.wilderness.itemcoordinates[mother] = (6, 6)
        self.assertFalse(rendezvous_satisfied(record, self.rendezvous_def, (mother,)))
        # Another provider at the same coordinate is another position too.
        mother.move_to(second, quiet=True)
        self.assertIs(mother.location, second)
        self.assertFalse(rendezvous_satisfied(record, self.rendezvous_def, (mother,)))
        # The same provider and coordinate is one position again.
        first.wilderness.itemcoordinates[mother] = (5, 5)
        mother.move_to(first, quiet=True)
        self.assertTrue(rendezvous_satisfied(record, self.rendezvous_def, (mother,)))

    def test_a_real_terrain_room_reports_its_wilderness_identity(self):
        daughter = self._npc("daughter")
        terrain = create_object(TerrainRoom, key="荒野實體")
        terrain.ndb.wildernessscript = SimpleNamespace(name="elosern")
        terrain.ndb.active_coordinates = (7, 7)
        daughter.move_to(terrain, quiet=True)
        self.assertEqual(
            authoritative_position(daughter),
            PositionKey(kind="wilderness", wilderness="elosern", x=7, y=7),
        )
        # An unavailable coordinate means no provable position at all.
        terrain.ndb.active_coordinates = None
        self.assertIsNone(authoritative_position(daughter))

    def test_predicates_refuse_a_stage_of_the_wrong_completion_mode(self):
        guarded = self._npc("escortee", self.room)
        destination = self._destination_record(guarded)
        with self.assertRaises(EscortPredicateError):
            rendezvous_satisfied(destination, self.destination_def, ())
        with self.assertRaises(EscortPredicateError):
            destination_satisfied(
                self._rendezvous_record(guarded), self.rendezvous_def, self.room
            )
        with self.assertRaises(EscortPredicateError):
            escort_objective(self.destination_def, 5)

    def test_predicates_never_mutate_state(self):
        guarded = self._npc("escortee", self.room)
        record = self._destination_record(guarded)
        before = record
        self.assertTrue(destination_satisfied(record, self.destination_def, self.room))
        self.assertEqual(record, before)
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        self.assertTrue(is_living(guarded))


if __name__ == "__main__":
    unittest.main()