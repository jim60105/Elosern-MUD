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

import importlib
import time

from world.observability import log_error, log_info, log_warn

# Patchable monotonic clock seam for startup timing tests.
_startup_clock = time.monotonic


def _late(module: str, name: str):
    """Import ``module`` at call time and run its ``name`` attribute.

    Keeps each dependency's import at its original pre-refactor execution
    point (title planner, prompt loader, art sync, art push), so an
    import-time failure in a late dependency can never block an earlier step.
    Uses the real import machinery (not the patchable
    ``importlib.import_module`` seam) so the attribute lookup still resolves
    test-patched bindings on the genuinely imported module.
    """
    return getattr(__import__(module, fromlist=(name,)), name)()

# Canonical ordered startup step catalog (change add-observability-lint-gate,
# design D7). The order IS the contract: clock-source registration must
# precede session restoration, restoration must precede wilderness sync, and
# quest runtime must run after the lore/map syncs. Guard tests assert against
# this catalog (behaviorally, via stubs) instead of source text.
STARTUP_STEP_ORDER: tuple[str, ...] = (
    "world_clock_init",
    "equipment_rulebook_validation",
    "sync_all",
    "sync_limbo",
    "sync_grid",
    "sync_service_interiors",
    "sync_quest_runtime",
    "sync_guild_economy",
    "sync_npc_schedules",
    "register_title_planner",
    "restore_persisted_sessions",
    "sync_wilderness",
    "load_prompt_library",
    "register_narrator_layer",
    "register_npc_dialogue_layer",
    "register_scenario_director_layer",
    "register_character_creation_layer",
    "register_scene_flavor_layer",
    "register_action_options_layer",
    "register_title_nomination_layer",
    "register_nomination_triggers",
    "art_sync_all",
    "connect_art_push",
)

# Any-unexpected-error tolerance, used by steps that were broadly guarded
# before the observability refactor (prompt library, nomination triggers).
_ALL_ERRORS: tuple[type[BaseException], ...] = (Exception,)


