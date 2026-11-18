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
from tools.spec_traceability import covers_requirement

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

    @covers_requirement(
        "webclient-character-creation-ui::pending-characters-request-portraits-from-exact-draft-values"
    )
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

    @covers_requirement(
        "webclient-character-creation-ui::pending-characters-request-portraits-from-exact-draft-values"
    )
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

    def test_a_first_draft_card_becomes_the_default_beside_unrelated_cards(self):
        unrelated = "44444444-4444-4444-8444-444444444444"
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
        first = self.admit()
        self.assertEqual(self.drain(), 1)
        record = gallery_api.record_for(self.subject)
        self.assertEqual(record.db.default_image_id, first.image_id)
        self.assertEqual(
            {card["image_id"] for card in self.cards()},
            {first.image_id, unrelated},
        )

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

    @covers_requirement(
        "webclient-character-creation-ui::pending-characters-request-portraits-from-exact-draft-values"
    )
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


# ---------------------------------------------------------------------------
# Confirmed reset (creation-draft-portrait-cleanup).
# ---------------------------------------------------------------------------

_UNRELATED_IMAGE_ID = "55555555-5555-4555-8555-555555555555"


def _write_unrelated_card(case) -> Path:
    """One unrelated card a player could own on the same subject, with its file."""
    identity = f"gallery/character/{case.character.pk}/{_UNRELATED_IMAGE_ID}.png"
    path = case.root / identity
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_png_bytes())
    gallery_api.append_card(
        case.subject,
        image_id=_UNRELATED_IMAGE_ID,
        stored_identity=identity,
        prompt=None,
        seed=None,
        checkpoint=None,
        requested_fields=[],
        binding=None,
        image_size={"width": 8, "height": 8},
        source="generated",
    )
    return path


def _claim_one(case):
    """Claim the one pending job the way the worker does; return (key, token)."""
    claimed = claim(1)
    case.assertEqual(len(claimed), 1)
    record = claimed[0]
    return record.db_key, record.db.generation_token


def _output_paths(case, job_key: str):
    """The (temporary, final) paths and identity one claimed job may publish."""
    image_id = job_key.rsplit(":", 1)[1]
    identity = f"gallery/character/{case.character.pk}/{image_id}.png"
    tmp = case.root / f"tmp-{image_id}.png"
    tmp.write_bytes(_png_bytes())
    target = case.root / identity
    target.parent.mkdir(parents=True, exist_ok=True)
    return tmp, target, identity


def _settle_success(case, job_key: str, token: str):
    """Settle a claimed job with a real temporary output; return (result, tmp, target)."""
    tmp, target, identity = _output_paths(case, job_key)
    result = settle_gallery_generated(
        job_key,
        generation_token=token,
        output_identity=identity,
        tmp_path=str(tmp),
        prompt=None,
        seed=None,
        checkpoint=None,
        image_size={"width": 8, "height": 8},
    )
    return result, tmp, target


