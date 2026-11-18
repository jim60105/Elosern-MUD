"""Synchronous causal publication groups for committed presentation effects.

One deterministic domain operation can commit several presentation side effects:
an ordinary panel push from an on-commit callback, a checkpoint fact from a
movement/combat/skip owner, and the notification fan-out to several watcher
sessions. This module is the narrow, ephemeral publication-context helper that
lets those effects share one *causal group* without holding any session-wide
publication token across a pending ``Deferred``:

- :func:`publication_group` binds a group for the duration of one synchronous
  callable (or one on-commit callback). The binding lives in a
  :class:`contextvars.ContextVar` and is **closed** in ``finally`` before the
  callable returns, so a returned ``Deferred`` never carries a live group.
- :func:`current_publication_group` reports the binding only while it is open.
  A copied asynchronous context (Twisted's ``@inlineCallbacks`` copies the
  context at generator start) keeps the *object* but not an open binding: a
  binding closed by its synchronous owner can never be revived by a resumed
  generator, so resumption never inherits an earlier, already-published group.
- :func:`on_publication_commit` registers a callback on Django's
  ``transaction.on_commit`` while capturing the group that was active at
  registration time; the callback rebinds exactly that group for its own
  synchronous execution. A rolled-back transaction runs nothing.
- :func:`defer_publication_callbacks` collects those callbacks for one outer
  scope and registers their drain only when the scope exits normally, so a
  mutation that must not run lock-taking callbacks beneath its own
  serialization can commit first, release, and only then publish. A nested
  scope joins the outer collector; an exception discards everything.
- :func:`emit_alignment_fact` delivers a committed checkpoint fact to every
  registered observer. Observers are the presentation layer's fan-out; M/S own
  the actual fact producers.

A nested :func:`publication_group` reuses the active group, so a callback
registered inside another callback keeps the same causal identity. Nothing here
is persisted, serialized, or written to the wire; group identity is an
ephemeral 32-hex value that disappears with the process.

This is not a game-state writer and not a general event bus: it only carries
which committed operation a presentation effect belongs to.
"""

import contextvars
import functools
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Literal

from world.observability import log_warn

__all__ = [
    "ALIGNMENT_CAUSES",
    "AlignmentIdentity",
    "PresentationAlignmentFact",
    "PublicationGroup",
    "clear_alignment_observers",
    "current_publication_group",
    "defer_publication_callbacks",
    "emit_alignment_fact",
    "new_publication_group",
    "on_publication_commit",
    "publication_group",
    "register_alignment_observer",
]

#: The complete set of alignment causes a checkpoint fact may name.
ALIGNMENT_CAUSES = frozenset(
    {"movement_boundary", "combat_terminal", "skip_completed"}
)

#: Length of the hex identity every group carries.
_GROUP_ID_HEX_CHARS = 32


