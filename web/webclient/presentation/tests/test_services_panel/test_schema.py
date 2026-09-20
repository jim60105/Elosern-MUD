"""Services panel schema tests: guild/store/giver envelope validation."""
import unittest
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, ProtocolValidationError, json_byte_size
from web.webclient.presentation.services import MAX_BOARD_ROWS, MAX_DETAIL_CODE_POINTS, MAX_HOST_DISPLAY_NAME_CODE_POINTS, MAX_INVENTORY_ROWS, MAX_KEY_CODE_POINTS, MAX_QUEST_ROWS, MAX_PRESENTATION_KEY_CODE_POINTS, MAX_PRESENTATION_SUMMARY_CODE_POINTS, MAX_QUANTITY, MAX_SELLABLE_ROWS, MAX_STOCK_ROWS, SERVICES_SCHEMA_VERSION, ServicesPanelError, validate_services
from world.quests.tests._fixtures import quest
from ._support import UNREGISTERED_PLAYER, _T_MEAL, _T_MEAL_DISPLAY, _action, _all_ceilings_payload, _realistic_maximal_payload, _valid_guild, _valid_payload, _valid_shop


class ServicesSchemaTests(unittest.TestCase):
    """Exact D4 bounds and envelope gate at the validator level."""


    def _inventory_payload(self, presentation):
        return _valid_payload(
            inventory={
                "rows": [
                    {
                        "item_key": _T_MEAL,
                        "display_name": _T_MEAL_DISPLAY,
                        "held": 1,
                        "equipped": False,
                        "action": None,
                        "presentation": presentation,
                    }
                ],
                "wallet": 0,
            }
        )


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
            "tracked": False,
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
            "item_key": _T_MEAL,
            "display_name": _T_MEAL_DISPLAY,
            "sell_copper": 5,
            "held": 1,
            "sell": _action("shop.sell"),
        }
        shop = _valid_shop(sellable=[row for _ in range(MAX_SELLABLE_ROWS + 1)])
        with self.assertRaises(ProtocolValidationError):
            validate_services(_valid_payload(shop=shop))


    def test_inventory_row_cap_enforced(self):
        row = {
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
            "tracked": False,
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


if __name__ == "__main__":
    unittest.main()
