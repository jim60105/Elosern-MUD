"""Shared lock and fingerprint chain for the static showcase builds.

The Evennia test runner is parallel (``--parallel 4`` in CI): multiple
worker processes share one checkout, and more than one worker needs both
static build outputs — the app ``dist`` (``pnpm run build``; B1's and C1's
vite-build evidence) and ``.storybook-out`` (``pnpm run build-storybook``;
the B1 showcase gate plus the B2/B3 family classes). Two races follow:

1. ``vite build`` runs with ``emptyOutDir: true``, so a worker rebuilding
   ``web/static/webclient/app/dist`` wipes it while another worker is
   reading its entries — or while ``storybook build`` copies
   ``web/static`` (``staticDirs`` serves the dist into the showcase). The
   vite build therefore takes the SAME process-wide exclusive ``fcntl``
   lock as the storybook build: one critical section for both builders and
   for every read of a build output.
2. Under ``--parallel 4`` every evidence class would otherwise pay a fresh
   build. A content fingerprint of each build's inputs is written into the
   build output after a green build; a worker finding a matching
   fingerprint reuses the output instead of rebuilding (rebuild only on
   mismatch). The fingerprint proves a green build of these exact inputs
   in this checkout, so reusing it is the same gate evidence, not a skip.

The lock file lives at the repo root (``.storybook-out.lock``), OUTSIDE the
build output directories: both builders wipe their output at the start of a
build, so locking a file inside an output means the build itself unlinks
the very inode that is locked; a second worker recreating the lock file
would then "acquire" the lock concurrently and the two builds interleave.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import subprocess
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = REPO_ROOT / ".storybook-out.lock"
DIST_ROOT = REPO_ROOT / "web/static/webclient/app/dist"
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"

# Marker files live INSIDE the build outputs on purpose: a wiped output
# loses its marker with it, so a missing/blank output can never look fresh.
_DIST_MARKER = DIST_ROOT / ".build-fingerprint"
_STORYBOOK_MARKER = STORYBOOK_OUT / ".build-fingerprint"

# Directories pruned from every fingerprint walk: installed packages and the
# two build outputs are inputs' environment, not inputs, and walking
# node_modules per worker would dominate the digest cost.
_PRUNED_DIRS = frozenset(
    {"node_modules", "dist", ".storybook-out", "__pycache__", ".vite"}
)


@contextlib.contextmanager
def showcase_build_lock() -> Iterator[None]:
    """Hold the exclusive showcase build lock for the ``with`` block."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _digest_tree(*roots: Path) -> str:
    """Hash every file under ``roots`` (relative path + content)."""
    digest = hashlib.sha256()
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if any(part in _PRUNED_DIRS for part in path.parts):
                continue
            if path.is_file():
                files.append(path)
    for path in sorted(files, key=lambda p: str(p.relative_to(REPO_ROOT))):
        digest.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _app_inputs_fingerprint() -> str:
    """Content fingerprint of everything ``vite build`` consumes."""
    digest = hashlib.sha256()
    digest.update(_digest_tree(REPO_ROOT / "web/webclient-app").encode())
    # The CJS-interop plugin transforms sources under the served static js
    # tree, so those UMD modules are build inputs too.
    digest.update(_digest_tree(REPO_ROOT / "web/static/webclient/js").encode())
    for extra in (
        REPO_ROOT / "vite.config.js",
        REPO_ROOT / "package.json",
        REPO_ROOT / "pnpm-lock.yaml",
    ):
        digest.update(extra.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _storybook_inputs_fingerprint(app_fingerprint: str) -> str:
    """Content fingerprint of everything ``build-storybook`` consumes.

    Includes the app fingerprint because ``staticDirs`` copies
    ``web/static`` — a stale dist under a fresh storybook marker must
    invalidate the showcase.
    """
    digest = hashlib.sha256()
    digest.update(app_fingerprint.encode())
    digest.update(b"\0")
    digest.update(_digest_tree(REPO_ROOT / ".storybook").encode())
    digest.update((REPO_ROOT / "package.json").read_bytes())
    digest.update(b"\0")
    return digest.hexdigest()


def _marker_matches(marker: Path, fingerprint: str) -> bool:
    try:
        return marker.read_text(encoding="utf-8").strip() == fingerprint
    except OSError:
        return False


def _write_marker(marker: Path, fingerprint: str) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(fingerprint + "\n", encoding="utf-8")


def _run_npm(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["npm", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ensure_app_dist() -> None:
    """Ensure a green ``pnpm run build`` covers the current inputs.

    MUST be called while holding :func:`showcase_build_lock` (the vite
    build wipes and repopulates ``dist/assets`` while storybook copies and
    evidence tests read it). Rebuilds only when the input fingerprint
    recorded in the output does not match the current sources. Raises
    ``AssertionError`` when a needed build fails — never returns silently
    over a red build.
    """
    fingerprint = _app_inputs_fingerprint()
    if (
        _marker_matches(_DIST_MARKER, fingerprint)
        and (DIST_ROOT / "index.js").is_file()
        and (DIST_ROOT / "index.css").is_file()
    ):
        return
    result = _run_npm(["run", "build"], timeout=600)
    assert (
        result.returncode == 0
    ), "vite build failed under evidence:\n" + result.stdout + result.stderr
    _write_marker(_DIST_MARKER, fingerprint)


def ensure_storybook_out() -> None:
    """Ensure a green storybook static build covers the current inputs.

    MUST be called while holding :func:`showcase_build_lock`. Refreshes the
    app ``dist`` first (the showcase copies it through ``staticDirs``), then
    rebuilds ``.storybook-out`` only on fingerprint mismatch. Raises
    ``AssertionError`` when a needed build fails.
    """
    ensure_app_dist()
    fingerprint = _storybook_inputs_fingerprint(_app_inputs_fingerprint())
    if (
        _marker_matches(_STORYBOOK_MARKER, fingerprint)
        and (STORYBOOK_OUT / "iframe.html").is_file()
        and (STORYBOOK_OUT / "index.json").is_file()
    ):
        return
    result = _run_npm(["run", "build-storybook"], timeout=900)
    assert (
        result.returncode == 0
    ), "Storybook build failed under showcase evidence:\n" + result.stdout + result.stderr
    _write_marker(_STORYBOOK_MARKER, fingerprint)
