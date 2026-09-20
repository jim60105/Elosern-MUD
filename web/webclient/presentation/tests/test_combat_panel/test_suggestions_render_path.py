import unittest
from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.rooms import Room
from web.webclient.presentation.combat_panel import validate_context_actions
from web.webclient.presentation.context import FrozenCard, OptionsSnapshot, PresentationContext
from web.webclient.presentation.options import MAX_OPTION_CARDS
from web.webclient.presentation.registry import build_production_registry
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage

from ._support import _player



class SuggestionsRenderPathTests(BattlefieldIsolation, EvenniaTestCase):
    """Exploration suggestions render paths (design D-3; task 5.2)."""
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="建議測試房")
        self.player = _player()
        self.player.location = self.room
        self.registry = build_production_registry()
        self.fingerprint = "fp"

    def _render(self, options_state=None, fingerprint="fp"):
        return self.registry.render(
            "context_actions",
            PresentationContext(
                actor=self.player,
                protocol_version=1,
                options_state=options_state,
                options_fingerprint=fingerprint,
            ),
        )

    def test_absent_snapshot_is_inert(self):
        payload = self._render(options_state=None)
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})

    def test_unavailable_snapshot_is_inert(self):
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="unavailable",
                generation_token=0,
                displayed=None,
            )
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})

    def test_generating_carries_status_alone(self):
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="generating",
                generation_token=3,
                displayed=None,
            )
        )
        self.assertEqual(payload["suggestions"], {"status": "generating"})

    @covers_requirement("webclient-context-actions-suggestions::exploration-suggestions-render-from-an-immutable-session-snapshot")
    def test_ready_renders_the_snapshot_displayed_cards(self):
        cards = (
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看房間",
                params={"room": True},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.wait",
                label="等待片刻",
                params={"daypart": "noon"},
            ),
            FrozenCard(
                kind="freeform",
                action_code="explore.talk_freeform",
                label="隨意聊聊",
                params={"npc_id": 5},
            ),
        )
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="ready",
                generation_token=3,
                displayed=cards,
            )
        )
        self.assertEqual(payload["suggestions"]["status"], "ready")
        self.assertEqual(payload["suggestions"]["cards"][0]["params"], {"room": True})
        self.assertEqual(
            payload["suggestions"]["cards"][1]["params"],
            {"daypart": "noon"},
        )
        self.assertEqual(
            payload["suggestions"]["cards"][2]["action_code"],
            "explore.talk_freeform",
        )

    def test_ready_render_is_stable_across_repeated_renders(self):
        cards = (
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看房間",
                params={"room": True},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.wait",
                label="等待片刻",
                params={"daypart": "noon"},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看木箱",
                params={"target_id": 9},
            ),
        )
        snapshot = OptionsSnapshot(
            fingerprint="fp",
            status="ready",
            generation_token=3,
            displayed=cards,
        )
        first = self._render(snapshot)
        second = self._render(snapshot)
        self.assertEqual(first["suggestions"], second["suggestions"])
        # The snapshot writer may replace the session state object later; the
        # presenter never consults default_cards for a ready render.
        self.assertEqual(first["suggestions"]["cards"][0]["action_code"], "explore.look")

    @covers_requirement("webclient-context-actions-suggestions::exploration-suggestions-render-from-an-immutable-session-snapshot")
    def test_degraded_derives_rule_cards_from_default_cards(self):
        payload = self._render(
            OptionsSnapshot(
                fingerprint="fp",
                status="degraded",
                generation_token=2,
                displayed=None,
            )
        )
        self.assertEqual(payload["suggestions"]["status"], "degraded")
        cards = payload["suggestions"]["cards"]
        self.assertGreaterEqual(len(cards), 1)
        self.assertLessEqual(len(cards), MAX_OPTION_CARDS)
        for card in cards:
            self.assertEqual(card["kind"], "known_action")
            self.assertIn(card["action_code"], ("explore.look", "explore.wait", "explore.move"))
        # The degraded derivation is a strict subset of the serialized form.
        affordance_payloads = {
            (entry["action_id"], str(entry["params"]), entry["label"])
            for entry in payload["affordances"]
            if entry.get("action_id") is not None
        }
        for card in cards:
            self.assertIn(
                (card["action_code"], str(card["params"]), card["label"]),
                affordance_payloads,
            )

    def test_corrupted_ready_falls_back_to_unavailable_without_fabrication(self):
        from unittest import mock

        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="ready",
                    generation_token=3,
                    displayed=None,
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="ready",
                    generation_token=3,
                    displayed=(
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.look",
                            label="bad",  # no CJK: fails the v5 shape gate
                            params={"room": True},
                        ),
                    ),
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()

    def test_degraded_with_ascii_display_names_fails_closed_to_unavailable(self):
        # The affordance vocabulary bounds display names at 128 code points
        # without a CJK requirement, while suggestion labels are 1..24 CJK.
        # An ASCII-named room must degrade the suggestions section alone —
        # never the whole exploration panel (rubber-duck review finding).
        from unittest import mock

        self.room.key = "english room name"
        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="degraded",
                    generation_token=2,
                    displayed=None,
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
        # The panel itself stays available and schema-valid.
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        validate_context_actions(payload)

    def test_degraded_with_overlong_display_name_fails_closed_to_unavailable(self):
        # A room display name beyond the 24-code-point suggestion label bound
        # must also fail closed to a section-level unavailable (rubber-duck
        # review finding); CJK content itself never guarantees the bound.
        from unittest import mock

        self.room.key = "這是一個非常非常非常非常非常非常非常非常長的房間名稱"
        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="degraded",
                    generation_token=2,
                    displayed=None,
                )
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
        self.assertTrue(payload["available"])
        validate_context_actions(payload)

    @covers_requirement(
        "action-options-trigger-service::current-situation-freshness-gates-session-backed-suggestions"
    )
    def test_stale_non_unavailable_snapshots_fail_closed_to_unavailable(self):
        """A snapshot whose fingerprint no longer matches the current
        situation renders unavailable with a bounded diagnostic and never
        reaches the wire with old cards or a stale generating line
        (action-options-wiring-hardening R1 scenarios)."""
        from unittest import mock

        stale_cards = (
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看房間",
                params={"room": True},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.wait",
                label="等待片刻",
                params={"daypart": "noon"},
            ),
            FrozenCard(
                kind="known_action",
                action_code="explore.look",
                label="查看木箱",
                params={"target_id": 9},
            ),
        )
        for status, displayed in (
            ("generating", None),
            ("ready", stale_cards),
            ("degraded", None),
        ):
            with self.subTest(status=status):
                with mock.patch(
                    "web.webclient.presentation.combat_panel.log_unavailable"
                ) as logged:
                    payload = self._render(
                        OptionsSnapshot(
                            fingerprint="fp",
                            status=status,
                            generation_token=3,
                            displayed=displayed,
                        ),
                        fingerprint="a-different-current-fingerprint",
                    )
                    self.assertEqual(payload["suggestions"], {"status": "unavailable"})
                    logged.assert_called_once()
                    self.assertNotIn("cards", payload["suggestions"])

    @covers_requirement(
        "action-options-trigger-service::current-situation-freshness-gates-session-backed-suggestions"
    )
    def test_absent_current_fingerprint_fails_closed_to_unavailable(self):
        """A context without a derivable exploration situation can never
        render a session-backed state: the gate emits unavailable even for a
        snapshot whose shape is valid (action-options-wiring-hardening R1)."""
        from unittest import mock

        with mock.patch("web.webclient.presentation.combat_panel.log_unavailable") as logged:
            payload = self._render(
                OptionsSnapshot(
                    fingerprint="fp",
                    status="ready",
                    generation_token=3,
                    displayed=(
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.look",
                            label="查看房間",
                            params={"room": True},
                        ),
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.wait",
                            label="等待片刻",
                            params={"daypart": "noon"},
                        ),
                        FrozenCard(
                            kind="known_action",
                            action_code="explore.look",
                            label="查看木箱",
                            params={"target_id": 9},
                        ),
                    ),
                ),
                fingerprint=None,
            )
            self.assertEqual(payload["suggestions"], {"status": "unavailable"})
            logged.assert_called_once()
            self.assertNotIn("cards", payload["suggestions"])

    def test_unavailable_snapshot_is_inert_regardless_of_fingerprint(self):
        """The ``unavailable`` status needs no fingerprint gate: it emits the
        same unavailable envelope whether or not the fingerprint matches."""
        from unittest import mock

        payload = self._render(
            OptionsSnapshot(
                fingerprint="stale",
                status="unavailable",
                generation_token=0,
                displayed=None,
            ),
            fingerprint="different",
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})
        payload = self._render(
            OptionsSnapshot(
                fingerprint="stale",
                status="unavailable",
                generation_token=0,
                displayed=None,
            ),
            fingerprint=None,
        )
        self.assertEqual(payload["suggestions"], {"status": "unavailable"})


if __name__ == "__main__":
    unittest.main()
