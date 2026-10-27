"""Exact service action payload validators and narrow adapters.

The seven production service actions are ``guild.register``,
``guild.quest_accept``, ``guild.quest_abandon``, ``guild.quest_turnin``,
``guild.exam_request``, ``shop.buy``, and ``shop.sell``; the read-only
``services.open`` names one selected provider. Each validator enforces an exact
bounded payload shape. Each provider mutation requires its exact ``npc_id``:
the adapter resolves that identity through
:func:`world.rules.service_targets.require_service_mutation` (visibility,
co-presence, capability, binding, schedule, combat and possession) and passes
the resolved host to the deterministic domain API, which validates it again
and owns every write. No room-wide discovery, substitution, or client flag
participates. Private escort abandonment keeps its host-free ``{quest_id}``
shape and ordinary guild abandonment requires its staff; the canonical quest
record decides which shape applies, so a missing ``npc_id`` can never turn an
ordinary record into host-free abandonment.

Adapters never assign ``.db`` attributes, traits, registration, rank, merit,
quest log, wallet, inventory, merchant stock, or location directly. No payload
accepts an actor, host, branch, session, price, stock, or wallet field; a party
member reference appears only in the exact member field its owning capability
defines (``inventory.use`` and ``inventory.toggle_equip`` ``actor_id``,
``shop.buy`` ``recipient_id``, ``shop.sell`` ``seller_id``), and no action
routes through the text command parser.
"""

from typing import Any

from typeclasses.components import GuildExamReception, GuildStaff, Merchant
from web.webclient.presentation.protocol import (
    MAX_RESULT_DATA_BYTES,
    MAX_SAFE_INTEGER,
    json_byte_size,
)
from world.quests.runtime import (
    QuestAlreadyActive,
    QuestDataError,
    QuestNotFound,
    QuestState,
    QuestTargetsUnavailable,
    QuestTransitionError,
    abandon_quest,
    find_record,
    read_records,
    set_quest_tracked,
)
from world.rules.combat_session import SessionReason
from world.rules.economy import TradeError, buy, sell
from world.rules.equipment_effects import toggle_equipment_message
from world.rules.event_log import render_plain_text
from world.rules.guild import (
    GuildDataError,
    GuildError,
    RewardClaimError,
    register_adventurer,
    turn_in_quest,
)
from world.rules.guild_exam_request import OUTCOME_SCHEDULE, request_guild_exam
from world.rules.guild_exams import GuildExamError
from world.rules.guild_offers import (
    BoardAccessError,
    GuildOfferError,
    accept_guild_offer,
    abandon_guild_quest,
)
from world.rules.party_inventory import toggle_member_equipment, use_member_item
from world.rules.party_scope import (
    PURPOSE_ACT,
    PartyScopeError,
    authorize_member,
    party_in_combat,
    resolve_commander,
)
from world.rules.player_messages import session_reason_message
from world.rules.service_messages import (
    exam_schedule_message,
    exam_started_message,
    rejection_code,
    rejection_message,
)
from world.rules.service_targets import (
    ServiceTargetError,
    require_service_mutation,
)
from world.rules.unlock_notices import deliver_unlocks, notices_from_events

# Wire limits (equal to or below the protocol identifier bound).
MAX_KEY_CODE_POINTS = 64
MAX_RANK_KEY_CODE_POINTS = 8
MAX_QUANTITY = 1000
MIN_QUANTITY = 1

