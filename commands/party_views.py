"""Player-facing member text views: ``狀態`` and ``技能``.

Both commands resolve their subject exactly as the party window does: an empty
argument names the commander, while an explicit token names the commander or
one of its effective companions (membership only; presence is not required).
They render the same read models the version-9 ``character`` panel publishes
and write nothing. Possession never changes the output: an empty argument
always describes the commander behind the possessed companion.
"""

from typing import Any

from commands.command import Command

from world.rules.lineage_query import (
    LineageQueryError,
    lineage_position_for,
    proficiency_progress_for_keys,
)
from world.rules.party_scope import (
    PartyScopeError,
    resolve_commander,
    resolve_member_token,
)
from world.rules.progression import freeform_ladder_for
from world.rules.status_query import (
    TRAIT_LABELS,
    StatusQueryError,
    build_character_read_model,
    group_skill_keys,
)
from world.rules.status_text import detailed_breakdown_text
from world.rules.unlock_notices import unlock_flags
from world.skills.registry import SKILL_REGISTRY

STATUS_UNAVAILABLE = "成員狀態暫時無法閱讀。"
SKILLS_UNAVAILABLE = "成員技能暫時無法閱讀。"
_DISGUISE_HEADING = "偽裝（顯示數值，非真實數值）："
_EMPTY_CONDITIONS = "狀態：無"
_EMPTY_SKILLS = "  （無）"


def _number_text(value: int | float) -> str:
    """Render a read-model value; an integer-looking float prints bare."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return format(value, "g")


def _member_name(member: Any) -> str:
    """The member's player-facing name: its plain authored key."""
    return str(member.key)


def _modifier_text(value: Any) -> str:
    """Render one condition modifier value verbatim, numbers bare."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    return _number_text(value)


def _conditions_text(model: Any) -> str:
    """Render the active condition rows: label, duration, modifiers, origin."""
    if not model.conditions:
        return _EMPTY_CONDITIONS
    lines = ["狀態："]
    for row in model.conditions:
        segments = [row.label]
        if row.remaining_seconds is None:
            segments.append("持續")
        else:
            segments.append(f"剩餘 {row.remaining_seconds} 秒")
        if row.modifiers:
            segments.append(
                "、".join(
                    f"{TRAIT_LABELS.get(key, key)} {_modifier_text(value)}"
                    for key, value in row.modifiers
                )
            )
        segments.append(f"來源：{row.source}")
        lines.append("  " + "｜".join(segments))
    return "\n".join(lines)


def member_status_text(member: Any) -> str:
    """Render one member's true status: traits, guild, conditions, disguise.

    Every trait row names its literal base, current/effective value and
    breakdown layers; a disguise is reported only in a separately labelled
    section, so its displayed values can never replace the true traits.
    """
    model = build_character_read_model(member)
    lines = [
        f"狀態：{_member_name(member)}",
        detailed_breakdown_text(model),
    ]
    if model.guild_rank is not None:
        lines.append(f"公會：階級 {model.guild_rank}｜功績 {model.guild_merit}")
    lines.append(_conditions_text(model))
    if model.disguise_active:
        lines.append(_DISGUISE_HEADING)
        if model.disguise_displayed:
            lines.extend(
                f"  {TRAIT_LABELS.get(key, key)}：{_number_text(value)}"
                for key, value in model.disguise_displayed
            )
        else:
            lines.append("  （無顯示數值）")
    return "\n".join(lines)


def _skill_band(row: Any, progress: Any) -> str:
    """The proficiency band or the capped mark for one active skill row."""
    fact = progress.get(row.key)
    if fact is None:
        return "（熟練 0/0）"
    if fact.capped:
        return "（見頂）"
    total = fact.xp_into_level + fact.xp_to_next_level
    return f"（熟練 {_number_text(fact.xp_into_level)}/{_number_text(total)}）"


def _active_skill_line(
    row: Any,
    progress: Any,
    recent: frozenset[str],
    booking: Any,
) -> str:
    """One active skill's identity, growth band and session marks."""
    fact = progress.get(row.key)
    level = 0 if fact is None else fact.level
    marks = ""
    if booking == row.key:
        marks += "［修煉中］"
    if row.key in recent:
        marks += "［新］"
    return f"{row.label} Lv.{level}{_skill_band(row, progress)}{marks}"


def _lineage_text(position: Any) -> list[str]:
    """The prerequisite and next-unlock lines of one lineage position."""
    lines: list[str] = []
    if position.prerequisites:
        lines.append(
            "        前置："
            + "、".join(
                f"{edge.display_name_zh} Lv.{edge.level}"
                for edge in position.prerequisites
            )
        )
    if position.next:
        lines.append(
            "        解鎖："
            + "、".join(
                f"{edge.display_name_zh} Lv.{edge.level}"
                for edge in position.next
            )
        )
    return lines


