"""Repository-wide regression for scripts/prepare-official-artwork.sh.

The one-shot preparation service (official-artwork-deployment) is the only
place in the project that extracts an archive: the game process reads the
official-artwork volume as-is and never extracts or fetches anything. The
script therefore owns the whole safety contract — refusing unsafe members under
finite caps, extracting into a fresh staging directory, and installing the
finished tree by renames so a failed or interrupted run leaves the previously
prepared tree byte-for-byte unchanged.

The tests drive the real script with ``/bin/sh`` against temporary volumes and
archives built in-process with ``tarfile``: no database, no container, no
network, and no shipped artwork (fixtures are synthetic bytes).
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "prepare-official-artwork.sh"

_GOOD_TREE = {
    "monster/alpha_wolf/portrait.png": b"\x89PNG\r\n\x1a\n-alpha\n",
    "preset/example_preset/portrait.png": b"\x89PNG\r\n\x1a\n-preset\n",
    "LICENSE": b"Artwork license notice\n",
}
_REPLACEMENT_TREE = {"npc/example_contact/portrait.png": b"\x89PNG\r\n\x1a\n-npc\n"}


def _digests(tree: dict[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha256(payload).hexdigest() for name, payload in tree.items()}


def _snapshot(root: Path) -> dict[str, str]:
    """Relative path -> content digest for every file under ``root``."""
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_archive(path: Path, tree: dict[str, bytes], mode: str = "w") -> None:
    with tarfile.open(path, mode) as archive:
        for name, payload in tree.items():
            if payload is None:  # a directory member
                info = tarfile.TarInfo(name)
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                archive.addfile(info)
                continue
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def _write_single_member_archive(path: Path, member: tarfile.TarInfo) -> None:
    """Write an archive holding exactly one (possibly hostile) member."""
    member.size = 0
    with tarfile.open(path, "w") as archive:
        archive.addfile(member, io.BytesIO(b""))


class _PreparationFixture:
    """Temporary volume, archive folder, and the script's environment."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.base = Path(self.tempdir.name)
        # ``volume`` stands in for the mounted ``evennia-art-official`` volume:
        # only its ``content`` subdirectory is ever replaced.
        self.volume = self.base / "volume"
        self.content = self.volume / "content"
        self.archives = self.base / "archives"
        self.archives.mkdir(parents=True)

    def prepare(self, archive: str | None = None, env: dict[str, str] | None = None):
        """Run the script once against this fixture's volume."""
        script_env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.base),
            "ART_OFFICIAL_CONTENT_DIR": str(self.content),
            "ART_OFFICIAL_ARCHIVE_DIR": str(self.archives),
        }
        if archive is not None:
            script_env["ART_OFFICIAL_ARCHIVE"] = archive
        script_env.update(env or {})
        return subprocess.run(
            ["/bin/sh", str(SCRIPT_PATH)],
            env=script_env,
            capture_output=True,
            text=True,
        )

    def assert_no_leftovers(self) -> None:
        if not self.volume.exists():
            return
        stray = sorted(
            entry.name
            for entry in self.volume.iterdir()
            if entry.name.startswith(".content.")
        )
        self.assertEqual(stray, [], "staging/previous directories were left behind")

    def seed_content(self, tree: dict[str, bytes] | None = None) -> None:
        for name, payload in (tree or _GOOD_TREE).items():
            target = self.content / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)


