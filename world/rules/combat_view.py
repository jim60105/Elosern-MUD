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

from world.rules.action_preview import preview_skill
from world.rules.combat import BattlefieldActionContext
from world.rules.combat_session import (
    CombatSessionError,
    read_session,
    reconstruct_battlefield,
)
from world.rules.player_messages import rejection_message
from world.skills.registry import SKILL_REGISTRY, SkillKind

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
        portrait_ref: Always ``None`` until the art panel change lands.
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
    enabled: bool
    reason_code: str | None
    reason_message: str | None
    valid_target_ids: tuple[int, ...]
    shorthands: tuple[str, ...]


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

    participants = _build_participants(actor, record, battlefield)
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
) -> tuple[ParticipantView, ...]:
    def resolve(dbref: int):
        from evennia.objects.models import ObjectDB

        return ObjectDB.objects.filter(id=dbref).first()

    participants: list[ParticipantView] = []
    for team, ids, prefix in (
        ("party", record.player_ids, "a"),
        ("foes", record.enemy_ids, "e"),
    ):
        for index, dbref in enumerate(ids, start=1):
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
                    portrait_ref=None,
                )
            )
    if not participants or len(participants) > MAX_PARTICIPANTS:
        raise CombatViewError("participant count is out of bounds")
    return tuple(participants)


def _build_skills(
    actor: Any,
    record: Any,
    battlefield: Any,
    participants: tuple[ParticipantView, ...],
) -> tuple[SkillDescriptorView, ...]:
    context = BattlefieldActionContext(
        battlefield,
        event_context={"battlefield": battlefield}
        if record.mode == "hostile"
        else {"battlefield": battlefield, "nonlethal": True},
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
                enabled=preview.enabled,
                reason_code=reason_code,
                reason_message=reason_message,
                valid_target_ids=valid_ids,
                shorthands=preview.shorthands,
            )
        )
    return tuple(descriptors)


def rejection_message_from_session(reason_code: str) -> str:
    """Return a safe Traditional Chinese message for a session reason code."""
    from world.rules.player_messages import session_reason_message

    return session_reason_message(reason_code)


__all__ = [
    "BASIC_ATTACK_KEY",
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
    "build_combat_view",
    "rejection_message_from_session",
]
