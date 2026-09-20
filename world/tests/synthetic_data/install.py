"""Process-scoped install (design D2b): idempotent process-wide synthetic swap.
"""

from __future__ import annotations

import importlib
from types import MappingProxyType

from world.tests.synthetic_data.targets import REGISTRY_TARGETS, _CONTENT
from world.tests.synthetic_data.patching import (
    _consumer_bindings,
    _dependency_order,
    _imported_modules,
    _late_binder_sweep,
)

# ---------------------------------------------------------------------------
# Process-scoped install (design D2b).
# ---------------------------------------------------------------------------
_INSTALL_STATE = {"installed": False}
_INSTALLED_ATTRS: list[tuple[object, str, object]] = []
_INSTALL_REPLACEMENTS: dict[str, tuple[object, object]] = {}
_INSTALLED_DICTS: list[tuple[dict, dict]] = []


def install_synthetic_catalogs(
    logicals: tuple[str, ...] | None = None,
) -> bool:
    """Swap the shipped catalogs to synthetic content process-wide.

    Idempotent: the second call is a no-op returning ``False``. Meant for the
    separate managed-browser seed/server processes whose startup world
    bootstrap mirrors catalogs into a private database — in-process patching
    from the Playwright process cannot reach them. Owner-module attributes
    are swapped (frozen targets) or their shipped content replaced in place
    (mutable targets); already-imported consumer bindings of frozen targets
    are swapped through the discovered binding table, and consumers imported
    LATER pick the installed values up naturally. Returns ``True`` when this
    call installed.
    """
    if _INSTALL_STATE["installed"]:
        return False
    names = tuple(logicals) if logicals else tuple(
        name for name in REGISTRY_TARGETS if name != "lore_sync"
    ) + ("lore_sync",)
    _INSTALL_REPLACEMENTS.clear()
    for logical in _dependency_order(names):
        module_name, attribute = REGISTRY_TARGETS[logical]
        module = importlib.import_module(module_name)
        shipped = getattr(module, attribute)
        content = dict(_CONTENT[logical]())
        if not isinstance(shipped, MappingProxyType):
            _INSTALLED_DICTS.append((shipped, dict(shipped)))
            shipped.clear()
            shipped.update(content)
        else:
            replacement = MappingProxyType(content)
            _INSTALL_REPLACEMENTS[logical] = (replacement, shipped)
            _INSTALLED_ATTRS.append((module, attribute, getattr(module, attribute)))
            setattr(module, attribute, replacement)
            for consumer_module, binding_name in _consumer_bindings(logical):
                if consumer_module in _imported_modules():
                    consumer = importlib.import_module(consumer_module)
                    _INSTALLED_ATTRS.append(
                        (consumer, binding_name, getattr(consumer, binding_name, None))
                    )
                    setattr(consumer, binding_name, replacement)
    _INSTALL_STATE["installed"] = True
    return True


_INSTALLED_DICTS: list[tuple[dict, dict]] = []


def uninstall_synthetic_catalogs() -> bool:
    """Restore the shipped state a previous :func:`install_synthetic_catalogs`
    changed: frozen attribute bindings are rebound and mutable catalogs are
    refilled with their pre-install content. Returns ``True`` when restored."""
    if not _INSTALL_STATE["installed"]:
        return False
    for holder, attribute, original in reversed(_INSTALLED_ATTRS):
        setattr(holder, attribute, original)
    _INSTALLED_ATTRS.clear()
    # Modules imported AFTER install bound the installed replacement at
    # their own import; sweep every discovered binding still pointing at it
    # back to the pre-install shipped object.
    for logical, (replacement, shipped) in _INSTALL_REPLACEMENTS.items():
        _late_binder_sweep(logical, replacement, shipped)
    _INSTALL_REPLACEMENTS.clear()
    for target, original in reversed(_INSTALLED_DICTS):
        target.clear()
        target.update(original)
    _INSTALLED_DICTS.clear()
    _INSTALL_STATE["installed"] = False
    return True

