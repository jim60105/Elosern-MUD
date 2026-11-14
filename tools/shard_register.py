"""Keep the three CI shard manifests in step with the test files on disk.

Every test has exactly one execution owner in CI:

    .github/evennia-shards.json    non-browser test modules (labels)
    .github/browser-shards.json    browser test methods (files_a / files_b)
    .github/top-level-shards.json  repository-wide ``tests/`` modules (labels)

After adding, renaming, moving or deleting a test module or a browser test
method, run:

    uv run --locked python -m tools.shard_register fix

It removes labels that no longer resolve to a test and gives every unowned
test one owner. ``check`` reports the same drift without writing anything:

    uv run --locked python -m tools.shard_register check

Placement is a neighbourhood heuristic, not a timing model: an unowned test
joins a shard that already owns its closest relatives (same class, then same
file, then same directory), and among those the one with the fewest tests. It
is appended to the end of that shard's list, so existing label order (which the
suite's module-neighbourhood state depends on) is never reshuffled. Whether a
shard still fits its time budget is only observable in CI; a rebalance is a
separate, deliberate change (docs/development/evennia-test-performance.md).

The tool never repairs a label owned twice or a shard that would be left with
no labels: both are reported and need a human decision.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
FIX_COMMAND = "uv run --locked python -m tools.shard_register fix"

EVENNIA_ROOTS = ("commands", "server", "typeclasses", "world", "web/webclient", "web/gm")
BROWSER_DIR = "web/tests/browser"
BROWSER_PREFIX = "web.tests.browser."
TOP_LEVEL_DIR = "tests"

_TEST_DEF = re.compile(r"^\s*(?:async\s+)?def test_", re.MULTILINE)


@dataclass
class Report:
    """Drift of one manifest: what `fix` did (or `check` found) and what it cannot repair."""

    name: str
    added: list[tuple[str, str]] = field(default_factory=list)  # (label, owner description)
    removed: list[tuple[str, str]] = field(default_factory=list)
    manual: list[str] = field(default_factory=list)

    @property
    def drifted(self) -> bool:
        return bool(self.added or self.removed or self.manual)


def _dotted(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _test_count(root: Path, module: str) -> int:
    """Number of test functions in a module: the placement weight."""
    path = root / (module.replace(".", "/") + ".py")
    try:
        return max(1, len(_TEST_DEF.findall(path.read_text(encoding="utf-8"))))
    except OSError:
        return 1


def _resolve_module_label(root: Path, label: str) -> set[str]:
    """A label names one module file, or a package directory walked recursively."""
    if (root / (label.replace(".", "/") + ".py")).is_file():
        return {label}
    package = root / label.replace(".", "/")
    if package.is_dir():
        return {_dotted(root, path) for path in package.rglob("test*.py")}
    return set()


def _browser_methods(root: Path) -> dict[tuple[str, str, str], None]:
    """Every (file, class, method) browser test, in source order."""
    methods: dict[tuple[str, str, str], None] = {}
    for path in sorted((root / BROWSER_DIR).glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    methods[(path.stem, node.name, child.name)] = None
    return methods


def _resolve_browser_label(
    label: str, methods: dict[tuple[str, str, str], None]
) -> set[tuple[str, str, str]]:
    """A browser label names a module, a class in it, or one test method."""
    if not label.startswith(BROWSER_PREFIX):
        return set()
    parts = label.removeprefix(BROWSER_PREFIX).split(".")
    if not 1 <= len(parts) <= 3:
        return set()
    return {method for method in methods if list(method[: len(parts)]) == parts}


def _sync(
    report: Report,
    lists: list[tuple[str, list[str]]],
    resolve,
    discovered: list,
    weight,
    relatives,
    label_of,
) -> None:
    """Drop stale labels and give every unowned unit one owner, in place.

    `lists` are the manifest's label lists with a description each; `resolve`
    maps a label to the units it owns; `relatives(unit)` yields predicates from
    the closest neighbourhood to the widest.
    """
    owner: dict = {}
    for description, labels in lists:
        stale = [label for label in labels if not resolve(label)]
        if stale and len(stale) == len(labels):
            report.manual.append(
                f"{description} would be left with no labels (all stale: {stale}); "
                "remove or refill that shard by hand"
            )
            stale = []
        for label in stale:
            labels.remove(label)
            report.removed.append((label, description))
        for label in labels:
            for unit in sorted(resolve(label)):
                if unit in owner:
                    report.manual.append(
                        f"{label_of(unit)} is owned twice ({owner[unit]} and {description}); "
                        "delete one of the overlapping labels by hand"
                    )
                owner[unit] = description
    by_description = dict(lists)
    load = {description: 0 for description, _ in lists}
    for unit, description in owner.items():
        load[description] += weight(unit)
    for unit in discovered:
        if unit in owner:
            continue
        candidates: list[str] = []
        for related in relatives(unit):
            candidates = sorted({owner[other] for other in owner if related(other)}, key=list(load).index)
            if candidates:
                break
        target = min(candidates or list(load), key=lambda description: load[description])
        by_description[target].append(label_of(unit))
        owner[unit] = target
        load[target] += weight(unit)
        report.added.append((label_of(unit), target))


def _module_relatives(module: str):
    """Same directory first, then each enclosing package."""
    parts = module.split(".")[:-1]
    for depth in range(len(parts), 0, -1):
        prefix = ".".join(parts[:depth]) + "."
        yield lambda other, prefix=prefix: other.startswith(prefix)


def sync_evennia(root: Path, manifest: dict) -> Report:
    report = Report("evennia-shards")
    discovered = sorted(
        {_dotted(root, path) for name in EVENNIA_ROOTS for path in (root / name).rglob("test*.py")}
    )
    lists = [(f"shard {shard['index']} ({shard.get('name')})", shard["labels"]) for shard in manifest["shards"]]
    _sync(
        report,
        lists,
        lambda label: _resolve_module_label(root, label),
        discovered,
        lambda module: _test_count(root, module),
        _module_relatives,
        lambda module: module,
    )
    return report


def sync_top_level(root: Path, manifest: dict) -> Report:
    report = Report("top-level-shards")
    discovered = sorted(_dotted(root, path) for path in (root / TOP_LEVEL_DIR).glob("test_*.py"))
    lists = [(f"shard {shard['index']} ({shard.get('name')})", shard["labels"]) for shard in manifest["shards"]]
    _sync(
        report,
        lists,
        lambda label: _resolve_module_label(root, label),
        discovered,
        lambda module: _test_count(root, module),
        lambda module: (),
        lambda module: module,
    )
    return report


def sync_browser(root: Path, manifest: dict) -> Report:
    report = Report("browser-shards")
    methods = _browser_methods(root)
    lists = [
        (f"shard {shard['index']} ({shard.get('name')}) {key}", shard[key])
        for shard in manifest["shards"]
        for key in ("files_a", "files_b")
    ]

    def relatives(unit):
        yield lambda other: other[:2] == unit[:2]  # same class: one server boot per process
        yield lambda other: other[0] == unit[0]

    _sync(
        report,
        lists,
        lambda label: _resolve_browser_label(label, methods),
        list(methods),
        lambda unit: 1,
        relatives,
        lambda unit: BROWSER_PREFIX + ".".join(unit),
    )
    return report


MANIFESTS = {
    "evennia-shards": sync_evennia,
    "browser-shards": sync_browser,
    "top-level-shards": sync_top_level,
}


def _indent_of(text: str) -> int:
    """The manifest's own indentation, so a rewrite keeps the diff minimal."""
    match = re.search(r"^( +)\S", text, re.MULTILINE)
    return len(match.group(1)) if match else 2


