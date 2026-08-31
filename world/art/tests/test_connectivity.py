"""Tests for the diagnostic connectivity probe and its never-gating boundary.

Deterministic and socket-free: the client seam is patched, the clock is
injected through the module-level ``_now`` seam, and the import boundary is
enforced by AST-parsing every production module in the package.
"""

import ast
from contextlib import contextmanager
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.art import connectivity
from world.art.connectivity import ProbeResult, probe
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.queue import ensure, record_key
from world.art.sd_worker import SDWebUIClient, SDError
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import drain_synchronous

class _FakeClock:
    """A manually advanced monotonic clock for TTL/age assertions."""

    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@contextmanager
def _clock(seconds: float = 1000.0):
    fake = _FakeClock(seconds)
    with patch.object(connectivity, "_now", fake):
        yield fake


class ProbeTests(unittest.TestCase):
    def setUp(self):
        connectivity._reset_for_testing()
        self.addCleanup(connectivity._reset_for_testing)
        self.client = FakeSDWebUIClient()

    def _probe(self, *, force=False, client=None):
        target = self.client if client is None else client
        with patch("world.art.connectivity.resolve_sd_client", return_value=target):
            return probe(force=force)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_reachable_server_yields_clean_ok_verdict(self):
        with _clock() as clock:
            result = self._probe()
        self.assertTrue(result.ok)
        self.assertIsNone(result.code)
        self.assertFalse(result.from_cache)
        self.assertEqual(result.checked_at, 1000.0)
        self.assertEqual(result.age_seconds, 0.0)
        self.assertEqual(self.client.probe_calls, [5.0])

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_named_error_code_becomes_failed_verdict_never_exception(self):
        self.client.fail_probe(SDError("sd_http_error", "HTTP 500"))
        with _clock():
            result = self._probe()
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "sd_http_error")

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_fresh_cache_entry_is_reused_without_a_request(self):
        with _clock() as clock:
            first = self._probe()
            clock.advance(299)
            second = self._probe()
        self.assertFalse(first.from_cache)
        self.assertTrue(second.from_cache)
        self.assertEqual(second.age_seconds, 299.0)
        self.assertEqual(self.client.probe_calls, [5.0])  # exactly one call

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_ttl_expiry_forces_a_fresh_probe(self):
        with _clock() as clock:
            self._probe()
            clock.advance(301)
            second = self._probe()
        self.assertFalse(second.from_cache)
        self.assertEqual(len(self.client.probe_calls), 2)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_forced_probe_bypasses_young_entry(self):
        with _clock() as clock:
            self._probe()
            clock.advance(1)
            forced = self._probe(force=True)
        self.assertFalse(forced.from_cache)
        self.assertEqual(len(self.client.probe_calls), 2)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_every_fingerprint_component_misses_the_cache(self):
        for override in (
            {"ART_SD_BASE_URL": "http://127.0.0.1:7861"},
            {"ART_SD_USERNAME": "someone"},
            {"ART_SD_PASSWORD": "secret"},
            {"ART_SD_PROBE_TIMEOUT_MS": 2_000},
        ):
            with self.subTest(**override):
                connectivity._reset_for_testing()
                calls_before = len(self.client.probe_calls)
                with _clock():
                    self._probe()  # seed the cache with baseline settings
                    with override_settings(**override):
                        second = self._probe()
                self.assertFalse(
                    second.from_cache, msg=f"{override} reused the cache"
                )
                self.assertEqual(len(self.client.probe_calls), calls_before + 2)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_probe_timeout_knob_reaches_the_seam(self):
        with _clock(), override_settings(ART_SD_PROBE_TIMEOUT_MS=2_000):
            self._probe()
        self.assertEqual(self.client.probe_calls, [2.0])

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_userinfo_url_leaks_nothing_into_verdict_or_cache(self):
        with _clock(), override_settings(
            ART_SD_BASE_URL="http://user:password@example.test:7860/",
            ART_SD_USERNAME="u",
            ART_SD_PASSWORD="p",
        ):
            result = self._probe()
            slot = connectivity._cache_slot
        self.assertEqual(result.host, "example.test:7860")
        for text in (repr(result), repr(slot)):
            for forbidden in ("user", "password", "u@", "p@", "@", "netloc"):
                self.assertNotIn(forbidden, text)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_bare_host_url_has_no_port_suffix(self):
        with _clock(), override_settings(ART_SD_BASE_URL="http://sd.internal"):
            result = self._probe()
        self.assertEqual(result.host, "sd.internal")

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_invalid_client_seam_yields_internal_error_verdict(self):
        with _clock(), override_settings(ART_SD_CLIENT="nope.NotAClass"):
            result = probe()
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "sd_internal_error")
        self.assertEqual(result.host, connectivity.UNKNOWN_HOST)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_unexpected_seam_exception_yields_internal_error(self):
        class _Boom(FakeSDWebUIClient):
            def probe_samplers(self, *, timeout_seconds: float) -> None:
                raise RuntimeError("boom")

        with _clock():
            result = self._probe(client=_Boom())
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "sd_internal_error")

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_malformed_base_url_never_raises(self):
        with _clock(), override_settings(ART_SD_BASE_URL="http://[::1"):
            result = self._probe()
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "sd_internal_error")
        self.assertEqual(result.host, connectivity.UNKNOWN_HOST)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_concurrent_unforced_callers_share_one_probe(self):
        gate = threading.Event()

        class _Slow(FakeSDWebUIClient):
            def probe_samplers(self, *, timeout_seconds: float) -> None:
                super().probe_samplers(timeout_seconds=timeout_seconds)
                gate.wait(2)

        slow = _Slow()
        results: list[ProbeResult] = []

        def _run():
            results.append(probe())

        # Patch in the MAIN thread only: nested patch enter/exit across two
        # threads leaks the inner value on teardown (whichever exits second
        # restores its own patch).
        with (
            _clock(),
            patch("world.art.connectivity.resolve_sd_client", return_value=slow),
        ):
            first = threading.Thread(target=_run)
            first.start()
            time.sleep(0.05)  # let the first caller enter the seam
            second = threading.Thread(target=_run)
            second.start()
            gate.set()
            first.join(5)
            second.join(5)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(slow.probe_calls), 1)
        self.assertEqual(sorted(r.from_cache for r in results), [False, True])

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_stale_completion_never_overwrites_a_newer_slot(self):
        with _clock() as clock:
            self._probe()  # slot timestamp 1000.0
            clock.now = 900.0  # simulate an older in-flight probe completing late
            forced = self._probe(force=True)
            self.assertFalse(forced.from_cache)
            self.assertEqual(connectivity._cache_slot[2], 1000.0)

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_probe_with_prepin_enabled_issues_only_the_samplers_get(self):
        requests: list[tuple[str, object]] = []

        def _record_http_request(url, payload, timeout_seconds=None):
            requests.append((url, payload))
            return ["Euler a"]

        with (
            override_settings(
                ART_SD_PREPIN_SAMPLES_FORMAT=True,
                ART_SD_CLIENT="world.art.sd_worker.SDWebUIClient",
            ),
            patch("world.art.sd_worker._http_request", _record_http_request),
            patch(
                "world.art.sd_worker._http_json",
                side_effect=AssertionError("pre-pin must not run for a probe"),
            ),
        ):
            result = probe(force=True)
        self.assertTrue(result.ok)
        self.assertEqual(
            [url for url, _ in requests],
            ["http://127.0.0.1:7860/sdapi/v1/samplers"],
        )

    def test_constructing_the_real_client_issues_no_http(self):
        # D1a invariant: the pre-pin (which mutates the server) is not a
        # constructor side effect any more.
        with (
            override_settings(ART_SD_PREPIN_SAMPLES_FORMAT=True),
            patch(
                "world.art.sd_worker._http_json",
                side_effect=AssertionError("constructor must not touch HTTP"),
            ),
            patch(
                "world.art.sd_worker._http_request",
                side_effect=AssertionError("constructor must not touch HTTP"),
            ),
        ):
            SDWebUIClient()

    @covers_requirement(
        "art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises"
    )
    def test_userinfo_is_not_a_fingerprint_component(self):
        # duck run-2: userinfo must not become (offline-guessable) cache
        # material, and it never affects a request — so it is not identity.
        with _clock():
            self._probe()  # seeds the slot with the bare target
            digest_without = connectivity._cache_slot[0]
            connectivity._reset_for_testing()
            self._probe()  # same configuration again
            digest_again = connectivity._cache_slot[0]
            with override_settings(
                ART_SD_BASE_URL="http://user:password@127.0.0.1:7860"
            ):
                forced = self._probe(force=True)
                digest_with = connectivity._cache_slot[0]
                young = self._probe()
        self.assertEqual(digest_without, digest_again)
        self.assertEqual(digest_with, digest_without)
        self.assertTrue(forced.ok)
        # Unforced read under the userinfo-only configuration still matches.
        self.assertTrue(young.ok)
        self.assertTrue(young.from_cache)

    @covers_requirement(
        "art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises"
    )
    def test_a_broken_clock_still_returns_a_verdict(self):
        # The absolute boundary must survive its OWN recovery path failing:
        # the first _now() breaks inside the inner arm, the second breaks in
        # the inner handler, and the absolute fallback uses no clock at all.
        attempts = iter((1_000.0,))

        def _flaky_clock() -> float:
            return next(attempts)

        class _Boom(FakeSDWebUIClient):
            def probe_samplers(self, *, timeout_seconds: float) -> None:
                raise RuntimeError("boom")  # forces the inner handler path

        with patch.object(connectivity, "_now", _flaky_clock):
            result = self._probe(client=_Boom())
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "sd_internal_error")
        self.assertEqual(result.host, connectivity.UNKNOWN_HOST)
        self.assertEqual(result.checked_at, connectivity._FALLBACK_CHECKED_AT)

    @covers_requirement(
        "art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises"
    )
    def test_lock_failure_yields_a_verdict_not_an_exception(self):
        class _BrokenLock:
            def __enter__(self):
                raise RuntimeError("lock is broken")

            def __exit__(self, *exc_info):
                return False

        with patch.object(connectivity, "_cache_lock", _BrokenLock()):
            result = probe()
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "sd_internal_error")
        self.assertEqual(result.host, connectivity.UNKNOWN_HOST)


