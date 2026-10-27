"""Exact service action payload validator tests (pure).

Every validator error branch of the eight service actions is exercised: exact
field sets, the required provider identity, unknown-field rejection, non-empty
bounded strings, quantity bounds excluding booleans, and the two exact
``guild.quest_abandon`` shapes (the canonical record kind chooses between
them, never the payload).
"""

import unittest

from tools.spec_traceability import covers_requirement

from web.webclient.actions.service_actions import (
    ServiceActionError,
    validate_buy_payload,
    validate_exam_request_payload,
    validate_guild_register_payload,
    validate_quest_abandon_payload,
    validate_quest_accept_payload,
    validate_quest_turnin_payload,
    validate_sell_payload,
    validate_services_open_payload,
)

_PROVIDER = 61
_BAD_PROVIDERS = (None, 0, -1, True, False, "61", 7.0, 2**53)


class ServiceValidatorTests(unittest.TestCase):
    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_guild_register_requires_exactly_its_provider(self):
        self.assertEqual(
            validate_guild_register_payload({"npc_id": _PROVIDER}),
            {"npc_id": _PROVIDER},
        )
        for bad in (None, {}, {"anything": 1}, {"npc_id": _PROVIDER, "extra": 1}):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_guild_register_payload(bad)
        for bad in _BAD_PROVIDERS:
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_guild_register_payload({"npc_id": bad})

    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_quest_accept_payload(self):
        self.assertEqual(
            validate_quest_accept_payload(
                {"definition_key": "introductory_hunt", "npc_id": _PROVIDER}
            ),
            {"definition_key": "introductory_hunt", "npc_id": _PROVIDER},
        )
        for bad in (
            None,
            {},
            {"definition_key": "introductory_hunt"},
            {"npc_id": _PROVIDER},
            {"definition_key": "introductory_hunt", "npc_id": _PROVIDER, "extra": 1},
            {"definition_key": "", "npc_id": _PROVIDER},
            {"definition_key": "   ", "npc_id": _PROVIDER},
            {"definition_key": "x" * 65, "npc_id": _PROVIDER},
            {"definition_key": 7, "npc_id": _PROVIDER},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_quest_accept_payload(bad)

    def test_quest_turnin_payload(self):
        self.assertEqual(
            validate_quest_turnin_payload({"quest_id": "q:1", "npc_id": _PROVIDER}),
            {"quest_id": "q:1", "npc_id": _PROVIDER},
        )
        for bad in (
            {},
            {"quest_id": "q:1"},
            {"npc_id": _PROVIDER},
            {"quest_id": "", "npc_id": _PROVIDER},
            {"quest_id": "x" * 65, "npc_id": _PROVIDER},
            {"quest_id": "q:1", "npc_id": _PROVIDER, "recipient_id": 7},
            None,
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_quest_turnin_payload(bad)

    @covers_requirement("webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_quest_abandon_admits_only_the_two_exact_shapes(self):
        # An ordinary guild record names its staff provider.
        self.assertEqual(
            validate_quest_abandon_payload({"quest_id": "q:1", "npc_id": _PROVIDER}),
            {"quest_id": "q:1", "npc_id": _PROVIDER},
        )
        # A private escort keeps the host-free shape.
        self.assertEqual(
            validate_quest_abandon_payload({"quest_id": "q:1"}),
            {"quest_id": "q:1"},
        )
        for bad in (
            {},
            {"quest_id": ""},
            {"quest_id": "x" * 65},
            {"npc_id": _PROVIDER},
            {"quest_id": "q:1", "npc_id": _PROVIDER, "tracked": True},
            {"quest_id": "q:1", "npc_id": None},
            None,
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_quest_abandon_payload(bad)

    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    @covers_requirement("guild-exam-requests::appointment-semantics-provide-information-without-storing-bookings")
    def test_exam_request_payload(self):
        self.assertEqual(
            validate_exam_request_payload({"target_rank": "E", "npc_id": _PROVIDER}),
            {"target_rank": "E", "npc_id": _PROVIDER},
        )
        # Authority-like fields (host, branch, clock, threshold) are unknown
        # fields and reject before the coordinator runs.
        for bad in (
            {},
            {"target_rank": ""},
            {"target_rank": "E" * 9},
            {"target_rank": "E"},
            None,
            {"target_rank": "E", "npc_id": _PROVIDER, "host": "#12"},
            {"target_rank": "E", "npc_id": _PROVIDER, "branch_key": "b"},
            {"target_rank": "E", "npc_id": _PROVIDER, "tick": 1},
            {"target_rank": "E", "npc_id": _PROVIDER, "threshold": 0},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_exam_request_payload(bad)

    @covers_requirement("webclient-service-menus::service-actions-are-exact-allowlisted-and-server-authoritative")
    def test_trade_payloads(self):
        buy_payload = {
            "item_key": "meal",
            "quantity": 3,
            "recipient_id": 7,
            "npc_id": _PROVIDER,
        }
        sell_payload = {
            "item_key": "meal",
            "quantity": 3,
            "seller_id": 7,
            "npc_id": _PROVIDER,
        }
        self.assertEqual(validate_buy_payload(buy_payload), buy_payload)
        self.assertEqual(validate_sell_payload(sell_payload), sell_payload)
        # Each trade names exactly its own member field and its merchant: the
        # buy recipient is not a seller, and no commander or host field stands
        # in for either.
        with self.assertRaises(ServiceActionError):
            validate_buy_payload(sell_payload)
        with self.assertRaises(ServiceActionError):
            validate_sell_payload(buy_payload)
        for bad in (
            None,
            {},
            {"item_key": "meal"},
            {"quantity": 3},
            {"item_key": "meal", "quantity": 3, "recipient_id": 7},
            {
                "item_key": "meal",
                "quantity": 3,
                "recipient_id": 7,
                "npc_id": _PROVIDER,
                "host": "1",
            },
            {"item_key": "", "quantity": 3, "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "x" * 65, "quantity": 3, "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 0, "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": -1, "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 1001, "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": True, "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": "3", "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3.0, "recipient_id": 7, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "recipient_id": 0, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "recipient_id": -1, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "recipient_id": True, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "recipient_id": "7", "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "recipient_id": 7.0, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "recipient_id": 2**53, "npc_id": _PROVIDER},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_buy_payload(bad)
        for bad in (
            {"item_key": "meal", "quantity": 3, "seller_id": 0, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "seller_id": "7", "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "seller_id": True, "npc_id": _PROVIDER},
            {"item_key": "meal", "quantity": 3, "seller_id": 7, "npc_id": 0},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_sell_payload(bad)

    def test_services_open_payload(self):
        self.assertEqual(
            validate_services_open_payload({"npc_id": _PROVIDER}),
            {"npc_id": _PROVIDER},
        )
        for bad in (
            None,
            {},
            {"npc_id": _PROVIDER, "extra": 1},
            {"npc_id": _PROVIDER, "services": {}},
        ):
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_services_open_payload(bad)
        for bad in _BAD_PROVIDERS:
            with self.assertRaises(ServiceActionError, msg=bad):
                validate_services_open_payload({"npc_id": bad})


if __name__ == "__main__":
    unittest.main()
