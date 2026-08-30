"""Player-facing ``title`` command: browse the title册, swap slots, answer ballots.

``title list`` shows the current composed full title, every guild fixed-title
row (banked rows marked, locked rows carrying their authored ``hint_zh``),
every banked epithet, and — when one is pending — the numbered epithet
nomination ballot (change G). ``title equip fixed`` and ``title equip
epithet`` swap one occupied slot for another (D8): both slots always hold a
value once the 册 is non-empty, there is no unequip surface, and an unknown,
unbanked, or wrong-kind display fails with one stable rejection that never
enumerates candidates or hints at what the player is missing.
``title accept <1|2|3>`` and ``title decline`` answer the pending 異名提名投票
with the numbered choice only (ballots are never answered with free text);
out-of-range and no-ballot answers reply with stable reasons and change
nothing. Malformed stored title state presents the same fixed unavailable
line and changes nothing.
"""

from evennia import Command

from world.lore.titles import FIXED_TITLE_REGISTRY
from world.rules.event_log import render_plain_text
from world.rules.titles import (
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    accept_epithet,
    banked_fixed_keys,
    banked_epithets,
    compose_full_title,
    decline_epithet_ballot,
    equip_epithet,
    equip_fixed,
    safe_pending_ballot,
)

_USAGE = (
    "語法：title list | title equip fixed <稱號> | title equip epithet <異名> "
    "| title accept <1|2|3> | title decline"
)
_UNAVAILABLE = "你的稱號冊暫時無法閱讀。"
_REJECTED = "無法掛上該稱號。"
_NO_BALLOT = "目前沒有待決的異名提名。"
_BAD_INDEX = "沒有這個編號的提名。"
_BANKED_MARK = "●"
_LOCKED_MARK = "○"


class CmdTitle(Command):
    """Browse the title册, swap slots, and answer epithet nomination ballots."""

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
