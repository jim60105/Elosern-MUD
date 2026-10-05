"""Tests for the deterministic gallery display chain (art-gallery-resolution).

Covers the four character-side steps (snapshot match, most-specific mask,
newest-``created_at`` tie-break, explicit default), the unbound-card rule,
the monster variant with no snapshot computation, identity validation skips
(vanished file, foreign subject, out-of-root, symlink), the terminal seam,
the official-default step (a preset-born entity's registered content reference
resolving the startup snapshot's default image, every absent/unregistered/
removed/monster case falling through, and the step's read-only purity), and
the module's connectivity/write-free import discipline.
"""

import ast
import io
import json
import shutil
import socket
import tempfile
from pathlib import Path
import time
from contextlib import ExitStack
from unittest.mock import patch
import uuid
import unittest

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase
from PIL import Image

from world.art import gallery_kinds, official, official_refs
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    GalleryRecord,
    append_card,
    cards_for,
    record_for,
    record_key,
    set_default,
)
from world.art.gallery_match import (
    fallback_for,
    official_default_for,
    resolve_card,
    validated_card_identity,
)
from world.art.official import (
    OfficialCatalog,
    OfficialContent,
    OfficialImage,
    current_catalog,
    load_catalog,
    reset_catalog,
)
from world.art.official_refs import (
    PRESET_PROVENANCE_ATTRIBUTE,
    UNRESOLVED_REFERENCE_EVENT,
)
from world.art.store import ArtAssetRecord
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]


def _character(key="chainhero"):
    return ArtSubject(ArtSubjectKind.CHARACTER, key)


def _monster(key="chaingoblin"):
    return ArtSubject(ArtSubjectKind.MONSTER, key)


