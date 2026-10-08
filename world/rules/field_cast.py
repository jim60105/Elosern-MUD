"""The one deterministic field-cast routing entry and its read-only preview.

Exploration skill use has exactly two settlement routes (field-combat-
initiation D-1/D-6): a cast aimed at a living, co-located, hostile Monster
opens combat with that cast as the opening action
(``initiate_field_combat``); every other permitted cast settles through
``settle_out_of_combat_cast``. Both the text ``cast`` command and the
WebClient ``explore.cast`` adapter route through :func:`cast_in_field`, so the
routing gates (monster normalization, the damage-requires-monster gate, the
mixed-list rejection) can never diverge between the two surfaces.

:func:`preview_field_skill` is the side-effect-free counterpart for one owned
active skill at one scale: it reports the ordinary explicit candidates and the
monster openings the same gates would accept right now. It never rolls,
stages effects, creates or advances the world clock, persists a combat
session, or registers skip-safety. The resolver, the settlement boundary, and
the initiation boundary stay authoritative and rerun every gate.
"""

from dataclasses import dataclass
from typing import Any, Literal

from world.rules.action import ActionRequest, RejectReason
from world.rules.action_preview import adjusted_cost, revalidate_submission
from world.rules.combat_initiation import (
    _room_monsters,
    field_combat_target,
    initiate_field_combat,
    preview_field_opening,
)
from world.rules.targeting import RoomActionContext, requirement_for
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec

# The presentation bound on each candidate list (equal to the panel bound).
# A room exceeding it reports the overflow instead of truncating.
MAX_FIELD_CANDIDATES = 64


def is_damaging(skill: SkillDef | None) -> bool:
    """Whether a skill carries a damage effect (the field-routing predicate).

    The same string-prefix test the text command has always applied before
    settlement, kept in one place so the two surfaces agree.
    """
    return skill is not None and any(
        effect.startswith("damage:") for effect in skill.effects
    )


@dataclass(frozen=True)
class FieldCastOutcome:
    """The routed result of one field cast.

    Attributes:
        route: ``"settlement"`` for an ordinary field cast,
            ``"initiation"`` for a monster opening, ``"rejected"`` for a
            routing-gate refusal raised before either boundary ran.
        settlement: The ``CastSettlement`` of the ordinary route.
        combat_result: The ``submit_player_action``-shaped dict of the
            opening route (a rejection, an ordinary round, or a terminal
            outcome).
        reason: The routing-gate rejection reason (``route == "rejected"``).
        detail: The routing-gate rejection detail.
    """

    route: Literal["settlement", "initiation", "rejected"]
    settlement: Any = None
    combat_result: dict[str, Any] | None = None
    reason: RejectReason | None = None
    detail: str | None = None


def _rejected(reason: RejectReason, detail: str) -> FieldCastOutcome:
    return FieldCastOutcome("rejected", reason=reason, detail=detail)


