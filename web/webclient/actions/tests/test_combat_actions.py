"""Party-combat command transport validators, adapters and result variants.

Each closed payload shape is checked at the validator level, and every adapter
is driven against a real synthetic combat session: the authorized commander
acts through the adapter, the rules boundary is the only writer, and the exact
result variant (draft progress, round, terminal, retry, stale, rejection) is
asserted together with the state it did or did not change.
"""

import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
from typeclasses.rooms import Room

from web.webclient.actions.combat_actions import (
    AFFECTED_PANELS,
    CODE_ACTOR_CHOICES,
    CODE_ALREADY_COMMITTED,
    CODE_COMBAT_TERMINAL,
    CODE_DRAFT_SAVED,
    CODE_NEEDS_SELECTION,
    CODE_PARTY_EXIT_PROMPT,
    CODE_ROUND_COMMITTED,
    CODE_STALE_COMMAND,
    CombatActionError,
    _actor_choices_adapter,
    _command_adapter,
    _exit_confirm_adapter,
    _exit_prompt_adapter,
    validate_actor_choices_payload,
    validate_command_payload,
    validate_exit_confirm_payload,
    validate_exit_prompt_payload,
    validate_party_exit_prompt_data,
)
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from world.rules.combat_beats import RoundRecord
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    PARTY_EXIT_RETREAT,
    PARTY_EXIT_SURRENDER,
    engage,
    read_session,
)
from world.rules.party import join_party
from world.rules.tests._combat_session_helpers import (
    _monster,
    _player,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.tests.synthetic_data import SYNTH_SKILLS

# Kit rows: one per TargetSpec the command union must discriminate.
_T_SINGLE = SYNTH_SKILLS["t_ember_burst"].key
_T_SELF = SYNTH_SKILLS["t_moss_veil"].key
_T_NONE = SYNTH_SKILLS["t_cinder_breath"].key
_T_AREA = SYNTH_SKILLS["t_glowmire_bloom"].key

_ALL_SKILLS = (_T_SINGLE, _T_SELF, _T_NONE, _T_AREA)


def _command(**overrides):
    value = {
        "session_id": "hostile:1:0",
        "round_revision": 1,
        "draft_version": 0,
        "actor_id": 2,
        "command": {"kind": "tactic", "payload": {"key": "defend"}},
    }
    value.update(overrides)
    return value


class CombatPayloadValidationTests(EvenniaTestCase):
    """Exact closed payload shapes, resolved through the scoped skill registry."""

    def setUp(self):
        # The skill command's TargetSpec comes from the registry, so the kit
        # scope must cover the validator as well as the adapters.
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            "items",
            extra=synth_innate_overlay(),
        )
        super().setUp()

    def test_actor_choices_payload_is_exact(self):
        validated = validate_actor_choices_payload(
            {"session_id": "hostile:1:0", "round_revision": 1, "actor_id": 7}
        )
        self.assertEqual(
            validated, {"session_id": "hostile:1:0", "round_revision": 1, "actor_id": 7}
        )
        bad = (
            {"session_id": "x", "round_revision": 1},
            {"session_id": "x", "round_revision": 1, "actor_id": 7, "extra": 1},
            {"session_id": "x", "round_revision": -1, "actor_id": 7},
            {"session_id": "x", "round_revision": True, "actor_id": 7},
            {"session_id": "x", "round_revision": 1, "actor_id": 0},
            {"session_id": "", "round_revision": 1, "actor_id": 7},
            {"session_id": "x" * 129, "round_revision": 1, "actor_id": 7},
            {"session_id": "x", "round_revision": 1, "actor_id": "7"},
        )
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(CombatActionError):
                    validate_actor_choices_payload(payload)
        # A first round's revision is zero, so it stays a legal reference.
        self.assertEqual(
            validate_actor_choices_payload(
                {"session_id": "x", "round_revision": 0, "actor_id": 7}
            )["round_revision"],
            0,
        )

    def test_command_payload_is_exact(self):
        validated = validate_command_payload(_command())
        self.assertEqual(validated["actor_id"], 2)
        self.assertEqual(validated["command"]["kind"], "tactic")
        bad = (
            {k: v for k, v in _command().items() if k != "draft_version"},
            {**_command(), "base_revision": 3},
            {**_command(), "round_revision": -1},
            {**_command(), "draft_version": True},
            {**_command(), "actor_id": None},
        )
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(CombatActionError):
                    validate_command_payload(payload)

    def test_skill_command_preserves_every_targetspec_shape(self):
        forms = (
            # NONE and SELF carry no target field at all.
            {"kind": "skill", "payload": {"skill_key": _T_NONE}},
            {"kind": "skill", "payload": {"skill_key": _T_SELF}},
            {
                "kind": "skill",
                "payload": {"skill_key": _T_SINGLE, "target_ids": [3]},
            },
            {
                "kind": "skill",
                "payload": {"skill_key": _T_AREA, "target_ids": [3, 4]},
            },
            {
                "kind": "skill",
                "payload": {"skill_key": _T_AREA, "target_shorthand": "all-enemies"},
            },
        )
        for form in forms:
            with self.subTest(form=form):
                normalized = validate_command_payload(_command(command=form))
                self.assertEqual(normalized["command"]["kind"], "skill")

    def test_skill_command_rejects_mismatched_and_reserved_shapes(self):
        bad = (
            # Reserved flee never travels as a skill command.
            {"kind": "skill", "payload": {"skill_key": "flee"}},
            {"kind": "skill", "payload": {"skill_key": "t_never_registered"}},
            # NONE/SELF accept no target field; SINGLE requires exactly one.
            {"kind": "skill", "payload": {"skill_key": _T_NONE, "target_ids": [3]}},
            {"kind": "skill", "payload": {"skill_key": _T_SELF, "target_ids": [3]}},
            {"kind": "skill", "payload": {"skill_key": _T_SINGLE, "target_ids": [3, 4]}},
            {"kind": "skill", "payload": {"skill_key": _T_SINGLE}},
            # Both target fields, empty lists, duplicates and bad shorthands.
            {
                "kind": "skill",
                "payload": {
                    "skill_key": _T_AREA,
                    "target_ids": [3],
                    "target_shorthand": "all",
                },
            },
            {"kind": "skill", "payload": {"skill_key": _T_AREA, "target_ids": []}},
            {"kind": "skill", "payload": {"skill_key": _T_AREA, "target_ids": [3, 3]}},
            {"kind": "skill", "payload": {"skill_key": _T_AREA, "target_ids": [0]}},
            {
                "kind": "skill",
                "payload": {"skill_key": _T_SINGLE, "target_shorthand": "all"},
            },
            {
                "kind": "skill",
                "payload": {"skill_key": _T_AREA, "target_shorthand": "all-foes"},
            },
            # Unknown fields, present-null optionals.
            {"kind": "skill", "payload": {"skill_key": _T_SINGLE, "target_id": 3}},
            {"kind": "skill", "payload": {"skill_key": _T_SINGLE, "target_ids": None}},
            {"kind": "skill", "payload": {"skill_key": _T_NONE, "scale": None}},
        )
        for command in bad:
            with self.subTest(command=command):
                with self.assertRaises(CombatActionError):
                    validate_command_payload(_command(command=command))

    @covers_requirement(
        "webclient-action-dispatch::combat-cast-payload-carries-an-optional-bounded-scale"
    )
    def test_skill_scale_stays_a_closed_bounded_set(self):
        for scale in (0.25, 0.5, 1, 2, 4):
            with self.subTest(scale=scale):
                normalized = validate_command_payload(
                    _command(
                        command={
                            "kind": "skill",
                            "payload": {
                                "skill_key": _T_AREA,
                                "target_shorthand": "all-enemies",
                                "scale": scale,
                            },
                        }
                    )
                )
                self.assertEqual(normalized["command"]["payload"]["scale"], float(scale))
        # An absent scale is exactly 1, and every non-member is malformed.
        self.assertEqual(
            validate_command_payload(
                _command(command={"kind": "skill", "payload": {"skill_key": _T_SELF}})
            )["command"]["payload"]["scale"],
            1.0,
        )
        for bad in (3.0, 0, "2", True, None):
            with self.subTest(scale=bad):
                with self.assertRaises(CombatActionError):
                    validate_command_payload(
                        _command(
                            command={
                                "kind": "skill",
                                "payload": {"skill_key": _T_SELF, "scale": bad},
                            }
                        )
                    )

    def test_item_and_tactic_commands_are_closed(self):
        validate_command_payload(
            _command(command={"kind": "item", "payload": {"item_key": "t_ember_spray"}})
        )
        validate_command_payload(
            _command(
                command={
                    "kind": "item",
                    "payload": {"item_key": "t_ember_spray", "target_id": 3},
                }
            )
        )
        validate_command_payload(
            _command(
                command={"kind": "tactic", "payload": {"key": "taunt", "target_id": 3}}
            )
        )
        bad = (
            {"kind": "item", "payload": {}},
            {"kind": "item", "payload": {"item_key": ""}},
            {"kind": "item", "payload": {"item_key": "two words"}},
            {"kind": "item", "payload": {"item_key": "x", "target_id": 0}},
            {"kind": "item", "payload": {"item_key": "x", "target_id": None}},
            {"kind": "item", "payload": {"item_key": "x", "quantity": 2}},
            {"kind": "tactic", "payload": {}},
            {"kind": "tactic", "payload": {"key": "block"}},
            {"kind": "tactic", "payload": {"key": "defend", "target_id": 3}},
            {"kind": "tactic", "payload": {"key": "dodge", "target_id": 3}},
            {"kind": "tactic", "payload": {"key": "taunt"}},
            {"kind": "tactic", "payload": {"key": "taunt", "target_id": None}},
            # The internal draft spelling is not the action's wire spelling.
            {"kind": "tactical", "payload": {"tactical_key": "defend"}},
            {"kind": "surrender", "payload": {}},
        )
        for command in bad:
            with self.subTest(command=command):
                with self.assertRaises(CombatActionError):
                    validate_command_payload(_command(command=command))

    def test_exit_payloads_are_exact(self):
        prompt = validate_exit_prompt_payload(
            {"session_id": "hostile:1:0", "round_revision": 1, "operation": "surrender"}
        )
        self.assertEqual(prompt["operation"], "surrender")
        confirmed = validate_exit_confirm_payload(
            {
                "session_id": "hostile:1:0",
                "round_revision": 1,
                "operation": "retreat",
                "confirmation_token": "R-1-abcDEF0123",
            }
        )
        self.assertEqual(confirmed["confirmation_token"], "R-1-abcDEF0123")
        bad = (
            {"session_id": "x", "round_revision": 1},
            {"session_id": "x", "round_revision": 1, "operation": "charge"},
            {"session_id": "x", "round_revision": 1, "operation": "surrender", "extra": 1},
            {"session_id": "x", "round_revision": 1, "operation": "surrender", "confirmation_token": "a b"},
            {"session_id": "x", "round_revision": 1, "operation": "surrender", "confirmation_token": ""},
            {"session_id": "x", "round_revision": 1, "operation": "surrender", "confirmation_token": "a" * 129},
        )
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(CombatActionError):
                    validate_exit_confirm_payload(payload)

    def test_party_exit_prompt_data_is_exactly_bounded(self):
        good = {
            "operation": "surrender",
            "confirmation_token": "S-1-abcdef",
            "scope": "party",
            "consequence": "整隊退出戰鬥。",
        }
        self.assertEqual(validate_party_exit_prompt_data(good), good)
        bad = (
            {k: v for k, v in good.items() if k != "consequence"},
            {**good, "session_id": "hostile:1:0"},
            {**good, "round_revision": 1},
            {**good, "scope": "self"},
            {**good, "operation": "charge"},
            {**good, "consequence": ""},
            {**good, "consequence": "字" * 513},
            {**good, "confirmation_token": "a b"},
        )
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(CombatActionError):
                    validate_party_exit_prompt_data(payload)


class CombatCommandAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    """Real-session adapter behavior for the four guarded combat actions."""

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
        self.room = create_object(Room, key="transport arena")
        self.player = _player("transport player")
        self.player.location = self.room
        self.monster = _monster("transport goblin")
        self.monster.location = self.room
        grant_lineage(self.player, list(_ALL_SKILLS))

    # -- helpers ---------------------------------------------------------

    def _companion(self, key="transport companion"):
        companion = create_object(NPC, key=key, location=self.room)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.base = 100
        companion.traits.hp.current = 100
        join_party(companion, self.player)
        return companion

    def _record(self):
        return read_session(self.player)

    def _engage(self):
        engage(self.player, self.monster)
        return self._record()

    def _command_payload(self, command, actor=None):
        record = self._record()
        return {
            "session_id": record.session_id,
            "round_revision": record.round_revision,
            "draft_version": record.draft_version,
            "actor_id": (actor or self.player).pk,
            "command": command,
        }

    # -- command variants ------------------------------------------------

    @covers_requirement(
        "webclient-action-dispatch::combat-cast-payload-carries-an-optional-bounded-scale"
    )
    def test_solo_command_commits_a_round_and_reports_round_committed(self):
        self._engage()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
        ):
            result = _command_adapter(
                self.player,
                self._command_payload(
                    {
                        "kind": "skill",
                        "payload": {"skill_key": _T_SINGLE, "target_ids": [self.monster.pk]},
                    }
                ),
            )
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(result["code"], CODE_ROUND_COMMITTED)
        self.assertEqual(result["affected_panels"], AFFECTED_PANELS)
        self.assertIsInstance(result["combat_round"], RoundRecord)
        self.assertNotIn("data", result)
        self.assertEqual(self._record().rounds_elapsed, 1)

    def test_party_member_command_is_saved_without_a_round(self):
        companion = self._companion()
        self._engage()
        before = self._record()
        result = _command_adapter(
            self.player,
            self._command_payload(
                {"kind": "tactic", "payload": {"key": "defend"}},
            ),
        )
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(result["code"], CODE_DRAFT_SAVED)
        self.assertNotIn("combat_round", result)
        after = self._record()
        self.assertEqual(after.rounds_elapsed, 0)
        self.assertEqual(after.draft_version, before.draft_version + 1)
        self.assertEqual(int(self.player.pk) in (after.draft_entries or {}), True)
        self.assertEqual(companion.pk in (after.draft_entries or {}), False)

    def test_member_needing_reselection_reports_needs_selection(self):
        companion = self._companion()
        self._engage()
        # The commander's own affordable selection is admitted first ...
        self.assertEqual(
            _command_adapter(
                self.player,
                self._command_payload(
                    {
                        "kind": "skill",
                        "payload": {"skill_key": _T_SINGLE, "target_ids": [self.monster.pk]},
                    }
                ),
            )["code"],
            CODE_DRAFT_SAVED,
        )
        # ... then the commander can no longer pay for it, so the next member's
        # confirmation must report the member-specific reselection.
        self.player.traits.mp.current = 0
        result = _command_adapter(
            self.player,
            self._command_payload(
                {"kind": "tactic", "payload": {"key": "defend"}}, actor=companion
            ),
        )
        self.assertEqual(result["outcome"], "rejected", result)
        self.assertEqual(result["code"], CODE_NEEDS_SELECTION)
        self.assertNotIn("data", result)
        self.assertEqual(self._record().rounds_elapsed, 0)

    def test_forged_actor_reference_is_rejected_without_state_change(self):
        self._engage()
        before = self._record()
        result = _command_adapter(
            self.player,
            self._command_payload(
                {"kind": "tactic", "payload": {"key": "defend"}}, actor=self.monster
            ),
        )
        self.assertEqual(result["outcome"], "rejected", result)
        self.assertEqual(result["code"], "forbidden_actor")
        after = self._record()
        self.assertEqual(after.draft_version, before.draft_version)
        self.assertEqual(after.rounds_elapsed, before.rounds_elapsed)

    def test_absent_actor_reference_is_rejected(self):
        self._engage()
        record = self._record()
        result = _command_adapter(
            self.player,
            {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "draft_version": record.draft_version,
                "actor_id": self.monster.pk + 100_000,
                "command": {"kind": "tactic", "payload": {"key": "defend"}},
            },
        )
        self.assertEqual(result["code"], "forbidden_actor")

    def test_stale_session_revision_and_draft_version_are_stale_command(self):
        self._engage()
        record = self._record()
        base = self._command_payload({"kind": "tactic", "payload": {"key": "defend"}})
        for overrides in (
            {"round_revision": record.round_revision + 1},
            {"draft_version": record.draft_version + 1},
            {"session_id": "hostile:999:0"},
        ):
            with self.subTest(overrides=overrides):
                result = _command_adapter(self.player, {**base, **overrides})
                self.assertEqual(result["outcome"], "stale", result)
                self.assertEqual(result["code"], CODE_STALE_COMMAND)
        self.assertEqual(self._record().draft_version, record.draft_version)

    def test_committed_round_retry_reports_already_committed(self):
        self._engage()
        self.monster.traits.hp.current = 1
        payload = self._command_payload(
            {
                "kind": "skill",
                "payload": {"skill_key": BASIC_ATTACK_KEY, "target_ids": [self.monster.pk]},
            }
        )

        # A single-member party commits on the first confirmation, and the
        # resolved round defeats the one-hit-point foe, so the settlement is
        # terminal and the active record is cleared.
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch("world.rules.action.gates.roll_d100", return_value=100),
        ):
            first = _command_adapter(self.player, payload)
        self.assertEqual(first["outcome"], "success", first)
        self.assertEqual(first["code"], CODE_COMBAT_TERMINAL)
        self.assertIsNone(self._record())
        # The durable receipt still names this session and revision, so the
        # retried confirmation is the accepted operation retry, not a
        # rejection and never a second round.
        retry = _command_adapter(self.player, payload)
        self.assertEqual(retry["outcome"], "success", retry)
        self.assertEqual(retry["code"], CODE_ALREADY_COMMITTED)
        self.assertNotIn("combat_round", retry)

    def test_no_active_session_rejects(self):
        result = _command_adapter(
            self.player,
            {
                "session_id": "hostile:1:0",
                "round_revision": 1,
                "draft_version": 0,
                "actor_id": self.player.pk,
                "command": {"kind": "tactic", "payload": {"key": "defend"}},
            },
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_active_session")

    def test_item_command_saves_an_actor_scoped_draft_entry(self):
        companion = self._companion()
        self.player.traits.hp.current = 50
        self.player.db.inventory = ["t_ember_spray"]
        self._engage()
        result = _command_adapter(
            self.player,
            self._command_payload(
                {"kind": "item", "payload": {"item_key": "t_ember_spray"}}
            ),
        )
        self.assertEqual(result["code"], CODE_DRAFT_SAVED, result)
        # The selection is a draft entry; nothing was consumed yet.
        self.assertEqual(self.player.db.inventory, ["t_ember_spray"])
        self.assertTrue(companion.pk not in (self._record().draft_entries or {}))

    # -- actor choices ---------------------------------------------------

    def test_item_command_commits_the_round_and_consumes_once(self):
        self.player.traits.hp.current = int(self.player.traits.hp.max) - 20
        self.player.db.inventory = ["t_ember_spray"]
        self._engage()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
        ):
            result = _command_adapter(
                self.player,
                self._command_payload(
                    {"kind": "item", "payload": {"item_key": "t_ember_spray"}}
                ),
            )
        self.assertEqual(result["code"], CODE_ROUND_COMMITTED, result)
        self.assertEqual(self.player.db.inventory, [])
        round_record = result["combat_round"]
        self.assertIsInstance(round_record, RoundRecord)
        self.assertEqual(
            round_record.round_id, f"{self._record().session_id}/1"
        )

    @covers_requirement(
        "webclient-combat-beats::beat-hp-is-projected-on-the-server-and-checked-against-the-round-s-recorded-hp"
    )
    def test_item_heal_with_foe_damage_makes_the_round_beats_unavailable(self):
        # The item heals the actor while the foe damages it in the same round:
        # the round has an HP change with no damage entry, so the projection
        # cannot be checked against the recorded HP and the panel is
        # unavailable while the text output stays authoritative.
        self.player.traits.hp.current = int(self.player.traits.hp.max) - 20
        self.player.db.inventory = ["t_ember_spray"]
        self._engage()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch("world.rules.action.gates.roll_d100", return_value=1),
        ):
            result = _command_adapter(
                self.player,
                self._command_payload(
                    {"kind": "item", "payload": {"item_key": "t_ember_spray"}}
                ),
            )
        self.assertEqual(result["code"], CODE_ROUND_COMMITTED, result)
        round_record = result["combat_round"]
        self.assertIsInstance(round_record, RoundRecord)
        with patch("web.webclient.presentation.combat_beats.log_warn") as warn:
            payload = build_production_registry().render(
                "combat_beats",
                PresentationContext(
                    actor=self.player,
                    protocol_version=1,
                    combat_round=round_record,
                ),
            )
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "presentation_unavailable")
        self.assertNotIn("beats", payload)
        # The heal is the unmodeled HP mover: the bounded reason is the HP
        # mismatch, never a bound.
        self.assertEqual(warn.call_args.kwargs["context"]["reason"], "hp_mismatch")

    def _session(self):
        from types import SimpleNamespace

        session = SimpleNamespace(
            puppet=self.player, sent=[], ndb=SimpleNamespace(), sessid=1
        )
        session.protocol_key = "websocket"
        session.msg = lambda **kwargs: session.sent.append(kwargs)
        attach_coordinator(session, build_production_registry())
        return session

    def test_actor_query_selects_the_authorized_companion_only(self):
        companion = self._companion()
        self._engage()
        record = self._record()
        session = self._session()
        result = _actor_choices_adapter(
            self.player,
            {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "actor_id": companion.pk,
            },
            session,
        )
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(result["code"], CODE_ACTOR_CHOICES)
        self.assertNotIn("data", result)
        # The selection is transport-owned and read back through the context.
        context = build_presentation_context(session, self.player)
        self.assertEqual(context.party_actor, companion.pk)
        # A read-only query never mutates the session or the draft.
        after = self._record()
        self.assertEqual(after.draft_version, record.draft_version)
        self.assertEqual(after.round_revision, record.round_revision)
        self.assertEqual(after.rounds_elapsed, record.rounds_elapsed)

    def test_actor_query_rejects_a_foe_and_a_stale_revision(self):
        self._engage()
        record = self._record()
        session = self._session()
        for payload, expected in (
            (
                {
                    "session_id": record.session_id,
                    "round_revision": record.round_revision,
                    "actor_id": self.monster.pk,
                },
                "forbidden_actor",
            ),
            (
                {
                    "session_id": "hostile:999:0",
                    "round_revision": record.round_revision,
                    "actor_id": self.player.pk,
                },
                CODE_STALE_COMMAND,
            ),
            (
                {
                    "session_id": record.session_id,
                    "round_revision": record.round_revision + 1,
                    "actor_id": self.player.pk,
                },
                CODE_STALE_COMMAND,
            ),
        ):
            with self.subTest(payload=payload):
                result = _actor_choices_adapter(self.player, payload, session)
                self.assertEqual(result["code"], expected)
                self.assertNotIn("data", result)
        self.assertEqual(build_presentation_context(session, self.player).party_actor, None)

    # -- party exit ------------------------------------------------------

    def test_exit_prompt_returns_exactly_the_bounded_data(self):
        record = self._engage()
        for operation in (PARTY_EXIT_SURRENDER, PARTY_EXIT_RETREAT):
            with self.subTest(operation=operation):
                result = _exit_prompt_adapter(
                    self.player,
                    {
                        "session_id": record.session_id,
                        "round_revision": record.round_revision,
                        "operation": operation,
                    },
                )
                self.assertEqual(result["outcome"], "success", result)
                self.assertEqual(result["code"], CODE_PARTY_EXIT_PROMPT)
                self.assertEqual(
                    set(result["data"]),
                    {"operation", "confirmation_token", "scope", "consequence"},
                )
                self.assertEqual(result["data"]["operation"], operation)
                self.assertEqual(result["data"]["scope"], "party")
                self.assertTrue(result["data"]["consequence"])
                self.assertLessEqual(len(result["data"]["consequence"]), 512)
                self.assertEqual(result["affected_panels"], ())
        # A prompt changes nothing.
        after = self._record()
        self.assertEqual(after.round_revision, record.round_revision)
        self.assertEqual(after.draft_version, record.draft_version)

    def test_exit_prompt_rejects_a_foreign_session_as_stale(self):
        record = self._engage()
        result = _exit_prompt_adapter(
            self.player,
            {
                "session_id": "hostile:999:0",
                "round_revision": record.round_revision,
                "operation": PARTY_EXIT_SURRENDER,
            },
        )
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(result["code"], CODE_STALE_COMMAND)

    def test_exit_confirm_settles_once_and_replays_as_already_committed(self):
        record = self._engage()
        prompt = _exit_prompt_adapter(
            self.player,
            {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "operation": PARTY_EXIT_SURRENDER,
            },
        )
        payload = {
            "session_id": record.session_id,
            "round_revision": record.round_revision,
            "operation": PARTY_EXIT_SURRENDER,
            "confirmation_token": prompt["data"]["confirmation_token"],
        }
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
        ):
            result = _exit_confirm_adapter(self.player, payload)
        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(result["code"], CODE_COMBAT_TERMINAL)
        self.assertNotIn("data", result)
        # The session is gone; the replayed confirmation is the boundary's own
        # recorded settlement, never a second settlement.
        replay = _exit_confirm_adapter(self.player, payload)
        self.assertEqual(replay["outcome"], "success")
        self.assertEqual(replay["code"], CODE_ALREADY_COMMITTED)

    def test_exit_confirm_rejects_a_forged_token(self):
        record = self._engage()
        result = _exit_confirm_adapter(
            self.player,
            {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "operation": PARTY_EXIT_SURRENDER,
                "confirmation_token": "S-1-0000000000000000",
            },
        )
        self.assertEqual(result["outcome"], "rejected", result)
        self.assertEqual(result["code"], "invalid_confirmation_token")
        self.assertEqual(self._record().round_revision, record.round_revision)

    def test_settlement_narrative_is_emitted_only_for_a_committed_round(self):
        companion = self._companion()
        record = self._engage()
        with patch.object(self.player, "msg") as emit:
            _command_adapter(
                self.player,
                {
                    "session_id": record.session_id,
                    "round_revision": record.round_revision,
                    "draft_version": record.draft_version,
                    "actor_id": self.player.pk,
                    "command": {"kind": "tactic", "payload": {"key": "defend"}},
                },
            )
            self.assertEqual(emit.call_count, 0)
        self.assertIsNotNone(companion)
        record = self._record()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch.object(self.player, "msg") as emit,
        ):
            result = _command_adapter(
                self.player,
                {
                    "session_id": record.session_id,
                    "round_revision": record.round_revision,
                    "draft_version": record.draft_version,
                    "actor_id": companion.pk,
                    "command": {"kind": "tactic", "payload": {"key": "defend"}},
                },
            )
        self.assertEqual(result["code"], CODE_ROUND_COMMITTED, result)
        self.assertGreater(emit.call_count, 0)
        self.assertIsInstance(result["combat_round"], RoundRecord)

if __name__ == "__main__":
    unittest.main()
