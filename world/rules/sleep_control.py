"""Authoritative sleep control view and the compensated all-party choice.

This module owns the read projection every transport renders while a
controlled body sleeps, plus the explicit all-party sleep operation. It never
settles time: the accepted receipt and the clock stay with
``world.rules.time_skip``/``world.rules.clock``.

The view is derived from committed state only: the authenticated owner behind
the controlled body, its verified possession mirrors, the controlled body's
posture, and the present effective companion roster in party order. A sleeping
owner with no possession additionally exposes the owner-only dream decision and
the retained same-sleep continuation state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.observability import log_error
from world.rules.fatigue import SleepPosture, read_optional_fatigue_state
from world.rules.party import is_companion, live_companions
from world.rules.party_scope import PartyScopeError, present_party_scope, resolve_commander
from world.rules.possession import (
    SLEEP_HANDOFF_POSSESS,
    SLEEP_HANDOFF_RETURN,
    PossessionGateError,
    PossessionWriteError,
    _account_characters,
    _account_possession_holder,
    _acting_sessions,
    _candidate_action_capable,
    _dialogue_open,
    _materialize_wilderness_location,
    _resolve_account,
    _restore_owner_control,
    _restore_owner_session,
    _session_controls_body,
    _sleep_posture_blocks,
    _snapshot_owner_control,
    confirm_sleep_handoff,
    current_possession,
    handoff_candidate_label,
    release_possession,
    restore_party_control,
    snapshot_party_control,
)
from world.rules.sleep_receipt import (
    CONTINUATION_COMPLETE,
    CONTINUATION_NONE,
    CONTINUATION_PAUSED,
    CONTINUATION_PENDING,
    DECISION_DECLINED,
    DECISION_ENTERED,
    SleepReceipt,
    read_sleep_view_decision,
    read_sleep_view_generation,
    read_sleep_receipt,
)
from world.rules.status_query.fatigue import build_fatigue_subject
from world.rules.status_query.models import StatusQueryError
from world.rules.time_skip import (
    MODE_RECOVERY,
    STALE_SLEEP_MESSAGE,
    SleepRefused,
    _party_member_eligible,
    _restore_sleep_surfaces,
    _sleep_surface_snapshot,
    enter_party_sleep,
    rejection_message,
)
from world.rules.skip_safety import evaluate_skip_safety

#: The exact final companion-list option required by the capability.
ALL_PARTY_SLEEP_LABEL = "全員一起睡眠"

#: The one player-facing question while the owner sleeps without possession.
SLEEP_DREAM_QUESTION = (
    "進入夢境協作？輸入 dream enter 進入，或 dream decline／sleep continue "
    "繼續睡眠。"
)

REASON_REMOTE = "不在同一地點"
REASON_ASLEEP = "沉睡中，無法行動"
REASON_CANNOT_ACT = "目前無法行動"
REASON_POSSESSED = "已被其他角色控制"
REASON_DIALOGUE = "正在交談"
REASON_OWNER_AWAKE = "主人已清醒"
REASON_NO_SLEEPER = "在場成員都已入睡或已完全恢復"
REASON_NOT_CONTROLLING = "目前未控制這個身體"
REASON_STALE = STALE_SLEEP_MESSAGE
REASON_NOT_OWNER = "只有甦醒的主人可以決定夢境"


@dataclass(frozen=True)
class SleepControlRow:
    """One contextual choice with its committed availability and reason."""

    kind: str
    identity: int
    name: str
    reserve_percent: int | None
    stage: str
    label: str
    enabled: bool
    reason: str | None


@dataclass(frozen=True)
class ControlledSleep:
    """The controlled body's own accepted receipt identity."""

    sleep_id: str
    revision: int


@dataclass(frozen=True)
class OwnerSleepView:
    """The released owner's dream question and retained continuation state."""

    sleep_id: str
    revision: int
    generation: int
    dream_pending: bool
    continuation: str
    continuation_available: bool
    continuation_reason: str | None


@dataclass(frozen=True)
class SleepControlView:
    """The authoritative contextual view of one sleeping controlled body."""

    owner_id: int
    controlled_body_id: int
    transition_id: str
    rows: tuple[SleepControlRow, ...]
    party_enabled: bool
    party_reason: str | None
    controlled_sleep: ControlledSleep | None
    owner_sleep: OwnerSleepView | None

    @property
    def selection_available(self) -> bool:
        return self.party_enabled or any(row.enabled for row in self.rows)


