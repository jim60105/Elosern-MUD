"""Frozen read-only combat-session view models and one strict query.

Presentation (WebClient ``context_actions``) and the Telnet ``combat actions``
command serialize the same frozen view; neither reads raw ``.db.active_combat``
fields directly. The query strictly parses the persistent record, reconstructs
its battlefield, preserves ``player_ids`` then ``enemy_ids`` order, and returns
frozen session, participant, and active-skill descriptor values. It never
mutates traits, resources, buffs, sexual state, battlefield, session, quest,
location, or world time, and it never materializes a lazy buff or sexual
handler.

A validly parsed session whose participants cannot be reconstructed yields a
bounded recovery view carrying only the session summary and a confirmed Forfeit
entry; a malformed record is surfaced as an unavailable presentation by the
caller rather than being repaired here.
"""

from dataclasses import dataclass
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.rules.action_preview import preview_skill
from world.rules.combat import BattlefieldActionContext
from world.rules.combat_session import (
    CombatSessionError,
    read_session,
    reconstruct_battlefield,
)
from world.rules.player_messages import rejection_message
from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    freeform_scales_for,
    scaled_mp_cost,
)
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillKind

# Presentation bounds owned by the combat view (equal or below protocol limits).
MAX_PARTICIPANTS = 16
MAX_SKILLS = 32
MAX_SESSION_ID_CODE_POINTS = 128
MAX_DISPLAY_NAME_CODE_POINTS = 64
MAX_REASON_MESSAGE_CODE_POINTS = 512

# Stable root action keys in approved keyboard order.
ROOT_ACTIONS = ("attack", "skills", "items", "defend", "flee")
SECONDARY_ACTIONS = ("forfeit",)
RECOVERY_SECONDARY_ACTIONS = ("forfeit",)
BASIC_ATTACK_KEY = "basic_attack"

# Display labels for every presentation category, in the registry's fixed
# declaration order. Kept beside the category enum so both presenters share
# exactly one heading vocabulary.
CATEGORY_LABELS: dict[SkillCategory, str] = {
    SkillCategory.ELEMENTAL_MAGIC: "元素魔法",
    SkillCategory.MARTIAL_ARTS: "武技",
    SkillCategory.ENHANCEMENT: "強化",
    SkillCategory.INNATE_GIFT: "天賦",
    SkillCategory.MOVEMENT: "移動",
    SkillCategory.DIVINE_MYSTERY: "神之秘法",
    SkillCategory.UTILITY: "特殊",
    SkillCategory.SEXUAL_ACT: "性愛行為",
}


class CombatViewError(ValueError):
    """The active combat record cannot be read or reconstructed for viewing."""


@dataclass(frozen=True)
class ParticipantView:
    """One ordered combat participant with a stable session token.

    Attributes:
        identity: The positive opaque ObjectDB dbref.
        token: The session-local ``aN`` or ``eN`` token.
        display_name: The bounded display name.
        team: ``"party"`` or ``"foes"``.
        state: ``"active"``, ``"fled"``, ``"knocked_out"``, or ``"defeated"``.
        hp_current: The current true HP value.
        hp_maximum: The maximum true HP value.
        portrait_ref: The opaque art-catalog key for this participant while
            the participant is present in the ``webclient-art-panel`` portrait
            catalog, else ``None``.
    """

    identity: int
    token: str
    display_name: str
    team: str
    state: str
    hp_current: int
    hp_maximum: int
    portrait_ref: str | None


@dataclass(frozen=True)
class SkillDescriptorView:
    """One owned active skill with deterministic availability data.

    Attributes:
        key: The stable skill key.
        label: The registry label.
        description: The registry effect description.
        cost: The exact resource cost mapping.
        target_spec: The ``TargetSpec`` value.
        element: The nullable element key.
        category: The ``SkillCategory`` value.
        group: The optional second-level group key (an element key for
            ``elemental_magic``, a line name for ``sexual_act``).
        enabled: Whether the skill is currently usable.
        reason_code: Stable disabled reason code, or ``None`` when enabled.
        reason_message: Safe Traditional Chinese disabled explanation.
        valid_target_ids: Ordered participant IDs that pass the target checks.
        shorthands: Applicable approved AREA shorthands.
    """

    key: str
    label: str
    description: str
    cost: dict[str, int]
    target_spec: str
    element: str | None
    category: str
    group: str | None
    enabled: bool
    reason_code: str | None
    reason_message: str | None
    valid_target_ids: tuple[int, ...]
    shorthands: tuple[str, ...]
    freeform_scales: tuple[tuple[float, str, int], ...]


