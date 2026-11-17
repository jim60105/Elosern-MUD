"""Rules-owned pending-character draft portrait admission.

Every test runs on the synthetic kit (races/subraces and an injected fake image
client) with a temporary art store, so no shipped content or network endpoint is
touched. The assertions are about observable committed state — policy, receipt,
gallery cards/files, queue records — never about elapsed time.
"""

import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter

from world.art import connectivity
from world.art import gallery as gallery_api
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.queue import claim, queue_lock, settle_gallery_generated
from world.art.store import GalleryJobRecord
from world.art.subjects import named_character_subject
from world.art.worker import drain_synchronous
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationError,
    CharacterCreationRequest,
    resolve_starting_profile,
)
from world.rules.creation_messages import rejection_code
from world.rules.creation_portrait import (
    DraftPortraitRequest,
    PortraitInFlight,
    PortraitServiceUnavailable,
    read_portrait_service_availability,
    request_draft_portrait,
)
from world.rules.creation_wizard import draft_fingerprint, save_custom_draft
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import (
    SYNTH_RACES,
    SYNTH_SUBRACES,
    make_race,
    make_subrace,
    synthetic_registries,
)

# A race that permits exactly one sex member, so a forbidden-sex rejection is
# observable without touching a shipped race's rule.
_SINGLE_SEX_RACE = make_race("t_single_sex", allowed_sexes=("female",))
_SINGLE_SEX_SUBRACE = make_subrace("t_single_sex_kin", race_key="t_single_sex")
_FORBIDDEN_SEX_FOR_SINGLE_SEX_RACE = "male"


def _race_key() -> str:
    return "t_duskmari"


def _subrace_key() -> str:
    return "t_duskmari_evensong"


