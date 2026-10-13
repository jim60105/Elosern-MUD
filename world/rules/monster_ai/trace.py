"""Opt-in trace of one monster utility decision.

A decision normally reports nothing but its selected request: the resolver owns
settlement, and the only facade line a utility decision can produce is the
typed invalid-state warning, whose context stays a bounded summary of
identifiers. Detailed debugging and manual reports are a separate, opt-in
result: the caller passes a sink and receives one :class:`DecisionTrace` per
decision, which it can print as JSON or write to an explicit report file.

Every field is a scalar, a string, an enum or a tuple of them, and the selected
plan is the *normalized* projection of a request -- its skill, scale,
recognized shorthand and stable target identifiers -- never the live request,
its context or its entities. That is what keeps a trace JSON-safe and keeps
pending player intent, live object addresses and internal containers out of any
report.

One part of the record is deliberately richer: the decision's *initial
observation snapshot*, the already settled public facts the score read (their
round, sequence, source and faction, action, recipients, signed health
magnitudes and status facts). Same-process replay is defined against exactly
those inputs -- identical initial observations, state, scope and tuning -- so a
report that cannot hand them back cannot claim its decision is reproducible.
They are flat primitives, so they stay JSON-safe and carry no entity, request
or prose.
"""

from dataclasses import dataclass
from json import dumps
from pathlib import Path
from typing import Any

from world.rules.combat.decision_scope import ExecutionScope
from world.rules.monster_ai.candidates import CandidateSet
from world.rules.monster_ai.estimation import (
    EstimateSet,
    EstimationLimit,
    InvalidEstimate,
)
from world.rules.monster_ai.utility import ScoredCandidate


