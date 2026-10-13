"""Complete shared legality for one planned monster action.

A planned action is only scored if it is legal by exactly the gates
deterministic settlement enforces: :func:`validate_plan` reconstructs the
plan's live participants from its stable identifiers and then runs the shared
submission revalidation, which is the same ordered ownership, active-kind,
identity, lineage, proficiency, resource, capability, cast, interaction and
target legality ``ActionResolver`` applies. There is no second rules
authority here and no simulation of effects: the resolver stays authoritative
and repeats its checks after initiative, so a plan that was legal when the
decision was made can still be rejected at settlement.

The reconstruction boundary is the only place a live entity appears. The
decision-local read set is never handed to the authoritative resolver, and the
snapshot's identifiers are never invented from live state.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from world.rules.action.contracts import RejectReason
from world.rules.action_preview import revalidate_submission
from world.rules.monster_ai.models import (
    DecisionSnapshot,
    PlannedAction,
    PlanVerdict,
    stable_identity,
)


def roster_index(participants: Sequence[Any]) -> dict[str, Any]:
    """Return the identity index one decision's plans are reconstructed from.

    A caller builds this from the same participants the decision's snapshot
    describes, so a plan's stable identifiers resolve back to the live
    entities that identity map names -- and to nothing else.
    """
    return {stable_identity(participant): participant for participant in participants}


def validate_plan(
    snapshot: DecisionSnapshot,
    plan: PlannedAction,
    *,
    actor: Any,
    context: Any,
    roster: Mapping[str, Any],
    reads: Any = None,
) -> PlanVerdict:
    """Return one planned action's legality at the decision boundary.

    ``snapshot`` is the decision's frozen input and states which participants
    the decision covers; ``actor`` and ``context`` are the resolved execution
    context the plan is judged in; ``roster`` maps the snapshot's identities
    back to the live participants; ``reads`` is that decision's read set, so
    every plan of one decision reuses one read.

    A plan naming a participant the live roster no longer carries is reported
    as a missing target rather than silently dropped, and a plan that names a
    participant outside the decision's own scope is rejected as a shape
    mismatch: a decision never validates an action about an entity it did not
    decide about.
    """
    if plan.shorthand is not None:
        if plan.target_ids:
            return PlanVerdict(
                False, RejectReason.TARGET_SPEC_MISMATCH, plan.shorthand
            )
        targets: list[Any] | str = plan.shorthand
    else:
        for identity in plan.target_ids:
            if not snapshot.knows(identity):
                return PlanVerdict(
                    False, RejectReason.TARGET_SPEC_MISMATCH, identity
                )
            if identity not in roster:
                return PlanVerdict(
                    False, RejectReason.TARGET_NOT_PRESENT, identity
                )
        targets = [roster[identity] for identity in plan.target_ids]
    preview = revalidate_submission(
        actor,
        plan.skill_key,
        context,
        targets,
        scale=plan.scale,
        readings=reads,
    )
    return PlanVerdict(preview.enabled, preview.reason, preview.detail)
