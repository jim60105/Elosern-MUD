"""Observed focus and threat projected from one decision's settled history.

The monster utility score (monster-ai-observed-coordination, tactics design
sections 5 and 9) values two features an earlier slice did not have: how hard
this actor's own side has already pressed each opponent, and how dangerous each
opponent has proved. Both are read from the decision's own snapshot -- the
already settled, eligible :class:`~world.rules.monster_ai.models.PublicObservation`
records the session's observation memory projected -- and from nothing else. A
queued player request, an unresolved teammate choice and hidden intent have no
field here, so no decision can turn one into an enemy attack.

Focus
    For each opponent, the sum of the health pressure this actor's side has
    already dealt it, normalized by the largest positive sum among the
    decision's opponents. Only signed health magnitudes count, so an ally's
    heal of an enemy adds nothing: friendly healing never becomes an
    alternative non-strike attack. A per-plan value is the **mean over the
    plan's distinct hostile recipients**, so a wider plan gains nothing for its
    count and duplicate recipients cannot raise it. An empty (or entirely
    non-positive) history is zero for every opponent, which is exactly what the
    score's ``w_focus`` term must add when nothing has been observed.

Threat
    For each opponent, an age-decayed sum of the public outcomes it published
    against this side, normalized by the two factions' own current capacity:
    the health it took from this actor's side, the health it restored to its
    own side, and the status mounts it landed on this actor's side. Only the
    applicable opposing sources are ranked (see
    :func:`world.rules.monster_ai.utility.score_candidates`), and only for a
    profile whose target strategy values threat at all.

The window and the decay are bounded and named. A fact is eligible when it
lies inside the session ring's retention window
(:data:`OBSERVATION_WINDOW_ROUNDS`, the ring's own
``MAX_RETAINED_ROUNDS``); the projection re-applies that window because the
pending transaction overlay can offer records the committed ring would
eventually evict, and a fact from a future round must never count. Eligible
facts are weighted by :func:`decayed_weight`, whose version is fingerprinted
with the tuning, so a change to this arithmetic invalidates a recorded
fingerprint instead of silently changing a decision. Both constants are
declared with the other tuning leaves in :mod:`world.rules.monster_behaviour`
-- the module whose startup fingerprint they belong to -- and read here.

Deliberate conservatism
    An outcome that is not observed contributes nothing rather than an invented
    value:

    * a recipient identity the decision's own eligible domains do not contain
      (dead, escaped, absent, knocked out or faction-changed) contributes zero,
      so an old identifier is never permission to treat a target as pressured
      or as a threat;
    * a status mount is counted only when the record positively reports one
      (the ``buff_applied`` fact), names a recipient on this actor's side that
      the same record left without a health magnitude, and reached no
      recipient outside this side at all; one status set covers the whole
      action, so a record that also reports a self-bound mount or an immune
      target, or that also aimed at the other side, does not establish which
      recipient received the mount and contributes no control impact; an
      item's status keys describe both application and removal, so they are not
      treated as mount evidence either;
    * a mount is worth one bounded count rather than an invented magnitude, and
      a mount that also carried an observed health magnitude is valued once,
      through that magnitude.
"""

from collections.abc import Iterable, Mapping, Sequence

from world.rules.monster_ai.estimation import PlanEstimate
from world.rules.monster_ai.models import (
    DecisionSnapshot,
    PublicObservation,
)
from world.rules.monster_behaviour import (
    OBSERVATION_WINDOW_ROUNDS,
    THREAT_DECAY_STEPS,
    THREAT_DECAY_VERSION,
)
from world.rules.targeting import Relation

#: The status fact a status mount on a non-actor recipient publishes
#: (``world.rules.action.event_log``: "the actor applied a status effect to the
#: target"). A self-bound mount publishes ``self_buff_applied`` instead, which
#: says nothing about this actor's side.
_CONTROL_MOUNT_STATUS = "buff_applied"

#: Status facts that leave a record's mount recipient ambiguous: a self-bound
#: mount names the publisher, and an immune participant reports that a mount
#: aimed at it was neutralized, so neither record establishes that the named
#: opposing recipients received anything.
_AMBIGUOUS_CONTROL_STATUSES = frozenset({"self_buff_applied", "equipment_immune"})

#: The target strategies whose profiles value observed threat at all. The
#: existing highest_effective_power strategy is the one that already reads the
#: opposing side's capacity, so it opts in; lowest_hp keeps its legacy metric
#: ordering untouched.
_THREAT_STRATEGIES = frozenset({"highest_effective_power"})

#: The health magnitudes that count in either direction.
_NO_HEALTH = 0.0


def threat_is_valued(target_strategy: str) -> bool:
    """Return whether one target strategy uses observed threat in preference."""
    return target_strategy in _THREAT_STRATEGIES


def decayed_weight(age: int) -> float:
    """Return the bounded weight of one observation ``age`` rounds old.

    Age is measured in actual rounds from the decision's own round, so age zero
    is a fact from the round being decided (a teammate that already acted in
    this transaction) and counts fully. An age outside the observation window
    -- an older fact the ring has not evicted yet, or a fact from a round the
    decision has not reached -- contributes nothing.
    """
    if age < 0 or age >= OBSERVATION_WINDOW_ROUNDS or age >= len(THREAT_DECAY_STEPS):
        return 0.0
    return THREAT_DECAY_STEPS[age]


