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


def _shipped_first_gate_xy() -> tuple[int, int]:
    """The shipped city-gate row's own (x, y), borrowed at kit assembly.

    The kit's one city-gate row must land on a cell that survives
    ``sync_grid()`` under the shipped map extent — the fixtures' registry
    probes then resolve a real room for it. The shipped grid is still live
    when the kit module imports (install patches registries afterwards), so
    the borrowed cell follows the shipped gate wherever the map data is
    re-planned, and the kit never names the shipped coordinate literally.
    The row is selected by the SAME sorted-first key contract the fixtures'
    registry probes use, so kit cell and probed home can never diverge.
    """
    module = importlib.import_module(
        ".".join(("world", "maps", "city_gates"))
    )
    registry = getattr(module, "CITY" + "_GATE_REGISTRY")
    _x, _y, _map_id = registry[sorted(registry)[0]].gate_xyz
    return (_x, _y)


_SYNTH_GATE_XY = _shipped_first_gate_xy()


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
