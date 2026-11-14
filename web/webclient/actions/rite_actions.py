"""The registered ``explore.landmark_rite`` action and its shared renderings.

One settlement (``world.rules.landmark_rites``) serves two entry points: this
browser action and the text command ``commands/rite.py``. Both are thin. The
action accepts exactly ``{option, member_id}``; the server resolves the district,
archetype, cost and scene from the record owner's node, so the request can name
nothing else. The success result carries the committed scene as an
authored-scene delivery (``landmark-rite-panel`` renders it) and whether this was
the district's first completion.

The delivery uses ``scene_revision``, never ``revision``: a result ``data``
object carrying the reserved key ``revision`` is replaced by the dispatcher's
internal-error envelope *after* the rite already committed.

The helpers are shared with the text command: it emits the same scene lines and
the same completion line, so the two entry points cannot drift.
"""

from __future__ import annotations

from typing import Any

from web.webclient.actions.exploration_actions import (
    AFFECTED_FULL,
    ExplorationActionError,
    _rejected,
    _require_positive_int,
)
from world.lore.rites.loader import KEY_PATTERN
from world.lore.scenes import line_to_dict
from world.observability import log_error
from world.rules.landmark_rites import (
    RiteRefused,
    RiteResult,
    perform_rite,
    record_owner_for,
)

#: The authored watch scene's companion-name placeholder (plain text, never
#: ``str.format``: authored prose may carry other braces).
NAME_PLACEHOLDER = "{name}"
#: The player-facing line of an unexpected settlement failure.
FAILED_MESSAGE = "現在無法進行儀式。"


def rite_delivery(result: RiteResult) -> dict[str, Any]:
    """The committed rite's authored-scene delivery in its exact wire form."""
    plan = result.plan
    scene = result.scene
    body_name = plan.body.key
    lines: list[dict[str, str]] = []
    for line in scene.lines:
        payload = line_to_dict(line)
        if plan.perspective == "watch":
            # One authored watch scene names whichever companion performs.
            payload = {
                **payload,
                "text": payload["text"].replace(NAME_PLACEHOLDER, body_name),
            }
        lines.append(payload)
    return {
        "kind": "formal",
        "delivery_id": f"rite:{plan.site.district_key}:{plan.option.key}:{result.tick}",
        "scene_id": scene.scene_id,
        "scene_revision": scene.revision,
        "actor_name": "你" if plan.perspective == "self" else body_name,
        "guardian_name": plan.site.archetype.guardian_name_zh,
        "lines": lines,
    }


def rite_scene_text(result: RiteResult) -> str:
    """The delivered scene as plain text lines, one per authored line."""
    delivery = rite_delivery(result)
    speaker_names = {
        "actor": delivery["actor_name"],
        "host": delivery["guardian_name"],
    }
    rendered: list[str] = []
    for line in delivery["lines"]:
        if line["kind"] == "speech":
            rendered.append(f"{speaker_names[line['speaker']]}：{line['text']}")
        else:
            rendered.append(line["text"])
    return "\n".join(rendered)


def rite_completion_line(result: RiteResult) -> str:
    """The one completion line emitted after the scene."""
    plan = result.plan
    name = "你" if plan.perspective == "self" else plan.body.key
    return f"{name}完成了{plan.site.landmark_name}的儀式。"


def validate_landmark_rite_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``explore.landmark_rite`` payload ``{option, member_id}``.

    Every field the settlement itself resolves (district, archetype, cost, scene)
    is unreachable from here: an extra key is a rejected payload, never ignored.
    """
    if not isinstance(payload, dict) or set(payload) != {"option", "member_id"}:
        raise ExplorationActionError(
            "explore.landmark_rite requires exactly option and member_id"
        )
    option = payload["option"]
    if not isinstance(option, str) or KEY_PATTERN.fullmatch(option) is None:
        raise ExplorationActionError(
            "explore.landmark_rite option is not an authored option key"
        )
    member_id = payload["member_id"]
    if member_id is not None:
        member_id = _require_positive_int(member_id, "member_id")
    return {"option": option, "member_id": member_id}


def landmark_rite_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Settle one landmark rite; the result carries the delivered scene."""
    del session
    from server.camp_service import operation_identity

    identity = payload.get("request_identity") or {}
    try:
        # The owner resolution refuses too; it belongs inside this boundary so a
        # normal refusal can never surface as the dispatcher's internal error.
        owner = record_owner_for(actor)
        # Only an admitted transport request is replayable: without a request id
        # a derived identity would be one constant per owner, so a second call
        # would replay the first rite instead of settling a new one.
        operation_id = (
            operation_identity(
                int(owner.pk),
                "rite",
                identity.get("epoch", ""),
                identity.get("request_id", ""),
            )
            if identity.get("request_id")
            else None
        )
        result = perform_rite(
            actor,
            payload["option"],
            payload["member_id"],
            operation_id=operation_id,
        )
    except RiteRefused as error:  # observability: ignore R2: the settlement's stable refusal IS the action result
        return _rejected(error.code, error.message)
    except Exception as error:  # observability: ignore R2: the bounded rite_failed result IS the client-facing report; log_error below is its diagnostic
        log_error("landmark_rite_failed", context={"char": actor.pk}, exc=error)
        return _rejected("rite_failed", FAILED_MESSAGE)
    message = rite_completion_line(result)
    owner.msg(message)
    delivery = rite_delivery(result)
    from web.webclient.presentation.rite import store_rite_delivery

    store_rite_delivery(owner, delivery)
    return {
        "outcome": "success",
        "code": "explore.landmark_rite",
        "message": message,
        "data": {
            "delivery": delivery,
            "first_completion": result.first_completion,
        },
        "affected_panels": AFFECTED_FULL,
    }