class ResetCleanupTests(_DraftPortraitCase):
    """Confirmed reset discards exactly the creation-owned portrait state."""

    def reset(self, *, execute=True):
        from world.rules.creation_wizard import reset_creation_draft

        with self.captureOnCommitCallbacks(execute=execute) as callbacks:
            reset_creation_draft(self.account, self.character)
        return callbacks

    def save_draft(self):
        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="暫存角色",
                age=20,
                apparent_age=20,
                race=_race_key(),
                subrace=_subrace_key(),
                allocations=_balanced_allocations(),
                affinity_elements=[],
            ),
        )

    @covers_requirement(
        "player-character-creation::draft-portrait-lifecycle-follows-reset-and-activation-ownership"
    )
    def test_a_ready_portrait_is_removed_and_its_file_unlinked_only_after_commit(self):
        from world.rules.creation_portrait import PORTRAIT_EMPTY, read_draft_portrait

        self.save_draft()
        self.admit()
        self.assertEqual(self.drain(), 1)
        creation_file = self.root / self.cards()[0]["stored_identity"]
        unrelated_file = _write_unrelated_card(self)
        policy = dict(self.policy())

        callbacks = self.reset(execute=False)
        # The card row is gone at commit, but no file is unlinked before the
        # commit-qualified callback runs.
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [_UNRELATED_IMAGE_ID]
        )
        self.assertTrue(creation_file.exists())
        for callback in callbacks:
            callback()
        self.assertFalse(creation_file.exists())
        self.assertTrue(unrelated_file.exists())
        self.assertIsNone(gallery_api.record_for(self.subject).db.default_image_id)
        self.assertIsNone(self.receipt())
        self.assertFalse(self.character.attributes.has("creation_draft"))
        self.assertEqual(dict(self.policy()), policy, "the named policy is retained")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.jobs(), [])
        self.assertEqual(read_draft_portrait(self.character).status, PORTRAIT_EMPTY)

    def test_a_pending_job_is_canceled_and_never_settles(self):
        self.admit()
        self.assertEqual(len(self.jobs()), 1)
        self.reset()
        self.assertEqual(self.jobs(), [])
        self.assertIsNone(self.receipt())
        self.assertEqual(self.drain(), 0)
        self.assertEqual(self.cards(), [])

    @covers_requirement(
        "player-character-creation::draft-portrait-lifecycle-follows-reset-and-activation-ownership"
    )
    def test_a_claimed_job_settling_after_reset_publishes_nothing(self):
        self.admit()
        job_key, token = _claim_one(self)
        self.reset()
        result, tmp, target = _settle_success(self, job_key, token)
        self.assertIsNone(result)
        self.assertFalse(tmp.exists(), "temporary output is discarded")
        self.assertFalse(target.exists())
        self.assertEqual(self.cards(), [])

    def test_a_late_failure_after_reset_records_nothing(self):
        from world.art.queue import settle_gallery_failed

        self.admit()
        job_key, token = _claim_one(self)
        self.reset()
        self.assertIsNone(
            settle_gallery_failed(job_key, generation_token=token, error="sd_timeout")
        )
        record = gallery_api.record_for(self.subject)
        self.assertTrue(record is None or record.db.last_error_code is None)

    def test_a_failed_receipt_resets_to_an_empty_slot(self):
        from world.art.sd_worker import SDError
        from world.rules.creation_portrait import (
            PORTRAIT_EMPTY,
            PORTRAIT_FAILED,
            read_draft_portrait,
        )

        failing = FakeSDWebUIClient()
        failing.fail_every_call(SDError("sd_connection_error", "offline"))
        self.admit()
        self.assertEqual(self.drain(client=failing), 1)
        self.assertEqual(read_draft_portrait(self.character).status, PORTRAIT_FAILED)
        self.reset()
        self.assertIsNone(gallery_api.record_for(self.subject).db.last_error_code)
        self.assertEqual(read_draft_portrait(self.character).status, PORTRAIT_EMPTY)
        self.character.attributes.reset_cache()
        self.assertEqual(read_draft_portrait(self.character).status, PORTRAIT_EMPTY)

    @covers_requirement(
        "player-character-creation::draft-portrait-lifecycle-follows-reset-and-activation-ownership"
    )
    def test_an_unsaved_draft_resets_twice_and_queues_nothing_while_pending(self):
        from world.art.service import _recover_named_portraits

        self.assertFalse(self.character.attributes.has("creation_draft"))
        self.admit()
        self.drain()
        self.reset()
        self.reset()
        self.assertEqual(self.cards(), [])
        self.assertEqual(self.jobs(), [])
        self.assertIsNone(self.receipt())
        _recover_named_portraits()
        self.assertEqual(self.jobs(), [], "no automatic portrait while pending")

    def test_ownership_and_pending_state_are_rechecked_without_mutation(self):
        from world.rules.creation_wizard import reset_creation_draft

        self.save_draft()
        self.admit()
        receipt = dict(self.receipt())
        intruder = create_account(
            "reset-intruder", "reset-intruder@example.test", "testpassword", typeclass=Account
        )
        with self.assertRaises(CharacterCreationError):
            reset_creation_draft(intruder, self.character)
        self.character.creation_pending = False
        with self.assertRaises(CharacterCreationError):
            reset_creation_draft(self.account, self.character)
        self.assertEqual(dict(self.receipt()), receipt)
        self.assertTrue(self.character.attributes.has("creation_draft"))
        self.assertEqual(len(self.jobs()), 1)

    def test_a_malformed_receipt_is_dropped_without_touching_cards(self):
        _write_unrelated_card(self)
        self.character.db.creation_portrait = {
            "version": 1,
            "image_id": _UNRELATED_IMAGE_ID,
            "retained_image_id": None,
            "fallback_key": "not a closed-vocabulary key",
        }
        self.reset()
        self.assertIsNone(self.receipt())
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [_UNRELATED_IMAGE_ID]
        )

    def test_an_injected_removal_failure_rolls_everything_back(self):
        from world.art.queue import gallery_job_in_flight
        from world.rules.creation_wizard import reset_creation_draft

        self.save_draft()
        first = self.admit()
        self.drain()
        creation_file = self.root / self.cards()[0]["stored_identity"]
        second = self.admit()
        draft_before = dict(self.character.db.creation_draft)
        receipt_before = dict(self.receipt())
        with patch(
            "world.art.gallery._remove_cards_locked",
            side_effect=RuntimeError("injected card removal failure"),
        ), self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaisesRegex(RuntimeError, "injected card removal failure"):
                reset_creation_draft(self.account, self.character)
        self.assertEqual(callbacks, [])
        self.assertTrue(creation_file.exists(), "no premature file deletion")
        self.assertEqual(dict(self.receipt()), receipt_before)
        self.assertEqual(dict(self.character.db.creation_draft), draft_before)
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [first.image_id]
        )
        # The deleted job row came back with the rollback and is still live,
        # discoverable and settleable work.
        self.assertTrue(gallery_job_in_flight(self.subject))
        self.assertEqual(
            [job.db.gallery_image_id for job in self.jobs()], [second.image_id]
        )
        self.assertEqual(self.drain(), 1)
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [second.image_id]
        )

    def test_an_enclosing_transaction_is_rejected_before_serialization(self):
        from django.db import transaction

        from world.rules.creation_portrait import DraftPortraitMutationError
        from world.rules.creation_wizard import reset_creation_draft

        self.admit()
        with patch(
            "world.rules.creation_portrait.serialized_gallery_mutation"
        ) as serialized:
            with transaction.atomic():
                with self.assertRaises(DraftPortraitMutationError):
                    reset_creation_draft(self.account, self.character)
        serialized.assert_not_called()
        self.assertIsNotNone(self.receipt())


