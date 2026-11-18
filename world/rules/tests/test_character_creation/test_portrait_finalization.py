"""Slice of ``test_character_creation``: PortraitFinalizationTests."""
from tools.spec_traceability import covers_requirement
from copy import deepcopy
import inspect
from inspect import signature
from dataclasses import replace
from contextlib import contextmanager
from unittest.mock import patch
import threading
import unittest
from django.test import TransactionTestCase
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.races import StatModifiers
from world.lore.starting_kits import SubraceStartingKit
from world.lore.sex import DEFAULT_SEX
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    PERSONA_IMPORT_CARD_KEYS,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    preflight_character_creation,
    resolve_preset_values,
    resolve_starting_profile,
)
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    SYNTH_SUBRACES,
    StaticBand,
    Vitals,
    _SYNTH_ELEMENT,
    make_element,
    make_item,
    make_race,
    make_preset,
    make_subrace,
    make_skill,
    synthetic_registries,
)
from world.skills.registry import SkillPrerequisite
from world.rules.tests._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
)

from ._support import (
    _portrait_ensure_callbacks,
    _race_key,
    balanced_allocations,
)
from world.tests.start_room_fixture import stub_start_room


class PortraitFinalizationTests(EvenniaTest):
    """Shared portrait finalization on every activation path
    (fix-creation-finalization-safety D3 / art-asset-lifecycle)."""

    def setUp(self):
        self.enterContext(stub_start_room())
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    def _portrait_key(self):
        return f"art:portrait:character:{self.character.pk}"

    def _gallery_jobs(self):
        from world.art.store import GalleryJobRecord

        return [
            record
            for record in GalleryJobRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    @covers_requirement(
        "art-gallery-autogen::every-player-activation-path-finalizes-the-portrait-lifecycle"
    )
    def test_activation_sets_the_named_policy_and_schedules_exactly_one_ensure(self):
        from world.art.store import GalleryJobRecord

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # The retrofit: the committed creation owns exactly one gallery job,
        # never a classic fixed-identity record.
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"{self._portrait_key()}:gen:"))
        self.assertEqual(
            GalleryJobRecord.objects.filter(db_key=self._portrait_key()).count(), 0
        )

    @covers_requirement(
        "art-gallery-autogen::every-player-activation-path-finalizes-the-portrait-lifecycle"
    )
    def test_web_activation_produces_identical_portrait_state(self):
        from web.webclient.actions.creation_actions import (
            _creation_activate_adapter,
            _creation_custom_adapter,
        )
        from world.art.store import GalleryJobRecord

        web = create_object(PlayerCharacter, key="web-shell")
        self.account.at_post_create_character(web)
        web.db_account = self.account
        _creation_custom_adapter(
            web,
            {
                "display_name": "網頁角色",
                "age": 20,
                "apparent_age": 20,
                "race": _race_key(),
                "subrace": next(iter(SYNTH_SUBRACES)),
                "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
                "background": None,
                "affinity_elements": [],
                "persona": None,
            },
        )
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            _creation_activate_adapter(web, {})
        self.assertFalse(web.creation_pending)
        self.assertEqual(
            web.db.portrait_policy,
            {"mode": "named", "stable_key": str(web.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # Same retrofit on the web activation path: one gallery job, no
        # classic fixed-identity record.
        self.assertEqual(len(self._gallery_jobs()), 1)
        self.assertEqual(
            GalleryJobRecord.objects.filter(
                db_key=f"art:portrait:character:{web.pk}"
            ).count(),
            0,
        )

    def test_failed_activation_leaves_no_policy_and_no_job(self):
        from world.art.store import GalleryJobRecord
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(self.account, self.character, self.request())

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(
                self.account, self.character,
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(
            GalleryJobRecord.objects.filter(db_key=self._portrait_key()).count(),
            0,
        )
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_skipped_activation_establishes_the_policy_and_enqueues_nothing(self):
        from world.art import gallery as gallery_api
        from world.art.presenter import describe_entity
        from world.art.subjects import ArtSubject, ArtSubjectKind

        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(skip_portrait=True),
            )
        # The named policy exists on the skipped path too — the character
        # stays eligible for a later request.
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(self._gallery_jobs(), [])
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.character.pk))
        self.assertEqual(gallery_api.cards_for(subject), [])
        # Empty-gallery resolution reaches the chain's terminal fallback seam
        # (world.art.gallery_match.fallback_for): filled by
        # gallery-builtin-fallbacks, the seam resolves a committed built-in
        # silhouette for the artless character, carried decoratively beside the
        # subject's true missing state (builtin-silhouette-stage-fallback).
        with patch("world.observability.log_info"):
            descriptor = describe_entity(self.character)
        # An eligible but artless character resolves no candidate while still
        # naming its own subject; only the attribute-selected alpha terminal
        # remains.
        self.assertEqual(descriptor["attempts"], [])
        self.assertEqual(
            descriptor["generation_subject"],
            ArtSubject(ArtSubjectKind.CHARACTER, str(self.character.pk)).full(),
        )
        self.assertTrue(descriptor["terminal"]["resource"]["url"].startswith("/art/defaults/"))
        with patch(
            "world.art.presenter.fallback_for",
            return_value={
                "identity": "defaults/man.webp",
                "key": "man",
                "face_rect": None,
            },
        ):
            served = describe_entity(self.character)
        self.assertEqual(served["terminal"]["resource"]["url"], "/art/defaults/man.webp")
        self.assertEqual(served["attempts"], [])

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_default_activation_still_schedules_one_generation(self):
        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(len(self._gallery_jobs()), 1)

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_a_rolled_back_skipped_activation_leaves_nothing(self):
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(
            self.account, self.character, self.request(skip_portrait=True)
        )

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(self.account, self.character, write_observer=fail)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(self._gallery_jobs(), [])


# ---------------------------------------------------------------------------
# Draft portrait disposition at activation (creation-draft-portrait-cleanup).
# ---------------------------------------------------------------------------

#: A companion-free synthetic preset card, so preset activation binds nothing.
_COMPANION_FREE_PRESET = "t_ash_finch"


def _png_bytes() -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, format="PNG")
    return buffer.getvalue()


