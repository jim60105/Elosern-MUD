"""Composition root bridging the ScenarioDirector to the quest compile boundary.

``request_generated_quest`` is the single production caller of
``world.ai.scenario_director.generate_quest_blueprint``. It lives in
``server/`` because that directory is the one place where both import
directions are legal under the repository contract tests: the deterministic
-path ban scans ``world/rules|maps|quests|commands`` and the transport boundary
scans ``world/ai/``, and ``server/`` is scanned by neither.

Every ``world.ai`` import is deferred into the call path so importing this
module at server startup cannot bind the guardrail's import-time ``None``
logger -- the same rule the narrator/dialogue registration seams follow. The
call bridges a guarded proposal (``generate_quest_blueprint``) to the
deterministic compile boundary (``compile_quest_blueprint`` +
``register_generated_quest``) and resolves to the registered ``CompiledQuest``,
never to ``None`` and never to an unregistered definition.
"""

from twisted.internet import defer


class NoSuitableTemplateError(RuntimeError):
    """No context-fitting template exists for the offline request.

    Raised at the composition boundary so deterministic ``commands/`` modules
    can surface a named rejection without importing ``world.ai``.
    """


class _OfflineStubClient:
    """A non-``None`` client injected when the ``scenario_director`` profile is
    disabled.

    The degrade path reaches the template draw before any transport work, so
    this stub is never called; its ``get_response`` fails loudly if it ever is,
    rather than silently half-opening a connection.
    """

    def get_response(self, descriptor):
        raise AssertionError(
            "offline stub client must never be called; the scenario_director "
            "degrades before any transport work"
        )


@defer.inlineCallbacks
def request_generated_quest(client=None, *, context):
    """Ask the director for one context-fitting quest and post its offer.

    Args:
        client: The injected client protocol, or ``None`` to build one from the
            ``scenario_director`` profile. When the profile is enabled an
            ``OpenAICompatClient`` is constructed; when it is disabled a stub
            is passed so the director's required-client gate is satisfied while
            the degrade path (which never touches the client) draws a
            context-fitting template.
        context: The caller's plain-data request: ``requested_type``,
            ``allowed_rank``, ``issuer_branch``, ``anchor``, and an optional
            ``note``.

    Returns:
        A Deferred resolving to the registered ``CompiledQuest``. On a degrade
        trigger the call resolves through the deterministic template pool like
        any other proposal; when no compatible template exists it errbacks with
        ``ScenarioDirectorTemplateError``.
    """
    if client is None:
        from world.ai.client import OpenAICompatClient
        from world.ai.profiles import get_profile

        profile = get_profile("scenario_director")
        if profile.enabled:
            client = OpenAICompatClient(profile)
        else:
            client = _OfflineStubClient()

    from world.ai.scenario_director import ScenarioDirectorTemplateError, generate_quest_blueprint
    from world.quests.compile import compile_quest_blueprint, register_generated_quest

    try:
        blueprint = yield generate_quest_blueprint(client, context=context)
    except ScenarioDirectorTemplateError as error:
        raise NoSuitableTemplateError(str(error)) from error
    compiled = compile_quest_blueprint(blueprint.to_payload())
    register_generated_quest(compiled)
    return compiled
