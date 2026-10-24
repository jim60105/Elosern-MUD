"""Player-facing possession commands: ``possess`` (附身) and ``unpossess`` (歸位).

Possession changes control, not ownership: the account temporarily drives its
own bound NPC companion while the party model, affinity records, and quest
credit survive untouched.

The puppet-transfer and cmdset-mount transitions are documented seams in
``world/rules/possession.py`` and land with ``companion-possession-transition``.
"""

from commands.command import Command
from commands.talk import _resolve_npc
from world.rules.party import is_companion
from world.rules.possession import (
    POSSESSION_REJECTION_MESSAGES,
    REASON_NOT_BOUND,
    REASON_RELEASE_REFUSED,
    REASON_SESSION_MISMATCH,
    SLEEP_HANDOFF_RETURN,
    UNPOSSESS_RELEASED_MESSAGE,
    PossessionGateError,
    PossessionWriteError,
    _account_characters,
    _resolve_account,
    _resolve_live_object,
    confirm_sleep_handoff,
    current_possession,
    enter_possession,
    release_possession,
)
from world.rules.time_skip import SleepRefused

_MISSING_TARGET = "你想附身誰？請指定一個同伴（possess <npc>）。"
_AMBIGUOUS_TARGET = "這裡有好幾個目標，請說得更明確一些。"
_NOT_NPC = "那不是你的同伴。"
_HANDOFF_USAGE = "用法：handoff、handoff <編號>、handoff cancel"
_HANDOFF_CANCELLED = "你取消了交接，控制權沒有改變。"
_HANDOFF_NO_RECOVERY = "目前沒有可以接手的清醒同伴。可先等待恢復：sleep。"
_HANDOFF_STALE = "交接選項已經失效，以下是最新的選項。"
_ALL_PARTY_TOKENS = ("party", "全員", "全員一起睡眠")


class CmdPossess(Command):
    """Possess a bound companion in the same room."""

    key = "possess"
    aliases = ("附身",)
    help_category = "General"

    def func(self) -> None:
        parts = self.args.strip().split(maxsplit=1)
        raw_target = parts[0] if parts else ""
        resolved = _resolve_npc(
            self.caller,
            raw_target,
            missing=_MISSING_TARGET,
            ambiguous=_AMBIGUOUS_TARGET,
            not_npc=_NOT_NPC,
        )
        if isinstance(resolved, str):
            self.caller.msg(resolved)
            return

        npc = resolved
        if not is_companion(npc, self.caller):
            self.caller.msg(POSSESSION_REJECTION_MESSAGES[REASON_NOT_BOUND])
            return

        try:
            enter_possession(self.caller, npc)
        except PossessionGateError as error:
            msg = POSSESSION_REJECTION_MESSAGES.get(error.reason, "無法附身。")
            self.caller.msg(msg)
            return
        except PossessionWriteError:
            self.caller.msg("附身操作失敗，請稍後再試。")
            return

        self.caller.msg(f"你附身到了{npc.key}身上。")


class CmdUnpossess(Command):
    """Release current companion possession and return to your own body."""

    key = "unpossess"
    aliases = ("歸位",)
    help_category = "General"

    def func(self) -> None:
        caller = self.caller
        player = None
        target_npc = None

        # 1. Caller is PlayerCharacter
        current = current_possession(caller)
        if current is not None:
            player = caller
        # 2. Caller is possessed NPC
        elif getattr(getattr(caller, "db", None), "possessed_by", None) is not None:
            player_id = int(caller.db.possessed_by)
            player = _resolve_live_object(player_id)
            target_npc = caller
        # 3. Caller is Account
        elif hasattr(caller, "characters"):
            for char in _account_characters(caller):
                if current_possession(char) is not None:
                    player = char
                    break

        if player is None:
            self.caller.msg("你目前並未附身在任何同伴身上。")
            return

        try:
            release_possession(player, npc=target_npc, reason="handback")
        except PossessionWriteError as error:
            if getattr(error, "reason", None) != REASON_RELEASE_REFUSED:
                self.caller.msg("歸位操作失敗，請稍後再試。")
            return
        self.caller.msg(UNPOSSESS_RELEASED_MESSAGE)
        from server.dream_service import pending_sleep_question

        question = pending_sleep_question(player)
        if question is not None:
            self.caller.msg(question)


