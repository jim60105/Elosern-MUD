"""Focused v7 party read-model and schema coverage.

Validates the bounded actor summaries, the single requested-actor choices
object, the durable draft progress, and the closed draft-command wire union at
the validator level, plus one real-session presentation of allied actors,
item rows and tactics.
"""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.rooms import Room
from web.webclient.presentation.combat_panel import (
    CONTEXT_ACTIONS_SCHEMA_VERSION,
    validate_context_actions,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from world.rules.combat_session import BASIC_ATTACK_KEY, engage
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.tests.synthetic_data import SYNTH_SKILLS

from ._support import (
    _TACTICS,
    _monster,
    _player,
    _recovery_panel,
    _valid_actor,
    _valid_choices,
    _valid_draft,
    _valid_panel,
    _valid_participant,
)


def _valid_item(**overrides):
    value = {
        "item_key": "t_ember_spray",
        "label": "合成噴霧",
        "summary": "回復少量生命。",
        "quantity": 1,
        "enabled": True,
        "reason": None,
        "target_spec": "self",
        "targets": [],
        "hostile": False,
        "beneficial": True,
    }
    value.update(overrides)
    return value


def _valid_tactic(**overrides):
    value = {
        "key": "defend",
        "label": "防禦",
        "enabled": True,
        "reason": None,
        "targets": [],
    }
    value.update(overrides)
    return value


class PartyProtocolSchemaTests(unittest.TestCase):
    def _panel(self, **choices_overrides):
        return _valid_panel(choices=_valid_choices(**choices_overrides))

    @covers_requirement(
        "webclient-combat-menu::party-protocol-publishes-bounded-actor-choices-and-durable-progress"
    )
    def test_valid_party_panel_round_trips(self):
        payload = _valid_panel(
            choices=_valid_choices(items=[_valid_item()], **{_TACTICS: [_valid_tactic()]})
        )
        normalized = validate_context_actions(payload)
        self.assertEqual(normalized["schema_version"], CONTEXT_ACTIONS_SCHEMA_VERSION)
        self.assertEqual(normalized["actors"][0]["identity"], 2)
        self.assertEqual(normalized["choices"]["actor_id"], 2)
        self.assertEqual(normalized["draft"]["round_revision"], 0)

    def test_actor_summary_reason_invariants(self):
        for bad in (
            {"commandable": False, "reason": None},
            {"commandable": True, "reason": {"code": "forbidden_actor", "message": "。"}},
        ):
            with self.subTest(actor=bad):
                with self.assertRaises(Exception):
                    validate_context_actions(_valid_panel(actors=[_valid_actor(**bad)]))
        # A duplicate actor identity rejects.
        with self.assertRaises(Exception):
            validate_context_actions(
                _valid_panel(actors=[_valid_actor(), _valid_actor()])
            )

    @covers_requirement(
        "webclient-combat-menu::party-protocol-publishes-bounded-actor-choices-and-durable-progress"
    )
    def test_choices_must_reference_an_actor_summary(self):
        with self.assertRaises(Exception):
            validate_context_actions(self._panel(actor_id=99))
        with self.assertRaises(Exception):
            validate_context_actions(_valid_panel(actors=[]))

    @covers_requirement(
        "webclient-combat-menu::actor-item-summaries-and-reselection-reasons-"
        "are-explicit-bounded-facts"
    )
    def test_item_rows_are_exact_and_bounded(self):
        good = _valid_item()
        normalized = validate_context_actions(self._panel(items=[good]))
        self.assertEqual(normalized["choices"]["items"], [good])
        for bad in (
            {**good, "summary": "字" * 513},
            {k: v for k, v in good.items() if k != "hostile"},
            {**good, "beneficial": None},
            {**good, "quantity": -1},
            {**good, "quantity": True},
            {**good, "target_spec": "area"},
            {**good, "targets": [99]},
            {**good, "enabled": False, "reason": None},
        ):
            with self.subTest(item=bad):
                with self.assertRaises(Exception):
                    validate_context_actions(self._panel(items=[bad]))

    @covers_requirement(
        "webclient-combat-menu::actor-item-summaries-and-reselection-reasons-"
        "are-explicit-bounded-facts"
    )
    def test_item_catalog_fails_closed_above_the_bound(self):
        # 128 distinct usable keys pass; 129 fail closed rather than truncate.
        ok = self._panel(items=[_valid_item(item_key=f"item_{index}") for index in range(128)])
        validate_context_actions(ok)
        over = self._panel(
            items=[_valid_item(item_key=f"item_{index}") for index in range(129)]
        )
        with self.assertRaises(Exception):
            validate_context_actions(over)

    def test_tactic_rows_are_exact_and_bounded(self):
        normalized = validate_context_actions(
            self._panel(**{_TACTICS: [_valid_tactic(), _valid_tactic(key="dodge", label="閃避")]})
        )
        self.assertEqual(len(normalized["choices"][_TACTICS]), 2)
        for bad in (
            {"key": "block", "label": "格擋", "enabled": True, "reason": None, "targets": []},
            {"key": "defend", "label": "防禦", "enabled": True, "reason": None, "targets": [2]},
            {"key": "taunt", "label": "嘲諷", "enabled": True, "reason": None, "targets": [99]},
            {"key": "taunt", "label": "嘲諷", "enabled": False, "reason": None, "targets": []},
        ):
            with self.subTest(tactic=bad):
                with self.assertRaises(Exception):
                    validate_context_actions(self._panel(**{_TACTICS: [bad]}))
        with self.assertRaises(Exception):
            validate_context_actions(
                self._panel(
                    **{
                        _TACTICS: [
                            _valid_tactic(key=key, label=key)
                            for key in ("defend", "dodge", "taunt", "defend")
                        ]
                    }
                )
            )

    @covers_requirement(
        "webclient-combat-menu::actor-item-summaries-and-reselection-reasons-"
        "are-explicit-bounded-facts"
    )
    def test_draft_entries_must_join_required_actors(self):
        with self.assertRaises(Exception):
            validate_context_actions(
                _valid_panel(
                    draft=_valid_draft(
                        entries=[
                            {
                                "actor_id": 99,
                                "command": {"kind": "item", "payload": {"item_key": "x"}},
                            }
                        ]
                    )
                )
            )

    @covers_requirement(
        "webclient-combat-menu::actor-item-summaries-and-reselection-reasons-"
        "are-explicit-bounded-facts"
    )
    def test_reselection_reasons_join_needs_selection_ids(self):
        panel = _valid_panel(
            draft=_valid_draft(
                needs_selection_ids=[2],
                reselection_reasons=[
                    {"actor_id": 2, "reason": {"code": "target_invalid", "message": "目標無效。"}}
                ],
            )
        )
        validate_context_actions(panel)
        with self.assertRaises(Exception):
            validate_context_actions(
                _valid_panel(
                    draft=_valid_draft(
                        needs_selection_ids=[],
                        reselection_reasons=[
                            {"actor_id": 2, "reason": {"code": "x", "message": "。"}}
                        ],
                    )
                )
            )
        with self.assertRaises(Exception):
            validate_context_actions(
                _valid_panel(
                    draft=_valid_draft(
                        reselection_reasons=[{"actor_id": 2, "reason": None}]
                    )
                )
            )

    @covers_requirement(
        "webclient-combat-menu::party-protocol-publishes-bounded-actor-choices-and-durable-progress"
    )
    def test_draft_revisions_are_safe_integers_and_match_the_session(self):
        panel = _valid_panel(
            draft=_valid_draft(round_revision=True, needs_selection_ids=[2])
        )
        with self.assertRaises(Exception):
            validate_context_actions(panel)
        with self.assertRaises(Exception):
            validate_context_actions(
                _valid_panel(draft=_valid_draft(round_revision=5))
            )

    def test_closed_draft_command_union_accepts_canonical_spellings(self):
        entries = [
            {
                "actor_id": 2,
                "command": {"kind": "skill", "payload": {"skill_key": "t_ember_burst", "target_ids": [2]}},
            },
            {
                "actor_id": 2,
                "command": {
                    "kind": "skill",
                    "payload": {"skill_key": "t_ember_burst", "target_shorthand": "all-enemies"},
                },
            },
            {"actor_id": 2, "command": {"kind": "item", "payload": {"item_key": "t_ember_spray", "target_id": 2}}},
            {"actor_id": 2, "command": {"kind": "tactical", "payload": {"key": "defend"}}},
            {"actor_id": 2, "command": {"kind": "tactical", "payload": {"key": "taunt", "target_id": 2}}},
        ]
        for entry in entries:
            with self.subTest(command=entry["command"]):
                validate_context_actions(
                    _valid_panel(
                        draft=_valid_draft(entries=[entry], needs_selection_ids=[])
                    )
                )

    def test_closed_draft_command_union_rejects_legacy_and_contradictory_spellings(self):
        bad = [
            {"kind": "skill", "payload": {"skill_key": "x", "targets_or_shorthand": [2]}},
            {"kind": "skill", "payload": {"skill_key": "x", "target_ids": [2], "target_shorthand": "all"}},
            {"kind": "skill", "payload": {"skill_key": "x", "scale": 3.0}},
            {"kind": "skill", "payload": {"skill_key": "flee"}},
            {"kind": "tactical", "payload": {"tactical_key": "defend"}},
            {"kind": "tactical", "payload": {"key": "taunt"}},
            {"kind": "tactical", "payload": {"key": "defend", "target_id": 2}},
            {"kind": "item", "payload": {"item_key": "x", "target_id": 0}},
            {"kind": "surrender", "payload": {}},
        ]
        for command in bad:
            with self.subTest(command=command):
                with self.assertRaises(Exception):
                    validate_context_actions(
                        _valid_panel(
                            draft=_valid_draft(
                                entries=[{"actor_id": 2, "command": command}],
                                needs_selection_ids=[],
                            )
                        )
                    )

    def test_draft_command_rejects_present_null_optional_fields(self):
        bad = [
            {"kind": "tactical", "payload": {"key": "defend", "target_id": None}},
            {"kind": "skill", "payload": {"skill_key": "t_ember_burst", "target_ids": None}},
            {"kind": "skill", "payload": {"skill_key": "t_ember_burst", "scale": None}},
            {"kind": "item", "payload": {"item_key": "t_ember_spray", "target_id": None}},
        ]
        for command in bad:
            with self.subTest(command=command):
                with self.assertRaises(Exception):
                    validate_context_actions(
                        _valid_panel(
                            draft=_valid_draft(
                                entries=[{"actor_id": 2, "command": command}],
                                needs_selection_ids=[],
                            )
                        )
                    )

    def test_wire_command_omits_an_empty_target_list(self):
        # A NONE/SELF skill stores an empty target list; the wire carries no
        # target field, so the panel still validates.
        from world.rules.combat_view import _wire_draft_command

        command = _wire_draft_command(
            {
                "kind": "skill",
                "payload": {"skill_key": "t_ember_burst", "targets_or_shorthand": []},
            }
        )
        self.assertEqual(
            command, {"kind": "skill", "payload": {"skill_key": "t_ember_burst"}}
        )
        validate_context_actions(
            _valid_panel(
                draft=_valid_draft(
                    entries=[{"actor_id": 2, "command": command}],
                    needs_selection_ids=[],
                )
            )
        )

    @covers_requirement(
        "webclient-combat-menu::party-protocol-publishes-bounded-actor-choices-and-durable-progress"
    )
    def test_actor_and_required_identities_must_be_presented_allies(self):
        # The actor summary and the draft's required actors must join party
        # participants, never a foe.
        with self.assertRaises(Exception):
            validate_context_actions(
                _valid_panel(participants=[_valid_participant(team="foes")])
            )
        with self.assertRaises(Exception):
            validate_context_actions(
                _valid_panel(
                    draft=_valid_draft(
                        required_actor_ids=[2, 9],
                        needs_selection_ids=[9],
                    ),
                    participants=[
                        _valid_participant(),
                        _valid_participant(identity=9, token="e1", team="foes"),
                    ],
                )
            )

    def test_taunt_targets_must_be_presented_enemies(self):
        with self.assertRaises(Exception):
            validate_context_actions(
                self._panel(
                    **{
                        _TACTICS: [
                            _valid_tactic(key="taunt", label="嘲諷", targets=[2])
                        ]
                    }
                )
            )

    @covers_requirement(
        "webclient-combat-menu::version-7-root-keys-and-recovery-choices-are-exact"
    )
    def test_recovery_has_no_personal_choices(self):
        with self.assertRaises(Exception):
            validate_context_actions(_recovery_panel(choices=_valid_choices()))
        with self.assertRaises(Exception):
            validate_context_actions(_recovery_panel(actors=[_valid_actor()]))
        with self.assertRaises(Exception):
            validate_context_actions(_recovery_panel(root_actions=["attack"]))
        normalized = validate_context_actions(_recovery_panel())
        self.assertIsNone(normalized["choices"])
        self.assertIsNone(normalized["draft"])
        self.assertEqual(normalized["secondary_actions"], ["surrender"])


class PartyProtocolPresenterTests(BattlefieldIsolation, EvenniaTestCase):
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
        self.room = create_object(Room, key="party arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster()
        self.monster.location = self.room
        self.registry = build_production_registry()

    def _render(self, actor=None):
        return self.registry.render(
            "context_actions",
            PresentationContext(actor=actor or self.player, protocol_version=1),
        )

    @covers_requirement(
        "webclient-combat-menu::party-protocol-publishes-bounded-actor-choices-and-durable-progress"
    )
    def test_ready_panel_publishes_actors_choices_items_and_tactics(self):
        self.player.db.inventory = ["t_ember_spray"]
        engage(self.player, self.monster)
        payload = self._render()
        self.assertEqual(
            [actor["identity"] for actor in payload["actors"]], [self.player.pk]
        )
        self.assertTrue(payload["actors"][0]["commandable"])
        self.assertIsNone(payload["actors"][0]["reason"])
        self.assertEqual(payload["choices"]["actor_id"], self.player.pk)
        item = next(
            row for row in payload["choices"]["items"] if row["item_key"] == "t_ember_spray"
        )
        self.assertEqual(item["quantity"], 1)
        self.assertTrue(item["summary"])
        self.assertTrue(item["beneficial"])
        self.assertFalse(item["hostile"])
        tactics = {row["key"]: row for row in payload["choices"][_TACTICS]}
        self.assertEqual(set(tactics), {"defend", "dodge", "taunt"})
        self.assertEqual(tactics["defend"]["targets"], [])
        self.assertEqual(tactics["dodge"]["targets"], [])
        self.assertIn(self.monster.pk, tactics["taunt"]["targets"])
        self.assertEqual(list(payload["draft"]["required_actor_ids"]), [self.player.pk])

    @covers_requirement(
        "webclient-combat-menu::party-protocol-publishes-bounded-actor-choices-and-durable-progress"
    )
    def test_partial_party_draft_carries_the_closed_wire_command(self):
        from typeclasses.npcs import NPC
        from world.rules.combat_session import submit_player_action
        from world.rules.party import join_party

        companion = create_object(NPC, key="draft companion", location=self.room)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.base = 100
        companion.traits.hp.current = 100
        join_party(companion, self.player)
        grant_lineage(self.player, [SYNTH_SKILLS["t_ember_burst"].key])
        engage(self.player, self.monster)
        result = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        self.assertEqual(result["outcome"], "draft", result)
        payload = self._render()
        self.assertEqual(
            sorted(payload["draft"]["required_actor_ids"]),
            sorted([self.player.pk, companion.pk]),
        )
        entry = next(
            row for row in payload["draft"]["entries"] if row["actor_id"] == self.player.pk
        )
        self.assertEqual(entry["command"]["kind"], "skill")
        self.assertIn("target_ids", entry["command"]["payload"])
        self.assertNotIn("targets_or_shorthand", entry["command"]["payload"])


if __name__ == "__main__":
    unittest.main()
