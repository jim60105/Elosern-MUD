"""Retained startup source-fault facts (``art-source-fault-facts``).

``OfficialCatalog`` keeps bounded facts beside its admitted images, so an empty
index can never erase why a source is absent or broken. These cases are pure
mechanism tests over a synthetic ``ART_OFFICIAL_ROOT`` (file-local ``t_synth_*``
keys, no shipped registry content, no authored artwork), and every expected
outcome is stated independently of the implementation:

* the root-health fact separates a deliberately absent DEFAULT optional root and
  a healthy empty root (both normal) from an explicitly configured missing root,
  an unreadable root and a refused/unusable root (all retained failures);
* a manifest-declared default that is missing or refused keeps an attributable
  fault BEFORE the deterministic substitute, while an admitted declared default
  keeps none;
* a malformed/inapplicable manifest keeps a metadata fault beside the safe
  fitted geometry and never blocks the valid image bytes;
* an unselected corrupt sibling stays an operational diagnostic, so a healthy
  requested image carries no fault from it;
* every retained token is bounded (a closed reason, or an identity built from a
  validated single-segment filename), and the facts survive an exhausted
  diagnostic budget;
* one case runs the real startup index plus the real chain lookup
  (``official_default_for``, no mocked catalog accessor) and proves the source
  files and the persisted records are unchanged by resolution.
"""

import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase
from PIL import Image

from world.art import official, official_refs
from world.art.gallery import default_face_rect, identity_stage
from world.art.gallery_match import official_default_for
from world.art.official import (
    ROOT_STATE_ABSENT,
    ROOT_STATE_EMPTY,
    ROOT_STATE_UNAVAILABLE,
    SOURCE_REASON_METADATA_INVALID,
    SOURCE_REASON_REFERENCE_MISSING,
    SOURCE_REASON_REJECTED,
    SOURCE_REASON_UNAVAILABLE,
    SOURCE_SCOPE_DEFAULT,
    SOURCE_SCOPE_METADATA,
    SOURCE_SCOPE_SOURCE,
    SourceFault,
    current_catalog,
    load_catalog,
    reset_catalog,
)
from world.art.official_refs import PRESET_PROVENANCE_ATTRIBUTE
from world.art.store import ArtAssetRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement

# File-local synthetic content keys: the catalog owns the INDEXING mechanics,
# never shipped content, so no registry key of the game appears here.
_PRESET_KEY = "t_synth_preset"
_NPC_KEY = "t_synth_profile"


def _png(width: int = 4, height: int = 4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


# A real decodable image (the bounded header decoder accepts only real bytes)
# and a payload no decoder can accept (the deterministic per-entry refusal).
_PNG = _png()
_UNDECODABLE = b"definitely not an image"


class _ProvenanceEntity:
    """An entity-shaped stand-in carrying stored official-content provenance."""

    def __init__(self, pk: int = 11, preset_key: str | None = _PRESET_KEY) -> None:
        self.pk = pk
        self.attributes = (
            {} if preset_key is None else {PRESET_PROVENANCE_ATTRIBUTE: preset_key}
        )


class _FaultCase(EvenniaTestCase):
    """A temporary official root, a synthetic preset registry and event sinks."""

    def setUp(self) -> None:
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name).resolve() / "art-official"
        # The provenance is pinned per case: the fixture's root is a settings
        # override, so a case that means "the operator bound it" says so.
        self.settings = override_settings(
            ART_OFFICIAL_ROOT=str(self.root), ART_OFFICIAL_ROOT_EXPLICIT=False
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        registry = patch.object(
            official, "_registered_preset_keys", return_value=frozenset({_PRESET_KEY})
        )
        registry.start()
        self.addCleanup(registry.stop)
        info = patch.object(official, "log_info")
        self.info = info.start()
        self.addCleanup(info.stop)
        warn = patch.object(official, "log_warn")
        self.warn = warn.start()
        self.addCleanup(warn.stop)

    # -- tree builders ----------------------------------------------------
    def image(
        self,
        name: str,
        content: bytes = _PNG,
        kind: str = "preset",
        key: str = _PRESET_KEY,
    ) -> str:
        folder = self.root / kind / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(content)
        return f"{kind}/{key}/{name}"

    def manifest(self, payload, kind: str = "preset", key: str = _PRESET_KEY) -> None:
        folder = self.root / kind / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / official.OFFICIAL_MANIFEST_FILENAME).write_text(
            payload if isinstance(payload, str) else json.dumps(payload),
            encoding="utf-8",
        )

    def fresh_root(self, name: str):
        """Point both the tree builder and the setting at a brand-new root."""
        self.root = (Path(self.tempdir.name) / name).resolve()
        return override_settings(
            ART_OFFICIAL_ROOT=str(self.root), ART_OFFICIAL_ROOT_EXPLICIT=False
        )

    def load(self) -> dict:
        return load_catalog()

    # -- assertions -------------------------------------------------------
    def contexts(self, mock) -> list[dict]:
        return [call.kwargs["context"] for call in mock.call_args_list]

    def reasons(self, mock) -> list[str]:
        return sorted(context.get("reason") for context in self.contexts(mock))

    def boundary(self) -> dict:
        self.assertEqual(
            len(self.info.call_args_list),
            1,
            msg=f"expected exactly one boundary event: {self.info.call_args_list}",
        )
        return self.contexts(self.info)[0]