class PreparationScriptContractTests(_PreparationFixture, unittest.TestCase):
    def test_the_script_is_posix_shell_syntax_and_never_fetches_anything(self):
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(SCRIPT_PATH)], capture_output=True, text=True
        )
        self.assertEqual(syntax.returncode, 0, msg=syntax.stderr)
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        for fetch_tool in ("git ", "curl", "wget", "aws", "rclone", "s3cmd"):
            with self.subTest(tool=fetch_tool):
                self.assertNotIn(fetch_tool, source)

    def test_a_valid_archive_populates_the_content_subdirectory(self):
        _write_archive(self.archives / "official.tar", _GOOD_TREE)
        # The volume root is never replaced: a sibling of the content
        # subdirectory survives, matching the ART_OFFICIAL_ROOT subdirectory
        # rule for named-volume deployments.
        self.volume.mkdir(parents=True)
        (self.volume / "keepme.txt").write_text("volume root\n")

        result = self.prepare("official.tar")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(_snapshot(self.content), _digests(_GOOD_TREE))
        self.assertEqual(
            (self.volume / "keepme.txt").read_text(encoding="utf-8"),
            "volume root\n",
        )
        self.assert_no_leftovers()

    def test_a_gzip_compressed_archive_is_extracted(self):
        # Uncompressed and gzip-compressed tar archives are the inputs the
        # runtime image's native tooling (tar + gzip) can read.
        _write_archive(self.archives / "official.tar.gz", _GOOD_TREE, mode="w:gz")

        result = self.prepare("official.tar.gz")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(_snapshot(self.content), _digests(_GOOD_TREE))

    def test_a_bare_name_resolves_inside_the_archive_directory(self):
        _write_archive(self.archives / "official.tar", _GOOD_TREE)

        result = self.prepare("official.tar")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(str(self.archives / "official.tar"), result.stderr)

    def test_replacing_a_prepared_tree_installs_only_the_new_tree(self):
        _write_archive(self.archives / "first.tar", _GOOD_TREE)
        _write_archive(self.archives / "second.tar", _REPLACEMENT_TREE)
        self.assertEqual(self.prepare("first.tar").returncode, 0)

        result = self.prepare("second.tar")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(_snapshot(self.content), _digests(_REPLACEMENT_TREE))
        self.assert_no_leftovers()

    def test_no_archive_supplied_is_a_no_op_that_erases_nothing(self):
        self.seed_content()
        before = _snapshot(self.content)

        result = self.prepare()

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("no archive supplied", result.stderr)
        self.assertEqual(_snapshot(self.content), before)
        self.assert_no_leftovers()

    def test_no_archive_supplied_creates_nothing_on_an_empty_volume(self):
        result = self.prepare()

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertFalse(self.content.exists())

    def test_a_missing_or_non_file_archive_is_an_error_not_a_no_op(self):
        self.seed_content()
        before = _snapshot(self.content)
        (self.archives / "a-directory").mkdir()

        for value in ("absent.tar", "a-directory"):
            with self.subTest(archive=value):
                result = self.prepare(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("not a regular file", result.stderr)
                self.assertEqual(_snapshot(self.content), before)

    def test_a_corrupt_archive_leaves_the_prepared_tree_byte_for_byte_unchanged(self):
        self.seed_content()
        before = _snapshot(self.content)
        (self.archives / "corrupt.tar.gz").write_bytes(b"not a tar archive at all")

        result = self.prepare("corrupt.tar.gz")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a readable tar archive", result.stderr)
        self.assertEqual(_snapshot(self.content), before)
        self.assert_no_leftovers()

    def test_unsafe_members_are_refused_and_the_prepared_tree_is_unchanged(self):
        self.seed_content()
        before = _snapshot(self.content)
        traversal = tarfile.TarInfo("../escaped/portrait.png")
        absolute = tarfile.TarInfo("/etc/escaped.conf")
        symlink = tarfile.TarInfo("monster/alpha_wolf/link.png")
        symlink.type = tarfile.SYMTYPE
        symlink.linkname = "/etc"
        hardlink = tarfile.TarInfo("monster/alpha_wolf/hard.png")
        hardlink.type = tarfile.LNKTYPE
        hardlink.linkname = "monster/alpha_wolf/portrait.png"
        fifo = tarfile.TarInfo("monster/alpha_wolf/pipe")
        fifo.type = tarfile.FIFOTYPE
        device = tarfile.TarInfo("monster/alpha_wolf/device")
        device.type = tarfile.CHRTYPE
        device.devmajor, device.devminor = 1, 3
        cases = (
            ("traversal.tar", traversal, "parent-directory traversal"),
            ("absolute.tar", absolute, "absolute path"),
            ("symlink.tar", symlink, "link entry"),
            ("hardlink.tar", hardlink, "link entry"),
            ("fifo.tar", fifo, "non-regular archive member"),
            ("device.tar", device, "non-regular archive member"),
        )

        for filename, member, message in cases:
            with self.subTest(member=filename):
                _write_single_member_archive(self.archives / filename, member)
                result = self.prepare(filename)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(_snapshot(self.content), before)
                self.assertFalse((self.base / "escaped").exists())
                self.assert_no_leftovers()

    def test_the_extraction_step_refuses_traversal_and_relocates_absolute_members(self):
        # Belt-and-suspenders for the listing parser above: even if a hostile
        # member reached extraction, the tar invocation the script uses must
        # never write outside its staging directory. Traversal members are
        # refused outright and absolute members are relocated inside the target
        # by the leading-slash strip — which is exactly why the parser refuses
        # absolute names before extraction instead of trusting that relocation.
        target = self.base / "target"
        target.mkdir()
        invocation = [
            "tar",
            "-xf",
            "",
            "--no-same-owner",
            "--no-same-permissions",
            "-C",
            str(target),
        ]

        traversal = self.archives / "traversal.tar"
        _write_archive(traversal, {"../escaped.png": b"poison\n"})
        invocation[2] = str(traversal)
        refused = subprocess.run(invocation, capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(_snapshot(target), {})
        self.assertFalse((self.base / "escaped.png").exists())

        outside = self.base / "escape-dir" / "poison.png"
        absolute = self.archives / "absolute.tar"
        _write_archive(absolute, {str(outside): b"poison\n"})
        invocation[2] = str(absolute)
        relocated = subprocess.run(invocation, capture_output=True, text=True)
        self.assertEqual(relocated.returncode, 0, msg=relocated.stderr)
        self.assertFalse(outside.exists())
        self.assertEqual(
            sorted(path.name for path in target.rglob("*") if path.is_file()),
            ["poison.png"],
        )

    def test_the_entry_count_and_size_caps_are_enforced(self):
        self.seed_content()
        before = _snapshot(self.content)
        _write_archive(self.archives / "official.tar", _GOOD_TREE)
        cases = (
            ({"ART_OFFICIAL_MAX_ENTRIES": "2"}, "more than 2 members"),
            ({"ART_OFFICIAL_MAX_FILE_BYTES": "8"}, "ART_OFFICIAL_MAX_FILE_BYTES"),
            ({"ART_OFFICIAL_MAX_TOTAL_BYTES": "12"}, "ART_OFFICIAL_MAX_TOTAL_BYTES"),
        )

        for env, message in cases:
            with self.subTest(**env):
                result = self.prepare("official.tar", env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(_snapshot(self.content), before)
                self.assert_no_leftovers()

    def test_invalid_cap_settings_are_refused_before_the_volume_is_touched(self):
        self.seed_content()
        before = _snapshot(self.content)
        _write_archive(self.archives / "official.tar", _GOOD_TREE)

        # An empty value means "use the default" (the shell's :- operator);
        # a malformed or non-positive value must fail before any write.
        for value in ("twenty", "0", "-1"):
            with self.subTest(ART_OFFICIAL_MAX_ENTRIES=value):
                result = self.prepare(
                    "official.tar", {"ART_OFFICIAL_MAX_ENTRIES": value}
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ART_OFFICIAL_MAX_ENTRIES", result.stderr)
                self.assertEqual(_snapshot(self.content), before)

    def test_an_interrupted_install_is_recovered_by_the_next_run(self):
        _write_archive(self.archives / "official.tar", _GOOD_TREE)
        self.volume.mkdir(parents=True)
        orphan_previous = self.volume / ".content.previous.4242"
        orphan_previous.mkdir()
        (orphan_previous / "portrait.png").write_bytes(b"last good tree\n")

        result = self.prepare("official.tar")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("restoring", result.stderr)
        self.assertEqual(_snapshot(self.content), _digests(_GOOD_TREE))
        self.assert_no_leftovers()

    def test_a_stale_previous_tree_and_staging_directory_are_cleaned_up(self):
        self.seed_content()
        _write_archive(self.archives / "official.tar", _GOOD_TREE)
        stale_previous = self.volume / ".content.previous.4243"
        stale_previous.mkdir()
        (stale_previous / "portrait.png").write_bytes(b"stale\n")
        stale_staging = self.volume / ".content.prepare.4244"
        stale_staging.mkdir()
        (stale_staging / "portrait.png").write_bytes(b"stale\n")

        result = self.prepare("official.tar")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("removing leftover staging directory", result.stderr)
        self.assertEqual(_snapshot(self.content), _digests(_GOOD_TREE))
        self.assert_no_leftovers()


class PreparationScriptScopeTests(unittest.TestCase):
    def test_the_game_never_runs_the_preparation_script(self):
        # The extraction path is deployment tooling: the evennia startup script
        # must not reference it, and the game service must not mount it.
        entrypoint = (REPO_ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
        self.assertNotIn("prepare-official-artwork", entrypoint)
        self.assertNotIn("art-official", entrypoint)


if __name__ == "__main__":
    unittest.main()
