"""Text parity for the finite, offline-safe collaborative dream surface."""

import json

from commands.command import Command


def render_state(state):
    if state is None:
        return "目前沒有夢境。使用 sleep dream，在睡眠結束後進入夢境。"
    parts = [state["opening"], state["scene"], state["dialogue"],
             f"剩餘交流次數：{state['remaining']}。"]
    if state["pending"]:
        parts.append("回應生成中，你仍可儲存草稿或醒來。")
    if state["failure"]:
        parts.append("回應暫時無法生成，你仍可儲存草稿或醒來。")
    if state["can_input"]:
        parts.append("dream say <想說的話>")
    if state["can_confirm"]:
        parts.append("dream confirm [故事方向] ／ dream draft [故事方向]")
        if state["thread_choices"]:
            parts.append("可調整的故事線：" + "、".join(state["thread_choices"]))
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
        from server.dream_service import act, dream_state
        state = dream_state(self.caller)
        if not self.args.strip():
            self.caller.msg(render_state(state))
            return
        action, _, text = self.args.strip().partition(" ")
        if state is None:
            self.caller.msg(render_state(None))
            return
        if action not in {"say", "draft", "confirm", "awaken"} or (action == "awaken" and text):
            self.caller.msg("用法：dream [say <文字>|draft [故事方向]|confirm [故事方向]|awaken]")
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
