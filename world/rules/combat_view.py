"""Frozen read-only combat-session view models and one strict query.

Presentation (WebClient ``context_actions``) and the Telnet ``combat actions``
command serialize the same frozen view; neither reads raw ``.db.active_combat``
fields directly. The query strictly parses the persistent record, reconstructs
its battlefield, preserves ``player_ids`` then ``enemy_ids`` order, and returns
frozen session, participant, actor, choices, and draft view values. It never
mutates traits, resources, buffs, sexual state, battlefield, session, quest,
location, or world time, and it never materializes a lazy buff or sexual
handler.

A validly parsed session whose participants cannot be reconstructed yields a
bounded recovery view carrying only the session summary and a confirmed Forfeit
entry; a malformed record is surfaced as an unavailable presentation by the
caller rather than being repaired here.

Participant conditions (context_actions v6) reuse the status panel's read model
for each participant entity: the same codes, labels and severities in the same
order, cut to the first ``MAX_PARTICIPANT_CONDITIONS``.

Skill descriptors carry ``hostile``/``beneficial``: the static target-side
classification of ``world.skills.effects.polarity`` over the effects routed to
the chosen targets.
"""

from dataclasses import dataclass
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.rules.action_preview import adjusted_cost
from world.rules.action_preview import preview_skill
from world.rules.combat import BattlefieldActionContext
from world.rules.combat_session import (
    CombatSessionError,
    read_session,
    reconstruct_battlefield,
)
from world.rules.combat_session.battlefield import authorize_combat_actor
from world.rules.combat_session.rounds import (
    _eligible_taunt_target,
    preflight_draft_entries,
)
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.items import enumerate_actor_item_choices
from world.rules.player_messages import rejection_message, session_reason_message
from world.rules.progression import freeform_scale_entries_for
from world.rules.status_display import MissingDisplayMetadataError
from world.rules.status_query import StatusQueryError, build_status_read_model
from world.skills.effects.polarity import skill_target_polarity
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillKind

# Presentation bounds owned by the combat view (equal or below protocol limits).
MAX_PARTICIPANTS = 16
MAX_ACTORS = 5
MAX_ITEMS = 128
MAX_TACTICS = 3
MAX_SKILLS = 192
MAX_SESSION_ID_CODE_POINTS = 128
MAX_DISPLAY_NAME_CODE_POINTS = 64
MAX_REASON_MESSAGE_CODE_POINTS = 512
MAX_PARTICIPANT_CONDITIONS = 8
MAX_PARTICIPANT_CONDITION_LABEL = 128
MAX_ITEM_SUMMARY_CODE_POINTS = 512

# Stable action keys in approved keyboard order (v7).
ROOT_ACTIONS = ("attack", "skills", "items", "defend", "dodge", "taunt", "retreat")
SECONDARY_ACTIONS = ("surrender",)
RECOVERY_SECONDARY_ACTIONS = ("surrender",)
BASIC_ATTACK_KEY = "basic_attack"

CATEGORY_LABELS: dict[SkillCategory, str] = {
    SkillCategory.ELEMENTAL_MAGIC: "元素魔法",
    SkillCategory.MARTIAL_ARTS: "武技",
    SkillCategory.ENHANCEMENT: "強化",
    SkillCategory.DIVINE_MYSTERY: "神之秘法",
    SkillCategory.UTILITY: "特殊",
    SkillCategory.SEXUAL_ACT: "性愛行為",
    SkillCategory.HOLY_RITE: "神聖聖儀",
}


class CombatViewError(ValueError):
    """The active combat record cannot be read or reconstructed for viewing."""


@dataclass(frozen=True)
class ConditionRow:
    code: str
    label: str
    severity: str


@dataclass(frozen=True)
class ParticipantView:
    identity: int
    token: str
    display_name: str
    team: str
    state: str
    hp_current: int
    hp_maximum: int
    portrait_ref: str | None
    conditions: tuple[ConditionRow, ...]


@dataclass(frozen=True)
class SkillDescriptorView:
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
    hostile: bool
    beneficial: bool


@dataclass(frozen=True)
class SkillGroupView:
    group: str | None
    label: str | None
    skills: tuple[SkillDescriptorView, ...]


@dataclass(frozen=True)
class CategoryGroupView:
    category: str
    label: str
    groups: tuple[SkillGroupView, ...]


@dataclass(frozen=True)
class ItemDescriptorView:
    item_key: str
    label: str
    summary: str
    quantity: int
    enabled: bool
    reason: tuple[str, str] | None
    target_spec: str
    targets: tuple[int, ...]
    hostile: bool
    beneficial: bool


