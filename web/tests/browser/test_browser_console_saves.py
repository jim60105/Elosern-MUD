"""Private save roots for the managed browser console (browser-console-save-isolation).

The managed runtime must exercise the production save boundary with private
files. These tests establish, without mocking the successful saver:

- the browser settings resolve every path the real snapshot path reads
  (``DATABASES``, ``GM_SAVES_ROOT``, ``ART_STORE_ROOT``) inside the
  invocation's temporary root, and retain the production
  ``GM_AUTOSAVE_KEEP`` meaning;
- two invocations own disjoint roots and teardown removes only their own;
- a real protected console teleport creates a complete pre-intervention save
  under the private root, the saved database still holds the pre-teleport
  location, and the live character commits the target room;
- an injected snapshot failure refuses with ``snapshot_failed`` before any
  mutation and leaves the policy baseline untouched.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

from . import fixtures
from .browser_base import BrowserAcceptanceTest
from .harness import ManagedServer

SAVE_ID_PATTERN = re.compile(r"\d{8}T\d{6}-[0-9a-f]{6}")

#: Production persistence the isolated runtime must never touch.
DEVELOPER_PATHS = (
    fixtures.PROJECT_ROOT / "server" / "db" / "evennia.db3",
    fixtures.PROJECT_ROOT / "server" / "db" / "saves",
    fixtures.PROJECT_ROOT / "server" / ".art",
)

#: Room kinds a teleport can target without entering the pooled wilderness or
#: a temporary instance room.
TELEPORTABLE_KINDS = frozenset({"格線房間", "錨點房間", "虛境", "房間"})


# --- settings probes --------------------------------------------------------


_SETTINGS_PROBE = r"""
import json

from django.conf import settings

from server.saves import snapshot

layout = snapshot.default_layout()
print(json.dumps({
    "database": str(layout.db_file),
    "saves_root": str(layout.saves_root),
    "art_root": str(layout.art_root),
    "autosave_keep": snapshot.autosave_keep(),
    "declared": {
        name: hasattr(settings, name)
        for name in ("GM_SAVES_ROOT", "GM_AUTOSAVE_KEEP")
    },
}))
"""


_RETENTION_PROBE = r"""
import json
import os
import sqlite3
from pathlib import Path

database = Path(os.environ["ELOSERN_BROWSER_DB"])
connection = sqlite3.connect(database)
connection.execute(
    "CREATE TABLE IF NOT EXISTS django_migrations "
    "(id INTEGER PRIMARY KEY, app TEXT, name TEXT, applied TEXT)"
)
connection.execute(
    "INSERT INTO django_migrations (app, name, applied) "
    "VALUES ('synthetic', '0001_initial', '')"
)
connection.commit()
connection.close()

from server.saves import snapshot

layout = snapshot.default_layout()


def metadata():
    return {"players": []}


created = {"auto_intervention": [], "auto_restore": []}
for kind in created:
    for index in range(3):
        info = snapshot.create_snapshot(
            kind,
            f"{kind} {index}",
            layout=layout,
            metadata=metadata,
            clock_reader=lambda path: {"tick": 0},
        )
        created[kind].append(info.id)