def _startup_step(
    name: str,
    run,
    *,
    fail_loud: bool = True,
    tolerant_on=(),
    degrade_level: str = "warn",
) -> None:
    """Run one catalog step with timing, one event, and preserved semantics.

    Success emits exactly one ``startup_step`` info event (``step``, ``ms``).
    Fail-loud steps log ``startup_step_failed`` with the exception chain and
    re-raise: the deterministic startup must not partially boot. Boot-tolerant
    steps (``fail_loud=False``) catch exactly the ``tolerant_on`` classes
    (a tuple, or a zero-argument callable resolving one lazily so the
    conflict classes are not imported until a step actually fails — the
    pre-refactor helpers imported them only at their own execution point), emit a structured
    ``startup_step_degraded`` with ``step`` and ``reason`` context plus the
    exception chain at ``degrade_level``, and let startup continue — at the
    level the pre-refactor site logged (prompt library at error, registration
    skips at warn). Any other exception propagates unlogged, exactly as
    before the refactor. The wrapper never re-orders steps.

    A step callable may also self-report a tolerated skip by returning
    ``False`` (the registration seams do this, so a direct call keeps the
    pre-refactor swallow-and-warn contract); the wrapper then emits no
    ``startup_step`` success event for it.
    """
    started = _startup_clock()
    try:
        result = run()
    except Exception as exc:
        classes = tolerant_on() if callable(tolerant_on) else tolerant_on
        if not isinstance(exc, classes):
            if fail_loud:
                log_error("startup_step_failed", exc=exc, context={"step": name})
            raise
        emit = log_error if degrade_level == "error" else log_warn
        emit(
            "startup_step_degraded",
            exc=exc,
            context={
                "step": name,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        return
    if result is False:
        return
    log_info(
        "startup_step",
        context={"step": name, "ms": int((_startup_clock() - started) * 1000)},
    )


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def _conflict_classes(*, schema: bool = False, profile: bool = False):
    """Resolve the tolerated registration-conflict classes (pre-refactor, the
    registration helpers imported them inside their own bodies; resolving them
    lazily keeps those imports off the path of every earlier startup step).
    """
    from world.ai.guardrail import GuardrailRegistrationError

    classes: list[type[BaseException]] = [GuardrailRegistrationError]
    if schema:
        from world.ai.schemas.registry import DuplicateSchemaError

        classes.append(DuplicateSchemaError)
    if profile:
        from world.ai.profiles import UnknownLayerError

        classes.append(UnknownLayerError)
    return tuple(classes)


def _tolerant_register(name: str, register, *, schema: bool = False, profile: bool = False) -> bool:
    """Register one guardrail layer, preserving the seam-level tolerance contract.

    The registration seams are called both from ``at_server_start`` (through
    ``_startup_step``) and directly by guarded tests that assert a foreign
    leftover registration never raises. The tolerance therefore lives here, at
    the seam: a tolerated conflict class is swallowed with a structured
    ``startup_step_degraded`` warn (``step``, ``reason``, exception chain), and
    ``False`` is returned so the wrapper skips its success event. Anything else
    propagates unchanged.
    """
    classes = _conflict_classes(schema=schema, profile=profile)
    try:
        register()
    except classes as exc:
        log_warn(
            "startup_step_degraded",
            exc=exc,
            context={"step": name, "reason": f"{type(exc).__name__}: {exc}"},
        )
        return False
    return True


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
    from world.ai.narrator import register_narrator
    from world.rules.event_log import render_plain_text

    return _tolerant_register(
        "register_narrator_layer",
        lambda: register_narrator(
            lambda event_logs: "\n".join(render_plain_text(log) for log in event_logs)
        ),
    )


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
    from world.ai.npc_dialogue import register_npc_dialogue

    return _tolerant_register(
        "register_npc_dialogue_layer", register_npc_dialogue, schema=True
    )


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
    from world.ai.scenario_director import register_scenario_director

    return _tolerant_register(
        "register_scenario_director_layer", register_scenario_director, schema=True
    )


def _register_character_creation_layer():
    """Register the character_creation layer's guardrail hooks.

    Called from ``at_server_start`` for the same reason as
    ``_register_narrator_layer``: ``world.ai.guardrail`` captures the logger at
    import time, so registration must happen after ``evennia._init()``. The
    registration is boot-tolerant: a foreign leftover character_creation
    registration (a conflicting fallback/validator, or a conflicting output
    schema) must never abort server startup; the proposal gate still fails
    loudly on a non-character_creation registration, so correctness is
    preserved. The tolerance lives in ``_tolerant_register`` so direct seam
    calls keep the same boot-tolerant contract.
    """
    from world.ai.character_creation import register_character_creation

    return _tolerant_register(
        "register_character_creation_layer", register_character_creation, schema=True
    )


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
    from world.ai.scene_flavor import register_scene_flavor

    return _tolerant_register("register_scene_flavor_layer", register_scene_flavor)


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
    from world.ai.action_options import register_action_options

    return _tolerant_register(
        "register_action_options_layer", register_action_options, schema=True, profile=True
    )


def _register_title_nomination_layer():
    """Register the title_nomination layer's guardrail hooks.

    Called from ``at_server_start`` for the same reason as
    ``_register_narrator_layer``: ``world.ai.guardrail`` captures the logger at
    import time, so registration must happen after ``evennia._init()``. The
    registration is boot-tolerant: a foreign leftover title_nomination
    registration (a conflicting fallback or output schema) must never abort
    server startup; the proposal gate still fails loudly on a
    non-title_nomination registration, so correctness is preserved.
    """
    from world.ai.title_nomination import register_title_nomination

    return _tolerant_register(
        "register_title_nomination_layer", register_title_nomination, schema=True
    )


def _register_nomination_triggers():
    """Install the epithet-nomination rest-point trigger observers (change G).

    The composition-root service registers the exam-pass and quest-completion
    observers (and owns the schedule path); every rest point silently no-ops
    while the LLM is offline, so this wiring is boot-tolerant with a bounded
    warning: a failure here can never take the deterministic game offline.
    The tolerance (any error) lives in the ``_startup_step`` wrapper.
    """
    from server.title_nomination_service import register_nomination_triggers

    register_nomination_triggers()


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.

    Every operation runs as a ``_startup_step`` from the ordered catalog
    above: one timed ``startup_step`` event per success, structured degrade
    events for the boot-tolerant classes, and log-then-raise for fail-loud
    steps. The call order below IS ``STARTUP_STEP_ORDER``; guard tests assert
    it behaviorally.
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

    # Per-layer tolerated registration-conflict classes, resolved lazily at
    # first failure exactly like the pre-refactor helper-local imports.

    # Deterministic startup owns the world-clock singleton; presentation reads
    # only through read_world_clock() and must never create it.
    _startup_step("world_clock_init", get_world_clock)
    # Fail-loud equipment-effect rulebook validation (add-equipment-effect-
    # rulebook D4): the only sanctioned startup consumer of the loader. The
    # module import itself validates the canonical rulebook; a malformed
    # roster aborts boot before any world sync can persist partial state.
    _startup_step(
        "equipment_rulebook_validation",
        lambda: importlib.import_module("world.rules.equipment_effects"),
    )
    _startup_step("sync_all", sync_all)
    _startup_step("sync_limbo", sync_limbo)
    _startup_step("sync_grid", sync_grid)
    # Every world-event clock source must be registered before any startup
    # operation can advance time: the service interiors, quest runtime, guild
    # economy, and NPC-schedule syncs all move ahead of session
    # restoration so a recovery settlement runs the complete stage set
    # (fix-startup-clock-source-order D1).
    _startup_step("sync_service_interiors", sync_service_interiors)
    _startup_step("sync_quest_runtime", sync_quest_runtime)
    _startup_step("sync_guild_economy", sync_guild_economy)
    _startup_step("sync_npc_schedules", sync_npc_schedules)
    # The title event-effect planner derives fixed-title grants from committed
    # actions; like the quest planner it must be registered before any player
    # action resolves (idempotent).
    _startup_step(
        "register_title_planner",
        lambda: _late("world.rules.titles", "register_title_planner"),
    )
    # Restore persisted combat sessions BEFORE wilderness population
    # reconciliation: a defeated population monster still referenced by a
    # committed session must not be deleted or respawned first
    # (fix-startup-session-restore-order D1).
    _startup_step("restore_persisted_sessions", restore_persisted_sessions)
    _startup_step("sync_wilderness", sync_wilderness)

    # Prompt library: validate every YAML prompt file and mark broken keys
    # unavailable. Failures are bounded per key and logged; server startup
    # always continues (design D3), so a broken prompt never takes the
    # deterministic game offline. The wrapper is a last-resort guard: even an
    # unforeseen loader failure must not abort startup (degrade at error
    # level, matching the pre-refactor log_err).
    _startup_step(
        "load_prompt_library",
        lambda: _late("world.prompts.loader", "load_prompt_library"),
        fail_loud=False,
        tolerant_on=_ALL_ERRORS,
        degrade_level="error",
    )

    # Guardrail-layer registrations: each seam is boot-tolerant for its
    # conflict classes via ``_tolerant_register`` (emitting its own
    # ``startup_step_degraded`` warn and reporting False); any other error
    # propagates unlogged, exactly as pre-refactor.
    _startup_step("register_narrator_layer", _register_narrator_layer, fail_loud=False)
    _startup_step(
        "register_npc_dialogue_layer", _register_npc_dialogue_layer, fail_loud=False
    )
    _startup_step(
        "register_scenario_director_layer",
        _register_scenario_director_layer,
        fail_loud=False,
    )
    _startup_step(
        "register_character_creation_layer",
        _register_character_creation_layer,
        fail_loud=False,
    )
    _startup_step("register_scene_flavor_layer", _register_scene_flavor_layer, fail_loud=False)
    _startup_step(
        "register_action_options_layer", _register_action_options_layer, fail_loud=False
    )
    _startup_step(
        "register_title_nomination_layer",
        _register_title_nomination_layer,
        fail_loud=False,
    )
    # Nomination triggers: any failure here can never take the deterministic
    # game offline (pre-refactor caught Exception broadly).
    _startup_step(
        "register_nomination_triggers",
        _register_nomination_triggers,
        fail_loud=False,
        tolerant_on=_ALL_ERRORS,
    )

    # Deterministic art-assets startup sync: ensure a record for every scene
    # and generic-monster subject, then recover explicit named portrait
    # policies (idempotent; failures are bounded internally, so the wrapper
    # keeps the pre-refactor fail-loud posture for unforeseen leaks).
    _startup_step("art_sync_all", lambda: _late("world.art.service", "art_sync_all"))

    # WebClient art completion push: re-entrant-safe via a stable dispatch UID.
    _startup_step(
        "connect_art_push",
        lambda: _late("web.webclient.presentation.art_push", "connect_art_push"),
    )


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
