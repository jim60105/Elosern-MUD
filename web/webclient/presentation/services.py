"""Exact schema-version-4 ``services`` panel and presenter (webclient-service-menus).

The presenter serializes the frozen no-mutation services view owned by
``world.rules.service_view`` and validates its own output against the exact
bounded schema (design D4) before returning it to the presentation registry.
Outside exploration mode, or when a global prerequisite (world clock or player
summary) cannot be read without mutation, it raises
:class:`PanelUnavailableError` so the registry emits the common unavailable
form; a failure confined to one surface is serialized as that surface's
``null`` while the rest of the panel stays available.

The payload shape and the exact shared bounds are mirrored by the client
validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded by a
dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    _validate_message,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.service_view import (
    ActionDescriptorView,
    BoardRowView,
    GuildSectionView,
    InventoryRowView,
    InventorySectionView,
    PlayerSummaryView,
    QuestRowView,
    RankView,
    RegistrationView,
    SellableRowView,
    ServicesView,
    ServicesViewError,
    ShopSectionView,
    StockRowView,
    build_services_view,
)

SERVICES_SCHEMA_VERSION = 4

# Exact shared bounds (design D4) -- must stay equal in the JS validator.
MAX_BOARD_ROWS = 12
MAX_QUEST_ROWS = 12
MAX_STOCK_ROWS = 12
MAX_SELLABLE_ROWS = 12
MAX_INVENTORY_ROWS = 32
MAX_KEY_CODE_POINTS = 64
MAX_DISPLAY_NAME_CODE_POINTS = 128
MAX_SUMMARY_CODE_POINTS = 128
MAX_DETAIL_CODE_POINTS = 512
MAX_DEADLINE_LINE_CODE_POINTS = 64
MAX_RANK_KEY_CODE_POINTS = 8
MAX_HOST_DISPLAY_NAME_CODE_POINTS = 256
MAX_LABEL_CODE_POINTS = 64
MAX_REASON_MESSAGE_CODE_POINTS = 128
MAX_QUANTITY = 1000
MIN_QUANTITY = 1
MAX_PRESENTATION_KEY_CODE_POINTS = 32
MAX_PRESENTATION_SUMMARY_CODE_POINTS = 240

QUEST_STATES = frozenset({"in_progress", "completed", "failed"})
REGISTER_ACTION = "guild.register"
ACCEPT_ACTION = "guild.quest_accept"
ABANDON_ACTION = "guild.quest_abandon"
TURNIN_ACTION = "guild.quest_turnin"
TRACK_ACTION = "guild.quest_track"
EXAM_ACTION = "guild.exam_start"
BUY_ACTION = "shop.buy"
SELL_ACTION = "shop.sell"
INVENTORY_USE_ACTION = "inventory.use"
INVENTORY_TOGGLE_ACTION = "inventory.toggle_equip"
_SERVICE_ACTIONS = frozenset(
    {
        REGISTER_ACTION,
        ACCEPT_ACTION,
        ABANDON_ACTION,
        TURNIN_ACTION,
        TRACK_ACTION,
        EXAM_ACTION,
        BUY_ACTION,
        SELL_ACTION,
        INVENTORY_USE_ACTION,
        INVENTORY_TOGGLE_ACTION,
    }
)


class ServicesPanelError(ProtocolValidationError):
    """The available services payload violates its exact bounded schema."""


def _validate_action_id(value: Any, field: str) -> str:
    validated = _validate_identifier(value, field)
    if len(validated) > MAX_KEY_CODE_POINTS:
        raise ProtocolValidationError(f"{field} exceeds its bound")
    return validated


def _validate_host_identity(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_KEY_CODE_POINTS:
        raise ProtocolValidationError(
            "host.identity must be 1..64 opaque ASCII characters"
        )
    if not value.isascii():
        raise ProtocolValidationError("host.identity must be ASCII")
    return value


def _validate_action(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "service action",
        {"action_id", "label", "enabled", "disabled_reason", "quantity"},
        {},
    )
    action_id = _validate_action_id(value["action_id"], "action_id")
    if action_id not in _SERVICE_ACTIONS:
        raise ProtocolValidationError(
            "action_id is not a registered service action"
        )
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("action label must be non-empty")
    enabled = _require_bool(value, "enabled")
    disabled_reason = value["disabled_reason"]
    if disabled_reason is None:
        if not enabled:
            raise ProtocolValidationError("a disabled action requires a disabled_reason")
    else:
        _require_exact_fields(
            disabled_reason, "disabled_reason", {"code", "message"}, {}
        )
        _validate_action_id(disabled_reason["code"], "disabled_reason code")
        message = _require_str(
            disabled_reason, "message", maximum=MAX_REASON_MESSAGE_CODE_POINTS
        )
        if not message.strip():
            raise ProtocolValidationError("disabled_reason message must be non-empty")
        if enabled:
            raise ProtocolValidationError("an enabled action must not carry a disabled_reason")
    quantity = value["quantity"]
    if quantity is None:
        if enabled and action_id in (BUY_ACTION, SELL_ACTION):
            raise ProtocolValidationError("a buy/sell action requires quantity bounds")
    else:
        if action_id not in (BUY_ACTION, SELL_ACTION):
            raise ProtocolValidationError("only buy/sell actions may carry quantity bounds")
        _require_exact_fields(quantity, "quantity bounds", {"min", "max"}, {})
        minimum = _require_int(
            quantity, "min", minimum=MIN_QUANTITY, maximum=MAX_QUANTITY
        )
        maximum = _require_int(
            quantity, "max", minimum=MIN_QUANTITY, maximum=MAX_QUANTITY
        )
        if minimum > maximum:
            raise ProtocolValidationError("quantity min must not exceed max")
    return {
        "action_id": action_id,
        "label": label,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "quantity": quantity,
    }


def _validate_registration(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "registration", {"registered", "register"}, {})
    registered = _require_bool(value, "registered")
    register = _validate_action(value["register"])
    if register["action_id"] != REGISTER_ACTION:
        raise ProtocolValidationError("registration.register must be guild.register")
    if registered == register["enabled"]:
        raise ProtocolValidationError(
            "registration.register enabled state must contradict registered"
        )
    return {"registered": registered, "register": register}


def _validate_board_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "board row",
        {
            "definition_key",
            "display_name",
            "objective_summary",
            "reward_summary",
            "rank",
            "accept",
        },
        {},
    )
    definition_key = _require_str(
        value, "definition_key", maximum=MAX_KEY_CODE_POINTS
    )
    if not definition_key.strip():
        raise ProtocolValidationError("board definition_key must be non-empty")
    display_name = _require_str(
        value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
    )
    if not display_name.strip():
        raise ProtocolValidationError("board display_name must be non-empty")
    objective_summary = _require_str(
        value, "objective_summary", maximum=MAX_SUMMARY_CODE_POINTS
    )
    reward_summary = _require_str(
        value, "reward_summary", maximum=MAX_SUMMARY_CODE_POINTS
    )
    if not objective_summary.strip() or not reward_summary.strip():
        raise ProtocolValidationError("board summaries must be non-empty")
    rank = _require_str(value, "rank", maximum=MAX_RANK_KEY_CODE_POINTS)
    if not rank.strip():
        raise ProtocolValidationError("board rank must be non-empty")
    accept = _validate_action(value["accept"])
    if accept["action_id"] != ACCEPT_ACTION:
        raise ProtocolValidationError("board accept must be guild.quest_accept")
    return {
        "definition_key": definition_key,
        "display_name": display_name,
        "objective_summary": objective_summary,
        "reward_summary": reward_summary,
        "rank": rank,
        "accept": accept,
    }


def _validate_quest_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "quest row",
        {
            "quest_id",
            "definition_key",
            "display_name",
            "state",
            "stage_index",
            "stage_progress",
            "objective_summary",
            "deadline_line",
            "detail",
            "abandon",
            "turnin",
            "tracked",
        },
        {},
    )
    quest_id = _require_str(value, "quest_id", maximum=MAX_KEY_CODE_POINTS)
    if not quest_id.strip():
        raise ProtocolValidationError("quest_id must be non-empty")
    definition_key = _require_str(
        value, "definition_key", maximum=MAX_KEY_CODE_POINTS
    )
    display_name = _require_str(
        value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
    )
    state = value["state"]
    if state not in QUEST_STATES:
        raise ProtocolValidationError("quest state is not a stable value")
    stage_index = _require_int(value, "stage_index", minimum=0, maximum=MAX_SAFE_INTEGER)
    stage_progress = _require_int(value, "stage_progress", minimum=0, maximum=MAX_SAFE_INTEGER)
    objective_summary = _require_str(
        value, "objective_summary", maximum=MAX_SUMMARY_CODE_POINTS
    )
    deadline_line = value["deadline_line"]
    if deadline_line is not None:
        deadline_line = _require_str(
            value, "deadline_line", maximum=MAX_DEADLINE_LINE_CODE_POINTS
        )
        if not deadline_line.strip():
            raise ProtocolValidationError("deadline_line must be non-empty when set")
    detail = _require_str(value, "detail", maximum=MAX_DETAIL_CODE_POINTS)
    if not detail.strip():
        raise ProtocolValidationError("quest detail must be non-empty")
    abandon = _validate_action(value["abandon"])
    turnin = _validate_action(value["turnin"])
    if abandon["action_id"] != ABANDON_ACTION:
        raise ProtocolValidationError("quest abandon must be guild.quest_abandon")
    if turnin["action_id"] != TURNIN_ACTION:
        raise ProtocolValidationError("quest turnin must be guild.quest_turnin")
    tracked = _require_bool(value, "tracked")
    return {
        "quest_id": quest_id,
        "definition_key": definition_key,
        "display_name": display_name,
        "state": state,
        "stage_index": stage_index,
        "stage_progress": stage_progress,
        "objective_summary": objective_summary,
        "deadline_line": deadline_line,
        "detail": detail,
        "abandon": abandon,
        "turnin": turnin,
        "tracked": tracked,
    }


def _validate_rank(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "rank",
        {"rank", "merit", "next_rank", "next_threshold", "eligible", "exam_start"},
        {},
    )
    rank = value["rank"]
    if rank is not None:
        rank = _require_str(value, "rank", maximum=MAX_RANK_KEY_CODE_POINTS)
        if not rank.strip():
            raise ProtocolValidationError("rank must be non-empty when set")
    merit = _require_int(value, "merit", minimum=0, maximum=MAX_SAFE_INTEGER)
    next_rank = value["next_rank"]
    if next_rank is not None:
        next_rank = _require_str(value, "next_rank", maximum=MAX_RANK_KEY_CODE_POINTS)
    next_threshold = value["next_threshold"]
    if next_threshold is not None:
        _require_int(value, "next_threshold", minimum=1, maximum=MAX_SAFE_INTEGER)
    if (next_rank is None) != (next_threshold is None):
        raise ProtocolValidationError("next_rank and next_threshold must both be set or null")
    eligible = _require_bool(value, "eligible")
    exam_start = _validate_action(value["exam_start"])
    if exam_start["action_id"] != EXAM_ACTION:
        raise ProtocolValidationError("rank exam_start must be guild.exam_start")
    if eligible != exam_start["enabled"]:
        raise ProtocolValidationError("rank eligible must match exam_start enabled")
    return {
        "rank": rank,
        "merit": merit,
        "next_rank": next_rank,
        "next_threshold": next_threshold,
        "eligible": eligible,
        "exam_start": exam_start,
    }


def _validate_guild(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "guild", {"registration", "board", "quests", "rank"}, {})
    registration = _validate_registration(value["registration"])
    board = value["board"]
    if not isinstance(board, list) or len(board) > MAX_BOARD_ROWS:
        raise ProtocolValidationError(f"board must be a list of at most {MAX_BOARD_ROWS} rows")
    board = [_validate_board_row(row) for row in board]
    quests = value["quests"]
    if not isinstance(quests, list) or len(quests) > MAX_QUEST_ROWS:
        raise ProtocolValidationError(f"quests must be a list of at most {MAX_QUEST_ROWS} rows")
    quests = [_validate_quest_row(row) for row in quests]
    rank = value["rank"]
    if rank is not None:
        rank = _validate_rank(rank)
    return {"registration": registration, "board": board, "quests": quests, "rank": rank}


def _validate_stock_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "stock row",
        {"item_key", "display_name", "buy_copper", "sell_copper", "stock", "max_stock", "buy"},
        {},
    )
    item_key = _require_str(value, "item_key", maximum=MAX_KEY_CODE_POINTS)
    if not item_key.strip():
        raise ProtocolValidationError("stock item_key must be non-empty")
    display_name = _require_str(
        value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
    )
    buy_copper = _require_int(value, "buy_copper", minimum=0, maximum=MAX_SAFE_INTEGER)
    sell_copper = _require_int(value, "sell_copper", minimum=0, maximum=MAX_SAFE_INTEGER)
    stock = _require_int(value, "stock", minimum=0, maximum=MAX_SAFE_INTEGER)
    max_stock = _require_int(value, "max_stock", minimum=1, maximum=MAX_SAFE_INTEGER)
    buy = _validate_action(value["buy"])
    if buy["action_id"] != BUY_ACTION:
        raise ProtocolValidationError("stock buy must be shop.buy")
    return {
        "item_key": item_key,
        "display_name": display_name,
        "buy_copper": buy_copper,
        "sell_copper": sell_copper,
        "stock": stock,
        "max_stock": max_stock,
        "buy": buy,
    }


def _validate_sellable_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "sellable row",
        {"item_key", "display_name", "sell_copper", "held", "sell"},
        {},
    )
    item_key = _require_str(value, "item_key", maximum=MAX_KEY_CODE_POINTS)
    display_name = _require_str(
        value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
    )
    sell_copper = _require_int(value, "sell_copper", minimum=0, maximum=MAX_SAFE_INTEGER)
    held = _require_int(value, "held", minimum=1, maximum=MAX_SAFE_INTEGER)
    sell = _validate_action(value["sell"])
    if sell["action_id"] != SELL_ACTION:
        raise ProtocolValidationError("sellable sell must be shop.sell")
    return {
        "item_key": item_key,
        "display_name": display_name,
        "sell_copper": sell_copper,
        "held": held,
        "sell": sell,
    }


def _validate_shop(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "shop", {"open", "stock", "sellable"}, {})
    open_now = _require_bool(value, "open")
    stock = value["stock"]
    if not isinstance(stock, list) or len(stock) > MAX_STOCK_ROWS:
        raise ProtocolValidationError(f"stock must be a list of at most {MAX_STOCK_ROWS} rows")
    stock = [_validate_stock_row(row) for row in stock]
    sellable = value["sellable"]
    if not isinstance(sellable, list) or len(sellable) > MAX_SELLABLE_ROWS:
        raise ProtocolValidationError(
            f"sellable must be a list of at most {MAX_SELLABLE_ROWS} rows"
        )
    sellable = [_validate_sellable_row(row) for row in sellable]
    return {"open": open_now, "stock": stock, "sellable": sellable}


def _validate_presentation_identifier(value: dict[str, Any], field: str) -> str:
    key = value[field]
    if not isinstance(key, str) or not 1 <= len(key) <= MAX_PRESENTATION_KEY_CODE_POINTS:
        raise ProtocolValidationError(
            f"presentation {field} must be 1..{MAX_PRESENTATION_KEY_CODE_POINTS} characters"
        )
    if not all(ch.isascii() and (ch.islower() or ch == "_") for ch in key):
        raise ProtocolValidationError(
            f"presentation {field} must be lowercase ASCII letters or underscores"
        )
    return key


def _validate_presentation(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(
        value, "presentation", {"kind", "icon_key", "rarity", "summary"}, {}
    )
    kind = _validate_presentation_identifier(value, "kind")
    icon_key = _validate_presentation_identifier(value, "icon_key")
    rarity = _validate_presentation_identifier(value, "rarity")
    summary = value["summary"]
    if not isinstance(summary, str):
        raise ProtocolValidationError("presentation summary must be a string")
    if not 1 <= sum(1 for _ in summary) <= MAX_PRESENTATION_SUMMARY_CODE_POINTS:
        raise ProtocolValidationError(
            f"presentation summary must be 1..{MAX_PRESENTATION_SUMMARY_CODE_POINTS} Unicode code points"
        )
    return {"kind": kind, "icon_key": icon_key, "rarity": rarity, "summary": summary}


def _validate_inventory(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "inventory", {"rows", "wallet"}, {})
    rows = value["rows"]
    if not isinstance(rows, list) or len(rows) > MAX_INVENTORY_ROWS:
        raise ProtocolValidationError(
            f"inventory rows must be a list of at most {MAX_INVENTORY_ROWS} entries"
        )
    wallet = _require_int(value, "wallet", minimum=0, maximum=MAX_SAFE_INTEGER)
    row_views = []
    for row in rows:
        _require_exact_fields(
            row,
            "inventory row",
            {
                "item_key",
                "display_name",
                "held",
                "equipped",
                "presentation",
                "action",
            },
            {},
        )
        item_key = _require_str(row, "item_key", maximum=MAX_KEY_CODE_POINTS)
        display_name = _require_str(
            row, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS
        )
        held = _require_int(row, "held", minimum=1, maximum=MAX_SAFE_INTEGER)
        equipped = _require_bool(row, "equipped")
        presentation = _validate_presentation(row["presentation"])
        action = row["action"]
        if action is not None:
            action = _validate_action(action)
            if action["action_id"] not in (INVENTORY_USE_ACTION, INVENTORY_TOGGLE_ACTION):
                raise ProtocolValidationError("inventory row action id is not allowed")
        row_views.append(
            {
                "item_key": item_key,
                "display_name": display_name,
                "held": held,
                "equipped": equipped,
                "presentation": presentation,
                "action": action,
            }
        )
    return {"rows": row_views, "wallet": wallet}


def _validate_pagination(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "pagination",
        {"board_total", "quest_total", "stock_total", "sellable_total", "inventory_total"},
        {},
    )
    totals = {}
    for field, ceiling in (
        ("board_total", MAX_BOARD_ROWS),
        ("quest_total", MAX_QUEST_ROWS),
        ("stock_total", MAX_STOCK_ROWS),
        ("sellable_total", MAX_SELLABLE_ROWS),
        ("inventory_total", MAX_INVENTORY_ROWS),
    ):
        totals[field] = _require_int(value, field, minimum=0, maximum=ceiling)
    return totals


def validate_services(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``services`` payload.

    Returns a normalized payload or raises :class:`ServicesPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "services panel",
        {
            "schema_version",
            "available",
            "kind",
            "host",
            "player",
            "guild",
            "shop",
            "inventory",
            "pagination",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != SERVICES_SCHEMA_VERSION:
        raise ServicesPanelError("unsupported services schema_version")
    if not _require_bool(payload, "available"):
        raise ServicesPanelError("available must be true for the services form")
    if payload["kind"] != "services":
        raise ServicesPanelError("services panel kind must be services")

    host = payload["host"]
    if host is not None:
        _require_exact_fields(host, "host", {"identity", "display_name"}, {})
        identity = _validate_host_identity(host["identity"])
        display_name = _require_str(
            host, "display_name", maximum=MAX_HOST_DISPLAY_NAME_CODE_POINTS
        )
        if not display_name.strip():
            raise ProtocolValidationError("host display_name must be non-empty")
    player = payload["player"]
    _require_exact_fields(
        player,
        "player",
        {"wallet", "guild_registered", "guild_rank", "guild_merit", "next_rank", "next_threshold"},
        {},
    )
    wallet = _require_int(player, "wallet", minimum=0, maximum=MAX_SAFE_INTEGER)
    guild_registered = _require_bool(player, "guild_registered")
    guild_rank = player["guild_rank"]
    if guild_rank is not None:
        guild_rank = _require_str(player, "guild_rank", maximum=MAX_RANK_KEY_CODE_POINTS)
        if not guild_rank.strip():
            raise ProtocolValidationError("guild_rank must be non-empty when set")
    guild_merit = _require_int(player, "guild_merit", minimum=0, maximum=MAX_SAFE_INTEGER)
    next_rank = player["next_rank"]
    if next_rank is not None:
        next_rank = _require_str(player, "next_rank", maximum=MAX_RANK_KEY_CODE_POINTS)
    next_threshold = player["next_threshold"]
    if next_threshold is not None:
        _require_int(player, "next_threshold", minimum=1, maximum=MAX_SAFE_INTEGER)
    if (next_rank is None) != (next_threshold is None):
        raise ProtocolValidationError(
            "player next_rank and next_threshold must both be set or null"
        )
    if guild_rank is None and guild_registered:
        raise ProtocolValidationError(
            "an unregistered player must not carry a guild rank in the summary"
        )

    guild = None if payload["guild"] is None else _validate_guild(payload["guild"])
    shop = None if payload["shop"] is None else _validate_shop(payload["shop"])
    inventory = (
        None if payload["inventory"] is None else _validate_inventory(payload["inventory"])
    )
    pagination = _validate_pagination(payload["pagination"])
    _validate_pagination_totals(pagination, guild, shop, inventory)

    result = {
        "schema_version": SERVICES_SCHEMA_VERSION,
        "available": True,
        "kind": "services",
        "host": host,
        "player": {
            "wallet": wallet,
            "guild_registered": guild_registered,
            "guild_rank": guild_rank,
            "guild_merit": guild_merit,
            "next_rank": next_rank,
            "next_threshold": next_threshold,
        },
        "guild": guild,
        "shop": shop,
        "inventory": inventory,
        "pagination": pagination,
    }
    # Envelope guarantee (design D4): a conforming payload must serialize within
    # the OOB envelope limit. Per-field bounds are ceilings, not a guarantee
    # that any combination of them fits, so the validator enforces the
    # serialized size directly -- an all-ceilings payload fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ServicesPanelError("services payload exceeds the OOB envelope limit")
    return result


def _validate_pagination_totals(
    pagination: dict[str, Any],
    guild: dict[str, Any] | None,
    shop: dict[str, Any] | None,
    inventory: dict[str, Any] | None,
) -> None:
    if guild is None:
        if pagination["board_total"] != 0 or pagination["quest_total"] != 0:
            raise ProtocolValidationError(
                "pagination board/quest totals must be zero when guild is null"
            )
    else:
        if pagination["board_total"] != len(guild["board"]):
            raise ProtocolValidationError("pagination board_total must match shipped rows")
        if pagination["quest_total"] != len(guild["quests"]):
            raise ProtocolValidationError("pagination quest_total must match shipped rows")
    if shop is None:
        if pagination["stock_total"] != 0 or pagination["sellable_total"] != 0:
            raise ProtocolValidationError(
                "pagination stock/sellable totals must be zero when shop is null"
            )
    else:
        if pagination["stock_total"] != len(shop["stock"]):
            raise ProtocolValidationError("pagination stock_total must match shipped rows")
        if pagination["sellable_total"] != len(shop["sellable"]):
            raise ProtocolValidationError("pagination sellable_total must match shipped rows")
    if inventory is None:
        if pagination["inventory_total"] != 0:
            raise ProtocolValidationError(
                "pagination inventory_total must be zero when inventory is null"
            )
    else:
        if pagination["inventory_total"] != len(inventory["rows"]):
            raise ProtocolValidationError(
                "pagination inventory_total must match shipped rows"
            )


# ---------------------------------------------------------------------------
# Serialization from the frozen read model.
# ---------------------------------------------------------------------------


def _serialize_action(action: ActionDescriptorView) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "label": action.label,
        "enabled": action.enabled,
        "disabled_reason": (
            None
            if action.reason_code is None
            else {"code": action.reason_code, "message": action.reason_message}
        ),
        "quantity": (
            None
            if action.quantity_min is None
            else {"min": action.quantity_min, "max": action.quantity_max}
        ),
    }


def _serialize_registration(registration: RegistrationView) -> dict[str, Any]:
    return {
        "registered": registration.registered,
        "register": _serialize_action(registration.register),
    }


def _serialize_board_row(row: BoardRowView) -> dict[str, Any]:
    return {
        "definition_key": row.definition_key,
        "display_name": row.display_name,
        "objective_summary": row.objective_summary,
        "reward_summary": row.reward_summary,
        "rank": row.rank,
        "accept": _serialize_action(row.accept),
    }


def _serialize_quest_row(row: QuestRowView) -> dict[str, Any]:
    return {
        "quest_id": row.quest_id,
        "definition_key": row.definition_key,
        "display_name": row.display_name,
        "state": row.state,
        "stage_index": row.stage_index,
        "stage_progress": row.stage_progress,
        "objective_summary": row.objective_summary,
        "deadline_line": row.deadline_line,
        "detail": row.detail,
        "abandon": _serialize_action(row.abandon),
        "turnin": _serialize_action(row.turnin),
        "tracked": row.tracked,
    }


def _serialize_rank(rank: RankView) -> dict[str, Any]:
    return {
        "rank": rank.rank,
        "merit": rank.merit,
        "next_rank": rank.next_rank,
        "next_threshold": rank.next_threshold,
        "eligible": rank.eligible,
        "exam_start": _serialize_action(rank.exam_start),
    }


def _serialize_guild(guild: GuildSectionView) -> dict[str, Any]:
    return {
        "registration": _serialize_registration(guild.registration),
        "board": [_serialize_board_row(row) for row in guild.board],
        "quests": [_serialize_quest_row(row) for row in guild.quests],
        "rank": None if guild.rank is None else _serialize_rank(guild.rank),
    }


def _serialize_stock_row(row: StockRowView) -> dict[str, Any]:
    return {
        "item_key": row.item_key,
        "display_name": row.display_name,
        "buy_copper": row.buy_copper,
        "sell_copper": row.sell_copper,
        "stock": row.stock,
        "max_stock": row.max_stock,
        "buy": _serialize_action(row.buy),
    }


def _serialize_sellable_row(row: SellableRowView) -> dict[str, Any]:
    return {
        "item_key": row.item_key,
        "display_name": row.display_name,
        "sell_copper": row.sell_copper,
        "held": row.held,
        "sell": _serialize_action(row.sell),
    }


def _serialize_shop(shop: ShopSectionView) -> dict[str, Any]:
    return {
        "open": shop.open,
        "stock": [_serialize_stock_row(row) for row in shop.stock],
        "sellable": [_serialize_sellable_row(row) for row in shop.sellable],
    }


def _serialize_presentation(row: InventoryRowView) -> dict[str, Any] | None:
    if row.presentation is None:
        return None
    return {
        "kind": row.presentation.kind.value,
        "icon_key": row.presentation.icon_key.value,
        "rarity": row.presentation.rarity.value,
        "summary": row.presentation.summary_zh,
    }


def _serialize_inventory(inventory: InventorySectionView) -> dict[str, Any]:
    return {
        "rows": [
            {
                "item_key": row.item_key,
                "display_name": row.display_name,
                "held": row.held,
                "equipped": row.equipped,
                "presentation": _serialize_presentation(row),
                "action": (
                    None
                    if row.action is None
                    else _serialize_action(row.action)
                ),
            }
            for row in inventory.rows
        ],
        "wallet": inventory.wallet,
    }


def _serialize_player(player: PlayerSummaryView) -> dict[str, Any]:
    return {
        "wallet": player.wallet,
        "guild_registered": player.guild_registered,
        "guild_rank": player.guild_rank,
        "guild_merit": player.guild_merit,
        "next_rank": player.next_rank,
        "next_threshold": player.next_threshold,
    }


def _serialize(view: ServicesView) -> dict[str, Any]:
    return {
        "schema_version": SERVICES_SCHEMA_VERSION,
        "available": True,
        "kind": "services",
        "host": (
            None
            if view.host is None
            else {"identity": view.host.identity, "display_name": view.host.display_name}
        ),
        "player": _serialize_player(view.player),
        "guild": None if view.guild is None else _serialize_guild(view.guild),
        "shop": None if view.shop is None else _serialize_shop(view.shop),
        "inventory": (
            None if view.inventory is None else _serialize_inventory(view.inventory)
        ),
        "pagination": {
            "board_total": view.pagination.board_total,
            "quest_total": view.pagination.quest_total,
            "stock_total": view.pagination.stock_total,
            "sellable_total": view.pagination.sellable_total,
            "inventory_total": view.pagination.inventory_total,
        },
    }


def services_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``services`` panel for the authenticated puppet.

    Exploration mode ships every surface normally; an active combat session
    keeps the canonical player and personal inventory data while the
    read model itself forces host, guild, and shop null. Creation-pending
    puppets and read-model failures use the common unavailable form.
    """
    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    try:
        view = build_services_view(actor)
    except ServicesViewError:
        raise PanelUnavailableError
    return validate_services(_serialize(view))


