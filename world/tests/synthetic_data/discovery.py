"""Consumer-binding discovery (design D2): AST over the source tree, cached.

Two tables come out of one walk over the source tree:

- consumer bindings: modules that MODULE-level name-imported a target
  attribute (``from x import Y``), which the scope machinery patches;
- import-time derivations: the subset of those modules that also reference
  the bound name from a module-level statement, i.e. that record catalog
  state in module scope when the module is first imported.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

from world.tests.synthetic_data.targets import REGISTRY_TARGETS

# ---------------------------------------------------------------------------
# Consumer-binding discovery (design D2): AST, cached, never hand-maintained.
# ---------------------------------------------------------------------------

_DISCOVERY_ROOTS = ("commands", "server", "typeclasses", "web", "world")
_DISCOVERY_EXCLUDES = ("/node_modules/", "/dist/", "/__pycache__/", "/.worktrees/")
_BINDINGS_CACHE: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {}
# (owner module, attribute) -> modules that derive state from that binding at
# import time. Importing one of these while a synthetic catalog is installed
# would freeze a synthetic projection into module scope for the rest of the
# process, so the scope machinery resolves them BEFORE it patches anything.
_DERIVATIONS_CACHE: dict[tuple[str, str], tuple[str, ...]] = {}


def import_time_names(nodes: Iterator[ast.stmt]) -> set[str]:
    """Names loaded by statements that execute at import.

    Function, async-function, and lambda bodies run on call, so a reference
    inside one is not import-time state; everything else nested in a module
    body — class bodies, comprehensions, decorators, default expressions —
    executes when the module is imported.
    """
    found: set[str] = set()
    stack = list(nodes)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            found.add(node.id)
        stack.extend(ast.iter_child_nodes(node))
    return found


def _iter_discovery_sources(root: Path) -> Iterator[tuple[str, Path]]:
    """Yield (dotted module name, path) for every discoverable source file."""
    for package in _DISCOVERY_ROOTS:
        base = root / package
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            text = "/" + "/".join(path.relative_to(root).parts)
            if any(marker in text for marker in _DISCOVERY_EXCLUDES):
                continue
            parts = path.relative_to(root).with_suffix("").parts
            if parts[-1] == "__init__":
                parts = parts[:-1]
            yield ".".join(parts), path


def local_import_bindings(tree: ast.Module) -> dict[str, tuple[str, str]]:
    """Map each local binding of ``tree`` to its (origin module, attribute).

    Covers MODULE-level ``from m import a [as b]`` only (local name ``b`` or
    ``a``): function-local imports re-resolve at call time, so patching the
    owner module already redirects them and a per-binding swap would target
    a name the module never carries.
    """
    resolved: dict[str, tuple[str, str]] = {}
    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                resolved[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    resolved[alias.asname] = (alias.name, "")
        elif isinstance(node, (ast.Try, ast.If)):
            # Conditional/guarded top-level imports still bind at module level.
            stack.extend(node.body)
            stack.extend(node.orelse)
            for handler in getattr(node, "handlers", ()):
                stack.extend(handler.body)
    return resolved


def discover_consumer_bindings(
    root: Path | None = None, *, refresh: bool = False
) -> dict[tuple[str, str], tuple[tuple[str, str], ...]]:
    """Map each (module, attribute) target to sorted consumer (module, binding) pairs.

    Pure AST over the source tree — every ``from <module> import <attr>`` with
    the LOCAL binding name (alias included), across production and test
    sources — cached after the first walk. Imports nothing; never hand-maintained.
    """
    _walk(root, refresh=refresh)
    return _BINDINGS_CACHE


def discover_import_time_derivations(
    root: Path | None = None, *, refresh: bool = False
) -> dict[tuple[str, str], tuple[str, ...]]:
    """Map each (module, attribute) target to modules deriving from it at import.

    Same walk and cache as :func:`discover_consumer_bindings`; a module is a
    derivation only when it both binds the target at module level and
    references that binding from an import-time statement.
    """
    _walk(root, refresh=refresh)
    return _DERIVATIONS_CACHE


def _walk(root: Path | None, *, refresh: bool) -> None:
    """Fill both caches from one AST pass over the discoverable sources."""
    if _BINDINGS_CACHE and not refresh:
        return
    if root is None:
        # Package depth: this module sits one level deeper than the
        # former single kit file (world/tests/synthetic_data/).
        root = Path(__file__).resolve().parents[3]
    found: dict[tuple[str, str], set[tuple[str, str]]] = {
        pair: set() for pair in REGISTRY_TARGETS.values()
    }
    derived: dict[tuple[str, str], set[str]] = {pair: set() for pair in found}
    for module_name, path in _iter_discovery_sources(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        loaded = import_time_names(
            node
            for node in tree.body
            if not isinstance(node, (ast.Import, ast.ImportFrom))
        )
        for binding_name, origin in local_import_bindings(tree).items():
            if origin not in found:
                continue
            found[origin].add((module_name, binding_name))
            if binding_name in loaded:
                derived[origin].add(module_name)
    _BINDINGS_CACHE.clear()
    for key, pairs in found.items():
        _BINDINGS_CACHE[key] = tuple(sorted(pairs))
    _DERIVATIONS_CACHE.clear()
    for key, module_names in derived.items():
        _DERIVATIONS_CACHE[key] = tuple(sorted(module_names))
