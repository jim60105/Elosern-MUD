"""Immutable starter characters offered during account registration.

The single-module history is split into modules of a shared surface (the
``world.lore.items`` package precedent applies here):
:mod:`~world.lore.player_presets.vocab` holds the shared imports, the persona
prose-field constant, and the six frozen dataclasses; the ``data_*`` modules
each carry one contiguous, in-order slice of the former
``PLAYER_PRESET_REGISTRY`` literal (authored card comments included);
:mod:`~world.lore.player_presets.assembly` concatenates the slices into
``PLAYER_PRESET_REGISTRY`` in exact global order; and
:mod:`~world.lore.player_presets.validation` holds the twelve fail-closed
load-time validators, run over the assembled registry below in the exact
order the single module ran them.

Every name resolves through this package's namespace exactly as the single
``world/lore/player_presets.py`` module exported it: consumers keep importing
``world.lore.player_presets``. ``PLAYER_PRESET_REGISTRY`` is re-exported live
from the assembly (never rebound here), so in-place views of that one dict
(e.g. ``patch.dict`` seams in tests) stay visible through every import path.
"""

from world.lore.player_presets.assembly import PLAYER_PRESET_REGISTRY
from world.lore.player_presets.validation import (
    _validate_preset_affinity_elements,
    _validate_preset_disguised_stats,
    _validate_preset_fallback_keys,
    _validate_preset_identities,
    _validate_preset_personas,
    _validate_preset_sex,
    _validate_preset_sexual_baselines,
    _validate_preset_skill_kits,
    _validate_preset_skill_proficiency,
    _validate_preset_starting_companions,
    _validate_preset_starting_equipment,
    _validate_preset_starting_items,
)
from world.lore.player_presets.vocab import (
    _PERSONA_PROSE_FIELDS,
    PlayerPreset,
    PresetAppearance,
    PresetIdentity,
    PresetPersona,
    PresetSexualBaseline,
    StartingCompanion,
)

# Byte-identical old-module namespace parity: the single-module history's
# top-level imports are part of its observable surface (probes read the
# registry and its vocabularies through getattr string-concat seams, and
# tests import the validator functions by name). These stay module-qualified
# so a package-path `patch(..., create=True)` can never silently replace the
# canonical objects.
from dataclasses import KW_ONLY as KW_ONLY  # noqa: F401  (old namespace name)
from dataclasses import asdict as asdict  # noqa: F401
from dataclasses import dataclass as dataclass  # noqa: F401
from dataclasses import fields as fields  # noqa: F401
from math import isfinite as isfinite  # noqa: F401
from typing import Any as Any  # noqa: F401
from world.art.fallback_keys import validate_fallback_key as validate_fallback_key  # noqa: F401
from world.lore.elements import ELEMENT_REGISTRY as ELEMENT_REGISTRY  # noqa: F401
from world.lore.items import ITEM_REGISTRY as ITEM_REGISTRY  # noqa: F401
from world.lore.races import RACE_REGISTRY as RACE_REGISTRY  # noqa: F401
from world.lore.races import SUBRACE_REGISTRY as SUBRACE_REGISTRY  # noqa: F401
from world.lore.sex import SEX_VALUES as SEX_VALUES  # noqa: F401
from world.lore.sexual_vocab import AROUSAL_LEVELS as AROUSAL_LEVELS  # noqa: F401
from world.lore.sexual_vocab import BODY_PARTS as BODY_PARTS  # noqa: F401
from world.lore.sexual_vocab import CLIMAX_PHASE_LEVELS as CLIMAX_PHASE_LEVELS  # noqa: F401
from world.lore.sexual_vocab import EXPOSURE_LEVELS as EXPOSURE_LEVELS  # noqa: F401
from world.lore.sexual_vocab import GENERIC_BODY_PART as GENERIC_BODY_PART  # noqa: F401
from world.lore.sexual_vocab import SENSITIVITY_LEVELS as SENSITIVITY_LEVELS  # noqa: F401
from world.lore.sexual_vocab import SHAME_LEVELS as SHAME_LEVELS  # noqa: F401
from world.lore.sexual_vocab import WETNESS_LEVELS as WETNESS_LEVELS  # noqa: F401
from world.lore.starting_kits import (
    validate_wearable_loadout as validate_wearable_loadout,  # noqa: F401
)
from world.skills.registry import SKILL_REGISTRY as SKILL_REGISTRY  # noqa: F401
from world.skills.registry import SkillKind as SkillKind  # noqa: F401

# Byte-parity of the lazily-created namespace entry: the old module's
# annotated registry assignment populated ``__annotations__``; this
# annotation-only statement creates the same entry without rebinding the
# live registry object re-exported from the assembly.
PLAYER_PRESET_REGISTRY: dict[str, PlayerPreset]

__all__ = [
    "PLAYER_PRESET_REGISTRY",
    "PlayerPreset",
    "PresetAppearance",
    "PresetIdentity",
    "PresetPersona",
    "PresetSexualBaseline",
    "StartingCompanion",
    "_PERSONA_PROSE_FIELDS",
    "_validate_preset_affinity_elements",
    "_validate_preset_disguised_stats",
    "_validate_preset_fallback_keys",
    "_validate_preset_identities",
    "_validate_preset_personas",
    "_validate_preset_sex",
    "_validate_preset_sexual_baselines",
    "_validate_preset_skill_kits",
    "_validate_preset_skill_proficiency",
    "_validate_preset_starting_companions",
    "_validate_preset_starting_equipment",
    "_validate_preset_starting_items",
]

# Load-time invariants, matching the single-module history: the twelve
# validators run when this package first imports, in the exact old order,
# before any consumer reads the registry.
_validate_preset_skill_kits(PLAYER_PRESET_REGISTRY)
_validate_preset_identities(PLAYER_PRESET_REGISTRY)
_validate_preset_affinity_elements(PLAYER_PRESET_REGISTRY)
_validate_preset_starting_items(PLAYER_PRESET_REGISTRY)
_validate_preset_starting_equipment(PLAYER_PRESET_REGISTRY)
_validate_preset_sex(PLAYER_PRESET_REGISTRY)
_validate_preset_personas(PLAYER_PRESET_REGISTRY)
_validate_preset_skill_proficiency(PLAYER_PRESET_REGISTRY)
_validate_preset_disguised_stats(PLAYER_PRESET_REGISTRY)
_validate_preset_sexual_baselines(PLAYER_PRESET_REGISTRY)
_validate_preset_starting_companions(PLAYER_PRESET_REGISTRY)
_validate_preset_fallback_keys(PLAYER_PRESET_REGISTRY)
