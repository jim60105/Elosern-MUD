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


def _register_npc_dialogue_layer():
    """Register the npc_dialogue layer's guardrail hooks.

    Called from ``at_server_start`` for the same reason as
    ``_register_narrator_layer``: ``world.ai.guardrail`` captures the logger at
    import time, so registration must happen after ``evennia._init()``. The
    registration is boot-tolerant: a foreign leftover npc_dialogue registration
    (a conflicting fallback/validator, or a conflicting output schema) must
    never abort server startup; the reply gate still fails loudly on a
    non-npc_dialogue registration, so correctness is preserved.
    """
    from evennia import logger
    from world.ai.guardrail import GuardrailRegistrationError
    from world.ai.npc_dialogue import register_npc_dialogue
    from world.ai.schemas.registry import DuplicateSchemaError

    try:
        register_npc_dialogue()
    except (GuardrailRegistrationError, DuplicateSchemaError) as exc:
        logger.log_warn(f"npc_dialogue registration skipped at server start: {exc}")


def _register_scenario_director_layer():
    """Register the scenario_director layer's guardrail hooks.

    Called from ``at_server_start`` for the same reason as
    ``_register_narrator_layer``: ``world.ai.guardrail`` captures the logger at
    import time, so registration must happen after ``evennia._init()``. The
    registration is boot-tolerant: a foreign leftover scenario_director
    registration (a conflicting fallback/validator, or a conflicting output
    schema) must never abort server startup; the proposal gate still fails
    loudly on a non-scenario_director registration, so correctness is
    preserved.
    """
    from evennia import logger
    from world.ai.guardrail import GuardrailRegistrationError
    from world.ai.scenario_director import register_scenario_director
    from world.ai.schemas.registry import DuplicateSchemaError

    try:
        register_scenario_director()
    except (GuardrailRegistrationError, DuplicateSchemaError) as exc:
        logger.log_warn(f"scenario_director registration skipped at server start: {exc}")


def _register_character_creation_layer():
    """Register the character_creation layer's guardrail hooks.

    Called from ``at_server_start`` for the same reason as
    ``_register_narrator_layer``: ``world.ai.guardrail`` captures the logger at
    import time, so registration must happen after ``evennia._init()``. The
    registration is boot-tolerant: a foreign leftover character_creation
    registration (a conflicting fallback/validator, or a conflicting output
    schema) must never abort server startup; the proposal gate still fails
    loudly on a non-character_creation registration, so correctness is
    preserved.
    """
    from evennia import logger
    from world.ai.character_creation import register_character_creation
    from world.ai.guardrail import GuardrailRegistrationError
    from world.ai.schemas.registry import DuplicateSchemaError

    try:
        register_character_creation()
    except (GuardrailRegistrationError, DuplicateSchemaError) as exc:
        logger.log_warn(f"character_creation registration skipped at server start: {exc}")


def _register_scene_flavor_layer():
    """Register the scene-flavor layer's guardrail hooks.

    Called from ``at_server_start`` for the same reason as
    ``_register_narrator_layer``: ``world.ai.guardrail`` captures the logger at
    import time, so registration must happen after ``evennia._init()``. The
    registration is boot-tolerant: a foreign leftover scene-flavor registration
    (a conflicting fallback or validator under the layer's profile key) must
    never abort server startup; the flavor gate still fails loudly on a
    non-scene-flavor registration, so correctness is preserved.

    Note for maintainers: a repository guarded test asserts that the
    deterministic scene materializer's literal profile key never appears in this
    file's source (startup must not resync its generated registry). Keep that
    key out of this module's text — the seam imports only the layer.
    """
    from evennia import logger
    from world.ai.guardrail import GuardrailRegistrationError
    from world.ai.scene_flavor import register_scene_flavor

    try:
        register_scene_flavor()
    except GuardrailRegistrationError as exc:
        logger.log_warn(f"scene_flavor registration skipped at server start: {exc}")


