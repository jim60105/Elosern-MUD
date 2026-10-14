"""Evidence bridge: run the shared image-loading Vitest gates as evidence.

The ordered image-attempt lifecycle of unified-image-loading-core is
implemented and verified in the Vue layer: the core reducer suite
(web/webclient-app/tests/core/image_attempts.test.js) asserts the canonical
rank order, canonical resource-key dedup, reached-only fault accumulation and
safe exhaustion; the editors suite
(web/webclient-app/tests/components/gallery_original_editors.test.js) asserts
the epoch-bound callbacks, the same-render no-retry, the availability
transitions, the geometry-only byte reuse and the bounded ArtworkFailure
category mapping. ``covers_requirement`` can only attach to a Python
``test_*`` function, so this module executes those gates and asserts they
pass; each annotation links one image-attempt-lifecycle main-spec requirement
to its substantively matching, executed evidence record
(webclient-gallery-ui / webclient-vue-application evidence-bridge precedent).

Test-to-requirement mapping:

- ``image-attempt-lifecycle::one-load-lifecycle-resolves-ordered-attempts``:
  ``test_ordered_lifecycle_reducer_passes`` (the canonical rank order, the
  dedup-then-order rule, the lower success retaining the earlier reached
  fault, the unreached fault staying invisible and the single terminal
  exhaustion are asserted in the core suite).
- ``image-attempt-lifecycle::attempt-callbacks-belong-to-the-active-revision``:
  ``test_attempt_callbacks_are_revision_bound`` (a superseded epoch or
  mismatched key cannot settle the state; a retired subject's late decode is
  rejected; each event binds to the element's own attempt; unchanged
  descriptors re-render with no new request; teardown disposes listeners).
- ``image-attempt-lifecycle::unexpected-failures-remain-locally-accessible``:
  ``test_failure_mapping_is_bounded`` (ArtworkFailure renders the bounded
  category text for a reached failure and nothing for expected absence; the
  browser journey test_browser_image_loading_core pins the persistent local
  marker separately).
- ``image-attempt-lifecycle::geometry-only-changes-reuse-successful-bytes``:
  ``test_geometry_only_revision_reuses_decoded_bytes`` (geometry is kept out
  of the resolution facts, and a geometry-only update reuses the decoded
  original with no new request and no source-key change, in the driver and in
  the face-rect editor).
- ``image-attempt-lifecycle::required-panel-failures-enter-the-common-availability-state``:
  ``test_required_panel_availability_states`` (first render on a failed
  availability is unavailable with no request, expected absence stays a normal
  non-error absence, and a turn to failed invalidates a prior success; the
  browser journey pins the editor-side save gate separately).
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"
CORE_ATTEMPTS = TESTS_DIR / "core" / "image_attempts.test.js"
ORIGINAL_EDITORS = TESTS_DIR / "components" / "gallery_original_editors.test.js"

# The vitest file-set results executed once per process (cold starts are
# shared); each annotated test asserts its own substantive mapping against the
# shared execution evidence.
_VITEST_RESULTS: dict[tuple[str, ...], subprocess.CompletedProcess[str]] = {}


def _run_vitest_once(*test_files: Path) -> subprocess.CompletedProcess[str]:
    """Run each vitest file-set once per process (cold starts are shared)."""
    key = tuple(str(p) for p in test_files)
    if key not in _VITEST_RESULTS:
        _VITEST_RESULTS[key] = subprocess.run(
            ["npx", "--no-install", "vitest", "run", *key],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
    return _VITEST_RESULTS[key]


def _assert_vitest_passes(result, label):
    assert result.returncode == 0, (
        f"{label} Vitest suite failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "passed" in result.stdout, f"{label}: expected a passing suite summary"


class VueImageLoadingEvidenceTest(unittest.TestCase):
    """Execute the image-loading Vitest gates as requirement evidence."""

    @covers_requirement(
        "image-attempt-lifecycle::one-load-lifecycle-resolves-ordered-attempts"
    )
    def test_ordered_lifecycle_reducer_passes(self):
        """The core ordered-attempt reducer suite passes."""
        _assert_vitest_passes(
            _run_vitest_once(CORE_ATTEMPTS), "image-attempt core reducer"
        )

    @covers_requirement(
        "image-attempt-lifecycle::attempt-callbacks-belong-to-the-active-revision"
    )
    def test_attempt_callbacks_are_revision_bound(self):
        """Epoch-bound callbacks, replacement and no-retry pass end to end."""
        _assert_vitest_passes(
            _run_vitest_once(CORE_ATTEMPTS, ORIGINAL_EDITORS),
            "image-attempt callback binding",
        )

    @covers_requirement(
        "image-attempt-lifecycle::unexpected-failures-remain-locally-accessible"
    )
    def test_failure_mapping_is_bounded(self):
        """The bounded ArtworkFailure category mapping passes."""
        _assert_vitest_passes(
            _run_vitest_once(ORIGINAL_EDITORS), "artwork failure mapping"
        )

    @covers_requirement(
        "image-attempt-lifecycle::geometry-only-changes-reuse-successful-bytes"
    )
    def test_geometry_only_revision_reuses_decoded_bytes(self):
        """Geometry-only revisions keep resolution facts and reuse bytes."""
        _assert_vitest_passes(
            _run_vitest_once(CORE_ATTEMPTS, ORIGINAL_EDITORS),
            "geometry-only byte reuse",
        )

    @covers_requirement(
        "image-attempt-lifecycle::required-panel-failures-enter-the-common-availability-state"
    )
    def test_required_panel_availability_states(self):
        """The shared availability states drive the panel without invention."""
        _assert_vitest_passes(
            _run_vitest_once(ORIGINAL_EDITORS), "required-panel availability"
        )


if __name__ == "__main__":
    unittest.main()
