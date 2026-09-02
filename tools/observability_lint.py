"""Static observability gate: enforce the log facade as the sole log writer.

Mirrors ``tools.spec_traceability`` (single file, stdlib AST, ``check`` CLI
with optional ``--json``, exit 0/1). Rules (design §3.2):

R1  Every Evennia-logger access path (and stdlib ``logging``) in scanned
    production files is a violation; ``world/observability/`` is the only
    permanent whitelist. Frozen files (the R1-debt inventory) are exempt
    from R1 only.
R2  In facade-adopter files (anything importing ``world.observability``,
    frozen included), no ``except`` may silently swallow: its AST subtree
    (recursive, skipping nested defs/lambdas) must contain a ``raise`` or a
    facade call, or carry a reasoned exemption comment.
R3  Facade calls must pass a non-``None`` ``context=``; ``log_error`` also
    needs ``exc=`` or a ``raise`` in the enclosing handler.

Exemption comments ``# observability: ignore <R1|R2|R3>: <reason>`` are
located by tokenization (comments are absent from the AST): R1 on the import
line or the line above; R2 on the ``except`` header or before its first body
statement; R3 on the call line or the line above. Empty reasons and unknown
rule ids are violations. Unparseable scanned files are violations.

The freeze list ``tools/observability_freeze.json`` is shrink-only: duplicate
or non-existent entries, and entries whose file no longer has R1 debt
(zombies), are violations.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("world", "typeclasses", "commands", "server", "web")
WHITELIST_DIRS = ("world/observability/",)
FREEZE_PATH = "tools/observability_freeze.json"
FACADE_MODULES = {"world.observability", "world.observability.api"}
FACADE_FUNCTIONS = frozenset({"log_debug", "log_info", "log_warn", "log_error"})
RULE_IDS = frozenset({"R1", "R2", "R3"})
EXEMPTION_RE = re.compile(r"#\s*observability:\s*ignore\s+([A-Za-z0-9]+)\s*:([^#]*)$")


@dataclass(frozen=True, order=True)
class Violation:
    rule: str
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class FileReport:
    violations: tuple[Violation, ...]
    exemptions: int


@dataclass(frozen=True)
class LintReport:
    violations: tuple[Violation, ...]
    exemptions: int
    scanned_files: int
    frozen_files: int

    @property
    def ok(self) -> bool:
        return not self.violations

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "summary": {
                "violations": len(self.violations),
                "exemptions": self.exemptions,
                "scanned_files": self.scanned_files,
                "frozen_files": self.frozen_files,
            },
            "violations": [asdict(item) for item in self.violations],
        }


def _is_scanned(rel_path: str) -> bool:
    if not rel_path.endswith(".py"):
        return False
    if "/tests/" in f"/{rel_path}" or Path(rel_path).name.startswith("test_"):
        return False
    return any(rel_path == d or rel_path.startswith(f"{d}/") for d in SCAN_DIRS)


def _whitelisted(rel_path: str) -> bool:
    return rel_path.startswith(WHITELIST_DIRS)


def _attr_chain(node: ast.AST) -> list[str] | None:
    """Full dotted chain of an attribute/name expression, or None."""
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return list(reversed(parts))
    return None


class _FacadeBindings(ast.NodeVisitor):
    """Collect per-file facade import state for adopter/call detection."""

    def __init__(self) -> None:
        self.adopter = False
        self.call_names: set[str] = set()
        self.module_aliases: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in FACADE_MODULES:
                self.adopter = True
                self.module_aliases.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module in FACADE_MODULES:
            for alias in node.names:
                self.adopter = True
                if alias.name in FACADE_FUNCTIONS:
                    self.call_names.add(alias.asname or alias.name)
                elif alias.name == "*":
                    self.call_names |= set(FACADE_FUNCTIONS)
                elif alias.name == "api":
                    self.module_aliases.add(alias.asname or "api")
            return
        # ``from world import observability [as a]`` reaches the same public
        # facade and must not escape adopter detection or call recognition.
        if node.module == "world":
            for alias in node.names:
                if alias.name == "observability":
                    self.adopter = True
                    self.module_aliases.add(alias.asname or "observability")


class _RaiseScan(ast.NodeVisitor):
    """True if a raise/facade call exists in the subtree, skipping defs."""

    def __init__(self, call_names: set[str], aliases: set[str]) -> None:
        self.found = False
        self._call_names = call_names
        self._aliases = aliases

    def _skip(self, node: ast.AST) -> bool:
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))

    def generic_visit(self, node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if self._skip(child):
                continue
            if isinstance(child, ast.Raise):
                self.found = True
                return
            if isinstance(child, ast.Call) and self._is_facade_call(child):
                self.found = True
                return
            self.generic_visit(child)
            if self.found:
                return

    def _is_facade_call(self, call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Name):
            return func.id in self._call_names
        chain = _attr_chain(func)
        if chain and len(chain) >= 2 and chain[0] in self._aliases:
            return chain[-1] in FACADE_FUNCTIONS
        return False


def _is_facade_call(call: ast.Call, bindings: _FacadeBindings) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in bindings.call_names
    chain = _attr_chain(func)
    if chain and len(chain) >= 2 and chain[0] in bindings.module_aliases:
        return chain[-1] in FACADE_FUNCTIONS
    return False


def _subtree_has_raise(handler: ast.ExceptHandler) -> bool:
    """True if any ``raise`` exists in the handler subtree (skipping defs)."""

    class _Probe(ast.NodeVisitor):
        def __init__(self) -> None:
            self.found = False

        def generic_visit(self, node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    continue
                if isinstance(child, ast.Raise):
                    self.found = True
                    return
                self.generic_visit(child)
                if self.found:
                    return

    probe = _Probe()
    probe.generic_visit(handler)
    return probe.found


def _comment_map(source: str) -> dict[int, str]:
    """Map physical line numbers to their trailing comment text."""
    comments: dict[int, str] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type == tokenize.COMMENT:
                comments[token.start[0]] = token.string
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return comments


def _exemption(
    comments: dict[int, str], primary_line: int, before_line: int, rule: str
) -> tuple[bool, bool, str | None]:
    """Return (matched, invalid, invalid_detail) for an exemption lookup.

    ``primary_line`` is the target line (import/except header/call);
    ``before_line`` is the line the comment may sit on instead (line above
    the import/call, or above the first body statement for R2).
    """
    invalid: str | None = None
    for line in (primary_line, before_line):
        text = comments.get(line)
        if text is None:
            continue
        match = EXEMPTION_RE.search(text)
        if not match:
            continue
        rule_id, reason = match.group(1), match.group(2).strip()
        if rule_id not in RULE_IDS:
            invalid = f"unknown-rule-exemption:{rule_id}"
            continue
        if rule_id != rule:
            continue
        if not reason:
            invalid = "empty-reason-exemption"
            continue
        return True, invalid is not None, invalid
    return False, invalid is not None, invalid


def _scan_r1(tree: ast.AST, rel: str) -> list[Violation]:
    found: list[Violation] = []
    evennia_names: set[str] = set()
    # Pass 1: imports (themselves violations, or bind Evennia root names).
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if alias.name == "evennia.utils.logger":
                    found.append(
                        Violation("R1", rel, node.lineno, f"imports {alias.name}")
                    )
                if alias.name == "evennia" or alias.name.startswith("evennia.utils"):
                    evennia_names.add(alias.asname or top)
                if alias.name == "logging" or alias.name.startswith("logging."):
                    found.append(
                        Violation(
                            "R1", rel, node.lineno, f"stdlib logging import: {alias.name}"
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "evennia.utils.logger" or module.startswith("logging."):
                found.append(Violation("R1", rel, node.lineno, f"imports {module}"))
            elif module in {"evennia", "evennia.utils"}:
                for alias in node.names:
                    if alias.name == "logger":
                        found.append(
                            Violation(
                                "R1",
                                rel,
                                node.lineno,
                                f"imports logger from {module}",
                            )
                        )
    # Pass 2: evennia.logger.* attribute access (imports bind root names above).
    if evennia_names:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            chain = _attr_chain(node)
            if (
                chain
                and chain[0] in evennia_names
                and "logger" in chain[1:]
            ):
                found.append(
                    Violation(
                        "R1",
                        rel,
                        node.lineno,
                        "accesses Evennia logger attribute",
                    )
                )
    return found


def _scan_file(rel: str, source: str) -> FileReport:
    violations: list[Violation] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return FileReport(
            (Violation("parse", rel, error.lineno or 1, f"unparseable: {error.msg}"),), 0
        )

    bindings = _FacadeBindings()
    bindings.visit(tree)
    comments = _comment_map(source)
    body_first_line = {
        id(handler): handler.body[0].lineno for handler in _handlers(tree) if handler.body
    }
    matched_exemptions = 0

    def consume_exempt(target_line: int, before_line: int, rule: str) -> bool:
        nonlocal matched_exemptions
        matched, invalid, detail = _exemption(comments, target_line, before_line, rule)
        if invalid and detail and not matched:
            violations.append(
                Violation(rule, rel, target_line, f"invalid exemption comment: {detail}")
            )
        if matched:
            matched_exemptions += 1
        return matched

    # R1
    if not _whitelisted(rel):
        for violation in _scan_r1(tree, rel):
            if not consume_exempt(violation.line, violation.line - 1, "R1"):
                violations.append(violation)

    if bindings.adopter:
        # R2: silent handlers in facade adopters.
        scanner = _RaiseScan(bindings.call_names, bindings.module_aliases)
        for handler in _handlers(tree):
            if not handler.body:
                continue
            scanner.found = False
            scanner.generic_visit(handler)
            if scanner.found:
                continue
            header = handler.lineno
            before = body_first_line.get(id(handler), header + 1) - 1
            if not consume_exempt(header, before, "R2"):
                where = getattr(handler.type, "id", None) or (
                    getattr(handler.type, "attr", None) if handler.type else "bare"
                )
                violations.append(
                    Violation(
                        "R2", rel, header, f"handler ({where}) swallows exception silently"
                    )
                )

        # R3: facade call sites.
        for call in _facade_calls(tree, bindings):
            func_name = _facade_call_name(call, bindings)
            kwargs = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}
            needs_context = "context" in kwargs and not (
                isinstance(kwargs["context"], ast.Constant) and kwargs["context"].value is None
            )
            problems: list[str] = []
            if not needs_context:
                problems.append("missing context")
            if func_name == "log_error":
                has_exc = "exc" in kwargs
                handler = _enclosing_handler(tree, call.lineno)
                has_raise = handler is not None and _subtree_has_raise(handler)
                if not has_exc and not has_raise:
                    problems.append("log_error without exc or raise")
            if not problems:
                continue
            if consume_exempt(call.lineno, call.lineno - 1, "R3"):
                continue
            violations.append(Violation("R3", rel, call.lineno, ", ".join(problems)))

    # Exemption comments that are structurally invalid anywhere in the file
    # (unknown rule id / empty reason) must stay visible even with no match.
    for line, text in comments.items():
        match = EXEMPTION_RE.search(text)
        if not match:
            continue
        rule_id, reason = match.group(1), match.group(2).strip()
        if rule_id not in RULE_IDS:
            violations.append(
                Violation("R3", rel, line, f"unknown rule id in exemption: {rule_id}")
            )
        elif not reason:
            violations.append(
                Violation(rule_id, rel, line, "exemption reason is empty")
            )

    deduped = sorted(set(violations))
    return FileReport(tuple(deduped), matched_exemptions)


def _handlers(tree: ast.AST) -> list[ast.ExceptHandler]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]


def _facade_calls(tree: ast.AST, bindings: _FacadeBindings) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_facade_call(node, bindings)
    ]


def _facade_call_name(call: ast.Call, bindings: _FacadeBindings) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    chain = _attr_chain(func)
    return chain[-1] if chain else ""


def _enclosing_handler(tree: ast.AST, call_line: int) -> ast.ExceptHandler | None:
    best: ast.ExceptHandler | None = None
    for handler in _handlers(tree):
        if handler.lineno <= call_line <= handler.end_lineno:  # type: ignore[operator]
            if best is None or handler.lineno > best.lineno:
                best = handler
    return best


def _production_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            if _is_scanned(rel):
                files.append(path)
    return files


def _load_freeze(root: Path) -> tuple[list[str], list[Violation]]:
    path = root / FREEZE_PATH
    if not path.is_file():
        return [], [Violation("freeze", FREEZE_PATH, 1, "freeze manifest missing")]
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [], [Violation("freeze", FREEZE_PATH, 1, f"invalid JSON: {error.msg}")]
    if not isinstance(entries, list) or any(not isinstance(e, str) for e in entries):
        return [], [Violation("freeze", FREEZE_PATH, 1, "manifest must be a list of paths")]
    violations: list[Violation] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if entry in seen:
            violations.append(Violation("freeze", FREEZE_PATH, index + 1, f"duplicate entry: {entry}"))
        seen.add(entry)
        if not (root / entry).is_file():
            violations.append(Violation("freeze", FREEZE_PATH, index + 1, f"non-existent path: {entry}"))
    return entries, violations


def check_repo(root: Path) -> LintReport:
    freeze, violations = _load_freeze(root)
    frozen = set(freeze)
    production = {
        path.relative_to(root).as_posix() for path in _production_files(root)
    }
    for index, entry in enumerate(freeze):
        # Only scanned production files can hold R1 debt; an entry elsewhere
        # (tests, tools, other trees) is an undetectable permanent zombie and
        # defeats the shrink-only ratchet.
        if entry not in production:
            violations.append(
                Violation(
                    "freeze",
                    FREEZE_PATH,
                    index + 1,
                    f"entry is not a scanned production file: {entry}",
                )
            )
    exemptions = 0
    scanned = 0
    for path in _production_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            violations.append(Violation("read", rel, 1, f"unreadable: {error}"))
            continue
        scanned += 1
        report = _scan_file(rel, source)
        r1 = [item for item in report.violations if item.rule == "R1"]
        other = [item for item in report.violations if item.rule != "R1"]
        exemptions += report.exemptions
        if rel in frozen:
            if not r1:
                violations.append(
                    Violation(
                        "freeze", FREEZE_PATH, 1, f"stale entry (no R1 debt remains): {rel}"
                    )
                )
        else:
            violations.extend(r1)
        violations.extend(other)
    return LintReport(
        violations=tuple(sorted(set(violations))),
        exemptions=exemptions,
        scanned_files=scanned,
        frozen_files=len(frozen),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.observability_lint")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="run the observability rules")
    check.add_argument("--json", action="store_true", help="emit the machine report")
    arguments = parser.parse_args(argv)
    if arguments.command == "check":
        report = check_repo(REPO_ROOT)
        if arguments.json:
            print(json.dumps(report.to_json(), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for item in report.violations:
                print(f"{item.path}:{item.line}: {item.rule}: {item.message}")
            print(
                f"scanned={report.scanned_files} frozen={report.frozen_files} "
                f"violations={len(report.violations)} exemptions={report.exemptions}"
            )
        return 0 if report.ok else 1
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
