"""Exact ``art`` schema, presenter, and surface-isolation tests (tasks 2.3, 7.1).

Covers the version-1 payload validation, scene done/missing/pending/failed/
scheduler-disabled/missing-file states, same-origin URL only, combat catalog
mirroring ``context_actions`` participants, exploration present-entity catalog
contents, gate-rejected entries as unavailable placeholders with no URL,
creation-mode unavailable form, presenter isolation, and the worst-case
serialization size.
"""

from pathlib import Path
import tempfile
import unittest

from tools.spec_traceability import covers_requirement

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation.art import (
    ART_SCHEMA_VERSION,
    ArtPanelError,
    validate_art,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.art.queue import claim, ensure, record_key, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.onboarding.guide_dialogue import GUILD_STAFF_DIALOGUE_KEY
from world.rules.combat_session import engage
from world.rules.tests.combat_fixtures import BattlefieldIsolation


def _valid_scene(**overrides):
    value = {
        "archetype": "tavern_interior",
        "label": "酒館內部",
        "subject_key": "scene:tavern_interior",
        "status": "done",
        "url": "/art/scene/tavern_interior.png",
        "aspect_ratio": "16:9",
        "alt": "酒館內部",
        "placeholder": None,
    }
    value.update(overrides)
    return value


def _valid_catalog_entry(**overrides):
    value = {
        "subject_key": "portrait:monster:low",
        "status": "done",
        "url": "/art/portrait/monster/low.png",
        "aspect_ratio": "3:4",
        "alt": "低階魔物",
        "placeholder": None,
        "context": {"name": "哥布林", "role": "敵方"},
    }
    value.update(overrides)
    return value


def _valid_payload(**overrides):
    value = {
        "schema_version": ART_SCHEMA_VERSION,
        "available": True,
        "kind": "scene",
        "scene": _valid_scene(),
        "portrait_catalog": {"42": _valid_catalog_entry()},
    }
    value.update(overrides)
    return value


class ArtSchemaTests(unittest.TestCase):
    def test_minimal_available_payload_passes(self):
        normalized = validate_art(_valid_payload())
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["schema_version"], ART_SCHEMA_VERSION)
        self.assertEqual(normalized["kind"], "scene")

    def test_unknown_or_missing_fields_reject(self):
        payload = _valid_payload(bogus=1)
        with self.assertRaises(Exception):
            validate_art(payload)
        payload = _valid_payload()
        del payload["portrait_catalog"]
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_wrong_version_kind_availability_reject(self):
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(schema_version=2))
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(available=False))
        with self.assertRaises(ArtPanelError):
            validate_art(_valid_payload(kind="combat"))

    def test_scene_url_must_be_same_origin(self):
        payload = _valid_payload(scene=_valid_scene(url="https://evil.test/x.png"))
        with self.assertRaises(Exception):
            validate_art(payload)
        payload = _valid_payload(scene=_valid_scene(url="/tmp/out.png"))
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_scene_placeholder_truthfulness(self):
        # A pending scene needs a placeholder; a done scene must not carry one.
        payload = _valid_payload(
            scene=_valid_scene(status="pending", url=None, placeholder=None)
        )
        with self.assertRaises(Exception):
            validate_art(payload)
        payload = _valid_payload(
            scene=_valid_scene(placeholder={"kind": "missing", "label": "未生成"})
        )
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_catalog_keys_must_be_decimal_strings(self):
        payload = _valid_payload(portrait_catalog={"abc": _valid_catalog_entry()})
        with self.assertRaises(Exception):
            validate_art(payload)
        payload = _valid_payload(portrait_catalog={42: _valid_catalog_entry()})
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_catalog_context_role_is_stable(self):
        payload = _valid_payload(
            portrait_catalog={
                "42": _valid_catalog_entry(context={"name": "x", "role": "boss"})
            }
        )
        with self.assertRaises(Exception):
            validate_art(payload)

    def test_catalog_ceiling_and_byte_gate(self):
        entries = {
            str(index): _valid_catalog_entry() for index in range(1, 33)
        }
        payload = _valid_payload(portrait_catalog=entries)
        normalized = validate_art(payload)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)
        entries = {str(index): _valid_catalog_entry() for index in range(1, 34)}
        with self.assertRaises(Exception):
            validate_art(_valid_payload(portrait_catalog=entries))

    def test_worst_case_realistic_payload_fits_the_envelope(self):
        entries = {
            str(index): _valid_catalog_entry(
                subject_key=f"portrait:character:{index}",
                alt="長替代文字" * 20,
            )
            for index in range(1, 33)
        }
        payload = _valid_payload(portrait_catalog=entries)
        normalized = validate_art(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)
        self.assertLess(size, 48 * 1024)


