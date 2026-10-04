"""Exact letter actions returning bounded, result-only personal read models."""

from world.narrative import player_correspondence as letters
from world.narrative.models import LetterState


def _fields(payload, fields):
    if not isinstance(payload, dict) or set(payload) != set(fields):
        raise ValueError("Unexpected correspondence payload fields.")
    return payload


def _string(value, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("Invalid bounded correspondence string.")
    return value


def validate_list(payload):
    _fields(payload, ("after",))
    if type(payload["after"]) is not int or not 0 <= payload["after"] <= 9_007_199_254_740_991:
        raise ValueError("Invalid correspondence cursor.")
    return dict(payload)


def validate_collect(payload):
    return dict(_fields(payload, ()))


def validate_read(payload):
    _fields(payload, ("source_id",))
    return {"source_id": _string(payload["source_id"], 128)}


def validate_send(payload):
    _fields(payload, ("recipient", "body_parts", "source_id"))
    parts = payload["body_parts"]
    if not isinstance(parts, list) or not 1 <= len(parts) <= 4:
        raise ValueError("Invalid correspondence body parts.")
    if any(not isinstance(part, str) or len(part) > 2000 for part in parts):
        raise ValueError("Invalid correspondence body part.")
    body = "".join(parts)
    _string(body, 8000)
    return {"recipient": _string(payload["recipient"], 255), "body": body,
            "source_id": _string(payload["source_id"], 128)}


def _result(operation):
    try:
        data = operation()
    except letters.CorrespondenceError as error:
        # observability: ignore R2: an expected refusal is the action result;
        # the dispatcher records the boundary without private letter prose.
        return {"outcome": "rejected", "code": "letters.denied", "message": str(error),
                "affected_panels": ()}
    return {"outcome": "success", "code": "letters.ok", "message": "信件操作完成。",
            "data": data, "affected_panels": ()}


def list_adapter(actor, payload, session=None):
    return _result(lambda: letters.list_letters(actor, payload["after"]))


def collect_adapter(actor, payload, session=None):
    def operation():
        acquired = letters.collect(actor)
        return {**letters.list_letters(actor), "count": len(acquired)}
    return _result(operation)


def send_adapter(actor, payload, session=None):
    def operation():
        record = letters.send(actor, payload["recipient"], payload["body"], payload["source_id"])
        return {**letters.list_letters(actor), "sent_id": record.source_id}
    return _result(operation)


def read_adapter(actor, payload, session=None):
    def operation():
        record = letters.read(actor, payload["source_id"])
        return {"source_id": record.source_id, "sender_id": record.sender_id,
                "read_tick": LetterState.objects.get(letter__source_id=record.source_id).read_tick,
                "body_parts": [record.body[offset:offset + 2000]
                               for offset in range(0, len(record.body), 2000)]}
    return _result(operation)
