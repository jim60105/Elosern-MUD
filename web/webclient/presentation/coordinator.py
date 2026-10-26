"""Session-scoped publication owner for the version-1 OOB protocol.

The coordinator owns the ephemeral presentation sequence for one live
WebSocket transport and active puppet: a cryptographically random epoch, a
monotonic per-epoch issued revision, the last successfully published baseline,
full snapshots, delta computation, calendar serialization, and puppet-change
reset. None of this state is ever persisted; it lives only on ``session.ndb``
and disappears with the transport.

It is also the **one** publication owner. Every publisher (graphical action
completion, stale/internal recovery, explicit sync, text-command settlement,
art completion, the panel pushes, and the on-demand map request) hands the
coordinator an immutable *intent* and observes one :class:`Deferred` that
resolves with a :class:`~web.webclient.presentation.publication.PublicationReceipt`
once the complete batch (every presentation frame and the matching action
result) has been sent. A publication that changes nothing consumes no revision
and sends no presentation frame.

Every queued intent belongs to one ephemeral *causal publication group*
(``world.rules.presentation_events``). Intents that share a committed
operation's group id merge into **one** pending group entry, so an ordinary
panel push and a checkpoint fact from the same commit coalesce into one fresh
publication for every watcher, whatever order the commit callbacks ran in.
Group-less work (an explicit sync, a text-command refresh, an async generation
completion) stays its own independent entry and never joins an ambient command
group.

Only one publication batch runs at a time. ``enqueue_publication`` appends the
intent and runs the drain, which is a private synchronous critical section:
nothing awaits and no other publication can interleave between an action's
presentation frames and its result. It completes before the enqueueing callback
returns, so a sequence-retiring effect the adapter scheduled for a later turn
always runs after its result. A reentrant publish (a sync, push or completion
requested from inside a send or a receipt callback) joins the same queue and is
drained immediately after the current batch, in order.

Grouped work drains at the reactor's next turn instead: every on-commit
callback of the synchronous owning transaction runs before the reactor returns,
so the group entry is complete before it is planned and sent. A process without
a running reactor (the test runner, a one-off command) has no live transport to
observe frames, so the injected scheduler publishes at the enqueue boundary
there. A completing action's result-only answer is flushed immediately (its
adapter may already have scheduled a sequence retirement for the next turn),
which is the narrow exception B already carved out for those actions.

The coordinator never writes canonical game state and never reaches for a
mutation helper: calendar data comes only from the read-only
``world.rules.clock.read_world_clock`` accessor.
"""

import secrets
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from twisted.internet.defer import Deferred, succeed
from twisted.python.failure import Failure

from world.observability import log_debug, log_error, log_info, log_warn
from world.rules.presentation_events import (
    current_publication_group,
    new_publication_group,
)

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    PROTOCOL_VERSION,
    UI_ACTION_RESULT,
    JSONSafetyError,
    ProtocolValidationError,
    check_envelope,
    json_byte_size,
    new_presentation_epoch,
    validate_ui_action_result,
    validate_ui_snapshot,
    validate_ui_update,
)
from web.webclient.presentation.map_panels import (
    WORLD_MAP_PANEL,
    carries_intact_world_map,
    check_world_map_envelope,
)
from web.webclient.presentation.publication import (
    PublicationCompletion,
    PublicationReceipt,
    copy_json_value,
    json_value_equal,
)
from web.webclient.presentation.registry import PresentationRegistry

# The approved default layout version shipped by this delivery unit.
LAYOUT_VERSION = 1

# The server message name carrying a full snapshot.
SNAPSHOT_MESSAGE = "ui_snapshot"
UPDATE_MESSAGE = "ui_update"

# Panel whose payload the recomputed mode is coupled to: every publication
# whose recomputed mode is dialogue renders it as a candidate, so the committed
# mode and the committed dialogue panel can never diverge on the wire.
DIALOGUE_PANEL = "dialogue"

# Bound on queued publication groups and on the waiting callers of one live
# sequence (64 each, result-only answers exempt). Reaching it is a defect (a
# publisher loop), never ordinary traffic: the overflow is reported and the
# baseline is invalidated so the next publication announces a fresh snapshot
# instead of a delta from a stale base.
MAX_PENDING_PUBLICATIONS = 64

_MISSING = object()


class ClockUnavailable(RuntimeError):
    """The world-clock singleton is absent; presentation cannot continue."""


class PresentationQueueFull(RuntimeError):
    """Too many publication intents are queued for one live sequence."""


class ResultDeliveryError(RuntimeError):
    """The action result failed to send after its presentation had published."""


def read_world_clock_calendar() -> Any:
    """Return the calendar of the existing world clock without creating one.

    Delegates to ``world.rules.clock.read_world_clock``, which never creates a
    Script. Returns ``None`` when the singleton is absent so the coordinator
    can fail safely with ``presentation_unavailable``.
    """
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return None if clock is None else clock.calendar


@dataclass
class _Baseline:
    """The last successfully published per-session baseline.

    ``panels`` holds only the eager panel values (owned plain-JSON trees); an
    on-demand map body is never stored here. ``valid`` is cleared when a send
    fails after a frame escaped, so no delta is ever computed from a state the
    client cannot hold.
    """

    epoch: str
    revision: int
    panels: dict[str, Any]
    mode: str
    layout_version: int
    server_time: dict[str, Any]
    valid: bool = True


@dataclass(frozen=True)
class _Intent:
    """One immutable, validated publication request.

    ``group_id`` is the causal group the request belongs to; every request with
    the same id merges into one :class:`_PendingGroup`. ``declared`` names an
    explicit eager scope (empty when the request declares none) and
    ``unknown_scope`` marks "compare every eager panel"; a candidate-only push
    declares neither and compares only its own candidates.
    """

    context_factory: Callable[[], PresentationContext]
    candidates: Mapping[str, Any] | None
    declared: frozenset[str]
    unknown_scope: bool
    removed_panels: tuple[str, ...]
    force_snapshot: bool
    result_only: bool
    group_id: str
    standalone: bool
    epoch: str
    expected_epoch: str | None
    completion: PublicationCompletion | None
    deferred: Deferred