class CmdHandoff(Command):
    """List or confirm a sleep-driven control handoff."""

    key = "handoff"
    aliases = ("交接",)
    help_category = "General"

    def _listing_store(self):
        session = getattr(self, "session", None)
        return getattr(session, "ndb", None) if session is not None else self.caller.ndb

    def _clear_listing(self) -> None:
        store = self._listing_store()
        if store is not None:
            store.sleep_handoff_listing = None

    def _show(self, view) -> None:
        store = self._listing_store()
        if store is not None:
            store.sleep_handoff_listing = (
                view.transition_id,
                tuple((row.identity, row.enabled) for row in view.rows),
            )
        from world.rules.sleep_control import render_sleep_control_text

        self.caller.msg(render_sleep_control_text(view))

    def func(self) -> None:
        from world.rules.party_scope import PartyScopeError, resolve_commander
        from world.rules.sleep_control import (
            begin_all_party_sleep,
            build_sleep_control_view,
        )

        choice = self.args.strip()
        try:
            resolve_commander(self.caller)
        except PartyScopeError:
            self.caller.msg(POSSESSION_REJECTION_MESSAGES[REASON_SESSION_MISMATCH])
            return
        session = getattr(self, "session", None)
        view = build_sleep_control_view(
            self.caller, session=session
        )
        if choice in ("cancel", "取消"):
            self._clear_listing()
            self.caller.msg(_HANDOFF_CANCELLED)
            return
        if view is None:
            self.caller.msg(_HANDOFF_NO_RECOVERY)
            return
        if not choice:
            self._show(view)
            return
        if choice in _ALL_PARTY_TOKENS:
            try:
                begin_all_party_sleep(self.caller, session=session)
            except (PossessionGateError, PossessionWriteError, SleepRefused) as error:
                self.caller.msg(getattr(error, "message", None) or _HANDOFF_NO_RECOVERY)
                return
            self._clear_listing()
            self.caller.msg("在場成員已進入睡眠。")
            return

        store = self._listing_store()
        listing = getattr(store, "sleep_handoff_listing", None) if store is not None else None
        if (
            not isinstance(listing, tuple)
            or len(listing) != 2
            or listing[0] != view.transition_id
            or not choice.isdigit()
            or not 1 <= int(choice) <= len(listing[1])
        ):
            self.caller.msg(_HANDOFF_STALE)
            self._show(view)
            return
        listed_id, listed_enabled = listing[1][int(choice) - 1]
        candidate_id = listed_id
        row = next((item for item in view.rows if item.identity == candidate_id), None)
        if row is None or (listed_enabled and not row.enabled):
            self.caller.msg(_HANDOFF_STALE)
            self._show(view)
            return
        if not row.enabled:
            self.caller.msg(f"這個選項目前無法使用：{row.reason}")
            return
        commander = resolve_commander(self.caller)
        account = _resolve_account(commander, self.caller)
        try:
            confirm_sleep_handoff(
                account,
                commander,
                self.caller,
                candidate_id,
                transition_id=listing[0],
                session=session,
            )
        except PossessionGateError as error:
            message = POSSESSION_REJECTION_MESSAGES.get(error.reason, _HANDOFF_STALE)
            self.caller.msg(message)
            current = build_sleep_control_view(self.caller, session=session)
            if current is not None and current.rows:
                self._show(current)
            else:
                self.caller.msg(_HANDOFF_NO_RECOVERY)
            return
        except PossessionWriteError:
            self.caller.msg("交接操作失敗，請稍後再試。")
            return
        self._clear_listing()
        if row.kind == SLEEP_HANDOFF_RETURN:
            self.caller.msg(UNPOSSESS_RELEASED_MESSAGE)
        else:
            self.caller.msg(f"你接手了{row.name}的身體。")
