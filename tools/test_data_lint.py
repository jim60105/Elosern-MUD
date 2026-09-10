"""Test-data independence gate: block shipped-content references in behavior tests.

Mirrors ``tools.spec_traceability`` / ``tools.observability_lint`` (single file,
stdlib + yaml + Evennia bootstrap, ``check``/``list``/``report`` CLI with
``--json``, exit 0/1). Design: openspec change ``add-test-data-independence-gate``.

Rules (design D2, stable violation codes):

``unexempted``          a flagged test file is in neither ``contract`` nor ``debt``
``new-debt``            a ``debt`` ledger path is absent from ``seedDebtPaths``
``untagged-contract``   a ``contract`` entry's file lacks the ``Data-contract test:`` tag
``stale-path``          a ledger path no longer exists on disk
``duplicate``           a path appears twice, or under both ledger kinds
``seed-mismatch``       the ledger's frozen fields diverge from the seed file the gate
                        carries as data (``tools/test_data_lint_seed.json``)

Findings (flag classes; any finding flags its file, ``quantity-pin`` is reported
separately in the machine output per design D4):

token        a statically resolvable string expression equal to a shipped-content
             universe token (constants, literal-only concatenation, all-literal
             f-strings joined and per-piece; JS/TS quoted and template literals)
symbol-ref   a name/attribute reference to a catalog symbol (``*_REGISTRY``,
             ``*_TABLE``, ``*_TIERS``, ``*_PACK_REGISTRY``, ``XYMAP_DATA``)
quantity-pin ``assertEqual``/``assertNotEqual`` of ``len(<catalog symbol>)`` against
             a literal count

The shipped-content token universe is derived at lint time (design D1): import the
locked catalogs (``world.lore``, ``world.skills``, ``world.quests``, ``world.maps``,
``world.rules.dialogue``) under ``server.conf.settings`` with no DB access, harvest
module-level mapping keys plus complete display-field values, add rulebook YAML
catalog keys, then subtract ``tools/test_data_lint_deny.json`` (rule-bound entries,
each with a reason and scanner regression). Display tokens are complete harvested
field values, never substrings.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import dataclasses
import importlib
import io
import json
import os
import pkgutil
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = "tools/test_data_freeze.json"
SEED_PATH = "tools/test_data_lint_seed.json"
DENY_PATH = "tools/test_data_lint_deny.json"
TAG = "Data-contract test:"
CORPUS_ROOTS = ("commands/", "server/", "typeclasses/", "world/", "web/", "tests/", "tools/tests/")
CORPUS_EXCLUDES = ("/dist/", "/node_modules/")
JS_SUFFIXES = (".js", ".mjs", ".cjs", ".ts", ".tsx")
CATALOG_PACKAGES = ("world.lore", "world.skills", "world.quests", "world.maps")
EXTRA_CATALOG_MODULES = ("world.rules.dialogue",)
SYMBOL_RE = re.compile(r"(_REGISTRY|_TABLE|_TIERS|_PACK_REGISTRY)$|^XYMAP_DATA$")
DISPLAY_FIELDS = frozenset(
    {
        "label", "name", "display_name", "display_name_zh", "display", "title",
        "name_zh", "common_name_zh", "host_name", "host_title",
        "examiner_name", "examiner_title", "rank_name", "pronoun_display",
        "label_zh", "title_zh", "display_label", "common_name",
    }
)
RULEBOOK_CATALOG_KEYS = {
    "buffs.yaml": ("buffs",),
    "professions.yaml": ("professions",),
    "clock.yaml": ("periods",),
    "npc_schedules.yaml": ("schedules",),
    "monster_behaviour.yaml": ("behaviours",),
    "item_effects.yaml": ("effects",),
    "equipment_effects.yaml": ("effects",),
    "sexual_pleasure.yaml": ("tiers",),
    "sexual_resist.yaml": ("stages",),
    "status_display.yaml": ("statuses",),
}
VIOLATION_CODES = ("unexempted", "new-debt", "untagged-contract", "stale-path", "duplicate", "seed-mismatch")

_JS_LITERAL_RE = re.compile(r"""(?:'([^'\\\n]{1,400})'|"([^"\\\n]{1,400})"|`([^`\\\n]{1,800})`)""", re.S)
_JS_CONCAT_RE = re.compile(r"(?:(['\"])(?:(?!\1).){1,400}?\1|\`[^\`\n]{1,800}?\`)(?:\s*\+\s*(?:(['\"])(?:(?!\2).){1,400}?\2|\`[^\`\n]{1,800}?\`))+")
_JS_PIECE_RE = re.compile(r"(['\"`])(?:(?!\1).)*?\1", re.S)