@dataclass(eq=False)
class _PendingGroup:
    """One queued causal group: merged declarations and their waiters.

    Every intent enqueued for the same ephemeral group id merges here, so one
    publication answers all of them: the union of candidate names and explicit
    removals, "unknown scope" if any request declared it, checkpoint promotion
    if any request forced a snapshot, and one receipt for every waiting
    ``Deferred``. ``grouped`` records whether the group was captured from a
    committed operation (deferred drain) or is a standalone request (drained at
    the enqueue boundary).
    """

    group_id: str
    context_factory: Callable[[], PresentationContext]
    candidates: dict[str, Any] | None
    declared: frozenset[str]
    unknown_scope: bool
    removed_panels: tuple[str, ...]
    force_snapshot: bool
    result_only: bool
    grouped: bool
    epoch: str
    expected_epoch: str | None
    completion: PublicationCompletion | None
    waiters: list[Deferred]
    completion_factory: bool

    @classmethod
    def from_intent(cls, intent: "_Intent", *, grouped: bool) -> "_PendingGroup":
        candidates = dict(intent.candidates) if intent.candidates is not None else None
        return cls(
            group_id=intent.group_id,
            context_factory=intent.context_factory,
            candidates=candidates,
            declared=intent.declared,
            unknown_scope=intent.unknown_scope,
            removed_panels=intent.removed_panels,
            force_snapshot=intent.force_snapshot,
            result_only=intent.result_only,
            grouped=grouped,
            epoch=intent.epoch,
            expected_epoch=intent.expected_epoch,
            completion=intent.completion,
            waiters=[intent.deferred],
            completion_factory=intent.completion is not None,
        )

    def merge(self, intent: "_Intent") -> None:
        """Merge one validated request into this entry.

        A removal always wins over a replacement of the same panel: an explicit
        removal is a declaration that the panel is gone, and B rejects a frame
        that both replaces and removes a name, so the merged entry can never
        plan one. A completion's context factory (it carries the action-local
        round record) survives later ordinary pushes; otherwise the newest
        factory wins, and every grouped factory rebuilds current canonical
        state.
        """
        if intent.candidates:
            merged = dict(self.candidates or {})
            merged.update(intent.candidates)
            self.candidates = merged
        if intent.declared:
            self.declared = self.declared | intent.declared
        self.unknown_scope = self.unknown_scope or intent.unknown_scope
        self.force_snapshot = self.force_snapshot or intent.force_snapshot
        self.result_only = self.result_only and intent.result_only
        if intent.completion is not None:
            self.completion = intent.completion
            self.context_factory = intent.context_factory
            self.completion_factory = True
        elif not self.completion_factory:
            self.context_factory = intent.context_factory
        self.removed_panels = _merge_removals(
            self.removed_panels, intent.removed_panels
        )
        if self.removed_panels:
            removed = set(self.removed_panels)
            if self.candidates:
                self.candidates = {
                    name: value
                    for name, value in self.candidates.items()
                    if name not in removed
                } or None
            if self.declared:
                self.declared = frozenset(
                    name for name in self.declared if name not in removed
                )
        if self.expected_epoch is None:
            self.expected_epoch = intent.expected_epoch
        self.waiters.append(intent.deferred)


def _merge_removals(first: tuple[str, ...], second: tuple[str, ...]) -> tuple[str, ...]:
    """Union two ordered removal tuples without repeating a panel name."""
    merged = list(first)
    seen = set(first)
    for name in second:
        if name not in seen:
            seen.add(name)
            merged.append(name)
    return tuple(merged)


def _reactor_scheduler(callback: Callable[[], None]) -> Any:
    """Run ``callback`` after the current reactor turn, or now without a reactor.

    Publication only reaches a live transport while the reactor is running; in
    a process without one (the test runner, a one-off command) no session can
    observe frames, so the enqueue boundary is the deterministic drain point.
    """
    from twisted.internet import reactor

    if not getattr(reactor, "running", False):
        callback()
        return None
    return reactor.callLater(0, callback)


@dataclass(frozen=True)
class _LogicalPublication:
    """One logical publication: consecutive frames sharing one revision."""

    snapshot: bool
    message: str
    revision: int
    frames: tuple[dict[str, Any], ...]
    replacements: Mapping[str, Any]
    removed: tuple[str, ...]
    mode: str
    server_time: Mapping[str, Any]
    map_panel: str | None = None
    parts: int = 0


