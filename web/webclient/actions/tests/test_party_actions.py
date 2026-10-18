"""Tests for the ``party.transfer`` action (party-item-transfer).

Intended requirement ID for the added capability, recorded here until it is
synced into ``openspec/specs/`` (``covers_requirement`` decorators are added
then, per the ``party-member-authority`` precedent):

- ``party-item-transfer::the-party-transfer-action-carries-exact-member-references``
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.party_actions import (
    PartyActionError,
    _party_transfer_adapter,
    validate_party_transfer_payload,
)
from web.webclient.actions.registry import build_production_action_registry
from world.rules.party import join_party
from world.rules.party_inventory import MAX_TRANSFER_QUANTITY
from world.rules.tests._combat_session_helpers import _race_key
from world.tests.synthetic_data import make_item, synthetic_registries

_POTION = make_item("t_transfer_potion", display_name_zh="測試藥水", sellable=False)

_VALID = {
    "giver_id": 3,
    "receiver_id": 7,
    "item_key": _POTION.key,
    "quantity": 2,
}


class PartyTransferPayloadTests(EvenniaTestCase):
    """The payload schema is exact and bounded."""

    def test_exact_payload_is_normalized(self):
        self.assertEqual(validate_party_transfer_payload(dict(_VALID)), _VALID)

    def test_each_malformed_payload_rejects(self):
        cases = (
            ("not an object", []),
            ("missing field", {k: v for k, v in _VALID.items() if k != "quantity"}),
            ("extra field", {**_VALID, "slot": "weapon_main"}),
            ("bool giver", {**_VALID, "giver_id": True}),
            ("zero giver", {**_VALID, "giver_id": 0}),
            ("unsafe receiver", {**_VALID, "receiver_id": 9_007_199_254_740_992}),
            ("whitespace key", {**_VALID, "item_key": "t transfer potion"}),
            ("empty key", {**_VALID, "item_key": ""}),
            ("non-string key", {**_VALID, "item_key": 5}),
            ("zero quantity", {**_VALID, "quantity": 0}),
            ("over quantity", {**_VALID, "quantity": MAX_TRANSFER_QUANTITY + 1}),
            ("bool quantity", {**_VALID, "quantity": True}),
            ("string quantity", {**_VALID, "quantity": "2"}),
        )
        for label, payload in cases:
            with self.subTest(label=label):
                with self.assertRaises(PartyActionError):
                    validate_party_transfer_payload(payload)


class PartyTransferAdapterTests(EvenniaTestCase):
    """The adapter reauthorizes every reference and publishes canonical state."""

    def setUp(self):
        super().setUp()
        scope = synthetic_registries(
            "races",
            "static_tiers",
            "subraces",
            "items",
            extra={"items": {_POTION.key: _POTION}},
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.room = create_object(Room, key="測試房間")
        self.commander = create_object(
            PlayerCharacter, key="指揮者", location=self.room
        )
        self.commander.race = _race_key()
        self.commander.apply_race_baseline()
        self.aila = create_object(
            NPC, key="艾拉", location=self.room, home=self.room
        )
        self.aila.race = _race_key()
        self.aila.apply_race_baseline()
        join_party(self.aila, self.commander)

    def _payload(self, **overrides):
        payload = {
            "giver_id": self.commander.pk,
            "receiver_id": self.aila.pk,
            "item_key": _POTION.key,
            "quantity": 1,
        }
        payload.update(overrides)
        return payload

    @covers_requirement(
        "webclient-action-dispatch::action-identity-comes-only-from-the-authenticated-session"
    )
    def test_forged_receiver_is_rejected_without_commander_substitution(self):
        outsider = create_object(NPC, key="路人", location=self.room)
        outsider.race = _race_key()
        outsider.apply_race_baseline()
        self.commander.db.inventory = [_POTION.key]

        result = _party_transfer_adapter(
            self.commander, self._payload(receiver_id=outsider.pk)
        )

        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_party_member")
        self.assertEqual(result["message"], "對方不是你的隊伍成員。")
        self.assertEqual(self.commander.db.inventory, [_POTION.key])
        self.assertFalse(outsider.db.inventory)
        self.assertFalse(self.aila.db.inventory)

    def test_success_returns_the_fixed_message_and_full_snapshot(self):
        self.commander.db.inventory = [_POTION.key, _POTION.key]

        result = _party_transfer_adapter(self.commander, self._payload(quantity=2))

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "transferred")
        self.assertEqual(result["message"], "你把 2 個測試藥水交給了艾拉。")
        self.assertEqual(result["affected_panels"], ())
        self.assertEqual(self.commander.db.inventory, [])
        self.assertEqual(self.aila.db.inventory, [_POTION.key, _POTION.key])

    def test_combat_rejection_maps_to_the_stable_code(self):
        self.commander.db.inventory = [_POTION.key]
        with patch(
            "world.rules.combat_session.is_in_active_session", return_value=True
        ):
            result = _party_transfer_adapter(self.commander, self._payload())
        self.assertEqual(
            result,
            {
                "outcome": "rejected",
                "code": "transfer_in_combat",
                "message": "戰鬥中無法交換物品。",
            },
        )

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_registered_with_an_empty_affected_panel_set(self):
        registry = build_production_action_registry()
        spec = registry.spec("party.transfer")
        self.assertIs(spec.validate_payload, validate_party_transfer_payload)
        self.assertIs(spec.adapter, _party_transfer_adapter)
        self.assertEqual(spec.affected_panels, ())