def run(root: Path, *, write: bool) -> list[Report]:
    """Synchronise every manifest in memory; persist the result only when `write`."""
    reports = []
    for name, sync in MANIFESTS.items():
        path = root / ".github" / f"{name}.json"
        text = path.read_text(encoding="utf-8")
        manifest = json.loads(text)
        report = sync(root, manifest)
        reports.append(report)
        if write and (report.added or report.removed):
            path.write_text(json.dumps(manifest, indent=_indent_of(text)) + "\n", encoding="utf-8")
    return reports


def _print(reports: list[Report], *, wrote: bool) -> None:
    add, drop = ("added", "removed") if wrote else ("unowned", "stale")
    for report in reports:
        for label, where in report.added:
            print(f"{report.name}: {add}: {label} -> {where}")
        for label, where in report.removed:
            print(f"{report.name}: {drop}: {label} (was in {where})")
        for message in report.manual:
            print(f"{report.name}: MANUAL: {message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.shard_register", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("check", "fix"))
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    write = arguments.command == "fix"
    reports = run(arguments.root, write=write)
    _print(reports, wrote=write)
    manual = any(report.manual for report in reports)
    if write:
        if manual:
            print("shard_register: the MANUAL items above need a hand edit of the manifest.")
            return 1
        changed = sum(len(report.added) + len(report.removed) for report in reports)
        print(f"shard_register: {changed} label(s) changed; every test has exactly one owner.")
        if changed:
            print("Commit the manifest change together with the test change that caused it.")
        return 0
    if any(report.drifted for report in reports):
        print(f"shard_register: manifests are out of step with the test files. Run: {FIX_COMMAND}")
        return 1
    print("shard_register: every test has exactly one owner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
