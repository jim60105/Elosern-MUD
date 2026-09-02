"""Targeted OOB art completion push tests (task 4.3).

Covers the ``asset_completed`` signal boundary: the payload contains only the
subject key, the subscriber runs on the calling thread (never the worker
thread), a referencing session receives one newer ``art`` update, a
non-referencing or creation-mode session receives nothing, a late completion
for an old room replaces nothing, a bad session does not stop the others, and
``world/art/`` never imports ``web/``.
"""

from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.presentation.art_push import (
    DISPATCH_UID,
    connect_art_push,
    on_asset_completed,
)
from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    read_world_clock_calendar,
)
from web.webclient.presentation.registry import build_production_registry
from world.art.queue import ensure, settle
from world.art.signals import asset_completed
from world.art.store import ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind


class FakeSession:
    """A minimal live WebClient session carrying an attached coordinator."""

    def __init__(self, actor, *, sessid=1, protocol_key="websocket"):
        self.actor = actor
        self._sessid = sessid
        self.sent = []
        self.protocol_key = protocol_key
        self.ndb = SimpleNamespace(elosern_coordinator=None)

    @property
    def sessid(self):
        return self._sessid

    @property
    def puppet(self):
        return self.actor

    def msg(self, **kwargs):
        self.sent.append(kwargs)


def _context(actor):
    return SimpleNamespace(actor=actor)


class FakeCalendar:
    year = 1204
    season_index = 2
    season_name = "仲夏"
    day_in_season = 17
    hour = 14
    minute = 30
    second = 5


def _fake_calendar():
    return FakeCalendar()


class ArtPushBoundaryTests(EvenniaTestCase):
    """The subscriber stays decoupled from world/art/ and the worker thread."""

    def test_world_art_never_imports_web(self):
        import ast
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        art_root = root / "world" / "art"
        violations = []
        for path in sorted(art_root.rglob("*.py")):
            if "/tests/" in str(path):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("web"):
                    violations.append(f"{path}: {ast.unparse(node)}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("web"):
                            violations.append(f"{path}: {ast.unparse(node)}")
        self.assertEqual(violations, [])

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_signal_payload_contains_only_the_subject_key(self):
        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs)

        asset_completed.connect(receiver, weak=False)
        try:
            from world.art.subjects import ArtSubject, ArtSubjectKind
            from world.art.worker import _notify_completed_batch

            _notify_completed_batch([ArtSubject(ArtSubjectKind.SCENE, "forest_path")])
        finally:
            asset_completed.disconnect(receiver)
        self.assertEqual(len(received), 1)
        # Django injects ``signal`` and ``sender``; the payload adds exactly
        # one project-local field.
        self.assertEqual(received[0]["subject_key"], "scene:forest_path")
        self.assertEqual(set(received[0]) - {"signal", "sender"}, {"subject_key"})

    def test_dispatch_uid_makes_connection_reentrant(self):
        connect_art_push()
        connect_art_push()
        # Django's dispatch_uid deduplicates receivers: exactly one live
        # receiver for our subscriber remains registered. The lookup key is
        # ``(dispatch_uid, sender_id)``.
        matching = [
            entry
            for entry in asset_completed.receivers
            if entry[0][0] == DISPATCH_UID
        ]
        self.assertEqual(len(matching), 1)

    def test_subscriber_runs_on_the_calling_thread_not_the_worker_thread(self):
        received_thread_names = []
        main_thread = __import__("threading").get_ident()

        def receiver(sender, **kwargs):
            received_thread_names.append(__import__("threading").get_ident())

        asset_completed.connect(receiver, weak=False)
        try:
            from world.art.subjects import ArtSubject, ArtSubjectKind
            from world.art.worker import _notify_completed_batch

            _notify_completed_batch([ArtSubject(ArtSubjectKind.SCENE, "forest_path")])
        finally:
            asset_completed.disconnect(receiver)
        self.assertEqual(received_thread_names, [main_thread])


class ArtPushPresenterTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir(parents=True, exist_ok=True)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.registry = build_production_registry()
        self.room = create_object(Room, key="push arena")
        self.room.scene_archetype = "forest_path"
        self.player = create_object(PlayerCharacter, key="push player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.age = 22
        self.player.apparent_age = 22
        self.player.location = self.room
        self.subject = ArtSubject(ArtSubjectKind.SCENE, "forest_path")
        self._scene_key = "scene:forest_path"

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _make_session(self, actor=None, mode="exploration", sessid=1):
        session = FakeSession(actor or self.player, sessid=sessid)
        coordinator = PresentationCoordinator(
            session,
            self.registry,
            mode_provider=lambda ctx: mode,
            calendar_provider=_fake_calendar,
        )
        session.ndb.elosern_coordinator = coordinator
        return session

    def _complete_scene(self):
        ensure(self.subject, "desc")
        from world.art.queue import claim

        claim(10)
        target = self.root / "scene" / "forest_path.png"
        target.write_bytes(b"asset")
        settle(
            self.subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_referencing_session_receives_one_newer_art_update(self):
        session = self._make_session()
        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]):
            self._complete_scene()
            on_asset_completed(subject_key=self._scene_key)
        updates = [
            kwargs
            for kwargs in session.sent
            if "ui_update" in kwargs and "art" in kwargs["ui_update"][0][0]["panels"]
        ]
        self.assertEqual(len(updates), 1)
        envelope = updates[0]["ui_update"][0][0]
        self.assertEqual(envelope["panels"]["art"]["scene"]["status"], ArtAssetStatus.DONE)
        self.assertEqual(envelope["panels"]["art"]["scene"]["url"], "/art/scene/forest_path.png")
        self.assertEqual(envelope["revision"], 1)
        self.assertNotIn("context_actions", envelope["panels"])

    def test_non_referencing_session_receives_nothing(self):
        # The session is showing a different scene archetype.
        other_room = create_object(Room, key="other room")
        other_room.scene_archetype = "tavern_interior"
        other_player = create_object(PlayerCharacter, key="other player")
        other_player.race = "human"
        other_player.apply_race_baseline()
        other_player.location = other_room
        session = self._make_session(other_player)
        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]):
            self._complete_scene()
            on_asset_completed(subject_key=self._scene_key)
        self.assertEqual(session.sent, [])

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_creation_mode_session_receives_nothing(self):
        pending = create_object(PlayerCharacter, key="pending shell")
        pending.creation_pending = True
        session = self._make_session(pending, mode="creation")
        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]):
            self._complete_scene()
            on_asset_completed(subject_key=self._scene_key)
        self.assertEqual(session.sent, [])

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_late_completion_for_an_old_room_replaces_nothing(self):
        session = self._make_session()
        # The actor has since moved to a room with a different archetype.
        other_room = create_object(Room, key="moved room")
        other_room.scene_archetype = "tavern_interior"
        self.player.location = other_room
        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]):
            self._complete_scene()
            on_asset_completed(subject_key=self._scene_key)
        self.assertEqual(session.sent, [])

    def test_one_bad_session_does_not_stop_the_others(self):
        good = self._make_session(sessid=1)

        class BadSession(FakeSession):
            @property
            def puppet(self):
                raise RuntimeError("boom")

        bad = BadSession(self.player, sessid=2)
        with (
            patch("evennia.SESSION_HANDLER.get_sessions", return_value=[bad, good]),
            patch("web.webclient.presentation.art_push.log_warn") as log_warn,
        ):
            self._complete_scene()
            on_asset_completed(subject_key=self._scene_key)
        log_warn.assert_called()
        updates = [
            kwargs
            for kwargs in good.sent
            if "ui_update" in kwargs and "art" in kwargs["ui_update"][0][0]["panels"]
        ]
        self.assertEqual(len(updates), 1)

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_reconnect_resolves_current_status_from_the_store(self):
        # A missed push is repaired by the full snapshot: once the record is
        # done, a fresh coordinator renders the done status without replaying.
        self._complete_scene()
        session = FakeSession(self.player)
        session.ndb.elosern_coordinator = PresentationCoordinator(
            session,
            self.registry,
            calendar_provider=_fake_calendar,
        )
        from web.webclient.presentation.context import PresentationContext

        context = PresentationContext(actor=self.player, protocol_version=1)
        session.ndb.elosern_coordinator.full_snapshot(context)
        snapshots = [
            kwargs["ui_snapshot"][0][0]
            for kwargs in session.sent
            if "ui_snapshot" in kwargs
        ]
        self.assertEqual(len(snapshots), 1)
        art = snapshots[0]["panels"]["art"]
        self.assertEqual(art["scene"]["status"], ArtAssetStatus.DONE)


if __name__ == "__main__":
    unittest.main()