class RootHealthFactTests(_FaultCase):
    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_default_absent_root_is_normal_and_retains_no_fault(self):
        absent = Path(self.tempdir.name) / "absent"
        with override_settings(ART_OFFICIAL_ROOT=str(absent)):
            summary = self.load()
        health = current_catalog().root_health()
        self.assertEqual(health.state, ROOT_STATE_ABSENT)
        self.assertFalse(health.configured)
        self.assertFalse(health.fault)
        self.assertFalse(summary["root_fault"])
        self.assertEqual(current_catalog().source_faults("preset", _PRESET_KEY), ())
        self.warn.assert_not_called()

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_configured_missing_root_survives_an_empty_index_as_a_fault(self):
        absent = Path(self.tempdir.name) / "absent"
        with override_settings(
            ART_OFFICIAL_ROOT=str(absent), ART_OFFICIAL_ROOT_EXPLICIT=True
        ):
            summary = self.load()
        catalog = current_catalog()
        health = catalog.root_health()
        self.assertEqual(len(catalog), 0)
        self.assertEqual(health.state, ROOT_STATE_UNAVAILABLE)
        self.assertTrue(health.configured)
        self.assertTrue(health.fault)
        self.assertEqual(self.boundary()["reason"], "official_root_absent")
        self.assertTrue(summary["root_fault"])
        self.assertEqual(self.reasons(self.warn), [SOURCE_REASON_UNAVAILABLE])
        self.assertNotIn(str(absent), str(self.contexts(self.warn)))

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_an_empty_root_is_healthy_and_an_unreadable_root_is_a_fault(self):
        self.root.mkdir(parents=True)
        self.load()
        health = current_catalog().root_health()
        self.assertEqual((health.state, health.fault), (ROOT_STATE_EMPTY, False))
        self.warn.assert_not_called()
        reset_catalog()
        with patch.object(official, "open_dir_fd", side_effect=OSError("denied")):
            summary = self.load()
        self.assertEqual(current_catalog().root_health().state, ROOT_STATE_UNAVAILABLE)
        self.assertTrue(current_catalog().root_health().fault)
        self.assertTrue(summary["root_fault"])
        self.assertEqual(self.reasons(self.warn), [SOURCE_REASON_UNAVAILABLE])


