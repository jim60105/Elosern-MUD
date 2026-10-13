"""Immutable models of the monster-AI decision boundary.

Every model here is a frozen value object built from scalars, stable
identifiers and immutable projections. A decision snapshot never carries a
mutable ORM entity, a lazy handler, a display label, a wall-clock timestamp or
a Python object address, so:

- nothing downstream of a decision can mutate the state the decision read;
- two decisions over identical settled state fingerprint identically, whatever
  their object identities were;
- hidden inputs -- a queued player request, an unresolved teammate choice, a
  ``disguised_stats`` display value -- have no representation to travel in.

Live participants are mapped back from a plan's stable identifiers only at the
request-reconstruction boundary (``world.rules.monster_ai.legality``), never
through a snapshot field.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from json import dumps
from typing import Any

from world.rules.action.contracts import RejectReason
from world.rules.targeting import Relation
from world.skills.registry import FactionConstraint, SkillKind, TargetSpec

#: The identity prefix of a persisted participant (see :func:`stable_identity`).
DBREF_PREFIX = "dbref:"
#: The identity prefix of a participant that carries no persisted identity.
KEY_PREFIX = "key:"


def stable_identity(entity: Any) -> str:
    """Return one participant's stable snapshot identity.

    A persisted participant is identified by its database reference, which
    never changes, never collides and is never a display label. An ephemeral
    double without one falls back to its own key, which is the only identity it
    has; a display name, a Python object address and the entity's ``repr`` are
    deliberately never used, so a snapshot cannot depend on where an object
    happens to live in memory.
    """
    pk = getattr(entity, "pk", None)
    if isinstance(pk, int) and not isinstance(pk, bool):
        return f"{DBREF_PREFIX}{pk}"
    return f"{KEY_PREFIX}{getattr(entity, 'key', '?')}"


@dataclass(frozen=True, slots=True)
class DecisionScope:
    """The real execution scope one decision belongs to.

    The session, the actual round and the actor's actual action slot: the
    identity a decision is reproducible against. Inspection outside an
    execution scope uses its own canonical values for the same fields, so a
    repeated inspection repeats its decision while a real round never shares
    another slot's identity.
    """

    session_id: str
    round_index: int
    slot_index: int


@dataclass(frozen=True, slots=True)
class CapabilityState:
    """Whether the participant can act at all this decision."""

    blocked_by_buff: bool
    actions_per_turn: int


@dataclass(frozen=True, slots=True)
class BuffProjection:
    """One active buff instance projected from persisted state.

    The projection carries the live instance's definition key, stack count,
    remaining game seconds and positional marker -- never the buff object, its
    handler or any cache entry it lives in.
    """

    key: str
    stacks: int
    remaining_seconds: int | None
    marker: str | None


@dataclass(frozen=True, slots=True)
class DivertLimit:
    """One active damage-diversion budget settlement would consume.

    Projected from the persisted buff cache without mounting a handler, so an
    estimate can subtract a known shield without running the damage handler:
    ``instance_key`` is the buff identity settlement orders diversion
    instances by (its own definition key then instance key order decides which
    budget absorbs first), ``gauge`` is the pool the diverted amount is paid
    from, ``fraction`` is the authored share of each strike's residual, and
    ``remaining_cap`` is the instance's authored cap minus what it has already
    spent.
    """

    instance_key: str
    definition_key: str
    gauge: str
    fraction: float
    remaining_cap: int


@dataclass(frozen=True, slots=True)
class ParticipantSnapshot:
    """One participant's immutable, no-create projection.

    Attributes:
        identity: The stable identity of the participant.
        relation: The participant's faction relation to the acting monster.
        present: Whether the resolved context places it with the actor.
        in_range: Whether the resolved context places it within reach.
        alive: Whether its stored hp is above zero.
        traits: The TRUE literal stored combat traits (never ``disguised_stats``).
        effective_traits: The same traits after the owned-passive and conferred
            grant fold -- the effective values combat reads.
        resources: Stored gauge ``(current, maximum)`` pairs by gauge key.
        capability: The participant's action capability projection.
        buffs: Active buff projections in stable key order.
    """

    identity: str
    relation: Relation
    present: bool
    in_range: bool
    alive: bool
    traits: Mapping[str, float]
    effective_traits: Mapping[str, float]
    resources: Mapping[str, tuple[int, int]]
    capability: CapabilityState
    buffs: tuple[BuffProjection, ...]


@dataclass(frozen=True, slots=True)
class OwnedSkillSnapshot:
    """One owned skill's stable registry identifiers."""

    key: str
    kind: SkillKind
    target_spec: TargetSpec
    faction_constraint: FactionConstraint