def _register_action_options_layer():
    """Register the action_options layer's guardrail hooks.

    Called from ``at_server_start`` for the same reason as
    ``_register_narrator_layer``: ``world.ai.guardrail`` captures the logger at
    import time, so registration must happen after ``evennia._init()``. The
    registration is boot-tolerant: a foreign leftover action_options
    registration (a conflicting fallback or output schema) must never abort
    server startup. Unlike the other layers, the ``action_options`` profile
    slot (``LAYER_NAMES``) arrives with the prompts change, so a branch that
    lands this wiring first must also survive ``UnknownLayerError`` with a
    bounded warning-and-skip — the same warning-and-skip applies to
    ``DuplicateSchemaError``/``GuardrailRegistrationError`` as with the other
    layers. The proposal gate still fails loudly on a non-action_options
    registration, so correctness is preserved.
    """
    from evennia import logger
    from world.ai.action_options import register_action_options
    from world.ai.guardrail import GuardrailRegistrationError
    from world.ai.profiles import UnknownLayerError
    from world.ai.schemas.registry import DuplicateSchemaError

    try:
        register_action_options()
    except (GuardrailRegistrationError, DuplicateSchemaError, UnknownLayerError) as exc:
        logger.log_warn(f"action_options registration skipped at server start: {exc}")


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from world.lore.sync import sync_all
    from world.maps.bootstrap import (
        sync_grid,
        sync_limbo,
        sync_service_interiors,
        sync_wilderness,
    )
    from world.quests.bootstrap import sync_quest_runtime
    from world.rules.clock import get_world_clock
    from world.rules.guild_economy import restore_persisted_sessions, sync_guild_economy
    from world.rules.npc_schedules import sync_npc_schedules
    from world.rules.onboarding import sync_guard_npc

    # Deterministic startup owns the world-clock singleton; presentation reads
    # only through read_world_clock() and must never create it.
    get_world_clock()
    sync_all()
    sync_limbo()
    sync_grid()
    # Every world-event clock source must be registered before any startup
    # operation can advance time: the service interiors, quest runtime, guild
    # economy, guard, and NPC-schedule syncs all move ahead of session
    # restoration so a recovery settlement runs the complete stage set
    # (fix-startup-clock-source-order D1).
    sync_service_interiors()
    sync_quest_runtime()
    sync_guild_economy()
    sync_guard_npc()
    sync_npc_schedules()
    # Restore persisted combat sessions BEFORE wilderness population
    # reconciliation: a defeated population monster still referenced by a
    # committed session must not be deleted or respawned first
    # (fix-startup-session-restore-order D1).
    restore_persisted_sessions()
    sync_wilderness()

    # Prompt library: validate every YAML prompt file and mark broken keys
    # unavailable. Failures are bounded per key and logged; server startup
    # always continues (design D3), so a broken prompt never takes the
    # deterministic game offline. The wrapper is a last-resort guard: even an
    # unforeseen loader failure must not abort startup.
    from evennia import logger as evennia_logger
    from world.prompts.loader import load_prompt_library

    try:
        load_prompt_library()
    except Exception as exc:
        evennia_logger.log_err(
            f"prompt library load failed; continuing with degraded prompts: {exc}"
        )

    _register_narrator_layer()
    _register_npc_dialogue_layer()
    _register_scenario_director_layer()
    _register_character_creation_layer()
    _register_scene_flavor_layer()
    _register_action_options_layer()

    # Deterministic art-assets startup sync: ensure a record for every scene
    # and generic-monster subject, then recover explicit named portrait
    # policies (idempotent; a failure is bounded and never aborts startup).
    from world.art.service import art_sync_all

    art_sync_all()

    # WebClient art completion push: re-entrant-safe via a stable dispatch UID.
    from web.webclient.presentation.art_push import connect_art_push

    connect_art_push()


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
