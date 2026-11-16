"""Behaviour tests: the activity record is stored in one part per settlement unit.

Every scenario is built from the synthetic two-zone world of
:class:`ScopedSettlementFixture`; no shipped zone, site, composition or
individual is named, and no test asserts elapsed time. Work is established by
call counts and object identity.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from types import MappingProxyType
from unittest.mock import patch

from django.db import transaction

from world.maps import monster_activity
from world.maps.monster_activity import (
    MONSTER_ACTIVITY_PART_CATEGORY,
    MODE_JOURNEY,
    RECEIPT_DEPARTURE,
    ActivityReceipt,
    JourneyPlan,
    MonsterActivityState,
    MonsterActivityStateInvalid,
    MonsterJourney,
    part_key,
)
from world.maps.tests.test_scoped_population_settlement import (
    START,
    WANDER_A,
    WANDER_B,
    ScopedSettlementFixture,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.movement_edges import LocationRef, PhysicalEdge

TRAVELLING_JOURNEY = "t_part_journey"
TRAVELLING_RECEIPT = "t_part_operation"


class StoredPartsTests(ScopedSettlementFixture):
    """One header and one part per settlement unit: placement, write, refusal."""

    # -- seams --------------------------------------------------------------

    def _part(self, unit: str) -> dict:
        return self.wilderness.attributes.get(
            part_key(unit), category=MONSTER_ACTIVITY_PART_CATEGORY
        )

    def _part_object(self, unit: str):
        return self.wilderness.attributes.get(
            part_key(unit),
            category=MONSTER_ACTIVITY_PART_CATEGORY,
            return_obj=True,
        )

    def _header(self):
        return self.wilderness.attributes.get(
            monster_activity.MONSTER_ACTIVITY_ATTRIBUTE, return_obj=True
        )

    def _header_value(self) -> dict:
        return dict(self._header().db_value)

    def _state(self) -> MonsterActivityState:
        return monster_activity.read_monster_activity(self.wilderness)

    def _write_groups(self, groups: dict, **fields) -> None:
        state = self._state()
        monster_activity.write_monster_activity(
            self.wilderness,
            MonsterActivityState(
                MappingProxyType(groups),
                state.journeys,
                state.receipts,
                fields.get("room_protection", state.room_protection),
                fields.get("settled_through_tick", state.settled_through_tick),
            ),
        )

    def _travelling_state(self, group_id: str, bodies) -> MonsterActivityState:
        """The stored state with one group rewritten as travelling, plus a receipt."""
        state = self._state()
        group = state.groups[group_id]
        source = group.home
        destination = LocationRef.wilderness(WILDERNESS_NAME, WANDER_A[0] + 1, WANDER_A[1])
        edge = PhysicalEdge(source, destination, "direction:e")
        journey = MonsterJourney(
            journey_id=TRAVELLING_JOURNEY,
            group_id=group_id,
            member_ids=group.member_ids,
            source=source,
            destination=destination,
            depart_tick=START,
            arrival_tick=START + 60,
            settled_through_tick=START,
            retry_tick=None,
            edge=edge,
            plan=JourneyPlan(60, Fraction(0), (), (), ()),
        )
        travelling = replace(
            group,
            journey_id=journey.journey_id,
            position=None,
            member_time={
                key: replace(member_time, mode=MODE_JOURNEY, session_id=None)
                for key, member_time in group.member_time.items()
            },
        )
        receipt = ActivityReceipt(
            TRAVELLING_RECEIPT,
            RECEIPT_DEPARTURE,
            group_id,
            journey.journey_id,
            None,
            START,
        )
        return MonsterActivityState(
            MappingProxyType({**state.groups, group_id: travelling}),
            MappingProxyType({**state.journeys, journey.journey_id: journey}),
            MappingProxyType({**state.receipts, receipt.operation_id: receipt}),
            state.room_protection,
            state.settled_through_tick,
        )

    # -- one part per settlement unit --------------------------------------

    def test_a_written_record_round_trips_through_the_stored_parts(self):
        self._reset_activity(tick=START)
        group_a, bodies_a = self._group(cell=WANDER_A)
        group_b, _bodies_b = self._group(cell=WANDER_B)
        state = self._travelling_state(group_a, bodies_a)
        written = monster_activity.state_to_dict(state)

        monster_activity.write_monster_activity(self.wilderness, state)
        self.wilderness.attributes.reset_cache()

        self.assertEqual(
            monster_activity.state_to_dict(
                monster_activity.read_monster_activity(self.wilderness)
            ),
            written,
        )
        self.assertEqual(set(self._header_value()["units"]), {self.unit_a, self.unit_b})
        self.assertEqual(set(self._part(self.unit_a)["groups"]), {group_a})
        self.assertEqual(set(self._part(self.unit_b)["groups"]), {group_b})

    def test_a_group_is_stored_in_the_part_of_its_home_unit(self):
        self._reset_activity(tick=START)
        group_a, _bodies_a = self._group(cell=WANDER_A)
        group_b, _bodies_b = self._group(cell=WANDER_B)

        part_a = self._part(self.unit_a)
        part_b = self._part(self.unit_b)
        self.assertEqual(set(part_a["groups"]), {group_a})
        self.assertNotIn(group_b, part_a["groups"])
        self.assertEqual(set(part_b["groups"]), {group_b})
        self.assertNotIn(group_a, part_b["groups"])

    def test_a_group_keeps_its_part_when_its_home_is_rewritten(self):
        self._reset_activity(tick=START)
        group_a, _bodies_a = self._group(cell=WANDER_A)
        self._group(cell=WANDER_B)
        state = self._state()
        rewritten = replace(
            state.groups[group_a],
            home=LocationRef.wilderness(WILDERNESS_NAME, *WANDER_B),
        )

        self._write_groups({**state.groups, group_a: rewritten})

        self.assertIn(group_a, self._part(self.unit_a)["groups"])
        self.assertNotIn(group_a, self._part(self.unit_b)["groups"])
        self.assertEqual(self._state().groups[group_a].home, rewritten.home)

    # -- only the changed parts are written --------------------------------

    def test_another_units_part_is_not_rewritten(self):
        self._reset_activity(tick=START)
        group_a, _bodies_a = self._group(cell=WANDER_A)
        self._group(cell=WANDER_B)
        untouched = self._part_object(self.unit_b)
        before = untouched.db_value
        state = self._state()

        self._write_groups(
            {
                **state.groups,
                group_a: replace(state.groups[group_a], sequence=7),
            }
        )

        self.assertIs(self._part_object(self.unit_b).db_value, before)

    def test_a_batched_pass_stores_the_changed_part_once(self):
        self._reset_activity(tick=START)
        group_a, _bodies_a = self._group(cell=WANDER_A)
        self._group(cell=WANDER_B)

        with patch.object(
            monster_activity, "_store_part", wraps=monster_activity._store_part
        ) as counted:
            with monster_activity.batched_state_writes(self.wilderness):
                for sequence in (1, 2, 3):
                    state = self._state()
                    self._write_groups(
                        {
                            **state.groups,
                            group_a: replace(
                                state.groups[group_a], sequence=sequence
                            ),
                        }
                    )

        self.assertEqual([call.args[1] for call in counted.call_args_list], [self.unit_a])
        self.assertEqual(self._state().groups[group_a].sequence, 3)

    def test_writing_the_state_read_back_unchanged_stores_nothing(self):
        self._reset_activity(tick=START)
        self._group(cell=WANDER_A)
        self._group(cell=WANDER_B)
        state = self._state()
        header = self._header()
        before = header.db_value

        with patch.object(
            monster_activity, "_store_part", wraps=monster_activity._store_part
        ) as counted:
            monster_activity.write_monster_activity(self.wilderness, state)

        self.assertFalse(counted.called)
        self.assertIs(self._header().db_value, before)

    def test_an_equal_state_rebuilt_from_the_projection_stores_nothing(self):
        self._reset_activity(tick=START)
        self._group(cell=WANDER_A)
        state = self._state()
        rebuilt = monster_activity.state_from_dict(
            monster_activity.state_to_dict(state)
        )
        header = self._header()
        before = header.db_value

        with patch.object(
            monster_activity, "_store_part", wraps=monster_activity._store_part
        ) as counted:
            monster_activity.write_monster_activity(self.wilderness, rebuilt)

        self.assertFalse(counted.called)
        self.assertIs(self._header().db_value, before)

    def test_a_header_only_change_stores_no_part(self):
        self._reset_activity(tick=START)
        self._group(cell=WANDER_A)
        state = self._state()

        with patch.object(
            monster_activity, "_store_part", wraps=monster_activity._store_part
        ) as counted:
            self._write_groups(
                dict(state.groups), settled_through_tick=state.settled_through_tick + 5
            )

        self.assertFalse(counted.called)
        self.assertEqual(
            self._header_value()["settled_through_tick"],
            state.settled_through_tick + 5,
        )

    # -- an incomplete record refuses --------------------------------------

    def test_a_malformed_header_refuses_and_rewrites_nothing(self):
        self._reset_activity(tick=START)
        self._group(cell=WANDER_A)
        header = self._header_value()

        for malformed in (
            {**header, "unknown": 1},
            {**header, "settled_through_tick": True},
        ):
            with self.subTest(malformed=malformed):
                self.wilderness.db.monster_activity = malformed
                before = self._header().db_value
                with patch.object(
                    monster_activity,
                    "_store_part",
                    wraps=monster_activity._store_part,
                ) as counted:
                    self.assertRaises(
                        MonsterActivityStateInvalid,
                        monster_activity.read_monster_activity,
                        self.wilderness,
                    )
                self.assertFalse(counted.called)
                self.assertIs(self._header().db_value, before)

    def test_a_missing_part_refuses_and_rewrites_nothing(self):
        self._reset_activity(tick=START)
        self._group(cell=WANDER_A)
        header = self._header_value()
        self.wilderness.db.monster_activity = {
            **header,
            "units": list(header["units"]) + ["t_no_such_unit"],
        }
        before = self._header().db_value

        with patch.object(
            monster_activity, "_store_part", wraps=monster_activity._store_part
        ) as counted:
            self.assertRaises(
                MonsterActivityStateInvalid,
                monster_activity.read_monster_activity,
                self.wilderness,
            )

        self.assertFalse(counted.called)
        self.assertIs(self._header().db_value, before)

    def test_two_parts_holding_one_group_refuse_and_rewrite_nothing(self):
        self._reset_activity(tick=START)
        group_a, _bodies_a = self._group(cell=WANDER_A)
        other = "t_part_duplicate_unit"
        self.wilderness.attributes.add(
            part_key(other),
            {**self._part(self.unit_a), "unit": other},
            category=MONSTER_ACTIVITY_PART_CATEGORY,
        )
        header = self._header_value()
        self.wilderness.db.monster_activity = {
            **header,
            "units": sorted(set(header["units"]) | {other}),
        }
        before = self._header().db_value

        with patch.object(
            monster_activity, "_store_part", wraps=monster_activity._store_part
        ) as counted:
            self.assertRaises(
                MonsterActivityStateInvalid,
                monster_activity.read_monster_activity,
                self.wilderness,
            )

        self.assertFalse(counted.called)
        self.assertIs(self._header().db_value, before)
        self.assertIn(group_a, self._part(self.unit_a)["groups"])


class RolledBackActivityWriteTests(ScopedSettlementFixture):
    """A failed write restores every part named in the snapshot."""

    def _record(self) -> dict:
        return monster_activity.state_to_dict(
            monster_activity.read_stored_monster_activity(self.wilderness)
        )

    def _header_units(self) -> list[str]:
        stored = self.wilderness.attributes.get(
            monster_activity.MONSTER_ACTIVITY_ATTRIBUTE, return_obj=True
        )
        return list(stored.db_value["units"])

    def test_a_rolled_back_group_change_restores_the_record(self):
        self._reset_activity(tick=START)
        group_a, _bodies_a = self._group(cell=WANDER_A)
        self._group(cell=WANDER_B)
        before = self._record()
        surfaces = monster_activity.snapshot_activity_surfaces(
            self.wilderness, member_ids=()
        )

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                state = monster_activity.read_monster_activity(self.wilderness)
                monster_activity.write_monster_activity(
                    self.wilderness,
                    MonsterActivityState(
                        MappingProxyType(
                            {
                                **state.groups,
                                group_a: replace(
                                    state.groups[group_a], sequence=99
                                ),
                            }
                        ),
                        state.journeys,
                        state.receipts,
                        state.room_protection,
                        state.settled_through_tick,
                    ),
                )
                raise RuntimeError("rollback")

        monster_activity.restore_activity_surfaces(
            surfaces, wilderness=self.wilderness
        )
        self.assertEqual(self._record(), before)
        self.wilderness.attributes.reset_cache()
        self.assertEqual(self._record(), before)

    def test_a_rolled_back_created_part_is_removed(self):
        self._reset_activity(tick=START)
        self._group(cell=WANDER_A)
        self.assertFalse(
            self.wilderness.attributes.has(
                part_key(self.unit_b), category=MONSTER_ACTIVITY_PART_CATEGORY
            )
        )
        before = self._record()
        surfaces = monster_activity.snapshot_activity_surfaces(
            self.wilderness, member_ids=()
        )

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self._group(cell=WANDER_B)
                raise RuntimeError("rollback")

        monster_activity.restore_activity_surfaces(
            surfaces, wilderness=self.wilderness
        )
        self.assertEqual(self._record(), before)
        self.wilderness.attributes.reset_cache()
        self.assertEqual(self._record(), before)
        self.assertFalse(
            self.wilderness.attributes.has(
                part_key(self.unit_b), category=MONSTER_ACTIVITY_PART_CATEGORY
            )
        )
        self.assertNotIn(self.unit_b, self._header_units())

        group_b, _bodies_b = self._group(cell=WANDER_B)
        self.assertIn(group_b, self._state_groups())

    def _state_groups(self):
        return monster_activity.read_monster_activity(self.wilderness).groups
