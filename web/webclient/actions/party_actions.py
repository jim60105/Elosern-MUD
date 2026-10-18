"""Exact party action payloads and adapters (party-item-transfer).

``party.transfer`` moves held items between the authenticated commander and one
authorized present party member through ``world.rules.party_inventory``. The
payload names member ids only: the dispatcher passes just the session puppet as
the acting character and the rule re-derives every referenced member, so a
rejected reference is never replaced by the commander. Success publishes the
full canonical snapshot (empty affected-panel set).
"""

from typing import Any

from web.webclient.actions.service_actions import (
    MAX_KEY_CODE_POINTS,
    ServiceActionError,
    _require_key_identifier,
)
from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.rules.party_inventory import (
    MAX_TRANSFER_QUANTITY,
    MIN_TRANSFER_QUANTITY,
    PartyTransferError,
    transfer_item,
)

_TRANSFER_FIELDS = frozenset({"giver_id", "receiver_id", "item_key", "quantity"})


class PartyActionError(ValueError):
    """A party action payload violates its exact bounded schema."""


def _member_id(value: Any, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_SAFE_INTEGER
    ):
        raise PartyActionError(f"{field} must be a positive safe integer")
    return value


def _item_key(value: Any) -> str:
    """The shared whitespace-free bounded key, as a party-action rejection."""
    try:
        return _require_key_identifier(value, "item_key", MAX_KEY_CODE_POINTS)
    except ServiceActionError as error:
        raise PartyActionError(str(error)) from error


def _quantity(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PartyActionError("quantity must be an integer")
    if not MIN_TRANSFER_QUANTITY <= value <= MAX_TRANSFER_QUANTITY:
        raise PartyActionError(
            f"quantity must be within {MIN_TRANSFER_QUANTITY}..{MAX_TRANSFER_QUANTITY}"
        )
    return value


def validate_party_transfer_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``party.transfer`` payload."""
    if not isinstance(payload, dict):
        raise PartyActionError("party.transfer payload must be an object")
    if set(payload) != _TRANSFER_FIELDS:
        raise PartyActionError(
            "party.transfer requires exactly giver_id, receiver_id, item_key and quantity"
        )
    return {
        "giver_id": _member_id(payload["giver_id"], "giver_id"),
        "receiver_id": _member_id(payload["receiver_id"], "receiver_id"),
        "item_key": _item_key(payload["item_key"]),
        "quantity": _quantity(payload["quantity"]),
    }


def _party_transfer_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Move the named items through the member transfer rule."""
    del session
    from world.rules.npc_identity import npc_display_name
    from world.rules.quest_delivery import item_display_name

    try:
        outcome = transfer_item(
            actor,
            payload["giver_id"],
            payload["receiver_id"],
            payload["item_key"],
            payload["quantity"],
        )
    except PartyTransferError as error:
        return {"outcome": "rejected", "code": error.reason, "message": error.message}
    message = (
        f"你把 {outcome.quantity} 個{item_display_name(outcome.item_key)}"
        f"交給了{npc_display_name(outcome.receiver)}。"
    )
    return {
        "outcome": "success",
        "code": "transferred",
        "message": message,
        "affected_panels": (),
    }
