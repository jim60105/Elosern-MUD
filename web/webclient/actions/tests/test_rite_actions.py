"""The ``explore.landmark_rite`` action: exact payload, delivery and refusals.

The action settles through the deterministic core (``world.rules.landmark_rites``)
and returns the committed scene as an authored-scene delivery. These tests pin
the three boundaries the browser depends on: the payload admits only an option
and a nullable performer, the result data carries ``scene_revision`` (never the
reserved key ``revision``), and every refusal is the settlement's own stable code
with nothing written.
"""

from __future__ import annotations

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from web.webclient.actions.dispatcher import _normalize_result, _result_envelope
from web.webclient.actions.exploration_actions import ExplorationActionError
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.rite_actions import (
    FAILED_MESSAGE,
    landmark_rite_adapter,
    rite_completion_line,
    rite_delivery,
    rite_scene_text,
    validate_landmark_rite_payload,
)
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    new_presentation_epoch,
    validate_ui_action_result,
)
from world.lore.scenes import Narration, Scene, Speech, line_to_dict
from world.rules.clock import get_world_clock
from world.rules.landmark_rites import REFUSAL_MESSAGES, RitePlan, RiteResult, RiteSite
from world.rules.tests.rite_fixtures import (
    DISTRICT_KEY,
    GUARDIAN_NAME,
    LANDMARK_NAME,
    SHARED,
    SOLO,
    RiteSettlementFixture,
)

_PURE_NARRATION = "測試敘述。"
_PURE_ACTOR_SPEECH = "測試自語。"
_PURE_HOST_SPEECH = "測試守護對{name}說話。"


def _pure_result(
    *,
    scene: Scene,
    option,
    perspective: str,
    body_key: str = "測試同伴",
) -> RiteResult:
    """One result value over a standalone synthetic scene, without a database."""
    plan = RitePlan(
        owner=SimpleNamespace(key="測試主角", pk=7),
        body=SimpleNamespace(key=body_key, pk=11),
        site=RiteSite(
            district_key="t_district",
            district_name="測試丘陵",
            landmark_name=LANDMARK_NAME,
            archetype=option_archetype(option),
        ),
        option=option,
        perspective=perspective,
    )
    return RiteResult(
        plan=plan,
        scene=scene,
        tick=150,
        elapsed_seconds=option.seconds,
        first_completion=True,
        climax=True,
        operation_id="t_rite_operation",
    )


def option_archetype(option):
    """The synthetic archetype holding one option, for the pure helper tests."""
    from world.lore.rites.shape import RiteArchetype

    return RiteArchetype(
        key="t_archetype",
        guardian_name_zh=GUARDIAN_NAME,
        guardian_form_zh="測試形體",
        options=(option,),
    )


def _three_line_scene() -> Scene:
    return Scene(
        scene_id="t_rite.pure",
        revision="r1",
        lines=(
            Narration(text=_PURE_NARRATION),
            Speech(speaker="actor", text=_PURE_ACTOR_SPEECH),
            Speech(speaker="host", text=_PURE_HOST_SPEECH),
        ),
    )


class RiteActionPayloadTests(unittest.TestCase):
    def test_the_exact_payload_is_normalized(self):
        self.assertEqual(
            validate_landmark_rite_payload({"option": "t_solo", "member_id": None}),
            {"option": "t_solo", "member_id": None},
        )
        self.assertEqual(
            validate_landmark_rite_payload({"option": "t_solo", "member_id": 42}),
            {"option": "t_solo", "member_id": 42},
        )

    def test_an_extra_or_missing_field_is_rejected(self):
        for payload in (
            {"option": "t_solo"},
            {"member_id": None},
            {"option": "t_solo", "member_id": None, "district_key": "t_district"},
            {"option": "t_solo", "member_id": None, "request_identity": {}},
            {},
            None,
            [],
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ExplorationActionError):
                    validate_landmark_rite_payload(payload)

    def test_a_malformed_option_is_rejected(self):
        for option in ("", "T_solo", "9solo", "t-solo", "t_solo_x" * 5, 7, None, True):
            with self.subTest(option=option):
                with self.assertRaises(ExplorationActionError):
                    validate_landmark_rite_payload(
                        {"option": option, "member_id": None}
                    )

    def test_a_boolean_or_out_of_range_member_id_is_rejected(self):
        for member_id in (True, False, 0, -1, 1.5, "7", 9_007_199_254_740_992):
            with self.subTest(member_id=member_id):
                with self.assertRaises(ExplorationActionError):
                    validate_landmark_rite_payload(
                        {"option": "t_solo", "member_id": member_id}
                    )


