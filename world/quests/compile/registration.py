"""All-or-nothing, durable-first registration publishing (quest-runtime D-2/D-3).

The write half of the ``world.quests.compile`` package. ``register_generated_quest``
appends the compiled payload to the durable store FIRST and only then
publishes through the shared ``_publish_registration``;
``register_restored_quest`` publishes a startup-restore payload without
touching the store. Every ``SCENE_REQUIREMENT_REGISTRY`` write lives in this
module, preserving the single-writer boundary the repository contract tests
assert.
"""

from world.quests.compile.contracts import (
    CompiledQuest,
    IssuanceDescriptor,
    SCENE_REQUIREMENT_REGISTRY,
    StageSpawnRequirement,
    _reject,
)
from world.quests.compile.payload import _compiled_to_payload
from world.quests.generated_quest_store import (
    append_payload as append_generated_quest_payload,
    remove_payload as remove_generated_quest_payload,
)
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    ObjectiveKind,
    QuestDefinition,
    register_quest_definition,
)
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
    register_guild_offer,
)
from world.rules.quest_issuance import (
    QUEST_ISSUANCE_REGISTRY,
    QuestIssuance,
    parse_issuer_key,
    register_quest_issuance,
)


def _publish_registration(
    definition: QuestDefinition,
    descriptor: IssuanceDescriptor,
    reward: QuestReward,
    requirements: tuple[StageSpawnRequirement, ...],
) -> None:
    """Preflight every registry, then write one registration all-or-nothing.

    The single namespace-dispatching publication both registration paths use
    (design D1): a guild issuance writes a ``GuildQuestOffer`` through
    ``register_guild_offer`` and a character issuance writes a
    ``QuestIssuance`` through ``register_quest_issuance``, so neither store
    gains a second writer. The preflight checks the definition, the
    namespace's own store, and the spawn-requirement entry before writing any
    of them; the writes then go definition first, issuance second (the
    ``QuestIssuance`` constructor requires the registered definition), and
    the requirements last, and a defensive failure after preflight rolls back
    every entry this call added.
    """
    parsed = parse_issuer_key(descriptor.issuer_key)
    offer: GuildQuestOffer | None = None
    offer_current: GuildQuestOffer | None = None
    issuance_current: QuestIssuance | None = None
    if parsed.namespace == "guild":
        offer = GuildQuestOffer(
            definition_key=definition.key,
            issuer_branch_key=parsed.remainder,
            reward=reward,
        )
        offer_current = GUILD_OFFER_REGISTRY.get((definition.key, parsed.remainder))
    else:
        issuance_current = QUEST_ISSUANCE_REGISTRY.get(
            (definition.key, descriptor.issuer_key)
        )
    definition_current = QUEST_DEFINITION_REGISTRY.get(definition.key)
    requirement_current = SCENE_REQUIREMENT_REGISTRY.get(definition.key)
    if definition_current is not None and definition_current != definition:
        _reject(f"conflicting definition already registered under {definition.key!r}")
    if offer is not None and offer_current is not None and offer_current != offer:
        _reject(
            f"conflicting offer already registered for {definition.key!r} "
            f"at branch {parsed.remainder!r}"
        )
    if issuance_current is not None and (
        issuance_current.reward != reward
        or issuance_current.settlement != descriptor.settlement
    ):
        _reject(
            f"conflicting issuance already registered for {definition.key!r} "
            f"under {descriptor.issuer_key!r}"
        )
    if requirement_current is not None and requirement_current != requirements:
        _reject(
            f"conflicting spawn requirements already registered under "
            f"{definition.key!r}"
        )

    definition_added = definition_current is None
    offer_added = offer is not None and offer_current is None
    issuance_added = parsed.namespace == "npc" and issuance_current is None
    requirement_added = requirement_current is None
    try:
        register_quest_definition(definition)
        if offer is not None:
            register_guild_offer(offer)
        else:
            register_quest_issuance(
                QuestIssuance(
                    definition_key=definition.key,
                    issuer_key=descriptor.issuer_key,
                    reward=reward,
                    settlement=descriptor.settlement,
                )
            )
        SCENE_REQUIREMENT_REGISTRY[definition.key] = requirements
    except Exception:
        if definition_added:
            QUEST_DEFINITION_REGISTRY.pop(definition.key, None)
        if offer_added:
            GUILD_OFFER_REGISTRY.pop((definition.key, parsed.remainder), None)
        if issuance_added:
            QUEST_ISSUANCE_REGISTRY.pop(
                (definition.key, descriptor.issuer_key), None
            )
        if requirement_added:
            SCENE_REQUIREMENT_REGISTRY.pop(definition.key, None)
        raise


def register_restored_quest(compiled: CompiledQuest) -> None:
    """Register one durable-mirror payload's aggregate (design D3).

    The compile-boundary write used by startup restore. It preflights and
    writes exactly like ``register_generated_quest`` but never touches the
    durable store -- the payload being restored IS the store's content.
    Equal registrations are no-ops and conflicting content raises before any
    write, so repeated restarts keep exactly one entry per issuance while a
    malformed or conflicting payload fails loudly instead of leaving a
    definition registered without its issuance or requirements. Keeping every
    ``SCENE_REQUIREMENT_REGISTRY`` write inside this module preserves the
    single-writer boundary the repository contract tests assert.
    """
    _publish_registration(
        compiled.definition,
        compiled.issuance,
        compiled.reward,
        compiled.stage_requirements,
    )


def register_generated_quest(compiled: CompiledQuest) -> None:
    """Register one compiled definition, its issuance, and its spawn
    requirements all-or-nothing and durable-first.

    The compiled payload is appended to the durable generated-quest store
    FIRST (D2): a store failure aborts registration with no in-memory
    entries. Only after the append succeeds is the registration written
    through ``_publish_registration``; if any write still fails despite
    preflight (defensive), every entry this call added -- the definition, the
    issuance, the requirements, and the store payload -- is rolled back
    together, so a generated definition is never left registered without its
    durable mirror.
    """
    definition = compiled.definition
    for stage in definition.stages:
        if stage.objective.kind is ObjectiveKind.ESCORT:
            _reject(
                "ESCORT stages cannot be published until a protected-entity "
                "binding flow exists; the whole quest is refused"
            )
    payload_added = append_generated_quest_payload(_compiled_to_payload(compiled))
    try:
        _publish_registration(
            definition,
            compiled.issuance,
            compiled.reward,
            compiled.stage_requirements,
        )
    except Exception:
        if payload_added:
            remove_generated_quest_payload(
                definition.key, compiled.issuance.issuer_key
            )
        raise