@dataclass(frozen=True)
class SkillGroupView:
    """One ordered sub-group of skill descriptors within a category.

    Attributes:
        group: The sub-group key (an element key or sexual-act line name),
            or ``None`` for categories that never carry a second level.
        label: The display label; ``None`` exactly when ``group`` is ``None``.
        skills: The ordered skill descriptors of this sub-group.
    """

    group: str | None
    label: str | None
    skills: tuple[SkillDescriptorView, ...]


@dataclass(frozen=True)
class CategoryGroupView:
    """One ordered category of skill sub-groups for presentation.

    Attributes:
        category: The ``SkillCategory`` value.
        label: The display label.
        groups: The ordered sub-groups; exactly one ``group=None`` sub-group
            for categories that never carry a second level.
    """

    category: str
    label: str
    groups: tuple[SkillGroupView, ...]


@dataclass(frozen=True)
class SessionView:
    """One bounded session summary for presentation.

    Attributes:
        session_id: The bounded stable session identifier.
        mode: ``hostile`` or ``guild_exam``.
        round: The non-negative elapsed round count.
        state: ``ready`` or ``recovery``.
        reason: A ``(code, message)`` reason for a recovery session, else ``None``.
    """

    session_id: str
    mode: str
    round: int
    state: str
    reason: tuple[str, str] | None


@dataclass(frozen=True)
class CombatView:
    """The complete frozen read-only combat presentation inputs."""

    session: SessionView
    participants: tuple[ParticipantView, ...]
    skills: tuple[SkillDescriptorView, ...]
    root_actions: tuple[str, ...]
    secondary_actions: tuple[str, ...]

    @property
    def recovery(self) -> bool:
        return self.session.state == "recovery"


def _stored_hp(entity: Any, key: str) -> int:
    from world.rules.action import _stored_trait_value

    trait = getattr(entity.traits, key)
    maximum = getattr(trait, "max", None)
    if maximum is None:
        maximum = getattr(trait, "max_value", None)
    if maximum is None:
        maximum = _stored_trait_value(trait)
    return max(int(_stored_trait_value(trait)), 0), max(int(maximum), 0)


def _participant_state(entity: Any, identity: int, record: Any) -> str:
    if identity in record.fled_ids:
        return "fled"
    if identity in record.knocked_out_ids:
        return "knocked_out"
    from world.rules.action import _stored_trait_value

    if _stored_trait_value(entity.traits.hp) <= 0:
        return "defeated"
    return "active"


def _bound(value: str, maximum: int, field: str) -> str:
    if sum(1 for _ in value) > maximum:
        raise CombatViewError(f"{field} exceeds {maximum} code points")
    return value


def combat_participants(actor: Any) -> tuple[int, ...]:
    """Return the ordered participant identities of the actor's active session.

    Reads the persisted ``player_ids`` then ``enemy_ids`` tuples and returns
    them in exactly that order, with no portrait or other presentation data.
    Both :func:`build_combat_view` and ``world.rules.art_view.build_art_view``
    consume this one roster query so the ``context_actions`` and ``art`` panels
    can never drift on participant membership or order. Raises
    :class:`CombatViewError` when there is no valid active session.
    """
    record = read_session(actor)
    if record is None:
        raise CombatViewError("no active combat session")
    return tuple((*record.player_ids, *record.enemy_ids))