@dataclass(frozen=True, slots=True)
class PublicObservation:
    """One already-settled public fact an earlier action published.

    Only settled, publicly observable facts are representable: where the fact
    happened (round and sequence), who published it, which skill or item it
    was, who received it and which outcome statuses were observed. A queued
    player request, an unresolved teammate choice, hidden intent and a
    disguised stat have no field here, which is what keeps them out of a
    snapshot, its fingerprint and every input derived from it.
    """

    round_index: int
    sequence: int
    source_id: str
    action_key: str
    recipient_ids: tuple[str, ...]
    statuses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionSnapshot:
    """One decision's complete immutable input.

    The read-once projection a decision is made from: the execution scope, the
    actor, the participants, the owned skill metadata, the identity facts, the
    resolved context mode and the settled public observations. ``fingerprint``
    is derived from the snapshot's own content in ``__post_init__``, so it can
    never disagree with what it describes and never has to be trusted from a
    caller.
    """

    scope: DecisionScope
    actor: ParticipantSnapshot
    participants: tuple[ParticipantSnapshot, ...]
    owned_skills: tuple[OwnedSkillSnapshot, ...]
    species_key: str | None
    variant_key: str | None
    threat_tier: str | None
    context_mode: str
    observations: tuple[PublicObservation, ...] = ()
    fingerprint: str = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fingerprint", _fingerprint(self))

    def knows(self, identity: str) -> bool:
        """Return whether this decision's scope contains one identity."""
        if identity == self.actor.identity:
            return True
        return any(item.identity == identity for item in self.participants)

    def participant(self, identity: str) -> ParticipantSnapshot | None:
        """Return one participant's projection by stable identity."""
        if identity == self.actor.identity:
            return self.actor
        for item in self.participants:
            if item.identity == identity:
                return item
        return None


@dataclass(frozen=True, slots=True)
class PlannedAction:
    """One submitted plan a decision candidate is allowed to be.

    ``target_ids`` are stable participant identities, or ``shorthand`` is one
    approved AREA shorthand; the two are never both set. ``scale`` is the
    authored cast scale, preserved end to end rather than normalized away.
    """

    skill_key: str
    scale: float = 1.0
    target_ids: tuple[str, ...] = ()
    shorthand: str | None = None


@dataclass(frozen=True, slots=True)
class PlanVerdict:
    """The legality of one planned action at the decision boundary.

    ``reason`` and ``detail`` are the shared gates' own stable rejection pair,
    so a rejected plan is excluded before scoring with exactly the rejection
    settlement would raise. The resolver repeats its checks after initiative
    and stays authoritative.
    """

    legal: bool
    reason: RejectReason | None = None
    detail: str | None = None


def _participant_payload(participant: ParticipantSnapshot) -> dict[str, Any]:
    """Return one participant's canonical fingerprint payload."""
    return {
        "identity": participant.identity,
        "relation": participant.relation.value,
        "present": participant.present,
        "in_range": participant.in_range,
        "alive": participant.alive,
        "traits": {key: participant.traits[key] for key in sorted(participant.traits)},
        "effective_traits": {
            key: participant.effective_traits[key]
            for key in sorted(participant.effective_traits)
        },
        "resources": {
            key: list(participant.resources[key])
            for key in sorted(participant.resources)
        },
        "capability": [
            participant.capability.blocked_by_buff,
            participant.capability.actions_per_turn,
        ],
        "buffs": [
            [buff.key, buff.stacks, buff.remaining_seconds, buff.marker]
            for buff in participant.buffs
        ],
    }


def _observation_payload(observation: PublicObservation) -> list[Any]:
    """Return one settled observation's canonical fingerprint payload."""
    return [
        observation.round_index,
        observation.sequence,
        observation.source_id,
        observation.action_key,
        list(observation.recipient_ids),
        list(observation.statuses),
    ]


def _payload(snapshot: DecisionSnapshot) -> dict[str, Any]:
    """Return the canonical, allowlisted fingerprint payload of one snapshot.

    Every field is named explicitly and every sequence is in a stable order, so
    the payload can never pick up an unordered container, a display label, an
    object address, a handler, a wall-clock timestamp or a hidden input by
    accident. ``json.dumps(..., sort_keys=True)`` canonicalizes the mappings;
    the sequences below are ordered by their own stable identifiers because
    ``sort_keys`` alone would not canonicalize them.
    """
    return {
        "scope": [
            snapshot.scope.session_id,
            snapshot.scope.round_index,
            snapshot.scope.slot_index,
        ],
        "actor": _participant_payload(snapshot.actor),
        "participants": [
            _participant_payload(item)
            for item in sorted(snapshot.participants, key=lambda p: p.identity)
        ],
        "owned_skills": [
            [
                skill.key,
                skill.kind.value,
                skill.target_spec.value,
                skill.faction_constraint.value,
            ]
            for skill in sorted(snapshot.owned_skills, key=lambda s: s.key)
        ],
        "identity": [
            snapshot.species_key,
            snapshot.variant_key,
            snapshot.threat_tier,
        ],
        "context_mode": snapshot.context_mode,
        "observations": [
            _observation_payload(observation)
            for observation in sorted(
                snapshot.observations,
                key=lambda o: (
                    o.round_index,
                    o.sequence,
                    o.source_id,
                    o.action_key,
                ),
            )
        ],
    }


def _fingerprint(snapshot: DecisionSnapshot) -> str:
    """Return the read-only digest of one snapshot's canonical payload."""
    encoded = dumps(
        _payload(snapshot),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return sha256(encoded.encode("utf-8")).hexdigest()
