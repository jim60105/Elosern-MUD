"""One command for the cheap repository-contract gates.

Run every gate (the local handoff/archive check):

    uv run --locked python -m tools.contract_gate

or name a subset (CI preflight runs the gates its other steps do not):

    uv run --locked python -m tools.contract_gate manifests contracts

On a feature worktree before the change's archive sync, name the active change
so the traceability gate tolerates only the requirements that change's delta
removes or renames (they stay in openspec/specs/ until the sync):

    uv run --locked python -m tools.contract_gate --change <change>

Each gate runs even when an earlier one fails, so one invocation reports every
broken contract. The exit status is non-zero when any selected gate fails, and
every failed gate is followed by its `NEXT_STEPS` entry: the command or the
document that repairs it.
"""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import sys

from tools import shard_register

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARD_MANIFESTS = ("evennia-shards", "browser-shards", "top-level-shards")
# Repository-wide ownership contracts that a feature change breaks silently:
# every test module/method owned by exactly one CI shard, and every managed
# browser target registered in the frozen webclient audit.
CONTRACT_MODULES = (
    "tests.test_evennia_test_optimization_contract",
    "tests.test_webclient_frozen_contract",
)


def manifest_errors(name: str, manifest: dict) -> list[str]:
    """Structural errors of one `.github/<name>.json` shard manifest."""
    shards = manifest.get("shards")
    if not shards:
        return [f"{name}: manifest declares no shards"]
    indices = [shard.get("index") for shard in shards]
    if indices != sorted(indices) or len(indices) != len(set(indices)):
        return [f"{name}: shard indices must be unique and sorted"]
    errors = []
    for shard in shards:
        if name == "browser-shards":
            files_a = shard.get("files_a") or []
            files_b = shard.get("files_b") or []
            if not files_a or not files_b:
                errors.append(f"{name}: shard {shard.get('index')} must declare non-empty files_a and files_b")
                continue
            items = [*files_a, *files_b]
        else:
            items = shard.get("labels") or shard.get("files")
        if not items or not all(isinstance(item, str) and item for item in items):
            errors.append(f"{name}: shard {shard.get('index')} must declare non-empty string labels/files")
    return errors


def _check_manifests() -> bool:
    errors = []
    for name in SHARD_MANIFESTS:
        path = REPO_ROOT / ".github" / f"{name}.json"
        errors.extend(manifest_errors(name, json.loads(path.read_text(encoding="utf-8"))))
    for error in errors:
        print(error)
    if errors:
        return False
    # Ownership drift (an unregistered or stale test label), reported with the
    # labels and the one command that repairs it.
    return shard_register.main(["check"]) == 0


def _run(*args: str) -> Callable[[], bool]:
    def run() -> bool:
        return subprocess.run([sys.executable, *args], cwd=REPO_ROOT).returncode == 0

    return run


def _traceability(change: str | None = None) -> Callable[[], bool]:
    extra = ("--change", change) if change else ()
    return _run("-m", "tools.spec_traceability", "check", *extra)


GATES: dict[str, Callable[[], bool]] = {
    "reference-context": _run("-m", "tools.map_reference_context", "--check"),
    "traceability": _traceability(),
    "observability": _run("-m", "tools.observability_lint", "check"),
    "test-data": _run("-m", "tools.test_data_lint", "check"),
    "manifests": _check_manifests,
    "contracts": _run("-m", "unittest", *CONTRACT_MODULES),
}


# What to do when a gate fails. Printed after the run for every failed gate, so
# the repair is in the output instead of in a document the reader must find.
NEXT_STEPS: dict[str, str] = {
    "reference-context": (
        "content/map-reference-context.json is generated. Regenerate and commit it:\n"
        "    uv run --locked python -m tools.map_reference_context"
    ),
    "traceability": (
        "A main requirement has no covering test, or an annotation is wrong. Print the canonical IDs with\n"
        "    uv run --locked python -m tools.spec_traceability list\n"
        "then put @covers_requirement(\"<id>\") on the test_* whose assertions establish that requirement\n"
        "(write the test if none exists). There is no waiver list; never annotate an unrelated or skipped\n"
        "test. Guide: docs/development/spec-test-traceability.md"
    ),
    "observability": (
        "Fix each `path:line: rule` above in the production file: R1 = log through world.observability\n"
        "(log_debug/log_info/log_warn/log_error) instead of the Evennia logger or stdlib logging;\n"
        "R2 = an except block re-raises, emits a facade event with exc=, or carries\n"
        "`# observability: ignore R2: <reason>`; R3 = pass context={...} (and exc= for log_error).\n"
        "Never add an entry to tools/observability_freeze.json: it is shrink-only."
    ),
    "test-data": (
        "A behavior test names shipped game content. Rewrite it on the synthetic test-data kit or a\n"
        "file-local synthetic fixture; do not add the file to the debt ledger in\n"
        "tools/test_data_freeze.json. Only a real data-contract test (first docstring line\n"
        "`Data-contract test: <rationale>`) is registered there. See AGENTS.md, section Testing."
    ),
    "manifests": (
        "A test has no CI owner, or a label points at a test that no longer exists. Run and commit:\n"
        f"    {shard_register.FIX_COMMAND}"
    ),
    "contracts": (
        "Read the assertion message above. For an unowned/stale shard label run\n"
        f"    {shard_register.FIX_COMMAND}\n"
        "A frozen-audit failure means docs/development/webclient-vue-frozen-contract-audit.md and the\n"
        "webclient specs disagree: change the audit only in the change that owns that requirement."
    ),
}


def _split_change(args: list[str]) -> tuple[list[str], str | None]:
    """Remove `--change <name>` / `--change=<name>`; raise ValueError if malformed."""
    names: list[str] = []
    change: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--change" or arg.startswith("--change="):
            if change is not None:
                raise ValueError("--change given more than once")
            if arg == "--change":
                index += 1
                if index == len(args):
                    raise ValueError("--change needs a change name")
                change = args[index]
            else:
                change = arg.removeprefix("--change=")
            if not change or change.startswith("-"):
                raise ValueError("--change needs a change name")
        else:
            names.append(arg)
        index += 1
    return names, change


def main(argv: list[str] | None = None) -> int:
    try:
        selected, change = _split_change(list(argv if argv is not None else sys.argv[1:]))
    except ValueError as exc:
        print(exc)
        return 2
    selected = selected or list(GATES)
    unknown = [name for name in selected if name not in GATES]
    if unknown:
        print(f"unknown gate(s): {', '.join(unknown)}; choose from {', '.join(GATES)}")
        return 2
    gates = dict(GATES)
    if change:
        gates["traceability"] = _traceability(change)
    failed = []
    for name in selected:
        print(f"== contract gate: {name}", flush=True)
        if not gates[name]():
            failed.append(name)
    if failed:
        print(f"contract gate FAILED: {', '.join(failed)}")
        for name in failed:
            print(f"\n-- next step for {name}:\n{NEXT_STEPS[name]}")
        return 1
    print(f"contract gate passed: {', '.join(selected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