# --- AST import boundary (design D2, duck run-1: spellings + fixtures) -----

_CONNECTIVITY_MODULES = {"world.art.connectivity", "connectivity"}

_WORLD_ART_ROOT = Path(connectivity.__file__).parent


def _imports_connectivity(source: str) -> bool:
    """True when source imports world.art.connectivity by ANY spelling."""
    tree = ast.parse(source)
    # duck run-2: dynamic import may be reached through an ALIASED binding
    # (`from importlib import import_module as load`); track those names.
    dynamic_bound: set[str] = set()
    importlib_bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    importlib_bound.add(alias.asname or "importlib")
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            if node.module in ("importlib", "builtins"):
                for alias in node.names:
                    if alias.name in ("import_module", "__import__"):
                        dynamic_bound.add(alias.asname or alias.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name in _CONNECTIVITY_MODULES for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and (
                module in ("", "art", "world.art") or module.endswith(".art")
            ):
                # relative: `from . import connectivity`, `from ..art import connectivity`
                if any(alias.name in _CONNECTIVITY_MODULES for alias in node.names):
                    return True
            if module in _CONNECTIVITY_MODULES:
                return True
            if module == "world.art" and any(
                alias.name in _CONNECTIVITY_MODULES for alias in node.names
            ):
                return True
        elif isinstance(node, ast.Call):
            func = node.func
            is_dynamic = (
                isinstance(func, ast.Name)
                # __import__ is ALWAYS available as a builtin.
                and (func.id == "__import__" or func.id in dynamic_bound)
            ) or (
                isinstance(func, ast.Attribute)
                and func.attr == "import_module"
                and isinstance(func.value, ast.Name)
                and func.value.id in importlib_bound
            )
            if is_dynamic:
                if node.args and isinstance(node.args[0], ast.Constant):
                    value = node.args[0].value
                    if isinstance(value, str) and value in _CONNECTIVITY_MODULES:
                        return True
    return False


class ImportBoundaryTests(unittest.TestCase):
    """The probe is diagnostic: NOTHING else in world/art may import it."""

    @covers_requirement("art-service-connectivity-surface::connectivity-state-never-gates-generation")
    def test_no_production_module_imports_connectivity(self):
        offenders = []
        for path in sorted(_WORLD_ART_ROOT.rglob("*.py")):
            relative_parts = path.relative_to(_WORLD_ART_ROOT).parts
            if "tests" in relative_parts:
                continue
            if path.name == "connectivity.py":
                continue
            if _imports_connectivity(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(_WORLD_ART_ROOT)))
        self.assertEqual(offenders, [])

    @covers_requirement("art-service-connectivity-surface::connectivity-state-never-gates-generation")
    def test_boundary_checker_rejects_every_spelling(self):
        spellings = (
            "import world.art.connectivity\n",
            "import world.art.connectivity as c\n",
            "from world.art import connectivity\n",
            "from world.art.connectivity import probe\n",
            "from . import connectivity\n",
            "from ..art import connectivity\n",
            "import importlib\nimportlib.import_module('world.art.connectivity')\n",
            "__import__('world.art.connectivity')\n",
            "from importlib import import_module as load\n"
            "load('world.art.connectivity')\n",
            "from builtins import __import__ as primal\n"
            "primal('world.art.connectivity')\n",
        )
        for source in spellings:
            with self.subTest(source=source.strip()):
                self.assertTrue(_imports_connectivity(source))
        clean = (
            "from world.art.sd_worker import SDError\n",
            "import world.art.worker\n",
            "from world import art\n",
        )
        for source in clean:
            with self.subTest(clean=source.strip()):
                self.assertFalse(_imports_connectivity(source))


