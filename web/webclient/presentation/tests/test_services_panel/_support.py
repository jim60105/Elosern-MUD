"""Shared module-level helpers for the ``services_panel`` test package."""
from web.webclient.presentation.services import MAX_BOARD_ROWS, MAX_DETAIL_CODE_POINTS, MAX_DISPLAY_NAME_CODE_POINTS, MAX_HOST_DISPLAY_NAME_CODE_POINTS, MAX_INVENTORY_ROWS, MAX_KEY_CODE_POINTS, MAX_LABEL_CODE_POINTS, MAX_QUEST_ROWS, MAX_PRESENTATION_KEY_CODE_POINTS, MAX_PRESENTATION_SUMMARY_CODE_POINTS, MAX_RANK_KEY_CODE_POINTS, MAX_REASON_MESSAGE_CODE_POINTS, MAX_SELLABLE_ROWS, MAX_STOCK_ROWS, MAX_SUMMARY_CODE_POINTS, SERVICES_SCHEMA_VERSION
from world.quests.tests._fixtures import quest, register_catalog_once
from world.rules.tests._guild_service_probes import synthetic_branch_key
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS


# The shipped affinity rulebook cross-references one catalog quest by key, so
# the affinity-config loader needs the catalog definitions present in-process.
# Registered at import (no synthetic scope is open yet).
register_catalog_once()


# Kit identities: the kit branch for the guild hosts, one synthetic shop
# config over kit items for the store, and kit items in the actor's pockets.
BRANCH = synthetic_branch_key()


# The kit's one shop identity, named explicitly (never first-row-order).
T_SHOP = "t_mossgate_stall"


assert T_SHOP in SYNTH_SHOPS, "kit shop identity moved"


_T_SPRAY = SYNTH_ITEMS["t_ember_spray"].key


_T_THORN = SYNTH_ITEMS["t_thorn_knife"].key


# File-local synthetic inventory rows for the pure validator fixtures —
# invented item keys and invented display prose, never shipped catalog data.
_T_MEAL = "t_panel_meal"


_T_MEAL_DISPLAY = "合成餐食"


UNREGISTERED_PLAYER = {
    "wallet": 0,
    "guild_registered": False,
    "guild_rank": None,
    "guild_merit": 0,
    "next_rank": None,
    "next_threshold": None,
}


def _action(action_id="guild.register", enabled=True, **overrides):
    value = {
        "action_id": action_id,
        "label": "測試動作",
        "enabled": enabled,
        "disabled_reason": None if enabled else {"code": "closed", "message": "測試原因"},
        "quantity": None,
    }
    value.update(overrides)
    return value


def _valid_payload(**overrides):
    value = {
        "schema_version": SERVICES_SCHEMA_VERSION,
        "available": True,
        "kind": "services",
        "host": None,
        "player": dict(UNREGISTERED_PLAYER),
        "guild": None,
        "shop": None,
        "inventory": {
            "rows": [
                {
                    "item_key": _T_MEAL,
                    "display_name": _T_MEAL_DISPLAY,
                    "held": 1,
                    "equipped": False,
                    "action": None,
                    "presentation": {
                        "kind": "food",
                        "icon_key": "food",
                        "rarity": "common",
                        "summary": "供旅人充飢的普通餐食。",
                    },
                }
            ],
            "wallet": 0,
        },
        "pagination": {
            "board_total": 0,
            "quest_total": 0,
            "stock_total": 0,
            "sellable_total": 0,
            "inventory_total": 1,
        },
    }
    value.update(overrides)
    return value


def _valid_guild(**overrides):
    value = {
        "registration": {"registered": True, "register": _action(enabled=False)},
        "board": [
            {
                "definition_key": "introductory_hunt",
                "display_name": "討伐低階魔物",
                "objective_summary": "討伐 1 隻低階魔物",
                "reward_summary": "獎勵：銅 50、功績 25、治療藥水 × 2",
                "rank": "F",
                "accept": _action("guild.quest_accept"),
            }
        ],
        "quests": [],
        "rank": None,
    }
    value.update(overrides)
    return value


def _valid_shop(**overrides):
    value = {
        "open": True,
        "stock": [
            {
                "item_key": _T_MEAL,
                "display_name": _T_MEAL_DISPLAY,
                "buy_copper": 10,
                "sell_copper": 5,
                "stock": 20,
                "max_stock": 20,
                "buy": _action(
                    "shop.buy",
                    quantity={"min": 1, "max": 20},
                ),
            }
        ],
        "sellable": [],
    }
    value.update(overrides)
    return value


