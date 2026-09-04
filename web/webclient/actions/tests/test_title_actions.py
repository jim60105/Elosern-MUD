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
    AFFECTED_CODEX,
    AFFECTED_EQUIP,
    BALLOT_UNAVAILABLE_CODE,
    EQUIP_REJECTED_CODE,
    EQUIP_REJECTED_MESSAGE,
    INDEX_OUT_OF_RANGE_CODE,
    NO_BALLOT_CODE,
    REMOVAL_EQUIPPED_CODE,
    REMOVAL_LAST_CODE,
    REMOVAL_UNKNOWN_CODE,
    TitleActionError,
    _title_accept_adapter,
    _title_decline_adapter,
    _title_equip_adapter,
    _title_remove_adapter,
    validate_title_accept_payload,
    validate_title_decline_payload,
    validate_title_equip_payload,
    validate_title_remove_payload,
)
from world.rules.clock import get_world_clock
from world.rules.titles import (
    PENDING_BALLOT_KEY,
    TITLE_COLLECTION_KEY,
    bank_fixed,
    banked_epithets,
    bank_epithet,
    decline_records,
    declined_digest,
    grant_first_quest_epithet,
    grant_rank_title,
    persist_nomination_ballot,
    read_pending_ballot,
    read_title_state,
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

    def test_registry_wires_both_actions_with_the_ballot_and_codex_panels(self):
        registry = build_production_action_registry()
        for action_id, validator, adapter in (
            ("title.accept", validate_title_accept_payload, _title_accept_adapter),
            ("title.decline", validate_title_decline_payload, _title_decline_adapter),
        ):
            spec = registry.spec(action_id)
            self.assertIs(spec.validate_payload, validator)
            self.assertIs(spec.adapter, adapter)
            self.assertEqual(spec.affected_panels, AFFECTED_BALLOT)
            self.assertEqual(spec.affected_panels, ("title_ballot", "title_codex"))


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


class TitleCodexValidatorTests(unittest.TestCase):
    def test_equip_accepts_both_kinds_within_bounds(self):
        self.assertEqual(
            validate_title_equip_payload({"kind": "fixed", "identifier": "g_f_rank"}),
            {"kind": "fixed", "identifier": "g_f_rank"},
        )
        self.assertEqual(
            validate_title_equip_payload({"kind": "epithet", "identifier": "夜襲之人"}),
            {"kind": "epithet", "identifier": "夜襲之人"},
        )
        at_cap = "長" * 64
        self.assertEqual(
            validate_title_equip_payload({"kind": "epithet", "identifier": at_cap})["identifier"],
            at_cap,
        )

    def test_equip_rejects_every_other_shape(self):
        for payload in (
            {},
            {"kind": "fixed"},
            {"identifier": "g_f_rank"},
            {"kind": "widget", "identifier": "g_f_rank"},
            {"kind": "Fixed", "identifier": "g_f_rank"},
            {"kind": "fixed", "identifier": ""},
            {"kind": "fixed", "identifier": "長" * 65},
            {"kind": "fixed", "identifier": 7},
            {"kind": "fixed", "identifier": "g_f_rank", "display": "x"},
            "not-a-dict",
            None,
        ):
            with self.subTest(payload=str(payload)[:60]):
                with self.assertRaises(TitleActionError):
                    validate_title_equip_payload(payload)

    def test_remove_requires_exactly_one_bounded_display(self):
        self.assertEqual(
            validate_title_remove_payload({"display": "夜襲之人"}),
            {"display": "夜襲之人"},
        )
        for payload in (
            {},
            {"display": ""},
            {"display": "長" * 65},
            {"display": 7},
            {"display": "夜襲之人", "confirm": True},
            {"kind": "epithet", "identifier": "夜襲之人"},
            "not-a-dict",
            None,
        ):
            with self.subTest(payload=str(payload)[:60]):
                with self.assertRaises(TitleActionError):
                    validate_title_remove_payload(payload)

    def test_registry_wires_equip_and_remove_with_their_panels(self):
        registry = build_production_action_registry()
        equip = registry.spec("title.equip")
        self.assertIs(equip.validate_payload, validate_title_equip_payload)
        self.assertIs(equip.adapter, _title_equip_adapter)
        self.assertEqual(equip.affected_panels, AFFECTED_EQUIP)
        self.assertEqual(equip.affected_panels, ("title_codex", "character"))
        remove = registry.spec("title.remove")
        self.assertIs(remove.validate_payload, validate_title_remove_payload)
        self.assertIs(remove.adapter, _title_remove_adapter)
        self.assertEqual(remove.affected_panels, AFFECTED_CODEX)


class TitleCodexAdapterTests(EvenniaTestCase):
    def setUp(self):
        get_world_clock()
        self.player = create_object(PlayerCharacter, key="codex actor")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.messages = []
        self.player.msg = lambda text, **kwargs: self.messages.append(text)

    def _bank_pair(self):
        grant_rank_title(self.player, "F")
        grant_first_quest_epithet(self.player)
        bank_epithet(self.player, "破城先鋒", "率先破門。", 500)

    def test_equip_fixed_banks_then_swaps_with_the_equip_affected_pair(self):
        bank_fixed(self.player, "g_f_rank", 1)
        bank_fixed(self.player, "g_e_rank", 2)
        result = _title_equip_adapter(
            self.player, {"kind": "fixed", "identifier": "g_e_rank"}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "equipped")
        self.assertEqual(result["message"], "你掛上稱號：E級斥候")
        self.assertEqual(result["affected_panels"], AFFECTED_EQUIP)
        self.assertEqual(read_title_state(self.player)[1]["fixed"], "g_e_rank")
        self.assertEqual(self.messages, ["你掛上稱號：E級斥候"])

    def test_equip_epithet_swaps_between_banked_rows(self):
        self._bank_pair()
        result = _title_equip_adapter(
            self.player, {"kind": "epithet", "identifier": "破城先鋒"}
        )
        self.assertEqual(result["message"], "你掛上異名：破城先鋒")
        self.assertEqual(read_title_state(self.player)[1]["epithet"], "破城先鋒")

    def test_unbanked_or_wrong_kind_targets_share_one_stable_rejection(self):
        self._bank_pair()
        for payload in (
            {"kind": "fixed", "identifier": "g_s_rank"},
            {"kind": "fixed", "identifier": "不存在"},
            {"kind": "epithet", "identifier": "g_f_rank"},
            {"kind": "epithet", "identifier": "未擁有"},
        ):
            with self.subTest(payload=str(payload)[:60]):
                before = read_title_state(self.player)
                result = _title_equip_adapter(self.player, payload)
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], EQUIP_REJECTED_CODE)
                self.assertEqual(result["message"], EQUIP_REJECTED_MESSAGE)
                self.assertEqual(read_title_state(self.player), before)
        self.assertEqual(self.messages, [])

    def test_equip_maps_malformed_state_to_the_unavailable_rejection(self):
        self.player.attributes.add(TITLE_COLLECTION_KEY, "not-a-list")
        result = _title_equip_adapter(
            self.player, {"kind": "fixed", "identifier": "g_f_rank"}
        )
        self.assertEqual(result["code"], BALLOT_UNAVAILABLE_CODE)

    def test_remove_deletes_through_the_sole_path_with_the_event_line(self):
        self._bank_pair()
        result = _title_remove_adapter(self.player, {"display": "破城先鋒"})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "removed")
        self.assertEqual(result["message"], "codex actor放下了異名：破城先鋒")
        self.assertEqual(result["affected_panels"], AFFECTED_CODEX)
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.player)],
            ["南門新客"],
        )
        self.assertEqual(self.messages, [result["message"]])

    def test_removal_gates_map_to_their_stable_rejections(self):
        self._bank_pair()
        for display, code in (
            ("不存在", REMOVAL_UNKNOWN_CODE),
            ("g_f_rank", REMOVAL_UNKNOWN_CODE),
            ("南門新客", REMOVAL_EQUIPPED_CODE),
        ):
            with self.subTest(display=display):
                before = read_title_state(self.player)
                result = _title_remove_adapter(self.player, {"display": display})
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], code)
                self.assertEqual(read_title_state(self.player), before)
        sole = create_object(PlayerCharacter, key="codex sole")
        sole.race = "human"
        sole.apply_race_baseline()
        sole.msg = lambda text, **kwargs: None
        grant_first_quest_epithet(sole)
        result = _title_remove_adapter(sole, {"display": "南門新客"})
        self.assertEqual(result["code"], REMOVAL_LAST_CODE)
        self.assertEqual(self.messages, [])

    def test_remove_maps_malformed_state_to_the_unavailable_rejection(self):
        self._bank_pair()
        self.player.attributes.add(TITLE_COLLECTION_KEY, "not-a-list")
        result = _title_remove_adapter(self.player, {"display": "破城先鋒"})
        self.assertEqual(result["code"], BALLOT_UNAVAILABLE_CODE)
