"""Verify traceability between main OpenSpec requirements and repository tests."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import asdict, dataclass
from functools import wraps
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from typing import Any, ParamSpec, TypeVar


EVIDENCE_ENV = "OPENSPEC_TEST_EVIDENCE"
DECORATOR_MODULE = "tools.spec_traceability"
REQUIREMENT_HEADING = re.compile(r"^### Requirement:\s*(.*?)\s*$")
P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True, order=True)
class SourceLocation:
    path: str
    line: int


@dataclass(frozen=True)
class Requirement:
    identifier: str
    name: str
    location: SourceLocation


@dataclass(frozen=True)
class Association:
    identifier: str
    test_identity: str
    location: SourceLocation


@dataclass(frozen=True, order=True)
class VerificationError:
    code: str
    message: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class TraceabilityReport:
    requirements: tuple[Requirement, ...]
    associations: tuple[Association, ...]
    covered: tuple[str, ...]
    uncovered: tuple[str, ...]
    errors: tuple[VerificationError, ...]

    @property
    def ok(self) -> bool:
        return not self.errors and not self.uncovered

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "summary": {
                "requirements": len(self.requirements),
                "associations": len(self.associations),
                "covered": len(self.covered),
                "uncovered": len(self.uncovered),
                "errors": len(self.errors),
            },
            "requirements": [asdict(item) for item in self.requirements],
            "associations": [asdict(item) for item in self.associations],
            "covered": list(self.covered),
            "uncovered": [
                {
                    "identifier": identifier,
                    "location": asdict(requirement_by_id(self.requirements)[identifier].location),
                    "association_status": "no-successful-test-association",
                }
                for identifier in self.uncovered
            ],
            "errors": [asdict(item) for item in self.errors],
        }


def covers_requirement(*requirement_ids: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Associate a test with requirements and record its successful CI execution."""
    if not requirement_ids or any(not isinstance(item, str) for item in requirement_ids):
        raise TypeError("covers_requirement requires one or more string IDs")

    def decorate(test: Callable[P, R]) -> Callable[P, R]:
        @wraps(test)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            result = test(*args, **kwargs)
            evidence_path = os.environ.get(EVIDENCE_ENV)
            if evidence_path:
                record = json.dumps(
                    {
                        "test": f"{test.__module__}.{test.__qualname__}",
                        "requirements": list(requirement_ids),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                descriptor = os.open(
                    evidence_path,
                    os.O_APPEND | os.O_CREAT | os.O_WRONLY,
                    0o600,
                )
                try:
                    os.write(descriptor, f"{record}\n".encode())
                finally:
                    os.close(descriptor)
            return result

        return wrapped

    return decorate


def normalize_requirement_name(name: str) -> str:
    """Return the canonical slug for a requirement heading."""
    normalized = unicodedata.normalize("NFKC", name).casefold()
    slug = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).strip("-_")
    return slug.replace("_", "-")


def parse_requirements(repo_root: Path) -> tuple[tuple[Requirement, ...], tuple[VerificationError, ...]]:
    """Index requirements from direct capability specs under openspec/specs."""
    specs_root = repo_root / "openspec" / "specs"
    requirements: list[Requirement] = []
    errors: list[VerificationError] = []
    by_id: dict[str, Requirement] = {}
    for spec_path in sorted(specs_root.glob("*/spec.md")):
        capability = spec_path.parent.name
        relative = spec_path.relative_to(repo_root).as_posix()
        for line_number, line in enumerate(spec_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("### Requirement:"):
                continue
            match = REQUIREMENT_HEADING.fullmatch(line)
            location = SourceLocation(relative, line_number)
            if not match or not match.group(1):
                errors.append(VerificationError("malformed-requirement", "Malformed requirement heading", location))
                continue
            name = match.group(1)
            slug = normalize_requirement_name(name)
            if not slug:
                errors.append(VerificationError("empty-requirement-id", f"Requirement {name!r} normalizes to an empty ID", location))
                continue
            requirement = Requirement(f"{capability}::{slug}", name, location)
            previous = by_id.get(requirement.identifier)
            if previous:
                errors.append(
                    VerificationError(
                        "requirement-id-collision",
                        f"{requirement.identifier} collides with {previous.location.path}:{previous.location.line}",
                        location,
                    )
                )
                continue
            by_id[requirement.identifier] = requirement
            requirements.append(requirement)
    return tuple(sorted(requirements, key=lambda item: item.identifier)), tuple(sorted(errors))


def _module_name(repo_root: Path, path: Path) -> str:
    return ".".join(path.relative_to(repo_root).with_suffix("").parts)


def _eligible_test_class(node: ast.ClassDef) -> bool:
    if node.name.endswith(("Test", "Tests", "TestCase")):
        return True
    return any(
        isinstance(base, ast.Name) and base.id.endswith(("Test", "Tests", "TestCase"))
        or isinstance(base, ast.Attribute) and base.attr.endswith(("Test", "Tests", "TestCase"))
        for base in node.bases
    )


def _decorator_aliases(tree: ast.Module) -> tuple[set[str], set[str], list[VerificationError]]:
    direct: set[str] = set()
    modules: set[str] = set()
    errors: list[VerificationError] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any(alias.name == "covers_requirement" for alias in node.names):
            if node.module != DECORATOR_MODULE:
                errors.append(VerificationError("invalid-decorator-import", f"covers_requirement must be imported from {DECORATOR_MODULE}"))
                continue
            direct.update(alias.asname or alias.name for alias in node.names if alias.name == "covers_requirement")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == DECORATOR_MODULE:
                    modules.add(alias.asname or alias.name)
    return direct, modules, errors


def _is_covers_call(node: ast.expr, direct: set[str], modules: set[str]) -> ast.Call | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Name) and node.func.id in direct:
        return node
    if isinstance(node.func, ast.Attribute) and node.func.attr == "covers_requirement":
        value = node.func.value
        if isinstance(value, ast.Name) and value.id in modules:
            return node
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and f"{value.value.id}.{value.attr}" in modules
        ):
            return node
    return None