def _run_in_thread(target, errors: list, results: dict, name: str) -> threading.Thread:
    """Run ``target`` on its own thread with its own database connection."""

    def body():
        from django.db import connection

        try:
            results[name] = target()
        except BaseException as error:  # noqa: BLE001 - re-raised by the test
            errors.append(error)
        finally:
            connection.close()

    thread = threading.Thread(target=body, daemon=True)
    thread.start()
    return thread


class _BlockingCall:
    """Wrap a callable so one call signals ``entered`` and waits for ``release``."""

    def __init__(self, original):
        self.original = original
        self.entered = threading.Event()
        self.release = threading.Event()

    def __call__(self, *args, **kwargs):
        self.entered.set()
        if not self.release.wait(20):
            raise RuntimeError("the test barrier was never released")
        return self.original(*args, **kwargs)


class ResetSettlementContentionTests(_CommittedDraftPortraitCase):
    """Real worker settlement contending with reset, in both orders."""

    def drain(self):
        with patch(
            "world.art.worker.resolve_sd_client", return_value=self.client
        ):
            return drain_synchronous(10)

    def reset_target(self):
        from world.rules.creation_wizard import reset_creation_draft

        return lambda: reset_creation_draft(self.account, self.character)

    def test_settlement_before_reset_is_then_removed_by_the_reset(self):
        from world.rules import creation_wizard

        first = self.admit()
        self.assertEqual(self.drain(), 1)
        first_file = self.root / self.cards()[0]["stored_identity"]
        second = self.admit()
        job_key, token = _claim_one(self)
        tmp, target, identity = _output_paths(self, job_key)
        blocker = _BlockingCall(gallery_api.append_replacement_card)
        unit_entered = threading.Event()
        original_snapshot = creation_wizard.snapshot_draft_portrait_state

        def observed_snapshot(character):
            unit_entered.set()
            return original_snapshot(character)

        errors: list = []
        results: dict = {}
        with patch(
            "world.art.queue.gallery_api.append_replacement_card", blocker
        ), patch.object(
            creation_wizard, "snapshot_draft_portrait_state", observed_snapshot
        ):
            settle = _run_in_thread(
                lambda: settle_gallery_generated(
                    job_key,
                    generation_token=token,
                    output_identity=identity,
                    tmp_path=str(tmp),
                    prompt=None,
                    seed=None,
                    checkpoint=None,
                    image_size={"width": 8, "height": 8},
                ),
                errors,
                results,
                "settle",
            )
            self.assertTrue(blocker.entered.wait(20))
            reset = _run_in_thread(self.reset_target(), errors, results, "reset")
            reset.join(0.2)
            # The reset waits for the queue serialization BEFORE its
            # transaction or any receipt read; it cannot overtake.
            self.assertTrue(reset.is_alive())
            self.assertFalse(unit_entered.is_set())
            blocker.release.set()
            settle.join(20)
            reset.join(20)
        self.assertFalse(errors, errors)
        self.assertIsNotNone(results["settle"])
        self.assertEqual(results["settle"]["image_id"], second.image_id)
        # The reset removed the card the worker just published, and its file.
        self.assertEqual(self.cards(), [])
        self.assertEqual(self.jobs(), [])
        self.assertIsNone(self.receipt())
        self.assertFalse(target.exists())
        self.assertFalse(first_file.exists())
        self.assertNotEqual(first.image_id, second.image_id)

    def _reset_before_settle(self, settle_call):
        from world.rules import creation_portrait

        self.admit()
        job_key, token = _claim_one(self)
        blocker = _BlockingCall(creation_portrait.remove_creation_portrait_output)
        errors: list = []
        results: dict = {}
        with patch.object(creation_portrait, "remove_creation_portrait_output", blocker):
            reset = _run_in_thread(self.reset_target(), errors, results, "reset")
            self.assertTrue(blocker.entered.wait(20))
            settle = _run_in_thread(
                lambda: settle_call(job_key, token), errors, results, "settle"
            )
            settle.join(0.2)
            # The worker's settlement waits on the queue lock the reset holds.
            self.assertTrue(settle.is_alive())
            blocker.release.set()
            reset.join(20)
            settle.join(20)
        self.assertFalse(errors, errors)
        self.assertIsNone(results["settle"])
        self.assertEqual(self.cards(), [])
        self.assertEqual(self.jobs(), [])
        self.assertIsNone(self.receipt())
        return job_key

    def test_reset_before_settlement_rejects_the_late_success(self):
        paths: dict = {}

        def settle(job_key, token):
            tmp, target, identity = _output_paths(self, job_key)
            paths.update(tmp=tmp, target=target)
            return settle_gallery_generated(
                job_key,
                generation_token=token,
                output_identity=identity,
                tmp_path=str(tmp),
                prompt=None,
                seed=None,
                checkpoint=None,
                image_size={"width": 8, "height": 8},
            )

        self._reset_before_settle(settle)
        self.assertFalse(paths["tmp"].exists(), "temporary output is discarded")
        self.assertFalse(paths["target"].exists(), "no stored output is published")

    def test_reset_before_settlement_rejects_the_late_failure(self):
        from world.art.queue import settle_gallery_failed

        self._reset_before_settle(
            lambda job_key, token: settle_gallery_failed(
                job_key, generation_token=token, error="sd_timeout"
            )
        )
        record = gallery_api.record_for(self.subject)
        self.assertTrue(record is None or record.db.last_error_code is None)

    def test_committed_unlinks_run_after_every_lock_was_released(self):
        from world.rules import creation_portrait

        self.admit()
        self.assertEqual(self.drain(), 1)
        creation_file = self.root / self.cards()[0]["stored_identity"]
        observed: list = []
        original = creation_portrait.unlink_creation_portrait_files

        def spy(subject, identities):
            observed.append((queue_lock.locked(), _gallery_locked(), tuple(identities)))
            original(subject, identities)

        with patch.object(creation_portrait, "unlink_creation_portrait_files", spy):
            self.reset_target()()
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][:2], (False, False))
        self.assertFalse(creation_file.exists())

    def test_a_failed_commit_keeps_cards_jobs_files_and_caches(self):
        from world.art.queue import gallery_job_in_flight
        from world.rules import creation_portrait, creation_wizard

        first = self.admit()
        self.assertEqual(self.drain(), 1)
        creation_file = self.root / self.cards()[0]["stored_identity"]
        second = self.admit()
        receipt_before = dict(self.receipt())
        unlinks: list = []
        original_clear = creation_wizard.clear_draft_portrait

        def clear_then_fail(character, unit):
            original_clear(character, unit)
            raise RuntimeError("injected failure after cleanup")

        with patch.object(
            creation_wizard, "clear_draft_portrait", clear_then_fail
        ), patch.object(
            creation_portrait,
            "unlink_creation_portrait_files",
            lambda subject, identities: unlinks.append(identities),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected failure after cleanup"):
                self.reset_target()()
        self.assertEqual(unlinks, [], "a rolled-back reset unlinks nothing")
        self.assertTrue(creation_file.exists())
        self.assertEqual(dict(self.receipt()), receipt_before)
        self.character.attributes.reset_cache()
        self.assertEqual(dict(self.receipt()), receipt_before)
        self.assertEqual(
            [card["image_id"] for card in self.cards()], [first.image_id]
        )
        self.assertTrue(gallery_job_in_flight(self.subject))
        self.assertEqual(
            [job.db.gallery_image_id for job in self.jobs()], [second.image_id]
        )
        self.assertFalse(queue_lock.locked())


class IdentityEditRetentionTests(_DraftPortraitCase):
    """Identity edits and custom saves never invalidate a creation portrait."""

    def save(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "暫存角色",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": _subrace_key(),
            "allocations": _balanced_allocations(),
            "affinity_elements": [],
            "sex": "female",
        }
        values.update(overrides)
        save_custom_draft(
            self.account, self.character, CharacterCreationRequest(**values)
        )

    @covers_requirement(
        "webclient-character-creation-ui::identity-edits-preserve-a-creation-portrait-without-warnings"
    )
    def test_ready_and_pending_portraits_survive_every_identity_edit(self):
        from world.rules.creation_portrait import (
            PORTRAIT_PENDING,
            PORTRAIT_READY,
            read_draft_portrait,
        )

        self.save()
        ready = self.admit()
        self.drain()
        edits = {
            "sex": {"sex": "male"},
            "apparent age": {"apparent_age": 61},
            "age": {"age": 63},
        }
        for label, overrides in edits.items():
            with self.subTest(label):
                self.save(**overrides)
                view = read_draft_portrait(self.character)
                self.assertEqual(view.status, PORTRAIT_READY)
                self.assertEqual(view.card["image_id"], ready.image_id)
                self.assertEqual(self.receipt()["image_id"], ready.image_id)
                self.assertEqual(self.jobs(), [])
        pending = self.admit()
        description = self.jobs()[0].db.source_description
        self.save(sex="female", apparent_age=17)
        self.assertEqual(read_draft_portrait(self.character).status, PORTRAIT_PENDING)
        self.assertEqual(
            [job.db.gallery_image_id for job in self.jobs()], [pending.image_id]
        )
        self.assertEqual(
            self.jobs()[0].db.source_description,
            description,
            "the admitted snapshot is never re-read from newer form values",
        )

    @covers_requirement(
        "webclient-character-creation-ui::identity-edits-preserve-a-creation-portrait-without-warnings"
    )
    def test_a_race_and_subrace_change_keeps_the_portrait(self):
        from world.rules.creation_portrait import PORTRAIT_READY, read_draft_portrait

        _inject_single_sex_race(self)
        self.save()
        ready = self.admit()
        self.drain()
        profile = resolve_starting_profile(
            _SINGLE_SEX_RACE.key, _SINGLE_SEX_SUBRACE.key
        )
        allocations = {key: 0 for key in ALLOCATABLE_AXES}
        remaining = profile.budget
        for key, (lower, upper) in profile.bounds:
            allocations[key] = min(upper - lower, remaining)
            remaining -= allocations[key]
        self.save(
            race=_SINGLE_SEX_RACE.key,
            subrace=_SINGLE_SEX_SUBRACE.key,
            allocations=allocations,
        )
        view = read_draft_portrait(self.character)
        self.assertEqual(view.status, PORTRAIT_READY)
        self.assertEqual(view.card["image_id"], ready.image_id)
        self.assertEqual(self.jobs(), [])
