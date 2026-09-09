"""Tests for the background-removal seam (art-portrait-cutout).

Covers the injectable seam (``resolve_cutout_backend`` and the bounded
``remove_background`` entry point), the subject-kind allowlist, the
deterministic fake double, and ``RembgCutoutBackend`` with the ONNX/``rembg``
session factory PATCHED — no test here ever loads a real model, touches the
network, or leaves the module session cache or the process environment
mutated. The laziness pair proves the optional stack is never imported at
module import and that a broken first use fails bounded.

Annotated with the canonical ``art-portrait-cutout`` requirement IDs the
archive sync published — the follow-up that tasks 6.11 deferred.
"""

from __future__ import annotations

import builtins
import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from django.test import override_settings
from PIL import Image, ImageMode

from world.art import cutout
from world.art.cutout import CUTOUT_SUBJECT_KINDS, CutoutError, applies_to
from world.art.fake_cutout import FakeCutoutBackend
from world.art.subjects import ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _opaque_png(size=(16, 12)) -> bytes:
    """An OPAQUE multi-pixel PNG fixture (never fake_sd_client.DEFAULT_PNG)."""
    image = Image.new("RGB", size, (200, 10, 10))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _png_with_mode(mode: str, size=(8, 8)) -> bytes:
    colour = (10, 20, 30, 255)[: len(ImageMode.getmode(mode).bands)]
    image = Image.new(mode, size, colour)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _StubBackend:
    """A minimal backend double with scripted behaviour per test."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def remove_background(self, png_bytes):
        self.calls.append(png_bytes)
        if self.error is not None:
            raise self.error
        return self.result


_FixedBackend_calls: list = []
_FIXED_PNG = _png_with_mode("RGBA")


class _FixedBackend:
    """A no-argument backend the real dotted-path resolution can build."""

    def remove_background(self, png_bytes):
        _FixedBackend_calls.append(png_bytes)
        return _FIXED_PNG


class SeamResolutionTests(unittest.TestCase):
    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_a_non_dotted_backend_path_is_unavailable(self):
        with override_settings(ART_REMBG_BACKEND="notadottedpath"):
            with self.assertRaises(CutoutError) as caught:
                cutout.resolve_cutout_backend()
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_an_unimportable_module_is_unavailable(self):
        with override_settings(ART_REMBG_BACKEND="no.such.module.Backend"):
            with self.assertRaises(CutoutError) as caught:
                cutout.resolve_cutout_backend()
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_a_missing_attribute_is_unavailable(self):
        with override_settings(
            ART_REMBG_BACKEND="world.art.cutout.NoSuchBackend"
        ):
            with self.assertRaises(CutoutError) as caught:
                cutout.resolve_cutout_backend()
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_a_failing_constructor_is_unavailable(self):
        class _Exploding:
            def __init__(self):
                raise RuntimeError("constructor exploded")

        with override_settings(
            ART_REMBG_BACKEND="world.art.tests.test_cutout._Exploding"
        ):
            with self.assertRaises(CutoutError) as caught:
                cutout.resolve_cutout_backend()
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_the_resolved_backend_is_instantiated_and_used(self):
        _FixedBackend_calls.clear()
        with override_settings(
            ART_REMBG_BACKEND="world.art.tests.test_cutout._FixedBackend"
        ):
            result = cutout.remove_background(b"input-bytes")
        self.assertEqual(result, _FIXED_PNG)
        self.assertEqual(_FixedBackend_calls, [b"input-bytes"])


class BoundedEntryTests(unittest.TestCase):
    """remove_background bounds every escaping failure to one of two codes."""

    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_an_arbitrary_backend_exception_becomes_art_cutout_error(self):
        stub = _StubBackend(error=RuntimeError("inference exploded"))
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_error")
        self.assertIsNotNone(caught.exception.__cause__)

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_non_bytes_return_is_art_cutout_error(self):
        stub = _StubBackend(result="not bytes")
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_error")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_empty_return_is_art_cutout_error(self):
        stub = _StubBackend(result=b"")
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_error")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_missing_png_magic_is_art_cutout_error(self):
        stub = _StubBackend(result=b"garbage-not-a-png")
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_error")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_magic_prefixed_corrupt_bytes_are_art_cutout_error(self):
        stub = _StubBackend(result=b"\x89PNG\r\n\x1a\nnot-really-a-png")
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_error")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_an_opaque_passthrough_is_art_cutout_error(self):
        # The stage's own postcondition is an alpha-carrying PNG: a backend
        # that returns the original opaque portrait unchanged must fail the
        # job instead of storing a non-cutout as a successful one.
        opaque = _opaque_png()
        stub = _StubBackend(result=opaque)
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(opaque)
        self.assertEqual(caught.exception.code, "art_cutout_error")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_an_opaque_jpeg_decoration_is_art_cutout_error(self):
        stub = _StubBackend(result=_png_with_mode("RGB"))
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_error")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_an_alpha_carrying_return_passes_through_untouched(self):
        payload = _png_with_mode("RGBA")
        stub = _StubBackend(result=payload)
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            self.assertEqual(cutout.remove_background(_opaque_png()), payload)

    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_a_scripted_cutout_error_propagates_unchanged(self):
        stub = _StubBackend(error=CutoutError("art_cutout_unavailable", "scripted"))
        with mock.patch.object(cutout, "resolve_cutout_backend", return_value=stub):
            with self.assertRaises(CutoutError) as caught:
                cutout.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")


class SubjectKindScopeTests(unittest.TestCase):
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_the_allowlist_holds_exactly_the_portrait_kinds(self):
        self.assertEqual(
            CUTOUT_SUBJECT_KINDS,
            frozenset({ArtSubjectKind.CHARACTER, ArtSubjectKind.MONSTER}),
        )

    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_scenes_are_outside_the_allowlist(self):
        self.assertFalse(applies_to(ArtSubjectKind.SCENE))

    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_every_subject_kind_is_classified_by_the_allowlist(self):
        # Exhaustiveness contract (design D3): a NEW ArtSubjectKind member must
        # fail this suite until it is deliberately classified.
        for kind in ArtSubjectKind:
            if kind is ArtSubjectKind.SCENE:
                self.assertFalse(applies_to(kind), kind)
            else:
                self.assertIn(kind, CUTOUT_SUBJECT_KINDS)
                self.assertTrue(applies_to(kind), kind)


class FakeCutoutTests(unittest.TestCase):
    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_the_fake_returns_a_real_png_with_a_zeroed_region(self):
        fake = FakeCutoutBackend()
        opaque = _opaque_png()
        result = fake.remove_background(opaque)
        self.assertNotEqual(result, opaque, "the fake must never pass through")
        with Image.open(io.BytesIO(result)) as image:
            self.assertEqual(image.mode, "RGBA")
            pixels = image.load()
            # In the zeroed top-left 8x8 region: fully transparent.
            self.assertEqual(pixels[0, 0][3], 0)
            self.assertEqual(pixels[7, 7][3], 0)
            # Outside it: still opaque (the fixture is 16x12).
            self.assertEqual(pixels[10, 10][3], 255)
            self.assertEqual(pixels[15, 11][3], 255)

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_the_fake_records_every_call(self):
        fake = FakeCutoutBackend()
        fake.remove_background(_opaque_png((4, 4)))
        fake.remove_background(_opaque_png((5, 5)))
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(fake.calls[0][:8], b"\x89PNG\r\n\x1a\n")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_the_fake_replays_scripted_failures(self):
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_error", "scripted"))
        with self.assertRaises(CutoutError) as caught:
            fake.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_error")

        matcher = FakeCutoutBackend()
        bad = _opaque_png((3, 3))
        matcher.add_failure(lambda payload: payload is bad, CutoutError("art_cutout_error", "match"))
        with self.assertRaises(CutoutError):
            matcher.remove_background(bad)
        good = _opaque_png((6, 6))
        self.assertEqual(matcher.remove_background(good)[:8], b"\x89PNG\r\n\x1a\n")

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_the_fake_never_imports_the_optional_stack(self):
        self.assertNotIn("rembg", sys.modules)


class _RembgBackendCase(unittest.TestCase):
    """Shared isolation plumbing for the real-backend tests (factory patched)."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.model_dir = Path(self.tempdir.name) / "models-home"
        # Snapshot the process-global state the backend deliberately mutates
        # (design D7): the model-home variables and the OMP thread cap.
        self._env_snapshot = {
            name: os.environ.get(name)
            for name in ("U2NET_HOME", "REMBG_HOME", "OMP_NUM_THREADS")
        }
        for name in ("U2NET_HOME", "REMBG_HOME", "OMP_NUM_THREADS"):
            os.environ.pop(name, None)
        # The session cache is keyed by model only — valid under restart-bound
        # production settings; tests must clear it so overrides never reuse a
        # session built for a previous configuration.
        self._cache_snapshot = dict(cutout._sessions)
        cutout._sessions.clear()
        self.addCleanup(self._restore)

    def _restore(self):
        cutout._sessions.clear()
        cutout._sessions.update(self._cache_snapshot)
        for name, value in self._env_snapshot.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _backend(self, **overrides):
        settings_override = override_settings(
            ART_REMBG_MODEL_DIR=str(self.model_dir), **overrides
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        return cutout.RembgCutoutBackend()


class RembgSessionTests(_RembgBackendCase):
    """RembgCutoutBackend with the rembg session factory PATCHED (no model)."""

    def _patched_new_session(self, sessions):
        recorded = {}

        def _factory(model_name, *args, **kwargs):
            recorded.setdefault("calls", []).append((model_name, args, kwargs))
            session = object()
            sessions.append(session)
            return session

        return _factory, recorded

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_only_the_cpu_provider_is_requested_and_the_session_is_built_once(self):
        sessions: list = []
        factory, recorded = self._patched_new_session(sessions)
        with mock.patch("rembg.new_session", side_effect=factory):
            backend = self._backend()
            with mock.patch("rembg.remove", side_effect=lambda data, session: b"\x89PNGout"):
                first = backend.remove_background(b"a")
                second = backend.remove_background(b"b")
                third = backend.remove_background(b"c")
        self.assertEqual(first, b"\x89PNGout")
        self.assertEqual(second, first)
        self.assertEqual(third, first)
        self.assertEqual(len(recorded["calls"]), 1, "one session per model")
        self.assertEqual(recorded["calls"][0][0], "bria-rmbg")
        self.assertEqual(
            recorded["calls"][0][2].get("providers"), ["CPUExecutionProvider"]
        )
        self.assertIs(sessions[0], cutout._sessions["bria-rmbg"])

    @covers_requirement("art-portrait-cutout::the-model-artifact-is-cached-in-a-code-only-persistent-directory-under-an-explicit-download-policy")
    def test_a_non_zero_thread_cap_reaches_omp_num_threads(self):
        sessions: list = []
        factory, recorded = self._patched_new_session(sessions)
        with mock.patch("rembg.new_session", side_effect=factory):
            backend = self._backend(ART_REMBG_THREADS=4)
            backend._session()
        self.assertEqual(os.environ.get("OMP_NUM_THREADS"), "4")
        self.assertEqual(os.environ.get("U2NET_HOME"), str(self.model_dir))
        self.assertEqual(os.environ.get("REMBG_HOME"), str(self.model_dir))
        self.assertTrue(self.model_dir.is_dir())

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_a_zero_thread_cap_leaves_omp_num_threads_untouched(self):
        sessions: list = []
        factory, recorded = self._patched_new_session(sessions)
        with mock.patch("rembg.new_session", side_effect=factory):
            backend = self._backend(ART_REMBG_THREADS=0)
            backend._session()
        self.assertIsNone(os.environ.get("OMP_NUM_THREADS"))

    @covers_requirement("art-portrait-cutout::the-model-artifact-is-cached-in-a-code-only-persistent-directory-under-an-explicit-download-policy")
    def test_downloads_disabled_without_an_artifact_fails_before_importing_rembg(self):
        backend = self._backend(ART_REMBG_DOWNLOAD_ENABLED=False)
        with mock.patch.dict(sys.modules, {"rembg": None}):
            with self.assertRaises(CutoutError) as caught:
                backend._session()
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")

    @covers_requirement("art-portrait-cutout::the-model-artifact-is-cached-in-a-code-only-persistent-directory-under-an-explicit-download-policy")
    def test_downloads_disabled_with_a_preseeded_artifact_builds_the_session(self):
        (self.model_dir / "models" / "isnet-anime").mkdir(parents=True)
        (self.model_dir / "models" / "isnet-anime" / "isnet-anime.onnx").write_bytes(b"model")
        sessions: list = []
        factory, recorded = self._patched_new_session(sessions)
        with mock.patch("rembg.new_session", side_effect=factory):
            backend = self._backend(ART_REMBG_DOWNLOAD_ENABLED=False, ART_REMBG_MODEL="isnet-anime")
            backend._session()
        self.assertEqual(recorded["calls"][0][0], "isnet-anime")

    @covers_requirement("art-portrait-cutout::the-model-artifact-is-cached-in-a-code-only-persistent-directory-under-an-explicit-download-policy")
    def test_downloads_disabled_accepts_the_flat_legacy_layout(self):
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / "u2net.onnx").write_bytes(b"model")
        sessions: list = []
        factory, recorded = self._patched_new_session(sessions)
        with mock.patch("rembg.new_session", side_effect=factory):
            backend = self._backend(ART_REMBG_DOWNLOAD_ENABLED=False, ART_REMBG_MODEL="u2net")
            backend._session()
        self.assertEqual(recorded["calls"][0][0], "u2net")

    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_a_failing_session_factory_is_art_cutout_unavailable(self):
        with mock.patch(
            "rembg.new_session", side_effect=ValueError("no session class")
        ):
            backend = self._backend()
            with self.assertRaises(CutoutError) as caught:
                backend._session()
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")


