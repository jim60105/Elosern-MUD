"""Dispatcher integration for the guarded party combat actions.

Drives the production dispatcher end to end: admission, exact payload
rejection before any adapter runs, authenticated-actor binding, canonical
publication before the matching result, the result variants of the four
guarded actions, and the terminal-combat trigger.
"""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room

from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.protocol import validate_ui_action_result
from web.webclient.presentation.registry import build_production_registry
from world.rules.combat_session import BASIC_ATTACK_KEY, engage, read_session
from world.rules.monster_behaviour import BEHAVIOUR_PROFILES
from world.rules.party import join_party
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.tests.synthetic_data import SYNTH_SKILLS

_T_SINGLE = SYNTH_SKILLS["t_ember_burst"].key


def _player(key="dispatch player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.magic_power.base = 30
    return player


def _monster(key="dispatch goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = next(iter(MONSTER_TIER_REGISTRY))
    monster.behaviour_tree = next(iter(BEHAVIOUR_PROFILES))
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = 10
    return monster


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 1
        self.protocol_key = "websocket"

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class CombatDispatchIntegrationTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            "items",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.room = create_object(Room, key="dispatch arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster()
        self.monster.location = self.room
        grant_lineage(self.player, [_T_SINGLE])
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()
        self.session = _FakeSession(self.player)

    # -- helpers ---------------------------------------------------------

    def _companion(self, key="dispatch companion"):
        companion = create_object(NPC, key=key, location=self.room)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.base = 100
        companion.traits.hp.current = 100
        join_party(companion, self.player)
        return companion

    def _coordinator(self):
        coordinator = attach_coordinator(self.session, self.registry)
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        self.session.sent.clear()
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

    def _dispatch(self, coordinator, action_id, payload, request_id="r1"):
        handle_ui_action(
            self.session,
            self.player,
            self._envelope(coordinator, action_id, payload, request_id),
            self.action_registry,
            self.registry,
        )
        return self._last_result()

    def _command_payload(self, command, actor=None):
        record = read_session(self.player)
        return {
            "session_id": record.session_id,
            "round_revision": record.round_revision,
            "draft_version": record.draft_version,
            "actor_id": (actor or self.player).pk,
            "command": command,
        }

    def _messages(self):
        return [next(key for key in call if key != "id") for call in self.session.sent]

    def _last_result(self):
        results = [call for call in self.session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    def _last_panel_message(self):
        messages = [
            call
            for call in self.session.sent
            if "ui_snapshot" in call or "ui_update" in call
        ]
        message = messages[-1]
        name = next(key for key in message if key != "id")
        return name, message[name][0][0]

    # -- publication and result variants ---------------------------------

    @covers_requirement(
        "webclient-action-dispatch::admitted-action-completion-publishes-canonical-state-before-unlocking"
    )
    def test_draft_edit_publishes_canonical_progress_before_its_result(self):
        self._companion()
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        result = self._dispatch(
            coordinator,
            "combat.command",
            self._command_payload(
                {"kind": "tactic", "payload": {"key": "defend"}}
            ),
        )
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(result["code"], "draft_saved")
        self.assertNotIn("data", result)
        # The canonical panel replacement reaches the client first, at the
        # same revision the result names.
        names = self._messages()
        self.assertEqual(names[-1], "ui_action_result")
        self.assertIn("ui_update", names[:-1])
        name, panel_message = self._last_panel_message()
        self.assertEqual(panel_message["revision"], result["presentation_revision"])
        payload = panel_message["panels"]["context_actions"]
        self.assertEqual(payload["kind"], "combat")
        self.assertEqual(
            payload["draft"]["draft_version"],
            read_session(self.player).draft_version,
        )
        self.assertNotIn("combat_beats", panel_message["panels"])

    @covers_requirement(
        "webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs"
    )
    @covers_requirement(
        "webclient-combat-beats::the-beats-panel-is-published-only-with-the-combat-action-that-produced-it"
    )
    def test_committed_round_publishes_the_beats_panel_with_the_result(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
        ):
            result = self._dispatch(
                coordinator,
                "combat.command",
                self._command_payload(
                    {
                        "kind": "skill",
                        "payload": {
                            "skill_key": _T_SINGLE,
                            "target_ids": [self.monster.pk],
                        },
                    }
                ),
            )
        self.assertEqual(result["code"], "round_committed", result)
        self.assertNotIn("data", result)
        name, panel_message = self._last_panel_message()
        self.assertEqual(name, "ui_update")
        self.assertTrue(panel_message["panels"]["combat_beats"]["available"])
        self.assertEqual(result["presentation_revision"], panel_message["revision"])

    def test_actor_query_publishes_the_requested_members_choices(self):
        companion = self._companion()
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        record = read_session(self.player)
        result = self._dispatch(
            coordinator,
            "combat.actor_choices",
            {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "actor_id": companion.pk,
            },
        )
        self.assertEqual(result["code"], "actor_choices", result)
        self.assertNotIn("data", result)
        _, panel_message = self._last_panel_message()
        choices = panel_message["panels"]["context_actions"]["choices"]
        self.assertEqual(choices["actor_id"], companion.pk)
        # The choice is transport-owned state, read back through the context.
        self.assertEqual(
            build_presentation_context(self.session, self.player).party_actor,
            companion.pk,
        )
        # A read-only query never changes the session or the draft.
        after = read_session(self.player)
        self.assertEqual(after.round_revision, record.round_revision)
        self.assertEqual(after.draft_version, record.draft_version)

    def test_exit_prompt_result_carries_the_exact_bounded_data(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        coordinator = self._coordinator()
        result = self._dispatch(
            coordinator,
            "combat.exit_prompt",
            {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "operation": "surrender",
            },
        )
        self.assertEqual(result["code"], "party_exit_prompt", result)
        self.assertEqual(
            set(result["data"]),
            {"operation", "confirmation_token", "scope", "consequence"},
        )
        # The emitted envelope is exactly the schema-valid result envelope.
        validate_ui_action_result(self.session.sent[-1]["ui_action_result"][0][0])

    def test_terminal_combat_schedules_exploration_options_once(self):
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch("world.rules.action.gates.roll_d100", return_value=100),
            patch(
                "server.option_proposal_service.schedule_action_options"
            ) as schedule,
        ):
            result = self._dispatch(
                coordinator,
                "combat.command",
                self._command_payload(
                    {
                        "kind": "skill",
                        "payload": {
                            "skill_key": BASIC_ATTACK_KEY,
                            "target_ids": [self.monster.pk],
                        },
                    }
                ),
            )
        self.assertEqual(result["code"], "combat_terminal", result)
        self.assertEqual(schedule.call_count, 1)

    def test_nonterminal_round_schedules_no_exploration_options(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch(
                "server.option_proposal_service.schedule_action_options"
            ) as schedule,
        ):
            result = self._dispatch(
                coordinator,
                "combat.command",
                self._command_payload(
                    {
                        "kind": "skill",
                        "payload": {
                            "skill_key": _T_SINGLE,
                            "target_ids": [self.monster.pk],
                        },
                    }
                ),
            )
        self.assertEqual(result["code"], "round_committed", result)
        self.assertEqual(schedule.call_count, 0)

    # -- admission and rejection -----------------------------------------

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_retired_action_ids_are_unknown_actions(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        for action_id in ("combat.cast", "combat.flee", "combat.forfeit"):
            with self.subTest(action_id=action_id):
                self.session.sent.clear()
                result = self._dispatch(
                    coordinator, action_id, {"session_id": "hostile:1:0"}
                )
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], "unknown_action")
                # No adapter ran, so no canonical publication happened either.
                self.assertEqual(self._messages(), ["ui_action_result"])

    def test_extra_payload_field_rejects_before_the_adapter_runs(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        before = read_session(self.player)
        payload = self._command_payload(
            {"kind": "tactic", "payload": {"key": "defend"}}
        )
        payload["puppet_id"] = self.monster.pk
        result = self._dispatch(coordinator, "combat.command", payload)
        self.assertEqual(result["outcome"], "rejected", result)
        self.assertEqual(result["code"], "malformed_payload")
        self.assertEqual(self._messages(), ["ui_action_result"])
        after = read_session(self.player)
        self.assertEqual(after.draft_version, before.draft_version)
        self.assertNotIn("ui_protocol_error", self._messages())

    def test_forged_actor_reference_reaches_the_rules_boundary_unmutated(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        before = read_session(self.player)
        result = self._dispatch(
            coordinator,
            "combat.command",
            self._command_payload(
                {"kind": "tactic", "payload": {"key": "defend"}}, actor=self.monster
            ),
        )
        self.assertEqual(result["outcome"], "rejected", result)
        self.assertEqual(result["code"], "forbidden_actor")
        after = read_session(self.player)
        self.assertEqual(after.draft_version, before.draft_version)
        self.assertEqual(after.round_revision, before.round_revision)

    def test_unknown_envelope_identity_field_is_a_protocol_error(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        envelope = self._envelope(
            coordinator,
            "combat.command",
            self._command_payload(
                {"kind": "tactic", "payload": {"key": "defend"}}
            ),
        )
        envelope["puppet"] = self.monster.pk
        handle_ui_action(
            self.session, self.player, envelope, self.action_registry, self.registry
        )
        self.assertEqual(self._messages(), ["ui_protocol_error"])

    def test_active_combat_inventory_use_is_rejected_without_mutation(self):
        self.player.traits.hp.current = 50
        self.player.db.inventory = ["t_ember_spray"]
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        result = self._dispatch(
            coordinator, "inventory.use", {"item_key": "t_ember_spray"}
        )
        self.assertEqual(result["outcome"], "rejected", result)
        self.assertEqual(result["code"], "combat_item_command_required")
        self.assertEqual(self.player.db.inventory, ["t_ember_spray"])
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement(
        "webclient-action-dispatch::completed-request-ids-are-deduplicated-within-a-bounded-session-cache"
    )
    def test_duplicate_request_id_replays_without_re_executing(self):
        self._companion()
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        payload = self._command_payload(
            {"kind": "tactic", "payload": {"key": "defend"}}
        )
        from web.webclient.actions import combat_actions

        real = combat_actions.confirm_actor_command
        with patch.object(
            combat_actions, "confirm_actor_command", side_effect=real
        ) as confirm:
            first = self._dispatch(coordinator, "combat.command", payload, "dup")
            before = read_session(self.player).draft_version
            second = self._dispatch(coordinator, "combat.command", payload, "dup")
        self.assertEqual(confirm.call_count, 1)
        self.assertEqual(first, second)
        self.assertEqual(read_session(self.player).draft_version, before)

    @covers_requirement(
        "webclient-action-dispatch::stale-presentation-state-prevents-adapter-invocation"
    )
    def test_stale_epoch_is_rejected_without_invoking_the_adapter(self):
        engage(self.player, self.monster)
        coordinator = self._coordinator()
        envelope = self._envelope(
            coordinator,
            "combat.command",
            self._command_payload(
                {"kind": "tactic", "payload": {"key": "defend"}}
            ),
        )
        envelope["presentation_epoch"] = "a" * 22
        with patch("web.webclient.actions.combat_actions.confirm_actor_command") as confirm:
            handle_ui_action(
                self.session, self.player, envelope, self.action_registry, self.registry
            )
        self.assertEqual(confirm.call_count, 0)
        self.assertEqual(self._last_result()["outcome"], "stale")


if __name__ == "__main__":
    unittest.main()
