"""Text parity for the finite, offline-safe collaborative dream surface."""

import json

from commands.command import Command

_USAGE = (
    "用法：dream [enter|decline|say <文字>|draft [故事方向]|"
    "confirm [故事方向]|awaken]"
)


def render_state(state):
    if state is None:
        return "目前沒有夢境。請先睡眠；主人未附身時會詢問是否進入夢境。"
    parts = [state["opening"], state["scene"], state["dialogue"],
             f"剩餘交流次數：{state['remaining']}。"]
    if state["pending"]:
        parts.append("回應生成中，你仍可儲存草稿或醒來。")
    if state["failure"]:
        parts.append("回應暫時無法生成，你仍可儲存草稿或醒來。")
    if state["can_input"]:
        parts.append("dream say <想說的話>")
    if state["can_confirm"]:
        requirements = state.get("requirements") or []
        if requirements:
            # The reviewed version travels with the rows: a confirmation must
            # echo the version it actually read, and the text transport is a
            # surface like any other, so it names the same identity the panel
            # does. A row set without one has not been persisted yet, and the
            # text says so instead of implying a review that never happened.
            listed = "、".join(
                str(row.get("text", "")) for row in requirements if row.get("text")
            )
            version = state.get("requirement_version")
            suffix = (
                f"（已檢視的版本：{version}）"
                if version
                else "（尚未檢視：先 dream draft 記下，才會保存這些需求）"
            )
            parts.append(f"這個方向的可執行需求：{listed}{suffix}")
        parts.append("dream confirm [故事方向] ／ dream draft [故事方向]")
        if state["thread_choices"]:
            parts.append("可調整的故事線：" + "、".join(
                f"{choice['label']}（{choice['id']}）" for choice in state["thread_choices"]))
        parts.append("方向可使用 JSON，指定 kind、thread_id 與偏好欄位。")
    parts.append(state["ending"] or "dream awaken")
    return "\n".join(part for part in parts if part)


class CmdDream(Command):
    """Review a dream, negotiate direction, save/confirm, or awaken offline.

    Usage: dream [say <text>|draft [direction]|confirm [direction]|awaken]
    """

    key = "dream"
    aliases = ("夢境",)

    def func(self):
        from server.dream_service import (
            act,
            answer_sleep_dream,
            dream_state,
            pending_sleep_question,
        )
        from world.rules.time_skip import owner_sleep_view_state

        state = dream_state(self.caller)
        if not self.args.strip():
            question = pending_sleep_question(self.caller)
            if question is not None:
                self.caller.msg(question)
                return
            self.caller.msg(render_state(state))
            return
        action, _, text = self.args.strip().partition(" ")
        if action in {"enter", "decline"}:
            if text:
                self.caller.msg(_USAGE)
                return
            view = owner_sleep_view_state(self.caller)
            if view is None:
                self.caller.msg("目前沒有等待回答的睡眠夢境問題。")
                return
            answer = answer_sleep_dream(
                self.caller,
                decision=action,
                sleep_id=view["sleep_id"],
                revision=view["revision"],
                generation=view["generation"],
                session=self.session,
            )
            self.caller.msg(answer["message"])
            current = dream_state(self.caller)
            if current is not None and current["open"]:
                self.caller.msg(render_state(current))
            return
        if state is None:
            self.caller.msg(render_state(None))
            return
        if action not in {"say", "draft", "confirm", "awaken"} or (action == "awaken" and text):
            self.caller.msg(_USAGE)
            return
        direction = text if action in {"draft", "confirm"} else ""
        if direction.lstrip().startswith("{"):
            try:
                direction = json.loads(direction)
            except json.JSONDecodeError:
                # observability: ignore R2: malformed player JSON is a local syntax refusal; no persistent state or generation is touched
                self.caller.msg("故事方向 JSON 格式無法讀取。")
                return
        result = act(
            self.caller, action, session_id=state["session_id"],
            revision=state["revision"], message=text if action == "say" else "",
            direction=direction,
            session=self.session,
        )

        def completed(value):
            if value["outcome"] == "rejected":
                self.caller.msg(value["message"])
            current = dream_state(self.caller)
            if current["open"]:
                self.caller.msg(render_state(current))
            return value

        result.addCallback(completed)
        return result
