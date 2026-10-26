"""Exact party action payloads and adapters.

``party.transfer`` moves held items between the authenticated commander and one
authorized present party member through ``world.rules.party_inventory``. The
payload names member ids only: the dispatcher passes just the session puppet as
the acting character and the rule re-derives every referenced member, so a
rejected reference is never replaced by the commander. Success publishes the
full canonical snapshot (empty affected-panel set).

``party.view_member`` stores which party member this session's party window is
looking at. It authorizes membership only (presence is not required, because
the window must keep a member visible while a failed follow strands them), is
keyed to the commander so possession keeps it, and never mutates gameplay
state: the only writes are the session-scoped selection and, for the skills
tab, that member's session unread dot.
"""

from typing import Any

from web.webclient.actions.service_actions import (
    MAX_KEY_CODE_POINTS,
    ServiceActionError,
    _success,
    _require_key_identifier,
)
from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from web.webclient.presentation.party_view_selection import TABS, select_party_view
from world.lore.items import ITEM_REGISTRY
from world.rules.party import live_companions
from world.rules.party_inventory import (
    MAX_TRANSFER_QUANTITY,
    MIN_TRANSFER_QUANTITY,
    PartyTransferError,
    transfer_item,
)
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
    resolve_commander,
)
from world.rules.unlock_notices import mark_unlocks_seen

_TRANSFER_FIELDS = frozenset({"giver_id", "receiver_id", "item_key", "quantity"})
_VIEW_MEMBER_FIELDS = frozenset({"member_id", "tab", "skill_key", "item_key"})


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


def _bounded_key(value: Any, field: str) -> str:
    """The shared whitespace-free bounded key, as a party-action rejection."""
    try:
        return _require_key_identifier(value, field, MAX_KEY_CODE_POINTS)
    except ServiceActionError as error:
        raise PartyActionError(str(error)) from error


def _item_key(value: Any) -> str:
    return _bounded_key(value, "item_key")


def _skill_key(value: Any) -> str | None:
    """The selected 技能-tab skill key: a bounded key, or null for none."""
    if value is None:
        return None
    return _bounded_key(value, "skill_key")


def _selected_item_key(value: Any) -> str | None:
    """The selected holdings item key: a bounded key, or null for none."""
    if value is None:
        return None
    return _bounded_key(value, "item_key")


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
        f"交給了{outcome.receiver.key}。"
    )
    return {
        "outcome": "success",
        "code": "transferred",
        "message": message,
        "affected_panels": (),
    }


def validate_party_view_member_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``party.view_member`` payload."""
    if not isinstance(payload, dict):
        raise PartyActionError("party.view_member payload must be an object")
    if set(payload) != _VIEW_MEMBER_FIELDS:
        raise PartyActionError(
            "party.view_member requires exactly member_id, tab, skill_key and item_key"
        )
    tab = payload["tab"]
    if not isinstance(tab, str) or tab not in TABS:
        raise PartyActionError("party.view_member tab must be a known member tab")
    return {
        "member_id": _member_id(payload["member_id"], "member_id"),
        "tab": tab,
        "skill_key": _skill_key(payload["skill_key"]),
        "item_key": _selected_item_key(payload["item_key"]),
    }


def _party_view_member_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Select one party member for this session's party window.

    Membership is re-derived through the party authority boundary, so a forged
    identity is refused with ``not_party_member`` and is never replaced by the
    commander; presence is deliberately not required. The only writes are the
    session-scoped selection and, on the skills tab, that member's unread dot.
    An item key no registry entry defines stores ``None``, so the holdings
    query reports no rows instead of an invented selection.
    """
    try:
        commander = resolve_commander(actor)
    except PartyScopeError as error:
        return {"outcome": "rejected", "code": error.reason, "message": error.message}
    member_id = payload["member_id"]
    commander_id = int(commander.pk)
    member = None
    if member_id == commander_id:
        member = commander
    else:
        member = next(
            (
                companion
                for companion in live_companions(commander)
                if int(companion.pk) == member_id
            ),
            None,
        )
    if member is None:
        return {
            "outcome": "rejected",
            "code": REASON_NOT_PARTY_MEMBER,
            "message": PARTY_SCOPE_MESSAGES[REASON_NOT_PARTY_MEMBER],
        }
    item_key = payload["item_key"]
    if item_key is not None and item_key not in ITEM_REGISTRY:
        item_key = None
    select_party_view(
        session,
        commander_id,
        member_id,
        payload["tab"],
        payload["skill_key"],
        item_key,
    )
    if payload["tab"] == "skills":
        mark_unlocks_seen(session, member_id)
    return _success(
        "viewing_member",
        "已選擇檢視的隊伍成員。",
        (
            "party",
            "party_member",
            "character",
            "party_inventory",
            "item_holdings",
            "lineage",
            # The shop rows follow the viewed member (services v7).
            "services",
        ),
    )
