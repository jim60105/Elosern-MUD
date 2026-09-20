"""The name-roll action over the synthetic name corpus."""
from web.webclient.actions.creation_actions import (
    _creation_activate_adapter,
    _creation_concept_adapter,
    _creation_custom_adapter,
    _creation_preset_adapter,
    _creation_reset_adapter,
    validate_creation_activate_payload,
    validate_creation_concept_payload,
    validate_creation_custom_payload,
    validate_creation_preset_payload,
    validate_creation_reset_payload,
)
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    activate_player_character,
    resolve_starting_profile,
)
from tools.spec_traceability import covers_requirement
from copy import deepcopy
from unittest.mock import patch
from world.rules.creation_wizard import draft_fingerprint, read_draft, save_custom_draft
import unittest
from ._support import (
    CreationActionBase,
    _T_NAME_POOL,
    _T_NAME_POOL_UNBOUND_ONLY,
    _T_OTHER_RACE,
    _T_RACE,
    _T_SUBRACE,
    _open_t_name_corpus,
    custom_payload,
    custom_request,
)


class NameRollActionTests(CreationActionBase):
    """The result-only name roll: semantic gate, zero writes, bound packs."""

    RACE = _T_RACE
    SUBRACE = _T_SUBRACE

    def _roll(self, race=RACE, subrace=SUBRACE, sex="female"):
        from web.webclient.actions.creation_actions import (
            _creation_roll_name_adapter,
        )

        return _creation_roll_name_adapter(
            self.character, {"race": race, "subrace": subrace, "sex": sex}
        )

    def setUp(self):
        super().setUp()
        _open_t_name_corpus(self)

    def _assert_result_only_frames(self, marker_index_start: int) -> None:
        for entry in self.fake_session.sent[marker_index_start:]:
            self.assertNotIn(
                "ui_snapshot", entry, "a name roll must not publish a snapshot"
            )
            self.assertNotIn(
                "ui_update", entry, "a name roll must not publish an update"
            )

    def _attribute_snapshot(self):
        return {
            key: (
                self.character.attributes.has(key),
                deepcopy(self.character.attributes.get(key))
                if self.character.attributes.has(key)
                else None,
            )
            for key in (
                "age", "apparent_age", "race", "subrace", "sex",
                "creation_pending", "creation_draft", "skills", "persona",
                "affinity_elements",
            )
        }

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_valid_roll_returns_name_with_zero_writes_and_no_publish(self):
        from world.rules.character_creation import _validate_name

        before_attributes = self._attribute_snapshot()
        frames_before = len(self.fake_session.sent)
        self._dispatch(
            self._envelope(
                "creation.roll_name",
                {"race": _T_RACE, "subrace": _T_SUBRACE, "sex": "female"},
                request_id="roll-1",
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "name_rolled")
        name = result["data"]["display_name"]
        self.assertEqual(_validate_name(name), name)
        self.assertNotIn("no_presentation", result)
        self.assertEqual(self._attribute_snapshot(), before_attributes)
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)
        self._assert_result_only_frames(frames_before)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_activated_character_cannot_roll(self):
        import web.webclient.actions.creation_actions as actions

        _creation_custom_adapter(self.character, custom_payload())
        activate_player_character(self.account, self.character, custom_request())
        self.assertFalse(self.character.creation_pending)

        def spy(*args, **kwargs):
            raise AssertionError("the roller must never be reached")

        calls: list = []
        with patch.object(actions, "roll_name_for_race", spy):
            frames_before = len(self.fake_session.sent)
            result = self._roll(_T_RACE, _T_SUBRACE, "female")
            calls.append(result)
        (result,) = calls
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        self.assertNotIn("data", result)
        self._assert_result_only_frames(frames_before)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_dirty_inputs_reject_before_the_roller(self):
        import web.webclient.actions.creation_actions as actions
        from world.rules.creation_messages import rejection_code

        calls: list = []

        def spy(*args, **kwargs):
            calls.append(args)
            raise AssertionError("the roller must never be reached")

        cases = {
            ("t_not_a_race", None, None): "unknown_race",
            ("t_not_a_race", _T_SUBRACE, None): "unknown_race",
            (_T_OTHER_RACE.key, _T_SUBRACE, None): "incompatible_subrace",
            (_T_RACE, "not_a_subrace", None): "unknown_subrace",
            (None, _T_SUBRACE, None): "incompatible_subrace",
            (_T_RACE, _T_SUBRACE, "nope"): "unknown_sex",
        }
        with patch.object(actions, "roll_name_for_race", spy):
            for (race, subrace, sex), expected_code in cases.items():
                with self.subTest(race=race, subrace=subrace, sex=sex):
                    frames_before = len(self.fake_session.sent)
                    result = self._roll(race, subrace, sex)
                    self.assertEqual(result["outcome"], "rejected")
                    self.assertEqual(result["code"], expected_code)
                    self.assertEqual(
                        rejection_code(result["code"]), expected_code
                    )
                    self.assertNotIn("data", result)
                    self.assertTrue(result["no_presentation"])
                    self._assert_result_only_frames(frames_before)
        self.assertEqual(calls, [], "rejected rolls must not reach the roller")

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_unselected_race_falls_back_only_to_bound_packs(self):
        from world.lore.names import NAME_SEPARATOR

        names = {
            self._roll(None, None, None)["data"]["display_name"]
            for _ in range(60)
        }
        self.assertTrue(names)
        for name in names:
            given, separator, surname = name.partition(NAME_SEPARATOR)
            self.assertTrue(separator)
            self.assertIn(given, _T_NAME_POOL, name)
            self.assertIn(surname, _T_NAME_POOL, name)
            self.assertNotIn(given, _T_NAME_POOL_UNBOUND_ONLY, name)
            self.assertNotIn(surname, _T_NAME_POOL_UNBOUND_ONLY, name)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_roller_receives_the_module_singleton_rng(self):
        import web.webclient.actions.creation_actions as actions

        seen: list = []

        def spy(race, sex, rng):
            seen.append(rng)
            return "測試名"

        with patch.object(actions, "roll_name_for_race", spy):
            self._roll()
            self._roll()
        self.assertEqual(len(seen), 2)
        self.assertIs(seen[0], seen[1])
        self.assertIs(seen[0], actions._ROLL_NAME_RNG)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_sex_channel_flows_from_custom_save_to_activation(self):
        self._dispatch(
            self._envelope(
                "creation.custom",
                custom_payload(sex="female"),
                request_id="custom-sex-1",
            )
        )
        self.assertEqual(self._last_result()["outcome"], "success")
        self.assertEqual(read_draft(self.character)["sex"], "female")
        self._dispatch(
            self._envelope("creation.activate", {}, request_id="activate-sex-1")
        )
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.sex, "female")
        self.assertIsNone(read_draft(self.character))

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_dirty_sex_rejected_by_the_deterministic_service(self):
        frames_before = len(self.fake_session.sent)
        self._dispatch(
            self._envelope(
                "creation.custom",
                custom_payload(sex="nope"),
                request_id="custom-dirty-1",
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_sex")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    @covers_requirement("webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping")
    def test_roll_result_round_trips_the_wire_validator(self):
        from web.webclient.presentation.protocol import validate_ui_action_result

        self._dispatch(
            self._envelope(
                "creation.roll_name",
                {"race": None, "subrace": None, "sex": "male"},
                request_id="roll-wire-1",
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        # The captured frame IS the wire envelope; the server-side mirror of
        # the JS validator must accept it unchanged (data slot consumption).
        envelope = next(
            entry["ui_action_result"][0][0]
            for entry in reversed(self.fake_session.sent)
            if "ui_action_result" in entry
        )
        validated = validate_ui_action_result(envelope)
        self.assertEqual(validated["outcome"], "success")
        self.assertEqual(
            validated["data"], {"display_name": result["data"]["display_name"]}
        )

if __name__ == "__main__":
    unittest.main()