def _max_string(length):
    return "獎" * length


def _all_ceilings_payload():
    """Every string field at its bound and every row list at its ceiling."""
    board = [
        {
            "definition_key": _max_string(MAX_KEY_CODE_POINTS),
            "display_name": _max_string(MAX_DISPLAY_NAME_CODE_POINTS),
            "objective_summary": _max_string(MAX_SUMMARY_CODE_POINTS),
            "reward_summary": _max_string(MAX_SUMMARY_CODE_POINTS),
            "rank": _max_string(MAX_RANK_KEY_CODE_POINTS),
            "accept": _action(
                "guild.quest_accept",
                label=_max_string(MAX_LABEL_CODE_POINTS),
            ),
        }
        for _ in range(MAX_BOARD_ROWS)
    ]
    quest = [
        {
            "quest_id": _max_string(MAX_KEY_CODE_POINTS),
            "definition_key": _max_string(MAX_KEY_CODE_POINTS),
            "display_name": _max_string(MAX_DISPLAY_NAME_CODE_POINTS),
            "state": "in_progress",
            "stage_index": 0,
            "stage_progress": 0,
            "objective_summary": _max_string(MAX_SUMMARY_CODE_POINTS),
            "deadline_line": _max_string(64),
            "detail": _max_string(MAX_DETAIL_CODE_POINTS),
            "abandon": _action("guild.quest_abandon"),
            "turnin": _action("guild.quest_turnin", enabled=False),
            "tracked": False,
        }
        for _ in range(MAX_QUEST_ROWS)
    ]
    stock = [
        {
            "item_key": _max_string(MAX_KEY_CODE_POINTS),
            "display_name": _max_string(MAX_DISPLAY_NAME_CODE_POINTS),
            "buy_copper": 10,
            "sell_copper": 5,
            "stock": 20,
            "max_stock": 20,
            "buy": _action(
                "shop.buy",
                label=_max_string(MAX_LABEL_CODE_POINTS),
                enabled=False,
                disabled_reason={
                    "code": "insufficient_stock",
                    "message": _max_string(MAX_REASON_MESSAGE_CODE_POINTS),
                },
            ),
        }
        for _ in range(MAX_STOCK_ROWS)
    ]
    sellable = [
        {
            "item_key": _max_string(MAX_KEY_CODE_POINTS),
            "display_name": _max_string(MAX_DISPLAY_NAME_CODE_POINTS),
            "sell_copper": 5,
            "held": 20,
            "sell": _action(
                "shop.sell",
                label=_max_string(MAX_LABEL_CODE_POINTS),
                enabled=False,
                disabled_reason={
                    "code": "stock_overflow",
                    "message": _max_string(MAX_REASON_MESSAGE_CODE_POINTS),
                },
            ),
        }
        for _ in range(MAX_SELLABLE_ROWS)
    ]
    inventory = [
        {
            "item_key": _max_string(MAX_KEY_CODE_POINTS),
            "display_name": _max_string(MAX_DISPLAY_NAME_CODE_POINTS),
            "held": 20,
            "equipped": False,
            "action": None,
            "presentation": {
                "kind": "k" * MAX_PRESENTATION_KEY_CODE_POINTS,
                "icon_key": "i" * MAX_PRESENTATION_KEY_CODE_POINTS,
                "rarity": "r" * MAX_PRESENTATION_KEY_CODE_POINTS,
                "summary": "獎" * MAX_PRESENTATION_SUMMARY_CODE_POINTS,
            },
        }
        for _ in range(MAX_INVENTORY_ROWS)
    ]
    return _valid_payload(
        host={"identity": "1" * MAX_KEY_CODE_POINTS, "display_name": _max_string(MAX_HOST_DISPLAY_NAME_CODE_POINTS)},
        player={
            "wallet": 0,
            "guild_registered": True,
            "guild_rank": _max_string(MAX_RANK_KEY_CODE_POINTS),
            "guild_merit": 0,
            "next_rank": _max_string(MAX_RANK_KEY_CODE_POINTS),
            "next_threshold": 1,
        },
        guild={
            "registration": {
                "registered": True,
                "register": _action(
                    "guild.register",
                    enabled=False,
                    disabled_reason={
                        "code": "already_registered",
                        "message": _max_string(MAX_REASON_MESSAGE_CODE_POINTS),
                    },
                ),
            },
            "board": board,
            "quests": quest,
            "rank": {
                "rank": _max_string(MAX_RANK_KEY_CODE_POINTS),
                "merit": 0,
                "next_rank": _max_string(MAX_RANK_KEY_CODE_POINTS),
                "next_threshold": 1,
                "eligible": False,
                "exam_start": _action(
                    "guild.exam_start",
                    enabled=False,
                    disabled_reason={
                        "code": "below_threshold",
                        "message": _max_string(MAX_REASON_MESSAGE_CODE_POINTS),
                    },
                ),
            },
        },
        shop={"open": False, "stock": stock, "sellable": sellable},
        inventory={"rows": inventory, "wallet": 0},
        pagination={
            "board_total": MAX_BOARD_ROWS,
            "quest_total": MAX_QUEST_ROWS,
            "stock_total": MAX_STOCK_ROWS,
            "sellable_total": MAX_SELLABLE_ROWS,
            "inventory_total": MAX_INVENTORY_ROWS,
        },
    )


