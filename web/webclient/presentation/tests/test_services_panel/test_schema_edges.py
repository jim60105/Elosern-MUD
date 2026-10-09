"""Services panel schema edge tests: prerequisite, quest-row, and inventory-row actions."""
import unittest
from tools.spec_traceability import covers_requirement
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.services import ServicesPanelError, validate_services
from ._support import UNREGISTERED_PLAYER, _T_MEAL, _T_MEAL_DISPLAY, _valid_payload


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
            "branch_label": "合成公會分行",
            "rank_ladder": ["F", "E", "D", "C", "B", "A", "S"],
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
            "tracked": False,
        }
        value.update(overrides)
        return value


    def _inventory_row_action_payload(self, action, *, drop_action=False):
        payload = _valid_payload()
        if drop_action:
            del payload["inventory"]["rows"][0]["action"]
        else:
            payload["inventory"]["rows"][0]["action"] = action
        return payload


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
            # Cross-service allowlisted ids are never valid row actions.
            self._action("shop.buy"),
            self._action("guild.register"),
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


    @covers_requirement("webclient-service-menus::board-offers-carry-structured-facts-from-the-canonical-seams")
    def test_board_row_branch_rejections(self):
        base = {
            "definition_key": "introductory_hunt",
            "display_name": "討伐低階魔物",
            "objective_summary": "討伐 1 隻低階魔物",
            "category": "defeat",
            "objective_note": None,
            "deadline_line": None,
            "rationale": None,
            "flavor": None,
            "reward": {"copper": 50, "merit": 0, "items": []},
            "rank": "F",
            "accept": self._action("guild.quest_accept"),
        }
        for overrides, _msg in (
            ({"definition_key": ""}, "def key"),
            ({"display_name": ""}, "display"),
            ({"objective_summary": ""}, "objective"),
            ({"reward_summary": ""}, "legacy reward"),
            ({"category": "unknown"}, "category"),
            ({"reward": None}, "null reward"),
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


    def _rank_payload(self, rank):
        return _valid_payload(
            guild=self._guild(rank=rank),
            pagination={**_valid_payload()["pagination"]},
        )

    def test_rank_branch_rejections(self):
        rank = {
            "rank": "F",
            "merit": 0,
            "next_rank": "E",
            "next_threshold": 50,
            "merit_qualified": False,
            "exam_request": self._action("guild.exam_request"),
        }
        legacy = {key: value for key, value in rank.items() if key not in ("merit_qualified", "exam_request")}
        legacy.update({"eligible": False, "exam_start": self._action("guild.exam_start")})
        for candidate, _msg in (
            (dict(rank, rank=""), "rank empty"),
            (dict(rank, next_rank=None, next_threshold=50), "next mismatch"),
            (dict(rank, exam_request=self._action("guild.register")), "exam action"),
            (dict(rank, exam_request=self._action("guild.exam_start")), "retired action"),
            (dict(rank, merit_qualified="no"), "qualified type"),
            (legacy, "retired fields"),
        ):
            with self.assertRaises(ProtocolValidationError, msg=_msg):
                validate_services(self._rank_payload(candidate))

    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_merit_qualification_is_independent_of_request_availability(self):
        below_merit_enabled = {
            "rank": "F", "merit": 0, "next_rank": "E", "next_threshold": 50,
            "merit_qualified": False,
            "exam_request": self._action("guild.exam_request"),
        }
        qualified_disabled = dict(
            below_merit_enabled, merit=50, merit_qualified=True,
            exam_request=self._action(
                "guild.exam_request", enabled=False,
                disabled_reason={"code": "schedule_blocked", "message": "她現在正忙著，沒有理會你。"},
            ),
        )
        for rank in (below_merit_enabled, qualified_disabled):
            validated = validate_services(self._rank_payload(rank))
            self.assertEqual(validated["guild"]["rank"]["merit_qualified"], rank["merit_qualified"])
            self.assertEqual(
                validated["guild"]["rank"]["exam_request"]["enabled"], rank["exam_request"]["enabled"]
            )


    def test_shop_row_branch_rejections(self):
        stock = [
            {
                "item_key": "",
                "display_name": _T_MEAL_DISPLAY,
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
                "item_key": _T_MEAL,
                "display_name": _T_MEAL_DISPLAY,
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
                "item_key": _T_MEAL,
                "display_name": _T_MEAL_DISPLAY,
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


if __name__ == "__main__":
    unittest.main()