@dataclass(frozen=True, order=True)
class Finding:
    kind: str  # token | symbol-ref | quantity-pin
    path: str
    line: int
    detail: str


@dataclass(frozen=True, order=True)
class Violation:
    rule: str
    path: str
    detail: str


@dataclass(frozen=True)
class Universe:
    tokens: frozenset[str]
    symbols: frozenset[str]
    denied: frozenset[str]
    raw_tokens: frozenset[str] = frozenset()
    skipped_modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateReport:
    violations: tuple[Violation, ...]
    token_findings: tuple[Finding, ...]
    quantity_pins: tuple[Finding, ...]
    symbol_refs: tuple[Finding, ...]
    flagged_files: int
    scanned_files: int
    universe_tokens: int
    universe_symbols: int

    @property
    def ok(self) -> bool:
        return not self.violations

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violations": [dataclasses.asdict(v) for v in self.violations],
            "findings": {
                "token": [dataclasses.asdict(f) for f in self.token_findings],
                "quantity-pin": [dataclasses.asdict(f) for f in self.quantity_pins],
                "symbol-ref": [dataclasses.asdict(f) for f in self.symbol_refs],
            },
            "summary": {
                "flagged_files": self.flagged_files,
                "scanned_files": self.scanned_files,
                "universe_tokens": self.universe_tokens,
                "universe_symbols": self.universe_symbols,
                "violations": len(self.violations),
            },
        }


# --------------------------------------------------------------------------- universe


def _harvest_display(value: Any, seen: set[int], out: set[str]) -> None:
    """Collect complete values of display-bearing fields from catalog structures."""
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, (dict, MappingProxyType)):
        for key, item in value.items():
            if isinstance(key, str) and key in DISPLAY_FIELDS and isinstance(item, str) and item:
                out.add(item)
            _harvest_display(item, seen, out)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _harvest_display(item, seen, out)
    elif isinstance(value, str):
        return
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for fld in dataclasses.fields(value):
            field_value = getattr(value, fld.name)
            if fld.name in DISPLAY_FIELDS and isinstance(field_value, str) and field_value:
                out.add(field_value)
            else:
                _harvest_display(field_value, seen, out)
    else:
        attributes = getattr(value, "__dict__", None)
        if isinstance(attributes, dict):
            for key, field_value in attributes.items():
                if key in DISPLAY_FIELDS and isinstance(field_value, str) and field_value:
                    out.add(field_value)
                else:
                    _harvest_display(field_value, seen, out)


def _catalog_module_names() -> list[str]:
    import world
    import world.lore
    import world.maps
    import world.quests
    import world.skills

    packages = {"world.lore": world.lore, "world.skills": world.skills, "world.quests": world.quests, "world.maps": world.maps}
    names: list[str] = []
    for package_name, package in packages.items():
        for module in pkgutil.walk_packages(package.__path__, package_name + "."):
            names.append(module.name)
    names.extend(EXTRA_CATALOG_MODULES)
    return names


def _defines_catalog_mapping(root: Path, module_name: str) -> bool:
    """True if a module's source assigns a module-level UPPER mapping (data module)."""
    rel = module_name.replace(".", "/")
    for candidate in (f"{rel}.py", f"{rel}/__init__.py"):
        path = root / candidate
        if path.is_file():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                return True
            for node in tree.body:
                if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                    continue
                if isinstance(node.value, (ast.Dict, ast.DictComp)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name) and re.match(r"[A-Z][A-Z0-9_]*$", target.id):
                            return True
            return False
    return False


def _rulebook_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    rulebook = root / "world" / "rules" / "rulebook"
    if not rulebook.is_dir():
        return keys
    for path in sorted(rulebook.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError):
            continue
        wrapper = RULEBOOK_CATALOG_KEYS.get(path.name)
        if wrapper:
            current = doc
            for word in wrapper:
                if not isinstance(current, dict) or word not in current:
                    current = None
                    break
                current = current[word]
            if isinstance(current, dict):
                keys.update(k for k in current if isinstance(k, str))
        elif isinstance(doc, dict):
            keys.update(k for k in doc if isinstance(k, str))
    return keys