class ProbeSeamTests(unittest.TestCase):
    """Focused behaviour of SDWebUIClient.probe_samplers (design D5)."""

    @staticmethod
    @contextmanager
    def _http(response):
        with patch("world.art.sd_worker._http_request", response) as mock:
            yield mock

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_seam_is_one_get_with_the_caller_timeout(self):
        seen: list[tuple[str, object, float]] = []

        def _record(url, payload, timeout_seconds=None):
            seen.append((url, payload, timeout_seconds))
            return ["a"]

        client = SDWebUIClient()
        with self._http(_record):
            client.probe_samplers(timeout_seconds=1.25)
        self.assertEqual(
            seen, [("http://127.0.0.1:7860/sdapi/v1/samplers", None, 1.25)]
        )

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_seam_accepts_arbitrary_list_items(self):
        # Deliberate: reachability + JSON-list shape only; no item cap, no
        # item-shape checks (that is @art options' job).
        client = SDWebUIClient()
        with self._http(lambda url, payload, timeout_seconds=None: [{"nope": 1}, 7, None]):
            self.assertIsNone(client.probe_samplers(timeout_seconds=1.0))

    @covers_requirement("art-service-connectivity-surface::connectivity-probing-is-bounded-cached-by-effective-configuration-and-never-raises")
    def test_seam_rejects_non_list_with_malformed_response(self):
        client = SDWebUIClient()
        with self._http(lambda url, payload, timeout_seconds=None: {"samplers": []}):
            with self.assertRaises(SDError) as caught:
                client.probe_samplers(timeout_seconds=1.0)
        self.assertEqual(caught.exception.code, "sd_malformed_response")


# --- Never-gating integration (task 4.2) ------------------------------------


class NeverGatingIntegrationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        import tempfile

        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        connectivity._reset_for_testing()
        self.addCleanup(connectivity._reset_for_testing)
        self.settings_overrides = override_settings(
            ART_STORE_ROOT=self.tempdir.name,
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.settings_overrides.enable()

    def tearDown(self):
        self.settings_overrides.disable()
        super().tearDown()

    @covers_requirement("art-service-connectivity-surface::connectivity-state-never-gates-generation")
    def test_failed_verdict_never_blocks_a_recovered_generation(self):
        fake = FakeSDWebUIClient()
        fake.fail_probe()
        subject = ArtSubject(ArtSubjectKind.SCENE, "forest_path")
        ensure(subject, "desc")
        with (
            patch("world.art.connectivity.resolve_sd_client", return_value=fake),
            patch("world.art.worker.resolve_sd_client", return_value=fake),
        ):
            verdict = connectivity.probe()
            self.assertFalse(verdict.ok)
            self.assertEqual(connectivity._cache_slot[1].ok, False)
            fake.recover_probe()
            dispatched = drain_synchronous(1)
        self.assertEqual(dispatched, 1)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/forest_path.png")


if __name__ == "__main__":
    unittest.main()
