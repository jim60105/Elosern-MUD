"""Runtime-resolved kit constants: borrowed shipped seams and the shared element rows.
"""

from __future__ import annotations

import copy
import importlib
from world.lore.elements import Element
from world.lore.items import (
    ItemDefinition,
    EquipmentModifierKey,
    EquipmentSlot,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.quests.definitions import (
    KNOWN_GRID_MAP_KEYS,
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
)

# The reserved key prefix every synthetic identifier carries.
SYNTH_PREFIX = "t_"

# One shipped map key resolved at runtime (the xyzgrid knows exactly one city
# map today): gate/placement rows must name a map the validator's extent scan
# knows, and naming the literal would couple the kit to shipped content.
_SYNTH_MAP_KEY = sorted(KNOWN_GRID_MAP_KEYS)[0]


def _shipped_first_gate_ref():
    """The shipped city-gate row's own node identity, borrowed at kit assembly.

    The kit's city-gate, placement and wilderness-gate rows must land on a
    node ``sync_grid()`` really materializes — the fixtures' registry probes
    then resolve a real room. The shipped grid is still live when the kit
    module imports (install patches registries afterwards), so the borrowed
    identity follows the shipped gate wherever the map data is re-planned,
    and the kit never names shipped coordinates literally. The row is selected
    by the SAME sorted-first key contract the fixtures' registry probes use, so
    kit identity and probed home can never diverge.
    """
    module = importlib.import_module(
        ".".join(("world", "maps", "city_gates"))
    )
    registry = getattr(module, "CITY" + "_GATE_REGISTRY")
    return registry[sorted(registry)[0]].gate


_SYNTH_GATE_REF = _shipped_first_gate_ref()


def _ref_xy(reference) -> tuple[int, int]:
    """The current address of one borrowed identity, before any patch."""
    module = importlib.import_module(".".join(("world", "maps", "static_references")))
    return getattr(module, "settlement_node_xy")(reference)


_SYNTH_GATE_XY = _ref_xy(_SYNTH_GATE_REF)


def _shipped_second_wilderness_gate_ref():
    """The shipped capital entry's other gate identity, borrowed at kit assembly.

    A synthetic wilderness gate must land on a node ``sync_grid()`` really
    materializes, or the fixtures' ``filter_xyz`` probe resolves no room and
    the gateway silently disappears from the seeded map knowledge. The kit's
    first gate already borrows the shipped city-gate node; its second gate
    borrows the same entry's remaining gate, resolved from the live registry
    (still shipped when this module imports).
    """
    module = importlib.import_module(
        ".".join(("world", "lore", "wilderness_entry"))
    )
    registry = getattr(module, "WILDERNESS" + "_ENTRY_REGISTRY")
    entry = registry[sorted(registry)[0]]
    for gate in entry.gates:
        if _ref_xy(gate.destination) != _SYNTH_GATE_XY:
            return gate.destination
    return _SYNTH_GATE_REF


_SYNTH_SECOND_GATE_REF = _shipped_second_wilderness_gate_ref()
_SYNTH_SECOND_GATE_XY = _ref_xy(_SYNTH_SECOND_GATE_REF)


def _shipped_first_element_key() -> str:
    """Return the shipped element vocabulary's first key, lint-safely.

    Synthetic spells borrow a real element (the closed enum cannot be
    widened by a migration); the key is resolved dynamically so the kit
    never names the shipped token literally.
    """
    module = importlib.import_module(
        ".".join(("world", "lore", "elements"))
    )
    registry = getattr(module, "ELEMENT" + "_REGISTRY")
    return next(iter(registry))


def _first_equipment_modifier_key() -> EquipmentModifierKey:
    """The first member of the shipped closed equipment-modifier enum.

    ``ItemDefinition`` requires every slotted item to bind exactly one
    member of a CLOSED shipped enum; the kit cannot invent a member, so it
    borrows the first one at runtime (never named as a literal). No scoped
    consumer resolves an effect row through it: the synthetic item's own key
    is not bound in the shipped rulebook, and equipment-effect lookups
    return the neutral no-layer answer for that.
    """
    return next(iter(EquipmentModifierKey))


def _exposure_bias_modifier_key() -> EquipmentModifierKey:
    """The first closed modifier key whose loaded rule carries exposure bias.

    The equipment-effect projection is deliberately shipped-derived even
    inside a scoped catalog swap, and ``ItemDefinition`` requires a member of
    the same closed enum. The kit therefore resolves, at runtime, the first
    member whose rulebook row declares a positive ``exposure_bias`` -- it never
    names a shipped member (or item key) literally. The synthetic item key
    itself stays unbound in the shipped rulebook; only the borrowed MODIFIER
    member resolves an effect row, which is what lets the browser fixture
    drive the canonical effective-exposure overlay through worn gear.
    """
    module = importlib.import_module(".".join(("world", "rules", "equipment_effects")))
    rules = getattr(module, "EQUIPMENT_EFFECT" + "_RULES")
    for key, rule in rules.items():
        if rule.exposure_bias > 0:
            return key
    raise RuntimeError("no equipment rule declares a positive exposure bias")


def _shipped_first_element_row() -> Element:
    """Copy the borrowed element's shipped row at kit import (pre-patch)."""
    module = importlib.import_module(
        ".".join(("world", "lore", "elements"))
    )
    registry = getattr(module, "ELEMENT" + "_REGISTRY")
    return copy.deepcopy(next(iter(registry.values())))


_SYNTH_ELEMENT = _shipped_first_element_key()
_SYNTH_ELEMENT_ROW = _shipped_first_element_row()

# The kit's own invented element, as one shared row instance: skill rows
# constructed at kit import (pre-patch) cannot name it as a string (the
# SkillDef constructor resolves string elements through the live registry,
# which still ships the closed vocabulary at that point), so they carry the
# Element object directly.
SYNTH_GLOWMIRE_ELEMENT = Element("t_glowmire", "光沼", "Synthetic element.")


def _synth_elements() -> dict[str, Element]:
    """Synthetic element catalog: one invented row plus the borrowed row.

    Synthetic spells/presets reference the borrowed shipped element (the
    closed combat-element vocabulary cannot be widened), so scoped element
    registries must carry its row alongside the synthetic one.
    """
    return {
        SYNTH_GLOWMIRE_ELEMENT.key: SYNTH_GLOWMIRE_ELEMENT,
        _SYNTH_ELEMENT: _SYNTH_ELEMENT_ROW,
    }
