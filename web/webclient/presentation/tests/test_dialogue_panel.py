"""Tests for the version-1 ``dialogue`` presentation panel (webclient-align-10).

Presenter shape (party-row host vocabulary, canonical bond-stage NAME or null,
table-order keyword choices, the recorded line), registered unavailable forms
(no session, corrupt-at-parse stored line, stale host dbid), read-only
rendering, the pure validator's drift rejections, the coordinator mode matrix
(creation > combat > dialogue-live > exploration), the live->clear committed
transitions through the wire, and the NPC-departure panel push seam.
``covers_requirement`` annotations for the two new ``webclient-dialogue-session``
IDs land at the change's archive/sync commit (the checker resolves IDs only
from ``openspec/specs/``).
"""

from copy import deepcopy
from types import SimpleNamespace
import unittest

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.exploration_actions import _engage_adapter
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation import watchers
from web.webclient.presentation.affordances import _scripted_keyword_descriptors
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.dialogue import (
    DIALOGUE_MAX_CHOICES,
    DIALOGUE_SCHEMA_VERSION,
    DialoguePanelError,
    dialogue_presenter,
    validate_dialogue,
)
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    validate_ui_snapshot,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.combat_session import engage, is_in_active_session
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    MAX_DIALOGUE_SESSION_LINE_CODE_POINTS,
    clear_dialogue_session,
    open_or_refresh_dialogue,
)
from world.rules.movement_settlement import settle_movement
from world.rules.npc_identity import npc_display_name
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.quests.catalog import register_catalog

UNAVAILABLE_PAYLOAD = {
    "schema_version": DIALOGUE_SCHEMA_VERSION,
    "available": False,
    "reason": {"code": "dialogue_unavailable", "message": "對話目前無法顯示"},
}

CALENDAR = SimpleNamespace(
    year=1,
    season_index=0,
    season_name="春季",
    day_in_season=3,
    hour=12,
    minute=0,
    second=0,
)