@dataclass(frozen=True)
class TacticDescriptorView:
    key: str
    label: str
    enabled: bool
    reason: tuple[str, str] | None
    targets: tuple[int, ...]


@dataclass(frozen=True)
class ActorSummaryView:
    identity: int
    commandable: bool
    reason: tuple[str, str] | None


@dataclass(frozen=True)
class ChoicesView:
    actor_id: int
    skills: tuple[CategoryGroupView, ...]
    items: tuple[ItemDescriptorView, ...]
    tactics: tuple[TacticDescriptorView, ...]


@dataclass(frozen=True)
class DraftEntryView:
    actor_id: int
    command: dict[str, Any]


@dataclass(frozen=True)
class ReselectionReasonView:
    actor_id: int
    reason: tuple[str, str]


@dataclass(frozen=True)
class DraftProgressView:
    round_revision: int
    draft_version: int
    required_actor_ids: tuple[int, ...]
    entries: tuple[DraftEntryView, ...]
    needs_selection_ids: tuple[int, ...]
    reselection_reasons: tuple[ReselectionReasonView, ...]


@dataclass(frozen=True)
class SessionView:
    session_id: str
    mode: str
    round: int
    round_revision: int
    state: str
    reason: tuple[str, str] | None


@dataclass(frozen=True)
class CombatView:
    session: SessionView
    participants: tuple[ParticipantView, ...]
    actors: tuple[ActorSummaryView, ...]
    choices: ChoicesView | None
    draft: DraftProgressView | None
    root_actions: tuple[str, ...]
    secondary_actions: tuple[str, ...]

    @property
    def recovery(self) -> bool:
        return self.session.state == "recovery"


def _stored_hp(entity: Any, key: str) -> tuple[int, int]:
    from world.rules.action import stored_gauge_pair

    return stored_gauge_pair(entity, key)


def _participant_state(entity: Any, identity: int, record: Any) -> str:
    if identity in record.fled_ids:
        return "fled"
    if identity in record.knocked_out_ids:
        return "knocked_out"
    from world.rules.action import _stored_trait_value

    if _stored_trait_value(entity.traits.hp) <= 0:
        return "defeated"
    return "active"


def participant_conditions(entity: Any) -> tuple[ConditionRow, ...]:
    try:
        model = build_status_read_model(entity)
    except (StatusQueryError, MissingDisplayMetadataError):
        return ()
    rows = tuple(
        ConditionRow(code=row.code, label=row.label, severity=row.severity)
        for row in model.conditions[:MAX_PARTICIPANT_CONDITIONS]
    )
    if any(
        sum(1 for _ in row.label) > MAX_PARTICIPANT_CONDITION_LABEL for row in rows
    ):
        return ()
    return rows


def _bound(value: str, maximum: int, field: str) -> str:
    if sum(1 for _ in value) > maximum:
        raise CombatViewError(f"{field} exceeds {maximum} code points")
    return value


def combat_participants(actor: Any) -> tuple[int, ...]:
    record = read_session(actor)
    if record is None:
        raise CombatViewError("no active combat session")
    return tuple((*record.player_ids, *record.enemy_ids))


def rejection_message_from_session(reason_code: str) -> str:
    return session_reason_message(reason_code)


def _reselection_reason_pair(raw_reason: Any) -> tuple[str, str]:
    if isinstance(raw_reason, dict):
        code = str(raw_reason.get("reason", "unknown"))
    elif hasattr(raw_reason, "value"):
        code = str(raw_reason.value)
    else:
        code = str(raw_reason)
    msg = session_reason_message(code)
    return (code, msg)


