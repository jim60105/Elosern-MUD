"""Title ballot answer adapters, validators, and registry wiring (change G).

Exercises the ``title.accept`` / ``title.decline`` exact payload validators,
the rules-writer delegation (bank + auto-equip discipline stays in
``world.rules.titles``), the stable rejection surface mirrored from the
telnet ``title`` command, and the targeted ``title_ballot`` affected-panel
declaration that makes the menu disappear immediately.
"""

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from tools.spec_traceability import covers_requirement
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.title_actions import (
    AFFECTED_BALLOT,
    BALLOT_UNAVAILABLE_CODE,
    INDEX_OUT_OF_RANGE_CODE,
    NO_BALLOT_CODE,
    TitleActionError,
    _title_accept_adapter,
    _title_decline_adapter,
    validate_title_accept_payload,
    validate_title_decline_payload,
)
from world.rules.clock import get_world_clock
from world.rules.titles import (
    PENDING_BALLOT_KEY,
    banked_epithets,
    bank_epithet,
    decline_records,
    declined_digest,
    persist_nomination_ballot,
    read_pending_ballot,
)

_BALLOT = [
    {"display": "破城先鋒", "basis": "率先破門。"},
    {"display": "夜襲之人", "basis": "夜半三度出入敵陣。"},
    {"display": "不屈之壁", "basis": "重傷仍守住隘口。"},
]


class TitleBallotValidatorTests(unittest.TestCase):
    def test_accept_accepts_one_index_in_range(self):
        for index in (1, 2, 3):
            self.assertEqual(
                validate_title_accept_payload({"index": index}), {"index": index}
            )

    def test_accept_rejects_every_other_shape(self):
        for payload in (
            {},
            {"index": 0},
            {"index": 4},
            {"index": -1},
            {"index": True},
            {"index": "1"},
            {"index": 1.5},
            {"index": 1, "display": "破城先鋒"},
            {"choice": 1},
            "not-a-dict",
            None,
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(TitleActionError):
                    validate_title_accept_payload(payload)

    def test_decline_requires_the_exact_empty_payload(self):
        self.assertEqual(validate_title_decline_payload({}), {})
        for payload in ({"index": 1}, {"reason": "no"}, "not-a-dict", None):
            with self.subTest(payload=payload):
                with self.assertRaises(TitleActionError):
                    validate_title_decline_payload(payload)

    def test_registry_wires_both_actions_with_the_ballot_panel(self):
        registry = build_production_action_registry()
        for action_id, validator, adapter in (
            ("title.accept", validate_title_accept_payload, _title_accept_adapter),
            ("title.decline", validate_title_decline_payload, _title_decline_adapter),
        ):
            spec = registry.spec(action_id)
            self.assertIs(spec.validate_payload, validator)
            self.assertIs(spec.adapter, adapter)
            self.assertEqual(spec.affected_panels, AFFECTED_BALLOT)
            self.assertEqual(spec.affected_panels, ("title_ballot",))


class TitleBallotAdapterTests(EvenniaTestCase):
    def setUp(self):
        get_world_clock()
        self.player = create_object(PlayerCharacter, key="ballot answerer")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.messages = []
        self.player.msg = lambda text, **kwargs: self.messages.append(text)

    def _deliver_ballot(self, entries=None):
        self.assertTrue(
            persist_nomination_ballot(self.player, entries or _BALLOT)
        )

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_accept_banks_the_numbered_choice_and_consumes_the_ballot(self):
        self._deliver_ballot()
        result = _title_accept_adapter(self.player, {"index": 2})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "accepted")
        self.assertEqual(result["message"], "你採納異名：夜襲之人")
        self.assertEqual(result["affected_panels"], AFFECTED_BALLOT)
        self.assertEqual(self.messages, ["你採納異名：夜襲之人"])
        self.assertEqual(read_pending_ballot(self.player), ())
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.player)],
            ["夜襲之人"],
        )
        self.assertEqual(
            banked_epithets(self.player)[0]["origin_quote"], "夜半三度出入敵陣。"
        )

    def test_accepting_a_duplicate_display_reports_prior_ownership_and_consumes(self):
        bank_epithet(self.player, "破城先鋒", "舊事蹟。", get_world_clock().tick)
        self._deliver_ballot()
        result = _title_accept_adapter(self.player, {"index": 1})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["message"], "你早已擁有異名：破城先鋒")
        self.assertEqual(read_pending_ballot(self.player), ())

    def test_accept_without_a_ballot_is_a_stable_no_change_rejection(self):
        result = _title_accept_adapter(self.player, {"index": 1})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], NO_BALLOT_CODE)
        self.assertEqual(result["message"], "目前沒有待決的異名提名。")
        self.assertNotIn("affected_panels", result)
        self.assertEqual(banked_epithets(self.player), ())
        self.assertEqual(self.messages, [])

    def test_accept_index_beyond_the_live_ballot_is_out_of_range(self):
        self._deliver_ballot(_BALLOT[:2])
        before = decline_records(self.player)
        result = _title_accept_adapter(self.player, {"index": 3})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], INDEX_OUT_OF_RANGE_CODE)
        self.assertEqual(result["message"], "沒有這個編號的提名。")
        # The ballot survives a rejected answer unchanged (consent rule).
        self.assertEqual(len(read_pending_ballot(self.player)), 2)
        self.assertEqual(decline_records(self.player), before)

    def test_accept_maps_malformed_title_state_to_the_unavailable_rejection(self):
        self._deliver_ballot()
        self.player.attributes.add("title_collection", "bogus")
        result = _title_accept_adapter(self.player, {"index": 1})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], BALLOT_UNAVAILABLE_CODE)
        self.assertEqual(result["message"], "你的稱號冊暫時無法閱讀。")

    def test_accept_maps_a_malformed_ballot_to_the_unavailable_rejection(self):
        self.player.attributes.add(PENDING_BALLOT_KEY, [{"nope": True}])
        result = _title_accept_adapter(self.player, {"index": 1})
        self.assertEqual(result["code"], BALLOT_UNAVAILABLE_CODE)
        self.assertEqual(banked_epithets(self.player), ())

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_decline_consumes_the_ballot_records_the_rejection_line(self):
        self._deliver_ballot()
        result = _title_decline_adapter(self.player, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "declined")
        self.assertEqual(result["affected_panels"], AFFECTED_BALLOT)
        self.assertEqual(read_pending_ballot(self.player), ())
        self.assertEqual(
            declined_digest(self.player), ("破城先鋒", "夜襲之人", "不屈之壁")
        )
        self.assertEqual(self.messages, [result["message"]])

    def test_decline_message_is_the_rendered_decline_event(self):
        # The decline message is the decline EventLog rendered as plain
        # text — the exact telnet line (commands/title.py _decline).
        self._deliver_ballot(_BALLOT[:2])
        result = _title_decline_adapter(self.player, {})
        self.assertEqual(
            result["message"],
            "ballot answerer拒絕了異名提名：破城先鋒、夜襲之人",
        )

    def test_decline_without_a_ballot_is_a_stable_no_change_rejection(self):
        result = _title_decline_adapter(self.player, {})
        self.assertEqual(result["code"], NO_BALLOT_CODE)
        self.assertEqual(result["message"], "目前沒有待決的異名提名。")
        self.assertEqual(self.messages, [])

    def test_decline_maps_malformed_title_state_to_the_unavailable_rejection(self):
        self._deliver_ballot()
        self.player.attributes.add(PENDING_BALLOT_KEY, [{"nope": True}])
        result = _title_decline_adapter(self.player, {})
        self.assertEqual(result["code"], BALLOT_UNAVAILABLE_CODE)