__all__ = [
    "ABANDON_ACTION",
    "ACCEPT_ACTION",
    "BUY_ACTION",
    "EXAM_ACTION",
    "INVENTORY_TOGGLE_ACTION",
    "INVENTORY_USE_ACTION",
    "MAX_BOARD_ROWS",
    "MAX_DETAIL_CODE_POINTS",
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_HOST_DISPLAY_NAME_CODE_POINTS",
    "MAX_INVENTORY_ROWS",
    "MAX_KEY_CODE_POINTS",
    "MAX_LABEL_CODE_POINTS",
    "MAX_QUEST_ROWS",
    "MAX_PRESENTATION_KEY_CODE_POINTS",
    "MAX_PRESENTATION_SUMMARY_CODE_POINTS",
    "MAX_QUANTITY",
    "MAX_RANK_KEY_CODE_POINTS",
    "MAX_REASON_MESSAGE_CODE_POINTS",
    "MAX_SELLABLE_ROWS",
    "MAX_STOCK_ROWS",
    "MAX_SUMMARY_CODE_POINTS",
    "MIN_QUANTITY",
    "QUEST_STATES",
    "REGISTER_ACTION",
    "SELL_ACTION",
    "SERVICES_SCHEMA_VERSION",
    "ServicesPanelError",
    "TRACK_ACTION",
    "TURNIN_ACTION",
    "services_presenter",
    "validate_services",
]