def _body_row(member: Any) -> tuple[str, int | None, str]:
    """Return ``(stage, reserve_percent, name)`` from the no-create projection."""
    try:
        subject = build_fatigue_subject(member)
    except StatusQueryError:  # observability: ignore R2: an unreadable body is still listed with an unknown reserve; eligibility is decided separately
        return "unknown", None, str(getattr(member, "key", "?"))
    return subject.stage, subject.reserve_percent, subject.name


def _row_reason(commander: Any, member: Any, *, current_body: Any) -> str | None:
    """The one stable reason a companion cannot be chosen, or ``None``."""
    if getattr(member, "_is_deleted", False):
        return REASON_CANNOT_ACT
    if getattr(member, "location", None) is not getattr(commander, "location", None):
        return REASON_REMOTE
    if _sleep_posture_blocks(member):
        return REASON_ASLEEP
    if not _candidate_action_capable(member):
        return REASON_CANNOT_ACT
    if getattr(getattr(member, "db", None), "possessed_by", None) is not None:
        return REASON_POSSESSED
    if member is not current_body and member is not commander and not is_companion(member, commander):
        return REASON_CANNOT_ACT
    if _dialogue_open(member, commander):
        return REASON_DIALOGUE
    return None


def _build_row(commander: Any, member: Any, kind: str, *, current_body: Any) -> SleepControlRow:
    stage, reserve, name = _body_row(member)
    enabled = _row_reason(commander, member, current_body=current_body) is None
    candidate = _LabelCandidate(
        identity=int(member.pk),
        name=name,
        kind=kind,
        reserve_percent=reserve,
    )
    reason = None if enabled else _row_reason(commander, member, current_body=current_body)
    return SleepControlRow(
        kind=kind,
        identity=int(member.pk),
        name=name,
        reserve_percent=reserve,
        stage=stage,
        label=handoff_candidate_label(candidate),
        enabled=enabled,
        reason=reason,
    )


class _LabelCandidate:
    """The minimal candidate shape the shared label renderer reads."""

    __slots__ = ("dbid", "name", "kind", "reserve_percent")

    def __init__(self, *, identity: int, name: str, kind: str, reserve_percent: int | None) -> None:
        self.dbid = identity
        self.name = name
        self.kind = kind
        self.reserve_percent = reserve_percent


def _party_status(commander: Any, *, actor: Any) -> tuple[bool, str | None]:
    """Whether the explicit all-party choice is currently available."""
    reason = evaluate_skip_safety(commander)
    if reason is not None:
        return False, rejection_message(reason) or "目前無法入睡。"
    if actor is not commander:
        binding = current_possession(commander)
        if (
            binding is None
            or int(binding.get("npc_dbid", 0)) != int(getattr(actor, "pk", 0))
            or getattr(getattr(actor, "db", None), "possessed_by", None)
            != getattr(commander, "pk", None)
        ):
            return False, REASON_NOT_CONTROLLING
    try:
        members = present_party_scope(commander)
    except PartyScopeError:  # observability: ignore R2: no party scope means no eligible party choice
        return False, REASON_NOT_CONTROLLING
    has_awake = False
    for member in members:
        if getattr(member, "_is_deleted", False):
            continue
        try:
            state = read_optional_fatigue_state(member)
        except Exception:  # observability: ignore R2: an unreadable body cannot be validated as an eligible sleeper; no state is written
            return False, REASON_CANNOT_ACT
        if state is None:
            return False, REASON_CANNOT_ACT
        if state.posture is SleepPosture.AWAKE:
            has_awake = True
            try:
                _party_member_eligible(member)
            except SleepRefused as error:
                return False, error.message
    if not has_awake:
        return False, REASON_NO_SLEEPER
    return True, None


def _transition_id(current_body: Any, binding: Any) -> str:
    """The stable sleep-control episode identity of the controlled body."""
    from world.rules.possession import _sleep_handoff_transition_id

    return _sleep_handoff_transition_id(current_body, binding)


def _owner_sleep_view(commander: Any, receipt: SleepReceipt) -> OwnerSleepView:
    generation = read_sleep_view_generation(commander)
    decision = read_sleep_view_decision(commander)
    answered = bool(
        decision is not None
        and decision["generation"] == generation
        and decision["sleep_id"] == receipt.sleep_id
    )
    continuation = decision["continuation"] if answered else CONTINUATION_NONE
    paused = continuation == CONTINUATION_PAUSED
    pending = continuation == CONTINUATION_PENDING
    reason = None
    if paused:
        reason = "睡眠因互動或安全邊界暫停；可繼續剩餘睡眠。"
    return OwnerSleepView(
        sleep_id=receipt.sleep_id,
        revision=receipt.revision,
        generation=generation,
        dream_pending=not answered,
        continuation=continuation,
        continuation_available=(
            receipt.sleeping and continuation != CONTINUATION_COMPLETE
        ),
        continuation_reason=reason,
    )


