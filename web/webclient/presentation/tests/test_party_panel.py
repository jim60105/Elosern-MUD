"""Tests for the version-1 ``party`` presentation panel (webclient-align-04).

Presenter shape (party-list order, exact row vocabulary, canonical bond-stage
names only, true-trait HP), empty-party availability, stale-dbid omission,
unavailable forms, read-only rendering, the pure validator's drift rejections,
the connected leave/purge push seams, and the identity-join contract against
the combat participant rows. ``covers_requirement`` annotations for the new
``webclient-party-panel`` IDs land at this change's archive/sync commit (the
checker resolves IDs only from ``openspec/specs/``).
"""

from copy import deepcopy
from types import SimpleNamespace
import unittest

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation import watchers
from web.webclient.presentation.affordances import MAX_DISPLAY_NAME_CODE_POINTS
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    validate_ui_snapshot,
)
from web.webclient.presentation.party import (
    PARTY_MAX_ROWS,
    PARTY_SCHEMA_VERSION,
    validate_party,
)
from web.webclient.presentation.registry import build_production_registry
from world.quests.catalog import register_catalog
from world.rules.action import stored_gauge_pair
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import get_config
from world.rules.combat_session import engage
from world.rules.npc_identity import npc_display_name
from world.rules.party import join_party
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage

UNAVAILABLE_PAYLOAD = {
    "schema_version": PARTY_SCHEMA_VERSION,
    "available": False,
    "reason": {"code": "party_unavailable", "message": "隊伍資訊目前無法顯示"},
}


