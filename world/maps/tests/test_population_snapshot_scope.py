"""Behaviour tests: a scoped settlement snapshots only its own activity parts.

Every scenario is built from the synthetic two-zone world of
:class:`ScopedSettlementFixture`; no shipped zone, site, composition or
individual is named, and no test asserts elapsed time. The proof is the named
set of activity parts each registry holds: a scope of the first zone names its
own part and leaves the second zone's out, a group stored outside its present
units is still named through the part it was first stored in, an orphan
receipt is named only under a residual scope, and a scoped pass writes only
the parts it named.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from django.db import transaction

from world.maps import monster_activity, population_units, regional_population
from world.maps.monster_activity import (
    MONSTER_ACTIVITY_ATTRIBUTE,
    MONSTER_ACTIVITY_PART_CATEGORY,
    ActivityReceipt,
    MonsterActivityState,
    part_key,
)
from world.maps.population_lifecycle import (
    settle_population_scope,
    snapshot_population_lifecycle_surfaces,
)
from world.maps.tests.test_monster_activity import GROUP_ACTIVITY
from world.maps.tests.test_population_catch_up import _drop_attribute_caches
from world.maps.tests.test_scoped_population_settlement import (
    ACTIVITY_B_WANDER,
    END,
    START,
    WANDER_A,
    WANDER_B,
    ZONE_B,
    ScopedSettlementFixture,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import restore_advance_registry
from world.rules.movement_edges import LocationRef

ORPHAN_RECEIPT = "t_scope_orphan_operation"


class SnapshotScopeFixture(ScopedSettlementFixture):
    """The two-zone world plus the surface-reading helpers every test uses."""

    def _scope(self, *units: str):
        return population_units.build_scope(self.wilderness, set(units))

    def _wilderness_attributes(self, registry):
        return registry[id(self.wilderness)].attributes

    @staticmethod
    def _activity_keys(attributes) -> set[str]:
        return {
            key
            for (key, category) in attributes
            if category == MONSTER_ACTIVITY_PART_CATEGORY
        }


class ScopedActivitySurfaceTests(SnapshotScopeFixture):
    """The activity owner's scoped snapshot names exactly the writable parts."""

    def test_another_units_part_is_left_out(self):
        self._build_scenario()
        scope = self._scope(self.unit_a)

        registry = monster_activity.snapshot_monster_activity_surfaces(
            START, END, scope=scope
        )
        keys = self._activity_keys(self._wilderness_attributes(registry))

        expected = {
            part_key(unit)
            for unit in monster_activity.scope_part_units(self.wilderness, scope)
        }
        self.assertEqual(keys, expected)
        self.assertIn(part_key(self.unit_a), keys)
        self.assertNotIn(part_key(self.unit_b), keys)

    def test_a_group_stored_outside_its_present_units_is_named(self):
        self._reset_activity(tick=START)
        group_id, _bodies = self._group(
            cell=WANDER_B,
            activity=ACTIVITY_B_WANDER,
            owner_kind="quest",
            owner_key="t_scope_quest",
            tick=START,
        )
        state = monster_activity.read_monster_activity(self.wilderness)
        home = LocationRef.wilderness(WILDERNESS_NAME, *WANDER_A)
        rewritten = replace(
            state.groups[group_id],
            activity_key=GROUP_ACTIVITY,
            home=home,
            position=home,
        )
        monster_activity.write_monster_activity(
            self.wilderness,
            MonsterActivityState(
                MappingProxyType({**state.groups, group_id: rewritten}),
                state.journeys,
                state.receipts,
                state.room_protection,
                state.settled_through_tick,
            ),
        )
        seeds = population_units.group_units(
            population_units.current_unit_index(), rewritten, None
        )
        scope = population_units.build_scope(self.wilderness, seeds)

        self.assertIn(group_id, scope.group_ids)
        self.assertNotIn(self.unit_b, scope.units)
        registry = monster_activity.snapshot_monster_activity_surfaces(
            START, END, scope=scope
        )
        self.assertIn(
            part_key(self.unit_b),
            self._activity_keys(self._wilderness_attributes(registry)),
        )

    def test_an_orphan_receipt_is_named_only_under_a_residual_scope(self):
        self._reset_activity(tick=START)
        group_id, _bodies = self._group(cell=WANDER_A, tick=START)
        state = monster_activity.read_monster_activity(self.wilderness)
        receipt = ActivityReceipt(
            ORPHAN_RECEIPT,
            monster_activity.RECEIPT_DEPARTURE,
            group_id,
            None,
            None,
            START,
        )
        monster_activity.write_monster_activity(
            self.wilderness,
            MonsterActivityState(
                state.groups,
                state.journeys,
                MappingProxyType({**state.receipts, receipt.operation_id: receipt}),
                state.room_protection,
                state.settled_through_tick,
            ),
        )
        orphaned = monster_activity.read_monster_activity(self.wilderness)
        monster_activity.write_monster_activity(
            self.wilderness,
            MonsterActivityState(
                MappingProxyType({}),
                orphaned.journeys,
                orphaned.receipts,
                orphaned.room_protection,
                orphaned.settled_through_tick,
            ),
        )

        residual = monster_activity.snapshot_monster_activity_surfaces(
            START, END, scope=self._scope(population_units.RESIDUAL_UNIT)
        )
        self.assertIn(
            part_key(self.unit_a),
            self._activity_keys(self._wilderness_attributes(residual)),
        )
        other = monster_activity.snapshot_monster_activity_surfaces(
            START, END, scope=self._scope(self.unit_b)
        )
        self.assertNotIn(
            part_key(self.unit_a),
            self._activity_keys(self._wilderness_attributes(other)),
        )

    def test_a_scoped_pass_writes_only_named_parts(self):
        self._build_scenario()
        scope = self._scope(self.unit_a)
        named = monster_activity.scope_part_units(self.wilderness, scope)

        with patch.object(
            monster_activity, "_store_part", wraps=monster_activity._store_part
        ) as stored:
            settle_population_scope(self.wilderness, {self.unit_a}, END)

        self.assertTrue(stored.call_count)
        written = {call.args[1] for call in stored.call_args_list}
        self.assertTrue(written <= named)