manual = snapshot.create_snapshot(
    "manual",
    "manual",
    layout=layout,
    metadata=metadata,
    clock_reader=lambda path: {"tick": 0},
)
print(json.dumps({
    "keep": snapshot.autosave_keep(),
    "created": created,
    "manual": manual.id,
    "layout": {
        "database": str(layout.db_file),
        "saves_root": str(layout.saves_root),
        "art_root": str(layout.art_root),
    },
    "saves": [[save.id, save.kind] for save in snapshot.list_saves(layout=layout)],
}))
"""


def _run_probe(
    runtime: fixtures.BrowserRuntime,
    script: str,
    *,
    env: dict[str, str] | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    """Run one settings probe in a child process bound to ``runtime``."""
    environment = fixtures._base_env(runtime, env)
    # Never inherit the caller's Django settings module: a production value
    # would point the probe's real snapshot path at developer persistence.
    environment["DJANGO_SETTINGS_MODULE"] = fixtures.SEED_SETTINGS_DOTPATH
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(fixtures.PROJECT_ROOT),
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


# --- developer persistence fingerprint --------------------------------------


def _path_fingerprint(path: Path):
    """A byte hash for a file, or a listing/size/mtime digest for a tree."""
    if not path.exists():
        return None
    if path.is_file():
        return ("file", hashlib.sha256(path.read_bytes()).hexdigest())
    digest = hashlib.sha256()
    for child in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        stat = child.stat()
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(f":{stat.st_size}:{stat.st_mtime_ns}\n".encode("ascii"))
    return ("dir", digest.hexdigest())


def _developer_fingerprint() -> dict[str, object]:
    return {str(path): _path_fingerprint(path) for path in DEVELOPER_PATHS}


# --- GM transport helpers ---------------------------------------------------


def _csrf_token(page, base_url: str) -> str:
    """Obtain the token from the portal shell, exactly as the operator does."""
    page.evaluate(
        "async () => { await fetch('/gm/', {credentials: 'same-origin'}); }"
    )
    for cookie in page.context.cookies(base_url):
        if cookie["name"] == "csrftoken":
            return cookie["value"]
    raise AssertionError("/gm/ did not issue a csrftoken cookie")


def _gm_get(page, path: str) -> dict:
    return page.evaluate(
        """async (path) => {
            const response = await fetch(path, {credentials: 'same-origin'});
            return {status: response.status, body: await response.json()};
        }""",
        path,
    )


def _gm_post(page, path: str, body: dict, token: str) -> dict:
    return page.evaluate(
        """async ([path, body, token]) => {
            const response = await fetch(path, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
                body: JSON.stringify(body),
            });
            return {status: response.status, body: await response.json()};
        }""",
        [path, body, token],
    )


def _character_dbref(page) -> str:
    """The seeded runtime's sole player character.

    Under ``ELOSERN_BROWSER_SYNTH_CATALOGS=1`` the seed activates the base
    character from the kit's preset card, which renames it; the dedicated
    runtime therefore owns exactly one player character, whoever the account
    puppets.
    """
    payload = _gm_get(page, "/gm/api/state/characters?limit=200")
    assert payload["status"] == 200, payload["body"]
    items = payload["body"]["data"]["items"]
    assert len(items) == 1, [item["label"] for item in items]
    return f"#{items[0]['dbref']}"


def _current_room(page, character: str) -> str:
    detail = _gm_get(page, f"/gm/api/state/characters/{character.lstrip('#')}")
    assert detail["status"] == 200, detail["body"]
    identity = next(
        section
        for section in detail["body"]["data"]["sections"]
        if section["key"] == "identity"
    )
    row = next(entry for entry in identity["rows"] if entry["label"] == "當前房間")
    identity_id = (row.get("link") or {}).get("id")
    return f"#{identity_id or str(row['value']).lstrip('#')}"


def _destination_room(page, current: str) -> str:
    """The lowest-dbref room that is not ``current`` and not a pooled room."""
    cursor = "/gm/api/state/rooms?limit=200"
    for _page_number in range(5):
        payload = _gm_get(page, cursor)
        assert payload["status"] == 200, payload["body"]
        data = payload["body"]["data"]
        for item in data["items"]:
            dbref = f"#{item['dbref']}"
            if dbref == current:
                continue
            kind = next(
                field["value"] for field in item["fields"] if field["label"] == "地點類型"
            )
            if kind in TELEPORTABLE_KINDS:
                return dbref
        if not data["next_cursor"]:
            break
        cursor = f"/gm/api/state/rooms?limit=200&cursor={data['next_cursor']}"
    raise AssertionError("no teleportable destination room in the managed runtime")


# --- fast configuration and retention coverage ------------------------------


class ConsoleSaveConfigurationTests(unittest.TestCase):
    """The managed settings and retention semantics, without a server boot."""

    def _runtime(self, prefix: str = "elosern-save-config-") -> fixtures.BrowserRuntime:
        runtime = fixtures.create_runtime(prefix=prefix)
        self.addCleanup(runtime.cleanup)
        return runtime

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-uses-an-isolated-managed-evennia-runtime"
    )
    def test_managed_settings_resolve_every_save_path_inside_the_runtime_root(self):
        runtime = self._runtime()
        result = _run_probe(
            runtime, _SETTINGS_PROBE, env={"ELOSERN_BROWSER_AUTOSAVE_KEEP": ""}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual(payload["declared"], {"GM_SAVES_ROOT": True, "GM_AUTOSAVE_KEEP": True})
        self.assertEqual(payload["database"], str(runtime.database_path))
        self.assertEqual(payload["saves_root"], str(runtime.saves_dir))
        self.assertEqual(payload["art_root"], str(runtime.cache_dir / "art"))
        for key in ("database", "saves_root", "art_root"):
            self.assertTrue(
                Path(payload[key]).is_relative_to(runtime.root_dir),
                f"{key} escapes the invocation root: {payload[key]}",
            )
        # Same meaning and default as production (server/conf/settings.py).
        self.assertEqual(payload["autosave_keep"], 10)

        # Omitting only the save-root override keeps saves inside the resolved
        # private cache root (never the imported Evennia cache directory).
        fallback = _run_probe(
            runtime,
            _SETTINGS_PROBE,
            env={
                "ELOSERN_BROWSER_SAVES_ROOT": "",
                "ELOSERN_BROWSER_AUTOSAVE_KEEP": "",
            },
        )
        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        self.assertEqual(
            json.loads(fallback.stdout)["saves_root"],
            str(runtime.cache_dir / "saves"),
        )

        rejected = _run_probe(
            runtime, _SETTINGS_PROBE, env={"ELOSERN_BROWSER_AUTOSAVE_KEEP": "0"}
        )
        self.assertNotEqual(rejected.returncode, 0, "a non-positive retention must fail")
        self.assertIn(
            "ELOSERN_BROWSER_AUTOSAVE_KEEP expected a positive integer",
            rejected.stderr,
        )

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-uses-an-isolated-managed-evennia-runtime"
    )
    def test_two_invocations_own_disjoint_private_roots(self):
        first = self._runtime("elosern-save-first-")
        second = self._runtime("elosern-save-second-")
        for name in ("database_path", "saves_dir", "cache_dir", "log_dir"):
            left, right = getattr(first, name), getattr(second, name)
            self.assertNotEqual(left, right, f"{name} is shared")
            self.assertFalse(left.is_relative_to(second.root_dir), f"{name} leaks")
            self.assertFalse(right.is_relative_to(first.root_dir), f"{name} leaks")
            self.assertTrue(left.is_relative_to(first.root_dir))
            self.assertTrue(right.is_relative_to(second.root_dir))

        second.cleanup()
        self.assertFalse(second.root_dir.exists(), "teardown must remove its own root")
        self.assertTrue(first.root_dir.exists(), "teardown removed another invocation's root")

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-uses-an-isolated-managed-evennia-runtime"
    )
    def test_configured_retention_prunes_each_private_root_independently(self):
        first = self._runtime("elosern-save-retention-a-")
        second = self._runtime("elosern-save-retention-b-")
        before = _developer_fingerprint()
        outcomes = []
        for runtime in (first, second):
            result = _run_probe(
                runtime, _RETENTION_PROBE, env={"ELOSERN_BROWSER_AUTOSAVE_KEEP": "2"}
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            outcomes.append(json.loads(result.stdout))

        for runtime, outcome in zip((first, second), outcomes, strict=True):
            self.assertEqual(outcome["keep"], 2)
            self.assertEqual(outcome["layout"]["database"], str(runtime.database_path))
            self.assertEqual(outcome["layout"]["saves_root"], str(runtime.saves_dir))
            self.assertEqual(outcome["layout"]["art_root"], str(runtime.cache_dir / "art"))
            art_saves = runtime.cache_dir / "art" / ".saves"
            retained = {save_id: kind for save_id, kind in outcome["saves"]}
            self.assertEqual(retained[outcome["manual"]], "manual")
            self.assertTrue(
                (runtime.saves_dir / outcome["manual"] / "evennia.db3").is_file()
            )
            self.assertTrue((art_saves / outcome["manual"]).is_dir())
            for kind, created in outcome["created"].items():
                self.assertEqual(len(created), 3, kind)
                self.assertEqual(
                    sorted(save_id for save_id, entry_kind in outcome["saves"] if entry_kind == kind),
                    sorted(created[-2:]),
                    f"{kind} must retain exactly its two newest saves",
                )
                # The oldest automatic save's database AND art halves are gone.
                self.assertFalse((runtime.saves_dir / created[0]).exists())
                self.assertFalse((art_saves / created[0]).exists())
                for save_id in created[-2:]:
                    self.assertTrue(
                        (runtime.saves_dir / save_id / "evennia.db3").is_file()
                    )
                    self.assertTrue((art_saves / save_id).is_dir())
            self.assertEqual(len(outcome["saves"]), 5)

        for runtime, outcome, sibling in (
            (first, outcomes[0], second),
            (second, outcomes[1], first),
        ):
            for save_id, _kind in outcome["saves"]:
                self.assertTrue((runtime.saves_dir / save_id).is_dir())
                self.assertFalse((sibling.saves_dir / save_id).exists())
        self.assertEqual(_developer_fingerprint(), before)


# --- real isolated-runtime regressions --------------------------------------


class _OwnedManagedServerTest(BrowserAcceptanceTest):
    """One dedicated managed runtime per class, owned and torn down here."""

    @classmethod
    def _prepare_runtime(cls) -> fixtures.BrowserRuntime:
        return fixtures.create_runtime(prefix="elosern-console-saves-")

    @classmethod
    def _after_start(cls, runtime: fixtures.BrowserRuntime) -> None:
        """Hook for a class that needs a fault after the processes are up."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.developer_fingerprint = _developer_fingerprint()
        cls.server = ManagedServer(runtime=cls._prepare_runtime())
        cls.server.start()
        cls._after_start(cls.server.runtime)
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    @classmethod
    def tearDownClass(cls) -> None:
        runtime = cls.server.runtime
        root = runtime.root_dir
        pids = dict(cls.server.pids)
        cls.server.stop()
        cls.server = None
        if root.exists():
            raise AssertionError("teardown left the invocation's private root behind")
        for pid in pids.values():
            if fixtures.process_is_alive(pid):
                raise AssertionError(f"teardown left owned process {pid} behind")
        if _developer_fingerprint() != cls.developer_fingerprint:
            raise AssertionError("the managed runtime changed developer persistence")


