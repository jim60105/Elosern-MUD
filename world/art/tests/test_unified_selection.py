"""Focused regressions for the one capability-driven artwork selection chain.

``unify-artwork-selection`` turns the gallery chain into the only source
selection policy for every gallery-bearing kind. These tests establish the
behavior the delta specs require without pinning shipped content: synthetic
scene/species registries, temporary official/store roots, a tiny decodable
image and the deterministic fake image client.

They cover the startup suppression gap (a bare registry subject with a valid
official default must not mint a card), refused and substituted defaults,
bounded-URL admission, manual generation remaining available, capped
replacement success/failure, explicit official selection retention, and a
redeclared kind following its declaration rather than a kind comparison.
"""

import base64
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase

from world.art import descriptors, gallery as gallery_api, gallery_kinds, official
from world.art import gallery_match, service, worker
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.gallery_match import (
    official_default_for,
    official_selection_for,
    resolve_display,
)
from world.art.official import load_catalog, reset_catalog
from world.art.presenter import _slot_source, describe_portrait
from world.art.queue import (
    claim,
    enqueue_gallery_job,
    gallery_record_key,
    record_key as classic_record_key,
    settle_gallery_failed,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import (
    ArtSubject,
    ArtSubjectKind,
    monster_subject_for,
    scene_subject_for,
)
from world.tests.synthetic_data import SYNTH_ARCHETYPES, synthetic_registries
from tools.spec_traceability import covers_requirement

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

class UnifiedSelectionTests(EvenniaTestCase):
    """Behavioral regressions for the unified chain (at most twelve methods)."""

    def setUp(self):
        scope = synthetic_registries("archetypes", "monster_tiers")
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        super().setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / "store"
        self.official_root = self.root / "official"
        self.seed = self.root / "seed"
        self.store.mkdir()
        self.seed.mkdir()
        self.settings = override_settings(
            ART_STORE_ROOT=str(self.store),
            ART_OFFICIAL_ROOT=str(self.official_root),
            ART_SEED_ROOT=str(self.seed),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        from world.lore.monster_visuals import get_monster_visual_registry

        self.scene_key = sorted(SYNTH_ARCHETYPES)[0]
        self.species_key = sorted(get_monster_visual_registry())[0]

    # -- harness ---------------------------------------------------------
    def _index(self, kind: str, key: str, name: str = "a.png", manifest=None) -> str:
        folder = self.official_root / kind / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_TINY_PNG)
        if manifest is not None:
            (folder / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
        load_catalog()
        return f"{kind}/{key}/{name}"

    def _subject(self, kind: ArtSubjectKind, key: str) -> ArtSubject:
        return (
            scene_subject_for(key)
            if kind is ArtSubjectKind.SCENE
            else monster_subject_for(key)
        )

    def _subject_jobs(self, subject: ArtSubject) -> list:
        prefix = f"art:{subject.full()}:gen:"
        return [
            record
            for record in ArtAssetRecord.objects.filter(db_key__startswith=prefix)
            if str(record.db.gallery_image_id or "")
        ]

    def _store_card(self, subject: ArtSubject) -> str:
        image_id = str(uuid.uuid4())
        identity = f"gallery/{subject.kind.value.split(':')[-1]}/{subject.key}/{image_id}.png"
        if subject.kind is ArtSubjectKind.SCENE:
            identity = f"gallery/scene/{subject.key}/{image_id}.png"
        path = self.store / identity
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic-card")
        gallery_api.append_card(
            subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="generated",
            image_size={"width": 16, "height": 9},
        )
        return identity

    def _drain(self, limit=20):
        with patch(
            "world.art.worker.resolve_sd_client", return_value=FakeSDWebUIClient()
        ):
            worker.drain_synchronous(limit)

    # -- suppression -----------------------------------------------------
    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_bare_startup_subjects_suppress_without_state_prompt_or_job(self):
        self._index("scene", self.scene_key)
        self._index("monster", self.species_key)
        scene = scene_subject_for(self.scene_key)
        species = monster_subject_for(self.species_key)
        with patch(
            "world.art.sd_worker.render_prompt_pair",
            return_value=("positive", "negative"),
        ) as render:
            service.art_sync_all()
        for subject in (scene, species):
            with self.subTest(subject=subject.full()):
                self.assertEqual(self._subject_jobs(subject), [])
                self.assertIsNone(gallery_api.record_for(subject))
                self.assertIsNone(
                    ArtAssetRecord.objects.filter(
                        db_key=classic_record_key(subject)
                    ).first()
                )
        prompted = [
            call.args[0]
            for call in render.call_args_list
            if call.args and call.args[0] in (scene, species)
        ]
        self.assertEqual(prompted, [])

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_a_refused_default_does_not_suppress(self):
        folder = self.official_root / "scene" / self.scene_key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "broken.png").write_bytes(b"not an image")
        load_catalog()
        subject = scene_subject_for(self.scene_key)
        with patch(
            "world.art.sd_worker.render_prompt_pair",
            return_value=("positive", "negative"),
        ):
            self.assertTrue(service._ensure_gallery_subject(subject))
        self.assertEqual(len(self._subject_jobs(subject)), 1)
        self.assertIsNone(official_default_for(subject))

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    @covers_requirement(
        "art-source-fault-facts::faults-are-attributed-to-requested-sources"
    )
    def test_a_substituted_manifest_default_satisfies_while_keeping_its_fault(self):
        identity = self._index(
            "scene", self.scene_key, manifest={"default": "missing.png"}
        )
        subject = scene_subject_for(self.scene_key)
        facts = official_default_for(subject)
        self.assertEqual(facts["identity"], identity)
        faults = official.current_catalog().source_faults("scene", self.scene_key)
        self.assertTrue(
            any(
                fault.scope == official.SOURCE_SCOPE_DEFAULT
                and fault.identity == f"scene/{self.scene_key}/missing.png"
                for fault in faults
            ),
            faults,
        )
        with patch(
            "world.art.sd_worker.render_prompt_pair",
            return_value=("positive", "negative"),
        ):
            self.assertFalse(service._ensure_gallery_subject(subject))
        self.assertEqual(self._subject_jobs(subject), [])

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_an_over_budget_official_default_does_not_suppress(self):
        name = "d" * 200 + ".png"
        self._index("scene", self.scene_key, name=name)
        subject = scene_subject_for(self.scene_key)
        self.assertGreater(len(official.current_catalog().url_for(
            f"scene/{self.scene_key}/{name}"
        )), gallery_match.descriptors.MAX_MEDIA_URL)
        with patch("world.art.gallery_match.log_warn") as warned, patch(
            "world.art.sd_worker.render_prompt_pair",
            return_value=("positive", "negative"),
        ):
            self.assertTrue(service._ensure_gallery_subject(subject))
        self.assertEqual(len(self._subject_jobs(subject)), 1)
        events = [call.args[0] for call in warned.call_args_list if call.args]
        self.assertEqual(events.count("art_official_url_over_wire_budget"), 1)

    # -- manual generation and replacement -------------------------------
    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_manual_generation_bypasses_suppression_and_settles_a_runtime_card(self):
        self._index("scene", self.scene_key)
        subject = scene_subject_for(self.scene_key)
        self.assertFalse(service._ensure_gallery_subject(subject))
        image_id = service.request_gallery_image(subject)
        self.assertEqual(len(self._subject_jobs(subject)), 1)
        self._drain(1)
        cards = gallery_api.cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [image_id])
        self.assertEqual(
            gallery_api.record_for(subject).db.default_image_id, image_id
        )

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_successful_capped_replacement_replaces_card_default_and_file(self):
        subject = monster_subject_for(self.species_key)
        old_identity = self._store_card(subject)
        old_file = self.store / old_identity
        new_identity = self._store_card(subject)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["stored_identity"], new_identity)
        self.assertEqual(
            gallery_api.record_for(subject).db.default_image_id,
            cards[0]["image_id"],
        )
        self.assertFalse(old_file.exists())

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_failed_capped_replacement_keeps_the_previous_card_and_bytes(self):
        subject = monster_subject_for(self.species_key)
        identity = self._store_card(subject)
        image_id = gallery_api.cards_for(subject)[0]["image_id"]
        enqueue_gallery_job(
            subject,
            "synthetic scene description",
            image_id=image_id,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        job = next(
            record
            for record in claim(ArtAssetRecord.objects.count() + 1)
            if record.db.gallery_image_id == image_id
        )
        settle_gallery_failed(
            gallery_record_key(subject, image_id),
            generation_token=str(job.db.generation_token),
            error="sd_connection_error",
        )
        cards = gallery_api.cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [image_id])
        self.assertEqual(
            gallery_api.record_for(subject).db.default_image_id, image_id
        )
        self.assertTrue((self.store / identity).exists())

    # -- preference ownership and declaration-driven policy --------------
    @covers_requirement(
        "official-art-personalization::a-personal-official-selection-is-an-entity-local-art-preference"
    )
    def test_explicit_selection_survives_replacement_and_failure(self):
        subject = scene_subject_for(self.scene_key)
        identity = self._index("scene", self.scene_key)
        gallery_api.set_official_selection(subject, identity)
        first = self._store_card(subject)
        self.assertEqual(
            gallery_api.official_preferences_for(subject).selection, identity
        )
        self.assertEqual(
            gallery_api.record_for(subject).db.default_image_id,
            gallery_api.cards_for(subject)[0]["image_id"],
        )
        second = self._store_card(subject)
        self.assertNotEqual(first, second)
        self.assertEqual(
            gallery_api.official_preferences_for(subject).selection, identity
        )
        gallery_api.record_error(subject, "sd_connection_error")
        self.assertEqual(
            gallery_api.official_preferences_for(subject).selection, identity
        )
        self.assertEqual(official_selection_for(subject)["identity"], identity)

    @covers_requirement(
        "art-gallery-resolution::monster-subjects-resolve-through-the-chain-without-the-binding-steps"
    )
    def test_a_redeclared_kind_follows_its_declaration_not_a_kind_comparison(self):
        subject = scene_subject_for(self.scene_key)
        identity = self._index("scene", self.scene_key)
        gallery_api.set_official_selection(subject, identity)
        self._store_card(subject)
        undeclared = gallery_kinds.capabilities_for(
            subject.kind.value
        ).with_values(supports_bindings=False, terminal_policy="none")

        def explode(*args, **kwargs):  # pragma: no cover - must never run
            raise AssertionError("a non-binding kind must not compute a snapshot")

        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {subject.kind.value: undeclared},
        ), patch("world.art.gallery_match.snapshot_for", side_effect=explode):
            outcome, facts = resolve_display(subject, None)
        self.assertEqual(outcome, "official")
        self.assertEqual(facts["identity"], identity)

    @covers_requirement(
        "art-gallery-resolution::the-chain-ends-at-one-fallback-seam"
    )
    def test_the_terminal_adapter_follows_the_declared_terminal_policy(self):
        subject = ArtSubject(ArtSubjectKind.CHARACTER, "t_synth_terminal")
        capability = gallery_kinds.capabilities_for(subject.kind.value)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {subject.kind.value: capability.with_values(terminal_policy="none")},
        ):
            self.assertIsNone(describe_portrait(subject)["terminal"])
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {subject.kind.value: capability.with_values(terminal_policy="alpha")},
        ):
            terminal = describe_portrait(subject)["terminal"]
        self.assertEqual(terminal["kind"], "alpha_mask")
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {subject.kind.value: capability.with_values(terminal_policy="scene")},
        ):
            self.assertIsNone(describe_portrait(subject)["terminal"])

    def test_long_official_fault_source_ids_stay_inside_the_wire_bound(self):
        identity = "scene/" + "d" * 220 + "/a.png"
        for layer in ("personal", "official"):
            source_id, _rank = _slot_source(layer, identity)
            self.assertLessEqual(len(source_id), descriptors.MAX_SOURCE_ID)


if __name__ == "__main__":
    unittest.main()
