"""Creation panel v8 ``portrait`` state reconstruction (creation-draft-portrait-panel).

Every state is reached through the real request owner and the real worker on
the synthetic kit with an injected fake image client and a temporary art
store; the service verdict is driven through the real connectivity cache with
a patched clock or configuration, never wall-clock time. The assertions are
about the rendered panel and the absence of presenter writes.
"""

import copy
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.creation import validate_creation
from web.webclient.presentation.registry import build_production_registry
from world.art import connectivity
from world.art import gallery as gallery_api
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.sd_worker import SDError
from world.art.store import GalleryJobRecord
from world.art.subjects import named_character_subject
from world.art.worker import drain_synchronous
from world.rules.creation_messages import CREATION_REASON_MESSAGES
from world.rules.creation_portrait import (
    DraftPortraitRequest,
    read_draft_portrait,
    receipt_owns_image,
    request_draft_portrait,
)
from world.tests.start_room_fixture import stub_start_room

from ._support import _T_RACE, _T_SUBRACE, _open_t_creation_scope, _shipped_race_affinity


def _plain(value):
    """A detached plain copy of one stored attribute value."""
    if hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    return copy.deepcopy(value)


class _PortraitPanelCase(EvenniaTestCase):
    """A pending shell, the kit creation scope, a temporary art store."""

    def setUp(self):
        self.enterContext(stub_start_room())
        _open_t_creation_scope(self)
        handle = patch(
            "web.webclient.presentation.creation._validate_affinity",
            _shipped_race_affinity,
        )
        handle.start()
        self.addCleanup(handle.stop)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        settings.enable()
        self.addCleanup(settings.disable)
        connectivity._reset_for_testing()
        self.addCleanup(connectivity._reset_for_testing)
        super().setUp()
        self.registry = build_production_registry()
        self.client = FakeSDWebUIClient()
        self.account, self.character = self._pending("portrait-owner")

    def _pending(self, name):
        account = create_account(
            name, f"{name}@example.test", "testpassword", typeclass=Account
        )
        character = create_object(PlayerCharacter, key=f"{name}-shell")
        account.at_post_create_character(character)
        return account, character

    # -- harness ----------------------------------------------------------
    def admit(self, account=None, character=None):
        with patch("world.art.connectivity.resolve_sd_client", return_value=self.client):
            return request_draft_portrait(
                account or self.account,
                character or self.character,
                DraftPortraitRequest(
                    race=_T_RACE, subrace=_T_SUBRACE, sex="female", apparent_age=26
                ),
            )

    def drain(self, client=None):
        with patch("world.art.worker.resolve_sd_client", return_value=client or self.client):
            drain_synchronous(10)

    def failing_client(self):
        client = FakeSDWebUIClient()
        client.fail_every_call(SDError("sd_generation_error", "scripted failure"))
        return client

    def cache_failed_verdict(self):
        """Record a CURRENT failed verdict through the real request-path probe."""
        client = FakeSDWebUIClient()
        client.fail_probe()
        with patch("world.art.connectivity.resolve_sd_client", return_value=client):
            connectivity.probe(force=True)

    def render(self, character=None):
        """Render through the production registry with probes forbidden."""
        context = PresentationContext(actor=character or self.character, protocol_version=1)
        with patch(
            "world.art.connectivity.probe",
            side_effect=AssertionError("presentation must never probe"),
        ), patch(
            "world.art.connectivity.resolve_sd_client",
            side_effect=AssertionError("presentation must never build a client"),
        ):
            payload = self.registry.render("creation", context)
        self.assertTrue(payload["available"])
        return payload

    def portrait(self, character=None):
        return self.render(character)["portrait"]

    def subject(self, character=None):
        return named_character_subject(character or self.character)

    def state(self, character=None):
        """Every fact presentation must never write."""
        character = character or self.character
        subject = self.subject(character)
        record = gallery_api.record_for(subject)
        return {
            "receipt": _plain(character.db.creation_portrait),
            "policy": _plain(character.db.portrait_policy),
            "jobs": sorted(
                (record.db_key, record.db.status) for record in GalleryJobRecord.objects.all()
            ),
            "cards": [card["image_id"] for card in gallery_api.cards_for(subject)],
            "error": None if record is None else record.db.last_error_code,
            "records": gallery_api.GalleryRecord.objects.count(),
            "cache": connectivity._cache_slot,
        }

    def assert_render_writes_nothing(self, character=None):
        before = self.state(character)
        payload = self.render(character)
        self.assertEqual(self.state(character), before)
        return payload