def _wire_draft_command(entry: Any) -> dict[str, Any]:
    """Normalize one stored draft entry into the closed v7 wire command union.

    The persisted draft keeps the internal ``{"kind", "payload"}`` shape whose
    skill payload uses ``targets_or_shorthand`` and whose tactical payload uses
    ``tactical_key``. The panel publishes one canonical spelling per kind
    instead: ``skill`` carries ``skill_key`` plus at most one of
    ``target_ids``/``target_shorthand`` and an optional ``scale``; ``item``
    carries ``item_key`` and an optional ``target_id``; ``tactical`` carries
    ``key`` and an optional ``target_id``.
    """
    if not isinstance(entry, dict):
        raise CombatViewError("draft entry is not a mapping")
    kind = entry.get("kind")
    payload = entry.get("payload") or {}
    if not isinstance(payload, dict):
        raise CombatViewError("draft entry payload is not a mapping")
    if kind == "skill":
        command: dict[str, Any] = {"skill_key": payload.get("skill_key")}
        targets_or_shorthand = payload.get("targets_or_shorthand")
        if isinstance(targets_or_shorthand, str):
            command["target_shorthand"] = targets_or_shorthand
        elif targets_or_shorthand:
            # An empty stored target list is the rules layer's input for a
            # NONE/SELF skill: the wire carries no target field at all.
            command["target_ids"] = [int(target) for target in targets_or_shorthand]
        if payload.get("scale") is not None:
            command["scale"] = float(payload["scale"])
        return {"kind": "skill", "payload": command}
    if kind == "item":
        item_command: dict[str, Any] = {"item_key": payload.get("item_key")}
        if payload.get("target_id") is not None:
            item_command["target_id"] = int(payload["target_id"])
        return {"kind": "item", "payload": item_command}
    if kind == "tactical":
        tactical_command: dict[str, Any] = {"key": payload.get("tactical_key")}
        if payload.get("target_id") is not None:
            tactical_command["target_id"] = int(payload["target_id"])
        return {"kind": "tactical", "payload": tactical_command}
    raise CombatViewError(f"unknown draft command kind {kind!r}")


def _build_actors(
    commander: Any, record: Any, battlefield: Any
) -> tuple[ActorSummaryView, ...]:
    from evennia.objects.models import ObjectDB

    actors: list[ActorSummaryView] = []
    for pid in record.player_ids:
        entity = ObjectDB.objects.filter(id=pid).first()
        if entity is None:
            continue
        try:
            authorize_combat_actor(commander, entity, record, battlefield)
            actors.append(ActorSummaryView(identity=pid, commandable=True, reason=None))
        except CombatSessionError as err:
            code = str(err.args[0]) if err.args else "forbidden_actor"
            msg = rejection_message_from_session(code)
            actors.append(
                ActorSummaryView(
                    identity=pid,
                    commandable=False,
                    reason=(code, msg),
                )
            )
    if len(actors) > MAX_ACTORS:
        raise CombatViewError(f"actors list exceeds {MAX_ACTORS}")
    return tuple(actors)


def _build_items(
    target_actor: Any,
    battlefield: Any,
    candidate_entities: list[Any] | None = None,
    in_combat: bool = True,
) -> tuple[ItemDescriptorView, ...]:
    from world.rules.service_messages import rejection_message as item_rejection_message

    context = BattlefieldActionContext(
        battlefield, event_context={"battlefield": battlefield}
    )
    choices = enumerate_actor_item_choices(
        target_actor,
        context,
        candidate_entities=list(candidate_entities or ()),
        in_combat=in_combat,
    )
    if len(choices) > MAX_ITEMS:
        raise CombatViewError(f"actor item choices {len(choices)} exceeds {MAX_ITEMS}")

    descriptors: list[ItemDescriptorView] = []
    for choice in choices:
        definition = ITEM_REGISTRY.get(choice.item_key)
        summary = (
            definition.presentation.summary_zh
            if definition and definition.presentation
            else ""
        )
        if sum(1 for _ in summary) > MAX_ITEM_SUMMARY_CODE_POINTS:
            summary = summary[:MAX_ITEM_SUMMARY_CODE_POINTS]

        reason_pair = None
        if not choice.enabled and choice.reason is not None:
            code = choice.reason.value
            msg = item_rejection_message(choice.reason)
            reason_pair = (code, msg)

        target_ids = tuple(
            int(t.pk) for t in choice.valid_targets if hasattr(t, "pk")
        )

        descriptors.append(
            ItemDescriptorView(
                item_key=choice.item_key,
                label=choice.label,
                summary=summary,
                quantity=choice.quantity,
                enabled=choice.enabled,
                reason=reason_pair,
                target_spec=choice.target_spec,
                targets=target_ids,
                hostile=choice.hostile,
                beneficial=choice.beneficial,
            )
        )
    return tuple(descriptors)


