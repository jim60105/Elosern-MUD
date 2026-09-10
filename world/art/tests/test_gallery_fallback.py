"""Tests for the deterministic built-in fallback resolver (art-gallery-fallback).

Covers the closed vocabulary committed to the repository (contract test in
both directions, size bound, no tracked runtime art), the ordered resolution
rule (declared registry key -> monster constant -> sex/age band ->
deterministic subject-key hash), fail-closed behaviour on malformed stored
sex/apparent age, restart determinism of the hash, the filled seam payload
through the presenter (one ``gallery_fallback_used`` event, zero writes), and
the closed serving vocabulary of the ``/art/defaults/`` route branch.
"""

import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase

from world.art import gallery_fallback as gf
from world.art.fallback_keys import (
    FALLBACK_DEFAULTS_DIRECTORY,
    FALLBACK_EXTENSION,
    FALLBACK_KEYS,
    FALLBACK_MAX_FILE_BYTES,
    validate_fallback_key,
)
from world.art.gallery_fallback import fallback_key_for, resolve_fallback
from world.art.gallery_match import fallback_for
from world.art.presenter import resolve_subject
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULTS_DIR = REPO_ROOT / FALLBACK_DEFAULTS_DIRECTORY

# Non-runtime images the repository deliberately tracks: the desktop-redesign
# mockups under docs/design/ (player-facing documentation screenshots) and
# the webclient fixture samples under web/webclient-app/assets/ (Storybook/
# Vitest sample art). They are not part of the closed fallback vocabulary
# and are never served through the /art/defaults/ route; each path joins
# this exact set deliberately, in review, never by directory prefix.
APPROVED_NON_RUNTIME_IMAGES = frozenset(
    [
        "docs/design/elosern-redesign2/任務公會.webp",
        "docs/design/elosern-redesign2/戰鬥-技能清單.webp",
        "docs/design/elosern-redesign2/戰鬥.webp",
        "docs/design/elosern-redesign2/探索.webp",
        "docs/design/elosern-redesign2/探索互動.webp",
        "docs/design/elosern-redesign2/探索對話.webp",
        "docs/design/elosern-redesign2/等待休息.webp",
        "docs/design/elosern-redesign2/背包.webp",
        "docs/design/elosern-redesign2/角色.webp",
        "docs/design/elosern-redesign2/角色肖像圖庫管理頁-圖庫主畫面.webp",
        "docs/design/elosern-redesign2/角色肖像圖庫管理頁-生成新圖.webp",
        "docs/design/elosern-redesign2/角色肖像圖庫管理頁-臉部框選.webp",
        "docs/design/elosern-redesign2/角色肖像圖庫管理頁-裝備綁定.webp",
        "web/webclient-app/assets/redesign/sample-forest.webp",
        "web/webclient-app/assets/redesign/sample-guild.webp",
        "web/webclient-app/assets/redesign/sample-town.webp",
    ]
)



def _character(key):
    return ArtSubject(ArtSubjectKind.CHARACTER, key)


def _monster(key="low"):
    return ArtSubject(ArtSubjectKind.MONSTER, key)