class LifecycleRegistryTests(SnapshotScopeFixture):
    """The merged lifecycle registry carries the scoped parts exactly once."""

    def test_growing_the_far_zone_names_the_same_activity_entries(self):
        self._build_scenario()
        scope = self._scope(self.unit_a)
        first = snapshot_population_lifecycle_surfaces(START, END, scope=scope)
        first_keys = self._activity_keys(self._wilderness_attributes(first))

        for _ in range(5):
            self._group(
                cell=WANDER_B,
                activity=ACTIVITY_B_WANDER,
                owner_key=ZONE_B,
                tick=START,
            )
        with patch.object(
            monster_activity,
            "_db_safe_attribute_snapshot",
            wraps=monster_activity._db_safe_attribute_snapshot,
        ) as snapshot:
            second = snapshot_population_lifecycle_surfaces(START, END, scope=scope)
        second_keys = self._activity_keys(self._wilderness_attributes(second))

        expected = {
            part_key(unit)
            for unit in monster_activity.scope_part_units(self.wilderness, scope)
        }
        self.assertEqual(first_keys, second_keys)
        self.assertEqual(second_keys, expected)
        self.assertNotIn(part_key(self.unit_b), second_keys)
        copies = [
            call
            for call in snapshot.call_args_list
            if call.args[1] == part_key(self.unit_a)
        ]
        self.assertEqual(len(copies), 1)

    def test_a_failed_scoped_pass_removes_the_part_it_created(self):
        self._reset_activity(tick=START)
        scope = self._scope(self.unit_b)
        before = monster_activity.state_to_dict(
            monster_activity.read_stored_monster_activity(self.wilderness)
        )
        registry = snapshot_population_lifecycle_surfaces(START, END, scope=scope)
        self.assertEqual(
            self._wilderness_attributes(registry)[
                (part_key(self.unit_b), MONSTER_ACTIVITY_PART_CATEGORY)
            ],
            (False, None),
        )

        try:
            with transaction.atomic():
                self._group(
                    cell=WANDER_B,
                    activity=ACTIVITY_B_WANDER,
                    owner_key=ZONE_B,
                    tick=START,
                )
                raise RuntimeError("the scoped pass failed")
        except RuntimeError:
            pass
        restore_advance_registry(registry, (self.wilderness,))

        self.assertIsNone(
            self.wilderness.attributes.get(
                part_key(self.unit_b), category=MONSTER_ACTIVITY_PART_CATEGORY
            )
        )
        self.assertEqual(
            monster_activity.state_to_dict(
                monster_activity.read_stored_monster_activity(self.wilderness)
            ),
            before,
        )
        _drop_attribute_caches(self.wilderness)
        self.assertEqual(
            monster_activity.state_to_dict(
                monster_activity.read_stored_monster_activity(self.wilderness)
            ),
            before,
        )

    def test_an_unscoped_population_snapshot_keeps_every_part(self):
        self._build_scenario()

        attributes = self._wilderness_attributes(
            regional_population.snapshot_population_surfaces(self.wilderness)
        )

        self.assertIn((MONSTER_ACTIVITY_ATTRIBUTE, None), attributes)
        self.assertIn(
            (part_key(self.unit_a), MONSTER_ACTIVITY_PART_CATEGORY), attributes
        )
        self.assertIn(
            (part_key(self.unit_b), MONSTER_ACTIVITY_PART_CATEGORY), attributes
        )
