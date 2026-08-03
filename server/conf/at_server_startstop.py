"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def _register_narrator_layer():
    """Register the narrator layer's guardrail hooks with the template renderer.

    Called from ``at_server_start`` because it must run after ``evennia._init()``
    has populated ``evennia.logger``: ``world.ai.guardrail`` captures the logger
    at import time, so registering during settings load would permanently bind a
    ``None`` logger and break every degrade path. This site may import
    ``world.rules`` on the narrator's behalf; ``world/ai/`` never does.

    Registration is boot-tolerant: an already-present narrator registration
    (this module's own idempotent re-registration, or a foreign one left by an
    earlier in-process test) must never abort server startup. The narrate gate
    still fails loudly on a non-narrator registration, so correctness is
    preserved even when this swallow path is taken.
    """
    from evennia import logger
    from world.ai.guardrail import GuardrailRegistrationError
    from world.ai.narrator import register_narrator
    from world.rules.event_log import render_plain_text

    try:
        register_narrator(
            lambda event_logs: "\n".join(render_plain_text(log) for log in event_logs)
        )
    except GuardrailRegistrationError as exc:
        logger.log_warn(f"narrator registration skipped at server start: {exc}")


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from world.lore.sync import sync_all
    from world.maps.bootstrap import (
        sync_grid,
        sync_service_interiors,
        sync_wilderness,
    )
    from world.quests.bootstrap import sync_quest_runtime
    from world.rules.clock import get_world_clock
    from world.rules.guild_economy import sync_guild_economy
    from world.rules.onboarding import sync_guard_npc

    # Deterministic startup owns the world-clock singleton; presentation reads
    # only through read_world_clock() and must never create it.
    get_world_clock()
    sync_all()
    sync_grid()
    sync_wilderness()
    sync_service_interiors()
    sync_quest_runtime()
    sync_guild_economy()
    sync_guard_npc()
    _register_narrator_layer()


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
