"""Player-facing scene-entry command for generated instance quests.

``CmdEnterScene`` materializes the caller's current active instance-layer stage
through ``world.quests.scene_builder.materialize_stage`` and then moves the
caller into the spawned room through the plain exit the builder created --
ordinary traversal, which charges the standard ``move`` clock cost and records
map knowledge through the shared ``typeclasses.exits.Exit`` machinery. The
materialization commits before the move; every rejection is a named,
side-effect-free message.
"""

from evennia import Command

from django.db import transaction

from world.quests.compile import scene_requirements_for
from world.quests.definitions import DestinationKind
from world.quests.runtime import QuestDataError, QuestState, read_records
from world.quests.scene_builder import SceneBuilderError, materialize_stage

_NO_INSTANCE_SCENE = "你目前沒有需要進入的任務場景。"
_ALREADY_INSIDE = "你已經在任務場景裡了。"
_NO_DOORWAY = "這裡沒有通往任務場景的入口。"
_COULD_NOT_ENTER = "無法進入任務場景：{}"
_ENTERED = "你沿著小徑，走入了任務場景。"
_COULD_NOT_ENTER_MOVE = "你無法沿著這條路進入任務場景。"


def _instance_stage_record(records, caller):
    """Return the first active record whose current stage is enterable now.

    Deterministic selection: the first active quest, in log order, whose
    current stage carries a registered ``BOUND_INSTANCE`` spawn requirement
    that the caller can enter from the current location — when the requirement
    declares an ``anchor_near``, the caller must currently be at that anchor
    (unless the caller is already inside the stage's bound room, in which case
    the stage is reported so the command can say so).
    """
    caller_anchor = getattr(caller.location, "anchor_key", None)
    for record in records:
        if record.state is not QuestState.IN_PROGRESS:
            continue
        for requirement in scene_requirements_for(record.definition_key):
            if (
                requirement.index != record.stage_index
                or requirement.location is None
                or requirement.location.kind is not DestinationKind.BOUND_INSTANCE
            ):
                continue
            already_inside = (
                record.stage_room_id is not None
                and caller.location is not None
                and int(caller.location.pk) == record.stage_room_id
            )
            if already_inside:
                return record
            if (
                requirement.anchor_near is not None
                and requirement.anchor_near != caller_anchor
            ):
                continue
            return record
    return None


class CmdEnterScene(Command):
    """Enter the current stage's generated instance scene."""

    key = "進入"
    aliases = ("enter",)
    help_category = "General"

    def func(self) -> None:
        try:
            records = read_records(self.caller)
            target = _instance_stage_record(records, self.caller)
        except QuestDataError as error:
            self.caller.msg(_COULD_NOT_ENTER.format(error))
            return
        if target is None:
            self.caller.msg(_NO_INSTANCE_SCENE)
            return
        if (
            target.stage_room_id is not None
            and self.caller.location is not None
            and int(self.caller.location.pk) == target.stage_room_id
        ):
            self.caller.msg(_ALREADY_INSIDE)
            return
        origin = self.caller.location
        if origin is None:
            self.caller.msg(_COULD_NOT_ENTER.format("你不在任何地方。"))
            return
        try:
            result = materialize_stage(self.caller, target.quest_id, origin_room=origin)
        except (SceneBuilderError, QuestDataError) as error:
            self.caller.msg(_COULD_NOT_ENTER.format(error))
            return
        room = result.room
        forward = [exit_obj for exit_obj in origin.exits if exit_obj.destination == room]
        if not forward:
            self.caller.msg(_NO_DOORWAY)
            return
        exit_obj = forward[0]
        if not exit_obj.access(self.caller, "traverse"):
            self.caller.msg(_COULD_NOT_ENTER_MOVE)
            return
        exit_obj.at_traverse(self.caller, room)
        if self.caller.location is not room:
            # The exit's own failed-traverse path already reported why the move
            # could not happen (e.g. a combat lock veto); do not claim success.
            return
        if result.flavor_context is not None:
            self._schedule_scene_flavor(result.room, result.flavor_context)
        self.caller.msg(_ENTERED)

    def _schedule_scene_flavor(self, room, flavor_context) -> None:
        """Register the flavor generation through ``transaction.on_commit``.

        Runs only after the caller has successfully traversed into the scene,
        so the completion push reaches a player already inside the room even
        when the callback fires immediately (no outer transaction) or the
        client resolves synchronously; a nested outer transaction that rolls
        back still never fires a generation (design D2). Fire-and-forget,
        never blocking arrival and never raising to the command (the service
        wraps every synchronous failure into a logged no-op).
        """
        from server.scene_flavor_service import schedule_scene_flavor

        transaction.on_commit(
            lambda: schedule_scene_flavor(room, flavor_context)
        )