class PortraitStateTests(_PortraitPanelCase):
    """The five states, derived from authorized draft state only."""

    @covers_requirement("webclient-character-creation-ui::creation-portrait-state-is-a-closed-read-only-union")
    def test_no_receipt_is_empty_and_writes_nothing(self):
        payload = self.assert_render_writes_nothing()
        self.assertEqual(payload["portrait"], {"status": "empty"})
        self.assertIsNone(self.character.db.creation_portrait)
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertIsNone(gallery_api.record_for(self.subject()))

    @covers_requirement("webclient-character-creation-ui::creation-portrait-state-is-a-closed-read-only-union")
    def test_pending_then_ready_with_the_exact_card(self):
        admission = self.admit()
        self.assertEqual(self.assert_render_writes_nothing()["portrait"], {"status": "pending"})
        self.drain()
        portrait = self.assert_render_writes_nothing()["portrait"]
        self.assertEqual(portrait["status"], "ready")
        self.assertEqual(set(portrait), {"status", "artwork"})
        artwork = portrait["artwork"]
        subject = self.subject()
        self.assertEqual(artwork["subject_id"], subject.full())
        self.assertEqual(artwork["generation_subject"], subject.full())
        self.assertEqual(artwork["generation_state"], "done")
        self.assertEqual(artwork["retention_sources"], [])
        self.assertEqual(len(artwork["attempts"]), 1)
        attempt = artwork["attempts"][0]
        self.assertEqual(attempt["source_id"], f"portrait.default:{admission.image_id}")
        self.assertEqual(attempt["resource"]["origin"], "runtime")
        self.assertIn(admission.image_id, attempt["resource"]["url"])
        self.assertTrue(attempt["resource"]["url"].startswith(f"/art/gallery/character/{subject.key}/"))
        terminal = artwork["terminal"]
        self.assertEqual(terminal["kind"], "alpha_mask")
        self.assertEqual(
            terminal["source_id"],
            f"portrait.alpha:{self.character.db.creation_portrait['fallback_key']}",
        )
        # No prompt material reaches the wire.
        self.assertNotIn("prompt", str(artwork))

    def test_a_failed_latest_request_reports_the_safe_reason_without_artwork(self):
        self.admit()
        self.drain(self.failing_client())
        portrait = self.assert_render_writes_nothing()["portrait"]
        self.assertEqual(
            portrait,
            {"status": "failed", "reason": CREATION_REASON_MESSAGES["portrait_generation_failed"]},
        )
        self.assertNotIn("sd_generation_error", portrait["reason"])

    def test_a_retained_card_is_not_shown_for_a_newer_pending_or_failed_request(self):
        self.admit()
        self.drain()
        first = self.portrait()["artwork"]
        self.admit()
        self.assertEqual(self.portrait(), {"status": "pending"})
        self.drain(self.failing_client())
        self.assertEqual(self.portrait()["status"], "failed")
        # The retained card is still stored: only its display is withheld.
        self.assertIn(
            first["attempts"][0]["source_id"].split(":", 1)[1],
            [card["image_id"] for card in gallery_api.cards_for(self.subject())],
        )

    def test_a_vanished_card_file_never_presents_a_url(self):
        admission = self.admit()
        self.drain()
        for path in self.root.rglob(f"{admission.image_id}*"):
            path.unlink()
        self.assertEqual(self.portrait(), {"status": "empty"})

    @covers_requirement("webclient-character-creation-ui::creation-portrait-state-is-a-closed-read-only-union")
    def test_reconnect_reconstructs_the_same_state_without_retrying(self):
        self.admit()
        self.drain()
        jobs_before = list(GalleryJobRecord.objects.all())
        first = self.assert_render_writes_nothing()
        second = self.assert_render_writes_nothing()
        self.assertEqual(first["portrait"], second["portrait"])
        self.assertEqual(list(GalleryJobRecord.objects.all()), jobs_before)
        self.assertEqual(self.client.calls[1:], [])
        validate_creation(second)

    def test_an_unrelated_actor_sees_none_of_another_actors_portrait(self):
        self.admit()
        self.drain()
        _other_account, other = self._pending("portrait-bystander")
        self.assertEqual(self.portrait()["status"], "ready")
        self.assertEqual(self.portrait(other), {"status": "empty"})