# Fallback matching is subject-key mechanics; a file-local synthetic scene
# identity keeps the suite independent of the shipped archetype vocabulary.
def _scene(key="t_synth_scene"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _new_id():
    return str(uuid.uuid4())


def _identity(subject, image_id, extension=".png"):
    kind_dir = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
    return f"gallery/{kind_dir}/{subject.key}/{image_id}{extension}"


def _card_fields(subject, image_id=None, **overrides):
    image_id = image_id or _new_id()
    fields = {
        "image_id": image_id,
        "stored_identity": _identity(subject, image_id),
        "prompt": {"positive": "a hero", "negative": "blur"},
        "seed": 1234,
        "checkpoint": "realVision.safetensors",
        # Declaration-aware: a kind without field-selection support stores an
        # empty provenance only (write-boundary rule, ``gallery-monster-generation``).
        "requested_fields": (
            ["appearance"]
            if gallery_kinds.capabilities_for(subject.kind.value).supports_field_selection
            else []
        ),
        "binding": None,
        "source": "generated",
        "image_size": {"width": 1000, "height": 1000},
    }
    fields.update(overrides)
    return fields


class _FakeDb:
    """Minimal ``entity.db`` namespace: reads return the stored value/None."""

    def __init__(self, values=None):
        self._values = dict(values or {})

    def __getattr__(self, name):
        return self._values.get(name)

    def get(self, name, default=None):
        return self._values.get(name, default)


class _FakeEntity:
    def __init__(self, equipment=None):
        self.db = _FakeDb({"equipment": equipment} if equipment is not None else {})


def _binding(mask, snapshot):
    return {"mask": mask, "snapshot": snapshot}


class _ChainBase(EvenniaTestCase):
    """Shared temp-store harness: cards need their files present on disk."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _make_file(self, identity):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        return target

    def _append_present(self, subject, **overrides):
        """Append one card whose stored file exists; returns (image_id, fields)."""
        fields = _card_fields(subject, **overrides)
        self._make_file(fields["stored_identity"])
        append_card(subject, **fields)
        return fields["image_id"]

    def _set_created_at(self, subject, image_id, created_at):
        record = record_for(subject)
        cards = [dict(card) for card in record.db.cards]
        for card in cards:
            if card["image_id"] == image_id:
                card["created_at"] = created_at
        record.db.cards = cards


class ChainBindingTests(_ChainBase):
    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_the_most_specific_matching_binding_wins(self):
        subject = _character("specific")
        entity = _FakeEntity(
            {"weapon_main": "short_sword", "armor": "leather_vest"}
        )
        broad = self._append_present(
            subject,
            binding=_binding(["armor"], {"armor": "leather_vest"}),
        )
        narrow = self._append_present(
            subject,
            binding=_binding(
                ["weapon_main", "armor"],
                {"weapon_main": "short_sword", "armor": "leather_vest"},
            ),
        )
        self.assertEqual(
            resolve_card(subject, entity)["image_id"],
            narrow,
            f"expected two-slot card {narrow}, got {broad}",
        )

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_an_equal_specificity_tie_resolves_to_the_newest_card(self):
        subject = _character("tiebreak")
        entity = _FakeEntity({"armor": "leather_vest"})
        older = self._append_present(
            subject, binding=_binding(["armor"], {"armor": "leather_vest"})
        )
        newer = self._append_present(
            subject, binding=_binding(["armor"], {"armor": "leather_vest"})
        )
        now = time.time()
        self._set_created_at(subject, older, now - 100)
        self._set_created_at(subject, newer, now - 1)
        self.assertEqual(resolve_card(subject, entity)["image_id"], newer)
        self._set_created_at(subject, older, now + 1)
        self._set_created_at(subject, newer, now - 1)
        self.assertEqual(resolve_card(subject, entity)["image_id"], older)

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_a_binding_over_empty_slots_matches_an_unequipped_entity(self):
        subject = _character("emptyward")
        bare = self._append_present(
            subject, binding=_binding(["armor"], {"armor": None})
        )
        entity = _FakeEntity()  # no stored equipment at all
        self.assertEqual(resolve_card(subject, entity)["image_id"], bare)
        wearing = _FakeEntity({"armor": "plate_harness"})
        resolved = resolve_card(subject, wearing)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["image_id"], bare, "unmasked slots are don't-cares")

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_changing_equipment_changes_the_resolved_card_without_a_write(self):
        subject = _character("swapper")
        first = self._append_present(
            subject, binding=_binding(["armor"], {"armor": "leather_vest"})
        )
        second = self._append_present(
            subject, binding=_binding(["armor"], {"armor": "plate_harness"})
        )
        cards_before = record_for(subject).db.cards
        self.assertEqual(
            resolve_card(subject, _FakeEntity({"armor": "leather_vest"}))["image_id"],
            first,
        )
        self.assertEqual(
            resolve_card(subject, _FakeEntity({"armor": "plate_harness"}))["image_id"],
            second,
        )
        self.assertEqual(record_for(subject).db.cards, cards_before)

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_no_binding_match_falls_through_to_the_default(self):
        subject = _character("fallthrough")
        fallback_default = self._append_present(subject)  # first append = default
        bound = self._append_present(
            subject, binding=_binding(["armor"], {"armor": "plate_harness"})
        )
        resolved = resolve_card(subject, _FakeEntity({"armor": "leather_vest"}))
        self.assertEqual(resolved["image_id"], fallback_default)
        # Once the bound card actually matches, it beats the default.
        self.assertEqual(
            resolve_card(subject, _FakeEntity({"armor": "plate_harness"}))["image_id"],
            bound,
        )


class UnboundCardTests(_ChainBase):
    @covers_requirement(
        "art-gallery-resolution::an-unbound-card-is-never-auto-selected"
    )
    def test_unbound_cards_without_a_default_are_never_shown(self):
        subject = _character("unbound")
        self._append_present(subject)
        self._append_present(subject)
        record = record_for(subject)
        record.db.default_image_id = None
        self.assertEqual(len(cards_for(subject)), 2)
        self.assertIsNone(resolve_card(subject, _FakeEntity()))

    @covers_requirement(
        "art-gallery-resolution::an-unbound-card-is-never-auto-selected"
    )
    def test_an_unbound_card_set_as_default_is_shown(self):
        subject = _character("unbounddefault")
        unbound = self._append_present(subject)
        self._append_present(
            subject, binding=_binding(["armor"], {"armor": "plate_harness"})
        )
        set_default(subject, unbound)
        resolved = resolve_card(subject, _FakeEntity({"armor": "leather_vest"}))
        self.assertEqual(resolved["image_id"], unbound)


class MonsterChainTests(_ChainBase):
    @covers_requirement(
        "art-gallery-resolution::monster-subjects-resolve-through-the-chain-without-the-binding-steps"
    )
    def test_a_monster_resolves_its_single_card_with_no_equipment_read(self):
        subject = _monster("snapshotless")
        card_id = self._append_present(subject)

        def explode(*args, **kwargs):  # pragma: no cover - must never run
            raise AssertionError("no equipment snapshot may be computed for a monster")

        with patch("world.art.gallery_match.snapshot_for", side_effect=explode):
            resolved = resolve_card(subject, _FakeEntity({"armor": "plate_harness"}))
        self.assertEqual(resolved["image_id"], card_id)

    @covers_requirement(
        "art-gallery-resolution::monster-subjects-resolve-through-the-chain-without-the-binding-steps"
    )
    def test_a_monster_with_no_card_resolves_to_nothing(self):
        self.assertIsNone(resolve_card(_monster("bare"), _FakeEntity()))

    @covers_requirement(
        "art-gallery-resolution::monster-subjects-resolve-through-the-chain-without-the-binding-steps"
    )
    def test_the_binding_skip_follows_the_declaration_not_the_kind(self):
        # A CHARACTER whose declaration is patched to drop binding support
        # must resolve through the chain with the binding steps skipped — no
        # snapshot computation — landing on the explicit default.
        subject = _character("declaredskip")
        unbound_default = self._append_present(subject)
        self._append_present(
            subject, binding=_binding(["armor"], {"armor": "leather_vest"})
        )
        unbound = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.CHARACTER.value
        ].with_values(supports_bindings=False)

        def explode(*args, **kwargs):
            raise AssertionError("snapshot computation must not run")

        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.CHARACTER.value: unbound},
        ), patch("world.art.gallery_match.snapshot_for", side_effect=explode):
            resolved = resolve_card(subject, _FakeEntity({"armor": "leather_vest"}))
        self.assertEqual(resolved["image_id"], unbound_default)

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_a_scene_subject_resolves_to_nothing(self):
        self.assertIsNone(resolve_card(_scene(), _FakeEntity()))


class IdentitySkipTests(_ChainBase):
    @covers_requirement(
        "art-gallery-resolution::gallery-urls-are-built-only-from-validated-card-identities"
    )
    def test_a_card_whose_file_vanished_is_skipped_and_the_chain_continues(self):
        subject = _character("vanished")
        default_id = self._append_present(subject)
        bound_identity = _identity(subject, _new_id())
        bound_id = str(uuid.UUID(Path(bound_identity).stem))
        self._make_file(bound_identity)
        append_card(
            subject,
            **_card_fields(
                subject,
                image_id=bound_id,
                stored_identity=bound_identity,
                binding=_binding(["armor"], {"armor": "plate_harness"}),
            ),
        )
        entity = _FakeEntity({"armor": "plate_harness"})
        # Default to the newest-created bound card? No — default is the FIRST
        # card; make the bound card win the binding step first, then delete it.
        self.assertEqual(resolve_card(subject, entity)["image_id"], bound_id)
        (self.root / bound_identity).unlink()
        resolved = resolve_card(subject, entity)
        self.assertEqual(resolved["image_id"], default_id)
        with patch("world.art.gallery_match.log_debug") as debug:
            resolve_card(subject, entity)
        events = [
            c
            for c in debug.call_args_list
            if c.args and c.args[0] == "gallery_card_skipped"
        ]
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["reason"], "referenced file is missing")

    @covers_requirement(
        "art-gallery-resolution::gallery-urls-are-built-only-from-validated-card-identities"
    )
    def test_a_symlinked_card_file_is_skipped(self):
        subject = _character("symlinked")
        default_id = self._append_present(subject)
        fields = _card_fields(
            subject, binding=_binding(["armor"], {"armor": "plate_harness"})
        )
        target = self.root / fields["stored_identity"]
        target.parent.mkdir(parents=True, exist_ok=True)
        external = Path(self.tempdir.name).parent / "chain-precious.png"
        external.write_bytes(b"do not serve")
        target.symlink_to(external)
        append_card(subject, **fields)
        resolved = resolve_card(subject, _FakeEntity({"armor": "plate_harness"}))
        self.assertEqual(resolved["image_id"], default_id)
        self.assertTrue(external.exists())

    @covers_requirement(
        "art-gallery-resolution::gallery-urls-are-built-only-from-validated-card-identities"
    )
    def test_validated_card_identity_rejects_every_malformed_identity(self):
        subject = _character("identityguard")
        image_id = _new_id()
        self._make_file(_identity(subject, image_id))
        cases = {
            "foreign subject": {
                "image_id": image_id,
                "stored_identity": f"gallery/character/someone-else/{image_id}.png",
            },
            "foreign kind directory": {
                "image_id": image_id,
                "stored_identity": f"gallery/monster/{subject.key}/{image_id}.png",
            },
            "non-store extension": {
                "image_id": image_id,
                "stored_identity": f"gallery/character/{subject.key}/{image_id}.jxl",
            },
            "traversal": {
                "image_id": image_id,
                "stored_identity": f"gallery/character/{subject.key}/../../outside.png",
            },
            "non-text identity": {"image_id": image_id, "stored_identity": 42},
        }
        for reason, card in cases.items():
            with self.subTest(reason=reason):
                self.assertIsNone(validated_card_identity(subject, card))
        # The well-formed card whose file exists passes.
        good = {"image_id": image_id, "stored_identity": _identity(subject, image_id)}
        self.assertEqual(validated_card_identity(subject, good), good["stored_identity"])

    @covers_requirement(
        "art-gallery-resolution::gallery-urls-are-built-only-from-validated-card-identities"
    )
    def test_a_poisoned_foreign_identity_never_reaches_the_chain_or_a_url(self):
        subject = _character("poisoned")
        good_id = self._append_present(subject)
        record = record_for(subject)
        poisoned = dict(record.db.cards[0])
        poisoned["stored_identity"] = f"gallery/character/other-victim/{_new_id()}.png"
        record.db.cards = [poisoned, dict(record.db.cards[0])]
        with patch("world.art.gallery.log_warn"):
            self.assertEqual([c["image_id"] for c in cards_for(subject)], [good_id])
        self.assertEqual(resolve_card(subject, _FakeEntity())["image_id"], good_id)


class FallbackSeamTests(_ChainBase):
    @covers_requirement(
        "art-gallery-resolution::the-chain-ends-at-one-fallback-seam"
    )
    def test_the_seam_resolves_persons_and_returns_nothing_for_scenes(self):
        # Filled by gallery-builtin-fallbacks: person subjects now resolve a
        # committed built-in default; a scene subject still falls through.
        with patch("world.observability.log_info"):
            person = fallback_for(_monster("seam"))
            character = fallback_for(_character("seam"))
        self.assertIsNone(fallback_for(_scene()))
        self.assertIsNotNone(person)
        self.assertTrue(person["identity"].startswith("defaults/"))
        self.assertTrue(character["identity"].startswith("defaults/"))

    @covers_requirement(
        "art-gallery-resolution::the-chain-ends-at-one-fallback-seam"
    )
    def test_the_chain_writes_nothing_for_an_unwritten_subject(self):
        subject = _character("neverwritten")
        self.assertIsNone(resolve_card(subject, _FakeEntity()))
        self.assertIsNone(record_for(subject))
        self.assertEqual(
            GalleryRecord.objects.filter(db_key=record_key(subject)).count(), 0
        )


# A file-local synthetic preset key and a real, decodable PNG: the catalog
# reads the header only, and no shipped registry key appears here.
_PRESET_KEY = "t_synth_preset"


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class _ProvenanceEntity:
    """An entity-shaped stand-in carrying stored official-content provenance."""

    def __init__(self, pk=11, preset_key=None):
        self.pk = pk
        self.attributes = (
            {} if preset_key is None else {PRESET_PROVENANCE_ATTRIBUTE: preset_key}
        )


class OfficialDefaultStepTests(EvenniaTestCase):
    """Chain step 6: the mounted catalog's official default (task 1.1)."""

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name).resolve() / "official"
        self.settings = override_settings(ART_OFFICIAL_ROOT=str(self.root))
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        registry = patch.object(
            official_refs, "PLAYER_PRESET_REGISTRY", {_PRESET_KEY: object()}
        )
        registry.start()
        self.addCleanup(registry.stop)
        # The catalog admits a ``preset`` directory only for a registered key.
        admitted = patch.object(
            official, "_registered_preset_keys", return_value=frozenset({_PRESET_KEY})
        )
        admitted.start()
        self.addCleanup(admitted.stop)

    def _index(self, name="hero.png", **manifest) -> str:
        """Write one preset content directory, load it, and return its identity."""
        folder = self.root / "preset" / _PRESET_KEY
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_png())
        if manifest:
            (folder / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
        load_catalog()
        return f"preset/{_PRESET_KEY}/{name}"

    def _subject(self, pk=11) -> ArtSubject:
        return ArtSubject(ArtSubjectKind.CHARACTER, str(pk))

    def _entity(self, preset_key=_PRESET_KEY, pk=11):
        return _ProvenanceEntity(pk=pk, preset_key=preset_key)

    def test_a_preset_reference_resolves_the_indexed_default(self):
        identity = self._index(
            face_rect={"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5},
            stage={"scale": 1.4, "x": 0.1, "y": -0.2},
        )
        facts = official_default_for(self._subject(), self._entity())
        self.assertEqual(facts["identity"], identity)
        self.assertEqual(facts["url"], current_catalog().url_for(identity))
        self.assertEqual(
            facts["url"],
            f"/art/official/{current_catalog().fingerprint_for(identity)}/{identity}",
        )
        # The catalog's load-time geometry rides through unchanged.
        self.assertEqual(facts["face_rect"], {"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5})
        self.assertEqual(facts["stage"], {"scale": 1.4, "x": 0.1, "y": -0.2})
        self.assertEqual(facts["image_size"], {"width": 4, "height": 4})

    def test_no_reference_resolves_nothing(self):
        self._index()
        # No entity at all, an entity carrying no provenance, and a scene.
        self.assertIsNone(official_default_for(self._subject(), None))
        self.assertIsNone(official_default_for(self._subject(), _ProvenanceEntity(11)))
        self.assertIsNone(official_default_for(_scene(), None))
        self.assertIsNotNone(official_default_for(self._subject(), self._entity()))

    def test_an_unregistered_reference_resolves_nothing_with_one_bounded_event(self):
        self._index()
        with patch.object(official_refs, "log_warn") as warned:
            facts = official_default_for(
                self._subject(), self._entity(preset_key="t_synth_absent")
            )
        self.assertIsNone(facts)
        events = [
            call
            for call in warned.call_args_list
            if call.args and call.args[0] == UNRESOLVED_REFERENCE_EVENT
        ]
        self.assertEqual(len(events), 1, events)

    def test_a_removed_content_directory_falls_through_without_a_diagnostic(self):
        self._index()
        self.assertIsNotNone(official_default_for(self._subject(), self._entity()))
        shutil.rmtree(self.root / "preset")
        load_catalog()
        with patch.object(official_refs, "log_warn") as warned:
            facts = official_default_for(self._subject(), self._entity())
        # The reference is still registered; only the snapshot lacks it.
        self.assertIsNone(facts)
        self.assertEqual(warned.call_args_list, [])

    def test_a_populated_matching_directory_resolves_nothing_for_monsters(self):
        folder = self.root / "monster" / "t_synth_species"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "a.png").write_bytes(_png())
        load_catalog()
        # The snapshot really holds the directory and its default image...
        self.assertIsNotNone(current_catalog().content("monster", "t_synth_species"))
        entity = _ProvenanceEntity(pk=5)
        entity.threat_tier = "t_synth_species"
        # ...and the monster's species seam is still a zero producer, so no
        # tier-to-content substitution can ever resolve it.
        self.assertIsNone(
            official_default_for(
                ArtSubject(ArtSubjectKind.MONSTER, "t_synth_species"), entity
            )
        )

    def test_a_hundred_resolutions_read_only_the_snapshot_and_write_nothing(self):
        self._index()
        entity = self._entity()
        subject = self._subject()
        store = Path(self.tempdir.name) / "store"
        store.mkdir()
        tripwires = (
            patch.object(socket, "create_connection", side_effect=AssertionError("network")),
            patch.object(socket.socket, "connect", side_effect=AssertionError("network")),
            patch("world.art.gallery.append_card", side_effect=AssertionError("card write")),
            patch("world.art.gallery.set_default", side_effect=AssertionError("default write")),
            patch(
                "world.art.queue.enqueue_gallery_job",
                side_effect=AssertionError("enqueue"),
            ),
            patch(
                "world.art.service.request_gallery_image",
                side_effect=AssertionError("enqueue"),
            ),
            # Resolution answers from the snapshot: it never re-walks or
            # re-loads the mounted tree.
            patch.object(official, "open_dir_fd", side_effect=AssertionError("re-walk")),
            patch.object(official, "load_catalog", side_effect=AssertionError("re-load")),
        )
        with override_settings(ART_STORE_ROOT=str(store)), ExitStack() as stack:
            for tripwire in tripwires:
                stack.enter_context(tripwire)
            before = (
                GalleryRecord.objects.count(),
                ArtAssetRecord.objects.count(),
                sorted(path.relative_to(store).as_posix() for path in store.rglob("*")),
                dict(entity.attributes),
            )
            facts = [official_default_for(subject, entity) for _ in range(100)]
            after = (
                GalleryRecord.objects.count(),
                ArtAssetRecord.objects.count(),
                sorted(path.relative_to(store).as_posix() for path in store.rglob("*")),
                dict(entity.attributes),
            )
        # The tripwire is not vacuous: every resolution really resolved.
        self.assertTrue(all(fact is not None for fact in facts))
        self.assertTrue(all(fact == facts[0] for fact in facts))
        self.assertEqual(before, after)


class ImportBoundaryTests(unittest.TestCase):
    FORBIDDEN = ("world.ai", "ollama", "llm_client", "world.art.connectivity")

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_gallery_match_imports_no_connectivity_module(self):
        source = (REPO_ROOT / "world/art/gallery_match.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for module in imported:
            for forbidden in self.FORBIDDEN:
                self.assertFalse(
                    module == forbidden or module.startswith(f"{forbidden}."),
                    f"gallery_match imports forbidden {module}",
                )


if __name__ == "__main__":
    unittest.main()