def build_combat_view(actor: Any) -> CombatView:
    """Build the frozen combat view for ``actor`` or raise ``CombatViewError``.

    A missing record raises ``CombatViewError`` so the caller can choose
    unavailable presentation. A strictly parsed but unreconstructable session
    returns a recovery view instead: no cast or flee action, one confirmed
    Forfeit entry, and no participant or skill data.
    """
    record = read_session(actor)
    if record is None:
        raise CombatViewError("no active combat session")
    roster = combat_participants(actor)
    session_id = _bound(record.session_id, MAX_SESSION_ID_CODE_POINTS, "session_id")
    session = SessionView(
        session_id=session_id,
        mode=record.mode,
        round=record.rounds_elapsed,
        state="ready",
        reason=None,
    )
    try:
        battlefield = reconstruct_battlefield(actor, record)
    except CombatSessionError as error:
        reason_code = str(error.args[0])
        reason_message = rejection_message_from_session(reason_code)
        return CombatView(
            session=SessionView(
                session_id=session_id,
                mode=record.mode,
                round=record.rounds_elapsed,
                state="recovery",
                reason=(reason_code, reason_message),
            ),
            participants=(),
            skills=(),
            root_actions=(),
            secondary_actions=RECOVERY_SECONDARY_ACTIONS,
        )

    participants = _build_participants(actor, record, battlefield, roster)
    skills = _build_skills(actor, record, battlefield, participants)
    return CombatView(
        session=session,
        participants=participants,
        skills=skills,
        root_actions=ROOT_ACTIONS,
        secondary_actions=SECONDARY_ACTIONS,
    )


def _build_participants(
    actor: Any,
    record: Any,
    battlefield: Any,
    roster: tuple[int, ...],
) -> tuple[ParticipantView, ...]:
    def resolve(dbref: int):
        from evennia.objects.models import ObjectDB

        return ObjectDB.objects.filter(id=dbref).first()

    from world.rules.art_view import portrait_catalog_key

    participants: list[ParticipantView] = []
    for team, ids, prefix in (
        ("party", record.player_ids, "a"),
        ("foes", record.enemy_ids, "e"),
    ):
        for index, dbref in enumerate(ids, start=1):
            if int(dbref) not in roster:
                raise CombatViewError(f"participant {dbref} is absent from the roster")
            entity = resolve(dbref)
            if entity is None:
                raise CombatViewError(f"participant {dbref} is unreconstructable")
            current, maximum = _stored_hp(entity, "hp")
            participants.append(
                ParticipantView(
                    identity=int(dbref),
                    token=f"{prefix}{index}",
                    display_name=_bound(
                        str(entity.key), MAX_DISPLAY_NAME_CODE_POINTS, "display_name"
                    ),
                    team=team,
                    state=_participant_state(entity, int(dbref), record),
                    hp_current=current,
                    hp_maximum=maximum,
                    portrait_ref=portrait_catalog_key(int(dbref)),
                )
            )
    if not participants or len(participants) > MAX_PARTICIPANTS:
        raise CombatViewError("participant count is out of bounds")
    return tuple(participants)


def _freeform_scales_for_skill(actor: Any, skill: Any) -> tuple[tuple[float, str, int], ...]:
    """Return the actor's allowed scale entries for one eligible skill.

    Entries are strictly ascending ``(scale, label, mp_cost)`` where
    ``mp_cost`` is computed server-side with the shared rounding helper, so
    the browser never re-implements cost scaling. An ineligible skill or an
    actor without direct mastery ownership of the skill's element yields an
    empty tuple, so the panel can omit the field entirely (the freeform
    feature is invisible to non-masters).
    """
    if not is_freeform_eligible(skill) or skill.element is None:
        return ()
    allowed = frozenset(freeform_scales_for(actor, skill.element.key))
    if not allowed:
        return ()
    base_mp = int(skill.cost["mp"])
    return tuple(
        (scale, label, scaled_mp_cost(base_mp, scale))
        for scale, label in FREEFORM_CAST_SCALES
        if scale in allowed
    )


def _build_skills(
    actor: Any,
    record: Any,
    battlefield: Any,
    participants: tuple[ParticipantView, ...],
) -> tuple[SkillDescriptorView, ...]:
    context = BattlefieldActionContext(
        battlefield,
        event_context={"battlefield": battlefield},
    )
    from evennia.objects.models import ObjectDB

    candidate_entities: list[Any] = []
    for participant in participants:
        entity = ObjectDB.objects.filter(id=participant.identity).first()
        if entity is None:
            raise CombatViewError(
                f"participant {participant.identity} is unreconstructable"
            )
        candidate_entities.append(entity)

    seen: set[str] = set()
    descriptors: list[SkillDescriptorView] = []
    for key in actor.skills.owned_keys():
        if key in seen:
            continue
        seen.add(key)
        skill = SKILL_REGISTRY.get(key)
        if skill is None or skill.kind is not SkillKind.ACTIVE:
            continue
        if len(descriptors) >= MAX_SKILLS:
            raise CombatViewError("active-skill count exceeds presentation bounds")
        preview = preview_skill(actor, key, context, list(candidate_entities))
        element = skill.element.key if skill.element is not None else None
        valid_ids = tuple(
            participant.identity
            for participant in participants
            if any(
                getattr(target, "pk", None) == participant.identity
                for target in preview.valid_targets
            )
        )
        if preview.enabled:
            reason_code = None
            reason_message = None
        else:
            reason_code = preview.reason.value if preview.reason is not None else "unavailable"
            reason_message = rejection_message(preview.reason) if preview.reason is not None else "目前無法使用。"
        descriptors.append(
            SkillDescriptorView(
                key=key,
                label=skill.label,
                description=skill.description,
                cost=dict(skill.cost),
                target_spec=skill.target_spec.value,
                element=element,
                category=skill.category.value,
                group=skill.group,
                enabled=preview.enabled,
                reason_code=reason_code,
                reason_message=reason_message,
                valid_target_ids=valid_ids,
                shorthands=preview.shorthands,
                freeform_scales=_freeform_scales_for_skill(actor, skill),
            )
        )
    return tuple(descriptors)


