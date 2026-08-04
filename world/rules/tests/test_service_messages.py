"""Stable service-rejection message mapping tests (task 1.2).

Every deterministic service rejection reason maps to a stable code and a safe
Traditional Chinese message; an unknown or unmapped input degrades to the
bounded generic fallback without exposing a traceback or raw payload.
"""

import unittest

from world.quests.runtime import (
    QuestAlreadyActive,
    QuestDataError,
    QuestNotFound,
    QuestTransitionError,
)
from world.rules.economy import TradeError, TradeReason
from world.rules.guild import (
    GuildDataError,
    GuildError,
    GuildServiceError,
    RegistrationReason,
    RewardClaim,
    RewardClaimError,
)
from world.rules.guild_exams import ExamReason, GuildExamError
from world.rules.guild_offers import (
    BoardAccessError,
    GuildOfferError,
    GuildOfferNotFound,
)
from world.rules.service_messages import (
    FALLBACK_CODE,
    FALLBACK_MESSAGE,
    SERVICE_REASON_MESSAGES,
    rejection_code,
    rejection_message,
    service_reason,
)


class ServiceMessagesTests(unittest.TestCase):
    def test_every_registration_reason_has_a_code_and_message(self):
        for reason in RegistrationReason:
            code = rejection_code(reason)
            self.assertEqual(code, reason.value)
            self.assertIn(code, SERVICE_REASON_MESSAGES)
            self.assertTrue(rejection_message(reason))

    def test_every_reward_claim_reason_has_a_code_and_message(self):
        for reason in RewardClaim:
            code = rejection_code(reason)
            self.assertEqual(code, reason.value)
            self.assertIn(code, SERVICE_REASON_MESSAGES)
            self.assertTrue(rejection_message(reason))

    def test_every_exam_reason_has_a_code_and_message(self):
        for reason in ExamReason:
            code = rejection_code(reason)
            self.assertEqual(code, reason.value)
            self.assertIn(code, SERVICE_REASON_MESSAGES)
            self.assertTrue(rejection_message(reason))

    def test_every_trade_reason_has_a_code_and_message(self):
        for reason in TradeReason:
            code = rejection_code(reason)
            self.assertEqual(code, reason.value)
            self.assertIn(code, SERVICE_REASON_MESSAGES)
            self.assertTrue(rejection_message(reason))

    def test_board_access_error_maps_to_a_stable_generic_code(self):
        error = BoardAccessError("actor is not registered")
        self.assertEqual(rejection_code(error), "board_access")
        code, message = service_reason(error)
        self.assertEqual(code, "board_access")
        self.assertTrue(message)

    def test_guild_data_error_maps_without_leaking_internal_message(self):
        error = GuildDataError("guild_registration has unknown fields ['x']")
        code, message = service_reason(error)
        self.assertEqual(code, "guild_data_error")
        self.assertNotIn("unknown fields", message)
        self.assertNotIn("x", message)

    def test_guild_service_error_maps_to_a_stable_code(self):
        error = GuildServiceError("no local service host")
        self.assertEqual(rejection_code(error), "guild_service_error")

    def test_guild_error_with_enum_reason_maps_to_that_reason(self):
        error = GuildError(RegistrationReason.NO_STAFF)
        self.assertEqual(rejection_code(error), "no_staff")

    def test_trade_error_carries_its_enum_reason(self):
        error = TradeError(TradeReason.CLOSED)
        self.assertEqual(rejection_code(error), "closed")
        self.assertEqual(rejection_message(error), SERVICE_REASON_MESSAGES["closed"])

    def test_trade_error_without_enum_reason_maps_to_malformed_stock(self):
        error = TradeError("unexpected raw message")
        self.assertEqual(rejection_code(error), "malformed_stock")

    def test_exam_error_carries_its_enum_reason(self):
        error = GuildExamError(ExamReason.BELOW_THRESHOLD)
        self.assertEqual(rejection_code(error), "below_threshold")

    def test_reward_claim_error_carries_its_enum_reason(self):
        error = RewardClaimError(RewardClaim.ALREADY_CLAIMED)
        self.assertEqual(rejection_code(error), "already_claimed")

    def test_quest_not_found_maps_to_a_stable_code(self):
        error = QuestNotFound("introductory_hunt:1")
        self.assertEqual(rejection_code(error), "quest_not_found")

    def test_quest_data_error_maps_to_a_stable_code(self):
        error = QuestDataError("record field is malformed")
        self.assertEqual(rejection_code(error), "quest_data_error")

    def test_quest_already_active_maps_to_a_stable_code(self):
        error = QuestAlreadyActive("introductory_hunt")
        self.assertEqual(rejection_code(error), "quest_already_active")

    def test_reward_claim_error_without_args_maps_to_malformed_claims(self):
        self.assertEqual(rejection_code(RewardClaimError()), "malformed_claims")

    def test_exam_error_without_enum_reason_maps_to_guild_service_error(self):
        self.assertEqual(rejection_code(GuildExamError("raw message")), "guild_service_error")

    def test_guild_error_without_enum_reason_maps_to_guild_service_error(self):
        self.assertEqual(rejection_code(GuildError("raw message")), "guild_service_error")

    def test_quest_transition_error_maps_to_a_stable_code(self):
        error = QuestTransitionError("invalid transition")
        self.assertEqual(rejection_code(error), "quest_transition")

    def test_guild_offer_not_found_maps_to_a_stable_code(self):
        error = GuildOfferNotFound("no offer")
        self.assertEqual(rejection_code(error), "offer_unknown")

    def test_guild_offer_error_maps_to_a_stable_code(self):
        error = GuildOfferError("invalid offer")
        self.assertEqual(rejection_code(error), "offer_invalid")

    def test_raw_stable_code_string_maps_verbatim(self):
        self.assertEqual(rejection_code("insufficient_funds"), "insufficient_funds")

    def test_unknown_exception_degrades_to_the_bounded_fallback(self):
        error = RuntimeError("keyboard interrupt everything traceback payload")
        self.assertEqual(rejection_code(error), FALLBACK_CODE)
        self.assertEqual(rejection_message(error), FALLBACK_MESSAGE)
        self.assertNotIn("keyboard", rejection_message(error))

    def test_unknown_raw_string_degrades_to_the_bounded_fallback(self):
        self.assertEqual(rejection_code("totally_unmapped_reason"), FALLBACK_CODE)
        self.assertEqual(rejection_message("totally_unmapped_reason"), FALLBACK_MESSAGE)

    def test_messages_never_contain_newlines_or_control_characters(self):
        for code, message in SERVICE_REASON_MESSAGES.items():
            self.assertNotIn("\n", message, code)
            self.assertTrue(message.strip(), code)

    def test_rejection_message_never_raises(self):
        for reason in (
            *RegistrationReason,
            *RewardClaim,
            *ExamReason,
            *TradeReason,
            BoardAccessError("x"),
            GuildDataError("x"),
            QuestNotFound("x"),
            object(),
        ):
            message = rejection_message(reason)
            self.assertIsInstance(message, str)
            self.assertTrue(message)


if __name__ == "__main__":
    unittest.main()
