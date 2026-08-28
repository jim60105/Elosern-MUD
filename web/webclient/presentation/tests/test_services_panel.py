"""Exact ``services`` schema, presenter, and surface-isolation tests.

Covers the D4 shared bounds, the version-2 payload validation, deterministic
row ordering, pagination totals, host identity/display-name limits,
action-descriptor shapes, the worst-case envelope size, and the isolation of a
corrupt quest log, malformed merchant stock, and non-exploration modes.
"""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.tests.combat_fixtures import BattlefieldIsolation

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from web.webclient.presentation.services import (
    MAX_BOARD_ROWS,
    MAX_DETAIL_CODE_POINTS,
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_HOST_DISPLAY_NAME_CODE_POINTS,
    MAX_INVENTORY_ROWS,
    MAX_KEY_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_QUEST_ROWS,
    MAX_PRESENTATION_KEY_CODE_POINTS,
    MAX_PRESENTATION_SUMMARY_CODE_POINTS,
    MAX_QUANTITY,
    MAX_RANK_KEY_CODE_POINTS,
    MAX_REASON_MESSAGE_CODE_POINTS,
    MAX_SELLABLE_ROWS,
    MAX_STOCK_ROWS,
    MAX_SUMMARY_CODE_POINTS,
    SERVICES_SCHEMA_VERSION,
    ServicesPanelError,
    validate_services,
)
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.guild_config import CATALOG, load_catalog_into_cache, register_catalog_offers
from world.rules.guild_offers import GUILD_OFFER_REGISTRY, accept_guild_offer
from world.rules.service_view import ServicesViewError
from world.rules.surfaces import write_counter_trait

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
                    "item_key": "meal",
                    "display_name": "普通餐食",
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
                "item_key": "meal",
                "display_name": "普通餐食",
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
        }
        for index in range(MAX_QUEST_ROWS)
    ]
    stock = [
        {
            "item_key": "meal",
            "display_name": "普通餐食",
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
            "item_key": "meal",
            "display_name": "普通餐食",
            "sell_copper": 5,
            "held": 20,
            "sell": _action("shop.sell", label="販賣", quantity={"min": 1, "max": 20}),
        }
        for _ in range(MAX_SELLABLE_ROWS)
    ]
    inventory = [
        {
            "item_key": "meal",
            "display_name": "普通餐食",
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
        host={"identity": "12345", "display_name": "埃洛西恩冒險者公會 阿爾托利亞分會"},
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


class ServicesSchemaTests(unittest.TestCase):
    """Exact D4 bounds and envelope gate at the validator level."""

    def test_minimal_available_payload_passes(self):
        payload = validate_services(_valid_payload())
        self.assertTrue(payload["available"])
        self.assertEqual(payload["schema_version"], SERVICES_SCHEMA_VERSION)
        self.assertEqual(payload["kind"], "services")

    def test_unknown_panel_field_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(extra_field=1))

    def test_board_row_cap_enforced(self):
        row = _valid_guild()["board"][0]
        guild = _valid_guild(board=[row for _ in range(MAX_BOARD_ROWS + 1)])
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    guild=guild,
                    pagination={
                        **_valid_payload()["pagination"],
                        "board_total": MAX_BOARD_ROWS + 1,
                    },
                )
            )

    def test_quest_row_cap_enforced(self):
        quest = {
            "quest_id": "q:1",
            "definition_key": "introductory_hunt",
            "display_name": "討伐低階魔物",
            "state": "in_progress",
            "stage_index": 0,
            "stage_progress": 0,
            "objective_summary": "討伐 1 隻低階魔物",
            "deadline_line": None,
            "detail": "詳情",
            "abandon": _action("guild.quest_abandon"),
            "turnin": _action("guild.quest_turnin", enabled=False),
        }
        guild = _valid_guild(quests=[quest for _ in range(MAX_QUEST_ROWS + 1)])
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(guild=guild))

    def test_stock_row_cap_enforced(self):
        row = _valid_shop()["stock"][0]
        shop = _valid_shop(stock=[row for _ in range(MAX_STOCK_ROWS + 1)])
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(shop=shop))

    def test_sellable_row_cap_enforced(self):
        row = {
            "item_key": "meal",
            "display_name": "普通餐食",
            "sell_copper": 5,
            "held": 1,
            "sell": _action("shop.sell"),
        }
        shop = _valid_shop(sellable=[row for _ in range(MAX_SELLABLE_ROWS + 1)])
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(shop=shop))

    def test_inventory_row_cap_enforced(self):
        row = {
            "item_key": "meal",
            "display_name": "普通餐食",
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
        inventory = {
            "rows": [row for _ in range(MAX_INVENTORY_ROWS + 1)],
            "wallet": 0,
        }
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(inventory=inventory))

    def test_string_ceilings_enforced(self):
        payload = _valid_payload(
            guild=_valid_guild(
                board=[
                    {
                        **_valid_guild()["board"][0],
                        "definition_key": "x" * (MAX_KEY_CODE_POINTS + 1),
                    }
                ]
            )
        )
        with self.assertRaises(ProtocolValidationError):
            validate_services(payload)

    def test_quest_detail_ceiling_enforced(self):
        quest = {
            "quest_id": "q:1",
            "definition_key": "introductory_hunt",
            "display_name": "討伐低階魔物",
            "state": "in_progress",
            "stage_index": 0,
            "stage_progress": 0,
            "objective_summary": "討伐 1 隻低階魔物",
            "deadline_line": None,
            "detail": "獎" * (MAX_DETAIL_CODE_POINTS + 1),
            "abandon": _action("guild.quest_abandon"),
            "turnin": _action("guild.quest_turnin", enabled=False),
        }
        guild = _valid_guild(quests=[quest])
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(guild=guild))

    def test_host_identity_must_be_ascii_and_bounded(self):
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(host={"identity": "公會長", "display_name": "x"}))
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(host={"identity": "1" * (MAX_KEY_CODE_POINTS + 1), "display_name": "x"})
            )
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    host={
                        "identity": "1",
                        "display_name": "獎" * (MAX_HOST_DISPLAY_NAME_CODE_POINTS + 1),
                    }
                )
            )

    def test_action_descriptor_shapes_enforced(self):
        guild = _valid_guild()
        guild["board"][0]["accept"] = _action(
            "guild.quest_accept",
            quantity={"min": 1, "max": 3},
        )
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(guild=guild))

        enabled_without_quantity = _valid_shop()
        enabled_without_quantity["stock"][0]["buy"] = _action("shop.buy")
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(shop=enabled_without_quantity))

        bad_quantity = _valid_shop()
        bad_quantity["stock"][0]["buy"] = _action(
            "shop.buy",
            quantity={"min": 1, "max": MAX_QUANTITY + 1},
        )
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(shop=bad_quantity))

        boolean_quantity = _valid_shop()
        boolean_quantity["stock"][0]["buy"] = _action(
            "shop.buy",
            quantity={"min": 1, "max": True},
        )
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(shop=boolean_quantity))

    def test_enabled_and_disabled_action_consistency(self):
        guild = _valid_guild()
        guild["board"][0]["accept"] = _action("guild.quest_accept", enabled=True, disabled_reason={"code": "x", "message": "y"})
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(guild=guild))
        guild = _valid_guild()
        guild["board"][0]["accept"] = _action("guild.quest_accept", enabled=False, disabled_reason=None)
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(guild=guild))

    def test_pagination_must_match_shipped_rows(self):
        payload = _valid_payload(guild=_valid_guild())
        payload["pagination"] = dict(payload["pagination"], board_total=0)
        with self.assertRaises(ProtocolValidationError):
            validate_services(payload)

    def test_pagination_zero_for_null_surfaces(self):
        payload = _valid_payload(guild=_valid_guild())
        payload["pagination"] = dict(payload["pagination"], board_total=1, quest_total=0)
        payload["guild"] = None
        with self.assertRaises(ProtocolValidationError):
            validate_services(payload)

    def test_player_consistency_between_rank_and_registration(self):
        player = dict(UNREGISTERED_PLAYER)
        player["guild_registered"] = True
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(player=player))

    def test_worst_case_realistic_payload_fits_the_envelope(self):
        """A structurally maximal realistic payload at all row ceilings stays
        comfortably under the 65,536-byte envelope (design D4)."""
        payload = _realistic_maximal_payload()
        validated = validate_services(payload)
        size = json_byte_size(validated)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)
        self.assertLess(size, 48 * 1024)

    def test_all_ceilings_payload_is_rejected_by_the_byte_gate(self):
        """A payload maximizing every string field simultaneously fails closed
        on serialized size even though each field is individually in bounds."""
        payload = _all_ceilings_payload()
        with self.assertRaises(ServicesPanelError):
            validate_services(payload)

    def _inventory_payload(self, presentation):
        return _valid_payload(
            inventory={
                "rows": [
                    {
                        "item_key": "meal",
                        "display_name": "普通餐食",
                        "held": 1,
                        "equipped": False,
                        "action": None,
                        "presentation": presentation,
                    }
                ],
                "wallet": 0,
            }
        )

    def test_presentation_null_for_unknown_key_passes(self):
        validated = validate_services(self._inventory_payload(None))
        self.assertIsNone(validated["inventory"]["rows"][0]["presentation"])

    def test_presentation_object_passes(self):
        presentation = {
            "kind": "food",
            "icon_key": "food",
            "rarity": "common",
            "summary": "供旅人充飢的普通餐食。",
        }
        validated = validate_services(self._inventory_payload(presentation))
        self.assertEqual(validated["inventory"]["rows"][0]["presentation"], presentation)

    def test_presentation_missing_field_rejected(self):
        presentation = {
            "kind": "food",
            "icon_key": "food",
            "rarity": "common",
        }
        with self.assertRaises(ProtocolValidationError):
            validate_services(self._inventory_payload(presentation))

    def test_presentation_extra_field_rejected(self):
        presentation = {
            "kind": "food",
            "icon_key": "food",
            "rarity": "common",
            "summary": "供旅人充飢的普通餐食。",
            "color": "red",
        }
        with self.assertRaises(ProtocolValidationError):
            validate_services(self._inventory_payload(presentation))

    def test_presentation_identifier_bound_enforced(self):
        presentation = {
            "kind": "k" * (MAX_PRESENTATION_KEY_CODE_POINTS + 1),
            "icon_key": "food",
            "rarity": "common",
            "summary": "供旅人充飢的普通餐食。",
        }
        with self.assertRaises(ProtocolValidationError):
            validate_services(self._inventory_payload(presentation))

    def test_presentation_identifier_case_and_charset_enforced(self):
        for bad in ("Food", "food ", "food-food", "foöd"):
            presentation = {
                "kind": bad,
                "icon_key": "food",
                "rarity": "common",
                "summary": "供旅人充飢的普通餐食。",
            }
            with self.assertRaises(ProtocolValidationError, msg=bad):
                validate_services(self._inventory_payload(presentation))

    def test_presentation_summary_bound_enforced(self):
        presentation = {
            "kind": "food",
            "icon_key": "food",
            "rarity": "common",
            "summary": "獎" * (MAX_PRESENTATION_SUMMARY_CODE_POINTS + 1),
        }
        with self.assertRaises(ProtocolValidationError):
            validate_services(self._inventory_payload(presentation))

    def test_presentation_summary_at_the_bound_is_accepted(self):
        presentation = {
            "kind": "food",
            "icon_key": "food",
            "rarity": "common",
            "summary": "獎" * MAX_PRESENTATION_SUMMARY_CODE_POINTS,
        }
        validated = validate_services(self._inventory_payload(presentation))
        self.assertEqual(
            validated["inventory"]["rows"][0]["presentation"]["summary"],
            "獎" * MAX_PRESENTATION_SUMMARY_CODE_POINTS,
        )

    def test_presentation_summary_type_enforced(self):
        for bad in (128, ["x"], True):
            presentation = {
                "kind": "food",
                "icon_key": "food",
                "rarity": "common",
                "summary": bad,
            }
            with self.assertRaises(ProtocolValidationError, msg=bad):
                validate_services(self._inventory_payload(presentation))


class ServicesPresenterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._catalog = CATALOG
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        register_catalog()
        catalog = load_catalog_into_cache()
        register_catalog_offers(catalog)
        get_world_clock()
        self.room1 = create_object(Room, key="guild hall")

        self.store = create_object(Room, key="general store")
        self.staff = create_object(NPC, key="guild master", location=self.room1)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        self.staff.components.add(
            GuildExaminer.create(self.staff, service_id="examiner", branch_key="guild_branch_altoria")
        )
        self.merchant_npc = create_object(NPC, key="merchant", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc, service_id="merchant", shop_key="altoria_general_store"
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {
            "meal": 20,
            "healing_potion": 3,
            "plain_sword": 1,
        }

        self.player = create_object(PlayerCharacter, key="service presenter")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.db.wallet = 1000
        register_adventurer(self.player, staff=self.staff)
        write_counter_trait(self.player, "guild_merit", 60)
        accept_guild_offer(self.player, self.staff, "introductory_hunt")

    def tearDown(self):
        global CATALOG
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offers)
        CATALOG = self._catalog
        super().tearDown()

    def _context(self):
        return PresentationContext(actor=self.player, protocol_version=1)

    def _render(self):
        return build_production_registry().render("services", self._context())

    @covers_requirement("webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel")
    def test_guild_hall_renders_available_services_payload(self):
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "services")
        self.assertIsNone(payload["shop"])
        self.assertIsNotNone(payload["guild"])
        self.assertIsNotNone(payload["player"])
        self.assertEqual(payload["pagination"]["board_total"], 1)
        self.assertEqual(payload["pagination"]["quest_total"], 1)
        self.assertEqual(payload["player"]["guild_rank"], "F")
        self.assertEqual(payload["guild"]["registration"]["registered"], True)

    def test_shop_renders_exact_copper_and_open_state(self):
        self.player.location = self.store
        get_world_clock()._persist(12 * 3600)
        payload = self._render()
        self.assertIsNotNone(payload["shop"])
        self.assertTrue(payload["shop"]["open"])
        meal = next(row for row in payload["shop"]["stock"] if row["item_key"] == "meal")
        self.assertEqual(meal["buy_copper"], 10)
        self.assertEqual(meal["sell_copper"], 5)
        self.assertEqual(meal["stock"], 20)
        self.assertIsNotNone(meal["buy"]["quantity"])
        self.assertIsNone(payload["guild"])

    def test_registered_panels_publish_affected_panels(self):
        # Rendering never mutates canonical surfaces.
        before = {
            "wallet": self.player.db.wallet,
            "quest_log": list(self.player.db.quest_log or []),
        }
        self._render()
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(list(self.player.db.quest_log or []), before["quest_log"])

    @covers_requirement("webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel")
    def test_combat_mode_ships_personal_inventory_only(self):
        from evennia.utils.create import create_object as co
        from typeclasses.monsters import Monster

        self.player.db.inventory = ["healing_potion"]
        monster = co(Monster, key="goblin", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        engage(self.player, monster)
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["host"])
        self.assertIsNone(payload["guild"])
        self.assertIsNone(payload["shop"])
        self.assertIsNotNone(payload["player"])
        self.assertIsNotNone(payload["inventory"])
        self.assertEqual(payload["pagination"]["board_total"], 0)
        self.assertEqual(payload["pagination"]["quest_total"], 0)
        self.assertEqual(payload["pagination"]["stock_total"], 0)
        self.assertEqual(payload["pagination"]["sellable_total"], 0)
        row = payload["inventory"]["rows"][0]
        self.assertEqual(row["item_key"], "healing_potion")
        self.assertEqual(row["action"]["action_id"], "inventory.use")

    def test_creation_pending_renders_unavailable_form(self):
        self.player.db.creation_pending = True
        payload = self._render()
        self.assertFalse(payload["available"])

    def test_corrupt_quest_log_degrades_only_guild_surface(self):
        self.player.db.quest_log = [{"quest_id": "broken", "definition_key": "nope"}]
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["guild"])
        self.assertIsNotNone(payload["inventory"])
        self.assertEqual(payload["pagination"]["board_total"], 0)
        self.assertEqual(payload["pagination"]["quest_total"], 0)

    def test_malformed_stock_degrades_only_shop_surface(self):
        self.merchant.merchant_stock = {"nope": 5}
        self.player.location = self.store
        get_world_clock()._persist(12 * 3600)
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["shop"])
        self.assertIsNotNone(payload["inventory"])

    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_registered_inventory_projects_registry_presentation(self):
        self.player.db.inventory = ["healing_potion", "healing_potion", "plain_sword"]
        payload = self._render()
        rows = {row["item_key"]: row for row in payload["inventory"]["rows"]}
        self.assertEqual(
            rows["healing_potion"]["presentation"],
            {
                "kind": "potion",
                "icon_key": "potion",
                "rarity": "rare",
                "summary": "盛裝於小瓶中的治療藥水。",
            },
        )
        self.assertEqual(rows["healing_potion"]["held"], 2)
        self.assertEqual(rows["plain_sword"]["presentation"]["rarity"], "common")

    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_unknown_inventory_key_projects_null_presentation(self):
        self.player.db.inventory = ["mystery_relic", "mystery_relic", "healing_potion"]
        payload = self._render()
        rows = {row["item_key"]: row for row in payload["inventory"]["rows"]}
        self.assertIsNone(rows["mystery_relic"]["presentation"])
        self.assertEqual(rows["mystery_relic"]["display_name"], "mystery_relic")
        self.assertIsNotNone(rows["healing_potion"]["presentation"])

    @covers_requirement("webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel")
    def test_rendering_inventory_never_mutates_canonical_state(self):
        self.player.db.inventory = ["healing_potion", "healing_potion", "mystery_relic", "plain_sword"]
        self.player.db.equipment = {"weapon_main": "plain_sword", "armor": "leather_armor"}
        before = {
            "inventory": list(self.player.db.inventory or []),
            "equipment": dict(self.player.db.equipment or {}),
            "wallet": self.player.db.wallet,
            "quest_log": list(self.player.db.quest_log or []),
        }
        payload = self._render()
        self.assertEqual(list(self.player.db.inventory or []), before["inventory"])
        self.assertEqual(dict(self.player.db.equipment or {}), before["equipment"])
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(list(self.player.db.quest_log or []), before["quest_log"])
        row = next(r for r in payload["inventory"]["rows"] if r["item_key"] == "plain_sword")
        self.assertTrue(row["equipped"])

    def test_unregistered_presenter_is_honest(self):
        newcomer = create_object(PlayerCharacter, key="newcomer")
        newcomer.race = "human"
        newcomer.apply_race_baseline()
        newcomer.location = self.room1
        newcomer.db.wallet = 5
        context = PresentationContext(actor=newcomer, protocol_version=1)
        payload = build_production_registry().render("services", context)
        self.assertTrue(payload["available"])
        self.assertFalse(payload["player"]["guild_registered"])
        self.assertIsNone(payload["player"]["guild_rank"])
        self.assertEqual(payload["guild"]["board"], [])
        self.assertEqual(payload["guild"]["registration"]["register"]["enabled"], True)