def _player(key="對話面板測試者"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _host(room, key="公會職員"):
    npc = create_object(NPC, key=key, location=room)
    npc.components.add(
        ScriptedDialogue.create(npc, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
    )
    return npc


class _RecordingSession:
    """Minimal session stand-in that records every transport send."""

    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = 931

    def msg(self, **kwargs):
        self.sent.append(kwargs)


def _choice(keyword):
    return {"keyword_id": keyword, "label": keyword}


def _available(**overrides):
    payload = {
        "schema_version": DIALOGUE_SCHEMA_VERSION,
        "available": True,
        "kind": "dialogue",
        "host": {
            "identity": 41,
            "display_name": "公會職員",
            "portrait_ref": None,
        },
        "bond_stage": "熟人",
        "line": "歡迎來到冒險者公會。",
        "choices": [_choice("公會"), _choice("任務")],
    }
    payload.update(overrides)
    return payload


class DialoguePresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        # The bond-stage reader resolves affinity cap-break quests.
        register_catalog()
        self.room = create_object(Room, key="公會大廳")
        self.away = create_object(Room, key="別處", location=None)
        self.player = _player()
        self.player.location = self.room
        self.host = _host(self.room)
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def _render(self):
        return self.registry.render("dialogue", self.context)

    def test_available_form_is_exact_vocabulary_for_a_bonded_host(self):
        apply_affinity_change(
            self.host, self.player, AffinitySource.QUEST_COMPLETION, 47
        )
        affinity_value = self.host.relations.affinity_for(self.player)
        open_or_refresh_dialogue(self.player, self.host, "任務板在右側。")

        payload = self._render()
        self.assertEqual(
            set(payload),
            {"schema_version", "available", "kind", "host", "bond_stage", "line", "choices"},
        )
        self.assertEqual(payload["schema_version"], DIALOGUE_SCHEMA_VERSION)
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["kind"], "dialogue")
        self.assertEqual(
            payload["host"],
            {
                "identity": int(self.host.pk),
                "display_name": npc_display_name(self.host),
                "portrait_ref": None,
            },
        )
        self.assertEqual(payload["bond_stage"], self.host.relations.stage_for(self.player).name)
        self.assertEqual(payload["line"], "任務板在右側。")
        # Same vocabulary owner as the interact target descriptor, table order.
        self.assertEqual(payload["choices"], _scripted_keyword_descriptors(self.host))
        self.assertTrue(payload["choices"])
        # The raw affinity number never rides the wire.
        self.assertNotIn(affinity_value, payload.values())

    def test_unbonded_host_discloses_a_null_stage(self):
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        payload = self._render()
        self.assertIsNone(payload["bond_stage"])
        self.assertIs(payload["available"], True)

    def test_no_session_renders_the_registered_unavailable_form(self):
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_corrupt_stored_line_degrades_unavailable_not_internal(self):
        for corrupt_line in (
            "言" * (MAX_DIALOGUE_SESSION_LINE_CODE_POINTS + 1),
            "\ud800坏掉的行",
        ):
            with self.subTest(line=repr(corrupt_line[:16])):
                self.player.db.dialogue_session = {
                    "npc_id": int(self.host.pk),
                    "line": corrupt_line,
                    "updated_tick": None,
                }
                self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_stale_host_never_reaches_the_wire(self):
        # A dbid that never resolves: not live -> registered unavailable.
        self.player.db.dialogue_session = {
            "npc_id": 9_999_999,
            "line": "幽靈台詞。",
            "updated_tick": None,
        }
        payload = self._render()
        self.assertEqual(payload, UNAVAILABLE_PAYLOAD)
        self.assertNotIn("9999999", str(payload))
        # A present host outside the location is likewise not live; the host
        # waits in another room so the departure hook never pre-clears it.
        parked = _host(self.away, "停放的職員")
        self.player.db.dialogue_session = {
            "npc_id": int(parked.pk),
            "line": "遠方台詞。",
            "updated_tick": None,
        }
        self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)

    def test_presenter_is_read_only(self):
        apply_affinity_change(
            self.host, self.player, AffinitySource.QUEST_COMPLETION, 47
        )
        open_or_refresh_dialogue(self.player, self.host, "第一句。")
        stored_before = deepcopy(self.player.db.dialogue_session)
        affinity_before = self.host.relations.affinity_for(self.player)

        first = self._render()
        second = self._render()
        self.assertEqual(first, second)
        self.assertEqual(self.player.db.dialogue_session, stored_before)
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)

    def test_refresh_updates_the_line_in_place(self):
        open_or_refresh_dialogue(self.player, self.host, "第一句。")
        first = self._render()
        open_or_refresh_dialogue(self.player, self.host, "第二句。")
        second = self._render()
        self.assertIs(second["available"], True)
        self.assertEqual(second["line"], "第二句。")
        self.assertEqual(second["host"], first["host"])
        self.assertEqual(second["choices"], first["choices"])

    def test_panel_is_registered_in_the_production_registry(self):
        self.assertIn("dialogue", self.registry.panel_names)

    def test_host_with_an_empty_table_ships_empty_choices(self):
        plain = create_object(NPC, key="無表NPC", location=self.room)
        open_or_refresh_dialogue(self.player, plain, "嗯。")
        payload = self._render()
        self.assertIs(payload["available"], True)
        self.assertEqual(payload["choices"], [])

    def test_creation_pending_puppet_never_sees_the_available_form(self):
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        self.player.creation_pending = True
        try:
            self.assertEqual(self._render(), UNAVAILABLE_PAYLOAD)
        finally:
            self.player.creation_pending = False


class DialogueValidatorTests(unittest.TestCase):
    def test_available_form_validates(self):
        self.assertEqual(validate_dialogue(_available()), _available())
        self.assertEqual(
            validate_dialogue(_available(bond_stage=None))["bond_stage"], None
        )
        self.assertEqual(validate_dialogue(_available(choices=[]))["choices"], [])
        # Paired astral code points are legal text.
        self.assertEqual(validate_dialogue(_available(line="歡迎\U0001F600。"))["line"], "歡迎\U0001F600。")

    def test_drift_rejects(self):
        bad_payloads = [
            # unknown top-level field
            _available(extra=1),
            # missing top-level field
            {k: v for k, v in _available().items() if k != "choices"},
            # schema drift
            _available(schema_version=2),
            # the unavailable form is the registry's, not the validator's
            dict(UNAVAILABLE_PAYLOAD),
            _available(available=False),
            _available(kind="party"),
            # host vocabulary drift
            _available(host={"identity": 1, "display_name": "a", "portrait_ref": "42"}),
            _available(host={"identity": 0, "display_name": "a", "portrait_ref": None}),
            _available(host={"identity": 1, "display_name": " ", "portrait_ref": None}),
            {
                **_available(),
                "host": {
                    "identity": 1,
                    "display_name": "同" * 129,
                    "portrait_ref": None,
                },
            },
            # numeric bond_stage (raw affinity can never reach the wire)
            _available(bond_stage=3),
            _available(bond_stage=""),
            # line bounds and surrogate rejection (server parity with the mirror)
            _available(line=""),
            _available(line="言" * (MAX_DIALOGUE_SESSION_LINE_CODE_POINTS + 1)),
            _available(line="\ud800壞"),
            # choice cap (seventeenth row)
            _available(choices=[_choice(f"詞{i}") for i in range(DIALOGUE_MAX_CHOICES + 1)]),
            # duplicate keyword ids
            _available(choices=[_choice("公會"), _choice("公會")]),
            # empty keyword id
            _available(choices=[_choice(" ")]),
            # choice row key drift
            _available(choices=[{"keyword_id": "公會"}]),
            _available(choices=[{"keyword_id": "公會", "label": "公會", "extra": 1}]),
            # over-long label
            _available(choices=[{"keyword_id": "公會", "label": "說" * 129}]),
        ]
        for bad in bad_payloads:
            with self.subTest(payload=repr(sorted(bad))[:60]):
                with self.assertRaises(ProtocolValidationError):
                    validate_dialogue(bad)

    def test_error_is_a_protocol_validation_error(self):
        self.assertTrue(issubclass(DialoguePanelError, ProtocolValidationError))