def cast_in_field(
    actor: Any,
    skill_key: str,
    *,
    targets: list[Any] | tuple[Any, ...] = (),
    opening_target: Any = None,
    scale: float = 1.0,
    context: Any = None,
) -> FieldCastOutcome:
    """Route one exploration cast to field settlement or field initiation.

    Exactly one target form applies: an explicit ordinary ``targets`` list
    (possibly empty, for NONE/SELF) or one monster ``opening_target`` anchor.
    Supplying both is a shape mismatch. Routing, in order:

    1. An explicit anchor opens combat through ``initiate_field_combat``
       (which enforces its own anchor, availability, and preflight gates).
    2. A one-element list naming a living co-located monster normalizes to
       that anchor, whatever the skill does — the text command's long-
       standing behaviour (healing a monster still starts the fight).
    3. A longer list containing a living co-located monster is refused: an
       arbitrary mixed ordinary/monster set never engages.
    4. A damaging skill with no monster anchor is refused before any
       resource, roll, session, or clock access.
    5. Everything else settles through ``settle_out_of_combat_cast`` under
       ``context`` (default: the actor's room with no extra event context).
    """
    from world.rules.cast_settlement import settle_out_of_combat_cast

    targets = list(targets)
    if opening_target is not None and targets:
        return _rejected(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
    if opening_target is None and len(targets) == 1:
        if field_combat_target(actor, targets[0]) is not None:
            opening_target = targets[0]
            targets = []
    if opening_target is not None:
        return FieldCastOutcome(
            "initiation",
            combat_result=initiate_field_combat(
                actor, skill_key, opening_target, scale=scale
            ),
        )
    if any(field_combat_target(actor, target) is not None for target in targets):
        return _rejected(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
    skill = SKILL_REGISTRY.get(skill_key)
    if is_damaging(skill):
        # Covers a non-monster target AND no target at all: this fires
        # before the settlement API, so no resource, roll, session, or
        # clock access happens on any of these casts.
        return _rejected(RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET, skill_key)
    if context is None:
        context = RoomActionContext(actor.location, {})
    settlement = settle_out_of_combat_cast(
        ActionRequest(
            actor=actor,
            skill_key=skill_key,
            targets=targets,
            context=context,
            scale=scale,
        )
    )
    return FieldCastOutcome("settlement", settlement=settlement)


# ---------------------------------------------------------------------------
# Read-only preview.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldChoice:
    """One previewed confirmation choice (an ordinary target or an opening).

    ``entity`` is the candidate (or the anchor monster); ``line_up`` is the
    effective enemy line-up of an opening (empty for ordinary targets).
    ``reason``/``detail`` carry the first failing gate when disabled;
    ``session_reason`` names a candidate-battlefield failure instead.
    """

    entity: Any
    enabled: bool
    reason: RejectReason | None = None
    detail: str | None = None
    session_reason: str | None = None
    line_up: tuple[Any, ...] = ()


@dataclass(frozen=True)
class FieldSkillPreview:
    """A frozen read-only field-use preview of one owned active skill.

    ``verdict`` is the NONE/SELF confirmation verdict (``None`` for
    SINGLE/AREA). ``targets`` are ordinary explicit candidates (SELF: the
    actor alone; NONE: none); ``openings`` are living co-located monster
    anchors (SINGLE/AREA only). ``cost`` is the adjusted selected-scale cost.
    ``overflow`` is true when a list would exceed ``MAX_FIELD_CANDIDATES``;
    the lists are then empty rather than truncated.
    """

    skill: SkillDef
    scale: float
    cost: dict[str, int]
    verdict: FieldChoice | None
    targets: tuple[FieldChoice, ...]
    openings: tuple[FieldChoice, ...]
    overflow: bool = False


def field_candidate_entities(actor: Any) -> list[Any]:
    """Every co-located entity an ordinary field cast may name, by pk.

    The actor plus the visible co-located living entities that are not
    Monsters (any Monster is an opening anchor or nothing). The adapter's
    identity re-resolution uses this same set, so a preview never lists a
    target the cast would refuse to resolve and vice versa.
    """
    from typeclasses.entities import LivingEntity
    from typeclasses.monsters import Monster

    location = getattr(actor, "location", None)
    if location is None:
        return [actor]
    others = [
        obj
        for obj in location.contents
        if obj is not actor
        and isinstance(obj, LivingEntity)
        and not isinstance(obj, Monster)
    ]
    visible = list(location.filter_visible(others, actor))
    visible.sort(key=lambda obj: int(obj.pk))
    return [actor, *visible]


def field_opening_anchors(actor: Any) -> list[Any]:
    """Every living co-located Monster, in deterministic sorted-pk order.

    Exactly the set an AREA opening engages (``_room_monsters``), so an AREA
    disclosure can never omit a participant the initiation would add.
    """
    if getattr(actor, "location", None) is None:
        return []
    return _room_monsters(actor)


def owned_active_skill(actor: Any, skill_key: str) -> SkillDef | None:
    """The registered ACTIVE skill ``actor`` owns under ``skill_key``, else None."""
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None or skill.kind is not SkillKind.ACTIVE:
        return None
    try:
        owned = skill_key in actor.skills.owned_keys()
    except AttributeError:
        return None
    return skill if owned else None


def _verdict(entity: Any, preview: Any) -> FieldChoice:
    if preview.enabled:
        return FieldChoice(entity, True)
    return FieldChoice(entity, False, preview.reason, preview.detail)


def preview_field_skill(
    actor: Any,
    skill: SkillDef,
    scale: float = 1.0,
) -> FieldSkillPreview:
    """Preview every field confirmation of one owned active skill at ``scale``.

    Ordinary choices are judged under the actor's plain room context through
    ``revalidate_submission`` (single-member lists for SINGLE and AREA rows),
    with damaging skills refused exactly as :func:`cast_in_field` refuses
    them. Monster openings are judged by ``preview_field_opening`` against an
    unpersisted candidate battlefield. Missing effect context disables a
    choice; it is never fabricated.
    """
    location = getattr(actor, "location", None)
    context = RoomActionContext(location, {})
    damaging = is_damaging(skill)
    spec = skill.target_spec
    cost = adjusted_cost(actor, skill, scale)
    verdict: FieldChoice | None = None
    targets: list[FieldChoice] = []
    openings: list[FieldChoice] = []
    if spec in (TargetSpec.NONE, TargetSpec.SELF):
        if damaging:
            verdict = FieldChoice(
                actor, False, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET, skill.key
            )
        else:
            verdict = _verdict(
                actor, revalidate_submission(actor, skill.key, context, [], scale=scale)
            )
        if spec is TargetSpec.SELF:
            targets.append(
                FieldChoice(actor, verdict.enabled, verdict.reason, verdict.detail)
            )
        return FieldSkillPreview(skill, scale, cost, verdict, tuple(targets), ())

    candidates = field_candidate_entities(actor)
    if requirement_for(skill).forbid_self:
        candidates = [entity for entity in candidates if entity is not actor]
    anchors = field_opening_anchors(actor)
    if len(candidates) > MAX_FIELD_CANDIDATES or len(anchors) > MAX_FIELD_CANDIDATES:
        return FieldSkillPreview(skill, scale, cost, None, (), (), overflow=True)
    for entity in candidates:
        if damaging:
            targets.append(
                FieldChoice(
                    entity, False, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET, skill.key
                )
            )
            continue
        targets.append(
            _verdict(
                entity,
                revalidate_submission(actor, skill.key, context, [entity], scale=scale),
            )
        )
    # An AREA opening engages the same whole line-up whichever living monster
    # anchors it, so one candidate battlefield answers for every anchor.
    shared = None
    for monster in anchors:
        if spec is TargetSpec.AREA and shared is not None:
            opening = shared
        else:
            opening = preview_field_opening(actor, skill.key, monster, scale=scale)
            if spec is TargetSpec.AREA:
                shared = opening
        openings.append(
            FieldChoice(
                monster,
                opening.enabled,
                opening.reason,
                opening.detail,
                opening.session_reason,
                tuple(opening.targets) or (monster,),
            )
        )
    return FieldSkillPreview(skill, scale, cost, None, tuple(targets), tuple(openings))


__all__ = [
    "FieldCastOutcome",
    "FieldChoice",
    "FieldSkillPreview",
    "MAX_FIELD_CANDIDATES",
    "cast_in_field",
    "field_candidate_entities",
    "field_opening_anchors",
    "is_damaging",
    "owned_active_skill",
    "preview_field_skill",
]