class ServicesSchemaEdgeTests(unittest.TestCase):
    """Remaining D4 validator error branches not covered by the happy-path tests."""

    def _action(self, action_id="guild.register", **overrides):
        value = {
            "action_id": action_id,
            "label": "測試",
            "enabled": True,
            "disabled_reason": None,
            "quantity": None,
        }
        value.update(overrides)
        return value

    def _guild(self, **overrides):
        value = {
            "registration": {"registered": False, "register": self._action()},
            "board": [],
            "quests": [],
            "rank": None,
        }
        value.update(overrides)
        return value

    def _quest_row(self, **overrides):
        value = {
            "quest_id": "q:1",
            "definition_key": "introductory_hunt",
            "display_name": "討伐低階魔物",
            "state": "in_progress",
            "stage_index": 0,
            "stage_progress": 0,
            "objective_summary": "討伐 1 隻低階魔物",
            "deadline_line": None,
            "detail": "詳情",
            "abandon": self._action("guild.quest_abandon"),
            "turnin": self._action("guild.quest_turnin", enabled=False),
        }
        value.update(overrides)
        return value

    def test_action_branch_rejections(self):
        cases = [
            {"label": "   "},
            {"label": "獎" * 65},
            {"quantity": {"min": 5, "max": 1}},
            {"action_id": "guild.register", "quantity": {"min": 1, "max": 2}},
        ]
        for overrides in cases:
            with self.assertRaises(ProtocolValidationError, msg=overrides):
                validate_services(
                    _valid_payload(
                        guild=self._guild(
                            registration={
                                "registered": False,
                                "register": self._action(**overrides),
                            }
                        )
                    )
                )

    def _inventory_row_action_payload(self, action, *, drop_action=False):
        payload = _valid_payload()
        if drop_action:
            del payload["inventory"]["rows"][0]["action"]
        else:
            payload["inventory"]["rows"][0]["action"] = action
        return payload

    def test_inventory_row_action_acceptance_and_rejections(self):
        good = self._action(
            "inventory.use",
            enabled=False,
            disabled_reason={"code": "hp_full", "message": "你的體力已經全滿。"},
        )
        payload = validate_services(self._inventory_row_action_payload(good))
        self.assertEqual(
            payload["inventory"]["rows"][0]["action"]["disabled_reason"]["code"],
            "hp_full",
        )
        bad = [
            self._action("mystery.action"),
            self._action("inventory.toggle_equip", quantity={"min": 1, "max": 2}),
            self._action("inventory.use", enabled=False),
            self._action(
                "inventory.use",
                enabled=True,
                disabled_reason={"code": "hp_full", "message": "你的體力已經全滿。"},
            ),
        ]
        for action in bad:
            with self.subTest(action_id=action["action_id"]):
                with self.assertRaises(ProtocolValidationError):
                    validate_services(
                        self._inventory_row_action_payload(action)
                    )
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                self._inventory_row_action_payload(None, drop_action=True)
            )

    def test_disabled_reason_branch_rejections(self):
        payload = _valid_payload(
            guild=self._guild(
                registration={
                    "registered": True,
                    "register": self._action(
                        enabled=False, disabled_reason={"code": "x", "message": "  "}
                    ),
                }
            )
        )
        with self.assertRaises(ProtocolValidationError):
            validate_services(payload)

    def test_registration_contract_rejections(self):
        payload = _valid_payload(
            guild=self._guild(
                registration={
                    "registered": True,
                    "register": self._action("shop.buy"),
                }
            )
        )
        with self.assertRaises(ProtocolValidationError):
            validate_services(payload)
        payload = _valid_payload(
            guild=self._guild(
                registration={
                    "registered": True,
                    "register": self._action(enabled=True),
                }
            )
        )
        with self.assertRaises(ProtocolValidationError):
            validate_services(payload)

    def test_board_row_branch_rejections(self):
        base = {
            "definition_key": "introductory_hunt",
            "display_name": "討伐低階魔物",
            "objective_summary": "討伐 1 隻低階魔物",
            "reward_summary": "獎勵：銅 50",
            "rank": "F",
            "accept": self._action("guild.quest_accept"),
        }
        for overrides, _msg in (
            ({"definition_key": ""}, "def key"),
            ({"display_name": ""}, "display"),
            ({"objective_summary": ""}, "objective"),
            ({"reward_summary": ""}, "reward"),
            ({"rank": ""}, "rank"),
            ({"accept": self._action("guild.register")}, "accept action"),
        ):
            row = dict(base, **overrides)
            with self.assertRaises(ProtocolValidationError, msg=_msg):
                validate_services(
                    _valid_payload(
                        guild=self._guild(board=[row]),
                        pagination={**_valid_payload()["pagination"], "board_total": 1},
                    )
                )

    def test_quest_row_branch_rejections(self):
        for overrides, _msg in (
            ({"quest_id": ""}, "quest id"),
            ({"state": "bogus"}, "state"),
            ({"deadline_line": "  "}, "deadline"),
            ({"detail": ""}, "detail"),
            ({"abandon": self._action("guild.register")}, "abandon action"),
            ({"turnin": self._action("guild.register")}, "turnin action"),
        ):
            with self.assertRaises(ProtocolValidationError, msg=_msg):
                validate_services(
                    _valid_payload(
                        guild=self._guild(quests=[self._quest_row(**overrides)]),
                        pagination={**_valid_payload()["pagination"], "quest_total": 1},
                    )
                )

    def test_rank_branch_rejections(self):
        rank = {
            "rank": "F",
            "merit": 0,
            "next_rank": "E",
            "next_threshold": 50,
            "eligible": True,
            "exam_start": self._action("guild.exam_start"),
        }
        for overrides, _msg in (
            ({"rank": ""}, "rank empty"),
            ({"next_rank": None, "next_threshold": 50}, "next mismatch"),
            ({"exam_start": self._action("guild.register")}, "exam action"),
            ({"eligible": False}, "eligible mismatch"),
        ):
            with self.assertRaises(ProtocolValidationError, msg=_msg):
                validate_services(
                    _valid_payload(
                        guild=self._guild(rank=dict(rank, **overrides)),
                        pagination={**_valid_payload()["pagination"]},
                    )
                )

    def test_shop_row_branch_rejections(self):
        stock = [
            {
                "item_key": "",
                "display_name": "普通餐食",
                "buy_copper": 10,
                "sell_copper": 5,
                "stock": 20,
                "max_stock": 20,
                "buy": self._action("shop.buy", quantity={"min": 1, "max": 20}),
            }
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    shop={"open": True, "stock": stock, "sellable": []},
                    pagination={**_valid_payload()["pagination"], "stock_total": 1},
                )
            )
        stock = [
            {
                "item_key": "meal",
                "display_name": "普通餐食",
                "buy_copper": 10,
                "sell_copper": 5,
                "stock": 20,
                "max_stock": 20,
                "buy": self._action("guild.register"),
            }
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    shop={"open": True, "stock": stock, "sellable": []},
                    pagination={**_valid_payload()["pagination"], "stock_total": 1},
                )
            )
        sellable = [
            {
                "item_key": "meal",
                "display_name": "普通餐食",
                "sell_copper": 5,
                "held": 1,
                "sell": self._action("guild.register"),
            }
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    shop={"open": True, "stock": [], "sellable": sellable},
                    pagination={**_valid_payload()["pagination"], "sellable_total": 1},
                )
            )

    def test_panel_level_branch_rejections(self):
        with self.assertRaises(ServicesPanelError):
            validate_services(_valid_payload(schema_version=1))
        with self.assertRaises(ServicesPanelError):
            validate_services(_valid_payload(available=False))
        with self.assertRaises(ServicesPanelError):
            validate_services(_valid_payload(kind="combat"))
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(host={"identity": "1", "display_name": " "}))
        player = dict(UNREGISTERED_PLAYER)
        player["next_rank"] = "E"
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(player=player))
        player = dict(UNREGISTERED_PLAYER)
        player["guild_merit"] = -1
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(player=player))

    def test_pagination_mismatch_branches(self):
        guild = self._guild(quests=[self._quest_row()])
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    guild=guild,
                    pagination={
                        **_valid_payload()["pagination"],
                        "board_total": 0,
                        "quest_total": 0,
                    },
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    shop={"open": True, "stock": [], "sellable": []},
                    pagination={**_valid_payload()["pagination"], "stock_total": 1},
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    shop={"open": True, "stock": [], "sellable": []},
                    pagination={**_valid_payload()["pagination"], "sellable_total": 1},
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_services(
                _valid_payload(
                    inventory={"rows": [], "wallet": 0},
                    pagination={**_valid_payload()["pagination"], "inventory_total": 1},
                )
            )


class ServicesPresenterPrerequisiteTests(EvenniaTestCase):
    """Global-prerequisite failures render the common unavailable form."""

    def setUp(self):
        self.room1 = create_object(Room, key="room")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()

    def test_services_view_error_renders_unavailable(self):
        from unittest.mock import patch

        actor = self.char1
        actor.location = self.room1
        context = PresentationContext(actor=actor, protocol_version=1)
        with patch(
            "web.webclient.presentation.services.build_services_view",
            side_effect=ServicesViewError("world clock is absent"),
        ):
            from web.webclient.presentation.registry import PanelUnavailableError

            with self.assertRaises(PanelUnavailableError):
                from web.webclient.presentation.services import services_presenter

                services_presenter(context)
        # A panel render converts it to the registry unavailable form.
        payload = build_production_registry().render("services", context)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "services_unavailable")

    def test_creation_pending_renders_unavailable(self):
        actor = self.char1
        actor.db.creation_pending = True
        context = PresentationContext(actor=actor, protocol_version=1)
        payload = build_production_registry().render("services", context)
        self.assertFalse(payload["available"])
        self.assertNotIn("player", payload)




if __name__ == "__main__":
    unittest.main()
