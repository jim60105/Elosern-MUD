"""Protected S6 transport: dispatch ownership and read committed projections."""

from __future__ import annotations

import json
import math

from server.console import registry as verbs, snapshot_policy
from server.console.errors import ConsoleError
from web.gm import responses
from web.gm.access import account_label
from web.gm.readers import registry as readers
from world.observability import log_error

STATUS = {
    "unknown_verb": 404, "registry_key_not_found": 404, "target_not_found": 404,
    "invalid_argument": 400, "target_kind_mismatch": 400, "raw_edit_invalid": 400,
    "snapshot_failed": 500, "internal_error": 500,
}


def _method(allow):
    response = responses.error("method_not_allowed", 405)
    response["Allow"] = allow
    return response


def _finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite JSON number")
    if isinstance(value, dict):
        for entry in value.values():
            _finite_json(entry)
    elif isinstance(value, list):
        for entry in value:
            _finite_json(entry)


def _body(request, code):
    try:
        body = json.loads(request.body)
        _finite_json(body)
        if not isinstance(body, dict):
            raise ValueError("object required")
        return body
    except (ValueError, UnicodeError) as error:
        raise ConsoleError(code) from error


def _refusal(error):
    message = None
    if error.code == "snapshot_failed" and error.reason in {"save_in_progress", "console_in_progress"}:
        message = "另一項存檔或主控台操作正在進行，操作未執行。請稍後再試。"
    return responses.error(error.code, STATUS[error.code], message, snapshot=error.snapshot)


def console_status(request):
    if request.method != "GET":
        return _method("GET")
    return responses.ok(snapshot_policy.status())


def _project(action, outcome, arguments):
    """No deleted-object read; special lifecycle surfaces keep their identity."""
    target = outcome["target"]
    if action == "delete_entity":
        return {"deleted": True, "dbref": target, "room": outcome.get("room")}
    if action == "advance_clock":
        from web.gm.dashboard import _world

        return _world()
    if action == "raw_edit":
        return readers.raw_object(target)
    if action in {"set_quest_state", "set_quest_stage", "issue_quest"}:
        return readers.build_list("quests", {"owner": target})
    if action in {"retract_memory", "supersede_memory"}:
        from world.narrative.memory import get_owner_generation

        owner = target.lstrip("#")
        filters = {"owner": target, "include_inactive": "true", "include_superseded": "true"}
        return {
            "memories": readers.build_list("memories", filters),
            "memory": readers.detail("memories", str(arguments["memory_id"]), filters),
            "generation": get_owner_generation(owner),
        }
    from evennia.objects.models import ObjectDB
    from web.gm.readers._entities import object_kind

    entity = ObjectDB.objects.get(pk=int(target.lstrip("#")))
    kind = object_kind(entity)
    state = readers.object_detail(kind, target) if kind is not None else readers.raw_object(target)
    if action == "spawn_monster":
        return {"monster": state, "room": outcome.get("room")}
    return state


def _completed(action, outcome, arguments):
    try:
        state = _project(action, outcome, arguments)
    except Exception as error:
        log_error("gm_projection_failed", context={"action": action, "target": outcome["target"]}, exc=error)
        state = {"error": {"code": "state_projection_failed", "message": responses.ERROR_MESSAGES["state_projection_failed"]}}
    return responses.ok({**outcome, "state": state})


def console_verb(request, verb):
    if request.method != "POST":
        return _method("POST")
    try:
        if verb not in verbs.VERBS:
            raise ConsoleError("unknown_verb")
        arguments = _body(request, "invalid_argument")
        verbs.validate_arguments(verb, arguments)
        target = arguments.get("target", arguments.get("room", "world"))
        # Do not echo malformed arbitrary strings into operational evidence.
        target = target if isinstance(target, str) and target.startswith("#") and target[1:].isdigit() else "world"
        outcome = snapshot_policy.policy.execute(
            lambda: verbs.dispatch(verb, arguments), action=verb,
            account=account_label(request.user), target=target,
            arguments=verbs.argument_summary(arguments),
        )
    except ConsoleError as error:  # observability: ignore R2: coordinator emits dispatched refusals; preflight is covered by gm_request
        return _refusal(error)
    return _completed(verb, outcome, arguments)


def raw_edit(request, dbref):
    from server.console.raw import apply_raw

    try:
        arguments = _body(request, "raw_edit_invalid")
        if set(arguments) != {"operations"} or not isinstance(arguments["operations"], list):
            raise ConsoleError("raw_edit_invalid")
        target = f"#{dbref.lstrip('#')}"
        outcome = snapshot_policy.policy.execute(
            lambda: apply_raw(target, arguments["operations"]), action="raw_edit",
            account=account_label(request.user), target=target if target[1:].isdigit() else "object",
            arguments=f"operations={len(arguments['operations'])}",
        )
    except ConsoleError as error:  # observability: ignore R2: coordinator emits dispatched refusals; preflight is covered by gm_request
        return _refusal(error)
    return _completed("raw_edit", outcome, arguments)