def _scene(key="forest_path"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _entity(sex="other", apparent_age=30, **attributes):
    """A minimal stand-in carrying exactly what the resolver reads."""
    return SimpleNamespace(
        sex=sex,
        db=SimpleNamespace(apparent_age=apparent_age),
        attributes=SimpleNamespace(get=lambda key, **_kw: attributes.get(key)),
    )


class ClosedVocabularyContractTests(unittest.TestCase):
    @covers_requirement("art-gallery-fallback::the-built-in-fallback-set-is-a-closed-vocabulary-committed-to-the-repository")
    def test_every_key_has_exactly_one_committed_file_within_the_bound(self):
        files = sorted(p.name for p in DEFAULTS_DIR.iterdir() if p.is_file())
        expected = sorted(f"{key}{FALLBACK_EXTENSION}" for key in FALLBACK_KEYS)
        self.assertEqual(files, expected)
        for path in DEFAULTS_DIR.iterdir():
            self.assertLess(path.stat().st_size, FALLBACK_MAX_FILE_BYTES)

    @covers_requirement("art-gallery-fallback::the-built-in-fallback-set-is-a-closed-vocabulary-committed-to-the-repository")
    def test_no_stray_file_sits_in_the_defaults_directory(self):
        for path in DEFAULTS_DIR.iterdir():
            stem = path.name[: path.name.rindex(".")]
            self.assertIn(stem, FALLBACK_KEYS)

    @covers_requirement("art-gallery-fallback::the-built-in-fallback-set-is-a-closed-vocabulary-committed-to-the-repository")
    def test_only_the_defaults_directory_carries_tracked_images(self):
        tracked = subprocess_git_ls_files_images()
        # The closed runtime vocabulary is still exclusive: the defaults
        # directory plus the explicitly reviewed documentation/fixture
        # images. A new tracked image outside this exact set fails here.
        self.assertEqual(
            tracked,
            {f"{FALLBACK_DEFAULTS_DIRECTORY}/{k}{FALLBACK_EXTENSION}" for k in FALLBACK_KEYS}
            | APPROVED_NON_RUNTIME_IMAGES,
        )


def subprocess_git_ls_files_images():
    import subprocess

    out = subprocess.run(
        [
            "git",
            "-c",
            "core.quotepath=off",
            "-C",
            str(REPO_ROOT),
            "ls-files",
            "*.png",
            "*.webp",
            "*.jpg",
            "*.avif",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return set(out.split())


class RegistryDeclarationTests(unittest.TestCase):
    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_a_declared_key_wins_over_the_band_rule(self):
        fake = SimpleNamespace(fallback_key="elder")
        entity = _entity(sex="female", apparent_age=30, creation_preset_key="declared_p")
        with patch.dict(gf.PLAYER_PRESET_REGISTRY, {"declared_p": fake}):
            self.assertEqual(
                fallback_key_for(_character("anyone"), entity),
                "elder",
            )

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_a_monster_tier_declaration_wins_over_the_constant(self):
        fake = SimpleNamespace(fallback_key="elder")
        with patch.dict(gf.MONSTER_TIER_REGISTRY, {"low": fake}):
            self.assertEqual(fallback_key_for(_monster("low"), None), "elder")

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_an_invalid_declared_key_raises_at_construction_time(self):
        from world.lore.npc_tiers import _validate_npc_tier_fallback_keys

        fake = SimpleNamespace(key="guard", fallback_key="teenager")
        with self.assertRaises(ValueError):
            _validate_npc_tier_fallback_keys({"guard": fake})
        with self.assertRaises(ValueError):
            validate_fallback_key("nope", "preset x")
        validate_fallback_key(None, "preset x")  # absence is legal

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_a_malformed_runtime_declaration_degrades_to_the_band_rule(self):
        fake = SimpleNamespace(fallback_key="not-a-key")
        entity = _entity(sex="male", apparent_age=30, creation_preset_key="bad_p")
        with patch.dict(gf.PLAYER_PRESET_REGISTRY, {"bad_p": fake}):
            self.assertEqual(fallback_key_for(_character("anyone"), entity), "man")


class BandRuleTests(unittest.TestCase):
    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_bands_and_sexes_resolve_their_keys(self):
        cases = [
            ("female", 30, "woman"),
            ("male", 30, "man"),
            ("female", 8, "girl"),
            ("male", 8, "boy"),
            ("female", 75, "elder"),
            ("male", 75, "elder"),
        ]
        for sex, apparent_age, key in cases:
            with self.subTest(sex=sex, apparent_age=apparent_age):
                entity = _entity(sex=sex, apparent_age=apparent_age)
                self.assertEqual(fallback_key_for(_character("band"), entity), key)

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_monsters_resolve_the_constant(self):
        self.assertEqual(fallback_key_for(_monster("low"), None), "monster_anon")
        self.assertEqual(fallback_key_for(_monster("calamity"), None), "monster_anon")

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_a_sex_outside_the_pair_hashes_into_its_band_pool(self):
        entity = _entity(sex="other", apparent_age=30)
        first = fallback_key_for(_character("poolcheck"), entity)
        self.assertIn(first, ("man", "woman"))
        self.assertEqual(first, fallback_key_for(_character("poolcheck"), entity))

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_the_hash_is_a_pure_function_of_the_full_subject_key(self):
        # Re-derived by hand: pins sha256-over-full-key modulo pool order, so
        # the mapping survives any module reload (simulated restart).
        pool = ("man", "woman")
        full = _character("poolcheck").full()
        digest = hashlib.sha256(full.encode("utf-8")).digest()
        expected = pool[int.from_bytes(digest, "big") % len(pool)]
        self.assertEqual(
            fallback_key_for(_character("poolcheck"), _entity(sex="other")), expected
        )

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_malformed_sex_or_age_fail_closed_to_the_adult_band(self):
        for sex in (None, 17, "", ["female"]):
            with self.subTest(sex=sex):
                entity = _entity(sex=sex, apparent_age=30)
                self.assertIn(fallback_key_for(_character("fc"), entity), ("man", "woman"))
        for age in (None, "thirty", 30.5, True):
            with self.subTest(age=age):
                key = fallback_key_for(_character("fc"), _entity(sex="other", apparent_age=age))
                self.assertIn(key, ("man", "woman"))

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_no_entity_fails_closed_to_the_adult_band(self):
        self.assertIn(fallback_key_for(_character("ghost"), None), ("man", "woman"))


class SeamPayloadTests(EvenniaTestCase):
    @covers_requirement("art-gallery-fallback::the-fallback-seam-supplies-a-url-and-a-face-rectangle-and-reports-its-use")
    def test_the_presenter_resolves_a_fallback_image_and_logs_one_event(self):
        subject = _character("fallbackhero")
        with patch("world.observability.log_info") as logged:
            payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], "asset")
        self.assertTrue(payload["url"].startswith("/art/defaults/"))
        self.assertTrue(payload["url"].endswith(FALLBACK_EXTENSION))
        rect = payload["face_rect"]
        self.assertEqual(sorted(rect), ["h", "w", "x", "y"])
        self.assertTrue(all(0.0 <= rect[f] <= 1.0 for f in ("x", "y", "w", "h")))
        events = [c for c in logged.call_args_list if c.args and c.args[0] == "gallery_fallback_used"]
        self.assertEqual(len(events), 1)
        context = events[0].kwargs["context"]
        self.assertEqual(context["subject"], subject.full())
        self.assertEqual(context["kind"], ArtSubjectKind.CHARACTER.value)
        self.assertIn(context["key"], FALLBACK_KEYS)

    @covers_requirement("art-gallery-fallback::the-fallback-seam-supplies-a-url-and-a-face-rectangle-and-reports-its-use")
    def test_the_fallback_writes_no_record_and_no_card(self):
        from world.art.gallery import GalleryRecord, record_key

        subject = _character("writenothing")
        with patch("world.observability.log_info"):
            fallback_for(subject)
        self.assertIsNone(GalleryRecord.objects.filter(db_key=record_key(subject)).first())

    @covers_requirement("art-gallery-fallback::the-fallback-seam-supplies-a-url-and-a-face-rectangle-and-reports-its-use")
    def test_a_scene_subject_still_falls_through_to_the_placeholder(self):
        with patch("world.observability.log_info"):
            self.assertIsNone(resolve_fallback(_scene()))

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_an_ambiguous_shared_stable_key_fails_closed_without_an_entity(self):
        # Two living entities legally sharing one stable portrait key make a
        # subject-only recovery ambiguous: no entity may be guessed, so the
        # band rule closes deterministically on the adult pool. Provenance is
        # never selected from an arbitrary DB row.
        from evennia.utils.create import create_object
        from typeclasses.npcs import NPC

        policy = {"mode": "named", "stable_key": "shared_twin"}
        first = create_object(NPC, key="twin-a")
        second = create_object(NPC, key="twin-b")
        for entity in (first, second):
            entity.db.portrait_policy = policy
            entity.db.apparent_age = 30
        subject = _character("shared_twin")
        with patch("world.observability.log_info"):
            resolution = resolve_fallback(subject)
        self.assertIn(resolution["key"], ("man", "woman"))
        # A unique carrier is recovered deterministically (elder band here).
        first.db.portrait_policy = None
        second.db.apparent_age = 75
        from world.art.gallery_fallback import _entity_for_character_subject

        self.assertIs(_entity_for_character_subject(subject), second)


class DefaultsRouteVocabularyTests(EvenniaTestCase):
    @covers_requirement("art-gallery-fallback::the-built-in-fallback-set-is-a-closed-vocabulary-committed-to-the-repository")
    def test_the_route_serves_every_committed_image_with_its_media_type(self):
        from django.test import Client

        static_root = REPO_ROOT / "web" / "static"
        with override_settings(STATICFILES_DIRS=[str(static_root)]):
            for key in FALLBACK_KEYS:
                with self.subTest(key=key):
                    response = Client().get(f"/art/defaults/{key}{FALLBACK_EXTENSION}")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response["Content-Type"], "image/webp")

    @covers_requirement("art-gallery-fallback::the-built-in-fallback-set-is-a-closed-vocabulary-committed-to-the-repository")
    def test_the_route_refuses_an_out_of_vocabulary_stem(self):
        from django.test import Client

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            defaults = Path(tmp) / "art" / "defaults"
            defaults.mkdir(parents=True)
            (defaults / "stray.webp").write_bytes(b"x")
            with override_settings(STATICFILES_DIRS=[tmp]):
                self.assertEqual(Client().get("/art/defaults/stray.webp").status_code, 404)


if __name__ == "__main__":
    unittest.main()
