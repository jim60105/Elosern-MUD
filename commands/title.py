"""Player-facing ``title`` command: browse the title冊, swap slots, answer ballots.

``title list`` shows the current composed full title, every guild fixed-title
row (banked rows marked, locked rows carrying their authored ``hint_zh``),
every banked epithet, and — when one is pending — the numbered epithet
nomination ballot (change G). ``title codex`` (change H) renders the full
codex view — the fixed/epithet blocks with the server-computed removal flags
and the 「提名中」 section — from the same pure read model as the OOB panel.
``title equip fixed`` and ``title equip epithet`` swap one occupied slot for
another (D8): both slots always hold a value once the 冊 is non-empty, there
is no unequip surface, and an unknown, unbanked, or wrong-kind display fails
with one stable rejection that never enumerates candidates or hints at what
the player is missing. ``title accept <1|2|3>`` and ``title decline`` answer
the pending 異名提名投票 with the numbered choice only (ballots are never
answered with free text); out-of-range and no-ballot answers reply with
stable reasons and change nothing. ``title remove epithet <異名>`` echoes the
removal review (display + basis) and the matching
``title remove epithet <異名> confirm`` executes the two-gated, irreversible
deletion; the gates answer with their own stable lines and never enter the
confirm flow, and any other continuation after the echo cancels statelessly
(a bare ``title remove fixed …`` is plain usage — fixed titles have no
delete surface). Malformed stored title state presents the same fixed
unavailable line and changes nothing.
"""

from commands.command import Command

from world.lore.titles import FIXED_TITLE_REGISTRY
from world.rules.event_log import render_plain_text
from world.rules.title_view import build_title_codex_view
from world.rules.titles import (
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    TitleRemovalError,
    TitleRemovalReason,
    accept_epithet,
    banked_fixed_keys,
    banked_epithets,
    compose_full_title,
    decline_epithet_ballot,
    equip_epithet,
    equip_fixed,
    epithet_removal_gate,
    remove_epithet,
    safe_pending_ballot,
)

_USAGE = (
    "語法：title list | title codex | title equip fixed <稱號> | title equip epithet <異名> "
    "| title accept <1|2|3> | title decline | title remove epithet <異名> [confirm]"
)
_UNAVAILABLE = "你的稱號冊暫時無法閱讀。"
_REJECTED = "無法掛上該稱號。"
_NO_BALLOT = "目前沒有待決的異名提名。"
_BAD_INDEX = "沒有這個編號的提名。"
_REMOVE_UNKNOWN = "無法移除該異名。"
_REMOVE_LAST = "至少需保留一個異名。"
_REMOVE_EQUIPPED = "裝備中的異名無法移除，請先改掛其他異名。"
_BANKED_MARK = "●"
_LOCKED_MARK = "○"
_EQUIPPED_MARK = "★"
_REMOVABLE_MARK = "（可移除）"
_CONFIRM_TOKEN = "confirm"
# Stable gate lines keyed by reason; a gated target never enters the confirm
# flow, so these answer in place of the review echo.
_REMOVAL_GATE_LINES = {
    TitleRemovalReason.TARGET_UNKNOWN: _REMOVE_UNKNOWN,
    TitleRemovalReason.LAST_EPITHET: _REMOVE_LAST,
    TitleRemovalReason.EQUIPPED_UNREMOVABLE: _REMOVE_EQUIPPED,
}