def discover_associations(
    repo_root: Path,
    known_ids: set[str],
) -> tuple[tuple[Association, ...], tuple[VerificationError, ...]]:
    """Find statically declared test associations without importing tests."""
    associations: list[Association] = []
    errors: list[VerificationError] = []
    excluded = {".git", ".venv", ".worktrees", "openspec"}
    paths = sorted(
        path
        for path in repo_root.rglob("test_*.py")
        if not excluded.intersection(path.relative_to(repo_root).parts)
    )
    for path in paths:
        relative = path.relative_to(repo_root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, SyntaxError) as exc:
            errors.append(VerificationError("test-parse-error", str(exc), SourceLocation(relative, getattr(exc, "lineno", 1) or 1)))
            continue
        direct, modules, import_errors = _decorator_aliases(tree)
        errors.extend(
            VerificationError(error.code, error.message, SourceLocation(relative, 1)) for error in import_errors
        )
        module = _module_name(repo_root, path)

        def inspect_function(node: ast.FunctionDef | ast.AsyncFunctionDef, class_node: ast.ClassDef | None) -> None:
            calls = [call for decorator in node.decorator_list if (call := _is_covers_call(decorator, direct, modules))]
            if not calls:
                return
            location = SourceLocation(relative, node.lineno)
            eligible = node.name.startswith("test_") and (class_node is None or _eligible_test_class(class_node))
            if not eligible:
                errors.append(VerificationError("invalid-annotation-placement", "Decorator must be on a discoverable test function or method", location))
            identity = f"{module}.{class_node.name + '.' if class_node else ''}{node.name}"
            for call in calls:
                if call.keywords or not call.args or any(not isinstance(arg, ast.Constant) or not isinstance(arg.value, str) for arg in call.args):
                    errors.append(VerificationError("dynamic-requirement-id", "Decorator arguments must be one or more string literals", SourceLocation(relative, call.lineno)))
                    continue
                for arg in call.args:
                    identifier = arg.value
                    if identifier not in known_ids:
                        errors.append(VerificationError("unknown-requirement-id", f"Unknown requirement ID: {identifier}", SourceLocation(relative, arg.lineno)))
                    elif eligible:
                        associations.append(Association(identifier, identity, location))

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inspect_function(node, None)
            elif isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        inspect_function(child, node)
    unique = {(item.identifier, item.test_identity, item.location): item for item in associations}
    return tuple(sorted(unique.values(), key=lambda item: (item.identifier, item.test_identity))), tuple(sorted(errors))


