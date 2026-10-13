"""Focused modules of the monster combat AI decision boundary.

The implemented slices are the decision *inputs* -- the immutable no-write
snapshot and the shared deterministic legality every planned action passes
before it is scored -- the bounded candidate enumeration that expands the owned
hostile damage skills into legal, deduplicated, budgeted proposals, and the
analytic effect estimation that projects each candidate's health effects with
settlement's own arithmetic, and the utility decision itself: the bounded score
of every supported candidate and the stable, independently seeded softmax
sampling that selects one. Every production variant is still authored
``legacy``, so the legacy decision body in
:mod:`world.rules.monster_behaviour` returns exactly what it returned before;
activating a variant is the separate staged-activation change's decision.

- :mod:`world.rules.monster_ai.models` -- the immutable models and the
  read-only snapshot fingerprint.
- :mod:`world.rules.monster_ai.snapshot` -- the decision-local no-create reads
  and the snapshot builder.
- :mod:`world.rules.monster_ai.legality` -- the shared plan legality.
- :mod:`world.rules.monster_ai.candidates` -- the bounded, deduplicated,
  semantically legal damage candidates.
- :mod:`world.rules.monster_ai.estimation` -- the signed, bounded health
  features of one candidate plan, with no dice, handlers, costs or events.
- :mod:`world.rules.monster_ai.utility` -- the bounded utility score of one
  candidate, with its three stable preference ranks.
- :mod:`world.rules.monster_ai.selection` -- canonical ordering, the stable
  softmax and the versioned execution-identity seed.
- :mod:`world.rules.monster_ai.trace` -- the opt-in, normalized decision
  trace.
"""

from world.rules.monster_ai.candidates import (
    DEFAULT_CANDIDATE_BUDGET,
    Candidate,
    CandidateExclusion,
    CandidateIdentity,
    CandidateRejection,
    CandidateSet,
    SkillObservation,
    enumerate_candidates,
)
from world.rules.monster_ai.estimation import (
    ApproximationClass,
    EffectDirection,
    EstimateSet,
    EstimationLimit,
    HealthFeature,
    InvalidEstimate,
    InvalidEstimateReason,
    PlanEstimate,
    RecipientProjection,
    ResourceProjection,
    estimate_candidates,
    estimate_plan,
)
from world.rules.monster_ai.legality import roster_index, validate_plan
from world.rules.monster_ai.models import (
    BuffProjection,
    CapabilityState,
    DecisionScope,
    DecisionSnapshot,
    DivertLimit,
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
from world.rules.monster_ai.selection import (
    SELECTION_SEED_VERSION,
    canonical_order,
    select_candidate,
    selection_seed,
    selection_seed_for,
    selection_temperature,
    softmax_probabilities,
)
from world.rules.monster_ai.trace import (
    DecisionTrace,
    TracePlan,
    write_trace_report,
)
from world.rules.monster_ai.utility import (
    MonsterAIStateError,
    ScoredCandidate,
    attack_utility,
    normalized_ranks,
    score_candidates,
)

__all__ = [
    "ApproximationClass",
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
    "DecisionTrace",
    "DivertLimit",
    "EffectDirection",
    "EstimateSet",
    "EstimationLimit",
    "HealthFeature",
    "InvalidEstimate",
    "InvalidEstimateReason",
    "MonsterAIStateError",
    "OwnedSkillSnapshot",
    "ParticipantSnapshot",
    "PlanVerdict",
    "PlannedAction",
    "PlanEstimate",
    "PublicObservation",
    "RecipientProjection",
    "ResourceProjection",
    "SELECTION_SEED_VERSION",
    "ScoredCandidate",
    "SkillObservation",
    "TracePlan",
    "attack_utility",
    "build_decision_snapshot",
    "canonical_order",
    "enumerate_candidates",
    "estimate_candidates",
    "estimate_plan",
    "normalized_ranks",
    "roster_index",
    "score_candidates",
    "select_candidate",
    "selection_seed",
    "selection_seed_for",
    "selection_temperature",
    "softmax_probabilities",
    "stable_identity",
    "validate_plan",
    "write_trace_report",
]
