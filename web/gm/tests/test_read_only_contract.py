"""Static read-only contract over ``web/gm/readers`` (tasks 1.3 / 6.1).

Establishes the delta requirement "Two-layer immutable inspection acceptance":
inspection modules may never call a writer (``save``/``create``/``delete``/
``update``/… ), assign a stored field (``obj.db.<key>``, ``obj.db_*``, an
Attribute/Tag handler) or import a known writer — including the dialogue
context assembly that settles correspondence and appends frames. The contract
also proves it rejects deliberately forbidden syntax, and that every reader
imports the helpers it uses (a missing section-helper import would otherwise
surface only as a contained runtime section error). The
``gm-runtime-state::*`` requirement IDs this module covers enter the
traceability index when the change's delta spec is synced at archive.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

READERS = Path(__file__).resolve().parents[1] / "readers"

#: Method names that create, mutate or remove persistent state.
FORBIDDEN_METHODS = frozenset(
    {
        "save",
        "create",
        "delete",
        "update",
        "add",
        "set",
        "remove",
        "clear",
        "get_or_create",
        "update_or_create",
        "bulk_create",
        "bulk_update",
    }
)

#: Imported symbols that write domain state (or assemble it for writing).
FORBIDDEN_IMPORTS = frozenset(
    {
        "build_dialogue_context",
        "record_memory",
        "revise_memory",
        "supersede_memory",
        "record_narrative_event",
        "append_payload",
        "remove_payload",
        "get_store",
        "settle_correspondence",
        "register_quest_definition",
        "register_quest_issuance",
    }
)

#: Assignment-target attribute prefixes that are stored state.
FORBIDDEN_TARGET_ATTRS = frozenset({"db", "attributes", "tags", "nattributes", "ndb"})

#: The internal modules whose exported helpers a reader must import to use.
HELPER_MODULES = ("_sections", "_entities", "_json")


def _modules() -> list[Path]:
    return sorted(path for path in READERS.glob("*.py") if path.name != "__init__.py")


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def forbidden_calls(tree: ast.Module) -> list[str]:
    """Every ``<expr>.save()``/``.create()``/… call, as ``name:line``."""
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else None
        if name in FORBIDDEN_METHODS:
            found.append(f"{name}:{node.lineno}")
        if isinstance(func, ast.Name) and func.id in {
            "create_object",
            "create_script",
            "create_account",
        }:
            found.append(f"{func.id}:{node.lineno}")
    return found


def forbidden_imports(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS or alias.asname in FORBIDDEN_IMPORTS:
                    found.append(f"{alias.name}:{node.lineno}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS:
                    found.append(f"{alias.name}:{node.lineno}")
    return found


def _assignment_targets(node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> list[ast.expr]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    return [node.target]


def forbidden_assignments(tree: ast.Module) -> list[str]:
    """Every assignment into ``.db``/``.db_*``/handler storage."""
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            continue
        for target in _assignment_targets(node):
            for candidate in ast.walk(target):
                if not isinstance(candidate, ast.Attribute):
                    continue
                if candidate.attr in FORBIDDEN_TARGET_ATTRS or candidate.attr.startswith("db_"):
                    found.append(f"{candidate.attr}:{candidate.lineno}")
    return found


def _argument_names(arguments: ast.arguments) -> set[str]:
    """Every parameter name an ``arguments`` node binds (functions and lambdas)."""
    names = {argument.arg for argument in (*arguments.posonlyargs, *arguments.args)}
    names.update(argument.arg for argument in arguments.kwonlyargs)
    if arguments.vararg:
        names.add(arguments.vararg.arg)
    if arguments.kwarg:
        names.add(arguments.kwarg.arg)
    return names


def _bound_names(tree: ast.Module) -> set[str]:
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                bound.update(_argument_names(node.args))
        elif isinstance(node, ast.Lambda):
            bound.update(_argument_names(node.args))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.Global | ast.Nonlocal):
            bound.update(node.names)
    return bound


def missing_helper_imports(tree: ast.Module, exported: set[str]) -> list[str]:
    """Exported helper names a module uses without importing or defining."""
    used = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    return sorted((used & exported) - _bound_names(tree))


def _exported_helpers() -> set[str]:
    exported: set[str] = set()
    for module in HELPER_MODULES:
        tree = _tree(READERS / f"{module}.py")
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            ):
                exported.update(
                    element.value
                    for element in node.value.elts  # type: ignore[attr-defined]
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                )
    return exported


class ReaderStaticContractTest(unittest.TestCase):
    def test_readers_never_call_a_writer(self):
        for path in _modules():
            with self.subTest(module=path.name):
                self.assertEqual(forbidden_calls(_tree(path)), [])

    def test_readers_never_import_a_known_writer(self):
        for path in _modules():
            with self.subTest(module=path.name):
                self.assertEqual(forbidden_imports(_tree(path)), [])

    def test_readers_never_assign_stored_state(self):
        for path in _modules():
            with self.subTest(module=path.name):
                self.assertEqual(forbidden_assignments(_tree(path)), [])

    def test_readers_import_every_section_helper_they_use(self):
        exported = _exported_helpers()
        self.assertIn("tree", exported)
        for path in _modules():
            with self.subTest(module=path.name):
                self.assertEqual(missing_helper_imports(_tree(path), exported), [])

    def test_the_contract_rejects_deliberately_forbidden_syntax(self):
        cases = {
            "obj.save()": forbidden_calls,
            "handler.attributes.add('x', value=1)": forbidden_calls,
            "Scratch.objects.get_or_create(key='x')": forbidden_calls,
            "obj.db.wallet = 5": forbidden_assignments,
            "obj.db_typeclass_path = 'x'": forbidden_assignments,
        }
        for source, checker in cases.items():
            with self.subTest(source=source):
                self.assertTrue(checker(ast.parse(source)))
        self.assertTrue(forbidden_imports(ast.parse("from world.narrative.dialogue import build_dialogue_context")))
        self.assertEqual(
            missing_helper_imports(ast.parse("def f():\n    return tree({})"), {"tree"}),
            ["tree"],
        )

    def test_the_contract_accepts_the_permitted_read_only_idioms(self):
        permitted = (
            "from web.gm.readers._sections import ledger, row\n"
            "class ReaderError(Exception):\n"
            "    def __init__(self, code):\n"
            "        super().__init__(code)\n"
            "        self.code = code\n"
            "        self.message = code\n"
            "def build(entity):\n"
            "    stored = entity.attributes.get('wallet', default=None)\n"
            "    labels = {}\n"
            "    labels['x'] = 1\n"
            "    return ledger([row('a', stored)]) if stored is not None else ledger([])\n"
        )
        tree = ast.parse(permitted)
        self.assertEqual(forbidden_calls(tree), [])
        self.assertEqual(forbidden_imports(tree), [])
        self.assertEqual(forbidden_assignments(tree), [])
        self.assertEqual(missing_helper_imports(tree, {"ledger", "row", "tree"}), [])