def _build_tactics(
    target_actor: Any, record: Any, battlefield: Any
) -> tuple[TacticDescriptorView, ...]:
    tactics: list[TacticDescriptorView] = []
    # Defend
    tactics.append(
        TacticDescriptorView(
            key="defend",
            label="防禦",
            enabled=True,
            reason=None,
            targets=(),
        )
    )
    # Dodge
    tactics.append(
        TacticDescriptorView(
            key="dodge",
            label="閃避",
            enabled=True,
            reason=None,
            targets=(),
        )
    )
    # Taunt
    eligible_enemy_ids = tuple(
        eid
        for eid in record.enemy_ids
        if _eligible_taunt_target(battlefield, record, eid) is not None
    )
    taunt_enabled = len(eligible_enemy_ids) > 0
    taunt_reason = (
        None
        if taunt_enabled
        else ("target_invalid", session_reason_message("target_invalid"))
    )
    tactics.append(
        TacticDescriptorView(
            key="taunt",
            label="嘲諷",
            enabled=taunt_enabled,
            reason=taunt_reason,
            targets=eligible_enemy_ids,
        )
    )
    return tuple(tactics)


def build_combat_view(actor: Any, *, for_actor: Any | None = None) -> CombatView:
    record = read_session(actor)
    if record is None:
        raise CombatViewError("no active combat session")
    roster = combat_participants(actor)
    session_id = _bound(record.session_id, MAX_SESSION_ID_CODE_POINTS, "session_id")

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
                round_revision=record.round_revision,
                state="recovery",
                reason=(reason_code, reason_message),
            ),
            participants=(),
            actors=(),
            choices=None,
            draft=None,
            root_actions=(),
            secondary_actions=RECOVERY_SECONDARY_ACTIONS,
        )

    actors = _build_actors(actor, record, battlefield)
    preflight = preflight_draft_entries(actor, record, battlefield)
    required_actor_ids = tuple(preflight["required_actors"])
    valid_entries = preflight["valid_entries"]
    needs_selection_ids = tuple(preflight["missing_actors"])

    reselection_reasons_list: list[ReselectionReasonView] = []
    for aid, r_info in preflight.get("reselection_reasons", {}).items():
        reselection_reasons_list.append(
            ReselectionReasonView(
                actor_id=aid,
                reason=_reselection_reason_pair(r_info),
            )
        )

    entries_list: list[DraftEntryView] = []
    for aid, entry in valid_entries.items():
        entries_list.append(DraftEntryView(actor_id=aid, command=_wire_draft_command(entry)))
    if len(entries_list) > MAX_ACTORS:
        raise CombatViewError(f"draft entries exceed {MAX_ACTORS}")
    if len(reselection_reasons_list) > MAX_ACTORS:
        raise CombatViewError(f"reselection reasons exceed {MAX_ACTORS}")

    draft = DraftProgressView(
        round_revision=record.round_revision,
        draft_version=record.draft_version,
        required_actor_ids=required_actor_ids,
        entries=tuple(entries_list),
        needs_selection_ids=needs_selection_ids,
        reselection_reasons=tuple(reselection_reasons_list),
    )

    # Determine requested actor
    if for_actor is not None:
        target_actor = for_actor
    elif needs_selection_ids:
        from evennia.objects.models import ObjectDB

        first_id = needs_selection_ids[0]
        target_actor = ObjectDB.objects.filter(id=first_id).first() or actor
    else:
        target_actor = actor

    try:
        authorize_combat_actor(actor, target_actor, record, battlefield)
        is_commandable = True
    except CombatSessionError as err:
        if for_actor is not None:
            raise CombatViewError(f"unauthorized actor: {err}") from err
        is_commandable = False

    participants = _build_participants(actor, record, battlefield, roster)

    if is_commandable:
        skill_descriptors = _build_skills(target_actor, record, battlefield, participants)
        skill_groups = group_skill_views(skill_descriptors)
        items = _build_items(
            target_actor, battlefield, _participant_entities(participants)
        )
        tactics = _build_tactics(target_actor, record, battlefield)
    else:
        skill_groups = ()
        items = ()
        tactics = ()

    choices = ChoicesView(
        actor_id=int(target_actor.pk),
        skills=skill_groups,
        items=items,
        tactics=tactics,
    )

    session = SessionView(
        session_id=session_id,
        mode=record.mode,
        round=record.rounds_elapsed,
        round_revision=record.round_revision,
        state="ready",
        reason=None,
    )

    return CombatView(
        session=session,
        participants=participants,
        actors=actors,
        choices=choices,
        draft=draft,
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
                    conditions=participant_conditions(entity),
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
        event_context={"battlefield": battlefield},
    )
    candidate_entities = _participant_entities(participants)

    seen: set[str] = set()
    descriptors: list[SkillDescriptorView] = []
    for key in actor.skills.owned_keys():
        if key in seen:
            continue
        seen.add(key)
        skill = SKILL_REGISTRY.get(key)
        if skill is None or skill.kind is not SkillKind.ACTIVE:
            continue
        if key == FLEE_SKILL_KEY:
            continue
        element = skill.element.key if skill.element is not None else None
        preview = preview_skill(actor, key, context, candidate_entities)
        valid_ids = tuple(
            int(target.pk)
            for target in preview.valid_targets
            if any(
                p.identity == int(target.pk) and p.state == "active"
                for p in participants
            )
        )
        if preview.enabled:
            reason_code = None
            reason_message = None
        else:
            reason_code = (
                preview.reason.value if preview.reason is not None else "unavailable"
            )
            reason_message = (
                rejection_message(preview.reason)
                if preview.reason is not None
                else "目前無法使用。"
            )
        hostile, beneficial = skill_target_polarity(skill)
        descriptors.append(
            SkillDescriptorView(
                key=key,
                label=skill.label,
                description=skill.description,
                cost=adjusted_cost(actor, skill),
                target_spec=skill.target_spec.value,
                element=element,
                category=skill.category.value,
                group=skill.group,
                enabled=preview.enabled,
                reason_code=reason_code,
                reason_message=reason_message,
                valid_target_ids=valid_ids,
                shorthands=preview.shorthands,
                freeform_scales=freeform_scale_entries_for(actor, skill),
                hostile=hostile,
                beneficial=beneficial,
            )
        )
    return tuple(descriptors)


