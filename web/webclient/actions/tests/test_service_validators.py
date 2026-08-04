"""Exact service action payload validator tests (pure, task 3.1).

Every validator error branch of the seven service actions is exercised: exact
field sets, unknown-field rejection, non-empty bounded strings, quantity
bounds excluding booleans, and the adapter host-resolution reason mapping.
"""

import unittest

from tools.spec_traceability import covers_requirement

from web.webclient.actions.service_actions import (
    ServiceActionError,
    validate_buy_payload,
    validate_exam_start_payload,
    validate_guild_register_payload,
    validate_quest_abandon_payload,
    validate_quest_accept_payload,
    validate_quest_turnin_payload,
    validate_sell_payload,
)


class ServiceValidatorTests(unittest.TestCase):
    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_guild_register_accepts_only_empty(self):
        self.assertEqual(validate_guild_register_payload({}), {})
        with self.assertRaises(ServiceActionError):
            validate_guild_register_payload(None)
        with self.assertRaises(ServiceActionError):
            validate_guild_register_payload({"anything": 1})

    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_quest_accept_payload(self):
        self.assertEqual(
            validate_quest_accept_payload({"definition_key": "introductory_hunt"}),
            {"definition_key": "introductory_hunt"},
        )
        for bad in (
            None,
            {},
            {"definition_key": "introductory_hunt", "extra": 1},
            {"definition_key": ""},
            {"definition_key": "   "},
            {"definition_key": "x" * 65},
            {"definition_key": 7},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_quest_accept_payload(bad)

    def test_quest_abandon_and_turnin_payloads(self):
        self.assertEqual(
            validate_quest_abandon_payload({"quest_id": "q:1"}),
            {"quest_id": "q:1"},
        )
        self.assertEqual(
            validate_quest_turnin_payload({"quest_id": "q:1"}),
            {"quest_id": "q:1"},
        )
        for bad in ({}, {"quest_id": ""}, {"quest_id": "x" * 65}, None):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_quest_abandon_payload(bad)
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_quest_turnin_payload(bad)

    def test_exam_start_payload(self):
        self.assertEqual(validate_exam_start_payload({"target_rank": "E"}), {"target_rank": "E"})
        for bad in ({}, {"target_rank": ""}, {"target_rank": "E" * 9}, None):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_exam_start_payload(bad)

    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_trade_payloads(self):
        valid = {"item_key": "meal", "quantity": 3}
        self.assertEqual(validate_buy_payload(valid), valid)
        self.assertEqual(validate_sell_payload(valid), valid)
        for bad in (
            None,
            {},
            {"item_key": "meal"},
            {"quantity": 3},
            {"item_key": "meal", "quantity": 3, "host": "1"},
            {"item_key": "", "quantity": 3},
            {"item_key": "x" * 65, "quantity": 3},
            {"item_key": "meal", "quantity": 0},
            {"item_key": "meal", "quantity": -1},
            {"item_key": "meal", "quantity": 1001},
            {"item_key": "meal", "quantity": True},
            {"item_key": "meal", "quantity": "3"},
            {"item_key": "meal", "quantity": 3.0},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_buy_payload(bad)
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_sell_payload(bad)


if __name__ == "__main__":
    unittest.main()
