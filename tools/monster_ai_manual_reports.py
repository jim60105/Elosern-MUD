#!/usr/bin/env python
"""Manual monster-AI evidence CLI (monster-ai-manual-evidence).

Run one explicit operation by hand against an isolated scratch database:

    uv run --locked python tools/monster_ai_manual_reports.py selector
    uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype brute
    uv run --locked python tools/monster_ai_manual_reports.py performance

The scratch database is a fresh temporary SQLite file (override with
``MUD_MANUAL_REPORT_DB``); the developer's live game database and the retained
Evennia test database are never opened, and no network/model service is
touched. This tool is manual acceptance evidence only: nothing imports it from
the game runtime, the default test discovery, the contract gates or CI.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / ".var" / "monster-ai-manual-reports"
_LIVE_DB = "server/db/evennia.db3"
_RETAINED_TEST_DB = "server/db/evennia-test.sqlite3"

# The game's packages (``server``, ``world``, ``typeclasses``) live at the
# repository root, which is also the game directory Evennia expects.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)


def _scratch_path() -> Path:
    """Return a fresh isolated scratch database path.

    A named override must not already exist (never migrate someone else's
    database) and may never be the live game database or the retained Evennia
    test database; without one, this run gets its own private temporary
    directory.
    """
    override = os.environ.get("MUD_MANUAL_REPORT_DB")
    if override:
        path = Path(override).resolve()
        if path.exists():
            raise SystemExit(
                f"refusing to migrate an existing database: {path}; "
                "name a fresh path or unset MUD_MANUAL_REPORT_DB"
            )
    else:
        directory = Path(tempfile.mkdtemp(prefix="monster-ai-manual-"))
        path = directory / "scratch.sqlite3"
    forbidden = {(REPO_ROOT / _LIVE_DB).resolve(), (REPO_ROOT / _RETAINED_TEST_DB).resolve()}
    if path in forbidden:
        raise SystemExit(f"refusing to run against a live/retained database: {path}")
    return path


def _bootstrap() -> Path:
    """Point Django at the fresh scratch database, then initialize it.

    The scratch path is published through ``MUD_MANUAL_REPORT_DB`` and the
    ``DJANGO_SETTINGS_MODULE`` is the tool's own scratch settings module, so the
    default connection is the scratch database before ``django.setup()`` and
    ``evennia._init()`` run. The resolved connection name is verified before any
    migration, so a misconfiguration fails loudly instead of touching a real
    database.
    """
    scratch = _scratch_path()
    os.environ["MUD_MANUAL_REPORT_DB"] = str(scratch)
    os.environ["DJANGO_SETTINGS_MODULE"] = "tools.monster_ai_manual_reports_settings"
    import django

    django.setup()
    from django.db import connection

    resolved = Path(str(connection.settings_dict["NAME"])).resolve()
    if resolved != scratch.resolve():
        raise SystemExit(
            f"scratch isolation failed: the default connection is {resolved}"
        )
    # Evennia's API (including the command/contrib bindings ``world.rules.dice``
    # reaches) is only published by ``_init()`` after Django models load.
    import evennia

    evennia._init()
    from django.core.management import call_command

    call_command("migrate", verbosity=0, interactive=False, run_syncdb=True)
    return scratch


def _baseline_commit() -> str:
    """Return the repository HEAD the report is baselined against."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("selector", "archetype", "performance")
    )
    parser.add_argument("--archetype", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--baseline-commit", default=None)
    parser.add_argument(
        "--selector-seeds", type=int, default=None,
        help="override the documented 128-seed selector replicate count",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    scratch = _bootstrap()

    from world.rules import monster_behaviour as behaviour
    from world.rules.monster_ai import manual_reports as reports
    from world.rules.monster_ai.manual_campaign import CampaignHarness

    baseline = args.baseline_commit or _baseline_commit()
    harness = None
    try:
        if args.operation != "selector":
            harness = CampaignHarness().__enter__()
        fingerprint = (
            harness.tuning.fingerprint
            if harness is not None
            else behaviour.MONSTER_AI_TUNING.fingerprint
        )
        header = reports.environment_header(
            baseline_commit=baseline,
            configuration_fingerprint=fingerprint,
            algorithm_version=behaviour.AI_ALGORITHM_VERSION,
        )
        result = reports.run_operation(
            operation=args.operation,
            harness=harness,
            header=header,
            output=args.output,
            archetype=args.archetype,
            selector_count=args.selector_seeds or reports.SELECTOR_SEED_COUNT,
        )
    finally:
        if harness is not None:
            harness.__exit__(None, None, None)

    print(f"scratch database: {scratch}")
    print(f"report: {result.paths[0]}")
    print(f"interpretation: {result.paths[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())