class LazinessTests(_RembgBackendCase):
    """The optional stack is lazy: import-time absence and broken first use."""

    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_importing_world_art_cutout_does_not_import_rembg(self):
        # Order-independent proof (a bare "not in sys.modules" would false-fail
        # after another test imported rembg, and a reload of the live module
        # would rebind its classes under every other test): pop any cached
        # rembg* modules, execute the cutout module body FRESH under a probe
        # name, and assert rembg stays absent from sys.modules.
        saved = {
            name: module
            for name, module in sys.modules.items()
            if name == "rembg" or name.startswith("rembg.")
        }
        probe_name = "world.art.cutout._laziness_probe"
        try:
            for name in saved:
                sys.modules.pop(name, None)
            spec = importlib.util.spec_from_file_location(
                probe_name, Path(cutout.__file__)
            )
            probe = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(probe)
            self.assertNotIn("rembg", sys.modules)
        finally:
            sys.modules.update(saved)

    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_a_broken_first_use_raises_art_cutout_unavailable(self):
        real_import = builtins.__import__

        def _raising_import(name, *args, **kwargs):
            if name == "rembg" or name.startswith("rembg."):
                raise ImportError("rembg is broken on this checkout")
            return real_import(name, *args, **kwargs)

        backend = self._backend()
        with mock.patch("builtins.__import__", side_effect=_raising_import):
            with self.assertRaises(CutoutError) as caught:
                backend.remove_background(_opaque_png())
        self.assertEqual(caught.exception.code, "art_cutout_unavailable")


if __name__ == "__main__":
    unittest.main()