class DeclaredDefaultFaultTests(_FaultCase):
    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_missing_declared_default_precedes_the_deterministic_substitute(self):
        self.image("a.png")
        self.image("z.png")
        self.manifest({"default": "hero.png"})
        self.load()
        catalog = current_catalog()
        content = catalog.content("preset", _PRESET_KEY)
        self.assertEqual(content.default_identity, f"preset/{_PRESET_KEY}/a.png")
        self.assertEqual(content.requested_default, f"preset/{_PRESET_KEY}/hero.png")
        faults = catalog.source_faults("preset", _PRESET_KEY)
        self.assertEqual(
            faults[0],
            SourceFault(
                SOURCE_SCOPE_DEFAULT,
                f"preset/{_PRESET_KEY}/hero.png",
                SOURCE_REASON_REFERENCE_MISSING,
            ),
        )
        # The substitute's declared geometry was replaced by the fitted one, so
        # its metadata fault follows the default fault.
        self.assertEqual(
            [fault.identity for fault in faults[1:]],
            [
                f"preset/{_PRESET_KEY}/a.png",
                f"preset/{_PRESET_KEY}/z.png",
            ],
        )
        self.assertTrue(
            all(fault.reason == SOURCE_REASON_METADATA_INVALID for fault in faults[1:])
        )
        self.assertIn("manifest_default_not_an_admitted_file", self.reasons(self.warn))

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_declared_default_refused_at_admission_is_a_rejected_fault(self):
        self.image("a.png")
        broken = self.image("broken.png", content=_UNDECODABLE)
        self.manifest({"default": "broken.png"})
        self.load()
        catalog = current_catalog()
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY)[0],
            SourceFault(SOURCE_SCOPE_DEFAULT, broken, SOURCE_REASON_REJECTED),
        )
        self.assertEqual(
            catalog.content("preset", _PRESET_KEY).default_identity,
            f"preset/{_PRESET_KEY}/a.png",
        )
        self.assertEqual(catalog.refusal_reason(broken), "image_undecodable")

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_an_admitted_declared_default_keeps_no_default_fault(self):
        identity = self.image("a.png")
        # The declared default IS the admitted image; an unrelated metadata
        # violation degrades the manifest whole but can never be reported as a
        # missing or rejected reference to that image.
        self.manifest({"default": "a.png", "stage": {"scale": 9}})
        self.load()
        catalog = current_catalog()
        content = catalog.content("preset", _PRESET_KEY)
        self.assertEqual(content.default_identity, identity)
        self.assertEqual(content.requested_default, identity)
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY),
            (
                SourceFault(
                    SOURCE_SCOPE_METADATA, identity, SOURCE_REASON_METADATA_INVALID
                ),
            ),
        )
        entry = catalog.entry(identity)
        self.assertEqual(entry.stage, identity_stage())
        self.assertEqual(entry.face_rect, default_face_rect({"width": 4, "height": 4}))

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_valid_declared_default_is_retained_beside_the_effective_selection(self):
        self.image("a.png")
        self.image("b.png")
        self.manifest({"default": "b.png"})
        self.load()
        content = current_catalog().content("preset", _PRESET_KEY)
        self.assertEqual(content.requested_default, f"preset/{_PRESET_KEY}/b.png")
        self.assertEqual(content.default_identity, content.requested_default)
        self.assertEqual(current_catalog().source_faults("preset", _PRESET_KEY), ())
        self.warn.assert_not_called()


class MetadataFaultTests(_FaultCase):
    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_malformed_manifest_keeps_a_metadata_fault_with_safe_geometry(self):
        identity = self.image("a.png")
        self.manifest("{not json")
        self.load()
        catalog = current_catalog()
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY),
            (
                SourceFault(
                    SOURCE_SCOPE_METADATA, identity, SOURCE_REASON_METADATA_INVALID
                ),
            ),
        )
        entry = catalog.entry(identity)
        self.assertEqual(entry.face_rect, default_face_rect({"width": 4, "height": 4}))
        self.assertEqual(entry.stage, identity_stage())
        # The valid image bytes stay admitted and servable.
        self.assertIsNotNone(catalog.fingerprint_for(identity))
        self.assertIsNotNone(catalog.url_for(identity))

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_an_unselected_corrupt_sibling_is_a_diagnostic_only(self):
        healthy = self.image("a.png")
        broken = self.image("broken.png", content=_UNDECODABLE)
        self.load()
        catalog = current_catalog()
        self.assertEqual(catalog.source_faults("preset", _PRESET_KEY), ())
        self.assertIsNone(catalog.fault_for(healthy))
        entry = catalog.entry(healthy)
        self.assertEqual(entry.face_rect, default_face_rect({"width": 4, "height": 4}))
        self.assertEqual(catalog.refusal_reason(broken), "image_undecodable")
        self.assertIn("image_undecodable", self.reasons(self.warn))

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_an_image_whose_rectangle_is_inapplicable_alone_carries_the_fault(self):
        rect = {"x": 0.1, "y": 0.05, "w": 0.5, "h": 0.9}
        square = self.image("square.png", content=_png(1, 1))
        tall = self.image("tall.png", content=_png(1, 2))
        # Pixel-square on 1x1 but not on 1x2 (the shared seed-metadata rule).
        self.manifest({"face_rect": rect})
        self.load()
        catalog = current_catalog()
        self.assertEqual(
            [fault.identity for fault in catalog.source_faults("preset", _PRESET_KEY)],
            [tall],
        )
        self.assertIsNone(catalog.fault_for(square))
        self.assertEqual(catalog.entry(square).face_rect, rect)
        self.assertEqual(
            catalog.entry(tall).face_rect, default_face_rect({"width": 1, "height": 2})
        )


