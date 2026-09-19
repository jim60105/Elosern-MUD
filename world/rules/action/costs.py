"""Cost, practice, and time stages of the action pipeline (steps 6 and 8).

Resource deduction reuses the shared :func:`world.rules.action.gates._adjusted_costs`
arithmetic, skill practice stages one dedupe-claim award per distinct target,
and the step-8 lookup resolves the world-clock time cost.
"""

from typing import Any

from world.rules.progression import grant_skill_practice_xp, practice_claim_key
from world.skills.registry import SkillDef

from world.rules.action.contracts import (
    _entity_key,
    _event_context,
    DEFAULT_CAST_SECONDS,
    SKILL_TIME_OVERRIDES,
    ActionRequest,
    PendingEffect,
    RejectedAction,
    RejectReason,
)
from world.rules.action.gates import _adjusted_costs, _stored_trait_value


def _deduct_resource(trait: Any, amount: int) -> None:
    if hasattr(trait, "current"):
        trait.current = trait.current - amount
    else:
        trait.value = trait.value - amount


def _step6_resource_deduction(
    actor: Any,
    skill: SkillDef,
    scale: float = 1.0,
) -> list[PendingEffect]:
    pending = []
    for resource_key, amount in _adjusted_costs(actor, skill, scale).items():
        trait = getattr(actor.traits, resource_key)
        if _stored_trait_value(trait) < amount:
            raise RejectedAction(
                RejectReason.RESOURCE_DEDUCTION_FAILED,
                resource_key,
            )
        if resource_key == "mp":
            from world.rules.mp_flow import apply_mp_change

            pending.append(
                PendingEffect(
                    actor,
                    f"resource_spend|{_entity_key(actor)}|{resource_key}|{amount}",
                    frozenset({"traits"}),
                    lambda actor=actor, amount=amount, skill_key=skill.key: (
                        apply_mp_change(actor, -amount, source_skill=skill_key)
                    ),
                )
            )
        else:
            pending.append(
                PendingEffect(
                    actor,
                    f"resource_spend|{_entity_key(actor)}|{resource_key}|{amount}",
                    frozenset({"traits"}),
                    lambda trait=trait, amount=amount: _deduct_resource(trait, amount),
                )
            )
    return pending


def _step6_skill_practice(
    request: ActionRequest,
    skill: SkillDef,
    targets: list[Any],
    claims_out: list[tuple[Any, str, Any]],
    unlocks_out: list[str],
) -> list[PendingEffect]:
    """Stage one practice award per DISTINCT target (DC3).

    An AREA hit accrues for each initially-living target it resolved against
    (dedupe claims are ``(actor, skill, target)`` triples), while a NONE/SELF
    skill with no targets accrues once against ``None``. A simulated (guild
    examination) context passes the nonlethal marker, so the whole staged
    batch awards nothing. Every claim the batch actually takes is appended to
    ``claims_out`` so a rolled-back commit can release them (a failed action
    must not silence the same tick's legitimate retry). Unlock lines a live
    award appends to ``unlocks_out`` are notification candidates only — the
    caller folds them into the result AFTER the commit succeeds.
    """
    simulated = bool(_event_context(request).get("simulated"))
    seen: list[Any] = []
    seen_keys: set[Any] = set()
    for target in targets:
        key = practice_claim_key(request.actor, skill.key, target)[2]
        if key not in seen_keys:
            seen_keys.add(key)
            seen.append(target)
    staged_targets: list[Any] = seen or [None]
    pending: list[PendingEffect] = []
    for target in staged_targets:
        actor = request.actor
        target_key = "-" if target is None else _entity_key(target)
        pending.append(
            PendingEffect(
                actor,
                f"skill_practice|{_entity_key(actor)}|{skill.key}|{target_key}",
                frozenset({"progression"}),
                lambda actor=actor, skill_key=skill.key, target=target,
                simulated=simulated, claims_out=claims_out,
                unlocks_out=unlocks_out: _apply_practice(
                    actor, skill_key, target, simulated, claims_out, unlocks_out
                ),
            )
        )
    return pending


def _apply_practice(
    actor: Any,
    skill_key: str,
    target: Any,
    simulated: bool,
    claims_out: list[tuple[Any, str, Any]],
    unlocks_out: list[str],
) -> None:
    """Apply one staged practice award, recording claims and unlock lines."""
    if grant_skill_practice_xp(
        actor, skill_key, target=target, nonlethal=simulated, unlocks_out=unlocks_out
    ):
        claims_out.append(practice_claim_key(actor, skill_key, target))


def _step8_time_cost(request: ActionRequest, skill: SkillDef) -> int:
    seconds = SKILL_TIME_OVERRIDES.get(skill.key, DEFAULT_CAST_SECONDS)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise RejectedAction(
            RejectReason.TIME_COST_LOOKUP_FAILED,
            f"{skill.key}: {seconds!r}",
        )
    return seconds