def build_sleep_control_view(
    actor: Any,
    *,
    account: Any = None,
    session: Any = None,
) -> SleepControlView | None:
    """Project the contextual sleep-control view, or ``None`` off-context.

    ``actor`` is the session's controlled body. The owner is resolved from the
    canonical commander boundary, never from ``actor.pk`` alone. A session,
    when supplied, must currently control that body. No state is written.
    """
    try:
        commander = resolve_commander(actor)
    except PartyScopeError:  # observability: ignore R2: a non-player body has no owner sleep view
        return None
    account = account if account is not None else _resolve_account(commander, actor)
    if account is None:
        return None
    holder = _account_possession_holder(account)
    if holder is not None and holder is not commander:
        return None
    if session is not None and not _session_controls_body(session, account, actor):
        return None
    binding = current_possession(commander)
    if actor is commander:
        if binding is not None or getattr(getattr(commander, "db", None), "possessed_by", None) is not None:
            return None
    else:
        if not is_companion(actor, commander):
            return None
        if (
            binding is None
            or int(binding.get("npc_dbid", 0)) != int(actor.pk)
            or getattr(getattr(actor, "db", None), "possessed_by", None)
            != int(commander.pk)
        ):
            return None
    if getattr(commander, "location", None) is None:
        return None
    if getattr(actor, "location", None) is not getattr(commander, "location", None):
        return None
    if not _sleep_posture_blocks(actor):
        return None

    rows: list[SleepControlRow] = []
    if actor is not commander:
        owner_reason = _row_reason(commander, commander, current_body=actor)
        stage, reserve, name = _body_row(commander)
        rows.append(
            SleepControlRow(
                kind=SLEEP_HANDOFF_RETURN,
                identity=int(commander.pk),
                name=name,
                reserve_percent=reserve,
                stage=stage,
                label=handoff_candidate_label(
                    _LabelCandidate(
                        identity=int(commander.pk),
                        name=name,
                        kind=SLEEP_HANDOFF_RETURN,
                        reserve_percent=reserve,
                    )
                ),
                enabled=owner_reason is None,
                reason=owner_reason,
            )
        )
    for member in live_companions(commander):
        if member is actor:
            continue
        rows.append(
            _build_row(commander, member, SLEEP_HANDOFF_POSSESS, current_body=actor)
        )
    party_enabled, party_reason = _party_status(commander, actor=actor)

    controlled_sleep = None
    try:
        own_receipt = read_sleep_receipt(actor)
    except Exception:  # observability: ignore R2: an unreadable receipt leaves the continuation row unavailable; no state is written
        own_receipt = None
    if own_receipt is not None and own_receipt.sleeping:
        controlled_sleep = ControlledSleep(own_receipt.sleep_id, own_receipt.revision)

    owner_sleep = None
    if actor is commander:
        try:
            owner_receipt = read_sleep_receipt(commander)
        except Exception:  # observability: ignore R2: an unreadable receipt opens no dream question; the continuation reports the stored fault
            owner_receipt = None
        if owner_receipt is not None and owner_receipt.sleeping:
            owner_sleep = _owner_sleep_view(commander, owner_receipt)

    return SleepControlView(
        owner_id=int(commander.pk),
        controlled_body_id=int(actor.pk),
        transition_id=_transition_id(actor, binding),
        rows=tuple(rows),
        party_enabled=party_enabled,
        party_reason=party_reason,
        controlled_sleep=controlled_sleep,
        owner_sleep=owner_sleep,
    )


def render_sleep_control_text(view: SleepControlView) -> str:
    """Render the same authoritative rows and decisions as the browser."""
    lines: list[str] = []
    for index, row in enumerate(view.rows, 1):
        if row.enabled:
            lines.append(f"{index}. {row.label}")
        else:
            lines.append(f"{index}. {row.label}（{row.reason}）")
    party_index = len(view.rows) + 1
    if view.party_enabled:
        lines.append(f"{party_index}. {ALL_PARTY_SLEEP_LABEL}")
    else:
        lines.append(f"{party_index}. {ALL_PARTY_SLEEP_LABEL}（{view.party_reason}）")
    lines.append("用法：handoff <編號>、handoff party、handoff cancel")
    if view.owner_sleep is not None and view.owner_sleep.dream_pending:
        lines.append(SLEEP_DREAM_QUESTION)
    elif (
        view.owner_sleep is not None
        and view.owner_sleep.continuation_available
    ):
        lines.append("sleep continue 可繼續剩餘睡眠。")
    return "\n".join(lines)