def derive_universe(root: Path) -> Universe:
    """Derive the shipped-content token universe + catalog symbols (design D1)."""
    # Evennia's bootstrap and catalog imports print operator warnings to stdout;
    # swallow the chatter so ``--json``/``report`` output stays machine-clean.
    with contextlib.redirect_stdout(io.StringIO()):
        universe = _derive_universe(root)
    if universe.skipped_modules:
        print(
            "test_data_lint: catalog-data modules skipped at import (need runtime state): "
            + ", ".join(universe.skipped_modules),
            file=sys.stderr,
        )
    return universe


def _derive_universe(root: Path) -> Universe:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()

    tokens: set[str] = set()
    symbols: set[str] = set()
    skipped: list[str] = []
    for name in _catalog_module_names():
        if ".tests" in name or ".test_" in name:
            continue
        try:
            module = importlib.import_module(name)
        except Exception:
            # Modules that need runtime state (DB/typeclass init) hold no catalog
            # data usable at lint time. The skip is reported to stderr (never
            # silent), so a catalog that stops importing cannot shrink the
            # universe unnoticed.
            if _defines_catalog_mapping(root, name):
                skipped.append(name)
            continue
        for attr, value in vars(module).items():
            if attr.startswith("_"):
                continue
            if isinstance(value, (dict, MappingProxyType)) and value:
                tokens.update(k for k in value if isinstance(k, str) and k)
                if attr.isupper() and SYMBOL_RE.search(attr):
                    symbols.add(attr)
                _harvest_display(value, set(), tokens)
    tokens.update(_rulebook_keys(root))

    deny_path = root / DENY_PATH
    denied: set[str] = set()
    if deny_path.is_file():
        payload = json.loads(deny_path.read_text(encoding="utf-8"))
        entries = payload.get("entries", []) if isinstance(payload, dict) else payload
        if not isinstance(entries, list) or any(
            not isinstance(e, dict) or not all(isinstance(e.get(k), str) and e.get(k) for k in ("token", "rule", "reason", "evidence"))
            for e in entries
        ):
            raise SystemExit(f"deny list malformed: {DENY_PATH} entries need string token/rule/reason/evidence")
        for entry in entries:
            token = entry["token"] if isinstance(entry, dict) else entry
            denied.add(token)
    return Universe(
        tokens=frozenset(tokens - denied),
        symbols=frozenset(symbols),
        denied=frozenset(denied),
        raw_tokens=frozenset(tokens),
        skipped_modules=tuple(skipped),
    )


# --------------------------------------------------------------------------- corpus


def _is_test_path(rel: str) -> bool:
    base = rel.rsplit("/", 1)[-1]
    return (
        "/tests/" in f"/{rel}"
        or (base.startswith("test_") and base.endswith(".py"))
        or bool(re.search(r"\.test\.(js|mjs|cjs|ts|tsx)$", base))
        or "_spec." in base
    )


def test_corpus(root: Path, files: Iterable[str] | None = None) -> list[str]:
    """Versioned test sources: ``git ls-files`` ∩ corpus roots ∩ test-file pattern (D4)."""
    if files is None:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True, text=True, check=True,
        )
        files = [name for name in proc.stdout.split("\0") if name]
    out: list[str] = []
    for rel in files:
        if not rel.startswith(CORPUS_ROOTS) or any(x in rel for x in CORPUS_EXCLUDES):
            continue
        if not rel.endswith((".py",) + JS_SUFFIXES):
            continue
        if _is_test_path(rel):
            out.append(rel)
    return sorted(out)


# --------------------------------------------------------------------------- scanning


def _resolvable_strings(node: ast.AST) -> list[str] | None:
    """Statically resolvable string values of an expression (constants, literal-only
    concatenation, all-literal f-strings: the joined string and each literal piece)."""
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolvable_strings(node.left)
        right = _resolvable_strings(node.right)
        if left is None or right is None:
            return None
        return [f"{a}{b}" for a in left for b in right]
    if isinstance(node, ast.JoinedStr):
        piece_options: list[list[str]] = []
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                resolved = _resolvable_strings(part.value)
            else:
                resolved = _resolvable_strings(part)
            if resolved is None:
                return None
            piece_options.append(resolved)
        joined = ["".join(combo) for combo in _product(piece_options)]
        pieces = [piece for options in piece_options for piece in options]
        return joined + pieces
    return None