def _player(key="隊伍測試者"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _companion(key, room, hp_current=100, hp_maximum=100):
    npc = create_object(NPC, key=key, location=room)
    npc.race = "human"
    npc.apply_race_baseline()
    npc.traits.hp.base = hp_maximum
    npc.traits.hp.current = hp_current
    npc.traits.agility.base = 10
    return npc


def _monster(key="哥布林測試", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


def _slot(**overrides):
    row = {
        "identity": 41,
        "display_name": "守衛長薇拉",
        "portrait_ref": None,
        "hp_current": 180,
        "hp_maximum": 220,
        "bond_stage": "摯友",
    }
    row.update(overrides)
    return row


class _RecordingSession:
    """Minimal session stand-in that records every transport send."""

    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 901

    def msg(self, **kwargs):
        self.sent.append(kwargs)


_CALENDAR = SimpleNamespace(
    year=1,
    season_index=0,
    season_name="春季",
    day_in_season=3,
    hour=12,
    minute=0,
    second=0,
)


class PartyPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="隊伍大廳")
        self.player = _player()
        self.player.location = self.room
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def _render(self):
        return self.registry.render("party", self.context)

    def test_two_companion_rows_follow_party_order_and_exact_vocabulary(self):
        first = _companion("薇拉", self.room, hp_current=60, hp_maximum=120)
        second = _companion("米雅", self.room, hp_current=44, hp_maximum=44)
        join_party(first, self.player)
        join_party(second, self.player)
        outcome = apply_affinity_change(
            first, self.player, AffinitySource.QUEST_COMPLETION, 47
        )
        self.assertTrue(outcome.applied)
        affinity_value = first.relations.affinity_for(self.player)

        payload = self._render()
        self.assertEqual(payload["schema_version"], PARTY_SCHEMA_VERSION)
        self.assertIs(payload["available"], True)
        self.assertEqual(
            [row["identity"] for row in payload["slots"]],
            [int(first.pk), int(second.pk)],
        )
        self.assertEqual(
            payload["slots"][0],
            {
                "identity": int(first.pk),
                "display_name": npc_display_name(first)[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                "portrait_ref": None,
                "hp_current": 60,
                "hp_maximum": 120,
                "bond_stage": get_config().stage_for_value(affinity_value).name,
            },
        )
        self.assertEqual(
            payload["slots"][1]["bond_stage"],
            get_config().stage_for_value(0).name,
        )
        # The raw affinity number never ships: the row key set is exact and no
        # numeric field carries the stored value.
        for row in payload["slots"]:
            self.assertEqual(
                set(row),
                {
                    "identity",
                    "display_name",
                    "portrait_ref",
                    "hp_current",
                    "hp_maximum",
                    "bond_stage",
                },
            )
            self.assertNotEqual(row["hp_current"], affinity_value)
            self.assertNotEqual(row["hp_maximum"], affinity_value)
            self.assertNotIn(affinity_value, row.values())

    def test_empty_party_is_available_with_no_slots(self):
        payload = self._render()
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["slots"], [])
        self.assertNotIn("reason", payload)

    def test_stale_membership_dbid_is_omitted_without_error(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        self.player.db.party = [int(companion.pk), 999_999]
        payload = self._render()
        self.assertEqual(
            [row["identity"] for row in payload["slots"]], [int(companion.pk)]
        )
        validate_party(payload)

    def test_creation_pending_puppet_sees_the_shared_unavailable_form(self):
        self.player.creation_pending = True
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_no_location_puppet_sees_the_shared_unavailable_form(self):
        self.player.location = None
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_rows_cap_at_four_and_presenting_twice_is_read_only(self):
        companions = [
            _companion(f"同伴{index}", self.room) for index in range(PARTY_MAX_ROWS)
        ]
        for companion in companions:
            join_party(companion, self.player)
        witness = companions[0]
        apply_affinity_change(
            witness, self.player, AffinitySource.QUEST_COMPLETION, 12
        )
        before = {
            "party": deepcopy(self.player.db.party),
            "relations": deepcopy(witness.db.relations_data),
            "traits": deepcopy(dict(witness.traits.trait_data)),
        }

        first = self._render()
        second = self._render()

        self.assertEqual(len(first["slots"]), PARTY_MAX_ROWS)
        self.assertEqual(first, second)
        self.assertEqual(self.player.db.party, before["party"])
        self.assertEqual(witness.db.relations_data, before["relations"])
        self.assertEqual(dict(witness.traits.trait_data), before["traits"])


class PartyValidatorTests(unittest.TestCase):
    def _panel(self, slots):
        return {"schema_version": PARTY_SCHEMA_VERSION, "available": True, "slots": slots}

    def test_valid_forms_normalize_identically(self):
        self.assertEqual(
            validate_party(self._panel([_slot()])), self._panel([_slot()])
        )
        self.assertEqual(validate_party(self._panel([])), self._panel([]))

    def test_bounds_only_hp_semantics(self):
        # Zero is legal and no current/maximum cross assertion exists — traits
        # are truth (the delta spec overrides the proposal's "positive" wording).
        validate_party(self._panel([_slot(hp_current=0, hp_maximum=0)]))
        validate_party(self._panel([_slot(hp_current=500, hp_maximum=1)]))

    def test_drift_rejections(self):
        cases = {
            "fifth row": self._panel([_slot(identity=i + 1) for i in range(5)]),
            "missing row key": self._panel(
                [{"identity": 1, "display_name": "a", "portrait_ref": None, "hp_current": 0, "hp_maximum": 0}]
            ),
            "unknown row key": self._panel([_slot(token="a1")]),
            "numeric bond_stage": self._panel([_slot(bond_stage=3)]),
            "bool bond_stage": self._panel([_slot(bond_stage=True)]),
            "blank bond_stage": self._panel([_slot(bond_stage="")]),
            "blank display_name": self._panel([_slot(display_name="")]),
            "over-bound display_name": self._panel(
                [_slot(display_name="同" * (MAX_DISPLAY_NAME_CODE_POINTS + 1))]
            ),
            "negative hp_current": self._panel([_slot(hp_current=-1)]),
            "bool identity": self._panel([_slot(identity=True)]),
            "zero identity": self._panel([_slot(identity=0)]),
            "non-null portrait_ref": self._panel([_slot(portrait_ref="42")]),
            "duplicate identities": self._panel(
                [_slot(identity=7), _slot(identity=7)]
            ),
            "version drift": {
                "schema_version": PARTY_SCHEMA_VERSION + 1,
                "available": True,
                "slots": [],
            },
            "unavailable discriminator": {
                "schema_version": PARTY_SCHEMA_VERSION,
                "available": False,
                "slots": [],
            },
            "slots not a list": {"schema_version": 1, "available": True, "slots": {}},
            "panel not a dict": ["nope"],
        }
        for label, payload in cases.items():
            with self.subTest(label):
                with self.assertRaises(ProtocolValidationError):
                    validate_party(payload)


class PartyPushTests(BattlefieldIsolation, EvenniaTest):
    """Connected-player pushes around the three party write seams."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self):
        super().setUp()
        register_catalog()
        watchers.clear_watchers()
        self.room = create_object(Room, key="队伍告别厅")
        self.player = _player()
        self.player.location = self.room
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()

    def tearDown(self):
        watchers.clear_watchers()
        super().tearDown()

    @staticmethod
    def _messages(session, name):
        return [call[name][0][0] for call in session.sent if name in call]

    def test_party_leave_action_publishes_full_snapshot_without_the_companion(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "r1",
            "base_revision": coordinator.revision,
            "action_id": "explore.party_leave",
            "payload": {"npc_id": int(companion.pk)},
        }

        handle_ui_action(
            session,
            self.player,
            envelope,
            self.action_registry,
            self.registry,
        )

        results = self._messages(session, "ui_action_result")
        snapshots = self._messages(session, "ui_snapshot")
        self.assertEqual(results[-1]["outcome"], "success")
        # The leave seam publishes a full snapshot (membership can pair with
        # anything), and the presentation publication precedes the result.
        self.assertTrue(snapshots, "party_leave must publish a full snapshot")
        last = snapshots[-1]
        identities = [row["identity"] for row in last["panels"]["party"]["slots"]]
        self.assertNotIn(int(companion.pk), identities)
        # Scripted protocol probe (task 5.2 evidence): the published envelope
        # is the exact wire form — full snapshot validated against the
        # registered panel allowlist, party included.
        normalized = validate_ui_snapshot(
            last, known_panels=set(self.registry.panel_names)
        )
        self.assertIn("party", normalized["panels"])
        self.assertEqual(normalized["panels"]["party"], last["panels"]["party"])
        sequence = [
            name
            for call in session.sent
            for name in ("ui_snapshot", "ui_action_result")
            if name in call
        ]
        self.assertLess(
            len(sequence) - 1 - sequence[::-1].index("ui_snapshot"),
            len(sequence) - 1 - sequence[::-1].index("ui_action_result"),
            "the post-leave snapshot must precede the action result",
        )

    def test_companion_deletion_pushes_party_update_to_live_watchers(self):
        companion = _companion("薇拉", self.room)
        join_party(companion, self.player)
        companion_id = int(companion.pk)
        session = ServerSession()
        session.init_session(
            "webclient/websocket", ("localhost", 9999), self.sessionhandler
        )
        session.sessid = 911
        # Mirror the test_watchers idiom: the mocked handler keeps an explicit
        # sessid mapping so the watcher registry's liveness check resolves it.
        self.sessionhandler[session.sessid] = session
        session.protocol_key = "webclient/websocket"
        session.puppet = self.player
        self.player.sessions.add(session)
        recorded = []
        session.msg = lambda **kwargs: recorded.append(kwargs)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        watchers.register_watcher(session)

        # The delete seam defers the fan-out through transaction.on_commit;
        # evennia's TestCase wraps the test in an outer transaction, so the
        # capture seam executes what the successful inner delete committed.
        with self.captureOnCommitCallbacks(execute=True):
            companion.delete()

        updates = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
        self.assertTrue(updates, "purge must push a party panel update")
        payload = updates[-1]["panels"]["party"]
        self.assertIs(payload["available"], True)
        self.assertNotIn(companion_id, [row["identity"] for row in payload["slots"]])
        self.assertEqual(payload["slots"], [])
        del self.sessionhandler[session.sessid]

    def test_deletion_without_watchers_is_a_silent_no_op(self):
        companion = _companion("孤身薇拉", self.room)
        join_party(companion, self.player)
        companion_id = int(companion.pk)
        with self.captureOnCommitCallbacks(execute=True):
            companion.delete()
        self.assertNotIn(companion_id, [int(dbid) for dbid in self.player.db.party or []])


class PartyCombatJoinTests(BattlefieldIsolation, EvenniaTest):
    """The join-by-identity contract and settlement push timing."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="队伍演武场")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, ["fire_ball"])
        self.companion = _companion("薇拉", self.room, hp_current=90, hp_maximum=90)
        join_party(self.companion, self.player)
        self.monster = _monster()
        self.monster.location = self.room
        self.action_registry = build_production_action_registry()
        self.registry = build_production_registry()

    def test_combat_partial_publishers_name_the_party_panel(self):
        for action_id in ("combat.cast", "combat.flee", "combat.forfeit"):
            with self.subTest(action_id):
                spec = self.action_registry.spec(action_id)
                self.assertIn("party", spec.affected_panels)

    def test_settlement_round_publishes_fresh_companion_hp(self):
        from unittest.mock import patch

        engage(self.player, self.monster)
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: _CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        priming = coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        priming_hp = next(
            row["hp_current"]
            for row in priming["panels"]["party"]["slots"]
            if row["identity"] == int(self.companion.pk)
        )
        self.assertEqual(priming_hp, 90)
        # Deterministic wound between commits: the round must not simply
        # re-render the same number, the pushed row has to visibly move off
        # the priming snapshot and track the post-settlement stored gauge.
        self.companion.traits.hp.current = 45
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "r1",
            "base_revision": coordinator.revision,
            "action_id": "combat.cast",
            "payload": {"skill_key": "fire_ball", "target_ids": [int(self.monster.pk)]},
        }
        with patch("world.rules.combat.roll_d100", return_value=100):
            handle_ui_action(
                session, self.player, envelope, self.action_registry, self.registry
            )
        party_payloads = [
            call[name][0][0]["panels"]["party"]
            for call in session.sent
            for name in ("ui_update", "ui_snapshot")
            if name in call and "party" in call[name][0][0]["panels"]
        ]
        self.assertGreaterEqual(
            len(party_payloads), 2, "the cast must publish party with the round"
        )
        committed = next(
            row
            for row in party_payloads[-1]["slots"]
            if row["identity"] == int(self.companion.pk)
        )
        stored = stored_gauge_pair(self.companion, "hp")
        self.assertEqual((committed["hp_current"], committed["hp_maximum"]), stored)
        self.assertNotEqual(
            committed["hp_current"],
            priming_hp,
            "the settlement push must reflect the new wound, not the priming snapshot",
        )
        results = [
            call["ui_action_result"][0][0] for call in session.sent if "ui_action_result" in call
        ]
        self.assertEqual(results[-1]["outcome"], "success")

    def test_identity_join_recovers_the_session_token_from_the_combat_panel(self):
        import re

        engage(self.player, self.monster)
        context = PresentationContext(actor=self.player, protocol_version=1)
        party = self.registry.render("party", context)
        combat = self.registry.render("context_actions", context)
        participants = {
            row["identity"]: row["token"] for row in combat["participants"]
        }
        pattern = re.compile(r"^a\d+$")
        for row in party["slots"]:
            participant_token = participants[row["identity"]]
            self.assertRegex(participant_token, pattern)
        # The party payload itself names no token anywhere.
        self.assertNotIn("token", party)
        for slot in party["slots"]:
            self.assertNotIn("token", slot)


if __name__ == "__main__":
    unittest.main()