class FactRetentionTests(_FaultCase):
    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_wholly_refused_directory_retains_its_requested_default_fault(self):
        broken = self.image("broken.png", content=_UNDECODABLE)
        self.manifest({"default": "broken.png"})
        self.load()
        catalog = current_catalog()
        # No image was admitted, so the directory is not indexed at all — the
        # facts are what survive.
        self.assertIsNone(catalog.content("preset", _PRESET_KEY))
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY),
            (SourceFault(SOURCE_SCOPE_DEFAULT, broken, SOURCE_REASON_REJECTED),),
        )
        self.assertEqual(catalog.refusal_reason(broken), "image_undecodable")

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_manifest_only_directory_retains_a_missing_reference_fault(self):
        self.manifest({"default": "hero.png"})
        self.load()
        catalog = current_catalog()
        self.assertIsNone(catalog.content("preset", _PRESET_KEY))
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY),
            (
                SourceFault(
                    SOURCE_SCOPE_DEFAULT,
                    f"preset/{_PRESET_KEY}/hero.png",
                    SOURCE_REASON_REFERENCE_MISSING,
                ),
            ),
        )

    @covers_requirement(
        "official-artwork-catalog::catalog-load-and-refusals-are-observable-through-the-facade"
    )
    def test_facts_survive_an_exhausted_diagnostic_budget(self):
        identity = self.image("a.png")
        for index in range(official._MAX_DIAGNOSTICS + 5):
            self.image(f"bad{index:03d}.jxl")
        self.manifest({"default": "hero.png"})
        summary = self.load()
        self.assertGreater(summary["suppressed_diagnostics"], 0)
        catalog = current_catalog()
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY)[0],
            SourceFault(
                SOURCE_SCOPE_DEFAULT,
                f"preset/{_PRESET_KEY}/hero.png",
                SOURCE_REASON_REFERENCE_MISSING,
            ),
        )
        self.assertEqual(
            catalog.fault_for(identity),
            SourceFault(SOURCE_SCOPE_METADATA, identity, SOURCE_REASON_METADATA_INVALID),
        )
        self.assertEqual(
            catalog.refusal_reason(f"preset/{_PRESET_KEY}/bad036.jxl"),
            "unsupported_extension_skipped",
        )

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_unsafe_declared_defaults_are_never_echoed_as_identities(self):
        unsafe = (
            "/private/operator/hero.png",
            "../../hero.png",
            "nested/hero.png",
            "hero\x00.png",
            "hero\n.png",
            "h" * (official._MAX_DECLARED_DEFAULT_LENGTH + 1),
            "",
            7,
        )
        for index, value in enumerate(unsafe):
            with self.subTest(value=repr(value)[:40]):
                self.warn.reset_mock()
                self.info.reset_mock()
                reset_catalog()
                with self.fresh_root(f"case-{index}"):
                    self.image("a.png")
                    self.manifest({"default": value})
                    self.load()
                catalog = current_catalog()
                # The manifest degrades whole as an inadmissible default, so no
                # default fault exists and the raw value is echoed nowhere.
                self.assertEqual(
                    catalog.source_faults("preset", _PRESET_KEY),
                    (
                        SourceFault(
                            SOURCE_SCOPE_METADATA,
                            f"preset/{_PRESET_KEY}/a.png",
                            SOURCE_REASON_METADATA_INVALID,
                        ),
                    ),
                )
                self.assertIn(
                    "manifest_default_not_an_admitted_file", self.reasons(self.warn)
                )
                self.assertIsNotNone(catalog.entry(f"preset/{_PRESET_KEY}/a.png"))
                if isinstance(value, str) and value:
                    rendered = " ".join(
                        str(context) for context in self.contexts(self.warn)
                    )
                    self.assertNotIn(value, rendered)

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_null_declared_default_is_no_declaration_at_all(self):
        identity = self.image("a.png")
        self.manifest({"default": None, "stage": {"scale": 1.2, "x": 0.1, "y": 0.1}})
        self.load()
        catalog = current_catalog()
        self.assertEqual(catalog.source_faults("preset", _PRESET_KEY), ())
        self.assertEqual(catalog.content("preset", _PRESET_KEY).default_identity, identity)
        self.assertEqual(
            catalog.content("preset", _PRESET_KEY).requested_default, None
        )
        self.assertEqual(
            catalog.entry(identity).stage, {"scale": 1.2, "x": 0.1, "y": 0.1}
        )
        self.warn.assert_not_called()

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_facts_are_isolated_per_source(self):
        self.image("a.png")
        self.image("c.png", kind="npc", key=_NPC_KEY)
        self.manifest({"default": "hero.png"})
        self.manifest({"default": "ghost.png"}, kind="npc", key=_NPC_KEY)
        self.load()
        catalog = current_catalog()
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY)[0].identity,
            f"preset/{_PRESET_KEY}/hero.png",
        )
        self.assertEqual(
            catalog.source_faults("npc", _NPC_KEY)[0].identity,
            f"npc/{_NPC_KEY}/ghost.png",
        )
        self.assertEqual(catalog.source_faults("preset", "t_synth_absent"), ())

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_an_unknown_manifest_key_never_loses_the_declared_default(self):
        """A manifest rejected for an unrelated key still keeps its default fact."""
        cases = (
            ("hero.png", SOURCE_REASON_REFERENCE_MISSING, False),
            ("broken.png", SOURCE_REASON_REJECTED, False),
            ("a.png", None, True),
        )
        for index, (declared, reason, admitted) in enumerate(cases):
            with self.subTest(declared=declared):
                self.warn.reset_mock()
                self.info.reset_mock()
                reset_catalog()
                with self.fresh_root(f"unknown-key-{index}"):
                    identity = self.image("a.png")
                    self.image("broken.png", content=_UNDECODABLE)
                    self.manifest({"default": declared, "package_id": "x"})
                    self.load()
                catalog = current_catalog()
                faults = catalog.source_faults("preset", _PRESET_KEY)
                if reason is None:
                    self.assertEqual(faults[0].scope, SOURCE_SCOPE_METADATA)
                    self.assertEqual(
                        catalog.content("preset", _PRESET_KEY).requested_default,
                        identity,
                    )
                else:
                    self.assertEqual(
                        faults[0],
                        SourceFault(
                            SOURCE_SCOPE_DEFAULT,
                            f"preset/{_PRESET_KEY}/{declared}",
                            reason,
                        ),
                    )
                # Still exactly one manifest diagnostic for the degraded whole.
                self.assertEqual(
                    [
                        candidate
                        for candidate in self.reasons(self.warn)
                        if candidate.startswith("manifest_")
                    ],
                    ["manifest_not_a_valid_object"],
                )

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_an_unopenable_content_directory_keeps_a_source_availability_fault(self):
        self.image("a.png")
        real_open_dir_fd = official.open_dir_fd

        def _denied(name, **kwargs):
            if name == _PRESET_KEY:
                raise PermissionError("denied")
            return real_open_dir_fd(name, **kwargs)

        with patch.object(official, "open_dir_fd", side_effect=_denied):
            self.load()
        catalog = current_catalog()
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY),
            (
                SourceFault(
                    SOURCE_SCOPE_SOURCE,
                    f"preset/{_PRESET_KEY}",
                    SOURCE_REASON_UNAVAILABLE,
                ),
            ),
        )
        self.assertIsNone(catalog.content("preset", _PRESET_KEY))
        self.assertEqual(catalog.refusal_reason(f"preset/{_PRESET_KEY}/a.png"), None)

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_failed_enumeration_is_a_source_fault_never_a_missing_reference(self):
        """A listing failure must not classify an on-disk default as missing.

        The walk lists the root, then the kind, then the content directory, so
        the third listing call is the content directory's: it fails while the
        manifest (whose declared default does exist on disk) stays readable.
        """
        identity = self.image("a.png")
        self.manifest({"default": "a.png"})
        listings = {"calls": 0}
        real_listdir = official.os.listdir

        def _fail_the_content_listing(target, *args, **kwargs):
            listings["calls"] += 1
            if listings["calls"] == 3:
                raise OSError("denied")
            return real_listdir(target, *args, **kwargs)

        with patch.object(official.os, "listdir", side_effect=_fail_the_content_listing):
            self.load()
        catalog = current_catalog()
        self.assertEqual(
            catalog.source_faults("preset", _PRESET_KEY),
            (
                SourceFault(
                    SOURCE_SCOPE_SOURCE,
                    f"preset/{_PRESET_KEY}",
                    SOURCE_REASON_UNAVAILABLE,
                ),
            ),
        )
        self.assertIsNone(catalog.content("preset", _PRESET_KEY))
        self.assertNotIn("manifest_default_not_an_admitted_file", self.reasons(self.warn))
        self.assertEqual(catalog.refusal_reason(identity), None)

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_the_unforeseen_fault_path_keeps_the_facts_already_collected(self):
        """The last-resort handler republishes the facts, not a bare snapshot."""
        first, second = "t_synth_aaa", "t_synth_zzz"
        registry = patch.object(
            official,
            "_registered_preset_keys",
            return_value=frozenset({first, second}),
        )
        registry.start()
        self.addCleanup(registry.stop)
        self.image("bad.jxl", kind="preset", key=first)
        self.manifest({"default": "hero.png"}, kind="preset", key=first)
        self.image("a.png", kind="preset", key=second)
        real_parse_manifest = official._parse_manifest

        def _explode_on_the_second(content_fd, admitted_names, diagnostics, kind, key):
            if key == second:
                raise RuntimeError("unforeseen")
            return real_parse_manifest(
                content_fd, admitted_names, diagnostics, kind, key
            )

        with patch.object(official, "_parse_manifest", side_effect=_explode_on_the_second):
            summary = self.load()
        catalog = current_catalog()
        self.assertEqual(catalog.root_health().reason, "catalog_load_failed")
        self.assertTrue(catalog.root_health().fault)
        self.assertTrue(summary["root_fault"])
        self.assertEqual(len(catalog), 0)
        self.assertEqual(
            catalog.source_faults("preset", first),
            (
                SourceFault(
                    SOURCE_SCOPE_DEFAULT,
                    f"preset/{first}/hero.png",
                    SOURCE_REASON_REFERENCE_MISSING,
                ),
            ),
        )
        self.assertEqual(
            catalog.refusal_reason(f"preset/{first}/bad.jxl"),
            "unsupported_extension_skipped",
        )