def _is_group_id(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _GROUP_ID_HEX_CHARS:
        return False
    try:
        int(value, 16)
    except ValueError:  # observability: ignore R2: an unparseable identifier is the rejected value, not a swallowed failure
        return False
    return True


@dataclass(frozen=True)
class PublicationGroup:
    """The ephemeral identity of one causal publication group."""

    id: str

    def __post_init__(self) -> None:
        if not _is_group_id(self.id):
            raise ValueError("a publication group id must be 32 hexadecimal characters")


class _Binding:
    """One open synchronous binding of a group, invalidated on scope exit."""

    __slots__ = ("group", "closed")

    def __init__(self, group: PublicationGroup) -> None:
        self.group = group
        self.closed = False


_active: contextvars.ContextVar[_Binding | None] = contextvars.ContextVar(
    "elosern_publication_group", default=None
)


class DeferredPublicationCallbacks:
    """The collector one outermost :func:`defer_publication_callbacks` scope owns.

    Each entered scope owns one FRAME. A frame keeps registration order and
    holds the already group-bound wrappers :func:`on_publication_commit`
    builds. A nested scope that fails drops only its own frame, so it can never
    discard callbacks an enclosing scope collected; the outermost scope's
    ``discard`` clears the frame it owns.
    """

    __slots__ = ("frames",)

    def __init__(self) -> None:
        self.frames: list[list[Callable[[], None]]] = [[]]

    def enter(self) -> list[Callable[[], None]]:
        frame: list[Callable[[], None]] = []
        self.frames.append(frame)
        return frame

    def leave(self, frame: list[Callable[[], None]]) -> None:
        try:
            self.frames.remove(frame)
        except ValueError:  # observability: ignore R2: an already-dropped frame is a no-op
            pass

    def add(self, callback: Callable[[], None]) -> None:
        self.frames[-1].append(callback)

    def discard(self) -> None:
        """Drop the CURRENT scope's frame (the outermost one at its own level)."""
        self.frames[-1].clear()

    def discard_all(self) -> None:
        for frame in self.frames:
            frame.clear()

    def pop_next(self) -> Callable[[], None] | None:
        for frame in list(self.frames):
            if frame:
                return frame.pop(0)
        return None


_active_deferral: contextvars.ContextVar[DeferredPublicationCallbacks | None] = (
    contextvars.ContextVar("elosern_deferred_publication_callbacks", default=None)
)


def _drain_deferred_callbacks(
    collector: DeferredPublicationCallbacks,
    delivered: list[Callable[[], None]] | None = None,
) -> None:
    """Run every collected callback once, in registration order.

    The collector stays active for the whole drain so a callback that registers
    another publication callback joins this same drain instead of escaping to a
    later transaction boundary. Every callback runs even when one raises
    (Django's own ``run_on_commit`` contract); the first failure is re-raised
    after the rest are delivered. The drain runs OUTSIDE the mutation's
    transaction and locks, so a publication failure can never roll back or
    reinterpret committed state.
    """
    token = _active_deferral.set(collector)
    first_error: BaseException | None = None
    try:
        while (callback := collector.pop_next()) is not None:
            if delivered is not None:
                delivered.append(callback)
            try:
                callback()
            except BaseException as error:  # observability: ignore R2: the first failure is re-raised after the remaining callbacks run (Django's run_on_commit contract)
                if first_error is None:
                    first_error = error
    finally:
        _active_deferral.reset(token)
    if first_error is not None:
        raise first_error


@contextmanager
def defer_publication_callbacks() -> Iterator[DeferredPublicationCallbacks]:
    """Collect publication callbacks and drain them after this scope exits.

    Registered callbacks are eligible only on a real successful commit: the
    drain is registered with Django's ``transaction.on_commit`` at the OUTER
    scope's exit, so an outer rollback runs none, and a successful inner
    savepoint does not qualify before the outer transaction commits. Nesting
    reuses the outer collector and adds one frame; a nested failure drops only
    its own frame. A body exception outside any enclosing scope discards
    everything. A caller that catches an inner rollback it owns must call
    ``discard()`` for its own frame: the collector is not a transaction hook.
    """
    outer = _active_deferral.get()
    if outer is not None:
        frame = outer.enter()
        try:
            yield outer
        except BaseException:
            outer.leave(frame)
            raise
        return
    collector = DeferredPublicationCallbacks()
    token = _active_deferral.set(collector)
    try:
        yield collector
    except BaseException:
        _active_deferral.reset(token)
        collector.discard_all()
        raise
    _active_deferral.reset(token)
    from django.db import transaction

    transaction.on_commit(_DeferredDrain(collector))


class _DeferredDrain:
    """The one ``on_commit`` registration of an outermost deferral scope.

    Calling it drains the collector. ``delivered`` is a snapshot (taken when
    the drain finishes) of the callbacks it ran, in order: a read-only
    introspection aid so a caller that captured on-commit callbacks can still
    classify the publication work this drain delivered. It never re-runs them.
    """

    __slots__ = ("_collector", "delivered")

    def __init__(self, collector: DeferredPublicationCallbacks) -> None:
        self._collector = collector
        self.delivered: tuple[Callable[[], None], ...] = ()

    def __call__(self) -> None:
        delivered: list[Callable[[], None]] = []
        try:
            _drain_deferred_callbacks(self._collector, delivered)
        finally:
            self.delivered = tuple(delivered)


def new_publication_group() -> PublicationGroup:
    """Return a fresh, unique, ephemeral publication group."""
    return PublicationGroup(secrets.token_hex(_GROUP_ID_HEX_CHARS // 2))


def current_publication_group() -> PublicationGroup | None:
    """The group bound to this synchronous call, or ``None`` when none is live.

    A binding whose synchronous scope already exited is reported as absent even
    when a copied asynchronous context still references it.
    """
    binding = _active.get()
    if binding is None or binding.closed:
        return None
    return binding.group


@contextmanager
def publication_group(group: PublicationGroup | None = None) -> Iterator[PublicationGroup]:
    """Bind ``group`` (or a new one) for one synchronous scope.

    A nested scope reuses the active group: every effect of one committed
    operation, including nested on-commit callbacks, shares one identity. The
    binding is closed and reset in ``finally``, so nothing observes it after the
    scope returns and a resumed asynchronous continuation cannot revive it. When
    the ambient binding is already closed (a copied asynchronous context), a
    fresh binding is opened instead of reviving it.
    """
    active = current_publication_group()
    if active is not None:
        yield active
        return
    binding = _Binding(group if group is not None else new_publication_group())
    token = _active.set(binding)
    try:
        yield binding.group
    finally:
        binding.closed = True
        _active.reset(token)


@contextmanager
def _exact_publication_group(group: PublicationGroup) -> Iterator[PublicationGroup]:
    """Bind exactly ``group`` for one synchronous scope, overriding any ambient one.

    Only :func:`on_publication_commit` uses this: a callback captured under group
    A must run under A even when it is invoked while group B is bound (an outer
    transaction committing inside another committed operation). Domain callers
    keep the nested-reuse rule of :func:`publication_group`.
    """
    binding = _Binding(group)
    token = _active.set(binding)
    try:
        yield group
    finally:
        binding.closed = True
        _active.reset(token)


def on_publication_commit(
    callback: Callable[[], None], *, using: str | None = None
) -> None:
    """Register ``callback`` to run once the surrounding transaction commits.

    The group active at registration time is captured and rebound only for the
    callback's own synchronous execution, so its presentation work joins the
    causal group of the transaction it belongs to. Django owns the commit and
    rollback behaviour: a rolled-back transaction runs nothing, and an exception
    raised by the callback keeps propagating exactly as before.

    Inside an active :func:`defer_publication_callbacks` scope the wrapped
    callback joins that scope's collector instead: it is still eligible only on
    a real successful commit (the collector itself is drained from a single
    ``transaction.on_commit`` registration), but it runs after the scope has
    released its own locks and serialization.
    """
    from django.db import transaction

    captured = current_publication_group() or new_publication_group()

    # ``functools.wraps`` keeps the wrapped callback's identity visible
    # (``__name__``, ``__doc__``, ``__wrapped__``), so diagnostics and the
    # tests that classify captured on-commit callbacks still see the owner
    # rather than this binder.
    @functools.wraps(callback)
    def _committed() -> None:
        with _exact_publication_group(captured):
            callback()

    collector = _active_deferral.get()
    if collector is not None:
        collector.add(_committed)
        return
    transaction.on_commit(_committed, using=using)


@dataclass(frozen=True)
class AlignmentIdentity:
    """The read-only alignment identity of one actor position.

    ``layer`` names the alignment layer (for example ``"wilderness"`` or
    ``"area"``); ``area_key`` is that layer's stable area key; ``instance_key``
    names a shared instance as ``(slot, token)`` and is ``None`` outside one.
    M owns the production reader that builds these values.
    """

    layer: str
    area_key: str
    instance_key: tuple[int, str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.layer, str) or not self.layer:
            raise ValueError("an alignment identity needs a layer")
        if not isinstance(self.area_key, str) or not self.area_key:
            raise ValueError("an alignment identity needs an area key")
        if self.instance_key is not None:
            key = self.instance_key
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not isinstance(key[0], int)
                or isinstance(key[0], bool)
                or not isinstance(key[1], str)
                or not key[1]
            ):
                raise ValueError(
                    "an alignment instance key is (slot, token) with a non-empty token"
                )


@dataclass(frozen=True)
class PresentationAlignmentFact:
    """One committed checkpoint fact for a presentation group.

    ``group_id`` is the causal group the fact belongs to; ``actor_id`` is the
    committed actor's primary key; ``cause`` names the checkpoint that produced
    it. ``source``/``destination`` are supplied by the producing owner (M for
    movement boundaries, S for terminal combat and completed skips).
    """

    group_id: str
    actor_id: int
    cause: Literal["movement_boundary", "combat_terminal", "skip_completed"]
    source: AlignmentIdentity | None = None
    destination: AlignmentIdentity | None = None

    def __post_init__(self) -> None:
        if not _is_group_id(self.group_id):
            raise ValueError("a fact group id must be 32 hexadecimal characters")
        if not isinstance(self.actor_id, int) or isinstance(self.actor_id, bool):
            raise ValueError("a fact actor id must be an integer primary key")
        if self.cause not in ALIGNMENT_CAUSES:
            raise ValueError(f"unknown alignment cause {self.cause!r}")
        for name in ("source", "destination"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, AlignmentIdentity):
                raise ValueError(f"{name} must be an AlignmentIdentity or None")


_observers: list[Callable[[PresentationAlignmentFact], None]] = []


def register_alignment_observer(
    callback: Callable[[PresentationAlignmentFact], None],
) -> None:
    """Register one committed-fact observer (idempotent per callback)."""
    if not callable(callback):
        raise TypeError("an alignment observer must be callable")
    if callback not in _observers:
        _observers.append(callback)


def clear_alignment_observers() -> None:
    """Forget every registered observer (test seam)."""
    _observers.clear()


def emit_alignment_fact(fact: PresentationAlignmentFact) -> None:
    """Deliver ``fact`` to every registered observer, synchronously.

    One observer's failure is reported and isolated: the remaining observers
    still receive the fact, and the fact producer is never changed by
    presentation work. An unregistered observer list cannot fake delivery, and a
    failing observer is a reported diagnostic rather than a silent success.
    """
    if not isinstance(fact, PresentationAlignmentFact):
        raise TypeError("emit_alignment_fact requires a PresentationAlignmentFact")
    for observer in tuple(_observers):
        try:
            observer(fact)
        except Exception as error:  # observability: R2 reported below; delivery to the remaining observers must continue
            log_warn(
                "alignment_fact_delivery_failed",
                context={
                    "surface": "presentation",
                    "cause": fact.cause,
                    "actor": str(fact.actor_id),
                },
                exc=error,
            )
