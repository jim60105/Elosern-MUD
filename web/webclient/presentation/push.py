"""Shared panel-push fan-out factory for the no-session-context push trio.

``party_push``, ``dialogue_push``, and ``lore_codex_push`` each re-render one
panel from CURRENT canonical state and publish it to every live watcher of the
player, with the same failure discipline: watcher lookup and registry
construction degrade to bounded diagnostics instead of raising into their
on-commit / reveal callers, and one bad session never suppresses the others.
That fan-out lives here once, as :func:`make_panel_pusher`.

Event ids are built as ``{event_prefix}_push_watchers_failed`` and
``{event_prefix}_push_failed`` so the trio's catalog strings stay
byte-identical (party/dialogue/lore_codex x the two templates);
``web/webclient/tests/test_panel_push_factory.py`` pins the six concrete
strings so a prefix typo can never silently mint a new event id.

The module import of ``world.observability.log_warn`` is intentional even
though the push closure rebinds it from the shell-provided dependency bundle
below: the import makes this file an observability-facade adopter, so the R2
silent-swallow gate keeps guarding the factory's three except handlers. Do not
clean it up as dead code.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from world.observability import log_warn

__all__ = ["PanelPushDeps", "make_panel_pusher"]


@dataclass(frozen=True)
class PanelPushDeps:
    """The collaborators one fan-out needs, resolved per call.

    Each ``*_push`` shell builds this bundle from its own module globals at
    call time, so identity-based test patches on the shell module
    (``patch.object(party_push, "watchers_for", ...)`` and friends) keep
    intercepting the shared body.
    """

    watchers_for: Callable[[Any], Any]
    build_registry: Callable[[], Any]
    build_context: Callable[[Any, Any], Any]
    publish: Callable[..., Any]
    log_warn: Callable[..., None]


def make_panel_pusher(
    panel_key: str,
    event_prefix: str,
    deps: Callable[[], PanelPushDeps],
) -> Callable[[Any], None]:
    """Build the shared fan-out for one panel, reading deps per push.

    ``deps`` is a zero-arg provider supplied by each shell that reads the
    *shell module's* global names at call time; the returned closure resolves
    every collaborator through it so test patches on the shell module keep
    working after the body moved here.
    """

    def push(player: Any) -> None:
        resolved = deps()
        # Rebinding the facade logger through the shell bundle per call is what
        # keeps ``patch.object(<shell>, "log_warn", ...)`` live (AGENTS.md:
        # assert on the caller module's binding, never world.observability.*).
        # The name must stay exactly ``log_warn`` so the observability lint's
        # syntactic facade-call recognition keeps enforcing R2 on the handlers.
        log_warn = resolved.log_warn
        try:
            watchers = resolved.watchers_for(player)
        except Exception as error:
            log_warn(
                f"{event_prefix}_push_watchers_failed",
                context={"surface": "presentation", "char": str(getattr(player, "pk", "?"))},
                exc=error,
            )
            return
        if not watchers:
            return
        try:
            registry = resolved.build_registry()
        except Exception as error:
            # A registry-construction defect must degrade to a bounded
            # diagnostic (final rubber-duck round): raising from an
            # on-commit callback would surface in the delete caller and
            # skip later commit callbacks.
            log_warn(
                f"{event_prefix}_push_failed",
                context={"surface": "presentation", "char": str(getattr(player, "pk", "?"))},
                exc=error,
            )
            return
        for session, epoch in watchers:
            try:
                context = resolved.build_context(session, player)
                payload = registry.render(panel_key, context)
                resolved.publish(
                    session,
                    player,
                    {panel_key: payload},
                    context=context,
                    expected_epoch=epoch,
                )
            except Exception as error:
                log_warn(
                    f"{event_prefix}_push_failed",
                    context={
                        "surface": "presentation",
                        "char": str(getattr(player, "pk", "?")),
                        "session": str(getattr(session, "sessid", "?")),
                    },
                    exc=error,
                )

    return push