def _product(options: list[list[str]]) -> Iterable[tuple[str, ...]]:
    combos: list[tuple[str, ...]] = [()]
    for choice in options:
        combos = [c + (pick,) for c in combos for pick in choice]
    return combos


def _string_findings(tree: ast.AST, universe: Universe, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Constant, ast.BinOp, ast.JoinedStr)):
            continue
        values = _resolvable_strings(node)
        if not values:
            continue
        for value in values:
            if value in universe.tokens:
                findings.append(Finding("token", rel, getattr(node, "lineno", 1), value))
    return findings


def _symbol_findings(tree: ast.AST, universe: Universe, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in universe.symbols:
            findings.append(Finding("symbol-ref", rel, node.lineno, node.id))
        elif isinstance(node, ast.Attribute) and node.attr in universe.symbols:
            findings.append(Finding("symbol-ref", rel, node.lineno, node.attr))
    return findings


def _quantity_pins(tree: ast.AST, universe: Universe, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in {"assertEqual", "assertNotEqual"} and len(node.args) == 2:
                length_arg, other_arg = (
                    (node.args[0], node.args[1])
                    if isinstance(node.args[0], ast.Call) and getattr(node.args[0].func, "id", None) == "len"
                    else (node.args[1], node.args[0])
                    if isinstance(node.args[1], ast.Call) and getattr(node.args[1].func, "id", None) == "len"
                    else (None, None)
                )
                if length_arg is not None and _pins_length(length_arg, other_arg, universe):
                    findings.append(Finding("quantity-pin", rel, node.lineno, name))
        elif isinstance(node, ast.Compare) and isinstance(node.comparators[0], ast.Constant):
            left_is_len = isinstance(node.left, ast.Call) and getattr(node.left.func, "id", None) == "len"
            right_is_len = isinstance(node.comparators[0], ast.Call)
            if not left_is_len:
                continue
            if type(node.ops[0]) not in (ast.Eq, ast.NotEq):
                continue
            if isinstance(node.comparators[0].value, int) and not isinstance(node.comparators[0].value, bool):
                if _references_symbol(node.left, universe):
                    findings.append(Finding("quantity-pin", rel, node.lineno, "assert"))
    return findings


def _references_symbol(length_call: ast.Call, universe: Universe) -> bool:
    referenced = {
        getattr(inner, "id", None) or getattr(inner, "attr", None)
        for inner in ast.walk(length_call)
    }
    return bool(referenced & universe.symbols)


def _pins_length(length_arg: ast.Call, other_arg: ast.AST, universe: Universe) -> bool:
    """A quantity pin: len(<catalog symbol>) compared against an integer literal."""
    if not isinstance(other_arg, ast.Constant) or isinstance(other_arg.value, bool) or not isinstance(other_arg.value, int):
        return False
    return _references_symbol(length_arg, universe)


def _js_string_findings(source: str, universe: Universe, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in _JS_LITERAL_RE.finditer(source):
        value = next((g for g in match.groups() if g is not None), "")
        if value in universe.tokens:
            line = source.count("\n", 0, match.start()) + 1
            findings.append(Finding("token", rel, line, value))
    seen_lines: set[int] = set()
    for match in _JS_CONCAT_RE.finditer(source):
        pieces = [m.group(0)[1:-1] for m in _JS_PIECE_RE.finditer(match.group(0))]
        joined = "".join(pieces)
        if joined in universe.tokens:
            line = source.count("\n", 0, match.start()) + 1
            if line not in seen_lines:
                seen_lines.add(line)
                findings.append(Finding("token", rel, line, joined))
    return findings


def scan_file(root: Path, rel: str, universe: Universe) -> list[Finding]:
    try:
        source = (root / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    if rel.endswith(".py"):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return [Finding("token", rel, 1, "<unparseable>")]
        return _string_findings(tree, universe, rel) + _symbol_findings(tree, universe, rel) + _quantity_pins(tree, universe, rel)
    return _js_string_findings(source, universe, rel)


# --------------------------------------------------------------------------- ledger


def _tag_rationale(root: Path, rel: str) -> str | None:
    """The rationale after the ``Data-contract test:`` tag, or None when untagged."""
    try:
        lines = (root / rel).read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return None
    if rel.endswith(".py"):
        try:
            doc = ast.get_docstring(ast.parse("\n".join(lines)), clean=False)
        except SyntaxError:
            return None
        if not doc:
            return None
        for line in doc.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[len(TAG):].strip() if stripped.startswith(TAG) else None
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            comment = stripped[2:].strip()
            return comment[len(TAG):].strip() if comment.startswith(TAG) else None
        return None
    return None


def _shape_error(payload: Any) -> str | None:
    """Deterministic shape check for ledger/seed payloads; None when well-formed."""
    if not isinstance(payload, dict):
        return "top level is not an object"
    if not isinstance(payload.get("seedDebtPaths", []), list) or any(
        not isinstance(p, str) for p in payload.get("seedDebtPaths", [])
    ):
        return "seedDebtPaths must be a list of paths"
    if not isinstance(payload.get("debt", []), list) or any(
        not isinstance(p, str) for p in payload.get("debt", [])
    ):
        return "debt must be a list of paths"
    if not isinstance(payload.get("contract", []), list):
        return "contract must be a list"
    for entry in payload.get("contract", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not isinstance(entry.get("reason"), str):
            return "contract entries need string path and reason"
    return None


def load_ledger(root: Path) -> tuple[dict[str, Any], list[Violation]]:
    path = root / LEDGER_PATH
    if not path.is_file():
        return {}, [Violation("stale-path", LEDGER_PATH, "ledger manifest missing")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {}, [Violation("stale-path", LEDGER_PATH, f"invalid JSON: {error.msg}")]
    shape = _shape_error(data)
    if shape:
        return {}, [Violation("stale-path", LEDGER_PATH, f"malformed ledger: {shape}")]
    return data, []


def load_seed(root: Path) -> dict[str, Any]:
    path = root / SEED_PATH
    if not path.is_file():
        raise SystemExit(f"seed classification missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    shape = _shape_error(payload)
    if shape:
        raise SystemExit(f"seed classification malformed: {shape}")
    return payload


def seed_freeze(root: Path) -> dict[str, Any]:
    """Deterministically regenerate the ledger from the carried classification (D6).

    ``contract`` and ``seedDebtPaths`` come verbatim (sorted) from
    ``tools/test_data_lint_seed.json``; ``debt`` is the seeded corpus plus any file
    the gate flags today that the classification did not know about.
    """
    seed = load_seed(root)
    universe = derive_universe(root)
    flagged = {finding.path for rel in test_corpus(root) for finding in scan_file(root, rel, universe)}
    contracts = sorted(seed["contract"], key=lambda c: c["path"])
    contract_paths = {c["path"] for c in contracts}
    seed_debt = sorted(set(seed["seedDebtPaths"]))
    debt = sorted((set(seed_debt) | flagged) - contract_paths)
    return {"seedDebtPaths": seed_debt, "contract": contracts, "debt": debt}


def check_ledger(root: Path, ledger: dict[str, Any], universe: Universe, files: Iterable[str] | None = None) -> GateReport:
    violations: list[Violation] = []
    seed = load_seed(root)
    seed_debt = sorted(set(seed["seedDebtPaths"]))
    seed_contracts = sorted(seed["contract"], key=lambda c: c["path"])

    contract_entries = ledger.get("contract", [])
    debt_entries = ledger.get("debt", [])
    ledger_seed = sorted(ledger.get("seedDebtPaths", []))
    if ledger_seed != seed_debt:
        violations.append(Violation("seed-mismatch", LEDGER_PATH, "seedDebtPaths diverges from tools/test_data_lint_seed.json"))
    ledger_by_path = {c["path"]: c.get("reason", "") for c in contract_entries}
    for entry in seed_contracts:
        recorded = ledger_by_path.get(entry["path"])
        if recorded is None:
            violations.append(Violation("seed-mismatch", entry["path"], "seeded contract entry missing from ledger"))
        elif recorded != entry["reason"]:
            violations.append(Violation("seed-mismatch", entry["path"], "contract reason diverges from tools/test_data_lint_seed.json"))

    debt = sorted(debt_entries)
    debt_set = set(debt_entries)
    contract_paths = {c["path"] for c in contract_entries}
    seed_contract_paths = {c["path"] for c in seed_contracts}
    for path in sorted(contract_paths - seed_contract_paths - set(seed_debt)):
        violations.append(Violation("new-debt", path, "contract registration outside the seeded classification"))

    if len(debt_set) != len(debt_entries):
        for path in sorted({p for p in debt_entries if debt_entries.count(p) > 1}):
            violations.append(Violation("duplicate", path, "debt path listed twice"))
    seen_contract: set[str] = set()
    for entry in contract_entries:
        path = entry["path"]
        if path in seen_contract:
            violations.append(Violation("duplicate", path, "contract path listed twice"))
        seen_contract.add(path)
        if path in debt_set:
            violations.append(Violation("duplicate", path, "registered as both contract and debt"))

    for path in sorted(debt_set - set(ledger_seed)):
        violations.append(Violation("new-debt", path, "debt entry absent from seedDebtPaths"))
    for path in sorted(debt_set | contract_paths):
        if not (root / path).is_file():
            violations.append(Violation("stale-path", path, "ledger path missing on disk"))
    for entry in sorted(contract_entries, key=lambda c: c["path"]):
        rationale = _tag_rationale(root, entry["path"])
        if rationale is None:
            violations.append(Violation("untagged-contract", entry["path"], f'missing "{TAG}" tag line'))
        elif not rationale:
            violations.append(Violation("untagged-contract", entry["path"], "tag carries no rationale"))
        elif rationale != entry.get("reason", ""):
            violations.append(Violation("untagged-contract", entry["path"], "tag rationale diverges from the ledger reason"))

    corpus = test_corpus(root, files)
    findings: list[Finding] = []
    for rel in corpus:
        findings.extend(scan_file(root, rel, universe))
    token = sorted(f for f in findings if f.kind == "token")
    pins = sorted(f for f in findings if f.kind == "quantity-pin")
    refs = sorted(f for f in findings if f.kind == "symbol-ref")
    flagged = sorted({f.path for f in findings})
    for path in flagged:
        if path not in debt_set and path not in contract_paths:
            details = "; ".join(sorted({f"{f.kind}:{f.detail}" for f in findings if f.path == path}))[:300]
            violations.append(Violation("unexempted", path, details))

    return GateReport(
        violations=tuple(sorted(violations)),
        token_findings=tuple(token),
        quantity_pins=tuple(pins),
        symbol_refs=tuple(refs),
        flagged_files=len(flagged),
        scanned_files=len(corpus),
        universe_tokens=len(universe.tokens),
        universe_symbols=len(universe.symbols),
    )


def check_repo(root: Path, files: Iterable[str] | None = None) -> GateReport:
    ledger, fatal = load_ledger(root)
    if fatal:
        return GateReport(tuple(fatal), (), (), (), 0, 0, 0, 0)
    universe = derive_universe(root)
    return check_ledger(root, ledger, universe, files)


# --------------------------------------------------------------------------- CLI


def _console(report: GateReport) -> None:
    for violation in report.violations:
        print(f"{violation.path}: {violation.rule}: {violation.detail}")
    print(
        f"test-data-lint: scanned={report.scanned_files} flagged={report.flagged_files} "
        f"universe={report.universe_tokens}+{report.universe_symbols} "
        f"quantity-pins={len(report.quantity_pins)} violations={len(report.violations)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.test_data_lint", description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("check", "run the gate against the committed ledger"),
        ("list", "list flagged files and findings without failing"),
        ("report", "full machine-readable scan"),
    ):
        sub.add_parser(name, help=help_text).add_argument("--json", action="store_true")
    seed_parser = sub.add_parser("seed", help="write the ledger from the carried classification (one-time)")
    seed_parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.command == "seed":
        freeze = seed_freeze(root)
        if args.dry_run:
            print(json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        (root / LEDGER_PATH).write_text(json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"seeded {LEDGER_PATH}: {len(freeze['contract'])} contract, {len(freeze['debt'])} debt")
        return 0

    if args.command == "report":
        universe = derive_universe(root)
        corpus = test_corpus(root)
        findings = sorted(f for rel in corpus for f in scan_file(root, rel, universe))
        payload = {
            "findings": [dataclasses.asdict(f) for f in findings],
            "summary": {"scanned_files": len(corpus), "flagged_files": len({f.path for f in findings})},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    report = check_repo(root)
    if args.command == "list":
        by_file: dict[str, list[Finding]] = {}
        for finding in report.token_findings + report.quantity_pins + report.symbol_refs:
            by_file.setdefault(finding.path, []).append(finding)
        for path in sorted(by_file):
            kinds = {f.kind for f in by_file[path]}
            print(f"{path}\t{','.join(sorted(kinds))}")
        return 0
    if args.json:
        print(json.dumps(report.to_json(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _console(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
