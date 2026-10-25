"""Dialogue-panel fan-out for one owning player's current connections.

``push_dialogue_update`` (the shared pusher factory shell) pushes a freshly
rendered panel to every live watcher of ONE actor. Reading completion needs a
narrower recipient set: the owning player's own current connections, never
another character of the same account, and each connection's panel must be
rendered from ITS OWN puppet, so a completion on one connection can never
replace another connection's locally playing scene.

``push_dialogue_reading(owner)`` is that seam. It discovers candidate
connections through the canonical account-session helper
(``world.rules.unlock_notices.commander_sessions``), filters each by
``resolve_commander(current puppet) is owner``, matches the connection against
that puppet's registered watchers (the pusher's epoch guard), and publishes the
panel through the same ``PanelPushDeps`` collaborators the shared pusher uses —
one epoch-guarded publish per connection, each failure isolated and
bounded-logged. Nothing is persisted; a missed push recovers on the next
canonical sync.
"""

from world.observability import log_warn

from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.push import PanelPushDeps, make_panel_pusher
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for

__all__ = ["push_dialogue_reading", "push_dialogue_update"]


def _deps() -> PanelPushDeps:
    """Resolve the fan-out collaborators from this module's globals.

    Read per call so identity-based test patches on this module's names keep
    intercepting the shared factory body.
    """
    return PanelPushDeps(
        watchers_for=watchers_for,
        build_registry=build_production_registry,
        build_context=build_presentation_context,
        publish=publish_panel_update,
        log_warn=log_warn,
    )


push_dialogue_update = make_panel_pusher("dialogue", "dialogue", _deps)


def _owner_connection(puppet: object, owner: object) -> bool:
    """Whether this connection's current puppet is lawfully commanded by ``owner``.

    ``resolve_commander`` resolves a player character to itself and a lawfully
    possessed companion to its commander. Anything else (a forged mirror, an
    unrelated body, another character of the same account) contributes nothing.
    """
    from world.rules.party_scope import PartyScopeError, resolve_commander

    try:
        commander = resolve_commander(puppet)
    except PartyScopeError:  # observability: ignore R2: an unowned body is simply excluded from the owner's fan-out
        return False
    except Exception:  # observability: ignore R2: an unreadable control read authorizes no recipient
        return False
    if commander is owner:
        return True
    # An idmapper round-trip can hand back an equal instance; the lawful control
    # resolution above is what authorizes the recipient, so compare identities.
    commander_pk = getattr(commander, "pk", None)
    owner_pk = getattr(owner, "pk", None)
    return (
        isinstance(commander_pk, int)
        and not isinstance(commander_pk, bool)
        and commander_pk > 0
        and commander_pk == owner_pk
    )


def push_dialogue_reading(owner: object) -> None:
    """Publish each of ``owner``'s current connections its own dialogue panel.

    Never raises: a failure is isolated to one bounded diagnostic and the next
    canonical sync re-establishes the truth.
    """
    deps = _deps()
    # The facade binding keeps the lint's syntactic facade-call recognition
    # live, exactly like the shared pusher factory does.
    log_warn = deps.log_warn
    puppets = _owner_puppets(owner, log_warn=log_warn)
    if not puppets:
        return
    try:
        registry = deps.build_registry()
    except Exception as error:
        log_warn(
            "dialogue_reading_push_failed",
            context={
                "surface": "presentation",
                "char": str(getattr(owner, "pk", "?")),
            },
            exc=error,
        )
        return
    for puppet in puppets:
        for watcher, epoch in deps.watchers_for(puppet):
            try:
                context = deps.build_context(watcher, puppet)
                payload = registry.render("dialogue", context)
                deps.publish(
                    watcher,
                    puppet,
                    {"dialogue": payload},
                    context=context,
                    expected_epoch=epoch,
                )
            except Exception as error:
                log_warn(
                    "dialogue_reading_push_failed",
                    context={
                        "surface": "presentation",
                        "char": str(getattr(owner, "pk", "?")),
                        "session": str(getattr(watcher, "sessid", "?")),
                    },
                    exc=error,
                )


def _owner_puppets(owner: object, *, log_warn: object) -> tuple[object, ...]:
    """Every puppet lawfully commanded by ``owner`` right now.

    Discovery starts from ``commander_sessions`` (the canonical account-session
    helper), so a second connection of the same owner is found even while the
    owner's body is unpuppeted by possession. The owner's own body and its
    currently possessed companion are added as candidates because a test or
    headless session may carry no account link; every candidate is then
    filtered by ``resolve_commander(candidate) is owner``, which never admits
    another character of the same account or a forged control mirror.
    """
    candidates: list[object] = []
    try:
        from world.rules.unlock_notices import commander_sessions

        for session in commander_sessions(owner):
            puppet = getattr(session, "puppet", None)
            if puppet is not None:
                candidates.append(puppet)
    except Exception as error:  # observability: ignore R2: account discovery failure is reported and the direct candidates still fan out
        log_warn(
            "dialogue_reading_push_watchers_failed",
            context={
                "surface": "presentation",
                "char": str(getattr(owner, "pk", "?")),
            },
            exc=error,
        )
    candidates.append(owner)
    body = _possession_body(owner)
    if body is not None:
        candidates.append(body)

    puppets: list[object] = []
    seen: set[int] = set()
    for candidate in candidates:
        identity = id(candidate)
        if identity in seen:
            continue
        seen.add(identity)
        if _owner_connection(candidate, owner):
            puppets.append(candidate)
    return tuple(puppets)


def _possession_body(owner: object) -> object | None:
    """The companion ``owner`` lawfully possesses right now, or ``None``.

    Both the possession mirror and the canonical party binding must agree, so a
    stale or forged mirror contributes no recipient.
    """
    from evennia.objects.objects import ObjectDB

    from world.rules.party import bound_owner_of
    from world.rules.possession import current_possession

    try:
        binding = current_possession(owner)
    except Exception:  # observability: ignore R2: an unreadable possession mirror yields no extra recipient
        return None
    if not binding:
        return None
    body = ObjectDB.objects.filter(id=binding.get("npc_dbid")).first()
    if body is None:
        return None
    if bound_owner_of(body) is not owner:
        return None
    if getattr(getattr(body, "db", None), "possessed_by", None) != int(
        getattr(owner, "pk", 0)
    ):
        return None
    return body
