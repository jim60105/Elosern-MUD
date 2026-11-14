"""The complete settlement state of one synthetic world, as comparable values.

Shared by the behavioural tests of the settlement chain. Every individual is
replaced by a stable label and no primary key appears anywhere, so the same
scenario settled twice yields equal projections even though the two runs
allocate different persistent identities.

Individuals written by a movement group are labelled ``"<group id>#<index in
member_ids>"``; every other referenced identity, including one recorded by a
site or a timeline transition that no longer belongs to a group, is labelled
``"free#<n>"`` in ascending persistent-ID order. The projection reads only the
owners' readers and is never imported by production code.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from typeclasses.monsters import Monster

from world.maps import monster_activity, monster_sites, regional_population
from world.rules.buffs import active_buff_keys_from_storage
from world.rules.clock import GAUGE_KEYS
from world.rules.fatigue import read_optional_fatigue_state
from world.rules.sleep_receipt import read_sleep_receipt
from world.rules.surfaces import persisted_hp


def settlement_projection(wilderness: Any) -> dict[str, Any]:
    """The activity, timeline, zone, site and body state of one world."""
    labels = _labels(wilderness)
    return {
        "activity": _activity(wilderness, labels),
        "timeline": _timeline(wilderness, labels),
        "zones": regional_population._state_map(wilderness),
        "sites": _sites(wilderness, labels),
        "bodies": _bodies(wilderness, labels),
    }


def catch_up_world(wilderness: Any) -> None:
    """Catch every unit up to the current tick (test helper).

    A clock advance settles only the observed units, so a test that advances
    and then asserts the state of a group no player observes calls this first:
    each unit of the authored geometry, and the residual unit, is caught up
    through the same entry point a command uses.
    """
    from world.maps import population_lifecycle, population_units

    index = population_units.current_unit_index()
    units = (
        {population_units.RESIDUAL_UNIT}
        | set(index.unit_of_zone.values())
        | set(index.unit_of_area.values())
    )
    for unit in sorted(units):
        population_lifecycle.ensure_population_current(wilderness, {unit})


def _labels(wilderness: Any) -> dict[int, str]:
    """One stable label per referenced persistent ID, without any raw ID."""
    state = monster_activity.read_monster_activity(wilderness)
    labels: dict[int, str] = {}
    for group_id in sorted(state.groups):
        for index, member_id in enumerate(state.groups[group_id].member_ids):
            labels[int(member_id)] = f"{group_id}#{index}"
    referenced: set[int] = set(labels)
    for journey in state.journeys.values():
        referenced.update(int(member_id) for member_id in journey.member_ids)
        referenced.update(
            int(member.individual_id) for member in journey.plan.members
        )
    for receipt in state.receipts.values():
        if receipt.individual_id is not None:
            referenced.add(int(receipt.individual_id))
    for transition in regional_population.read_population_timeline(
        wilderness
    ).transitions:
        referenced.add(int(transition.individual_id))
    for record in (monster_sites._read_state_map(wilderness) or {}).values():
        member_ids = _member_ids(record.get("member_ids"))
        if member_ids is not None:
            referenced.update(member_ids)
    for individual in _living_rows():
        referenced.add(int(individual.pk))
    free = 0
    for member_id in sorted(referenced):
        if member_id in labels:
            continue
        labels[member_id] = f"free#{free}"
        free += 1
    return labels


def _living_rows() -> tuple[Monster, ...]:
    """Every living individual row, in persistent-ID order."""
    return tuple(
        sorted(
            (
                individual
                for individual in Monster.objects.all_family()
                if persisted_hp(individual) > 0
            ),
            key=lambda individual: individual.pk,
        )
    )


def _activity(wilderness: Any, labels: dict[int, str]) -> dict[str, Any]:
    """The activity owner's persisted record with every member ID labelled."""
    record = monster_activity.state_to_dict(
        monster_activity.read_monster_activity(wilderness)
    )
    for group in record["groups"].values():
        group["member_ids"] = [
            labels[int(member_id)] for member_id in group["member_ids"]
        ]
        # ``member_time`` is keyed by the string form of each member ID.
        group["member_time"] = {
            labels[int(key)]: value for key, value in group["member_time"].items()
        }
    for journey in record["journeys"].values():
        journey["member_ids"] = [
            labels[int(member_id)] for member_id in journey["member_ids"]
        ]
        journey["plan"]["members"] = [
            {**member, "individual_id": labels[int(member["individual_id"])]}
            for member in journey["plan"]["members"]
        ]
    for receipt in record["receipts"].values():
        if receipt["individual_id"] is not None:
            receipt["individual_id"] = labels[int(receipt["individual_id"])]
    return record


