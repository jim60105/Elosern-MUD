"""Skill definitions from design section 5.2 and ``skills-equipment``.

The frozen skill-lineage registry, split into modules of a shared surface
(the twelve prior registry-package precedents in this repo apply here):
:mod:`~world.skills.registry.vocab` holds the enums, bounds, immutable
collection types, and the ``SkillDef``/``SkillPrerequisite`` dataclasses;
:mod:`~world.skills.registry.builders` holds the seed-row builders; the
``data_*`` modules each carry one contiguous, in-order domain slice of the
former ``SKILL_REGISTRY`` literal (section comments included);
:mod:`~world.skills.registry.assembly` concatenates the slices into
``SKILL_REGISTRY`` in exact global order; and
:mod:`~world.skills.registry.validation` runs the fail-closed
prerequisite-graph check and owns the reverse-edge caches.

Every name resolves through this package's namespace exactly as the single
``world/skills/registry.py`` module exported it: consumers keep importing
``world.skills.registry``. ``SKILL_REGISTRY`` is re-exported live from the
assembly (never rebound here), so the ``world/rules/disengage.py`` and
``world/skills/sexual_acts`` registration side effects — in-place
mutations of that one dict — stay visible through every import path.

``SkillKind`` and ``TargetSpec`` are forward declarations for change 8's
action resolver to import rather than redefine. Every ``effects`` string is
parsed into a typed dataclass by ``world.skills.effects.parse_effect`` at
construction; see that module for the recognized effect-ID conventions.

``SkillPrerequisite`` declares the skill-lineage DAG (use-driven-progression
design §9): an edge ``consumer -> (skill_key, min_proficiency)`` gating USE
(never ownership). ``validate_prerequisite_graph`` runs fail-closed at
registry load and caches the reverse-edge map the tip-cap derivation reads.
"""

from world.skills.registry.assembly import SKILL_REGISTRY
from world.skills.registry.builders import (
    _body_multiplier,
    _elemental_spells,
    _skill,
    _spell,
)
from world.skills.registry.validation import (
    declared_prerequisites,
    prerequisite_consumers,
    validate_prerequisite_graph,
)
from world.skills.registry.vocab import (
    DESCRIPTION_MAX,
    LABEL_MAX,
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    _FrozenDict,
    _FrozenList,
    _validate_metadata,
)

# Load-time invariant, matching the single-module history: the lineage graph
# is validated when this package first imports, before any consumer reads it.
validate_prerequisite_graph(SKILL_REGISTRY)

__all__ = [
    "DESCRIPTION_MAX",
    "LABEL_MAX",
    "FactionConstraint",
    "SKILL_REGISTRY",
    "SkillCategory",
    "SkillDef",
    "SkillKind",
    "SkillPrerequisite",
    "TargetSpec",
    "declared_prerequisites",
    "prerequisite_consumers",
    "validate_prerequisite_graph",
]