class DialogueModeResolutionTests(BattlefieldIsolation, EvenniaTest):
    """The committed mode matrix: creation > combat > dialogue-live > exploration."""

    def setUp(self):
        super().setUp()
        self.player = _player("模式矩陣測試者")
        self.player.location = self.room1
        self.host = _host(self.room1, "職員")
        self.context = PresentationContext(actor=self.player, protocol_version=1)

    def _mode(self):
        return PresentationCoordinator.mode_for(self.context)

    def test_matrix(self):
        self.assertEqual(self._mode(), "exploration")
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        self.assertEqual(self._mode(), "dialogue")
        clear_dialogue_session(self.player)
        self.assertEqual(self._mode(), "exploration")
        self.player.creation_pending = True
        try:
            open_or_refresh_dialogue(self.player, self.host, "歡迎。")
            self.assertEqual(self._mode(), "creation")
        finally:
            self.player.creation_pending = False

    def test_combat_outranks_a_live_session(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        engage(self.player, monster)
        # A session object re-saved while combat is active (the cleanup seam
        # lost a race): the committed mode is still combat, never dialogue.
        open_or_refresh_dialogue(self.player, self.host, "殘留台詞。")
        self.assertTrue(is_in_active_session(self.player))
        self.assertEqual(self._mode(), "combat")

    def test_stale_session_never_resolves_dialogue_mode(self):
        self.player.db.dialogue_session = {
            "npc_id": 9_999_999,
            "line": "幽靈台詞。",
            "updated_tick": None,
        }
        self.assertEqual(self._mode(), "exploration")


class DialogueWireTransitionTests(BattlefieldIsolation, EvenniaTest):
    """The settled record reaches the wire and the clear returns the mode."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self):
        super().setUp()
        register_catalog()
        watchers.clear_watchers()
        self.player = _player("對話總線測試者")
        self.player.location = self.room1
        self.host = _host(self.room1, "職員")
        self.registry = build_production_registry()
        self.action_registry = build_production_action_registry()

    def tearDown(self):
        watchers.clear_watchers()
        super().tearDown()

    def _coordinator(self):
        session = _RecordingSession(self.player)
        coordinator = PresentationCoordinator(
            session, self.registry, calendar_provider=lambda: CALENDAR
        )
        session.ndb.elosern_coordinator = coordinator
        return session, coordinator

    def test_scripted_talk_commits_dialogue_mode_atomically(self):
        session, coordinator = self._coordinator()
        before = coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        self.assertEqual(before["mode"], "exploration")
        self.assertEqual(before["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)
        # validate against the registered allowlist — the panel name must be known
        validate_ui_snapshot(before, known_panels=set(self.registry.panel_names))

        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "d1",
            "base_revision": coordinator.revision,
            "action_id": "explore.talk_scripted",
            "payload": {"npc_id": int(self.host.pk), "keyword_id": "公會"},
        }
        handle_ui_action(
            session, self.player, envelope, self.action_registry, self.registry
        )
        snapshots = [
            call["ui_snapshot"][0][0] for call in session.sent if "ui_snapshot" in call
        ]
        results = [
            call["ui_action_result"][0][0]
            for call in session.sent
            if "ui_action_result" in call
        ]
        self.assertEqual(results[-1]["outcome"], "success")
        committed = snapshots[-1]
        # The settled record precedes the existing snapshot publication: the
        # published panel already carries the authored reply.
        self.assertEqual(committed["mode"], "dialogue")
        self.assertIs(committed["panels"]["dialogue"]["available"], True)
        self.assertEqual(
            committed["panels"]["dialogue"]["line"],
            self.player.db.dialogue_session["line"],
        )
        self.assertIn("冒險者公會", committed["panels"]["dialogue"]["line"])
        self.assertEqual(
            committed["panels"]["dialogue"]["choices"],
            _scripted_keyword_descriptors(self.host),
        )
        # The exploration panel keeps shipping its ordinary available payload —
        # dialogue mode does not blank it (the talk's +1 affinity may flip
        # affordance availability, so payload equality is not the contract).
        self.assertIs(committed["panels"]["exploration"]["available"], True)
        self.assertEqual(
            set(committed["panels"]["exploration"]),
            set(before["panels"]["exploration"]),
        )
        validate_ui_snapshot(committed, known_panels=set(self.registry.panel_names))

    def test_movement_clear_returns_mode_and_degrades_the_panel(self):
        session, coordinator = self._coordinator()
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        opened = coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        self.assertEqual(opened["mode"], "dialogue")

        away = create_object(Room, key="廣場", location=None)
        settle_movement(
            self.player,
            self.room1,
            traverse=lambda: self.player.move_to(away) or True,
            destination=away,
        )
        self.assertIsNone(self.player.db.dialogue_session)
        cleared = coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        self.assertEqual(cleared["mode"], "exploration")
        self.assertEqual(cleared["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)
        latest = [
            call["ui_snapshot"][0][0] for call in session.sent if "ui_snapshot" in call
        ][-1]
        self.assertEqual(latest["mode"], "exploration")
        self.assertEqual(latest["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)

    def test_engage_update_carries_the_dialogue_panel_under_combat_mode(self):
        session, coordinator = self._coordinator()
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        coordinator.full_snapshot(PresentationContext(actor=self.player, protocol_version=1))
        monster = create_object(Monster, key="襲擊的哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "d2",
            "base_revision": coordinator.revision,
            "action_id": "explore.engage",
            "payload": {"monster_id": int(monster.pk)},
        }
        handle_ui_action(
            session, self.player, envelope, self.action_registry, self.registry
        )
        updates = [call["ui_update"][0][0] for call in session.sent if "ui_update" in call]
        self.assertTrue(updates, "engage must publish its affected-panel update")
        committed = updates[-1]
        self.assertEqual(committed["mode"], "combat")
        # The engage clear is reflected atomically: dialogue re-renders
        # unavailable inside the same update, never left stale-available.
        self.assertIn("dialogue", committed["panels"])
        self.assertEqual(committed["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)

    def test_engage_adapter_names_the_dialogue_panel(self):
        monster = create_object(Monster, key="測試哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            result["affected_panels"], ("status", "context_actions", "dialogue")
        )
        spec = self.action_registry.spec("explore.engage")
        self.assertEqual(spec.affected_panels, ("status", "context_actions", "dialogue"))

    def test_npc_departure_pushes_unavailable_dialogue_to_live_watchers(self):
        session, coordinator = self._coordinator()
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        coordinator.full_snapshot(PresentationContext(actor=self.player, protocol_version=1))
        real = ServerSession()
        real.init_session("webclient/websocket", ("localhost", 9999), self.sessionhandler)
        real.sessid = 941
        self.sessionhandler[real.sessid] = real
        real.protocol_key = "webclient/websocket"
        real.puppet = self.player
        self.player.sessions.add(real)
        recorded = []
        real.msg = lambda **kwargs: recorded.append(kwargs)
        live_coordinator = PresentationCoordinator(
            real, self.registry, calendar_provider=lambda: CALENDAR
        )
        real.ndb.elosern_coordinator = live_coordinator
        live_coordinator.full_snapshot(
            PresentationContext(actor=self.player, protocol_version=1)
        )
        watchers.register_watcher(real)

        away = create_object(Room, key="後巷", location=None)
        # The departure clear fans out through transaction.on_commit; the
        # capture seam executes what a committed move would deliver.
        with self.captureOnCommitCallbacks(execute=True):
            self.host.move_to(away)

        updates = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
        self.assertTrue(updates, "departure must push a dialogue panel update")
        self.assertIsNone(self.player.db.dialogue_session)
        self.assertEqual(updates[-1]["panels"]["dialogue"], UNAVAILABLE_PAYLOAD)
        # The update carries the recomputed mode atomically with the clear.
        self.assertEqual(updates[-1]["mode"], "exploration")
        del self.sessionhandler[real.sessid]

    def test_departure_without_watchers_is_a_silent_no_op(self):
        open_or_refresh_dialogue(self.player, self.host, "歡迎。")
        away = create_object(Room, key="後巷二", location=None)
        with self.captureOnCommitCallbacks(execute=True):
            self.host.move_to(away)
        self.assertIsNone(self.player.db.dialogue_session)


if __name__ == "__main__":
    unittest.main()