class CmdTitle(Command):
    """Browse the title冊, swap slots, answer ballots, remove epithets."""

    key = "title"
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split()
        if not parts:
            self.caller.msg(_USAGE)
            return
        verb = parts[0].lower()
        if verb == "list" and len(parts) == 1:
            self._list()
            return
        if verb == "codex" and len(parts) == 1:
            self._codex()
            return
        if verb == "accept" and len(parts) <= 2:
            self._accept(parts[1].strip() if len(parts) > 1 else "")
            return
        if verb == "decline" and len(parts) == 1:
            self._decline()
            return
        if verb == "equip" and len(parts) > 2:
            kind = parts[1].lower()
            name = " ".join(parts[2:]).strip()
            if kind == "fixed":
                self._equip_fixed(name)
                return
            if kind == "epithet":
                self._equip_epithet(name)
                return
        if verb == "remove" and len(parts) > 2 and parts[1].lower() == "epithet":
            # Grammar: a literal trailing ``confirm`` token confirms; a
            # display whose tail would eat that token is echoed quoted (the
            # parse strips one matching pair). Bare ``remove fixed …`` never
            # matches — fixed titles have no delete surface at all.
            tail = parts[2:]
            confirmed = len(tail) > 1 and tail[-1].lower() == _CONFIRM_TOKEN
            if confirmed:
                tail = tail[:-1]
            self._remove_epithet(" ".join(tail), confirmed=confirmed)
            return
        self.caller.msg(_USAGE)

    def _list(self) -> None:
        try:
            full_title = compose_full_title(self.caller)
            fixed_keys = banked_fixed_keys(self.caller)
            epithets = banked_epithets(self.caller)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
            return
        lines = ["── 稱號冊 ──", f"當前全銜：{full_title}", "◆ 稱號"]
        for entry in FIXED_TITLE_REGISTRY.values():
            mark = _BANKED_MARK if entry.key in fixed_keys else _LOCKED_MARK
            suffix = "" if entry.key in fixed_keys else f"（{entry.hint_zh}）"
            lines.append(f"　{mark} {entry.display_name_zh}{suffix}")
        lines.append("◆ 異名")
        if epithets:
            lines.extend(f"　{_BANKED_MARK} {entry['display']}" for entry in epithets)
        else:
            lines.append("　（尚未取得）")
        ballot = safe_pending_ballot(self.caller)
        if ballot:
            lines.append("◆ 異名提名（待決）")
            lines.extend(_ballot_line(index, entry) for index, entry in enumerate(ballot, start=1))
            lines.append("　以 title accept <編號> 採納，或 title decline 放棄。")
        self.caller.msg("\n".join(lines))

    def _codex(self) -> None:
        """Render the full codex from the same pure view as the OOB panel."""
        try:
            view = build_title_codex_view(self.caller)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
            return
        lines = [
            "── 稱號冊 ──",
            f"當前全銜：{view.full_title}",
            f"已解鎖 {view.unlocked} / {view.total}",
            "◆ 稱號",
        ]
        for row in view.fixed_rows:
            mark = _BANKED_MARK if row.unlocked else _LOCKED_MARK
            suffix = "" if row.unlocked else f"（{row.hint}）"
            lines.append(f"　{mark} {row.display}{suffix}")
        lines.append("◆ 異名")
        if view.epithet_rows:
            for row in view.epithet_rows:
                mark = _EQUIPPED_MARK if row.equipped else _BANKED_MARK
                suffix = _REMOVABLE_MARK if row.can_remove else ""
                lines.append(f"　{mark} {row.display}{suffix}")
                lines.append(f"　　─ {row.basis}")
        else:
            lines.append("　（尚未取得）")
        if view.pending_ballot:
            lines.append("◆ 異名提名（待決）")
            lines.extend(
                _ballot_line(index, entry)
                for index, entry in enumerate(view.pending_ballot, start=1)
            )
            lines.append("　以 title accept <編號> 採納，或 title decline 放棄。")
        self.caller.msg("\n".join(lines))

    def _equip_fixed(self, name: str) -> None:
        if not name:
            self.caller.msg(_USAGE)
            return
        try:
            fixed_display = equip_fixed(self.caller, name)
        except TitleEquipError:
            self.caller.msg(_REJECTED)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
        else:
            self.caller.msg(f"你掛上稱號：{fixed_display}")

    def _equip_epithet(self, name: str) -> None:
        if not name:
            self.caller.msg(_USAGE)
            return
        try:
            epithet = equip_epithet(self.caller, name)
        except TitleEquipError:
            self.caller.msg(_REJECTED)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
        else:
            self.caller.msg(f"你掛上異名：{epithet}")

    def _remove_epithet(self, name: str, *, confirmed: bool) -> None:
        """Two-step epithet removal: echo review, then literal ``confirm``.

        The gate answers BEFORE any review exists (a gated target never sees
        the confirm flow); the confirming call re-validates the same gates
        inside ``remove_epithet`` itself. No review state is stored anywhere,
        so any other continuation trivially cancels byte-identically.
        """
        display = _strip_wrapping_quotes(name.strip())
        if not display:
            self.caller.msg(_USAGE)
            return
        if confirmed:
            try:
                event_log = remove_epithet(self.caller, display)
            except TitleRemovalError as error:
                self.caller.msg(_REMOVAL_GATE_LINES[error.reason])
            except TitleDataError:
                self.caller.msg(_UNAVAILABLE)
            else:
                self.caller.msg(render_plain_text(event_log))
            return
        try:
            reason = epithet_removal_gate(self.caller, display)
            basis = next(
                (
                    entry["origin_quote"]
                    for entry in banked_epithets(self.caller)
                    if entry["display"] == display
                ),
                "",
            )
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
            return
        if reason is not None:
            self.caller.msg(_REMOVAL_GATE_LINES[reason])
            return
        lines = [
            "── 異名移除確認 ──",
            f"　{_BANKED_MARK} {display}",
            f"　　─ {basis}",
            "　此操作不可恢復。",
            "　確認請輸入："
            f"title remove epithet {_quote_for_confirm(display)} {_CONFIRM_TOKEN}",
            "　輸入其他任何內容即取消此次移除（本次輸入不造成任何改變）。",
        ]
        self.caller.msg("\n".join(lines))

    def _accept(self, raw: str) -> None:
        if not raw:
            self._show_ballot()
            return
        try:
            index = int(raw)
        except ValueError:
            self.caller.msg(_BAD_INDEX)
            return
        try:
            display, banked = accept_epithet(self.caller, index)
        except TitleBallotError as error:
            if error.reason is TitleBallotReason.NO_PENDING_BALLOT:
                self.caller.msg(_NO_BALLOT)
            else:
                self.caller.msg(_BAD_INDEX)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
        else:
            self.caller.msg(
                f"你採納異名：{display}" if banked else f"你早已擁有異名：{display}"
            )

    def _decline(self) -> None:
        try:
            event_log = decline_epithet_ballot(self.caller)
        except TitleBallotError:
            self.caller.msg(_NO_BALLOT)
        except TitleDataError:
            self.caller.msg(_UNAVAILABLE)
        else:
            self.caller.msg(render_plain_text(event_log))

    def _show_ballot(self) -> None:
        ballot = safe_pending_ballot(self.caller)
        if not ballot:
            self.caller.msg(_NO_BALLOT)
            return
        lines = ["◆ 異名提名（待決）"]
        lines.extend(_ballot_line(index, entry) for index, entry in enumerate(ballot, start=1))
        lines.append("　以 title accept <編號> 採納，或 title decline 放棄。")
        self.caller.msg("\n".join(lines))


def _ballot_line(index: int, entry: dict) -> str:
    """One numbered ballot card: display plus its 事蹟引用."""
    return f"　{index}. {entry['display']}——{entry['basis']}"


def _strip_wrapping_quotes(name: str) -> str:
    """Drop one matching outer quote pair (the confirm-token escape form)."""
    if len(name) >= 2 and name[0] == name[-1] and name[0] in "\"'":
        return name[1:-1].strip()
    return name


def _quote_for_confirm(display: str) -> str:
    """Quote a display whose tail would eat the literal confirm token.

    ``title remove epithet foo confirm`` is ambiguous when ``foo confirm`` is
    itself a display, so the echoed confirmation line wraps such displays in
    quotes; the parse side strips one matching pair before the gate match.
    """
    lowered = display.lower()
    if lowered == _CONFIRM_TOKEN or lowered.endswith(f" {_CONFIRM_TOKEN}"):
        return f'"{display}"'
    return display