def _realistic_maximal_payload():
    """Every row list at its ceiling with realistic bounded content."""
    board = [
        {
            "definition_key": f"quest_key_{index}",
            "display_name": "討伐低階魔物",
            "objective_summary": "討伐 1 隻低階魔物",
            "reward_summary": "獎勵：銅 50、功績 25、治療藥水 × 2",
            "rank": "F",
            "accept": _action("guild.quest_accept", label="接取"),
        }
        for index in range(MAX_BOARD_ROWS)
    ]
    quest = [
        {
            "quest_id": f"introductory_hunt:{index + 1}",
            "definition_key": "introductory_hunt",
            "display_name": "討伐低階魔物",
            "state": "in_progress",
            "stage_index": 0,
            "stage_progress": 0,
            "objective_summary": "討伐 1 隻低階魔物",
            "deadline_line": "期限：剩餘 3 小時",
            "detail": "討伐低階魔物\n狀態：進行中\n階段：1\n目標：討伐 1 隻低階魔物\n進度：0 / 1\n獎勵：銅 50、功績 25、治療藥水 × 2",
            "abandon": _action("guild.quest_abandon", label="放棄"),
            "turnin": _action("guild.quest_turnin", label="回報", enabled=False),
            "tracked": False,
        }
        for index in range(MAX_QUEST_ROWS)
    ]
    stock = [
        {
            "item_key": _T_MEAL,
            "display_name": _T_MEAL_DISPLAY,
            "buy_copper": 10,
            "sell_copper": 5,
            "stock": 20,
            "max_stock": 20,
            "buy": _action("shop.buy", label="購買", quantity={"min": 1, "max": 20}),
        }
        for _ in range(MAX_STOCK_ROWS)
    ]
    sellable = [
        {
            "item_key": _T_MEAL,
            "display_name": _T_MEAL_DISPLAY,
            "sell_copper": 5,
            "held": 20,
            "sell": _action("shop.sell", label="販賣", quantity={"min": 1, "max": 20}),
        }
        for _ in range(MAX_SELLABLE_ROWS)
    ]
    inventory = [
        {
            "item_key": _T_MEAL,
            "display_name": _T_MEAL_DISPLAY,
            "held": 2,
            "equipped": False,
            "action": None,
            "presentation": {
                "kind": "food",
                "icon_key": "food",
                "rarity": "common",
                "summary": "供旅人充飢的普通餐食。",
            },
        }
        for _ in range(MAX_INVENTORY_ROWS)
    ]
    return _valid_payload(
        host={"identity": "12345", "display_name": "合成公會測試分行"},
        player={
            "wallet": 1000000,
            "guild_registered": True,
            "guild_rank": "F",
            "guild_merit": 60,
            "next_rank": "E",
            "next_threshold": 50,
        },
        guild={
            "registration": {
                "registered": True,
                "register": _action(
                    "guild.register",
                    label="註冊為冒險者",
                    enabled=False,
                    disabled_reason={
                        "code": "already_registered",
                        "message": "你已經是冒險者了。",
                    },
                ),
            },
            "board": board,
            "quests": quest,
            "rank": {
                "rank": "F",
                "merit": 60,
                "next_rank": "E",
                "next_threshold": 50,
                "eligible": True,
                "exam_start": _action("guild.exam_start", label="升階考核（E）"),
            },
        },
        shop={"open": True, "stock": stock, "sellable": sellable},
        inventory={"rows": inventory, "wallet": 1000000},
        pagination={
            "board_total": MAX_BOARD_ROWS,
            "quest_total": MAX_QUEST_ROWS,
            "stock_total": MAX_STOCK_ROWS,
            "sellable_total": MAX_SELLABLE_ROWS,
            "inventory_total": MAX_INVENTORY_ROWS,
        },
    )