def _timeline(wilderness: Any, labels: dict[int, str]) -> dict[str, Any]:
    """The timeline's progress, transitions and protection as plain values."""
    timeline = regional_population.read_population_timeline(wilderness)
    return {
        "settled_through_tick": int(timeline.settled_through_tick),
        "transitions": [
            {
                "source_id": transition.source_id,
                "individual": labels[int(transition.individual_id)],
                "occurred_tick": int(transition.occurred_tick),
                "before": _presence(transition.before),
                "after": _presence(transition.after),
            }
            for transition in timeline.transitions
        ],
        "protection": [
            {
                "engagement_id": protection.engagement_id,
                "cell": [
                    protection.cell.wilderness,
                    int(protection.cell.x),
                    int(protection.cell.y),
                ],
                "start_tick": int(protection.start_tick),
                "end_tick": (
                    None if protection.end_tick is None else int(protection.end_tick)
                ),
            }
            for protection in timeline.protection
        ],
    }


def _presence(fact: regional_population.PopulationPresence) -> dict[str, Any]:
    """One presence fact without any identity, only its measured values."""
    position = fact.position
    return {
        "alive": bool(fact.alive),
        "cell": (
            None
            if position is None
            else [position.wilderness, int(position.x), int(position.y)]
        ),
        "home_zone": fact.home_zone,
        "site_key": fact.site_key,
    }


def _sites(wilderness: Any, labels: dict[int, str]) -> dict[str, dict]:
    """Every site record with its member IDs labelled and its lists plain."""
    states = monster_sites._read_state_map(wilderness) or {}
    projection: dict[str, dict] = {}
    for key in sorted(states):
        record = dict(states[key])
        member_ids = _member_ids(record.get("member_ids"))
        if member_ids is not None:
            record["member_ids"] = [labels[member_id] for member_id in member_ids]
        projection[key] = record
    return projection


def _member_ids(value: Any) -> list[int] | None:
    """One stored member-ID sequence as plain integers (Evennia's saver type)."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    return [int(member_id) for member_id in value]


def _bodies(wilderness: Any, labels: dict[int, str]) -> dict[str, dict[str, Any]]:
    """Each living individual's position, gauges, physiology and buffs."""
    bodies: dict[str, dict[str, Any]] = {}
    for individual in _living_rows():
        gauges: dict[str, Any] = {}
        for key in GAUGE_KEYS:
            gauge = getattr(individual.traits, key, None)
            gauges[key] = (
                None
                if gauge is None
                else {
                    "current": gauge.current,
                    "regen_remainder": float(getattr(gauge, "regen_remainder", 0.0)),
                }
            )
        fatigue = read_optional_fatigue_state(individual)
        receipt = read_sleep_receipt(individual)
        bodies[labels[int(individual.pk)]] = {
            "cell": regional_population.actual_cell(wilderness, individual),
            "located": getattr(individual, "location", None) is not None,
            "gauges": gauges,
            "reserve_units": None if fatigue is None else int(fatigue.reserve_units),
            "posture": None if fatigue is None else fatigue.posture,
            "receipt": None if receipt is None else receipt.state,
            "buffs": sorted(active_buff_keys_from_storage(individual)),
        }
    return bodies
