"""Reference-preserving replacement of one settlement's generated street graph.

The generator produces a fresh plan and contains no identity that a consumer
joins on: every slot is new. A replace therefore needs one more input, an
explicit binding of the existing node ids that other documents and code name
onto plan slots. This module owns that resolution and the document rebuild; the
command line owns reading, validation, linting and the atomic write.

The rules are deliberate and exhaustive. All problems are collected before one
:class:`ReworkError` is raised, so a refused run reports every reason at once
and writes nothing.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from elosern_map_core.documents import SettlementDocument

from tools.settlement_synthesis.generate import GenerationResult, Slot
from tools.settlement_synthesis.workspace import (
    WorkspaceError,
    WorkspaceView,
    incoming_reference_keys,
)

#: The one anchor slot id the generator emits.
ANCHOR_SLOT = "central_plaza"

#: The plan slot roles a nearest binding may resolve to.
NEAREST_ROLES = frozenset({"approach", "filler"})


@dataclass(frozen=True)
class ReworkPlan:
    """The final data of one replacement, with its resolution bookkeeping."""

    data: Mapping[str, Any]          # final settlement document data
    bound: Mapping[str, str]         # existing_id -> slot_id (resolved)
    dropped: tuple[str, ...]         # sorted existing ids removed
    renamed_slots: Mapping[str, str] # generated slot id -> suffixed id
    warnings: tuple[str, ...]


class ReworkError(ValueError):
    """One replace or prose input was refused; ``problems`` names every fault."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("\n".join(self.problems))


def protected_nodes(
    view: WorkspaceView, map_id: str
) -> tuple[frozenset[str], bool]:
    """The node ids a replace must keep, and whether the index is present.

    A missing reference index protects every existing node, because an absent
    index cannot prove that an external declaration does not name one.
    """

    document = view.world.settlements.get(map_id)
    if document is None:
        raise WorkspaceError(f"unknown map {map_id!r}")

    protected: set[str] = set()
    for interior in view.world.interiors.values():
        exterior = interior.exterior
        if exterior is not None and exterior.settlement == map_id:
            protected.add(exterior.node)
    for district in view.world.districts.districts.values():
        landmark = district.landmark
        if (
            landmark.domain == "settlement_node"
            and landmark.map_id == map_id
            and landmark.object_id is not None
        ):
            protected.add(landmark.object_id)

    keys = incoming_reference_keys(view.root)
    if keys is None:
        return frozenset(document.nodes), False
    prefix = f"settlement_node:{map_id}:"
    for key in keys:
        if key.startswith(prefix):
            protected.add(key[len(prefix):])

    if document.city_gate is not None:
        protected.add(document.city_gate.node)
    anchor = document.anchor_node
    if anchor is not None:
        protected.add(anchor.node_id)
    return frozenset(protected), True


def apply_bindings(
    existing: SettlementDocument,
    result: GenerationResult,
    bindings: Sequence[tuple[str, str]],
    protected: frozenset[str],
) -> ReworkPlan:
    """Resolve every binding and rebuild the document data in plan order."""

    slots = {slot.slot_id: slot for slot in result.slots}
    bound: dict[str, str] = {}
    slot_owner: dict[str, str] = {}
    problems: list[str] = []

    for existing_id, specification in bindings:
        if existing_id not in existing.nodes:
            problems.append(f"unknown_node:{existing_id}")
            continue
        if specification.startswith("nearest:"):
            reference_id = specification[len("nearest:"):]
            reference = slots.get(reference_id)
            if reference is None:
                problems.append(f"unknown_slot:{existing_id}->{specification}")
                continue
            candidates = [
                slot
                for slot in result.slots
                if slot.role in NEAREST_ROLES and slot.slot_id not in slot_owner
            ]
            if not candidates:
                problems.append(f"no_nearest:{existing_id}")
                continue
            chosen = min(candidates, key=lambda slot: _distance(slot, reference))
            bound[existing_id] = chosen.slot_id
            slot_owner[chosen.slot_id] = existing_id
            continue
        slot = slots.get(specification)
        if slot is None:
            problems.append(f"unknown_slot:{existing_id}->{specification}")
            continue
        if specification in slot_owner:
            problems.append(f"duplicate_slot:{specification}")
            continue
        bound[existing_id] = specification
        slot_owner[specification] = existing_id

    anchor = existing.anchor_node
    if anchor is not None and anchor.node_id in bound:
        slot_id = bound[anchor.node_id]
        if slot_id != ANCHOR_SLOT:
            problems.append(f"anchor_mismatch:{slot_id}")
    for node_id in sorted(protected):
        if node_id not in bound:
            problems.append(f"unbound_protected:{node_id}")

    if problems:
        raise ReworkError(problems)

    final_ids = _final_ids(result.slots, bound, slot_owner)
    data = _rebuild_data(existing, result, final_ids, slot_owner)
    dropped = tuple(sorted(set(existing.nodes) - set(bound)))
    renamed = {
        slot.slot_id: final_ids[slot.slot_id]
        for slot in result.slots
        if slot.slot_id not in slot_owner
        and final_ids[slot.slot_id] != slot.slot_id
    }
    return ReworkPlan(
        data=data,
        bound=dict(bound),
        dropped=dropped,
        renamed_slots=renamed,
        warnings=tuple(sorted(set(result.warnings))),
    )