class RuntimeLookupSmokeTests(_FaultCase):
    """The changed path end to end: real startup indexing, real chain lookup."""

    def setUp(self) -> None:
        super().setUp()
        registry = patch.object(
            official_refs, "PLAYER_PRESET_REGISTRY", {_PRESET_KEY: object()}
        )
        registry.start()
        self.addCleanup(registry.stop)

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention",
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration",
    )
    def test_the_real_lookup_resolves_the_substitute_and_writes_nothing(self):
        broken = self.image("broken.png", content=_UNDECODABLE)
        substitute = self.image("a.png")
        self.image("z.png")
        self.manifest({"default": "broken.png"})
        before = {
            path: path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }
        self.load()
        catalog = current_catalog()
        # The declared default precedes its deterministic substitute in fact
        # order, and the substitute is what the real chain step selects.
        faults = catalog.source_faults("preset", _PRESET_KEY)
        self.assertEqual(
            faults[0],
            SourceFault(SOURCE_SCOPE_DEFAULT, broken, SOURCE_REASON_REJECTED),
        )
        self.assertEqual(catalog.refusal_reason(broken), "image_undecodable")
        facts = official_default_for(
            ArtSubject(ArtSubjectKind.CHARACTER, "11"), _ProvenanceEntity()
        )
        self.assertIsNotNone(facts)
        self.assertEqual(facts["identity"], substitute)
        self.assertEqual(facts["url"], catalog.url_for(substitute))
        # The substitute's own fact is the manifest's metadata degradation, never
        # the refused sibling's rejection.
        self.assertEqual(
            catalog.fault_for(substitute).scope, SOURCE_SCOPE_METADATA
        )
        # Resolution reads the snapshot only: the tree and the records are
        # byte-for-byte unchanged by the load and by the lookup.
        after = {
            path: path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }
        self.assertEqual(before, after)
        self.assertEqual(ArtAssetRecord.objects.count(), 0)

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_disabled_generation_scheduler_never_clears_a_recorded_fault(self):
        absent = Path(self.tempdir.name) / "absent"
        with override_settings(
            ART_OFFICIAL_ROOT=str(absent),
            ART_OFFICIAL_ROOT_EXPLICIT=True,
            ART_SCHEDULER_ENABLED=False,
        ):
            summary = self.load()
        health = current_catalog().root_health()
        self.assertEqual((health.state, health.fault), (ROOT_STATE_UNAVAILABLE, True))
        self.assertTrue(summary["root_fault"])
        self.assertEqual(len(current_catalog()), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