def _element_label(element_key: str) -> str | None:
    element = ELEMENT_REGISTRY.get(element_key)
    return element.display_name_zh if element is not None else element_key


def _participant_entities(participants: tuple[ParticipantView, ...]) -> list[Any]:
    """Resolve every presented participant to its live entity, or fail closed."""
    from evennia.objects.models import ObjectDB

    entities: list[Any] = []
    for participant in participants:
        entity = ObjectDB.objects.filter(id=participant.identity).first()
        if entity is None:
            raise CombatViewError(
                f"participant {participant.identity} is unreconstructable"
            )
        entities.append(entity)
    return entities


def group_skill_views(
    skills: tuple[SkillDescriptorView, ...],
) -> tuple[CategoryGroupView, ...]:
    categories: list[CategoryGroupView] = []
    for category in SkillCategory:
        owned = tuple(skill for skill in skills if skill.category == category.value)
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
        elif category is SkillCategory.ENHANCEMENT:
            sub_groups = []
            for group_key in (None, "天賦", "身法"):
                members = tuple(
                    skill for skill in owned if skill.group == group_key
                )
                if not members:
                    continue
                sub_groups.append(
                    SkillGroupView(
                        group=group_key,
                        label=group_key,
                        skills=members,
                    )
                )
        elif category is SkillCategory.SEXUAL_ACT:
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
        elif category is SkillCategory.HOLY_RITE:
            sub_groups = []
            for group_key in (None, "聖禮"):
                members = tuple(
                    skill for skill in owned if skill.group == group_key
                )
                if not members:
                    continue
                sub_groups.append(
                    SkillGroupView(
                        group=group_key,
                        label=group_key,
                        skills=members,
                    )
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


__all__ = [
    "BASIC_ATTACK_KEY",
    "CATEGORY_LABELS",
    "ActorSummaryView",
    "CategoryGroupView",
    "ChoicesView",
    "CombatView",
    "CombatViewError",
    "ConditionRow",
    "DraftEntryView",
    "DraftProgressView",
    "ItemDescriptorView",
    "MAX_ACTORS",
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_ITEMS",
    "MAX_ITEM_SUMMARY_CODE_POINTS",
    "MAX_PARTICIPANT_CONDITION_LABEL",
    "MAX_PARTICIPANT_CONDITIONS",
    "MAX_PARTICIPANTS",
    "MAX_REASON_MESSAGE_CODE_POINTS",
    "MAX_SESSION_ID_CODE_POINTS",
    "MAX_SKILLS",
    "MAX_TACTICS",
    "ParticipantView",
    "RECOVERY_SECONDARY_ACTIONS",
    "ReselectionReasonView",
    "ROOT_ACTIONS",
    "SECONDARY_ACTIONS",
    "SessionView",
    "SkillDescriptorView",
    "SkillGroupView",
    "TacticDescriptorView",
    "build_combat_view",
    "combat_participants",
    "group_skill_views",
    "participant_conditions",
    "rejection_message_from_session",
]