def _lock_control(
    account: Any, commander: Any, current_body: Any, members: tuple[Any, ...]
) -> None:
    ids = {int(commander.pk), int(current_body.pk)}
    ids.update(int(member.pk) for member in members)
    if account is not None:
        ids.update(int(char.pk) for char in _account_characters(account))
    list(
        ObjectDB.objects.select_for_update()
        .filter(id__in=sorted(ids))
        .order_by("id")
        .values_list("id", flat=True)
    )


def begin_all_party_sleep(
    actor: Any,
    *,
    mode: str = MODE_RECOVERY,
    seconds: int | None = None,
    session: Any = None,
) -> Any:
    """Enter every present effective member's sleep and release control.

    The controlled companion case releases through the verified possession
    writer inside one outer compensated transaction: any failure after the
    posture/receipt or control writes restores every member's physiology,
    receipt, projection and the exact prior control/session/bookkeeping
    surfaces. No time passes.
    """
    commander = resolve_commander(actor)
    account = _resolve_account(commander, actor)
    view = build_sleep_control_view(actor, account=account, session=session)
    if view is None or not view.party_enabled:
        raise SleepRefused(
            "party_unavailable", view.party_reason if view is not None else REASON_NOT_CONTROLLING
        )
    possessed = actor is not commander
    owner_sessions = tuple(_acting_sessions(actor)) if possessed else ()
    if possessed:
        try:
            _materialize_wilderness_location(commander)
        except Exception as error:
            raise PossessionWriteError("write_failed", str(error)) from error
    members = present_party_scope(commander)
    control_before = snapshot_party_control(commander, actor) if possessed else None
    owner_before = _snapshot_owner_control(commander) if possessed else None
    snapshots: dict[int, tuple[Any, dict[str, Any]]] = {}
    try:
        with transaction.atomic():
            _lock_control(account, commander, actor, members)
            locked = build_sleep_control_view(actor, account=account, session=session)
            if locked is None or not locked.party_enabled:
                raise SleepRefused(
                    "party_unavailable",
                    locked.party_reason if locked is not None else REASON_NOT_CONTROLLING,
                )
            if possessed:
                binding = current_possession(commander)
                if (
                    binding is None
                    or int(binding.get("npc_dbid", 0)) != int(actor.pk)
                    or getattr(getattr(actor, "db", None), "possessed_by", None)
                    != int(commander.pk)
                ):
                    raise PossessionGateError(REASON_NOT_CONTROLLING)
            touched = {id(commander): commander}
            for member in members:
                touched[id(member)] = member
            snapshots = {
                key: (member, _sleep_surface_snapshot(member))
                for key, member in touched.items()
            }
            outcome = enter_party_sleep(commander, mode=mode, seconds=seconds)
            if possessed:
                release_possession(commander, npc=actor, reason="sleep_handoff")
    except Exception as error:
        # The outer transaction rolled the durable writes back; the puppet,
        # cmdset, lock and location effects are not transactional.
        if possessed and control_before is not None:
            restore_party_control(commander, actor, control_before)
            if owner_before is not None:
                _restore_owner_control(commander, owner_before)
            _restore_owner_session(commander, account, owner_sessions)
        for member, member_snapshots in snapshots.values():
            _restore_sleep_surfaces(member, member_snapshots)
        if isinstance(error, (PossessionGateError, PossessionWriteError, SleepRefused)):
            raise
        log_error(
            "party_sleep_failed",
            context={
                "char": str(getattr(commander, "pk", "?")),
                "controlled": str(getattr(actor, "pk", "?")),
            },
            exc=error,
        )
        raise PossessionWriteError("write_failed", str(error)) from error
    return outcome


__all__ = [
    "ALL_PARTY_SLEEP_LABEL",
    "ControlledSleep",
    "OwnerSleepView",
    "REASON_ASLEEP",
    "REASON_CANNOT_ACT",
    "REASON_DIALOGUE",
    "REASON_NOT_CONTROLLING",
    "REASON_NOT_OWNER",
    "REASON_NO_SLEEPER",
    "REASON_OWNER_AWAKE",
    "REASON_POSSESSED",
    "REASON_REMOTE",
    "REASON_STALE",
    "SLEEP_DREAM_QUESTION",
    "SleepControlRow",
    "SleepControlView",
    "begin_all_party_sleep",
    "build_sleep_control_view",
    "render_sleep_control_text",
]