class ConsoleSaveIsolationBrowserTest(_OwnedManagedServerTest):
    """The first protected teleport owns a private, complete snapshot."""

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-uses-an-isolated-managed-evennia-runtime"
    )
    def test_first_protected_teleport_saves_the_before_state_privately(self):
        runtime = self.server.runtime
        page = self.logged_in_page()
        token = _csrf_token(page, self.base_url)

        status = _gm_get(page, "/gm/api/console/status")
        self.assertEqual(status["status"], 200, status["body"])
        self.assertIsNone(status["body"]["data"]["baseline_tick"])
        self.assertTrue(status["body"]["data"]["will_snapshot"])

        character = _character_dbref(page)
        before_room = _current_room(page, character)
        destination = _destination_room(page, before_room)
        self.assertNotEqual(before_room, destination)

        response = _gm_post(
            page,
            "/gm/api/console/teleport",
            {"target": character, "room": destination},
            token,
        )
        self.assertEqual(response["status"], 200, response["body"])
        self.assertTrue(response["body"]["ok"], response["body"])
        snapshot = response["body"]["data"]["snapshot"]
        self.assertTrue(snapshot["taken"], "the first intervention must save first")
        save_id = snapshot["save_id"]
        self.assertRegex(save_id, SAVE_ID_PATTERN)

        # Completeness is authoritative through the same listing the operator sees.
        listing = _gm_get(page, "/gm/api/saves")["body"]["data"]
        self.assertEqual(listing["autosave_keep"], 10)
        saved = next(item for item in listing["saves"] if item["id"] == save_id)
        self.assertEqual(saved["kind"], "auto_intervention")
        self.assertFalse(saved["deletable"])
        self.assertFalse(saved["pending"])

        database_copy = runtime.saves_dir / save_id / "evennia.db3"
        manifest = json.loads(
            (runtime.saves_dir / save_id / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["id"], save_id)
        self.assertEqual(manifest["kind"], "auto_intervention")
        self.assertTrue(database_copy.is_file())
        self.assertTrue((runtime.cache_dir / "art" / ".saves" / save_id).is_dir())

        # The snapshot database still holds the pre-teleport location.
        connection = sqlite3.connect(
            f"{database_copy.resolve().as_uri()}?mode=ro", uri=True
        )
        try:
            row = connection.execute(
                "SELECT db_location_id FROM objects_objectdb WHERE id = ?",
                (int(character.lstrip("#")),),
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(row, "the saved database must carry the character")
        self.assertEqual(f"#{row[0]}", before_room)

        # The live world committed the target room only after the save.
        self.assertEqual(_current_room(page, character), destination)

        # Every half resolves under this invocation's private root.
        for path in (runtime.database_path, runtime.saves_dir, runtime.cache_dir / "art"):
            self.assertTrue(path.is_relative_to(runtime.root_dir), str(path))
        self.assertEqual(_developer_fingerprint(), self.developer_fingerprint)

        # A sibling invocation owns a disjoint save root.
        sibling = fixtures.create_runtime(prefix="elosern-console-saves-sibling-")
        self.addCleanup(sibling.cleanup)
        self.assertNotEqual(sibling.saves_dir, runtime.saves_dir)
        self.assertFalse(sibling.saves_dir.is_relative_to(runtime.root_dir))
        self.assertFalse(runtime.saves_dir.is_relative_to(sibling.root_dir))


class ConsoleSnapshotFailureBrowserTest(_OwnedManagedServerTest):
    """An unusable private save root refuses before the mutation."""

    @classmethod
    def _after_start(cls, runtime: fixtures.BrowserRuntime) -> None:
        # A file where the private save root belongs: every snapshot fails at
        # publication, while the server itself boots normally. Installed after
        # boot so a port-conflict retry (which replaces the runtime) cannot
        # discard the fault.
        shutil.rmtree(runtime.saves_dir, ignore_errors=True)
        runtime.saves_dir.write_text("not a directory\n", encoding="utf-8")

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-uses-an-isolated-managed-evennia-runtime"
    )
    def test_snapshot_failure_refuses_before_mutation_and_keeps_the_baseline(self):
        runtime = self.server.runtime
        self.assertTrue(
            runtime.saves_dir.is_file(),
            "the injected save-root fault must survive startup",
        )
        page = self.logged_in_page()
        token = _csrf_token(page, self.base_url)

        before_status = _gm_get(page, "/gm/api/console/status")["body"]["data"]
        self.assertIsNone(before_status["baseline_tick"])
        self.assertTrue(before_status["will_snapshot"])

        character = _character_dbref(page)
        before_room = _current_room(page, character)
        destination = _destination_room(page, before_room)

        response = _gm_post(
            page,
            "/gm/api/console/teleport",
            {"target": character, "room": destination},
            token,
        )
        self.assertEqual(response["status"], 500, response["body"])
        self.assertFalse(response["body"]["ok"])
        self.assertEqual(response["body"]["error"]["code"], "snapshot_failed")
        self.assertEqual(response["body"]["snapshot"], {"taken": False, "save_id": None})

        # No operation ran: the target is still in its original room and the
        # policy baseline was never advanced.
        self.assertEqual(_current_room(page, character), before_room)
        after_status = _gm_get(page, "/gm/api/console/status")["body"]["data"]
        self.assertEqual(after_status["baseline_tick"], before_status["baseline_tick"])
        self.assertTrue(after_status["will_snapshot"])
        self.assertTrue(runtime.saves_dir.is_file())
        self.assertEqual(_developer_fingerprint(), self.developer_fingerprint)


if __name__ == "__main__":
    unittest.main()