class PortraitAuthorizationTests(_PortraitPanelCase):
    """Unusable or foreign receipts never present artwork."""

    def unavailable_state(self):
        return {
            "status": "unavailable",
            "reason": CREATION_REASON_MESSAGES["portrait_state_unavailable"],
        }

    def test_malformed_receipts_are_safely_unavailable(self):
        admission = self.admit()
        self.drain()
        valid = dict(self.character.db.creation_portrait)
        cases = {
            "not a mapping": "receipt",
            "wrong version": dict(valid, version=2),
            "non-canonical image id": dict(valid, image_id=admission.image_id.upper()),
            "non-text image id": dict(valid, image_id=7),
            "bad retained id": dict(valid, retained_image_id="not-a-uuid"),
            "unknown fallback key": dict(valid, fallback_key="t_not_a_fallback"),
            "missing fallback key": {k: v for k, v in valid.items() if k != "fallback_key"},
        }
        for label, receipt in cases.items():
            with self.subTest(label):
                self.character.db.creation_portrait = receipt
                self.assertEqual(self.assert_render_writes_nothing()["portrait"], self.unavailable_state())
                self.assertFalse(
                    receipt_owns_image(self.character, self.subject().full(), admission.image_id)
                )

    def test_a_policy_naming_another_subject_is_unauthorized(self):
        admission = self.admit()
        self.drain()
        self.character.db.portrait_policy = {"mode": "named", "stable_key": "t_someone_else"}
        self.assertEqual(self.portrait(), self.unavailable_state())
        self.assertFalse(
            receipt_owns_image(self.character, self.subject().full(), admission.image_id)
        )

    def test_a_receipt_naming_another_characters_image_is_not_ready(self):
        other_account, other = self._pending("portrait-foreign")
        foreign = self.admit(other_account, other)
        self.drain()
        self.admit()
        self.drain()
        self.character.db.creation_portrait = dict(
            self.character.db.creation_portrait, image_id=foreign.image_id
        )
        portrait = self.portrait()
        self.assertEqual(portrait, {"status": "empty"})
        self.assertNotIn(foreign.image_id, str(portrait))

    def test_a_foreign_pending_job_does_not_make_the_receipt_pending(self):
        admission = self.admit()
        self.drain()
        # Another job for the same subject (not the receipt's image) is live.
        from world.art.queue import enqueue_gallery_job

        enqueue_gallery_job(
            self.subject(),
            "foreign request",
            image_id="aaaaaaaa-1111-4111-8111-111111111111",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        portrait = self.portrait()
        self.assertEqual(portrait["status"], "ready")
        self.assertIn(admission.image_id, portrait["artwork"]["attempts"][0]["resource"]["url"])

    def test_receipt_ownership_requires_the_current_image_and_pending_actor(self):
        first = self.admit()
        self.drain()
        second = self.admit()
        subject_key = self.subject().full()
        self.assertTrue(receipt_owns_image(self.character, subject_key, second.image_id))
        self.assertFalse(receipt_owns_image(self.character, subject_key, first.image_id))
        self.assertFalse(receipt_owns_image(self.character, "portrait:character:t_other", second.image_id))
        self.character.creation_pending = False
        self.assertFalse(receipt_owns_image(self.character, subject_key, second.image_id))


class PortraitAvailabilityTests(_PortraitPanelCase):
    """The cached service verdict is a transient, read-only projection."""

    def service_unavailable(self):
        return {
            "status": "unavailable",
            "reason": CREATION_REASON_MESSAGES["portrait_service_unavailable"],
        }

    @covers_requirement("webclient-character-creation-ui::creation-portrait-state-is-a-closed-read-only-union")
    def test_a_current_failed_verdict_is_unavailable_without_a_receipt(self):
        self.cache_failed_verdict()
        self.assertEqual(self.assert_render_writes_nothing()["portrait"], self.service_unavailable())
        self.assertIsNone(self.character.db.creation_portrait)

    def test_an_admitted_job_stays_pending_through_unavailability(self):
        self.admit()
        self.cache_failed_verdict()
        self.assertEqual(self.assert_render_writes_nothing()["portrait"], {"status": "pending"})
        self.assertEqual(len(GalleryJobRecord.objects.all()), 1)

    def test_unavailability_hides_but_preserves_a_ready_card_until_expiry(self):
        self.admit()
        self.drain()
        ready = self.portrait()
        self.cache_failed_verdict()
        cards = [card["image_id"] for card in gallery_api.cards_for(self.subject())]
        self.assertEqual(self.assert_render_writes_nothing()["portrait"], self.service_unavailable())
        self.assertEqual(
            [card["image_id"] for card in gallery_api.cards_for(self.subject())], cards
        )
        # An explicit refresh after expiry recomputes availability read-only.
        with patch.object(connectivity, "_now", return_value=1e12):
            self.assertEqual(self.assert_render_writes_nothing()["portrait"], ready)

    def test_a_configuration_change_invalidates_the_failed_verdict(self):
        self.admit()
        self.drain()
        ready = self.portrait()
        self.cache_failed_verdict()
        self.assertEqual(self.portrait(), self.service_unavailable())
        with override_settings(ART_SD_PROBE_TIMEOUT_MS=1234567):
            self.assertEqual(self.assert_render_writes_nothing()["portrait"], ready)

    def test_a_refreshed_healthy_verdict_restores_ready_and_admission(self):
        self.cache_failed_verdict()
        self.assertEqual(self.portrait(), self.service_unavailable())
        connectivity._reset_for_testing()
        self.assertEqual(self.portrait(), {"status": "empty"})
        self.admit()
        self.assertEqual(self.portrait(), {"status": "pending"})
        self.drain()
        self.assertEqual(self.portrait()["status"], "ready")

    def test_a_failed_request_under_unavailability_reports_unavailable(self):
        self.admit()
        self.drain(self.failing_client())
        self.cache_failed_verdict()
        self.assertEqual(self.portrait(), self.service_unavailable())


class ReadModelPurityTests(_PortraitPanelCase):
    """The rules reader itself creates no record and never probes."""

    def test_the_reader_is_pure(self):
        self.admit()
        before = self.state()
        with patch(
            "world.art.connectivity.probe",
            side_effect=AssertionError("the reader must never probe"),
        ):
            for _ in range(2):
                view = read_draft_portrait(self.character)
        self.assertEqual(view.status, "pending")
        self.assertEqual(self.state(), before)