def observed_focus(
    snapshot: DecisionSnapshot,
    *,
    hostiles: Sequence[str],
) -> dict[str, float]:
    """Return each opponent's normalized observed allied pressure.

    ``hostiles`` are the decision's applicable hostile identities -- the same
    domain the static target ranks normalize over -- so an unavailable opponent
    can never dilute the others' focus. Every opponent with no observed allied
    pressure, and every decision with no positive pressure at all, is ``0.0``.
    """
    pressure = {identity: _NO_HEALTH for identity in hostiles}
    if not pressure:
        return pressure
    for record in _eligible_records(snapshot):
        if not _allied_source(snapshot, record.source_id):
            continue
        for identity, magnitude in record.magnitudes:
            if identity not in pressure or magnitude >= 0:
                # Positive magnitudes are healing; only harm is pressure.
                continue
            pressure[identity] += -float(magnitude)
    largest = max(pressure.values())
    if largest <= 0.0:
        return pressure
    return {identity: value / largest for identity, value in pressure.items()}


def observed_threat(
    snapshot: DecisionSnapshot,
    *,
    hostiles: Sequence[str],
    allies: Sequence[str],
    friendly_capacity: float,
    hostile_capacity: float,
) -> dict[str, float]:
    """Return each opponent's normalized, age-decayed observed threat.

    ``hostiles`` and ``allies`` are the decision's own eligible domains: the
    actor is a member of ``allies`` (its own side), and a named identity outside
    either domain contributes nothing. ``friendly_capacity`` is this side's
    current capacity -- the eligible live maximum-health sum the effect
    estimator already uses -- and ``hostile_capacity`` the opposing side's.
    """
    totals = {identity: _NO_HEALTH for identity in hostiles}
    if not totals:
        return totals
    friendly = frozenset(allies)
    hostile = frozenset(hostiles)
    friendly_scale = 1.0 / max(float(friendly_capacity), 1.0)
    hostile_scale = 1.0 / max(float(hostile_capacity), 1.0)
    for record in _eligible_records(snapshot):
        if record.source_id not in totals:
            continue
        weight = decayed_weight(snapshot.scope.round_index - record.round_index)
        if weight <= 0.0:
            continue
        totals[record.source_id] += weight * (
            _health_against(record, friendly, harm=True) * friendly_scale
            + _health_against(record, hostile, harm=False) * hostile_scale
            + _control_mounts(record, friendly) * friendly_scale
        )
    return totals


def focus_for_plan(
    estimate: PlanEstimate,
    focus: Mapping[str, float],
) -> float:
    """Return one plan's observed focus over its distinct hostile recipients.

    The plan's own estimated recipient projections decide which recipients are
    hostile, and each identity is counted once: a plan that reaches no hostile
    recipient carries no observed pressure at all, and a wider plan averages
    rather than sums, so an area plan gains nothing for its target count.
    """
    reached = {
        recipient.identity: focus.get(recipient.identity, _NO_HEALTH)
        for recipient in estimate.recipients
        if recipient.relation is Relation.ENEMY
    }
    if not reached:
        return _NO_HEALTH
    return sum(reached.values()) / len(reached)


def _eligible_records(snapshot: DecisionSnapshot) -> Iterable[PublicObservation]:
    """Yield one decision's observations inside the coordination window."""
    current = snapshot.scope.round_index
    for record in snapshot.observations:
        age = current - record.round_index
        if 0 <= age < OBSERVATION_WINDOW_ROUNDS:
            yield record


def _allied_source(snapshot: DecisionSnapshot, source_id: str) -> bool:
    """Return whether one observation's source is the actor's own side."""
    if source_id == snapshot.actor.identity:
        return True
    participant = snapshot.participant(source_id)
    return participant is not None and participant.relation in (
        Relation.SELF,
        Relation.ALLY,
    )


def _health_against(
    record: PublicObservation,
    members: frozenset[str],
    *,
    harm: bool,
) -> float:
    """Return one record's signed health magnitude against one side.

    ``harm`` selects the damage direction (a negative magnitude on a member of
    the side) and its absence the recovery direction (a positive magnitude on a
    member of the side), so healing handed to the enemy is never pressure and
    self-inflicted harm is never opposing support.
    """
    total = _NO_HEALTH
    for identity, magnitude in record.magnitudes:
        if identity not in members:
            continue
        if harm and magnitude < 0:
            total += -float(magnitude)
        elif not harm and magnitude > 0:
            total += float(magnitude)
    return total


def _control_mounts(record: PublicObservation, allies: frozenset[str]) -> float:
    """Return one record's observed status mounts on the actor's own side.

    The compact record keeps one status set for its whole action, so a mount
    counts only when that record positively reports one, names no recipient
    outside this side, and names a recipient of this side the same record left
    without a health magnitude. A record that also reached the other side does
    not establish that the mount landed here, a record that reports a
    self-bound mount or an immune target does not establish its recipient, and
    a mount already carried by an observed health magnitude is valued once
    through that magnitude. One record is worth one bounded mount.
    """
    statuses = frozenset(record.statuses)
    if _CONTROL_MOUNT_STATUS not in statuses:
        return _NO_HEALTH
    if statuses & _AMBIGUOUS_CONTROL_STATUSES:
        return _NO_HEALTH
    if any(identity not in allies for identity in record.recipient_ids):
        # The mount's own recipient is not recoverable from the record, so an
        # action that also aimed at the other side cannot establish that the
        # mount landed on ours; unknown contributes zero.
        return _NO_HEALTH
    observed_health = {identity for identity, _ in record.magnitudes}
    if any(
        identity in allies and identity not in observed_health
        for identity in record.recipient_ids
    ):
        return 1.0
    return _NO_HEALTH
