"""Migration inventories without Django (standard library only).

Restore compatibility compares the migrations recorded in a saved database
with the migrations the current code ships. The pre-start restore tool runs
before Django exists, so "known" migrations are discovered from the source
tree: every ``migrations`` package under the project's own top-level packages
and under the installed ``evennia`` and ``django`` distributions. The app
label is the migration package's parent directory name, which is what every
installed app here uses; a Django-side contract test pins that every disk
migration Django itself loads is present in this inventory. The live server
uses the same function, so there is one discovery rule, never a second
hand-maintained list.
"""

from __future__ import annotations

import os
import sqlite3
import sysconfig
from pathlib import Path

#: Project packages that may hold app migrations, relative to the project root.
PROJECT_PACKAGES = ("commands", "server", "typeclasses", "web", "world")
#: Installed distributions whose apps run migrations here.
DEPENDENCY_PACKAGES = ("evennia", "django")

Inventory = dict[str, set[str]]


def search_roots(project_root: Path, purelib: str | None = None) -> list[Path]:
    """Directories walked for ``migrations`` packages."""
    site = Path(purelib or sysconfig.get_paths()["purelib"])
    roots = [Path(project_root) / name for name in PROJECT_PACKAGES]
    roots += [site / name for name in DEPENDENCY_PACKAGES]
    return [root for root in roots if root.is_dir()]


def known_migrations(project_root: Path, purelib: str | None = None) -> Inventory:
    """``{app_label: {migration_name, ...}}`` from the code on disk."""
    known: Inventory = {}
    for root in search_roots(project_root, purelib):
        for directory, subdirs, files in os.walk(root):
            subdirs[:] = [name for name in subdirs if name not in {"__pycache__", "node_modules"}]
            path = Path(directory)
            if path.name != "migrations" or "__init__.py" not in files:
                continue
            names = {
                name[:-3]
                for name in files
                if name.endswith(".py") and not name.startswith(("_", "~"))
            }
            known.setdefault(path.parent.name, set()).update(names)
    return known


def applied_migrations(db_path: Path) -> list[tuple[int, str, str]]:
    """``(id, app, name)`` rows of ``django_migrations`` in ``db_path``."""
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute("SELECT id, app, name FROM django_migrations ORDER BY id").fetchall()
    finally:
        connection.close()
    return [(int(row[0]), str(row[1]), str(row[2])) for row in rows]


def latest_per_app(rows: list[tuple[int, str, str]]) -> dict[str, str]:
    """The most recently applied migration name of each app."""
    latest: dict[str, tuple[int, str]] = {}
    for row_id, app, name in rows:
        if app not in latest or row_id > latest[app][0]:
            latest[app] = (row_id, name)
    return {app: latest[app][1] for app in sorted(latest)}


def unknown_migrations(rows: list[tuple[int, str, str]], known: Inventory) -> list[str]:
    """``app.name`` of every applied migration the current code does not ship."""
    return sorted(
        f"{app}.{name}" for _row_id, app, name in rows if name not in known.get(app, set())
    )
