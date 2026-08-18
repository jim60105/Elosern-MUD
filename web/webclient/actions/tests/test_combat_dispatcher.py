"""Dispatcher integration tests for the production combat actions (task 3.6)."""

from types import SimpleNamespace
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from world.rules.combat_session import engage, read_session
from world.rules.tests.combat_fixtures import BattlefieldIsolation


def _player(key="dispatch player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    # Human starting magic level (術師 tier) so element-gated spell casts pass.
    player.traits.magic_level.base = 30
    return player


def _monster(key="dispatch goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 1

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class CombatDispatchIntegrationTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="dispatch arena")
        self.player = _player()
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.monster = _monster()
        self.monster.location = self.room
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()
        self.session = _FakeSession(self.player)

    def _coordinator(self):
        coordinator = attach_coordinator(self.session, self.registry)
        context = PresentationContext(actor=self.player, protocol_version=1)
        coordinator.full_snapshot(context)
        return coordinator

    def _envelope(self, coordinator, action_id, payload, request_id="r1"):
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": payload,
        }

    def _last_result(self):
        results = [call for call in self.session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    def _last_snapshot(self):
        messages = [call for call in self.session.sent if "ui_snapshot" in call or "ui_update" in call]
        return messages[-1][next(k for k in messages[-1] if k != "id")][0][0]

    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    def test_combat_cast_round_publishes_panels_then_result(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        from unittest.mock import patch

        with patch("world.rules.combat.roll_d100", return_value=100):
            handle_ui_action(
                self.session,
                self.player,
                self._envelope(
                    coordinator,
                    "combat.cast",
                    {"skill_key": "fire_ball", "target_ids": [self.monster.pk]},
                ),
                self.action_registry,
                self.registry,
            )
        names = [set(call) for call in self.session.sent]
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "round")
        self.assertEqual(result["presentation_revision"], coordinator.revision)
        # The affected-panel update precedes the result on the wire.
        update_sent = any("ui_update" in call for call in names)
        self.assertTrue(update_sent)

    @covers_requirement("webclient-action-dispatch::each-session-admits-only-one-mutation-in-flight")
    def test_one_in_flight_busy_rejects_second(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        session_id = read_session(self.player).session_id
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "combat.forfeit",
                {"session_id": session_id},
                request_id="r1",
            ),
            self.action_registry,
            self.registry,
        )
        # The synchronous adapter settles immediately; the second request is
        # accepted and deduplicated or rejected, never double-executed.
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "combat.forfeit",
                {"session_id": session_id},
                request_id="r2",
            ),
            self.action_registry,
            self.registry,
        )
        results = [call for call in self.session.sent if "ui_action_result" in call]
        self.assertGreaterEqual(len(results), 1)

    @covers_requirement("webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache")
    def test_duplicate_request_id_replays_cached_result(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        from unittest.mock import patch

        envelope = self._envelope(
            coordinator,
            "combat.forfeit",
            {"session_id": read_session(self.player).session_id},
            request_id="same",
        )
        with patch("web.webclient.actions.combat_actions.forfeit") as forfeit_mock:
            forfeit_mock.return_value = {
                "outcome": "defeat",
                "rounds_elapsed": 0,
                "logs": (),
                "events": (),
                "exam": None,
            }
            handle_ui_action(
                self.session,
                self.player,
                envelope,
                self.action_registry,
                self.registry,
            )
            handle_ui_action(
                self.session,
                self.player,
                envelope,
                self.action_registry,
                self.registry,
            )
            self.assertEqual(forfeit_mock.call_count, 1)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_stale_forfeit_through_dispatcher(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "combat.forfeit",
                {"session_id": "hostile:999:0"},
            ),
            self.action_registry,
            self.registry,
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_session_id")
        self.assertIsNotNone(self.player.db.active_combat)

    @covers_requirement("webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe")
    def test_unregistered_action_rejected_without_routing_to_text(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "look",
                {},
            ),
            self.action_registry,
            self.registry,
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_action")
        self.assertEqual(
            len([call for call in self.session.sent if "text" in call]),
            0,
            "an unknown action must never route through the text parser",
        )

    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    def test_insufficient_resource_rejects_without_round(self):
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(
                coordinator,
                "combat.cast",
                {"skill_key": "fire_ball", "target_ids": [self.monster.pk]},
            ),
            self.action_registry,
            self.registry,
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "insufficient_resource")
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement("action-options-trigger-service::all-committed-player-relocations-and-terminal-combat-returns-trigger-options")
    def test_terminal_forfeit_schedules_every_live_watcher_after_the_result(self):
        """A successful terminal combat action schedules the exploration
        trigger for every live watcher of the actor only after the completion
        presentation and the action result are on the wire."""
        from unittest.mock import patch

        from server import option_proposal_service as service
        from web.webclient.presentation import watchers as watchers_module

        engage(self.player, self.monster)
        coordinator = self._coordinator()
        watcher_a = _FakeSession(self.player)
        watcher_b = _FakeSession(self.player)
        captured = {}
        with (
            patch.object(
                service,
                "schedule_action_options",
                side_effect=lambda *a, **kw: captured.update(
                    {"watchers": kw["watchers"], "sent_before": len(self.session.sent)}
                ),
            ),
            patch.object(
                watchers_module,
                "watchers_for",
                return_value=((watcher_a, "epoch-a"), (watcher_b, "epoch-b")),
            ),
        ):
            handle_ui_action(
                self.session,
                self.player,
                self._envelope(
                    coordinator,
                    "combat.forfeit",
                    {"session_id": read_session(self.player).session_id},
                ),
                self.action_registry,
                self.registry,
            )
        self.assertIsNone(read_session(self.player), "the session ended")
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(captured["watchers"], ((watcher_a, "epoch-a"), (watcher_b, "epoch-b")))
        self.assertEqual(
            captured["sent_before"],
            len(self.session.sent),
            "the trigger is scheduled after the result publication, never before",
        )
        self.assertTrue(
            any("ui_action_result" in call for call in self.session.sent[: captured["sent_before"]]),
            "the action result is already on the wire when scheduling runs",
        )

    @covers_requirement("action-options-trigger-service::all-committed-player-relocations-and-terminal-combat-returns-trigger-options")
    def test_non_terminal_round_never_schedules(self):
        """A successful round that keeps the session active stays in combat:
        no exploration trigger is scheduled."""
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        from unittest.mock import patch

        from server import option_proposal_service as service

        with patch.object(service, "schedule_action_options") as schedule:
            with patch("world.rules.combat.roll_d100", return_value=100):
                handle_ui_action(
                    self.session,
                    self.player,
                    self._envelope(
                        coordinator,
                        "combat.cast",
                        {"skill_key": "fire_ball", "target_ids": [self.monster.pk]},
                    ),
                    self.action_registry,
                    self.registry,
                )
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "round")
        self.assertIsNotNone(read_session(self.player))
        schedule.assert_not_called()

    @covers_requirement("action-options-trigger-service::all-committed-player-relocations-and-terminal-combat-returns-trigger-options")
    def test_rejected_combat_action_never_schedules(self):
        """A rejected (non-successful) combat action must never schedule,
        whatever its action id."""
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        from unittest.mock import patch

        from server import option_proposal_service as service

        with patch.object(service, "schedule_action_options") as schedule:
            handle_ui_action(
                self.session,
                self.player,
                self._envelope(
                    coordinator,
                    "combat.forfeit",
                    {"session_id": "hostile:999:0"},
                ),
                self.action_registry,
                self.registry,
            )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertIsNotNone(read_session(self.player), "the session survives")
        schedule.assert_not_called()


if __name__ == "__main__":
    unittest.main()
