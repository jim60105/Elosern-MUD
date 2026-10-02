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
from typeclasses.accounts import Account

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.presentation.art_push import (
    DISPATCH_UID,
    _art_subject_keys,
    _gallery_subject_keys,
    _panel_matches_subject,
    _roster_subject_keys,
    connect_art_push,
    on_asset_completed,
)
from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    attach_coordinator,
    read_world_clock_calendar,
)
from web.webclient.presentation.gallery_selection import GallerySelection
from web.webclient.presentation.registry import build_production_registry
from world.art.queue import ensure, settle
from world.art.signals import asset_completed
from world.art.store import ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.rules.tests._combat_session_helpers import open_synthetic_scope


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


class ArtPushPureGateTests(unittest.TestCase):
    """Pure-logic tests for subject extraction and panel gating rules."""

    def test_art_subject_keys_extraction(self):
        self.assertEqual(_art_subject_keys({}), set())
        self.assertEqual(_art_subject_keys({"scene": None}), set())
        self.assertEqual(_art_subject_keys({"scene": {"subject_key": ""}}), set())
        self.assertEqual(_art_subject_keys({"scene": {"subject_key": "scene:arena"}}), {"scene:arena"})
        catalog = {
            "char_1": {"subject_key": "portrait:character:alice"},
            "char_2": {"subject_key": ""},
            "char_3": None,
        }
        self.assertEqual(
            _art_subject_keys({"scene": {"subject_key": "scene:arena"}, "portrait_catalog": catalog}),
            {"scene:arena", "portrait:character:alice"},
        )

    def test_gallery_subject_keys_selected_only(self):
        self.assertEqual(_gallery_subject_keys({}), set())
        self.assertEqual(_gallery_subject_keys({"selected": None}), set())
        self.assertEqual(_gallery_subject_keys({"selected": ""}), set())
        self.assertEqual(
            _gallery_subject_keys({
                "selected": "portrait:character:hero",
                "subjects": [{"subject_key": "portrait:character:other"}],
            }),
            {"portrait:character:hero"},
        )

    def test_roster_subject_keys_all_rows(self):
        self.assertEqual(_roster_subject_keys({}), set())
        self.assertEqual(_roster_subject_keys({"characters": None}), set())
        payload = {
            "characters": [
                {"portrait": {"subject_key": "portrait:character:c1"}},
                {"portrait": None},
                {"portrait": {"subject_key": ""}},
                {"portrait": {"subject_key": "portrait:character:c2"}},
            ]
        }
        self.assertEqual(_roster_subject_keys(payload), {"portrait:character:c1", "portrait:character:c2"})

    def test_panel_matches_subject_availability_and_omission(self):
        unavail = {"available": False, "selected": "portrait:character:c1"}
        self.assertFalse(_panel_matches_subject("gallery", unavail, "portrait:character:c1"))
        avail_gallery = {"available": True, "selected": "portrait:character:c1"}
        self.assertTrue(_panel_matches_subject("gallery", avail_gallery, "portrait:character:c1"))
        self.assertFalse(_panel_matches_subject("gallery", avail_gallery, "portrait:character:c2"))
        self.assertFalse(_panel_matches_subject("unknown_panel", {"available": True}, "s1"))

    def test_session_context_sharing_and_isolation(self):
        from web.webclient.presentation.art_push import _push_for_subject
        from unittest.mock import MagicMock

        sess1 = FakeSession(SimpleNamespace(pk=1), sessid=101)
        sess2 = FakeSession(SimpleNamespace(pk=2), sessid=102)

        contexts_sess1 = []
        contexts_sess2 = []

        def fake_render1(name, ctx):
            contexts_sess1.append(ctx)
            if name == "art":
                return {"available": True, "scene": {"subject_key": "target"}}
            return {"available": False}

        def fake_render2(name, ctx):
            contexts_sess2.append(ctx)
            return {"available": False}

        reg1 = MagicMock()
        reg1.panel_names = {"art", "gallery", "roster"}
        reg1.render.side_effect = fake_render1
        coord1 = MagicMock()
        coord1.registry = reg1
        sess1.ndb.elosern_coordinator = coord1

        reg2 = MagicMock()
        reg2.panel_names = {"art", "gallery", "roster"}
        reg2.render.side_effect = fake_render2
        coord2 = MagicMock()
        coord2.registry = reg2
        sess2.ndb.elosern_coordinator = coord2

        _push_for_subject(sess1, sess1.actor, "target")
        _push_for_subject(sess2, sess2.actor, "target")

        self.assertEqual(len(contexts_sess1), 3)
        self.assertIs(contexts_sess1[0], contexts_sess1[1])
        self.assertIs(contexts_sess1[1], contexts_sess1[2])
        coord1.panel_update.assert_called_once()
        self.assertIs(coord1.panel_update.call_args[0][0], contexts_sess1[0])
        self.assertEqual(list(coord1.panel_update.call_args[0][1].keys()), ["art"])

        self.assertEqual(len(contexts_sess2), 3)
        self.assertIs(contexts_sess2[0], contexts_sess2[1])
        self.assertIsNot(contexts_sess1[0], contexts_sess2[0])
        coord2.panel_update.assert_not_called()


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

            _notify_completed_batch([ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar")])
        finally:
            asset_completed.disconnect(receiver)
        self.assertEqual(len(received), 1)
        # Django injects ``signal`` and ``sender``; the payload adds exactly
        # one project-local field.
        self.assertEqual(received[0]["subject_key"], "scene:t_synth_bazaar")
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

            _notify_completed_batch([ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar")])
        finally:
            asset_completed.disconnect(receiver)
        self.assertEqual(received_thread_names, [main_thread])


class ArtPushPresenterTests(EvenniaTestCase):
    def setUp(self):
        # Scene presentation re-validates the room's archetype against the
        # live registry: run the surface on the kit archetype rows.
        open_synthetic_scope(self, "archetypes")
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir(parents=True, exist_ok=True)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.registry = build_production_registry()
        self.room = create_object(Room, key="push arena")
        self.room.scene_archetype = "t_synth_bazaar"
        self.player = create_object(PlayerCharacter, key="push player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.age = 22
        self.player.apparent_age = 22
        self.player.location = self.room
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.subject = ArtSubject(ArtSubjectKind.SCENE, "t_synth_bazaar")
        self._scene_key = "scene:t_synth_bazaar"

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

        claimed = claim(10)
        target = self.root / "scene" / "t_synth_bazaar.png"
        target.write_bytes(b"asset")
        settle(
            self.subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity="scene/t_synth_bazaar.png",
            error=None,
        )

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_settled_gallery_job_refreshes_all_three_referencing_panels_together(self):
        from evennia.utils.create import create_account
        from world.art import gallery as gallery_api
        (self.root / f"gallery/character/{self.player.pk}").mkdir(parents=True, exist_ok=True)
        from world.art.queue import claim, settle_gallery_generated
        from world.art.service import request_gallery_image

        char_subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.player.pk))
        char_key = char_subject.full()

        # Account owns player
        account = create_account("test_acct_1", "t1@example.test", "testpassword", typeclass=Account)
        account.characters.add(self.player)
        self.player.account = account

        # Other character in the room carrying named portrait policy so art catalog references it
        other_char = create_object(PlayerCharacter, key="arena ally", location=self.room)
        other_char.age = 22
        other_char.apparent_age = 22
        other_char.db.portrait_policy = {"mode": "named", "stable_key": f"ally_{self.player.pk}"}
        other_key = ArtSubject(ArtSubjectKind.CHARACTER, f"ally_{self.player.pk}").full()
        # Session selects char_subject
        session = self._make_session()
        session.ndb.gallery_selection = GallerySelection(
            self.player.pk, session.ndb.elosern_coordinator.epoch, char_key
        )

        # Queue a gallery job
        image_id = request_gallery_image(other_char, fields=[], custom_prompt="")
        claimed = claim(10)
        job = next(j for j in claimed if j.db.gallery_image_id == image_id)

        # Settle the gallery job
        img_path = self.root / f"gallery/character/{other_key.split(':')[-1]}/{image_id}.png"
        img_path.parent.mkdir(parents=True, exist_ok=True)
        img_path.write_bytes(b"card")
        settle_gallery_generated(
            job.key,
            generation_token=job.db.generation_token,
            output_identity=f"gallery/character/{other_key.split(':')[-1]}/{image_id}.png",
            tmp_path=str(img_path),
            prompt={"positive": "ally", "negative": ""},
            seed=1,
            checkpoint="sd_v1-5",
        )

        with (
            patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]),
            patch("web.webclient.presentation.art_push.log_info") as info_mock,
        ):
            # Selected is also set to other_key so gallery matches, art catalog references it, and make account own other_char too so roster matches!
            account.characters.add(other_char)
            other_char.account = account
            session.ndb.gallery_selection = GallerySelection(
                self.player.pk, session.ndb.elosern_coordinator.epoch, other_key
            )
            on_asset_completed(subject_key=other_key)

        updates = [k["ui_update"][0][0] for k in session.sent if "ui_update" in k]
        self.assertEqual(len(updates), 1)
        panels = updates[0]["panels"]
        self.assertIn("gallery", panels)
        self.assertIn("art", panels)
        self.assertIn("roster", panels)
        self.assertEqual(panels["gallery"]["selected"], other_key)
        self.assertEqual(len(panels["gallery"]["cards"]), 1)
        ctx = info_mock.call_args.kwargs["context"]
        self.assertEqual(ctx["session"], session.sessid)
        self.assertEqual(set(ctx["panels"]), {"gallery", "art", "roster"})

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_selected_gallery_refreshes_without_art_or_roster_match(self):
        from world.art import gallery as gallery_api
        from world.art.queue import claim, settle_gallery_generated
        from world.art.service import request_gallery_image

        monster_sub = ArtSubject(ArtSubjectKind.MONSTER, "low")
        monster_key = monster_sub.full()
        (self.root / "gallery/monster/low").mkdir(parents=True, exist_ok=True)

        session = self._make_session()
        session.ndb.gallery_selection = GallerySelection(
            self.player.pk, session.ndb.elosern_coordinator.epoch, monster_key
        )

        image_id = request_gallery_image(monster_sub, fields=[], custom_prompt="")
        claimed = claim(10)
        job = next(j for j in claimed if j.db.gallery_image_id == image_id)
        img_path = self.root / f"gallery/monster/low/{image_id}.png"
        img_path.parent.mkdir(parents=True, exist_ok=True)
        img_path.write_bytes(b"monster")
        settle_gallery_generated(
            job.key,
            generation_token=job.db.generation_token,
            output_identity=f"gallery/monster/low/{image_id}.png",
            tmp_path=str(img_path),
            prompt={"positive": "m", "negative": ""},
            seed=1,
            checkpoint="sd_v1-5",
        )

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]):
            on_asset_completed(subject_key=monster_key)

        updates = [k["ui_update"][0][0] for k in session.sent if "ui_update" in k]
        self.assertEqual(len(updates), 1)
        panels = updates[0]["panels"]
        self.assertEqual(set(panels.keys()), {"gallery"})
        self.assertEqual(panels["gallery"]["selected"], monster_key)

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_off_room_roster_sibling_refreshes_without_art_or_gallery_match(self):
        from evennia.utils.create import create_account
        account = create_account("test_acct_2", "t2@example.test", "testpassword", typeclass=Account)
        sibling = create_object(PlayerCharacter, key="sibling character")
        sibling.race = "human"
        sibling.apply_race_baseline()
        sibling.age = 22
        sibling.apparent_age = 22
        sibling.db.portrait_policy = {"mode": "named", "stable_key": str(sibling.pk)}
        sibling_key = ArtSubject(ArtSubjectKind.CHARACTER, str(sibling.pk)).full()

        account.characters.add(self.player)
        account.characters.add(sibling)
        self.player.account = account
        sibling.account = account
        other_room = create_object(Room, key="distant room")
        sibling.location = other_room
        sibling_key = ArtSubject(ArtSubjectKind.CHARACTER, str(sibling.pk)).full()

        session = self._make_session()
        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]), patch("web.webclient.presentation.ingress.is_webclient", return_value=True):
            on_asset_completed(subject_key=sibling_key)

        updates = [k["ui_update"][0][0] for k in session.sent if "ui_update" in k]
        self.assertEqual(len(updates), 1)
        panels = updates[0]["panels"]
        self.assertEqual(set(panels.keys()), {"roster"})

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_unavailable_art_cannot_suppress_gallery_or_roster_match(self):
        from evennia.utils.create import create_account
        account = create_account("test_acct_3", "t3@example.test", "testpassword", typeclass=Account)
        account.characters.add(self.player)
        self.player.account = account
        char_key = ArtSubject(ArtSubjectKind.CHARACTER, str(self.player.pk)).full()
        session = self._make_session()
        # Patch art presenter in registry to return unavailable
        orig_render = session.ndb.elosern_coordinator.registry.render
        def fake_render(name, ctx):
            if name == "art" or (hasattr(name, "name") and name.name == "art"):
                return {"available": False, "reason": "test"}
            return orig_render(name, ctx)

        with (
            patch.object(session.ndb.elosern_coordinator.registry, "render", side_effect=fake_render),
            patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]),
        ):
            on_asset_completed(subject_key=char_key)

        updates = [k["ui_update"][0][0] for k in session.sent if "ui_update" in k]
        self.assertEqual(len(updates), 1)
        panels = updates[0]["panels"]
        self.assertNotIn("art", panels)
        self.assertIn("gallery", panels)
        self.assertIn("roster", panels)

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
        self.assertEqual(envelope["panels"]["art"]["scene"]["url"], "/art/scene/t_synth_bazaar.png")
        self.assertEqual(envelope["revision"], 1)
        self.assertNotIn("context_actions", envelope["panels"])

    def test_non_referencing_session_receives_nothing(self):
        # The session is showing a different scene archetype.
        other_room = create_object(Room, key="other room")
        other_room.scene_archetype = "t_synth_lodge"
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
        other_room.scene_archetype = "t_synth_lodge"
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
    def test_changed_selection_cannot_be_restored_by_late_completion(self):
        # Use registered monster tiers low and mid
        sub_a = ArtSubject(ArtSubjectKind.MONSTER, "low")
        sub_b = ArtSubject(ArtSubjectKind.MONSTER, "mid")
        session = self._make_session()
        # Select A then B
        from web.webclient.presentation.gallery_selection import select_gallery_subject, gallery_selection_snapshot
        res_a = select_gallery_subject(session, self.player, sub_a.full())
        self.assertEqual(res_a["outcome"], "success")
        res_b = select_gallery_subject(session, self.player, sub_b.full())
        self.assertEqual(res_b["outcome"], "success")
        self.assertEqual(gallery_selection_snapshot(session, self.player), sub_b.full())

        # A completes while B is selected
        session.sent.clear()
        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]):
            on_asset_completed(subject_key=sub_a.full())

        self.assertEqual(session.sent, [])

    @covers_requirement("webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update")
    def test_failed_gallery_settlement_removes_pending_row_truthfully(self):
        from world.art.queue import claim, settle_gallery_failed
        from world.art.service import request_gallery_image
        monster_sub = ArtSubject(ArtSubjectKind.MONSTER, "mid")
        monster_key = monster_sub.full()
        (self.root / "gallery/monster/mid").mkdir(parents=True, exist_ok=True)

        session = self._make_session()
        session.ndb.gallery_selection = GallerySelection(
            self.player.pk, session.ndb.elosern_coordinator.epoch, monster_key
        )

        image_id = request_gallery_image(monster_sub, fields=[], custom_prompt="")
        claimed = claim(10)
        job = next(j for j in claimed if j.db.gallery_image_id == image_id)

        # Settle as failed
        settle_gallery_failed(
            job.key,
            generation_token=job.db.generation_token,
            error="sd_unreachable",
        )

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]):
            on_asset_completed(subject_key=monster_key)

        updates = [k["ui_update"][0][0] for k in session.sent if "ui_update" in k]
        self.assertEqual(len(updates), 1)
        panels = updates[0]["panels"]
        self.assertIn("gallery", panels)
        cards = panels["gallery"]["cards"]
        # Should show error card/row, not a completed card
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["status"], "failed")
        self.assertIn("sd_unreachable", cards[0]["label"])

    def test_one_bad_session_logs_warning_with_subject_context(self):
        session = self._make_session()
        with (
            patch.object(session.ndb.elosern_coordinator.registry, "render", side_effect=RuntimeError("kaboom")),
            patch("evennia.SESSION_HANDLER.get_sessions", return_value=[session]),
            patch("web.webclient.presentation.art_push.log_warn") as warn_mock,
        ):
            on_asset_completed(subject_key=self._scene_key)
        warn_mock.assert_called_once()
        self.assertEqual(warn_mock.call_args.args, ("art_push_unavailable",))
        kw = warn_mock.call_args.kwargs
        self.assertIn("exc", kw)
        self.assertEqual(
            kw["context"],
            {"surface": "art", "session": session.sessid, "subject": self._scene_key},
        )

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