class RiteRenderingTests(unittest.TestCase):
    def test_the_self_delivery_carries_the_scene_in_authored_order(self):
        scene = _three_line_scene()
        result = _pure_result(scene=scene, option=SOLO, perspective="self")

        delivery = rite_delivery(result)

        self.assertEqual(delivery["kind"], "formal")
        self.assertEqual(delivery["delivery_id"], "rite:t_district:solo:150")
        self.assertEqual(delivery["scene_id"], scene.scene_id)
        self.assertEqual(delivery["scene_revision"], scene.revision)
        self.assertNotIn("revision", delivery)
        self.assertEqual(delivery["actor_name"], "你")
        self.assertEqual(delivery["guardian_name"], GUARDIAN_NAME)
        self.assertEqual(
            delivery["lines"], [line_to_dict(line) for line in scene.lines]
        )
        # The self perspective never substitutes the authored placeholder.
        self.assertEqual(delivery["lines"][2]["text"], _PURE_HOST_SPEECH)

    def test_the_watch_delivery_names_the_performing_companion(self):
        scene = _three_line_scene()
        result = _pure_result(scene=scene, option=SHARED, perspective="watch")

        delivery = rite_delivery(result)

        self.assertEqual(delivery["actor_name"], "測試同伴")
        self.assertEqual(delivery["lines"][2]["text"], "測試守護對測試同伴說話。")
        self.assertNotIn(
            "{name}", "".join(line["text"] for line in delivery["lines"])
        )

    def test_the_scene_text_renders_each_line_with_its_speaker(self):
        result = _pure_result(
            scene=_three_line_scene(), option=SHARED, perspective="watch"
        )

        self.assertEqual(
            rite_scene_text(result),
            "\n".join(
                (
                    _PURE_NARRATION,
                    f"測試同伴：{_PURE_ACTOR_SPEECH}",
                    "測試守護：測試守護對測試同伴說話。",
                )
            ),
        )

    def test_the_completion_line_names_the_performer(self):
        self.assertEqual(
            rite_completion_line(
                _pure_result(scene=_three_line_scene(), option=SOLO, perspective="self")
            ),
            f"你完成了{LANDMARK_NAME}的儀式。",
        )
        self.assertEqual(
            rite_completion_line(
                _pure_result(
                    scene=_three_line_scene(), option=SHARED, perspective="watch"
                )
            ),
            f"測試同伴完成了{LANDMARK_NAME}的儀式。",
        )