def _player(key="art player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.age = 22
    player.apparent_age = 22
    return player


def _monster(key="art goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class ArtPresenterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir(parents=True, exist_ok=True)
        (self.root / "portrait" / "character").mkdir(parents=True, exist_ok=True)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.room = create_object(Room, key="art arena")
        self.room.scene_archetype = "tavern_interior"
        self.player = _player()
        self.player.location = self.room
        self.registry = build_production_registry()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _context(self):
        return PresentationContext(actor=self.player, protocol_version=1)

    def _render(self):
        return self.registry.render("art", self._context())

    def _write_asset(self, identity):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")

    def _settle_done(self, subject, identity):
        ensure(subject, "desc")
        self._write_asset(identity)
        from world.art.queue import claim

        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
        )

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_done_scene_renders_same_origin_url(self):
        self._settle_done(
            ArtSubject(ArtSubjectKind.SCENE, "tavern_interior"),
            "scene/tavern_interior.png",
        )
        payload = self._render()
        self.assertTrue(payload["available"])
        scene = payload["scene"]
        self.assertEqual(scene["archetype"], "tavern_interior")
        self.assertEqual(scene["label"], "酒館內部")
        self.assertEqual(scene["subject_key"], "scene:tavern_interior")
        self.assertEqual(scene["status"], ArtAssetStatus.DONE)
        self.assertEqual(scene["url"], "/art/scene/tavern_interior.png")
        self.assertEqual(scene["aspect_ratio"], "16:9")
        self.assertIsNone(scene["placeholder"])
        self.assertNotIn("out_path", repr(payload))
        self.assertNotIn(self.root.as_posix(), repr(payload))

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_pending_missing_failed_states_render_placeholders(self):
        from world.art.queue import claim

        pending = ArtSubject(ArtSubjectKind.SCENE, "tavern_interior")
        ensure(pending, "desc")
        claim(10)
        pending_record = __import__("world.art.queue", fromlist=["record_key"]).record_key(
            pending
        )
        record = __import__(
            "world.art.store", fromlist=["ArtAssetRecord"]
        ).ArtAssetRecord.objects.filter(db_key=pending_record).first()
        record.db.status = ArtAssetStatus.PENDING
        record.save()
        payload = self._render()
        scene = payload["scene"]
        self.assertEqual(scene["status"], ArtAssetStatus.PENDING)
        self.assertIsNone(scene["url"])
        self.assertEqual(scene["placeholder"]["kind"], "missing")

        failed = ArtSubject(ArtSubjectKind.SCENE, "tavern_interior")
        ensure(failed, "desc")
        claim(10)
        settle(
            failed,
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="boom",
        )
        payload = self._render()
        self.assertEqual(payload["scene"]["status"], ArtAssetStatus.FAILED)
        self.assertIsNone(payload["scene"]["url"])

    @covers_requirement("webclient-art-panel::the-art-panel-accepts-the-normalized-in-flight-state")
    @covers_requirement("art-queue-worker::in-flight-generation-exposes-a-wire-stable-status")
    def test_claimed_record_renders_available_with_a_pending_placeholder(self):
        subject = ArtSubject(ArtSubjectKind.SCENE, "tavern_interior")
        ensure(subject, "desc")
        claim(10)
        payload = self._render()
        self.assertTrue(payload["available"])
        scene = payload["scene"]
        self.assertEqual(scene["subject_key"], "scene:tavern_interior")
        self.assertEqual(scene["status"], "pending")
        self.assertIsNone(scene["url"])
        self.assertEqual(scene["placeholder"]["kind"], "missing")
        self.assertEqual(scene["aspect_ratio"], "16:9")
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)

    def test_unresolvable_scene_archetype_renders_unavailable(self):
        self.room.scene_archetype = None
        payload = self._render()
        scene = payload["scene"]
        self.assertIsNone(scene["archetype"])
        self.assertEqual(scene["placeholder"]["kind"], "unavailable")
        self.assertIsNone(scene["url"])
        self.assertIsNone(scene["subject_key"])

    def test_missing_file_for_done_record_renders_unavailable(self):
        ensure(ArtSubject(ArtSubjectKind.SCENE, "tavern_interior"), "desc")
        from world.art.queue import claim

        claim(10)
        settle(
            ArtSubject(ArtSubjectKind.SCENE, "tavern_interior"),
            status=ArtAssetStatus.DONE,
            output_identity="scene/tavern_interior.png",
            error=None,
        )
        # The file is never written, so the presenter treats it as unavailable.
        payload = self._render()
        self.assertEqual(payload["scene"]["placeholder"]["kind"], "unavailable")
        self.assertIsNone(payload["scene"]["url"])

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-adult-gated-and-bounded")
    def test_combat_catalog_mirrors_context_actions_participants(self):
        monster = _monster()
        monster.location = self.room
        engage(self.player, monster)
        combat = self.registry.render(
            "context_actions", self._context()
        )
        payload = self._render()
        self.assertEqual(
            set(payload["portrait_catalog"]),
            {str(p["identity"]) for p in combat["participants"]},
        )
        for identity, entry in payload["portrait_catalog"].items():
            participant = next(
                p for p in combat["participants"] if str(p["identity"]) == identity
            )
            self.assertEqual(entry["context"]["name"], participant["display_name"])
            self.assertIn(entry["context"]["role"], ("隊友", "敵方"))
        monster_entry = payload["portrait_catalog"][str(monster.pk)]
        self.assertEqual(monster_entry["subject_key"], "portrait:monster:low")

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-adult-gated-and-bounded")
    def test_exploration_catalog_contains_hosts_and_named_policy(self):
        host = create_object(NPC, key="innkeeper", location=self.room)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        named = create_object(PlayerCharacter, key="named-guest")
        named.race = "human"
        named.apply_race_baseline()
        named.age = 30
        named.apparent_age = 30
        named.db.portrait_policy = {"mode": "named", "stable_key": "named-guest"}
        named.location = self.room
        monster = _monster(key="lurking-wolf")
        monster.location = self.room
        payload = self._render()
        catalog = payload["portrait_catalog"]
        self.assertIn(str(host.pk), catalog)
        self.assertIn(str(named.pk), catalog)
        self.assertNotIn(str(monster.pk), catalog)
        self.assertEqual(catalog[str(host.pk)]["context"]["role"], "對話對象")
        self.assertEqual(catalog[str(named.pk)]["context"]["role"], "人物")

    @covers_requirement("webclient-art-panel::the-portrait-catalog-is-server-authored-adult-gated-and-bounded")
    def test_underage_character_renders_placeholder_without_url(self):
        underage = _player(key="young guest")
        underage.location = self.room
        underage.db.portrait_policy = {"mode": "named", "stable_key": "young-guest"}
        underage.age = 17
        payload = self._render()
        entry = payload["portrait_catalog"][str(underage.pk)]
        self.assertEqual(entry["placeholder"]["kind"], "unavailable")
        self.assertIsNone(entry["subject_key"])
        self.assertIsNone(entry["url"])
        self.assertNotIn("underage", repr(payload))
        self.assertNotIn("17", repr(payload))

    def test_creation_mode_renders_unavailable_form(self):
        self.player.db.creation_pending = True
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("scene", payload)
        self.assertNotIn("portrait_catalog", payload)

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_presenter_is_read_only(self):
        self._settle_done(
            ArtSubject(ArtSubjectKind.SCENE, "tavern_interior"),
            "scene/tavern_interior.png",
        )
        before = {
            "hp": self.player.traits.hp.current,
            "active_combat": self.player.db.active_combat,
        }
        self._render()
        after = {
            "hp": self.player.traits.hp.current,
            "active_combat": self.player.db.active_combat,
        }
        self.assertEqual(before, after)

    def test_presenter_isolation_on_view_error(self):
        long_named = create_object(NPC, key="長" * 200, location=self.room)
        long_named.components.add(
            ScriptedDialogue.create(long_named, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "art_unavailable")


class ArtSnapshotIntegrationTests(BattlefieldIsolation, EvenniaTest):
    """Full-snapshot and combat-result atomicity integration (task 7.1)."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        import evennia
        from server.conf.tests.test_inputfuncs import _make_session

        self.sessionhandler = evennia.SESSION_HANDLER
        self.ws_session = _make_session(self.sessionhandler, "webclient/websocket")
        self.ws_session.puppet = self.char1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.age = 22
        self.char1.apparent_age = 22
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.sessionhandler.data_out.reset_mock()

    def tearDown(self):
        self.sessionhandler.data_out.reset_mock()
        super().tearDown()

    def _sync(self):
        from server.conf import inputfuncs

        self.sessionhandler.data_out.reset_mock()
        inputfuncs.ui_sync(self.ws_session, {"protocol_version": 1})
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        envelope = calls[-1].kwargs["ui_snapshot"][0][0]
        return envelope

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_full_snapshot_includes_art_in_exploration_and_combat_modes(self):
        room = create_object(Room, key="snapshot arena")
        room.scene_archetype = "tavern_interior"
        self.char1.location = room
        envelope = self._sync()
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["available"], True)
        self.assertEqual(envelope["panels"]["art"]["kind"], "scene")

        monster = _monster()
        monster.location = room
        engage(self.char1, monster)
        envelope = self._sync()
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["available"], True)
        self.assertIn(str(monster.pk), envelope["panels"]["art"]["portrait_catalog"])

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_full_snapshot_in_creation_mode_uses_the_unavailable_form(self):
        self.char1.db.creation_pending = True
        envelope = self._sync()
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["available"], False)
        self.assertNotIn("scene", envelope["panels"]["art"])

    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    def test_combat_result_publishes_status_context_actions_and_art_together(self):
        from unittest.mock import patch

        from server.conf import inputfuncs
        from web.webclient.actions.registry import build_production_action_registry
        from web.webclient.actions.dispatcher import handle_ui_action
        from web.webclient.presentation.registry import build_production_registry

        room = create_object(Room, key="atomic arena")
        room.scene_archetype = "forest_path"
        self.char1.location = room
        monster = _monster()
        monster.location = room
        engage(self.char1, monster)
        envelope = self._sync()
        coordinator = __import__(
            "web.webclient.presentation.coordinator", fromlist=["attach_coordinator"]
        ).attach_coordinator(self.ws_session, build_production_registry())
        action = {
            "protocol_version": 1,
            "presentation_epoch": envelope["presentation_epoch"],
            "request_id": "combat:1",
            "base_revision": envelope["revision"],
            "action_id": "combat.flee",
            "payload": {},
        }
        self.sessionhandler.data_out.reset_mock()
        with patch("world.rules.disengage.roll_d100", return_value=100):
            handle_ui_action(
                self.ws_session,
                self.char1,
                action,
                build_production_action_registry(),
                build_production_registry(),
            )
        # A terminal outcome (flee) publishes a full snapshot: the mode flips
        # back to exploration, so every mode-relevant panel is replaced,
        # including the art catalog without the fled monster.
        snapshots = [
            call.kwargs["ui_snapshot"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(snapshots, "a terminal combat action must publish a full snapshot")
        panels = snapshots[-1]["panels"]
        for name in ("status", "context_actions", "art", "exploration", "character", "services", "local_map"):
            self.assertIn(name, panels)
        # The fled participant leaves the art catalog in the same publication.
        catalog = panels["art"]["portrait_catalog"]
        self.assertNotIn(str(monster.pk), catalog)
        self.assertNotIn(str(self.char1.pk), catalog)
        updates = [
            call.kwargs["ui_update"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_update" in call.kwargs
        ]
        self.assertFalse(updates, "a terminal outcome must not publish a partial update")

    @covers_requirement("webclient-art-panel::the-art-panel-is-an-exact-read-only-panel-available-in-exploration-and-combat-modes")
    def test_text_command_refresh_snapshot_includes_the_art_panel(self):
        from server.conf import inputfuncs

        room = create_object(Room, key="refresh arena")
        room.scene_archetype = "tavern_interior"
        self.char1.location = room
        deferred = __import__("twisted.internet.defer", fromlist=["Deferred"]).Deferred()
        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "server.conf.inputfuncs.cmdhandler", return_value=deferred
        ):
            inputfuncs.text(self.ws_session, "look")
            deferred.callback(None)
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(calls, "no refresh snapshot was emitted")
        envelope = calls[-1].kwargs["ui_snapshot"][0][0]
        self.assertIn("art", envelope["panels"])
        self.assertEqual(envelope["panels"]["art"]["kind"], "scene")
        self.assertEqual(envelope["panels"]["art"]["scene"]["archetype"], "tavern_interior")


if __name__ == "__main__":
    unittest.main()