def read_evidence(path: Path) -> tuple[set[tuple[str, str]], tuple[VerificationError, ...]]:
    """Read successful test/requirement pairs from a JSON Lines evidence file."""
    pairs: set[tuple[str, str]] = set()
    errors: list[VerificationError] = []
    if not path.is_file():
        return pairs, (VerificationError("missing-evidence", f"Evidence file does not exist: {path}"),)
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            record = json.loads(line)
            test = record["test"]
            identifiers = record["requirements"]
            if not isinstance(test, str) or not isinstance(identifiers, list) or any(not isinstance(item, str) for item in identifiers):
                raise ValueError("invalid evidence shape")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            errors.append(VerificationError("invalid-evidence", str(exc), SourceLocation(path.as_posix(), line_number)))
            continue
        pairs.update((test, identifier) for identifier in identifiers)
    return pairs, tuple(sorted(errors))


def requirement_by_id(requirements: Iterable[Requirement]) -> dict[str, Requirement]:
    return {item.identifier: item for item in requirements}


def verify(repo_root: Path, evidence_path: Path | None = None) -> TraceabilityReport:
    requirements, requirement_errors = parse_requirements(repo_root)
    associations, association_errors = discover_associations(repo_root, set(requirement_by_id(requirements)))
    evidence_pairs: set[tuple[str, str]] | None = None
    evidence_errors: tuple[VerificationError, ...] = ()
    if evidence_path is not None:
        evidence_pairs, evidence_errors = read_evidence(evidence_path)
    covered = {
        association.identifier
        for association in associations
        if evidence_pairs is None or (association.test_identity, association.identifier) in evidence_pairs
    }
    identifiers = set(requirement_by_id(requirements))
    return TraceabilityReport(
        requirements,
        associations,
        tuple(sorted(covered)),
        tuple(sorted(identifiers - covered)),
        tuple(sorted((*requirement_errors, *association_errors, *evidence_errors))),
    )


def _print_console(report: TraceabilityReport, show_covered: bool) -> None:
    """Print a short summary plus the failing requirements to the console."""
    by_id = requirement_by_id(report.requirements)
    print(
        f"spec traceability: {len(report.requirements)} requirements, "
        f"{len(report.associations)} associations, "
        f"{len(report.covered)} covered, "
        f"{len(report.uncovered)} uncovered, "
        f"{len(report.errors)} errors"
    )
    if report.uncovered:
        print("Uncovered requirements:")
        for identifier in report.uncovered:
            location = by_id[identifier].location
            print(f"  - {identifier} ({location.path}:{location.line})")
    if report.errors:
        print("Errors:")
        for error in report.errors:
            location = f" ({error.location.path}:{error.location.line})" if error.location else ""
            print(f"  - [{error.code}] {error.message}{location}")
    if show_covered:
        print("Covered requirements:")
        for identifier in report.covered:
            print(f"  - {identifier}")


def _write_report(
    report: TraceabilityReport,
    json_output: Path | None,
    show_covered: bool = False,
) -> None:
    if json_output:
        payload = json.dumps(report.to_json(), ensure_ascii=False, indent=2, sort_keys=True)
        json_output.write_text(f"{payload}\n", encoding="utf-8")
    else:
        _print_console(report, show_covered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="List canonical requirement IDs")
    list_parser.add_argument("--json-output", type=Path)
    check_parser = subparsers.add_parser("check", help="Check static annotations and completeness")
    check_parser.add_argument("--json-output", type=Path)
    check_parser.add_argument(
        "--show-covered", action="store_true",
        help="Also print the full list of covered requirement IDs in the console output",
    )
    verify_parser = subparsers.add_parser("verify", help="Require successful runtime evidence")
    verify_parser.add_argument("--evidence", type=Path, required=True)
    verify_parser.add_argument("--json-output", type=Path)
    verify_parser.add_argument(
        "--show-covered", action="store_true",
        help="Also print the full list of covered requirement IDs in the console output",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    show_covered = bool(getattr(args, "show_covered", False))
    if args.command == "list":
        requirements, errors = parse_requirements(repo_root)
        report = TraceabilityReport(requirements, (), (), (), errors)
        _write_report(report, args.json_output, show_covered)
        return bool(errors)
    report = verify(repo_root, getattr(args, "evidence", None))
    _write_report(report, args.json_output, show_covered)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
