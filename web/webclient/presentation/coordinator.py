"""Session-scoped snapshot coordinator for the version-1 OOB protocol.

The coordinator owns the ephemeral presentation sequence for one live
WebSocket transport and active puppet: a cryptographically random epoch,
a monotonic per-epoch revision counter, full snapshots, complete panel
replacements, calendar serialization, and puppet-change reset. None of this
state is ever persisted; it lives only on ``session.ndb`` and disappears with
the transport.

The coordinator never writes canonical game state and never reaches for a
mutation helper: calendar data comes only from the read-only
``world.rules.clock.read_world_clock`` accessor.
"""

from typing import Any, Callable

from world.observability import log_warn

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    PROTOCOL_VERSION,
    new_presentation_epoch,
)
from web.webclient.presentation.registry import PresentationRegistry

# The approved default layout version shipped by this delivery unit.
LAYOUT_VERSION = 1

# The server message name carrying a full snapshot.
SNAPSHOT_MESSAGE = "ui_snapshot"
UPDATE_MESSAGE = "ui_update"


class ClockUnavailable(RuntimeError):
    """The world-clock singleton is absent; presentation cannot continue."""


def read_world_clock_calendar() -> Any:
    """Return the calendar of the existing world clock without creating one.

    Delegates to ``world.rules.clock.read_world_clock``, which never creates a
    Script. Returns ``None`` when the singleton is absent so the coordinator
    can fail safely with ``presentation_unavailable``.
    """
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return None if clock is None else clock.calendar


class PresentationCoordinator:
    """One ephemeral presentation sequence bound to a live server session.

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
    ) -> None:
        self.session = session
        self.registry = registry
        self._calendar_provider = calendar_provider
        self._mode_provider = mode_provider or self.mode_for
        self._epoch = new_presentation_epoch()
        self._revision = 0

    @property
    def epoch(self) -> str:
        return self._epoch

    @property
    def revision(self) -> int:
        return self._revision

    def reset(self) -> None:
        """Start a fresh presentation sequence (reconnect or puppet change)."""
        self._epoch = new_presentation_epoch()
        self._revision = 0

    def _next_revision(self) -> int:
        if self._revision >= MAX_SAFE_INTEGER:
            raise RuntimeError("presentation revision range exhausted")
        self._revision += 1
        return self._revision

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

    def _build_presentation(
        self, context: PresentationContext, panels: dict[str, Any]
    ) -> dict[str, Any]:
        """Assemble one exact snapshot/update envelope from committed panel data."""
        return {
            "protocol_version": PROTOCOL_VERSION,
            "presentation_epoch": self._epoch,
            "revision": self._next_revision(),
            "mode": self._mode_provider(context),
            "panels": panels,
            "layout_version": LAYOUT_VERSION,
            "server_time": self.server_time(),
        }

    def _send(self, message_name: str, envelope: dict[str, Any]) -> None:
        """Deliver one exact envelope as the only positional transport arg."""
        self.session.msg(**{message_name: ((envelope,), {})})

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
        from world.rules.combat_session import is_in_active_session

        if is_in_active_session(actor):
            return "combat"
        from world.rules.dialogue import live_dialogue_session

        if live_dialogue_session(actor) is not None:
            return "dialogue"
        return "exploration"

    def _render_all(self, context: PresentationContext) -> dict[str, Any]:
        """Render every registered panel, isolating each presenter failure."""
        return {
            panel_name: self.registry.render(panel_name, context)
            for panel_name in sorted(self.registry.panel_names)
        }

    def full_snapshot(self, context: PresentationContext) -> dict[str, Any]:
        """Build and send a full snapshot containing every registered panel."""
        envelope = self._build_presentation(context, self._render_all(context))
        self._send(SNAPSHOT_MESSAGE, envelope)
        return envelope

    def panel_update(
        self, context: PresentationContext, panels: dict[str, Any]
    ) -> dict[str, Any]:
        """Build and send an affected-panel update at a new revision.

        ``panels`` must be a nonempty subset of registered panel names. Every
        included panel completely replaces its prior value; the update carries
        the same metadata as a snapshot.
        """
        if not panels:
            raise ValueError("panel update requires a nonempty panel subset")
        unknown = set(panels) - self.registry.panel_names
        if unknown:
            raise ValueError(
                f"panel update references unknown panels {sorted(unknown)}"
            )
        envelope = self._build_presentation(context, panels)
        self._send(UPDATE_MESSAGE, envelope)
        return envelope

    def _publish_presentation(
        self,
        context: PresentationContext,
        affected_panels: set[str] | None,
    ) -> int:
        """Publish canonical presentation and return the revision just issued.

        ``affected_panels`` of ``None`` (or an empty set) produces a full
        snapshot; a nonempty set produces a single affected-panel update.
        This is the single publication critical section used by action
        completion and by ordinary text-command refresh.
        """
        if affected_panels:
            self.panel_update(context, {name: self.registry.render(name, context) for name in affected_panels})
        else:
            self.full_snapshot(context)
        return self._revision

    def synchronize(self, context: PresentationContext) -> None:
        """Publish a full snapshot from then-current canonical state.

        Raises :class:`ClockUnavailable` when the world-clock singleton is
        absent so the input function can emit ``presentation_unavailable``.
        """
        self.full_snapshot(context)

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
    panels: dict[str, Any],
    *,
    context: PresentationContext,
    expected_epoch: str,
) -> dict[str, Any] | None:
    """Push one validated panel subset to a live session under the epoch guard.

    The trigger service's async generation completes after scheduling; between
    the two moments a puppet change, reconnect, or sequence reset may have
    started a fresh presentation sequence. This helper returns the emitted
    envelope, or publishes nothing (returning ``None``) when the session's live
    coordinator is absent or its epoch no longer equals the ``expected_epoch``
    captured when the push was scheduled. An absent coordinator is left alone —
    nothing is attached by this helper; the ingress attaches on the session's
    next sync. ``context`` is the caller's :class:`PresentationContext`,
    assembled through the shared ingress factory so the ``context_actions``
    presenter renders from the ``OptionsSnapshot``.
    """
    ndb = getattr(session, "ndb", None)
    coordinator = getattr(ndb, "elosern_coordinator", None) if ndb is not None else None
    if coordinator is None or coordinator.epoch != expected_epoch:
        return None
    try:
        return coordinator.panel_update(context, panels)
    except Exception as error:
        # A guarded push's contract is a silent no-op toward its caller: an
        # async delivery cannot raise into the generation route, and the
        # session's next snapshot re-establishes the truth.
        log_warn(
            "presentation_push_failed",
            context={"surface": "presentation", "panels": str(panels)},
            exc=error,
        )
        return None


def detach_coordinator(session: Any) -> None:
    """Drop the ephemeral coordinator (transport or puppet change)."""
    if getattr(session, "ndb", None) is not None:
        session.ndb.elosern_coordinator = None


def log_unavailable(session_tag: str, message: str) -> None:
    """Log a safe presentation-unavailable notice without a traceback."""
    log_warn(
        "presentation_unavailable",
        context={"surface": "presentation", "session": session_tag, "reason": message},
    )
