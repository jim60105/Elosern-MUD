"""Scoped patching (design D2): synthetic_registries and the target application machinery.
"""

from __future__ import annotations

import functools
import importlib
import unittest.mock
from collections.abc import Callable, Iterator, Mapping
from contextlib import ContextDecorator, ExitStack
from types import MappingProxyType

from world.tests.synthetic_data.targets import REGISTRY_TARGETS, _CONTENT, _TARGET_DEPENDENCIES
from world.tests.synthetic_data.discovery import discover_consumer_bindings

# ---------------------------------------------------------------------------
# Scoped patching (design D2).
# ---------------------------------------------------------------------------
class synthetic_registries(ContextDecorator):
    """Patch selected shipped catalogs with the synthetic catalogs.

    Usable as a context manager, a function/method decorator, or a class
    decorator (each ``test*`` method then gets a fresh, independent scope).
    ``extra={logical: {key: entry}}`` merges factory-built local entries into
    this scope's replacement only; frozen targets keep their frozen shape.
    ``include_sync_capture=True`` also patches the lore-sync import-time
    capture for scopes that invoke ``sync_all()`` (the capture category set
    covers the same registries; pass the logical targets a scope reads plus
    this flag when it writes to the DB mirror).
    """

    def __init__(
        self,
        *logicals: str,
        extra: Mapping[str, Mapping[str, object]] | None = None,
        include_sync_capture: bool = False,
    ) -> None:
        names = list(dict.fromkeys(logicals))
        for logical in names:
            if logical not in REGISTRY_TARGETS:
                raise KeyError(f"unknown synthetic registry target {logical!r}")
        # Dependency closure: rows whose construction resolves foreign keys
        # through other catalogs require those targets in the same scope.
        for logical in tuple(names):
            for dependency in _TARGET_DEPENDENCIES.get(logical, ()):
                if dependency not in names:
                    names.append(dependency)
        # Usable-item closure: settlement resolves an item's effects by item
        # key through the live profile map, so every scoped item registry
        # carries its rulebook-side profiles automatically.
        if "items" in names and "item_effect_profiles" not in names:
            names.append("item_effect_profiles")
        if include_sync_capture:
            if "lore_sync" not in names:
                names.append("lore_sync")
            # sync_all reads placements through the live module binding; the
            # capture additionally resolves wilderness/entry dependents.
            for dependency in _TARGET_DEPENDENCIES["lore_sync"]:
                if dependency not in names:
                    names.append(dependency)
        self._logicals = tuple(names)
        self._extra = dict(extra or {})
        for logical in self._extra:
            if logical not in REGISTRY_TARGETS:
                raise KeyError(f"unknown synthetic registry target {logical!r}")

    # -- scope lifecycle -----------------------------------------------------

    def __enter__(self) -> "synthetic_registries":
        if getattr(self, "_open", False):
            raise RuntimeError(
                "this synthetic_registries scope is already open: re-entering "
                "the same object replaces the live patch stack with a fresh "
                "one, orphaning the shipped-catalog restore callbacks and "
                "leaking the synthetic registries into later tests; build a "
                "new scope instead"
            )
        stack = ExitStack()
        self._open = True
        try:
            for logical in _dependency_order(self._logicals):
                _apply_target(stack, logical, self._extra)
        except Exception:
            # A failed __enter__ never reaches __exit__; unwind the partial
            # stack here so the scope leaves no patches behind.
            stack.close()
            self._open = False
            raise
        self._stack = stack
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        stack = self.__dict__.pop("_stack", None)
        try:
            if stack is not None:
                stack.__exit__(exc_type, exc, tb)
        finally:
            self._open = False
        return False

    def _recreate_cm(self) -> "synthetic_registries":
        clone = object.__new__(synthetic_registries)
        clone._logicals = self._logicals
        clone._extra = self._extra
        return clone

    # -- decorator dispatch ---------------------------------------------------

    def __call__(self, target):
        if isinstance(target, type):
            return self._decorate_class(target)
        return super().__call__(target)

    def _decorate_class(self, cls):
        # The unittest loader collects test* through dir() — inherited
        # methods included — so wrap every collected test (resolved through
        # the MRO) and install the wrapper on THIS class. Wrapping vars(cls)
        # only would silently run inherited tests against shipped catalogs.
        for name in dir(cls):
            if not name.startswith("test"):
                continue
            try:
                method = getattr(cls, name)
            except Exception:
                continue  # observability: ignore R1: exotic attributes stay untouched
            if callable(method):
                setattr(cls, name, self._wrap_method(method))
        return cls

    def _wrap_method(self, method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            with self._recreate_cm():
                return method(*args, **kwargs)

        return wrapper


def _apply_target(
    stack: ExitStack, logical: str, extra: Mapping[str, Mapping[str, object]]
) -> None:
    """Patch one logical target (owner attribute + discovered consumers) in ``stack``."""
    module_name, attribute = REGISTRY_TARGETS[logical]
    module = importlib.import_module(module_name)
    shipped = getattr(module, attribute)
    content = dict(_CONTENT[logical]())
    content.update(extra.get(logical, {}))
    if not isinstance(shipped, MappingProxyType):
        if not isinstance(shipped, dict) or not isinstance(content, dict):
            raise TypeError(
                f"registry target {logical!r} has an unexpected shipped shape"
            )
        # In-place: every consumer binding IS this dict object.
        stack.enter_context(unittest.mock.patch.dict(shipped, content, clear=True))
        return
    # Frozen swap: resolve every consumer module BEFORE patching so each
    # patch.object captures the shipped object as its restore value. A
    # consumer imported after the owner swap would bind the replacement at
    # its own import and capture THAT as "original", leaving it stale after
    # the scope. Consumers that cannot import (their rulebook validation
    # needs runtime state) bind the synthetic replacement on the late
    # import — the documented lazy-import limitation of design D2.
    resolved_consumers: list[tuple[object, str]] = []
    for consumer_module, binding_name in _consumer_bindings(logical):
        try:
            resolved_consumers.append(
                (importlib.import_module(consumer_module), binding_name)
            )
        except Exception:
            continue  # observability: ignore R2: late-binding consumers stay owner-patched
    replacement = MappingProxyType(content)
    for consumer, binding_name in resolved_consumers:
        stack.enter_context(
            unittest.mock.patch.object(consumer, binding_name, replacement)
        )
    stack.enter_context(unittest.mock.patch.object(module, attribute, replacement))
    # patch.object only restores bindings that existed at entry. Sweep at
    # teardown: a consumer imported DURING the scope bound the replacement at
    # its own import, so rebind every still-synthetic discovered binding to
    # the pre-scope shipped object — the scope leaks nothing.
    stack.callback(_late_binder_sweep, logical, replacement, shipped)


def _late_binder_sweep(logical: str, replacement: object, original: object) -> None:
    """Rebind discovered consumer bindings that still point at a stale replacement."""
    for consumer_module, binding_name in _consumer_bindings(logical):
        module = _imported_modules().get(consumer_module)
        if module is None:
            continue
        if getattr(module, binding_name, None) is replacement:
            setattr(module, binding_name, original)


def _consumer_bindings(logical: str) -> tuple[tuple[str, str], ...]:
    owner = REGISTRY_TARGETS[logical]
    return discover_consumer_bindings().get(owner, ())


def _dependency_order(logicals: tuple[str, ...]) -> tuple[str, ...]:
    """Topologically order targets so dependency content is patched first."""
    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(logical: str) -> None:
        if logical in ordered:
            return
        if logical in visiting:
            raise ValueError(f"cyclic synthetic target dependency at {logical!r}")
        visiting.add(logical)
        for dependency in _TARGET_DEPENDENCIES.get(logical, ()):
            visit(dependency)
        visiting.discard(logical)
        ordered.append(logical)

    for logical in logicals:
        visit(logical)
    return tuple(ordered)

def _imported_modules() -> Mapping[str, object]:
    import sys

    return sys.modules
