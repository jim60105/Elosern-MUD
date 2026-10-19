"""Tests for the party actions (party-item-transfer, party-panel-v3-view-member)."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.party_actions import (
    PartyActionError,
    _party_view_member_adapter,
    _party_transfer_adapter,
    validate_party_transfer_payload,
    validate_party_view_member_payload,
)
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.rules.party import join_party
from world.rules.party_inventory import MAX_TRANSFER_QUANTITY
from world.rules.tests._combat_session_helpers import _race_key
from world.rules.unlock_notices import MemberUnlocks, unlock_flags
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

    @covers_requirement(
        "party-item-transfer::the-party-transfer-action-carries-exact-member-references"
    )
    def test_exact_payload_is_normalized(self):
        self.assertEqual(validate_party_transfer_payload(dict(_VALID)), _VALID)

    @covers_requirement(
        "party-item-transfer::the-party-transfer-action-carries-exact-member-references"
    )
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

    @covers_requirement(
        "party-item-transfer::the-party-transfer-action-carries-exact-member-references"
    )
    def test_success_returns_the_fixed_message_and_full_snapshot(self):
        self.commander.db.inventory = [_POTION.key, _POTION.key]

        result = _party_transfer_adapter(self.commander, self._payload(quantity=2))

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "transferred")
        self.assertEqual(result["message"], "你把 2 個測試藥水交給了艾拉。")
        self.assertEqual(result["affected_panels"], ())
        self.assertEqual(self.commander.db.inventory, [])
        self.assertEqual(self.aila.db.inventory, [_POTION.key, _POTION.key])

    @covers_requirement(
        "party-item-transfer::transfer-rejections-are-stable-and-observable"
    )
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
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe",
        "party-item-transfer::the-party-transfer-action-carries-exact-member-references",
    )
    def test_registered_with_an_empty_affected_panel_set(self):
        registry = build_production_action_registry()
        spec = registry.spec("party.transfer")
        self.assertIs(spec.validate_payload, validate_party_transfer_payload)
        self.assertIs(spec.adapter, _party_transfer_adapter)
        self.assertEqual(spec.affected_panels, ())


class PartyViewMemberPayloadTests(unittest.TestCase):
    """The ``party.view_member`` schema is exact and bounded."""

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_exact_payload_is_normalized(self):
        self.assertEqual(
            validate_party_view_member_payload(
                {
                    "member_id": 7,
                    "tab": "member",
                    "skill_key": None,
                    "item_key": None,
                }
            ),
            {
                "member_id": 7,
                "tab": "member",
                "skill_key": None,
                "item_key": None,
            },
        )
        self.assertEqual(
            validate_party_view_member_payload(
                {
                    "member_id": 7,
                    "tab": "skills",
                    "skill_key": "t_ember_burst",
                    "item_key": _POTION.key,
                }
            )["skill_key"],
            "t_ember_burst",
        )
        self.assertEqual(
            validate_party_view_member_payload(
                {
                    "member_id": 7,
                    "tab": "bag",
                    "skill_key": None,
                    "item_key": _POTION.key,
                }
            )["item_key"],
            _POTION.key,
        )
        for tab in ("member", "bag", "status", "skills", "lineage", "shop"):
            self.assertEqual(
                validate_party_view_member_payload(
                    {
                        "member_id": 1,
                        "tab": tab,
                        "skill_key": None,
                        "item_key": None,
                    }
                )["tab"],
                tab,
            )

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_each_malformed_payload_rejects(self):
        cases = (
            ("not an object", []),
            ("missing tab", {"member_id": 1, "skill_key": None, "item_key": None}),
            ("missing skill key", {"member_id": 1, "tab": "member", "item_key": None}),
            ("missing item key", {"member_id": 1, "tab": "member", "skill_key": None}),
            (
                "extra key",
                {
                    "member_id": 1,
                    "tab": "member",
                    "skill_key": None,
                    "item_key": None,
                    "x": 1,
                },
            ),
            ("unknown tab", {"member_id": 1, "tab": "detail", "skill_key": None, "item_key": None}),
            ("non-string tab", {"member_id": 1, "tab": 3, "skill_key": None, "item_key": None}),
            ("zero member", {"member_id": 0, "tab": "member", "skill_key": None, "item_key": None}),
            ("negative member", {"member_id": -1, "tab": "member", "skill_key": None, "item_key": None}),
            ("bool member", {"member_id": True, "tab": "member", "skill_key": None, "item_key": None}),
            ("string member", {"member_id": "7", "tab": "member", "skill_key": None, "item_key": None}),
            ("float member", {"member_id": 7.0, "tab": "member", "skill_key": None, "item_key": None}),
            (
                "over safe integer",
                {
                    "member_id": MAX_SAFE_INTEGER + 1,
                    "tab": "member",
                    "skill_key": None,
                    "item_key": None,
                },
            ),
            ("non-string skill", {"member_id": 1, "tab": "skills", "skill_key": 3, "item_key": None}),
            ("blank skill", {"member_id": 1, "tab": "skills", "skill_key": "  ", "item_key": None}),
            ("empty skill", {"member_id": 1, "tab": "skills", "skill_key": "", "item_key": None}),
            (
                "over-bound skill",
                {"member_id": 1, "tab": "skills", "skill_key": "k" * 65, "item_key": None},
            ),
            ("non-string item", {"member_id": 1, "tab": "bag", "skill_key": None, "item_key": 3}),
            ("blank item", {"member_id": 1, "tab": "bag", "skill_key": None, "item_key": "  "}),
            ("empty item", {"member_id": 1, "tab": "bag", "skill_key": None, "item_key": ""}),
            (
                "over-bound item",
                {"member_id": 1, "tab": "bag", "skill_key": None, "item_key": "k" * 65},
            ),
        )
        for label, payload in cases:
            with self.subTest(label=label):
                with self.assertRaises(PartyActionError):
                    validate_party_view_member_payload(payload)


class PartyViewMemberAdapterTests(EvenniaTestCase):
    """The adapter authorizes membership only and records a session selection."""

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
        self.room = create_object(Room, key="隊伍房間")
        self.other_room = create_object(Room, key="別處")
        self.commander = create_object(
            PlayerCharacter, key="指揮者", location=self.room
        )
        self.commander.race = _race_key()
        self.commander.apply_race_baseline()
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        self.session = SimpleNamespace(
            ndb=SimpleNamespace(),
            puppet=self.commander,
            protocol_key="webclient/websocket",
        )

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        join_party(npc, self.commander)
        return npc

    def _select(self, member_id, tab="member", skill_key=None, item_key=None):
        return _party_view_member_adapter(
            self.commander,
            {
                "member_id": member_id,
                "tab": tab,
                "skill_key": skill_key,
                "item_key": item_key,
            },
            self.session,
        )

    def _selection(self, actor=None):
        return build_presentation_context(
            self.session, actor or self.commander
        ).party_view

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    @covers_requirement(
        "webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection"
    )
    def test_success_records_the_selection_and_republishes_party(self):
        self.assertEqual(
            self._select(self.aila.pk),
            {
                "outcome": "success",
                "code": "viewing_member",
                "message": "已選擇檢視的隊伍成員。",
                "affected_panels": (
                    "party",
                    "party_member",
                    "character",
                    "party_inventory",
                    "item_holdings",
                    "lineage",
                    "services",
                ),
            },
        )
        self.assertEqual(
            self._selection(),
            PartyViewSelection(
                int(self.commander.pk), int(self.aila.pk), "member", None, None
            ),
        )

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    @covers_requirement(
        "webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection"
    )
    def test_the_selected_item_is_stored_and_an_unknown_key_clears_it(self):
        self._select(self.aila.pk, "bag", item_key=_POTION.key)
        self.assertEqual(self._selection().item_key, _POTION.key)
        self.assertEqual(
            self._selection(),
            PartyViewSelection(
                int(self.commander.pk),
                int(self.aila.pk),
                "bag",
                None,
                _POTION.key,
            ),
        )
        # A later selection without an item clears it.
        self._select(self.aila.pk, "bag")
        self.assertIsNone(self._selection().item_key)
        # An unknown registry key stores null rather than an invented selection.
        self._select(self.aila.pk, "bag", item_key="t_unregistered_item")
        self.assertIsNone(self._selection().item_key)

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_the_selected_skill_is_stored_with_the_selection(self):
        self._select(self.aila.pk, "skills", "t_group_heal")
        self.assertEqual(
            self._selection(),
            PartyViewSelection(
                int(self.commander.pk), int(self.aila.pk), "skills", "t_group_heal"
            ),
        )
        # A later selection without a skill clears it.
        self._select(self.aila.pk, "member")
        self.assertIsNone(self._selection().skill_key)

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_forged_member_is_refused_without_substitution(self):
        self._select(self.aila.pk)
        outsider = create_object(NPC, key="陌客", location=self.room)
        outsider.race = _race_key()
        outsider.apply_race_baseline()
        for member_id in (outsider.pk, 999_999):
            with self.subTest(member_id=member_id):
                result = self._select(member_id)
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], "not_party_member")
                self.assertNotIn("affected_panels", result)
                # The previous selection stays exactly as it was.
                self.assertEqual(self._selection().member_id, int(self.aila.pk))

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_absent_but_effective_member_is_accepted(self):
        self.aila.location = self.other_room
        result = self._select(self.aila.pk, "bag")
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            self._selection(),
            PartyViewSelection(int(self.commander.pk), int(self.aila.pk), "bag", None),
        )

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_selection_survives_the_possession_transition(self):
        self._select(self.kahn.pk, "status")
        # Possession puppets the companion; the party-panel owner stays the
        # commander through the companion's back-reference.
        self.session.puppet = self.kahn
        self.assertEqual(
            self._selection(self.kahn),
            PartyViewSelection(
                int(self.commander.pk), int(self.kahn.pk), "status", None
            ),
        )

    @covers_requirement(
        "webclient-party-panel::opening-a-member-s-skills-clears-that-member-s-unread-mark"
    )
    def test_skills_tab_clears_only_that_members_unread_mark(self):
        self.session.ndb.party_unlocks = {
            int(self.aila.pk): MemberUnlocks(True, frozenset({"t_group_heal"})),
            int(self.kahn.pk): MemberUnlocks(True, frozenset({"t_guard"})),
        }
        # A non-skills tab never clears a dot.
        self._select(self.aila.pk, "member")
        self.assertIs(unlock_flags(self.session)[int(self.aila.pk)].unread, True)
        self._select(self.aila.pk, "skills")
        flags = unlock_flags(self.session)
        self.assertIs(flags[int(self.aila.pk)].unread, False)
        self.assertIs(flags[int(self.kahn.pk)].unread, True)

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe",
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session",
    )
    def test_registered_with_the_party_panel_affected_set(self):
        registry = build_production_action_registry()
        spec = registry.spec("party.view_member")
        self.assertIs(spec.validate_payload, validate_party_view_member_payload)
        self.assertIs(spec.adapter, _party_view_member_adapter)
        self.assertEqual(
            spec.affected_panels,
            (
                "party",
                "party_member",
                "character",
                "party_inventory",
                "item_holdings",
                "services",
            ),
        )

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    def test_every_holding_mutation_republishes_the_holdings_panel(self):
        # Selection and every partial-publication mutation that can change a
        # member's held count or the combat transfer bar names the panel;
        # transfers, item use and equipment toggles publish full snapshots.
        registry = build_production_action_registry()
        for action_id in (
            "party.view_member",
            "shop.buy",
            "shop.sell",
            "guild.quest_turnin",
            "guild.exam_request",
            "explore.engage",
        ):
            with self.subTest(action=action_id):
                self.assertIn(
                    "item_holdings",
                    registry.spec(action_id).affected_panels,
                )