class _DraftPortraitCase(EvenniaTestCase):
    """Shared pending shell, temporary art store, and injected image client."""

    def setUp(self):
        open_synthetic_scope(self, "races", "subraces")
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
        self.account = create_account(
            "draft-owner", "draft@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="draft-shell")
        self.account.at_post_create_character(self.character)
        self.client = FakeSDWebUIClient()

    # -- harness ----------------------------------------------------------
    @property
    def subject(self):
        return named_character_subject(self.character)

    def request(self, **overrides):
        values = {
            "race": _race_key(),
            "subrace": _subrace_key(),
            "sex": "female",
            "apparent_age": 26,
            "custom_prompt": "",
        }
        values.update(overrides)
        return DraftPortraitRequest(**values)

    def admit(self, **overrides):
        with patch(
            "world.art.connectivity.resolve_sd_client", return_value=self.client
        ):
            with self.captureOnCommitCallbacks(execute=True):
                return request_draft_portrait(
                    self.account, self.character, self.request(**overrides)
                )

    def jobs(self):
        return [
            record
            for record in GalleryJobRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    def drain(self, client=None):
        with patch(
            "world.art.worker.resolve_sd_client",
            return_value=client or self.client,
        ):
            return drain_synchronous(10)

    def receipt(self):
        return self.character.db.creation_portrait

    def policy(self):
        return self.character.db.portrait_policy

    def cards(self):
        return gallery_api.cards_for(self.subject)

    def assert_nothing_written(self):
        self.assertEqual(self.jobs(), [])
        self.assertIsNone(self.policy())
        self.assertIsNone(self.receipt())
        self.assertEqual(self.cards(), [])


class AdmissionWritesTests(_DraftPortraitCase):
    """One valid request queues exactly one named-subject image job."""

    def test_a_valid_draft_request_needs_no_saved_form(self):
        admission = self.admit(custom_prompt="  紅色長髮  ")
        self.assertEqual(len(self.jobs()), 1)
        job = self.jobs()[0]
        self.assertTrue(job.db_key.startswith(f"art:{self.subject.full()}:gen:"))
        self.assertEqual(job.db_key.split(":gen:")[1], admission.image_id)
        self.assertIsNone(job.db.gallery_binding)
        self.assertIsNone(job.db.gallery_face_rect)
        self.assertEqual(list(job.db.gallery_requested_fields), [])
        self.assertEqual(
            self.policy(), {"mode": "named", "stable_key": str(self.character.pk)}
        )
        receipt = self.receipt()
        self.assertEqual(receipt["version"], 1)
        self.assertEqual(receipt["image_id"], admission.image_id)
        self.assertIsNone(receipt["retained_image_id"])
        self.assertTrue(receipt["fallback_key"])
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [], "no card exists yet"
        )
        self.assertTrue(job.db.source_description)
        self.assertNotIn("draft-shell", job.db.source_description)

    def test_no_canonical_identity_draft_or_confirmation_write_occurs(self):
        request = CharacterCreationRequest(
            mode="custom",
            display_name="暫存角色",
            age=20,
            apparent_age=20,
            race=_race_key(),
            subrace=_subrace_key(),
            allocations=_balanced_allocations(),
            affinity_elements=[],
        )
        save_custom_draft(self.account, self.character, request)
        fingerprint = draft_fingerprint(self.character)
        marker = "confirmed-marker"
        setattr(self.character.ndb, "elosern_confirmed_draft_fingerprint", marker)
        before = {
            attribute: getattr(self.character.db, attribute, None)
            for attribute in ("age", "apparent_age", "race", "subrace", "sex")
        }
        self.admit()
        for attribute, value in before.items():
            self.assertEqual(
                getattr(self.character.db, attribute, None),
                value,
                f"portrait admission must not write {attribute}",
            )
        self.assertIsNone(before["race"])
        self.assertIsNone(before["apparent_age"])
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(draft_fingerprint(self.character), fingerprint)
        self.assertEqual(
            getattr(self.character.ndb, "elosern_confirmed_draft_fingerprint"), marker
        )

    def test_identity_validation_rejects_before_any_write(self):
        cases = {
            "unknown race": {"race": "t_unregistered_race"},
            "unregistered subrace": {"subrace": "t_unregistered_subrace"},
            "unknown sex member": {"sex": "unknown"},
            "boolean apparent age": {"apparent_age": True},
            "out of range apparent age": {"apparent_age": 10001},
            "negative apparent age": {"apparent_age": -1},
            "control-bearing prompt": {"custom_prompt": "bad\x07prompt"},
        }
        for label, overrides in cases.items():
            with self.subTest(label):
                connectivity._reset_for_testing()
                with self.assertRaises(CharacterCreationError):
                    self.admit(**overrides)
                self.assert_nothing_written()

    def test_a_subrace_from_another_race_is_rejected(self):
        _inject_single_sex_race(self)
        with self.assertRaises(CharacterCreationError):
            self.admit(race=_race_key(), subrace=_SINGLE_SEX_SUBRACE.key)
        self.assert_nothing_written()

    def test_a_forbidden_sex_is_rejected_before_any_write(self):
        _inject_single_sex_race(self)
        with self.assertRaises(CharacterCreationError):
            self.admit(
                race=_SINGLE_SEX_RACE.key,
                subrace=_SINGLE_SEX_SUBRACE.key,
                sex=_FORBIDDEN_SEX_FOR_SINGLE_SEX_RACE,
            )
        self.assert_nothing_written()

    def test_a_blank_or_whitespace_prompt_normalizes_to_the_legal_noop(self):
        self.admit(custom_prompt="   ")
        self.assertEqual(len(self.jobs()), 1)

    def test_ownership_and_pending_state_are_rechecked(self):
        other = create_account(
            "intruder", "intruder@example.test", "testpassword", typeclass=Account
        )
        with patch(
            "world.art.connectivity.resolve_sd_client", return_value=self.client
        ):
            with self.assertRaises(CharacterCreationError):
                request_draft_portrait(other, self.character, self.request())
        self.assert_nothing_written()

        self.character.creation_pending = False
        with patch(
            "world.art.connectivity.resolve_sd_client", return_value=self.client
        ):
            with self.assertRaises(CharacterCreationError):
                request_draft_portrait(self.account, self.character, self.request())
        self.assert_nothing_written()

    def test_an_activated_character_cannot_use_the_draft_path(self):
        self.character.creation_pending = False
        with self.assertRaises(CharacterCreationError):
            self.admit()
        self.assert_nothing_written()


class InFlightTests(_DraftPortraitCase):
    """A second request while one job is live is refused without writes."""

    def test_a_second_request_is_rejected_before_the_policy_write(self):
        first = self.admit()
        receipt_before = dict(self.receipt())
        policy_before = dict(self.policy())
        with self.assertRaises(PortraitInFlight):
            self.admit()
        self.assertEqual(len(self.jobs()), 1)
        self.assertEqual(self.jobs()[0].db_key.split(":gen:")[1], first.image_id)
        self.assertEqual(self.policy(), policy_before)
        self.assertEqual(self.receipt(), receipt_before)
        self.assertEqual(self.cards(), [])


class ReceiptRetentionTests(_DraftPortraitCase):
    """Only a readable creation card is ever replaceable."""

    def test_settlement_replaces_only_the_previous_creation_card(self):
        first = self.admit()
        self.assertEqual(self.drain(), 1)
        cards = self.cards()
        self.assertEqual([card["image_id"] for card in cards], [first.image_id])
        first_identity = cards[0]["stored_identity"]
        self.assertTrue((self.root / first_identity).exists())
        # One unrelated card a player could own on the same record.
        unrelated = "33333333-3333-4333-8333-333333333333"
        gallery_api.append_card(
            self.subject,
            image_id=unrelated,
            stored_identity=f"gallery/character/{self.character.pk}/{unrelated}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            image_size={"width": 8, "height": 8},
            source="generated",
        )

        second = self.admit()
        self.assertEqual(second.retained_image_id, first.image_id)
        job = self.jobs()[0]
        self.assertEqual(job.db.gallery_replacement_image_id, first.image_id)
        self.assertEqual(self.drain(), 1)
        remaining = {card["image_id"] for card in self.cards()}
        self.assertEqual(remaining, {second.image_id, unrelated})
        record = gallery_api.record_for(self.subject)
        self.assertEqual(record.db.default_image_id, second.image_id)
        self.assertFalse((self.root / first_identity).exists())

    def test_a_failed_attempt_never_becomes_the_retained_card(self):
        from world.art.sd_worker import SDError

        first = self.admit()
        self.assertEqual(self.drain(), 1)
        failing = FakeSDWebUIClient()
        failing.fail_every_call(SDError("sd_connection_error", "offline"))
        second = self.admit()
        self.assertEqual(second.retained_image_id, first.image_id)
        self.assertEqual(self.drain(client=failing), 1)
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [first.image_id]
        )
        third = self.admit()
        self.assertEqual(third.retained_image_id, first.image_id)
        self.assertEqual(self.drain(client=failing), 1)
        fourth = self.admit()
        self.assertEqual(fourth.retained_image_id, first.image_id)
        self.assertEqual(self.drain(), 1)
        # The replacement chain never adopts a failed request id.
        self.assertEqual(
            {card["image_id"] for card in self.cards()}, {fourth.image_id}
        )
        record = gallery_api.record_for(self.subject)
        self.assertEqual(record.db.default_image_id, fourth.image_id)


