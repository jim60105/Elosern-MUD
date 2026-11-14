"""The ``rite`` / ``儀式`` command: listing, self, companion and refusals.

The command shares the browser action's settlement and renderings: whatever the
action delivers is what the text client prints, in the same order. These tests
pin the three syntaxes, the experienced mark, and that every refusal is the
settlement's own stable line with nothing written.
"""

from __future__ import annotations

import unittest

from evennia.utils.test_resources import EvenniaCommandTestMixin

from commands.rite import CmdRite
from tools.spec_traceability import covers_requirement
from world.rules.landmark_rites import REFUSAL_MESSAGES
from world.rules.tests.rite_fixtures import (
    GUARDIAN_FORM,
    GUARDIAN_NAME,
    LANDMARK_NAME,
    SHARED,
    SOLO,
    RiteSettlementFixture,
)

_EXPERIENCED = "　已體驗"
_USAGE = "用法：儀式 <選項> [隊友]"


class RiteCommandTests(EvenniaCommandTestMixin, RiteSettlementFixture):
    def _listing(self, cmdstring: str | None = None) -> str:
        return self.call(CmdRite(), "", cmdstring=cmdstring)

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_the_listing_names_the_guardian_options_and_usage(self):
        output = self._listing()

        self.assertIn(f"{LANDMARK_NAME}・{GUARDIAN_NAME}", output)
        self.assertIn(GUARDIAN_FORM, output)
        self.assertIn(f"　{SOLO.label_zh}（{SOLO.key}）", output)
        self.assertIn(f"　{SHARED.label_zh}（{SHARED.key}）", output)
        self.assertIn(_USAGE, output)
        self.assertNotIn(_EXPERIENCED, output)

    def test_the_alias_lists_the_same_surface(self):
        self.assertEqual(self._listing("儀式"), self._listing())

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_the_listing_changes_nothing(self):
        before = self.world_state()

        self._listing()

        self.assert_unchanged(before)

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_only_the_completed_option_is_marked_experienced(self):
        self.call(CmdRite(), SHARED.key)

        listing = self._listing()

        self.assertIn(f"　{SHARED.label_zh}（{SHARED.key}）{_EXPERIENCED}", listing)
        self.assertIn(f"　{SOLO.label_zh}（{SOLO.key}）", listing)
        self.assertNotIn(f"　{SOLO.label_zh}（{SOLO.key}）{_EXPERIENCED}", listing)

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_key_and_label_each_perform_and_emit_the_scene_before_the_completion(self):
        for token in (SOLO.key, SOLO.label_zh):
            with self.subTest(token=token):
                output = self.call(CmdRite(), token)

                emitted = (
                    "測試敘述。",
                    "你：測試自語。",
                    "測試守護：測試守護對{name}說話。",
                    f"你完成了{LANDMARK_NAME}的儀式。",
                )
                offsets = [output.index(line) for line in emitted]
                self.assertEqual(offsets, sorted(offsets))
                self.assertEqual(output.count(emitted[-1]), 1)

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_a_named_companion_performs_with_the_watch_scene(self):
        output = self.call(CmdRite(), f"{SHARED.key} {self.companion.key}")

        self.assertIn(f"測試守護對{self.companion.key}說話。", output)
        self.assertIn(
            f"{self.companion.key}完成了{LANDMARK_NAME}的儀式。", output
        )
        self.assertEqual(
            output.count(f"{self.companion.key}完成了{LANDMARK_NAME}的儀式。"), 1
        )
        self.assertEqual(self.companion.sexual.climax_today, 1)
        self.assertEqual(self.player.sexual.climax_today, 0)

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_an_unknown_option_is_refused_unchanged(self):
        before = self.world_state()

        self.call(CmdRite(), "t_none", REFUSAL_MESSAGES["rite_unknown_option"])

        self.assert_unchanged(before)

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_an_unknown_companion_is_refused_unchanged(self):
        before = self.world_state()

        self.call(
            CmdRite(),
            f"{SHARED.key} 路人",
            REFUSAL_MESSAGES["rite_member_unavailable"],
        )

        self.assert_unchanged(before)

    @covers_requirement(
        "landmark-rite-command::the-rite-command-lists-and-performs-rites-from-the-text-client"
    )
    def test_a_non_landmark_location_refuses_both_listing_and_performance(self):
        self.player.location = self.source
        before = self.world_state()

        self.call(CmdRite(), "", REFUSAL_MESSAGES["rite_no_landmark"])
        self.call(CmdRite(), SOLO.key, REFUSAL_MESSAGES["rite_no_landmark"])

        self.assert_unchanged(before)

    def test_more_than_two_tokens_print_the_usage_line(self):
        before = self.world_state()

        self.call(CmdRite(), f"{SHARED.key} {self.companion.key} extra", _USAGE)

        self.assert_unchanged(before)


if __name__ == "__main__":
    unittest.main()