@dataclass(frozen=True, slots=True)
class TracePlan:
    """One candidate's normalized, JSON-safe projection."""

    skill_key: str
    scale: float
    shorthand: str | None
    target_ids: tuple[str, ...]
    score: float
    damage: float
    healing: float
    control: float
    focus: float
    preference: float
    finishing: float
    cost: float
    waste: float
    limits: tuple[EstimationLimit, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Return this projection as a JSON-safe mapping."""
        return {
            "skill_key": self.skill_key,
            "scale": self.scale,
            "shorthand": self.shorthand,
            "target_ids": list(self.target_ids),
            "score": self.score,
            "damage": self.damage,
            "healing": self.healing,
            "control": self.control,
            "focus": self.focus,
            "preference": self.preference,
            "finishing": self.finishing,
            "cost": self.cost,
            "waste": self.waste,
            "limits": [limit.value for limit in self.limits],
        }


@dataclass(frozen=True, slots=True)
class DecisionTrace:
    """One decision's complete, opt-in diagnostic record.

    ``scope`` is ``(session id, round index, actor id, slot index, context
    mode)``; ``inspected`` is true when the decision ran outside any execution
    scope, which is exactly when the seed came from the canonical inspection
    identity and the snapshot fingerprint.
    """

    scope: tuple[str, int, str, int, str]
    inspected: bool
    algorithm_version: int
    configuration_fingerprint: str
    snapshot_fingerprint: str
    intelligence: int
    temperature: float
    seed: int
    candidates: int
    rejections: tuple[tuple[str, str, str | None], ...] = ()
    exclusions: tuple[tuple[str, str], ...] = ()
    unavailable: tuple[tuple[str, str, str | None], ...] = ()
    omitted_estimates: tuple[tuple[str, str], ...] = ()
    omitted_families: int = 0
    omitted_targets: int = 0
    exhausted: bool = False
    observations: tuple[tuple[Any, ...], ...] = ()
    plans: tuple[TracePlan, ...] = ()
    selected: TracePlan | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return this record as a JSON-safe mapping."""
        session_id, round_index, actor_id, slot_index, context_mode = self.scope
        return {
            "scope": {
                "session": session_id,
                "round": round_index,
                "actor": actor_id,
                "slot": slot_index,
                "context_mode": context_mode,
                "inspected": self.inspected,
            },
            "algorithm_version": self.algorithm_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "intelligence": self.intelligence,
            "temperature": self.temperature,
            "seed": self.seed,
            "candidates": self.candidates,
            "rejections": [
                {"skill_key": skill, "reason": reason, "detail": detail}
                for skill, reason, detail in self.rejections
            ],
            "exclusions": [
                {"identity": identity, "reason": reason}
                for identity, reason in self.exclusions
            ],
            "unavailable": [
                {"skill_key": skill, "reason": reason, "detail": detail}
                for skill, reason, detail in self.unavailable
            ],
            "omitted_estimates": [
                {"identity": identity, "reason": reason}
                for identity, reason in self.omitted_estimates
            ],
            "omitted_families": self.omitted_families,
            "omitted_targets": self.omitted_targets,
            "exhausted": self.exhausted,
            "observations": [list(record) for record in self.observations],
            "plans": [plan.to_payload() for plan in self.plans],
            "selected": None if self.selected is None else self.selected.to_payload(),
        }

    def summary_context(self) -> dict[str, Any]:
        """Return the bounded summary a facade line may carry.

        Counts and identifiers only: no feature value, no plan and no
        selection detail ever rides an ordinary facade context.
        """
        session_id, round_index, actor_id, slot_index, context_mode = self.scope
        return {
            "session": session_id,
            "round": round_index,
            "slot": slot_index,
            "char": actor_id,
            "mode": context_mode,
            "inspected": self.inspected,
            "candidates": self.candidates,
            "plans": len(self.plans),
            "selected": None if self.selected is None else self.selected.skill_key,
        }


def trace_scope(scope: ExecutionScope | None) -> tuple[str, int, str, int, str]:
    """Return the recorded scope of one decision, canonical when inspected."""
    if scope is None:
        return ("", 0, "", 0, "normal")
    return (
        scope.session_id,
        scope.round_index,
        scope.actor_id,
        scope.slot_index,
        scope.context_mode,
    )


def trace_plan(scored: ScoredCandidate) -> TracePlan:
    """Return one scored candidate's normalized projection."""
    plan = scored.plan
    return TracePlan(
        skill_key=plan.skill_key,
        scale=plan.scale,
        shorthand=plan.shorthand,
        target_ids=tuple(scored.identity.target_ids),
        score=scored.score,
        damage=scored.damage,
        healing=scored.healing,
        control=scored.control,
        focus=scored.focus,
        preference=scored.preference,
        finishing=scored.finishing,
        cost=scored.cost,
        waste=scored.waste,
        limits=scored.limits,
    )


def trace_observations(snapshot: Any) -> tuple[tuple[Any, ...], ...]:
    """Return one decision's initial observation snapshot, as flat primitives.

    The replay evidence, in the snapshot's own order: where each settled fact
    happened, who published it and as which faction, what was used, who
    received it, the signed health magnitudes observed and the status facts
    recorded. Nothing else about the decision's state travels with it; the
    snapshot fingerprint already identifies that. Every record and every
    sequence inside it is a tuple, so the JSON payload a report builds from
    these values can never alias -- and therefore never mutate -- the
    observations the decision actually reproduced.
    """
    return tuple(
        (
            record.round_index,
            record.sequence,
            record.source_id,
            record.source_faction,
            record.action_key,
            tuple(record.recipient_ids),
            tuple(
                (identity, float(magnitude))
                for identity, magnitude in record.magnitudes
            ),
            tuple(record.statuses),
        )
        for record in snapshot.observations
    )


def trace_rejections(candidates: CandidateSet) -> tuple[tuple[str, str, str | None], ...]:
    """Return every refusal of one candidate enumeration, as plain values."""
    return tuple(
        (item.identity.skill_key, item.reason.value, item.detail)
        for item in candidates.rejections
    )


def trace_exclusions(candidates: CandidateSet) -> tuple[tuple[str, str], ...]:
    """Return every mandatory-restriction removal of one enumeration."""
    return tuple(
        (str(item.identity), item.reason) for item in candidates.exclusions
    )


def trace_unavailable(
    candidates: CandidateSet,
) -> tuple[tuple[str, str, str | None], ...]:
    """Return every unusable owned skill of one enumeration."""
    return tuple(
        (item.skill_key, item.reason.value, item.detail)
        for item in candidates.unavailable
    )


def trace_omissions(estimates: EstimateSet) -> tuple[tuple[str, str], ...]:
    """Return every candidate the estimator refused, with its typed reason."""
    return tuple(
        (str(estimate.identity), estimate.reason.value)
        for estimate in estimates.estimates
        if isinstance(estimate, InvalidEstimate)
    )


def write_trace_report(path: Path, trace: DecisionTrace) -> None:
    """Write one decision's trace to an explicit JSON report file."""
    path.write_text(
        dumps(trace.to_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