# Stable panels each admitted service action may publish. Every quest write
# seam publishes the ``objectives`` panel beside its paired ``services`` rows
# (webclient-align-06: the tracker island must never lag the quest log).
AFFECTED_REGISTER = ("status", "services")
AFFECTED_ACCEPT = ("services", "objectives", "quest_log")
AFFECTED_ABANDON = ("services", "objectives", "quest_log")
# A turn-in can add reward items to a member's canonical bag, and an admitted
# examination enters combat, so both republish the selected item's holdings.
AFFECTED_TURNIN = (
    "status",
    "services",
    "objectives",
    "quest_log",
    "item_holdings",
)
AFFECTED_EXAM = ("status", "services", "context_actions", "item_holdings")
# Planned attendance writes nothing; republishing the unchanged services
# panel settles the request without a full snapshot.
AFFECTED_EXAM_SCHEDULE = ("services",)
# A trade rewrites a member's canonical bag and the party purse, so the
# selected item's holdings query and the viewed member's bag panel (the party
# window's 背包 tab and header purse) are republished beside the shop rows.
AFFECTED_TRADE = (
    "status",
    "services",
    "objectives",
    "quest_log",
    "item_holdings",
    "party_inventory",
)
AFFECTED_TRACK = ("services", "objectives", "quest_log")
#: The exact abandonment shape mismatch: the canonical record kind and the
#: supplied payload disagree. Never a fallback to the other shape.
REASON_ABANDON_SHAPE = "abandon_target_mismatch"
#: ``services.open`` cannot build a conforming payload for a mode that has no
#: player to read for.
REASON_NOT_ALLOWED_MODE = "not_allowed_mode"
REASON_SERVICES_TOO_LARGE = "services_too_large"


class ServiceActionError(ValueError):
    """A service action payload violates its exact bounded schema."""