def ordered_retained_tree(
    retained_tree: Mapping[str, Any], data: Mapping[str, Any]
) -> Mapping[str, Any]:
    """A retained YAML tree whose node keys follow ``data``.

    The codec's merge keeps a retained mapping key's existing position, so a
    replacement must reorder the node mapping before serializing or the file
    keeps the old authored order. Comments on retained entries survive.
    """

    from ruamel.yaml.comments import CommentedMap

    tree = copy.deepcopy(retained_tree)
    existing_nodes = tree.get("nodes")
    ordered: Any = CommentedMap()
    for node_id in data["nodes"]:
        if isinstance(existing_nodes, Mapping) and node_id in existing_nodes:
            ordered[node_id] = existing_nodes[node_id]
        else:
            ordered[node_id] = copy.deepcopy(data["nodes"][node_id])
    tree["nodes"] = ordered
    return tree


def _distance(left: Slot, right: Slot) -> float:
    return math.hypot(
        left.rel_m[0] - right.rel_m[0], left.rel_m[1] - right.rel_m[1]
    )


def _final_ids(
    slots: Sequence[Slot],
    bound: Mapping[str, str],
    slot_owner: Mapping[str, str],
) -> dict[str, str]:
    """Plan slot id -> final node id, suffixed on collision in plan order."""

    bound_slots = {slot_id: existing_id for existing_id, slot_id in bound.items()}
    used = set(bound_slots.values())
    final: dict[str, str] = {}
    for slot in slots:
        if slot.slot_id in slot_owner:
            final[slot.slot_id] = bound_slots[slot.slot_id]
            continue
        candidate = slot.slot_id
        if candidate in used:
            suffix = 2
            while f"{slot.slot_id}_{suffix}" in used:
                suffix += 1
            candidate = f"{slot.slot_id}_{suffix}"
        final[slot.slot_id] = candidate
        used.add(candidate)
    return final


def _rebuild_data(
    existing: SettlementDocument,
    result: GenerationResult,
    final_ids: Mapping[str, str],
    slot_owner: Mapping[str, str],
) -> dict[str, Any]:
    data = copy.deepcopy(dict(result.data))
    plan_nodes = data["nodes"]

    nodes: dict[str, Any] = {}
    for slot in result.slots:
        node = copy.deepcopy(plan_nodes[slot.slot_id])
        owner = slot_owner.get(slot.slot_id)
        if owner is not None:
            old = existing.nodes[owner]
            node["key"] = old.key
            node["desc"] = old.desc
            node["typeclass"] = old.typeclass
            node["scene_archetype"] = old.scene_archetype
        nodes[final_ids[slot.slot_id]] = node
    data["nodes"] = nodes

    data["roads"] = [
        {
            **road,
            "source": final_ids[road["source"]],
            "destination": final_ids[road["destination"]],
        }
        for road in data["roads"]
    ]

    entry = data.get("wilderness_entry")
    if entry is not None:
        data["wilderness_entry"] = {
            **entry,
            "gates": [
                {
                    **gate,
                    "destination_node": final_ids[gate["destination_node"]],
                }
                for gate in entry["gates"]
            ],
        }

    data["options"] = copy.deepcopy(dict(existing.options))
    data["exit_prototype"] = copy.deepcopy(dict(existing.exit_prototype))
    gate = existing.city_gate
    data["city_gate"] = (
        None
        if gate is None
        else {
            "node": gate.node,
            "exit_key": gate.exit_key,
            "exit_aliases": list(gate.exit_aliases),
        }
    )
    return data


__all__ = [
    "ANCHOR_SLOT",
    "ReworkError",
    "ReworkPlan",
    "apply_bindings",
    "ordered_retained_tree",
    "protected_nodes",
]