def _ladder_text(member: Any, skill: Any) -> str | None:
    """The freeform ladder line, or ``None`` when the member has no ladder."""
    rungs = freeform_ladder_for(member, skill)
    if not rungs:
        return None
    rendered = []
    for rung in rungs:
        if rung.mp_cost is not None:
            rendered.append(f"{rung.label} MP {rung.mp_cost}")
        else:
            rendered.append(f"{rung.label} 需 Lv.{rung.unlock_level}")
    return "        威力：" + " ‧ ".join(rendered)


def _active_skill_detail_lines(member: Any, row: Any) -> list[str]:
    """The lineage and freeform-ladder detail of one active skill row."""
    skill = SKILL_REGISTRY.get(row.key)
    if skill is None:
        return []
    lines = _lineage_text(lineage_position_for(member, row.key))
    ladder = _ladder_text(member, skill)
    if ladder is not None:
        lines.append(ladder)
    return lines


def _skill_section(
    heading: str,
    keys: tuple[str, ...],
    *,
    member: Any,
    active: bool,
    progress: Any = None,
    recent: frozenset[str] = frozenset(),
    booking: Any = None,
) -> list[str]:
    """One active/passive skill section grouped by category and sub-group."""
    lines = [heading]
    categories = group_skill_keys(keys)
    if not categories:
        lines.append(_EMPTY_SKILLS)
        return lines
    for category in categories:
        lines.append(f"  〔{category.label}〕")
        for group in category.groups:
            if group.label is not None:
                lines.append(f"    {group.label}")
            for row in group.skills:
                if active:
                    lines.append(
                        "      "
                        + _active_skill_line(row, progress, recent, booking)
                    )
                    lines.extend(_active_skill_detail_lines(member, row))
                else:
                    lines.append(f"      {row.label}")
    return lines


def skills_text(member: Any, recent: frozenset[str] = frozenset()) -> str:
    """Render one member's active and passive skills with their growth facts.

    Active rows carry the version-9 presenter's own facts: the proficiency
    level and XP band (or the capped mark), the standing practice booking, the
    session's recent-unlock mark, the declared prerequisite/next unlocks, and
    the freeform ladder while the member owns the element's mastery.
    """
    model = build_character_read_model(member)
    progress = proficiency_progress_for_keys(member, model.active_keys)
    booking = getattr(member.db, "practice_booking", None)
    lines = [f"技能：{_member_name(member)}"]
    lines.extend(
        _skill_section(
            "主動技能",
            model.active_keys,
            member=member,
            active=True,
            progress=progress,
            recent=recent,
            booking=booking,
        )
    )
    lines.extend(
        _skill_section(
            "被動技能",
            model.passive_keys,
            member=member,
            active=False,
        )
    )
    return "\n".join(lines)


def _session_recent(session: Any, member: Any) -> frozenset[str]:
    """This session's recent-unlock set for one member (empty when absent)."""
    if session is None or getattr(session, "ndb", None) is None:
        return frozenset()
    state = unlock_flags(session).get(int(member.pk))
    return frozenset() if state is None else state.recent


class _CmdMemberView(Command):
    """Shared subject resolution for the read-only member text views."""

    help_category = "General"
    unavailable = ""

    def _resolve_member(self) -> Any | None:
        token = self.args.strip()
        try:
            if token:
                return resolve_member_token(self.caller, token)
            return resolve_commander(self.caller)
        except PartyScopeError as error:
            self.caller.msg(error.message)
            return None


class CmdMemberStatus(_CmdMemberView):
    """Show a party member's true status, breakdown, conditions and disguise."""

    key = "狀態"
    aliases = ("status",)
    unavailable = STATUS_UNAVAILABLE

    def func(self) -> None:
        member = self._resolve_member()
        if member is None:
            return
        try:
            output = member_status_text(member)
        except (StatusQueryError, ValueError):
            self.caller.msg(self.unavailable)
            return
        self.caller.msg(output)


class CmdMemberSkills(_CmdMemberView):
    """Show a party member's skills, growth facts and freeform ladder."""

    key = "技能"
    aliases = ("skills",)
    unavailable = SKILLS_UNAVAILABLE

    def func(self) -> None:
        member = self._resolve_member()
        if member is None:
            return
        try:
            output = skills_text(
                member, recent=_session_recent(self.session, member)
            )
        except (StatusQueryError, LineageQueryError, ValueError):
            self.caller.msg(self.unavailable)
            return
        self.caller.msg(output)