def _require_non_empty_string(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ServiceActionError(f"{field} must be a non-empty string")
    if sum(1 for _ in value) > maximum:
        raise ServiceActionError(f"{field} exceeds its bound")
    return value


def _require_quantity(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ServiceActionError("quantity must be an integer")
    if not MIN_QUANTITY <= value <= MAX_QUANTITY:
        raise ServiceActionError(f"quantity must be within {MIN_QUANTITY}..{MAX_QUANTITY}")
    return value


def _require_npc_identifier(value: Any) -> int:
    """Require one positive safe integer provider identity."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_SAFE_INTEGER
    ):
        raise ServiceActionError("npc_id must be a positive safe integer")
    return value


def _validate_provider_payload(
    payload: dict[str, Any], action_id: str, required: set[str]
) -> dict[str, Any]:
    """Validate one exact provider-mutation payload.

    ``required`` names the action's own bounded fields; ``npc_id`` is required
    on top of them and nothing else may appear.
    """
    if not isinstance(payload, dict):
        raise ServiceActionError(f"{action_id} payload must be an object")
    expected = required | {"npc_id"}
    unknown = set(payload) - expected
    if unknown:
        raise ServiceActionError(f"payload has unknown fields {sorted(unknown)}")
    missing = expected - set(payload)
    if missing:
        raise ServiceActionError(f"payload requires {sorted(missing)}")
    return payload


def validate_guild_register_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.register`` payload (one provider identity)."""
    _validate_provider_payload(payload, "guild.register", set())
    return {"npc_id": _require_npc_identifier(payload["npc_id"])}


def validate_quest_accept_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.quest_accept`` payload."""
    _validate_provider_payload(
        payload, "guild.quest_accept", {"definition_key"}
    )
    return {
        "definition_key": _require_non_empty_string(
            payload["definition_key"], "definition_key", MAX_KEY_CODE_POINTS
        ),
        "npc_id": _require_npc_identifier(payload["npc_id"]),
    }


def validate_quest_abandon_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate one of the two exact ``guild.quest_abandon`` payloads.

    Ordinarily ``{quest_id, npc_id}``; a private escort keeps the host-free
    ``{quest_id}``. The validator admits exactly those shapes and nothing else;
    the adapter decides which one the canonical record kind requires.
    """
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    unknown = set(payload) - {"quest_id", "npc_id"}
    if unknown:
        raise ServiceActionError(
            f"payload has unknown fields {sorted(unknown)}"
        )
    if "quest_id" not in payload:
        raise ServiceActionError("payload requires ['quest_id']")
    validated = {
        "quest_id": _require_non_empty_string(
            payload["quest_id"], "quest_id", MAX_KEY_CODE_POINTS
        )
    }
    if "npc_id" in payload:
        validated["npc_id"] = _require_npc_identifier(payload["npc_id"])
    return validated


def validate_quest_turnin_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.quest_turnin`` payload."""
    _validate_provider_payload(payload, "guild.quest_turnin", {"quest_id"})
    return {
        "quest_id": _require_non_empty_string(
            payload["quest_id"], "quest_id", MAX_KEY_CODE_POINTS
        ),
        "npc_id": _require_npc_identifier(payload["npc_id"]),
    }


def validate_quest_track_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.quest_track`` payload (quest ID plus flag)."""
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    if set(payload) != {"quest_id", "tracked"}:
        raise ServiceActionError("guild.quest_track accepts exactly quest_id and tracked")
    quest_id = _require_non_empty_string(payload["quest_id"], "quest_id", MAX_KEY_CODE_POINTS)
    tracked = payload["tracked"]
    if not isinstance(tracked, bool):
        raise ServiceActionError("tracked must be a boolean")
    return {"quest_id": quest_id, "tracked": tracked}


def validate_exam_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``guild.exam_request`` payload.

    Branch, examiner, clock and threshold fields are unknown fields and reject
    here, before the request coordinator runs; ``npc_id`` names the selected
    reception.
    """
    _validate_provider_payload(payload, "guild.exam_request", {"target_rank"})
    return {
        "target_rank": _require_non_empty_string(
            payload["target_rank"], "target_rank", MAX_RANK_KEY_CODE_POINTS
        ),
        "npc_id": _require_npc_identifier(payload["npc_id"]),
    }


def validate_services_open_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``services.open`` payload (one selected provider)."""
    _validate_provider_payload(payload, "services.open", set())
    return {"npc_id": _require_npc_identifier(payload["npc_id"])}


def _validate_trade_payload(
    payload: dict[str, Any], action_id: str, member_field: str
) -> dict[str, Any]:
    _validate_provider_payload(
        payload, action_id, {"item_key", "quantity", member_field}
    )
    return {
        "item_key": _require_non_empty_string(
            payload["item_key"], "item_key", MAX_KEY_CODE_POINTS
        ),
        "quantity": _require_quantity(payload["quantity"]),
        member_field: _require_member_identifier(
            payload[member_field], member_field
        ),
        "npc_id": _require_npc_identifier(payload["npc_id"]),
    }


def validate_buy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``shop.buy`` payload (item, quantity, recipient)."""
    return _validate_trade_payload(payload, "shop.buy", "recipient_id")


def validate_sell_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``shop.sell`` payload (item, quantity, seller)."""
    return _validate_trade_payload(payload, "shop.sell", "seller_id")


def _require_key_identifier(value: Any, field: str, maximum: int) -> str:
    """Require a whitespace-free bounded key.

    The typed `使用`/`use` command takes its key as the first
    whitespace-delimited token and `裝備`/`equip` resolves its whole item
    argument as a registry key or a held display name, while the browser's
    input echo prints the key verbatim — a whitespace-bearing key would echo a
    line whose keyboard replay resolves a DIFFERENT item. Reject at the action
    boundary instead (complete-ui-command-echo D1).
    """
    text = _require_non_empty_string(value, field, maximum)
    if any(character.isspace() for character in text):
        raise ServiceActionError(f"{field} must not contain whitespace")
    return text


def _require_member_identifier(value: Any, field: str = "actor_id") -> int:
    """Require one positive safe integer member identity.

    A bool is an int subclass, so it is excluded explicitly; a string, float,
    zero, negative, or out-of-range identity never reaches the party boundary.
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_SAFE_INTEGER
    ):
        raise ServiceActionError(f"{field} must be a positive safe integer")
    return value


def validate_inventory_use_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``inventory.use`` payload (member, key, target).

    Accepted forms are exactly ``{actor_id, item_key}`` or
    ``{actor_id, item_key, target_key}``. ``actor_id`` names the member who
    uses the item from that member's own bag (reauthorized for the acting
    purpose in the adapter) and is never replaced by the commander.
    ``target_key`` names *whom* an effect reaches and never *what* the item
    does (add-item-effect-targeting): it is consumed only by an effect the
    rulebook already scoped to a single entity, and a token the adapter
    cannot resolve to a present entity — a group shorthand included — is the
    deterministic preflight's fail-closed rejection, never a silently
    ignored reach.
    """
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    unknown = set(payload) - {"actor_id", "item_key", "target_key"}
    if unknown:
        raise ServiceActionError(f"payload has unknown fields {sorted(unknown)}")
    missing = {"actor_id", "item_key"} - set(payload)
    if missing:
        raise ServiceActionError(f"payload requires {sorted(missing)}")
    validated = {
        "actor_id": _require_member_identifier(payload["actor_id"]),
        "item_key": _require_key_identifier(
            payload["item_key"], "item_key", MAX_KEY_CODE_POINTS
        ),
    }
    if "target_key" in payload:
        validated["target_key"] = _require_key_identifier(
            payload["target_key"], "target_key", MAX_KEY_CODE_POINTS
        )
    return validated


def validate_inventory_toggle_equip_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``inventory.toggle_equip`` payload (member plus key).

    ``actor_id`` names the member whose equipment toggles and is reauthorized
    by the party member boundary in the adapter, never by the payload; the
    client still chooses no slot, effect, or quantity.
    """
    if not isinstance(payload, dict):
        raise ServiceActionError("payload must be an object")
    unknown = set(payload) - {"actor_id", "item_key"}
    if unknown:
        raise ServiceActionError(f"payload has unknown fields {sorted(unknown)}")
    missing = {"actor_id", "item_key"} - set(payload)
    if missing:
        raise ServiceActionError(f"payload requires {sorted(missing)}")
    return {
        "actor_id": _require_member_identifier(payload["actor_id"]),
        "item_key": _require_key_identifier(
            payload["item_key"], "item_key", MAX_KEY_CODE_POINTS
        ),
    }


# ---------------------------------------------------------------------------
# Adapter helpers.
# ---------------------------------------------------------------------------


def _resolve_target(
    actor: Any, payload: dict[str, Any], component_class: type
) -> tuple[Any, dict[str, Any] | None]:
    """Return ``(provider, None)`` or ``(None, rejection)`` for one exact npc.

    Admission revalidates the whole selection against committed state at
    submit time; the host it returns is the only host the domain API receives.
    """
    try:
        npc, _component = require_service_mutation(
            actor, payload["npc_id"], component_class
        )
    except ServiceTargetError as error:
        return None, _rejected(error)
    return npc, None


def _rejected(reason: Any) -> dict[str, Any]:
    code = rejection_code(reason)
    return {"outcome": "rejected", "code": code, "message": rejection_message(reason)}


def _session_rejected(reason: Any) -> dict[str, Any]:
    code = str(reason)
    return {"outcome": "rejected", "code": code, "message": session_reason_message(code)}


def _success(code: str, message: str, affected: tuple[str, ...]) -> dict[str, Any]:
    return {
        "outcome": "success",
        "code": code,
        "message": message,
        "affected_panels": affected,
    }


# ---------------------------------------------------------------------------
# Adapters.
# ---------------------------------------------------------------------------


def _guild_register_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Register the actor at rank F through the exact selected staff host."""
    del session
    staff, rejection = _resolve_target(actor, payload, GuildStaff)
    if rejection is not None:
        return rejection
    try:
        record = register_adventurer(actor, staff)
    except (GuildDataError, GuildError) as error:
        return _rejected(error)
    message = f"你已註冊為冒險者，階級 F。公會：{record['branch_key']}"
    actor.msg(message)
    for line in record.get("title_notifications", ()):
        actor.msg(line)
    return _success("registered", message, AFFECTED_REGISTER)


def _quest_accept_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Revalidate board eligibility and delegate acceptance to the quest runtime."""
    del session
    definition_key = payload["definition_key"]
    staff, rejection = _resolve_target(actor, payload, GuildStaff)
    if rejection is not None:
        return rejection
    try:
        record = accept_guild_offer(actor, staff, definition_key)
    except (
        BoardAccessError,
        GuildOfferError,
        QuestDataError,
        QuestNotFound,
        QuestAlreadyActive,
        QuestTargetsUnavailable,
    ) as error:
        return _rejected(error)
    message = f"你接取了任務 {record.quest_id}。"
    actor.msg(message)
    return _success("accepted", message, AFFECTED_ACCEPT)


def _quest_abandon_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Abandon one record in the shape its canonical kind requires.

    An ordinary guild record needs its exact selected staff host; a private
    escort accepted under a published package keeps the host-free shape. The
    canonical record decides, so neither payload can stand in for the other.
    """
    del session
    quest_id = payload["quest_id"]
    try:
        records = read_records(actor)
    except QuestDataError as error:
        return _rejected(error)
    record = find_record(records, quest_id)
    if record is None:
        return _rejected(QuestNotFound(quest_id))
    if record.state is not QuestState.IN_PROGRESS:
        # A terminal record (including an invalidated escort) is never
        # abandoned again, in either shape.
        return _rejected(QuestTransitionError("quest_transition"))
    if record.package_id is not None:
        if "npc_id" in payload:
            return _rejected(REASON_ABANDON_SHAPE)
        try:
            failed = abandon_quest(actor, quest_id)
        except (QuestNotFound, QuestDataError) as error:
            return _rejected(error)
        message = f"你放棄了任務 {failed.quest_id}。"
        actor.msg(message)
        return _success("abandoned", message, AFFECTED_ABANDON)
    if "npc_id" not in payload:
        return _rejected(REASON_ABANDON_SHAPE)
    staff, rejection = _resolve_target(actor, payload, GuildStaff)
    if rejection is not None:
        return rejection
    try:
        record = abandon_guild_quest(actor, staff, quest_id)
    except (QuestNotFound, QuestDataError) as error:
        return _rejected(error)
    message = f"你放棄了任務 {record.quest_id}。"
    actor.msg(message)
    return _success("abandoned", message, AFFECTED_ABANDON)


def _quest_turnin_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Claim one completed quest reward exactly once through the local staff."""
    del session
    quest_id = payload["quest_id"]
    staff, rejection = _resolve_target(actor, payload, GuildStaff)
    if rejection is not None:
        return rejection
    try:
        result = turn_in_quest(actor, staff, quest_id)
    except (RewardClaimError, GuildDataError, GuildError, QuestDataError) as error:
        return _rejected(error)
    message = (
        f"你回報了任務 {result['quest_id']}，獲得 {result['copper']} 銅、"
        f"功績 {result['merit']} 與道具 {result['items']}。"
    )
    actor.msg(message)
    for line in result.get("title_notifications", ()):
        actor.msg(line)
    return _success("claimed", message, AFFECTED_TURNIN)


def _quest_track_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Flip the tracking flag on exactly one of the holder's own records.

    Host-independent by contract (webclient-align-06): tracking truth is
    player state, so NO staff host and NO schedule gate is consulted — the
    lifecycle operation itself is the only authority, and it validates the
    whole log before writing.
    """
    del session
    quest_id = payload["quest_id"]
    tracked = payload["tracked"]
    try:
        record = set_quest_tracked(actor, quest_id, tracked)
    except (QuestNotFound, QuestDataError, QuestTransitionError) as error:
        return _rejected(error)
    if tracked:
        message = f"你已開始追蹤任務 {record.quest_id}。"
    else:
        message = f"你已取消追蹤任務 {record.quest_id}。"
    actor.msg(message)
    return _success(
        "tracked" if tracked else "untracked", message, AFFECTED_TRACK
    )


def _exam_request_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Ask the shared coordinator for planned attendance or the exam start.

    The selected reception is the request's speaker, so the counter is the
    exact NPC the client opened; the branch, next-rank target and qualified
    persistent adventurer are derived server-side and merit/host presence
    never gate the request itself. ``exam_schedule`` is read-only planned
    information (no panel changes), ``exam_started`` hands the shell to combat.
    """
    del session
    target_rank = payload["target_rank"]
    reception, rejection = _resolve_target(actor, payload, GuildExamReception)
    if rejection is not None:
        return rejection
    try:
        outcome = request_guild_exam(
            actor, target_rank, speaker=reception, requested_by="webclient"
        )
    except GuildExamError as error:
        return _rejected(error)
    if outcome.kind == OUTCOME_SCHEDULE:
        message = exam_schedule_message(
            outcome.host_name, outcome.target_rank,
            outcome.interval.start_tick, outcome.interval.end_tick,
        )
        actor.msg(message)
        return _success("exam_schedule", message, AFFECTED_EXAM_SCHEDULE)
    message = exam_started_message(outcome.target_rank)
    actor.msg(message)
    return _success("exam_started", message, AFFECTED_EXAM)


def _buy_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Recheck the host, then buy for the named recipient from the party purse.

    The recipient is reauthorized by the economy rule's party boundary (a
    forged, absent, or non-member id rejects with the shared party code and
    the commander never receives the goods in its place); the adapter itself
    never writes state. A possessed actor settles through the same rule, with
    the commander's purse and the named member's bag.
    """
    del session
    item_key = payload["item_key"]
    quantity = payload["quantity"]
    merchant_host, rejection = _resolve_target(actor, payload, Merchant)
    if rejection is not None:
        return rejection
    try:
        result = buy(
            actor, merchant_host, item_key, quantity, payload["recipient_id"]
        )
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    except TradeError as error:
        return _rejected(error)
    message = (
        f"你買了 {result['quantity']} 個 {result['item_key']}，"
        f"花費 {result['total_copper']} 銅，剩餘 {result['wallet']} 銅。"
    )
    actor.msg(message)
    return _success("bought", message, AFFECTED_TRADE)


def _sell_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Recheck the host, then sell the named seller's unequipped items.

    The seller is reauthorized by the economy rule's party boundary; the
    unchanged sell price is credited to the party purse, and the adapter
    itself never writes state. A possessed actor settles through the same
    rule, with the named member's bag and the commander's purse.
    """
    del session
    item_key = payload["item_key"]
    quantity = payload["quantity"]
    merchant_host, rejection = _resolve_target(actor, payload, Merchant)
    if rejection is not None:
        return rejection
    try:
        result = sell(
            actor, merchant_host, item_key, quantity, payload["seller_id"]
        )
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    except TradeError as error:
        return _rejected(error)
    message = (
        f"你賣了 {result['quantity']} 個 {result['item_key']}，"
        f"獲得 {result['total_copper']} 銅，目前 {result['wallet']} 銅。"
    )
    actor.msg(message)
    return _success("sold", message, AFFECTED_TRADE)


def _resolve_inventory_target(actor: Any, target_key: str) -> Any:
    """Resolve one ``target_key`` to a present entity for item targeting.

    Only the exploration path reaches this helper: during an active combat
    session ``inventory.use`` rejects before any resolution, because a party
    session's item selections are actor-scoped draft entries saved through the
    guarded ``combat.command`` path. ``actor`` is the member who uses the item
    (never the commander behind it), so the world view is that member's
    current location's contents — the same room the party boundary already
    proved it shares with the commander. An unresolvable token — an unknown
    key or a group shorthand — travels on as the raw string, where the
    deterministic preflight's fail-closed target guard rejects it with the
    stable invalid-target reason: the client can never select a reach the
    rulebook did not grant.
    """
    location = getattr(actor, "location", None)
    if location is not None:
        for obj in location.contents:
            if getattr(obj, "key", None) == target_key:
                return obj
    return target_key


def _services_open_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Read one selected provider's services snapshot as a private result.

    Read-only: it resolves the exact selected NPC, serializes the schema-8
    snapshot that targets it and returns it in the result's own data slot
    (``{npc_id, services}``). Nothing is published, no clock or effect runs,
    and every rejection keeps the same private, presentation-free shape so a
    stale or unauthorized provider never reopens UI through a side channel.
    """
    npc_id = payload["npc_id"]
    if bool(getattr(actor, "creation_pending", False)):
        return {**_rejected(REASON_NOT_ALLOWED_MODE), "no_presentation": True}
    from web.webclient.presentation.party_view_selection import (
        resolve_session_viewed_member,
    )
    from web.webclient.presentation.services import build_services_payload
    from world.rules.service_view import ServicesViewError

    try:
        viewed = resolve_session_viewed_member(session, actor)
        snapshot = build_services_payload(actor, viewed, provider_id=npc_id)
    except ServiceTargetError as error:
        return {**_rejected(error), "no_presentation": True}
    except ServicesViewError:
        return {**_rejected("services_unavailable"), "no_presentation": True}
    data = {"npc_id": npc_id, "services": snapshot}
    if json_byte_size(data) > MAX_RESULT_DATA_BYTES:
        # Over the private result budget: refuse with a bounded result rather
        # than truncating rows or relaxing a transport limit.
        return {**_rejected(REASON_SERVICES_TOO_LARGE), "no_presentation": True}
    return {
        "outcome": "success",
        "code": "services_open",
        "message": "已讀取服務資訊。",
        "data": data,
        "affected_panels": (),
        "no_presentation": True,
    }


def _inventory_use_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Reauthorize one member and delegate its item use to the member rule.

    During an active combat session the request rejects before any member or
    target resolution: a party session's items are actor-scoped draft entries,
    so only the guarded ``combat.command`` path may save one member's item
    selection. In exploration ``actor_id`` is reauthorized for the acting
    purpose, so a forged, absent, or knocked-out member rejects with the shared
    party code and the authenticated actor is never used in its place; the item
    is then consumed from that member's own bag, SELF effects bind to it, and
    the canonical six-second cost settles the present party. Success always
    publishes a full snapshot (empty affected-panel set).

    An optional ``target_key`` names whom a single-scope effect reaches; it is
    resolved relative to the member's own room, never changes what the item
    does, and a self-scoped item ignores it exactly as the rulebook's scopes
    dictate.
    """
    del session
    if party_in_combat(actor):
        # Deliberately before target resolution: an in-combat request must not
        # resolve, consume, mutate or advance anything. The party-wide check
        # also covers a session persisted under the actor's commander.
        return _session_rejected(SessionReason.COMBAT_ITEM_COMMAND_REQUIRED)
    item_key = payload["item_key"]
    try:
        member = authorize_member(
            resolve_commander(actor),
            payload["actor_id"],
            PURPOSE_ACT,
            anchor=actor,
        )
        target = (
            _resolve_inventory_target(member, payload["target_key"])
            if "target_key" in payload
            else None
        )
        outcome = use_member_item(actor, payload["actor_id"], item_key, target=target)
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    result = outcome.settlement.result
    if result.outcome != "success":
        return _rejected(result.reason)
    message = render_plain_text(result.event_log)
    actor.msg(message)
    # The committed use settles the present party's advance; a booked-practice
    # unlock that advance staged is delivered here (this adapter renders no
    # notification lines, so the line is new).
    deliver_unlocks(actor, notices_from_events(outcome.settlement.events))
    return _success("item_used", message, ())


def _inventory_toggle_equip_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]:
    """Delegate one member's ownership-aware equipment toggle (a free action).

    ``actor_id`` is reauthorized by the party member boundary: a forged or
    absent member reference rejects with the shared party code and the
    commander is never toggled in its place. The toggle stays free in
    exploration and in combat, and its existing draft-preview invalidation
    applies to the re-equipped member.
    """
    del session
    item_key = payload["item_key"]
    try:
        outcome = toggle_member_equipment(actor, payload["actor_id"], item_key)
    except PartyScopeError as error:
        return {
            "outcome": "rejected",
            "code": error.reason,
            "message": error.message,
        }
    result = outcome.result
    if result.outcome != "success":
        return _rejected(result.reason)
    subject = "你" if outcome.member is actor else str(outcome.member.key)
    message = toggle_equipment_message(result, item_key, subject)
    actor.msg(message)
    return _success("equipment_toggled", message, ())


__all__ = [
    "REASON_ABANDON_SHAPE",
    "ServiceActionError",
    "validate_buy_payload",
    "validate_exam_request_payload",
    "validate_guild_register_payload",
    "validate_inventory_toggle_equip_payload",
    "validate_inventory_use_payload",
    "validate_quest_abandon_payload",
    "validate_quest_accept_payload",
    "validate_quest_track_payload",
    "validate_quest_turnin_payload",
    "validate_sell_payload",
    "validate_services_open_payload",
]