class RiteActionTests(RiteSettlementFixture):
    """One settlement reached through the registered adapter."""

    def _identity(self) -> dict[str, str]:
        return {
            "epoch": new_presentation_epoch(),
            "request_id": uuid4().hex,
        }

    def _adapter_payload(self, option: str, member_id=None, *, identity=None):
        return {
            **validate_landmark_rite_payload(
                {"option": option, "member_id": member_id}
            ),
            "request_identity": identity or self._identity(),
        }

    def settle(self, option: str, member_id=None, *, identity=None):
        """Dispatch one request through the adapter, delivering its callbacks."""
        with self.captureOnCommitCallbacks(execute=True):
            return landmark_rite_adapter(
                self.player,
                self._adapter_payload(option, member_id, identity=identity),
            )

    def test_the_solo_result_carries_the_self_scene_and_first_completion(self):
        with patch.object(self.player, "msg") as message:
            result = self.settle("solo")

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "explore.landmark_rite")
        self.assertEqual(result["affected_panels"], ())
        self.assertEqual(result["message"], f"你完成了{LANDMARK_NAME}的儀式。")
        message.assert_called_once_with(result["message"])
        delivery = result["data"]["delivery"]
        self.assertEqual(delivery["kind"], "formal")
        self.assertTrue(1 <= len(delivery["delivery_id"]) <= 128)
        self.assertTrue(delivery["delivery_id"].isascii())
        self.assertEqual(delivery["scene_id"], SOLO.self_scene.scene_id)
        self.assertEqual(delivery["scene_revision"], SOLO.self_scene.revision)
        self.assertEqual(delivery["actor_name"], "你")
        self.assertEqual(delivery["guardian_name"], GUARDIAN_NAME)
        self.assertEqual(
            delivery["lines"], [line_to_dict(line) for line in SOLO.self_scene.lines]
        )
        self.assertEqual(delivery["lines"][2]["text"], "測試守護對{name}說話。")
        self.assertTrue(result["data"]["first_completion"])

    def test_a_companion_request_delivers_the_watch_scene(self):
        result = self.settle("shared", self.companion.id)

        delivery = result["data"]["delivery"]
        self.assertEqual(delivery["actor_name"], self.companion.key)
        self.assertEqual(delivery["scene_id"], SHARED.watch_scene.scene_id)
        self.assertEqual(delivery["lines"][2]["text"], f"測試守護對{self.companion.key}說話。")
        self.assertEqual(
            result["message"],
            f"{self.companion.key}完成了{LANDMARK_NAME}的儀式。",
        )
        self.assertEqual(self.companion.sexual.climax_today, 1)
        self.assertEqual(self.player.sexual.climax_today, 0)

    def test_a_request_away_from_the_landmark_is_rejected_unchanged(self):
        self.player.location = self.source
        before = self.world_state()

        result = self.settle("solo")

        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "rite_no_landmark")
        self.assertEqual(result["message"], REFUSAL_MESSAGES["rite_no_landmark"])
        self.assertNotIn("data", result)
        # The stable code survives the dispatcher's result normalization: a
        # refusal is never rewritten into the internal-error envelope.
        self.assertEqual(_normalize_result(result)["code"], "rite_no_landmark")
        self.assert_unchanged(before)

    def test_an_unknown_option_is_rejected_unchanged(self):
        before = self.world_state()

        result = self.settle("t_none")

        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "rite_unknown_option")
        self.assertEqual(result["message"], REFUSAL_MESSAGES["rite_unknown_option"])
        self.assertNotIn("data", result)
        self.assert_unchanged(before)

    def test_two_requests_with_one_identity_settle_once(self):
        identity = self._identity()
        tick_before = get_world_clock().tick

        first = self.settle("solo", identity=identity)
        replay = landmark_rite_adapter(
            self.player, self._adapter_payload("solo", identity=identity)
        )

        self.assertEqual(get_world_clock().tick - tick_before, SOLO.seconds)
        self.assertEqual(self.record()["completed"][DISTRICT_KEY]["count"], 1)
        self.assertEqual(
            replay["data"]["delivery"]["delivery_id"],
            first["data"]["delivery"]["delivery_id"],
        )
        self.assertEqual(
            replay["data"]["first_completion"],
            first["data"]["first_completion"],
        )

    def test_an_unexpected_settlement_failure_is_a_bounded_rejection(self):
        with (
            patch(
                "web.webclient.actions.rite_actions.perform_rite",
                side_effect=RuntimeError("settlement exploded"),
            ),
            patch("web.webclient.actions.rite_actions.log_error") as error,
        ):
            result = landmark_rite_adapter(
                self.player, self._adapter_payload("solo")
            )

        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "rite_failed")
        self.assertEqual(result["message"], FAILED_MESSAGE)
        self.assertNotIn("data", result)
        error.assert_called_once()
        self.assertEqual(error.call_args.args[0], "landmark_rite_failed")
        self.assertEqual(error.call_args.kwargs["context"], {"char": self.player.pk})

    def test_without_a_request_identity_each_call_settles(self):
        # Only an admitted transport request is replayable: a caller that brings
        # no identity must never reuse one derived constant and replay a rite.
        payload = validate_landmark_rite_payload({"option": "solo", "member_id": None})
        tick_before = get_world_clock().tick

        for _ in range(2):
            result = landmark_rite_adapter(self.player, payload)
            self.assertEqual(result["outcome"], "success")

        self.assertEqual(get_world_clock().tick - tick_before, 2 * SOLO.seconds)
        self.assertEqual(self.record()["completed"][DISTRICT_KEY]["count"], 2)

    def test_the_success_result_passes_the_browser_result_schema(self):
        result = self.settle("solo")

        normalized = _normalize_result(result)
        envelope = _result_envelope(
            new_presentation_epoch(), uuid4().hex, normalized, 0
        )
        validated = validate_ui_action_result(envelope)

        self.assertEqual(validated["outcome"], "success")
        self.assertEqual(
            validated["data"]["delivery"]["scene_revision"],
            SOLO.self_scene.revision,
        )

    def test_a_delivery_carrying_the_reserved_revision_key_is_out_of_schema(self):
        result = self.settle("solo")
        envelope = _result_envelope(
            new_presentation_epoch(), uuid4().hex, _normalize_result(result), 0
        )
        bad = copy.deepcopy(envelope)
        delivery = bad["data"]["delivery"]
        delivery["revision"] = delivery.pop("scene_revision")

        with self.assertRaises(ProtocolValidationError):
            validate_ui_action_result(bad)
        # The dispatch wrapper replaces exactly this slot with the internal
        # error, which is why the delivery never uses the reserved key.
        self.assertEqual(
            _normalize_result({**result, "data": bad["data"]})["outcome"], "error"
        )

    def test_the_production_registry_binds_the_exact_rite_spec(self):
        spec = build_production_action_registry().spec("explore.landmark_rite")

        self.assertIs(spec.validate_payload, validate_landmark_rite_payload)
        self.assertIs(spec.adapter, landmark_rite_adapter)
        self.assertEqual(spec.affected_panels, ())


if __name__ == "__main__":
    unittest.main()