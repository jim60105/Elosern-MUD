"""Consumer-binding discovery (design D2): AST over the source tree, cached.
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
    if _BINDINGS_CACHE and not refresh:
        return _BINDINGS_CACHE
    if root is None:
        # Package depth: this module sits one level deeper than the
        # former single kit file (world/tests/synthetic_data/).
        root = Path(__file__).resolve().parents[3]
    found: dict[tuple[str, str], set[tuple[str, str]]] = {
        pair: set() for pair in REGISTRY_TARGETS.values()
    }
    for module_name, path in _iter_discovery_sources(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for binding_name, origin in local_import_bindings(tree).items():
            if origin in found:
                found[origin].add((module_name, binding_name))
    _BINDINGS_CACHE.clear()
    for key, pairs in found.items():
        _BINDINGS_CACHE[key] = tuple(sorted(pairs))
    return _BINDINGS_CACHE
