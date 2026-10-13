"""Focused modules of the monster combat AI decision boundary.

The implemented slices are the decision *inputs* -- the immutable no-write
snapshot and the shared deterministic legality every planned action passes
before it is scored -- and the bounded candidate enumeration that expands the
owned hostile damage skills into legal, deduplicated, budgeted proposals.
Effect estimation, utility scoring and sampling are later slices and are not
implemented here, so every production variant stays ``legacy`` and the legacy
decision body in :mod:`world.rules.monster_behaviour` is unchanged.

- :mod:`world.rules.monster_ai.models` -- the immutable models and the
  read-only snapshot fingerprint.
- :mod:`world.rules.monster_ai.snapshot` -- the decision-local no-create reads
  and the snapshot builder.
- :mod:`world.rules.monster_ai.legality` -- the shared plan legality.
- :mod:`world.rules.monster_ai.candidates` -- the bounded, deduplicated,
  semantically legal damage candidates.
"""

from world.rules.monster_ai.candidates import (
    DEFAULT_CANDIDATE_BUDGET,
    Candidate,
    CandidateExclusion,
    CandidateIdentity,
    CandidateRejection,
    CandidateSet,
    SkillObservation,
    canonical_plan,
    enumerate_candidates,
)
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
    "Candidate",
    "CandidateExclusion",
    "CandidateIdentity",
    "CandidateRejection",
    "CandidateSet",
    "CapabilityState",
    "DEFAULT_CANDIDATE_BUDGET",
    "DecisionReads",
    "DecisionScope",
    "DecisionSnapshot",
    "OwnedSkillSnapshot",
    "ParticipantSnapshot",
    "PlanVerdict",
    "PlannedAction",
    "PublicObservation",
    "SkillObservation",
    "build_decision_snapshot",
    "canonical_plan",
    "enumerate_candidates",
    "roster_index",
    "stable_identity",
    "validate_plan",
]