class PresentationCoordinator:
    """One ephemeral publication sequence bound to a live server session.

    Attributes:
        session: The live Evennia session that owns this sequence.
        registry: The :class:`PresentationRegistry` supplying panel specs.
        calendar_provider: A zero-argument callable returning a calendar
            object with ``year``, ``season_index``, ``season_name``,
            ``day_in_season``, ``hour``, ``minute``, and ``second``, or ``None``
            when the world clock is absent. Injectable for tests.
    """

    def __init__(
        self,
        session: Any,
        registry: PresentationRegistry,
        calendar_provider: Callable[[], Any] = read_world_clock_calendar,
        mode_provider: Callable[[PresentationContext], str] | None = None,
        scheduler: Callable[[Callable[[], None]], Any] | None = None,
    ) -> None:
        self.session = session
        self.registry = registry
        self._calendar_provider = calendar_provider
        self._mode_provider = mode_provider or self.mode_for
        #: Injected reactor-next-turn seam for grouped publications. Tests pass
        #: a queued scheduler to prove coalescing deterministically.
        self._scheduler = scheduler or _reactor_scheduler
        self._epoch = new_presentation_epoch()
        self._revision = 0
        self._baseline: _Baseline | None = None
        # A publication that was dropped or failed after a frame escaped leaves
        # the client's committed state uncertain until a snapshot repairs it.
        self._repair_required = False
        self._pending: deque[_PendingGroup] = deque()
        self._pending_groups: dict[str, _PendingGroup] = {}
        self._drain_scheduled = False
        self._draining = False

    @property
    def epoch(self) -> str:
        return self._epoch

    @property
    def revision(self) -> int:
        """The newest revision issued to this sequence.

        The issued revision can be newer than the last *successful* baseline
        revision after a partial send; deltas always use the baseline revision
        and a fresh snapshot repairs the gap.
        """
        return self._revision

    @property
    def published_revision(self) -> int:
        """The revision the client can hold, or 0 before the first publication."""
        baseline = self._baseline
        if baseline is not None and baseline.valid:
            return baseline.revision
        return self._revision

    @property
    def committed_panels(self) -> dict[str, Any]:
        """Owned copies of the eager panel values the client currently holds.

        Empty before the first publication and after an invalidated baseline.
        The copy keeps the published baseline unreachable, so a caller can
        inspect what this sequence committed without being able to mutate it.
        """
        baseline = self._baseline
        if baseline is None or not baseline.valid:
            return {}
        return copy_json_value(baseline.panels)

    def reset(self) -> None:
        """Start a fresh presentation sequence (reconnect or puppet change)."""
        from web.webclient.presentation.gallery_selection import retire_gallery_selection

        retire_gallery_selection(self.session)
        self._retire_pending()
        self._epoch = new_presentation_epoch()
        self._revision = 0
        self._baseline = None
        self._repair_required = False

    def _retire_pending(self) -> None:
        """Resolve every queued publication with ``None``: its sequence retired.

        Completed group metadata is dropped with the waiters, so no group history
        outlives the pending queue and a retired sequence can never reuse one.
        """
        pending, self._pending = self._pending, deque()
        self._pending_groups = {}
        self._drain_scheduled = False
        for entry in pending:
            self._resolve(entry, None)

    def _invalidate_baseline(self) -> None:
        """Forbid deltas from the current baseline values (they were not held)."""
        self._repair_required = True
        if self._baseline is not None:
            self._baseline.valid = False

    def server_time(self) -> dict[str, Any]:
        """Serialize the current calendar into the exact ``server_time`` shape."""
        calendar = self._calendar_provider()
        if calendar is None:
            raise ClockUnavailable("world-clock singleton is absent")
        return {
            "year": int(calendar.year),
            "season_index": int(calendar.season_index),
            "season_label": str(calendar.season_name),
            "day_in_season": int(calendar.day_in_season),
            "hour": int(calendar.hour),
            "minute": int(calendar.minute),
            "second": int(calendar.second),
        }

    # ------------------------------------------------------------------
    # Public publication API: every entry point ALWAYS returns a Deferred.
    # ------------------------------------------------------------------

    def enqueue_publication(
        self,
        context_factory: Callable[[], PresentationContext],
        *,
        affected_panels: Any = None,
        candidate_panels: Mapping[str, Any] | None = None,
        removed_panels: tuple[str, ...] | list[str] = (),
        force_snapshot: bool = False,
        expected_epoch: str | None = None,
        completion: PublicationCompletion | None = None,
        result_only: bool = False,
        group_id: str | None = None,
        independent: bool = False,
    ) -> Deferred:
        """Queue one publication and return its always-present Deferred.

        ``context_factory`` rebuilds the canonical read context when the intent
        executes; action-local immutable round data may be captured by the
        closure. ``affected_panels`` and ``candidate_panels`` are mutually
        exclusive: an absent, empty or invalid affected declaration means
        unknown scope (every eager panel is re-rendered and only real
        differences are transmitted), while ``candidate_panels`` are
        already-rendered payloads (a push) isolated here. ``removed_panels`` is
        an explicit eager removal set.

        ``force_snapshot`` renders and sends the complete eager snapshot even
        when nothing changed. ``result_only`` sends the associated action result
        with no presentation at all (the pre-existing ``no_presentation`` and
        safe-failure exception). An intent whose sequence retires before it
        executes resolves ``None``.

        ``group_id`` is the internal causal group of the committed operation the
        request belongs to; when it is absent the group bound to this call is
        used, and a request outside any binding becomes its own standalone
        group. Requests sharing a group merge into one publication, so every
        waiting Deferred resolves with the same actual receipt. ``independent``
        marks an explicit entry (a sync or a recovery answer) that must never
        join an ambient command group.
        """
        deferred: Deferred = Deferred()
        try:
            intent = self._build_intent(
                context_factory,
                affected_panels=affected_panels,
                candidate_panels=candidate_panels,
                removed_panels=removed_panels,
                force_snapshot=force_snapshot,
                expected_epoch=expected_epoch,
                completion=completion,
                result_only=result_only,
                group_id=group_id,
                independent=independent,
                deferred=deferred,
            )
        except Exception as error:  # observability: ignore R2: a rejected declaration is reported to its caller through the returned Deferred's errback; the receipt consumer owns the diagnosis and its own log event
            deferred.errback(error)
            return deferred
        entry = self._pending_groups.get(intent.group_id)
        if entry is None:
            # A result-only answer is one admitted action's completion, not a
            # presentation intent: it is bounded by the sequence's single
            # in-flight marker, so the queue bound (a publisher-loop guard)
            # never drops it.
            if not intent.result_only and (
                len(self._pending) >= MAX_PENDING_PUBLICATIONS
                or self._pending_waiter_count() >= MAX_PENDING_PUBLICATIONS
            ):
                self._invalidate_baseline()
                deferred.errback(
                    PresentationQueueFull(
                        "presentation queue full for %s" % self.describe_session()
                    )
                )
                return deferred
            entry = _PendingGroup.from_intent(intent, grouped=not intent.standalone)
            self._pending.append(entry)
            self._pending_groups[intent.group_id] = entry
        else:
            if (
                not intent.result_only
                and len(entry.waiters) >= MAX_PENDING_PUBLICATIONS
            ):
                self._invalidate_baseline()
                deferred.errback(
                    PresentationQueueFull(
                        "presentation group overflow for %s"
                        % self.describe_session()
                    )
                )
                return deferred
            entry.merge(intent)
        if entry.grouped:
            self._schedule_deferred_drain()
        else:
            self._schedule_drain()
        return deferred

    def full_snapshot(self, context: PresentationContext) -> Deferred:
        """Publish the complete eager snapshot at one fresh revision."""
        return self.enqueue_publication(
            lambda: context, force_snapshot=True, independent=True
        )

    def panel_update(
        self,
        context: PresentationContext,
        panels: Mapping[str, Any],
        removed_panels: tuple[str, ...] | list[str] = (),
    ) -> Deferred:
        """Publish already-rendered candidates and/or explicit removals."""
        if not panels and not removed_panels:
            deferred: Deferred = Deferred()
            deferred.errback(
                ValueError("panel update requires a panel subset or removals")
            )
            return deferred
        return self.enqueue_publication(
            lambda: context,
            candidate_panels=panels,
            removed_panels=removed_panels,
        )

    def synchronize(self, context: PresentationContext) -> Deferred:
        """Publish a complete baseline from then-current canonical state.

        Errbacks with :class:`ClockUnavailable` when the world-clock singleton
        is absent so the ingress can emit ``presentation_unavailable``.
        """
        return self.enqueue_publication(
            lambda: context, force_snapshot=True, independent=True
        )

    def _build_intent(
        self,
        context_factory: Callable[[], PresentationContext],
        *,
        affected_panels: Any,
        candidate_panels: Mapping[str, Any] | None,
        removed_panels: tuple[str, ...] | list[str],
        force_snapshot: bool,
        expected_epoch: str | None,
        completion: PublicationCompletion | None,
        result_only: bool,
        group_id: str | None,
        independent: bool,
        deferred: Deferred,
    ) -> _Intent:
        """Validate one raw declaration and isolate its supplied candidates.

        Every declaration error is raised here, before queueing, so a rejected
        publication is answered deterministically and never depends on the
        current baseline: unknown candidate names, unknown/duplicate/on-demand
        removals, replace/remove overlap, and a candidate+affected combination
        all fail. An invalid *affected* declaration is not an error (it means
        unknown scope) and is widened during planning.

        The causal group is resolved here, at the call boundary: an explicit
        ``group_id`` wins, otherwise the group bound to this synchronous call,
        otherwise a fresh standalone group. ``independent`` deliberately ignores
        an ambient binding.
        """
        if candidate_panels is not None and affected_panels is not None:
            raise ValueError(
                "a publication declares either affected panels or candidates, never both"
            )
        if result_only and (
            force_snapshot or candidate_panels or affected_panels or removed_panels
        ):
            raise ValueError("a result-only publication carries no presentation")
        candidates: dict[str, Any] | None = None
        if candidate_panels is not None:
            unknown = set(candidate_panels) - self.registry.panel_names
            if unknown:
                raise ValueError(
                    f"publication references unknown panels {sorted(unknown)}"
                )
            candidates = {
                str(name): copy_json_value(value)
                for name, value in candidate_panels.items()
            }
        removed = tuple(str(name) for name in removed_panels)
        if len(set(removed)) != len(removed):
            raise ValueError("a removal list must not repeat a panel name")
        unknown_removed = set(removed) - self.registry.eager_panel_names
        if unknown_removed:
            raise ValueError(
                f"publication removes unregistered eager panels {sorted(unknown_removed)}"
            )
        declared = self._declared_scope(affected_panels)
        if candidates is not None:
            scope = set(candidates)
        else:
            scope = set(declared or ())
        overlap = set(removed) & scope
        if overlap:
            raise ValueError(
                f"publication both replaces and removes {sorted(overlap)}"
            )
        ambient = None if independent else current_publication_group()
        captured = group_id if group_id is not None else (
            ambient.id if ambient is not None else None
        )
        return _Intent(
            context_factory=context_factory,
            candidates=candidates,
            declared=frozenset(declared or ()),
            unknown_scope=(
                not result_only and declared is None and candidates is None
            ),
            removed_panels=removed,
            force_snapshot=bool(force_snapshot),
            result_only=bool(result_only),
            group_id=captured or new_publication_group().id,
            standalone=captured is None,
            epoch=self._epoch,
            expected_epoch=expected_epoch,
            completion=completion,
            deferred=deferred,
        )

    def _declared_scope(self, affected_panels: Any) -> frozenset[str] | None:
        """Normalize one affected declaration, or ``None`` for unknown scope.

        An absent, empty, non-iterable, non-string or non-registered
        declaration is *invalid*, and an invalid declaration means unknown
        scope: every eager panel is re-rendered and compared. Nothing is ever
        silently omitted.
        """
        if not affected_panels:
            return None
        try:
            names = tuple(affected_panels)
        except TypeError:  # observability: ignore R2: an invalid declaration is the designed unknown-scope signal, not a reported failure
            return None
        if not names or any(not isinstance(name, str) for name in names):
            return None
        if any(name not in self.registry.panel_names for name in names):
            return None
        return frozenset(names)

    # ------------------------------------------------------------------
    # Serialized drain and the single synchronous publisher.
    # ------------------------------------------------------------------

    def _schedule_drain(self) -> None:
        """Run the serialized drain for standalone intents before returning.

        An intent that belongs to no captured group publishes at its own enqueue
        boundary, as B defined: an explicit sync or recovery answer must be on
        the wire before a sequence-retiring effect the adapter already scheduled
        can retire the epoch. Grouped intents are deliberately left queued for
        :meth:`_schedule_deferred_drain`, because their own commit callbacks have
        not all run yet; publishing them here would split one causal group into
        an intermediate delta plus its checkpoint snapshot.
        """
        if self._draining:
            return
        self._drain(standalone_only=True)

    def drain(self) -> None:
        """Run every queued publication now (deterministic seam for tests/tooling)."""
        self._drain()

    def flush_publication_group(self, group_id: str) -> None:
        """Publish one pending group now, in place, without touching the others.

        The dispatcher's result-only completion uses this narrow seam: its
        adapter may already have scheduled a sequence retirement for the next
        reactor turn, so that answer must leave first. Every other group keeps
        waiting for the deferred boundary, so no unrelated group is finalized
        before its own commit callbacks finish.
        """
        entry = self._pending_groups.get(group_id)
        if entry is None:
            return
        self._drain(only=entry)

    def _schedule_deferred_drain(self) -> None:
        """Schedule one drain after the current reactor turn.

        A committed operation's on-commit callbacks all run before the reactor
        returns, so its group entry is complete when the scheduled drain runs.
        """
        if self._drain_scheduled:
            return
        self._drain_scheduled = True
        try:
            self._scheduler(self._deferred_drain)
        except Exception as error:  # observability: R2 reported here; no waiter may hang because scheduling failed
            self._drain_scheduled = False
            log_warn(
                "publication_schedule_failed",
                context={
                    "surface": "presentation",
                    "session": getattr(self.session, "sessid", "?"),
                },
                exc=error,
            )
            self._drain()

    def _deferred_drain(self) -> None:
        """The scheduled boundary: clear the marker, then drain every entry."""
        self._drain_scheduled = False
        self._drain()

    def _pending_waiter_count(self) -> int:
        """Every queued Deferred across all pending groups."""
        return sum(len(entry.waiters) for entry in self._pending)

    def _drain(
        self,
        *,
        standalone_only: bool = False,
        only: "_PendingGroup | None" = None,
    ) -> None:
        """Run queued group entries in order inside the publication critical section.

        ``standalone_only`` publishes the entries that belong to no captured
        group and leaves grouped entries for their deferred boundary.
        ``only`` publishes exactly one identified entry in place.
        """
        if self._draining:
            return
        self._draining = True
        try:
            while self._pending:
                if only is not None:
                    if self._pending_groups.get(only.group_id) is not only:
                        return
                    entry = only
                else:
                    entry = next(
                        (
                            candidate
                            for candidate in self._pending
                            if not standalone_only or not candidate.grouped
                        ),
                        None,
                    )
                    if entry is None:
                        return
                self._pending.remove(entry)
                self._pending_groups.pop(entry.group_id, None)
                self._execute(entry)
        finally:
            self._draining = False
        if standalone_only and self._pending and not self._drain_scheduled:
            # A reentrant enqueue hit the draining guard: retry the grouped work
            # at its deferred boundary instead of stranding its waiters.
            self._schedule_deferred_drain()

    def _execute(self, entry: _PendingGroup) -> None:
        """Execute one group entry, resolving every waiter exactly once."""
        if entry.epoch != self._epoch:
            self._resolve(entry, None)
            return
        if entry.expected_epoch is not None and entry.expected_epoch != self._epoch:
            self._resolve(entry, None)
            return
        try:
            receipt = self._publish_now(entry)
        except Exception as error:  # observability: ignore R2: the real error is delivered to every waiter's errback, where the publisher reports it with its own catalogued event
            self._fail(entry, error)
            return
        self._resolve(entry, receipt)

    @staticmethod
    def _resolve(entry: _PendingGroup, receipt: PublicationReceipt | None) -> None:
        for deferred in entry.waiters:
            deferred.callback(receipt)

    @staticmethod
    def _fail(entry: _PendingGroup, error: BaseException) -> None:
        for deferred in entry.waiters:
            deferred.errback(error)

    def _publish_now(self, entry: _PendingGroup) -> PublicationReceipt | None:
        """Plan, prevalidate and send one publication batch synchronously.

        Nothing awaits and nothing reenters: the whole batch (every planned
        frame plus the matching action result) leaves in one critical section,
        so no other publication can appear between a presentation and its
        result. The baseline is installed only after a logical publication's
        frames all sent; the issued revision advances at the first attempted
        send so an escaped target is never reused.
        """
        if entry.result_only:
            revision = self.published_revision
            envelope = self._completion_envelope(entry, revision)
            if envelope is not None:
                self._send_result(envelope)
            return PublicationReceipt(self._epoch, revision, "unchanged", False)
        context = entry.context_factory()
        mode = self._mode_provider(context)
        server_time = copy_json_value(self.server_time())
        baseline = self._baseline
        if (
            entry.force_snapshot
            or baseline is None
            or not baseline.valid
            or self._repair_required
            or self._revision == 0
        ):
            plans: list[_LogicalPublication] = [
                self._plan_snapshot(context, mode, server_time)
            ]
        else:
            plans = self._plan_delta(context, entry, baseline, mode, server_time)
        target = plans[-1].revision if plans else self.published_revision
        result_envelope = self._completion_envelope(entry, target)
        self._send_plans(plans)
        if result_envelope is not None:
            self._send_result(result_envelope)
        if self._epoch != entry.epoch:
            # The sequence was retired while the batch was sending; nothing
            # about the new sequence may be reported as this entry's result.
            return None
        if not plans:
            return PublicationReceipt(
                self._epoch, self.published_revision, "unchanged", False
            )
        kind = "snapshot" if plans[0].snapshot else "delta"
        return PublicationReceipt(self._epoch, plans[-1].revision, kind, True)

    def _completion_envelope(
        self, entry: _PendingGroup, revision: int
    ) -> dict[str, Any] | None:
        """Build and prevalidate the matching action result before any send."""
        if entry.completion is None:
            return None
        envelope = entry.completion.envelope(self._epoch, revision)
        validate_ui_action_result(envelope)
        return envelope

    def _send_plans(self, plans: list[_LogicalPublication]) -> None:
        for plan in plans:
            self._revision = plan.revision
            try:
                for frame in plan.frames:
                    self._send(plan.message, frame)
            except Exception:
                # An escaped frame is on the wire, so these values can never be
                # a delta base again; the issued target stays consumed.
                self._invalidate_baseline()
                raise
            self._install(plan)
            if plan.map_panel is not None:
                if plan.parts:
                    log_debug(
                        "map_panel_transfer_sent",
                        context={
                            "surface": "presentation",
                            "panel": plan.map_panel,
                            "revision": plan.revision,
                            "parts": plan.parts,
                        },
                    )
                else:
                    self._log_intact_world_map(plan.frames[0])
            log_info(
                "presentation_published",
                context={
                    "surface": "presentation",
                    "session": getattr(self.session, "sessid", "?"),
                    "kind": "snapshot" if plan.snapshot else "delta",
                    "revision": plan.revision,
                    "mode": plan.mode,
                    "panels": ",".join(sorted(plan.replacements)) or "-",
                    "removed": ",".join(plan.removed) or "-",
                },
            )

    def _install(self, plan: _LogicalPublication) -> None:
        """Install the just-published values as the new baseline."""
        if plan.snapshot:
            panels = dict(plan.replacements)
            self._repair_required = False
        else:
            panels = dict(self._baseline.panels) if self._baseline is not None else {}
            panels.update(plan.replacements)
            for name in plan.removed:
                panels.pop(name, None)
        self._baseline = _Baseline(
            epoch=self._epoch,
            revision=plan.revision,
            panels=panels,
            mode=plan.mode,
            layout_version=LAYOUT_VERSION,
            server_time=dict(plan.server_time),
            valid=True,
        )

    # ------------------------------------------------------------------
    # Planning.
    # ------------------------------------------------------------------

    def _plan_snapshot(
        self, context: PresentationContext, mode: str, server_time: dict[str, Any]
    ) -> _LogicalPublication:
        """Plan the complete eager snapshot at one fresh revision."""
        revision = self._reserve(self._revision + 1)
        panels = {
            name: copy_json_value(value)
            for name, value in self._render_all(context).items()
        }
        envelope = self._snapshot_envelope(panels, revision, mode, server_time)
        check_envelope(envelope)
        validate_ui_snapshot(envelope, known_panels=set(self.registry.panel_names))
        return _LogicalPublication(
            snapshot=True,
            message=SNAPSHOT_MESSAGE,
            revision=revision,
            frames=(envelope,),
            replacements=panels,
            removed=(),
            mode=mode,
            server_time=server_time,
        )

    def _plan_delta(
        self,
        context: PresentationContext,
        entry: _PendingGroup,
        baseline: _Baseline,
        mode: str,
        server_time: dict[str, Any],
    ) -> list[_LogicalPublication]:
        """Plan only the differences between the declared scope and the baseline.

        A merged group may combine supplied candidates with a declared scope or
        with unknown scope, so the compared scope is their union and the
        unknown-scope flag widens it to every eager panel exactly as before.
        """
        eager_names = self.registry.eager_panel_names
        scope = set(entry.declared)
        if entry.candidates is not None:
            scope |= set(entry.candidates)
        unknown_scope = entry.unknown_scope
        removed_now = set(entry.removed_panels)
        if unknown_scope or mode != baseline.mode:
            # Unknown scope and every mode transition recompute all eager
            # panels: a transition into or out of dialogue must carry the
            # mode-dependent payloads together, and supplied candidates keep
            # their supplied value. An explicit removal is never re-rendered:
            # the removal wins, so the expansion cannot both replace and remove
            # the same name (or add back a panel the planner deleted).
            scope |= set(eager_names) - removed_now
        if (
            mode == DIALOGUE_PANEL
            and DIALOGUE_PANEL in eager_names
            and DIALOGUE_PANEL not in removed_now
        ):
            scope.add(DIALOGUE_PANEL)

        values: dict[str, Any] = {}
        map_bodies: dict[str, Any] = {}
        for name in sorted(scope):
            supplied = entry.candidates is not None and name in entry.candidates
            value = entry.candidates[name] if supplied else self.registry.render(name, context)
            if name in self.registry.on_demand_panel_names:
                map_bodies[name] = self._checked_map_body(name, value)
                continue
            values[name] = value

        replacements: dict[str, Any] = {}
        for name, value in values.items():
            known = baseline.panels.get(name, _MISSING)
            if known is not _MISSING and json_value_equal(known, value):
                continue
            supplied = entry.candidates is not None and name in entry.candidates
            # Own the adopted value before anything is sent, so a presenter that
            # reuses its returned container cannot change what was published.
            replacements[name] = value if supplied else copy_json_value(value)
        removed = tuple(
            name for name in entry.removed_panels if name in baseline.panels
        )
        metadata_changed = (
            mode != baseline.mode
            or baseline.layout_version != LAYOUT_VERSION
            or not json_value_equal(baseline.server_time, server_time)
        )

        plans: list[_LogicalPublication] = []
        base = baseline.revision
        if map_bodies:
            combined = dict(replacements)
            combined.update(map_bodies)
            candidate = self._update_envelope(
                combined, self._reserve(base + 1), base, removed, mode, server_time
            )
            if self._fits_one_frame(candidate):
                # ``_fits_one_frame`` already enforced either the generic
                # bounds or the scoped world-map allowance, so only the delta
                # schema remains to check here.
                validate_ui_update(
                    candidate, known_panels=set(self.registry.panel_names)
                )
                plans.append(
                    _LogicalPublication(
                        snapshot=False,
                        message=UPDATE_MESSAGE,
                        revision=candidate["revision"],
                        frames=(candidate,),
                        replacements=replacements,
                        removed=removed,
                        mode=mode,
                        server_time=server_time,
                        map_panel=sorted(map_bodies)[0] if len(map_bodies) == 1 else None,
                    )
                )
                return plans
            if replacements or removed or metadata_changed:
                eager_revision = self._reserve(base + 1)
                eager = self._update_envelope(
                    replacements, eager_revision, base, removed, mode, server_time
                )
                self._checked_update(eager)
                plans.append(
                    _LogicalPublication(
                        snapshot=False,
                        message=UPDATE_MESSAGE,
                        revision=eager_revision,
                        frames=(eager,),
                        replacements=replacements,
                        removed=removed,
                        mode=mode,
                        server_time=server_time,
                    )
                )
                base = eager_revision
            for name in sorted(map_bodies):
                frames, parts = self._map_frames(
                    name, map_bodies[name], self._reserve(base + 1), base, mode, server_time
                )
                plans.append(
                    _LogicalPublication(
                        snapshot=False,
                        message=UPDATE_MESSAGE,
                        revision=frames[0]["revision"],
                        frames=frames,
                        replacements={},
                        removed=(),
                        mode=mode,
                        server_time=server_time,
                        map_panel=name,
                        parts=parts,
                    )
                )
                base = frames[0]["revision"]
            return plans

        if not replacements and not removed and not metadata_changed:
            return []
        revision = self._reserve(base + 1)
        envelope = self._update_envelope(
            replacements, revision, base, removed, mode, server_time
        )
        self._checked_update(envelope)
        return [
            _LogicalPublication(
                snapshot=False,
                message=UPDATE_MESSAGE,
                revision=revision,
                frames=(envelope,),
                replacements=replacements,
                removed=removed,
                mode=mode,
                server_time=server_time,
            )
        ]

    def _map_frames(
        self,
        name: str,
        body: dict[str, Any],
        revision: int,
        base_revision: int,
        mode: str,
        server_time: dict[str, Any],
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Build and prevalidate every frame of one logical map publication.

        A world map is one intact frame under its scoped allowance; an area map
        is a bounded part transfer. All frames repeat the same exact base and
        revision, so no part advances the client's committed revision.
        """
        if name == WORLD_MAP_PANEL:
            frames = (
                self._update_envelope(
                    {name: body}, revision, base_revision, (), mode, server_time
                ),
            )
            check_world_map_envelope(frames[0])
        else:
            from web.webclient.presentation.map_parts import encode_map_parts

            frames = tuple(
                self._update_envelope(
                    {name: part}, revision, base_revision, (), mode, server_time
                )
                for part in encode_map_parts(name, body)
            )
        for frame in frames:
            if carries_intact_world_map(frame):
                check_world_map_envelope(frame)
            else:
                check_envelope(frame)
            validate_ui_update(frame, known_panels=set(self.registry.panel_names))
        return frames, (len(frames) if name != WORLD_MAP_PANEL else 0)

    def _reserve(self, revision: int) -> int:
        """Return ``revision`` after checking the safe-integer ceiling."""
        if revision > MAX_SAFE_INTEGER:
            raise RuntimeError("presentation revision range exhausted")
        return revision

    # ------------------------------------------------------------------
    # Envelope builders, transport and prevalidation helpers.
    # ------------------------------------------------------------------

    def _snapshot_envelope(
        self,
        panels: dict[str, Any],
        revision: int,
        mode: str,
        server_time: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "presentation_epoch": self._epoch,
            "revision": revision,
            "mode": mode,
            "panels": panels,
            "layout_version": LAYOUT_VERSION,
            "server_time": server_time,
        }

    def _update_envelope(
        self,
        panels: Mapping[str, Any],
        revision: int,
        base_revision: int,
        removed: tuple[str, ...],
        mode: str,
        server_time: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "presentation_epoch": self._epoch,
            "revision": revision,
            "base_revision": base_revision,
            "removed_panels": list(removed),
            "mode": mode,
            "panels": dict(panels),
            "layout_version": LAYOUT_VERSION,
            "server_time": server_time,
        }

    def _checked_update(self, envelope: dict[str, Any]) -> None:
        """Prevalidate one delta against both the frame and the delta schema."""
        check_envelope(envelope)
        validate_ui_update(envelope, known_panels=set(self.registry.panel_names))

    def _checked_map_body(self, name: str, payload: Any) -> dict[str, Any]:
        """Validate one map body, degrading a malformed one to unavailable.

        The registry isolates presenter exceptions; a presenter that returns a
        body violating the fixed map schema is isolated the same way here, so
        no invalid map ever reaches the wire.
        """
        from web.webclient.presentation.map_panels import validate_map_panel

        try:
            return validate_map_panel(name, payload)
        except ProtocolValidationError as error:
            correlation_id = secrets.token_hex(16)
            log_error(
                "map_panel_invalid",
                context={"surface": "presentation", "panel": name, "correlation_id": correlation_id},
                exc=error,
            )
            return self.registry.build_unavailable(name, internal=True, correlation_id=correlation_id)

    @staticmethod
    def _fits_one_frame(candidate: dict[str, Any]) -> bool:
        """Whether one update frame may carry ``candidate`` intact.

        A frame fits when it passes the generic envelope bounds, or when it
        carries an intact world map and passes the scoped world-map allowance
        (everything else generic, the world map within its own ceiling).
        """
        try:
            check_envelope(candidate)
            return True
        except JSONSafetyError:  # observability: ignore R2: an over-bound map update is the designed trigger for the scoped world-map check or bounded part delivery
            pass
        if not carries_intact_world_map(candidate):
            return False
        try:
            check_world_map_envelope(candidate)
            return True
        except ProtocolValidationError:  # observability: ignore R2: a combined frame outside the allowance falls back to separate frames, each re-checked (and raising) before any send
            return False

    @staticmethod
    def _log_intact_world_map(frame: dict[str, Any]) -> None:
        """Debug trace of an intact world-map frame and its canonical size."""
        body = frame["panels"].get(WORLD_MAP_PANEL)
        if not isinstance(body, dict) or "part" in body:
            return
        log_debug(
            "world_map_frame_sent",
            context={
                "surface": "presentation",
                "panel": WORLD_MAP_PANEL,
                "revision": frame["revision"],
                "bytes": json_byte_size(body),
            },
        )

    def _send(self, message_name: str, envelope: dict[str, Any]) -> None:
        """Deliver one exact envelope as the only positional transport arg."""
        self.session.msg(**{message_name: ((envelope,), {})})

    def _send_result(self, envelope: dict[str, Any]) -> None:
        """Deliver the matching action result inside the same critical section."""
        try:
            self.session.msg(**{UI_ACTION_RESULT: ((envelope,), {})})
        except Exception as error:
            raise ResultDeliveryError("action result delivery failed") from error

    @staticmethod
    def mode_for(context: PresentationContext) -> str:
        """Derive the snapshot mode from canonical puppet state only.

        Resolution order (webclient-align-10): creation-pending → ``creation``,
        active combat → ``combat``, live dialogue session → ``dialogue``,
        else ``exploration``. Combat outranks a live session object whose
        cleanup seam has not run yet; ``live_dialogue_session`` is the sole
        liveness gate, so a session naming a departed/stale host never
        resolves the dialogue mode.
        """
        actor = context.actor
        if bool(getattr(actor, "creation_pending", False)):
            return "creation"
        from world.rules.combat_session import is_in_active_session, session_owner

        # A possessed puppet operates its commander's session, so the combat
        # mode follows the session owner rather than the puppet.
        if is_in_active_session(session_owner(actor)):
            return "combat"
        from world.rules.dialogue import live_dialogue_session

        if live_dialogue_session(actor) is not None:
            return "dialogue"
        return "exploration"

    def _render_all(self, context: PresentationContext) -> dict[str, Any]:
        """Render every eager panel, isolating each presenter failure.

        On-demand map panels are never rendered here: an eager snapshot omits
        their bodies, and the browser retains same-epoch maps separately.
        """
        return {
            panel_name: self.registry.render(panel_name, context)
            for panel_name in sorted(self.registry.eager_panel_names)
        }

    def describe_session(self) -> str:
        """Return a diagnostic label that never leaks canonical state."""
        return "session %s" % getattr(self.session, "sessid", "?")


def attach_coordinator(session: Any, registry: PresentationRegistry) -> PresentationCoordinator:
    """Return (and lazily attach) the ephemeral coordinator for a session."""
    ndb = getattr(session, "ndb", None)
    coordinator = getattr(ndb, "elosern_coordinator", None) if ndb is not None else None
    if coordinator is None:
        coordinator = PresentationCoordinator(session, registry)
        if ndb is not None:
            ndb.elosern_coordinator = coordinator
    return coordinator


def publish_panel_update(
    session: Any,
    actor: Any,
    panels: Mapping[str, Any],
    *,
    context: PresentationContext | None = None,
    expected_epoch: str,
    affected_panels: tuple[str, ...] | list[str] | None = None,
    independent: bool = False,
) -> Deferred:
    """Push one validated panel subset to a live session under the epoch guard.

    The trigger service's async generation completes after scheduling; between
    the two moments a puppet change, reconnect, or sequence reset may have
    started a fresh presentation sequence. This helper resolves ``None``
    without publishing when the session's live coordinator is absent or its
    epoch no longer equals the ``expected_epoch`` captured when the push was
    scheduled, and otherwise resolves the publication's
    :class:`~web.webclient.presentation.publication.PublicationReceipt`
    (``published=False`` for an unchanged push). A failed publication is logged
    and resolved ``None``: an async delivery cannot raise into the generation
    route, and the session's next snapshot re-establishes the truth. An absent
    coordinator is left alone — nothing is attached by this helper; the ingress
    attaches on the session's next sync. ``context`` is the caller's
    :class:`PresentationContext`, assembled through the shared ingress factory
    so the ``context_actions`` presenter renders from the ``OptionsSnapshot``.

    The queued request always rebuilds its context through that same ingress
    factory at drain time, so a grouped push can never re-render from a stale
    snapshot. ``affected_panels`` lets a producer submit the panel *names* it
    changed instead of an eagerly rendered payload; the coordinator then renders
    them from current canonical state, which is what a grouped ordinary push
    does. When it is supplied, ``panels`` is ignored. ``independent`` marks a
    delivery that must never join an ambient group: a one-shot notice whose
    decoration cannot survive a checkpoint promotion (a claimed dialogue unlock
    batch) publishes as its own entry.
    """
    ndb = getattr(session, "ndb", None)
    coordinator = getattr(ndb, "elosern_coordinator", None) if ndb is not None else None
    if coordinator is None or coordinator.epoch != expected_epoch:
        return succeed(None)
    declared = (
        tuple(str(name) for name in affected_panels)
        if affected_panels is not None
        else None
    )

    def _context() -> PresentationContext:
        from web.webclient.presentation.ingress import build_presentation_context

        return build_presentation_context(session, actor)

    deferred = coordinator.enqueue_publication(
        _context,
        candidate_panels=panels if declared is None else None,
        affected_panels=declared,
        expected_epoch=expected_epoch,
        independent=independent,
    )
    names = declared if declared is not None else tuple(panels)

    def _failed(failure: Any) -> Any:
        error = failure.value if isinstance(failure, Failure) else failure
        log_warn(
            "presentation_push_failed",
            context={"surface": "presentation", "panels": ",".join(sorted(names))},
            exc=error,
        )
        return None

    deferred.addErrback(_failed)
    return deferred


def detach_coordinator(session: Any) -> None:
    """Drop the ephemeral coordinator (transport or puppet change)."""
    from web.webclient.presentation.gallery_selection import retire_gallery_selection

    ndb = getattr(session, "ndb", None)
    coordinator = getattr(ndb, "elosern_coordinator", None) if ndb is not None else None
    if coordinator is not None:
        # Retire the old sequence's baseline and queued work before dropping
        # the reference, so nothing it captured can publish afterwards.
        coordinator.reset()
    retire_gallery_selection(session)
    if ndb is not None:
        session.ndb.elosern_coordinator = None


def log_unavailable(session_tag: str, message: str) -> None:
    """Log a safe presentation-unavailable notice without a traceback."""
    log_warn(
        "presentation_unavailable",
        context={"surface": "presentation", "session": session_tag, "reason": message},
    )