def _presented_resource(descriptor):
    """The descriptor's first presented image resource, or ``None``."""
    for attempt in descriptor["attempts"]:
        if attempt["type"] == "image":
            return attempt["resource"]
    return None


class _DraftPortraitActivationMixin:
    """A pending shell with a temporary art store and an injected image client."""

    def enter_art_store(self):
        import tempfile
        from pathlib import Path

        from django.test import override_settings

        from world.art import connectivity
        from world.art.fake_sd_client import FakeSDWebUIClient

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
        self.client = FakeSDWebUIClient()

    @property
    def subject(self):
        from world.art.subjects import named_character_subject

        return named_character_subject(self.character)

    def custom_request(self, **overrides):
        subrace = next(iter(SYNTH_SUBRACES))
        values = {
            "mode": "custom",
            "display_name": "新角色",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": subrace,
            "allocations": balanced_allocations(_race_key(), subrace),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    def preset_request(self, **overrides):
        return CharacterCreationRequest(
            mode="preset", preset_key=_COMPANION_FREE_PRESET, **overrides
        )

    def admit(self):
        from world.rules.creation_portrait import (
            DraftPortraitRequest,
            request_draft_portrait,
        )

        with patch(
            "world.art.connectivity.resolve_sd_client", return_value=self.client
        ):
            return request_draft_portrait(
                self.account,
                self.character,
                DraftPortraitRequest(
                    race=_race_key(),
                    subrace=next(iter(SYNTH_SUBRACES)),
                    sex="female",
                    apparent_age=20,
                ),
            )

    def drain(self):
        from world.art.worker import drain_synchronous

        with patch("world.art.worker.resolve_sd_client", return_value=self.client):
            return drain_synchronous(10)

    @contextmanager
    def count_enqueues(self):
        """Count the automatic-path gallery enqueues inside the block."""
        from world.art import service

        original = service.request_gallery_image
        calls = []

        def counted(entity, **kwargs):
            calls.append(entity)
            return original(entity, **kwargs)

        with patch.object(service, "request_gallery_image", counted):
            yield calls

    def jobs(self):
        from world.art.store import GalleryJobRecord

        return [
            record
            for record in GalleryJobRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    def job_ids(self):
        return sorted(str(job.db.gallery_image_id) for job in self.jobs())

    def cards(self):
        from world.art import gallery as gallery_api

        return gallery_api.cards_for(self.subject)

    def card_ids(self):
        return [card["image_id"] for card in self.cards()]

    def default_image_id(self):
        from world.art import gallery as gallery_api

        record = gallery_api.record_for(self.subject)
        return None if record is None else record.db.default_image_id

    def ready_card(self):
        """Admit and settle one creation card; return (admission, file path)."""
        admission = self.admit()
        self.drain()
        self.assertEqual(self.card_ids(), [admission.image_id])
        return admission, self.root / self.cards()[0]["stored_identity"]

    def claim_one(self):
        from world.art.queue import claim

        claimed = claim(1)
        self.assertEqual(len(claimed), 1)
        return claimed[0].db_key, claimed[0].db.generation_token

    def settle_success(self, job_key, token):
        from world.art.queue import settle_gallery_generated

        image_id = job_key.rsplit(":", 1)[1]
        identity = f"gallery/character/{self.character.pk}/{image_id}.png"
        tmp = self.root / f"tmp-{image_id}.png"
        tmp.write_bytes(_png_bytes())
        (self.root / identity).parent.mkdir(parents=True, exist_ok=True)
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
        return result, tmp, self.root / identity


class DraftPortraitDispositionTests(_DraftPortraitActivationMixin, EvenniaTest):
    """Custom activation keeps draft art; preset activation discards it."""

    def setUp(self):
        self.enterContext(stub_start_room())
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.enter_art_store()
        self.account = create_account(
            "portrait-owner", "portrait-owner@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="portrait-shell")
        self.account.at_post_create_character(self.character)

    def activate_custom(self, **overrides):
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(self.account, self.character, self.custom_request(**overrides))
        with self.count_enqueues() as enqueued:
            with self.captureOnCommitCallbacks(execute=True):
                activate_draft(self.account, self.character)
        return enqueued

    @covers_requirement(
        "art-gallery-autogen::every-player-activation-path-finalizes-the-portrait-lifecycle"
    )
    def test_custom_activation_keeps_a_ready_card_and_queues_no_duplicate(self):
        admission, path = self.ready_card()
        policy = dict(self.character.db.portrait_policy)
        enqueued = self.activate_custom()
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.card_ids(), [admission.image_id])
        self.assertEqual(self.default_image_id(), admission.image_id)
        self.assertTrue(path.exists())
        self.assertEqual(self.jobs(), [], "the guard sees the card: no enqueue")
        self.assertEqual(enqueued, [], "no second request reached the enqueue seam")
        self.assertEqual(dict(self.character.db.portrait_policy), policy)
        self.assertFalse(self.character.attributes.has("creation_portrait"))

    @covers_requirement(
        "art-gallery-autogen::every-player-activation-path-finalizes-the-portrait-lifecycle"
    )
    def test_custom_activation_keeps_in_flight_work_that_settles_afterwards(self):
        first, first_path = self.ready_card()
        pending = self.admit()
        description = self.jobs()[0].db.source_description
        enqueued = self.activate_custom(apparent_age=55, sex="male")
        self.assertEqual(self.job_ids(), [pending.image_id], "exactly the admitted job")
        self.assertEqual(self.jobs()[0].db.source_description, description)
        self.assertEqual(enqueued, [], "the in-flight job satisfies the guard")
        self.assertEqual(self.drain(), 1)
        # The late success settles on the same subject, replacing exactly the
        # retained creation card it was admitted against.
        self.assertEqual(self.card_ids(), [pending.image_id])
        self.assertEqual(self.default_image_id(), pending.image_id)
        self.assertFalse(first_path.exists())
        self.assertNotEqual(first.image_id, pending.image_id)

    def test_a_skipped_custom_activation_keeps_the_card_and_queues_nothing(self):
        # The skip flag is an activation request field, not part of the saved
        # draft, so the direct transport carries it explicitly.
        from world.rules.creation_wizard import save_custom_draft

        admission, path = self.ready_card()
        save_custom_draft(self.account, self.character, self.custom_request())
        with self.count_enqueues() as enqueued:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                activate_player_character(
                    self.account,
                    self.character,
                    self.custom_request(skip_portrait=True),
                )
        self.assertEqual(self.card_ids(), [admission.image_id])
        self.assertTrue(path.exists())
        self.assertEqual(self.jobs(), [])
        self.assertEqual(enqueued, [], "a skipped creation schedules nothing")
        self.assertEqual(
            _portrait_ensure_callbacks(callbacks), [], "no ensure is even registered"
        )

    def test_an_untouched_custom_activation_still_generates_once(self):
        enqueued = self.activate_custom()
        self.assertEqual(len(self.jobs()), 1)
        self.assertEqual(enqueued, [self.character], "ordinary creation auto-generates once")
        self.assertEqual(self.cards(), [])

    def test_nested_activation_reuses_the_one_held_serialization(self):
        from world.art import service
        from world.art.queue import queue_lock
        from world.rules import character_creation, creation_portrait
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        acquisitions = []
        arrivals = []
        ensures = []
        original_serialized = creation_portrait.serialized_gallery_mutation
        original_arrival = character_creation._run_start_arrival_effects
        original_ensure = service._ensure_gallery_subject

        @contextmanager
        def serialized_spy(subject):
            acquisitions.append(queue_lock.locked())
            with original_serialized(subject) as token:
                yield token

        def arrival_spy(*args):
            arrivals.append(queue_lock.locked())
            return original_arrival(*args)

        def ensure_spy(entity):
            ensures.append(queue_lock.locked())
            return original_ensure(entity)

        save_custom_draft(self.account, self.character, self.custom_request())
        with patch.object(
            creation_portrait, "serialized_gallery_mutation", serialized_spy
        ), patch.object(
            character_creation, "_run_start_arrival_effects", arrival_spy
        ), patch.object(service, "_ensure_gallery_subject", ensure_spy):
            with self.captureOnCommitCallbacks(execute=True):
                activate_draft(self.account, self.character)
        # The nested direct activation reuses its caller's unit: exactly one
        # queue acquisition, taken from an unheld state.
        self.assertEqual(acquisitions, [False])
        self.assertEqual(arrivals, [False], "arrival effects wait for the release")
        self.assertEqual(ensures, [False], "the ensure waits for the release")
        self.assertFalse(queue_lock.locked())

    def test_an_enclosing_transaction_is_rejected_before_serialization(self):
        from django.db import transaction

        from world.rules import creation_portrait
        from world.rules.creation_portrait import DraftPortraitMutationError

        with patch.object(creation_portrait, "serialized_gallery_mutation") as serialized:
            with transaction.atomic():
                with self.assertRaises(DraftPortraitMutationError):
                    activate_player_character(
                        self.account, self.character, self.custom_request()
                    )
        serialized.assert_not_called()
        self.assertTrue(self.character.creation_pending)

    def test_preset_activation_discards_creation_art_before_its_own_portrait(self):
        first, first_path = self.ready_card()
        pending = self.admit()
        job_key, token = self.claim_one()
        with self.captureOnCommitCallbacks() as callbacks:
            activate_player_character(
                self.account, self.character, self.preset_request()
            )
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.cards(), [])
        self.assertEqual(self.jobs(), [], "the creation job is canceled")
        self.assertTrue(first_path.exists(), "no unlink before the commit callbacks")
        with self.count_enqueues() as enqueued:
            for callback in callbacks:
                callback()
        self.assertFalse(first_path.exists())
        self.assertFalse(self.character.attributes.has("creation_portrait"))
        # The preset's normal source decided its portrait: nothing satisfies
        # it in the synthetic kit, so exactly one fresh automatic job.
        self.assertEqual(len(self.jobs()), 1)
        self.assertNotIn(self.job_ids()[0], {first.image_id, pending.image_id})
        self.assertFalse(self.jobs()[0].db.gallery_creation_draft)
        self.assertEqual(len(enqueued), 1, "one normal-source automatic request")
        # The canceled worker returns: nothing is published.
        result, tmp, target = self.settle_success(job_key, token)
        self.assertIsNone(result)
        self.assertFalse(tmp.exists())
        self.assertFalse(target.exists())
        self.assertEqual(self.cards(), [])

    def test_a_preset_activation_resolves_its_normal_official_portrait(self):
        from django.test import override_settings

        from world.art.official import load_catalog, reset_catalog
        from world.art.presenter import ORIGIN_OFFICIAL, describe_entity
        from world.rules.creation_wizard import activate_draft, save_preset_draft

        official_root = self.root / "official"
        folder = official_root / "preset" / _COMPANION_FREE_PRESET
        folder.mkdir(parents=True)
        (folder / "a.png").write_bytes(_png_bytes())
        settings = override_settings(ART_OFFICIAL_ROOT=str(official_root))
        settings.enable()
        self.addCleanup(settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        load_catalog()

        _, path = self.ready_card()
        save_preset_draft(self.account, self.character, _COMPANION_FREE_PRESET)
        with self.count_enqueues() as enqueued:
            with self.captureOnCommitCallbacks(execute=True):
                activate_draft(self.account, self.character)
        # The draft card is gone before the preset's own source is consulted.
        self.assertEqual(self.cards(), [])
        self.assertFalse(path.exists())
        self.assertFalse(self.character.attributes.has("creation_portrait"))
        # The preset's satisfied official source decides the portrait: no
        # automatic request is enqueued and the chain presents the official
        # image instead of the discarded custom one.
        self.assertEqual(enqueued, [], "an official default suppresses generation")
        self.assertEqual(self.jobs(), [])
        presented = _presented_resource(describe_entity(self.character))
        self.assertIsNotNone(presented)
        self.assertEqual(presented["origin"], ORIGIN_OFFICIAL)
        self.assertTrue(presented["url"].startswith("/art/official/"))

    def test_a_failure_after_cleanup_preserves_prior_art(self):
        for mode, stage in (
            ("preset", "draft_portrait"),
            ("preset", "portrait_policy"),
            ("custom", "draft_portrait"),
        ):
            with self.subTest(mode=mode, stage=stage):
                character = create_object(PlayerCharacter, key=f"shell-{mode}-{stage}")
                self.account.at_post_create_character(character)
                self.character = character
                admission, path = self.ready_card()
                pending = self.admit()
                receipt = dict(character.db.creation_portrait)
                policy = dict(character.db.portrait_policy)

                def fail(current, target=stage):
                    if current == target:
                        raise RuntimeError(target)

                request = (
                    self.preset_request() if mode == "preset" else self.custom_request()
                )
                with self.captureOnCommitCallbacks(execute=True) as callbacks:
                    with self.assertRaisesRegex(RuntimeError, stage):
                        activate_player_character(
                            self.account, character, request, write_observer=fail
                        )
                self.assertEqual(callbacks, [])
                self.assertTrue(character.creation_pending)
                self.assertEqual(dict(character.db.creation_portrait), receipt)
                self.assertEqual(dict(character.db.portrait_policy), policy)
                self.assertEqual(self.card_ids(), [admission.image_id])
                self.assertEqual(self.default_image_id(), admission.image_id)
                self.assertEqual(self.job_ids(), [pending.image_id])
                self.assertTrue(path.exists())

    def test_an_outer_commit_failure_preserves_prior_art(self):
        from types import SimpleNamespace

        from django.db import DatabaseError, transaction

        from world.rules.creation_wizard import activate_draft, save_preset_draft

        admission, path = self.ready_card()
        pending = self.admit()
        receipt = dict(self.character.db.creation_portrait)
        save_preset_draft(self.account, self.character, _COMPANION_FREE_PRESET)

        @contextmanager
        def failing_commit():
            with transaction.atomic():
                yield
                raise DatabaseError("injected commit failure")

        failing = SimpleNamespace(atomic=failing_commit, on_commit=transaction.on_commit)
        with patch("world.rules.creation_wizard.transaction", failing), patch(
            "world.rules.creation_portrait.unlink_creation_portrait_files"
        ) as unlink, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesRegex(DatabaseError, "injected commit failure"):
                activate_draft(self.account, self.character)
        unlink.assert_not_called()
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(dict(self.character.db.creation_portrait), receipt)
        self.assertEqual(self.card_ids(), [admission.image_id])
        self.assertEqual(self.job_ids(), [pending.image_id])
        self.assertTrue(path.exists())


def _run_on_own_connection(target, errors, results, name):
    """Run ``target`` on a thread with its own connection; record and join it."""

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


class _ProbedLock:
    """Delegate to one real lock and signal every acquisition attempt."""

    def __init__(self, lock, attempted):
        self._lock = lock
        self._attempted = attempted

    def __enter__(self):
        self._attempted.set()
        return self._lock.__enter__()

    def __exit__(self, *exc_info):
        return self._lock.__exit__(*exc_info)

    def acquire(self, *args, **kwargs):
        self._attempted.set()
        return self._lock.acquire(*args, **kwargs)

    def release(self):
        return self._lock.release()

    def locked(self):
        return self._lock.locked()


@contextmanager
def _probed_serialization(attempted):
    """Signal the serialized-mutation acquisition attempt, then acquire."""
    from world.rules import creation_portrait

    original = creation_portrait.serialized_gallery_mutation

    @contextmanager
    def probe(subject):
        attempted.set()
        with original(subject) as token:
            yield token

    with patch.object(creation_portrait, "serialized_gallery_mutation", probe):
        yield


class ActivationSettlementContentionTests(
    _DraftPortraitActivationMixin, TransactionTestCase
):
    """A real settling worker and activation, in both serialization orders.

    Django's atomic ``TestCase`` wrapper would hide the activation's committed
    rows from the worker's connection, so this class uses the documented
    ``TransactionTestCase`` precedent for transaction-semantics evidence. The
    barriers prove ordering and completion, never elapsed time.
    """

    def setUp(self):
        from typeclasses.rooms import Room
        from world.tests.start_room_fixture import STUB_START_ROOM_KEY

        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.enter_art_store()
        super().setUp()
        self.enterContext(stub_start_room())
        # Resolve the stub start room on this thread before any activation
        # thread runs, so the activation's placement is a pure read.
        create_object(Room, key=STUB_START_ROOM_KEY, nohome=True)
        self.account = create_account(
            "contended-owner",
            "contended@example.test",
            "testpassword",
            typeclass=Account,
        )
        self.character = create_object(PlayerCharacter, key="contended-shell")
        self.account.at_post_create_character(self.character)

    def outputs(self, job_key):
        """The (temporary, final) output paths and identity of one claimed job."""
        image_id = job_key.rsplit(":", 1)[1]
        identity = f"gallery/character/{self.character.pk}/{image_id}.png"
        tmp = self.root / f"tmp-{image_id}.png"
        tmp.write_bytes(_png_bytes())
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        return tmp, target, identity

    def settle(self, job_key, token, identity, tmp):
        from world.art.queue import settle_gallery_generated

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

    def observe_activation_entry(self, observed):
        """Patch the wizard's pre-transaction read to report when activation starts."""
        from world.rules import creation_wizard

        original = creation_wizard.snapshot_draft_portrait_state

        def snapshot(character):
            observed.set()
            return original(character)

        patcher = patch.object(
            creation_wizard, "snapshot_draft_portrait_state", snapshot
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return patcher

    def test_a_settled_card_survives_the_custom_activation_that_was_waiting(self):
        from world.art import gallery as gallery_api
        from world.art.queue import queue_lock
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(self.account, self.character, self.custom_request())
        admission = self.admit()
        job_key, token = self.claim_one()
        tmp, target, identity = self.outputs(job_key)
        blocker = _BlockingCall(gallery_api.append_replacement_card)
        self.addCleanup(blocker.release.set)
        started = threading.Event()
        attempted = threading.Event()
        self.observe_activation_entry(started)
        errors: list = []
        results: dict = {}
        with patch(
            "world.art.queue.gallery_api.append_replacement_card", blocker
        ), _probed_serialization(attempted):
            settle = _run_on_own_connection(
                lambda: self.settle(job_key, token, identity, tmp),
                errors,
                results,
                "settle",
            )
            self.assertTrue(blocker.entered.wait(20))
            activation = _run_on_own_connection(
                lambda: activate_draft(self.account, self.character),
                errors,
                results,
                "activate",
            )
            # The activation thread has reached the serialization point; the
            # worker still holds it, so the activation cannot pass.
            self.assertTrue(attempted.wait(20))
            activation.join(0.2)
            self.assertTrue(activation.is_alive())
            self.assertFalse(started.is_set())
            blocker.release.set()
            settle.join(20)
            activation.join(20)
        self.assertFalse(errors, errors)
        self.assertEqual(results["settle"]["image_id"], admission.image_id)
        # The settled card is the custom activation's portrait: it keeps it,
        # reuses the receipt's subject, and the guard enqueues nothing.
        self.assertEqual(self.card_ids(), [admission.image_id])
        self.assertEqual(self.default_image_id(), admission.image_id)
        self.assertTrue(target.exists())
        self.assertEqual(self.jobs(), [])
        self.assertFalse(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("creation_portrait"))
        self.assertFalse(queue_lock.locked())

    def test_a_settlement_before_preset_activation_is_then_removed(self):
        from world.art import gallery as gallery_api
        from world.art.queue import queue_lock
        from world.rules.creation_wizard import activate_draft, save_preset_draft

        save_preset_draft(self.account, self.character, _COMPANION_FREE_PRESET)
        admission = self.admit()
        job_key, token = self.claim_one()
        tmp, target, identity = self.outputs(job_key)
        blocker = _BlockingCall(gallery_api.append_replacement_card)
        self.addCleanup(blocker.release.set)
        started = threading.Event()
        attempted = threading.Event()
        self.observe_activation_entry(started)
        errors: list = []
        results: dict = {}
        with patch(
            "world.art.queue.gallery_api.append_replacement_card", blocker
        ), _probed_serialization(attempted):
            settle = _run_on_own_connection(
                lambda: self.settle(job_key, token, identity, tmp),
                errors,
                results,
                "settle",
            )
            self.assertTrue(blocker.entered.wait(20))
            activation = _run_on_own_connection(
                lambda: activate_draft(self.account, self.character),
                errors,
                results,
                "activate",
            )
            self.assertTrue(attempted.wait(20))
            activation.join(0.2)
            self.assertTrue(activation.is_alive())
            self.assertFalse(started.is_set())
            blocker.release.set()
            settle.join(20)
            activation.join(20)
        self.assertFalse(errors, errors)
        self.assertEqual(results["settle"]["image_id"], admission.image_id)
        # The preset activation removed the card the worker had just
        # published, and its file only after the commit callbacks ran.
        self.assertEqual(self.cards(), [])
        self.assertFalse(target.exists())
        self.assertFalse(self.character.attributes.has("creation_portrait"))
        # Its own normal source found nothing, so exactly one fresh automatic
        # request remains; the draft image never comes back.
        self.assertEqual(len(self.jobs()), 1)
        self.assertNotEqual(self.job_ids()[0], admission.image_id)
        self.assertFalse(self.jobs()[0].db.gallery_creation_draft)
        self.assertFalse(queue_lock.locked())

    def test_a_preset_activation_cancels_the_job_before_a_late_settlement(self):
        from world.art.queue import queue_lock
        from world.rules import creation_portrait
        from world.rules.creation_wizard import activate_draft, save_preset_draft

        save_preset_draft(self.account, self.character, _COMPANION_FREE_PRESET)
        admission = self.admit()
        job_key, token = self.claim_one()
        tmp, target, identity = self.outputs(job_key)
        blocker = _BlockingCall(creation_portrait.clear_draft_portrait)
        self.addCleanup(blocker.release.set)
        attempted = threading.Event()
        errors: list = []
        results: dict = {}
        with patch.object(
            creation_portrait, "clear_draft_portrait", blocker
        ), patch("world.art.queue.queue_lock", _ProbedLock(queue_lock, attempted)):
            activation = _run_on_own_connection(
                lambda: activate_draft(self.account, self.character),
                errors,
                results,
                "activate",
            )
            self.assertTrue(blocker.entered.wait(20))
            settle = _run_on_own_connection(
                lambda: self.settle(job_key, token, identity, tmp),
                errors,
                results,
                "settle",
            )
            # The worker has reached the queue acquisition the activation
            # holds; it cannot publish while the cleanup is in progress.
            self.assertTrue(attempted.wait(20))
            settle.join(0.2)
            self.assertTrue(settle.is_alive())
            blocker.release.set()
            activation.join(20)
            settle.join(20)
        self.assertFalse(errors, errors)
        # The canceled job's late return publishes nothing and discards its
        # temporary output.
        self.assertIsNone(results["settle"])
        self.assertFalse(tmp.exists())
        self.assertFalse(target.exists())
        self.assertEqual(self.cards(), [])
        self.assertFalse(self.character.attributes.has("creation_portrait"))
        self.assertEqual(len(self.jobs()), 1)
        self.assertNotEqual(self.job_ids()[0], admission.image_id)
        self.assertFalse(self.jobs()[0].db.gallery_creation_draft)
        self.assertFalse(queue_lock.locked())