def _element_label(element_key: str) -> str | None:
    """Return the display label for one element sub-group key."""
    element = ELEMENT_REGISTRY.get(element_key)
    return element.display_name_zh if element is not None else element_key


def group_skill_views(
    skills: tuple[SkillDescriptorView, ...],
) -> tuple[CategoryGroupView, ...]:
    """Group ordered skill descriptors into the categorized panel structure.

    Iterates ``SkillCategory`` in declaration order, so category order never
    depends on what the entity happens to own. Within ``elemental_magic``
    sub-groups follow ``ELEMENT_REGISTRY`` declaration order; within
    ``sexual_act`` sub-groups follow first-seen ``group`` order among the
    entity's owned skills; every other category emits exactly one
    ``group=None`` sub-group. A category or sub-group with zero owned skills
    is omitted entirely, not emitted empty. Skills keep their ``owned_keys()``
    order within every sub-group.
    """
    categories: list[CategoryGroupView] = []
    for category in SkillCategory:
        owned = tuple(
            skill for skill in skills if skill.category == category.value
        )
        if not owned:
            continue
        if category is SkillCategory.ELEMENTAL_MAGIC:
            sub_groups: list[SkillGroupView] = []
            for element_key in ELEMENT_REGISTRY:
                members = tuple(
                    skill for skill in owned if skill.group == element_key
                )
                if not members:
                    continue
                sub_groups.append(
                    SkillGroupView(
                        group=element_key,
                        label=_element_label(element_key),
                        skills=members,
                    )
                )
        elif category is SkillCategory.SEXUAL_ACT:
            # First-seen ``group`` order among the owned skills. A ``None``
            # group is its own bucket (``group=None``/``label=None``), so a
            # line-less act is still presented rather than silently dropped.
            sub_groups = []
            seen: set[str | None] = set()
            for skill in owned:
                group = skill.group
                if group in seen:
                    continue
                seen.add(group)
                members = tuple(
                    member for member in owned if member.group == group
                )
                sub_groups.append(
                    SkillGroupView(group=group, label=group, skills=members)
                )
        else:
            sub_groups = [SkillGroupView(group=None, label=None, skills=owned)]
        categories.append(
            CategoryGroupView(
                category=category.value,
                label=CATEGORY_LABELS[category],
                groups=tuple(sub_groups),
            )
        )
    return tuple(categories)


def rejection_message_from_session(reason_code: str) -> str:
    """Return a safe Traditional Chinese message for a session reason code."""
    from world.rules.player_messages import session_reason_message

    return session_reason_message(reason_code)


__all__ = [
    "BASIC_ATTACK_KEY",
    "CATEGORY_LABELS",
    "CategoryGroupView",
    "CombatView",
    "CombatViewError",
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_PARTICIPANTS",
    "MAX_REASON_MESSAGE_CODE_POINTS",
    "MAX_SESSION_ID_CODE_POINTS",
    "MAX_SKILLS",
    "ParticipantView",
    "RECOVERY_SECONDARY_ACTIONS",
    "ROOT_ACTIONS",
    "SECONDARY_ACTIONS",
    "SessionView",
    "SkillDescriptorView",
    "SkillGroupView",
    "build_combat_view",
    "combat_participants",
    "group_skill_views",
    "rejection_message_from_session",
]