class RollbackTests(_DraftPortraitCase):
    """A failed admission leaves no policy, receipt, card or job behind."""

    def test_a_failed_queue_write_restores_policy_and_receipt_caches(self):
        with patch(
            "world.rules.creation_portrait.request_gallery_image",
            side_effect=RuntimeError("queue unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self.admit()
        self.assert_nothing_written()

    def test_a_rollback_leaves_the_previous_receipt_untouched(self):
        self.admit()
        self.drain()
        policy_before = dict(self.policy())
        receipt_before = dict(self.receipt())
        with patch(
            "world.rules.creation_portrait.request_gallery_image",
            side_effect=RuntimeError("late failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.admit()
        self.assertEqual(self.policy(), policy_before)
        self.assertEqual(self.receipt(), receipt_before)
        self.assertEqual(len(self.jobs()), 0)


class ConnectivityRefusalTests(_DraftPortraitCase):
    """The one admission exception: known-unavailable refuses retryably."""

    def test_known_unavailable_refuses_before_mutation_and_permits_retry(self):
        self.client.fail_probe()
        with self.assertRaises(PortraitServiceUnavailable) as caught:
            self.admit()
        self.assertEqual(
            rejection_code(caught.exception), "portrait_service_unavailable"
        )
        self.assert_nothing_written()
        # A later successful verdict admits the explicit retry (the cached
        # failed verdict expires, so the retry re-probes).
        self.client.recover_probe()
        connectivity._reset_for_testing()
        self.admit()
        self.assertEqual(len(self.jobs()), 1)

    def test_availability_reader_never_probes_and_ignores_absent_verdicts(self):
        calls_before = len(self.client.probe_calls)
        self.assertTrue(read_portrait_service_availability().available)
        self.assertEqual(len(self.client.probe_calls), calls_before)
        with patch(
            "world.art.connectivity.resolve_sd_client", return_value=self.client
        ):
            self.client.fail_probe()
            connectivity.probe()
        availability = read_portrait_service_availability()
        self.assertFalse(availability.available)
        self.assertTrue(availability.reason)
        self.assertEqual(len(self.client.probe_calls), calls_before + 1)

    def test_an_expired_verdict_does_not_manufacture_unavailability(self):
        with patch(
            "world.art.connectivity.resolve_sd_client", return_value=self.client
        ):
            self.client.fail_probe()
            connectivity.probe()
        with patch.object(connectivity, "_now", return_value=1e12):
            self.assertTrue(read_portrait_service_availability().available)


class StartupRecoveryTests(_DraftPortraitCase):
    """Startup never manufactures an automatic replacement for a pending shell."""

    def test_a_pending_policy_is_not_recovered(self):
        from world.art.service import _recover_named_portraits

        self.admit()
        self.assertEqual(len(self.jobs()), 1)
        _recover_named_portraits()
        self.assertEqual(len(self.jobs()), 1)

    def test_a_settled_pending_card_is_left_alone(self):
        from world.art.service import _recover_named_portraits

        self.admit()
        self.drain()
        self.assertEqual(len(self.cards()), 1)
        _recover_named_portraits()
        self.assertEqual(len(self.jobs()), 0)
        self.assertEqual(len(self.cards()), 1)


class _CommittedDraftPortraitCase(TransactionTestCase):
    """The same pending shell on REAL commits, so threads observe stored rows.

    Django's atomic ``TestCase`` wrapper would both hide committed state from a
    second connection and make the commit-callback deferral untestable, so this
    narrow class uses the documented ``TransactionTestCase`` precedent for
    transaction-semantics evidence.
    """

    def setUp(self):
        open_synthetic_scope(self, "races", "subraces")
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
        self.account = create_account(
            "draft-owner", "draft@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="draft-shell")
        self.account.at_post_create_character(self.character)
        self.client = FakeSDWebUIClient()

    @property
    def subject(self):
        return named_character_subject(self.character)

    def request(self, **overrides):
        values = {
            "race": _race_key(),
            "subrace": _subrace_key(),
            "sex": "female",
            "apparent_age": 26,
            "custom_prompt": "",
        }
        values.update(overrides)
        return DraftPortraitRequest(**values)

    def admit(self, **overrides):
        with patch(
            "world.art.connectivity.resolve_sd_client", return_value=self.client
        ):
            return request_draft_portrait(
                self.account, self.character, self.request(**overrides)
            )

    def jobs(self):
        return [
            record
            for record in GalleryJobRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    def cards(self):
        return gallery_api.cards_for(self.subject)

    def receipt(self):
        return self.character.db.creation_portrait


class SerializationOrderingTests(_CommittedDraftPortraitCase):
    """Queue-before-database ordering, proven with real threads and barriers."""

    def test_admission_waits_for_a_held_serialization(self):
        from world.art.service import serialized_gallery_mutation

        held = threading.Event()
        release = threading.Event()
        started = threading.Event()
        errors: list[BaseException] = []
        result: dict = {}

        def holder():
            with serialized_gallery_mutation(self.subject):
                held.set()
                release.wait(10)

        def admit():
            started.set()
            try:
                result["admission"] = self.admit()
            except BaseException as error:  # noqa: BLE001 - re-raised below
                errors.append(error)

        worker_thread = threading.Thread(target=holder, daemon=True)
        admit_thread = threading.Thread(target=admit, daemon=True)
        worker_thread.start()
        self.assertTrue(held.wait(10))
        admit_thread.start()
        self.assertTrue(started.wait(10))
        # The admission cannot complete while the shared serialization is held.
        self.assertTrue(admit_thread.is_alive())
        release.set()
        worker_thread.join(20)
        admit_thread.join(20)
        self.assertFalse(errors, errors)
        self.assertEqual(len(self.jobs()), 1)

    def test_a_contending_settlement_is_seen_as_the_retained_card(self):
        """The admission waits, then retains the settlement's committed card."""
        gallery_module = gallery_api
        first = self.admit()
        claimed = claim(10)
        self.assertEqual(len(claimed), 1)
        token = str(claimed[0].db.generation_token)
        identity = f"gallery/character/{self.character.pk}/{first.image_id}.png"
        tmp_path = self.root / "pending-upload.png"
        tmp_path.write_bytes(_png_bytes())
        (self.root / identity).parent.mkdir(parents=True, exist_ok=True)

        started = threading.Event()
        release_settlement = threading.Event()
        original_append = gallery_module.append_card

        def slow_append(subject, **card_fields):
            started.set()
            release_settlement.wait(10)
            return original_append(subject, **card_fields)

        settlement_errors: list[BaseException] = []
        settlement_result: dict = {}

        def settle():
            try:
                settlement_result["card"] = settle_gallery_generated(
                    claimed[0].db_key,
                    generation_token=token,
                    output_identity=identity,
                    tmp_path=str(tmp_path),
                    prompt={"positive": "p", "negative": "n"},
                    seed=None,
                    checkpoint=None,
                    image_size={"width": 8, "height": 8},
                )
            except BaseException as error:  # noqa: BLE001 - re-raised below
                settlement_errors.append(error)

        admission_errors: list[BaseException] = []
        admission_started = threading.Event()
        admission_result: dict = {}

        def admit():
            admission_started.set()
            try:
                admission_result["admission"] = self.admit()
            except BaseException as error:  # noqa: BLE001 - re-raised below
                admission_errors.append(error)

        settle_thread = threading.Thread(target=settle, daemon=True)
        admit_thread = threading.Thread(target=admit, daemon=True)
        with patch.object(gallery_module, "append_card", slow_append):
            settle_thread.start()
            self.assertTrue(started.wait(10))
            admit_thread.start()
            self.assertTrue(admission_started.wait(10))
            self.assertTrue(admit_thread.is_alive())
            release_settlement.set()
            settle_thread.join(20)
            admit_thread.join(20)
        self.assertFalse(settlement_errors, settlement_errors)
        self.assertFalse(admission_errors, admission_errors)
        self.assertIsNotNone(settlement_result.get("card"))
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [first.image_id]
        )
        admission = admission_result["admission"]
        self.assertEqual(admission.retained_image_id, first.image_id)
        self.assertEqual(len(self.jobs()), 1)

    def test_deferred_callbacks_run_after_the_locks_are_released(self):
        from world.art.service import serialized_gallery_mutation
        from world.rules.presentation_events import (
            defer_publication_callbacks,
            on_publication_commit,
        )

        observed: list[tuple[bool, bool]] = []
        # A real commit: the deferral scope exits only after the serialized
        # unit was released, and Django runs the drain at that commit.
        with defer_publication_callbacks():
            with serialized_gallery_mutation(self.subject):
                on_publication_commit(
                    lambda: observed.append(
                        (queue_lock.locked(), _gallery_locked())
                    )
                )
        self.assertEqual(observed, [(False, False)])


def _gallery_locked() -> bool:
    from world.art import gallery as gallery_module

    lock = gallery_module.gallery_lock
    acquired = lock.acquire(blocking=False)
    if acquired:
        lock.release()
        return False
    return True


def _png_bytes() -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, format="PNG")
    return buffer.getvalue()


def _balanced_allocations() -> dict[str, int]:
    profile = resolve_starting_profile(_race_key(), _subrace_key())
    remaining = profile.budget
    result = {key: 0 for key in ALLOCATABLE_AXES}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    return result


def _inject_single_sex_race(case) -> None:
    """Add the restricted-sex synthetic rows on top of this test's scope."""
    scope = synthetic_registries(
        "races",
        "subraces",
        extra={
            "races": {
                **{row.key: row for row in SYNTH_RACES.values()},
                _SINGLE_SEX_RACE.key: _SINGLE_SEX_RACE,
            },
            "subraces": {
                **{row.key: row for row in SYNTH_SUBRACES.values()},
                _SINGLE_SEX_SUBRACE.key: _SINGLE_SEX_SUBRACE,
            },
        },
    )
    case.enterContext(scope)
