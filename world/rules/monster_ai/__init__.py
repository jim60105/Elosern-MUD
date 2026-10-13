"""Focused modules of the monster combat AI decision boundary.

This slice implements the decision *inputs* only: the immutable no-write
snapshot and the shared deterministic legality every planned action passes
before it is scored. Candidate enumeration, effect estimation, utility scoring
and sampling are later slices and are not implemented here, so every
production variant stays ``legacy`` and the legacy decision body in
:mod:`world.rules.monster_behaviour` is unchanged.

- :mod:`world.rules.monster_ai.models` -- the immutable models and the
  read-only snapshot fingerprint.
- :mod:`world.rules.monster_ai.snapshot` -- the decision-local no-create reads
  and the snapshot builder.
- :mod:`world.rules.monster_ai.legality` -- the shared plan legality.
"""

from world.rules.monster_ai.legality import roster_index, validate_plan
from world.rules.monster_ai.models import (
    BuffProjection,
    CapabilityState,
    DecisionScope,
    DecisionSnapshot,
    OwnedSkillSnapshot,
    ParticipantSnapshot,
    PlannedAction,
    PlanVerdict,
    PublicObservation,
    stable_identity,
)
from world.rules.monster_ai.snapshot import (
    DecisionReads,
    build_decision_snapshot,
)

__all__ = [
    "BuffProjection",
    "CapabilityState",
    "DecisionReads",
    "DecisionScope",
    "DecisionSnapshot",
    "OwnedSkillSnapshot",
    "ParticipantSnapshot",
    "PlanVerdict",
    "PlannedAction",
    "PublicObservation",
    "build_decision_snapshot",
    "roster_index",
    "stable_identity",
    "validate_plan",
]
