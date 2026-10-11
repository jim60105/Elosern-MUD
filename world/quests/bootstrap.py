"""Server-startup composition root for the deterministic quest runtime (D-7)."""

from .catalog import register_catalog
from .compile import payload_to_registrations, register_restored_quest
from .deadlines import (
    settle_quest_deadlines,
    snapshot_quest_deadline_surfaces,
)
from .generated_quest_store import list_payloads
from .planner import quest_event_effect_planner
from world.rules.action import register_event_effect_planner
from world.rules.clock import register_event_source


def restore_generated_quests() -> None:
    """Repopulate the process-local registries from the durable store.

    Called at startup before any player quest-log read (D3): every stored
    payload is reconstructed into its compiled aggregate and registered
    through its namespace's own writer -- a guild offer into the guild offer
    registry, a private commission into the quest issuance registry (the
    ``QuestIssuance`` constructor requires the registered definition, so the
    definition always registers first). Equal registrations are no-ops, so
    repeated restarts are idempotent and a crash mid-restore self-heals on
    the next start; a payload that fails to reconstruct or register raises
    loudly instead of being silently dropped.
    """
    for payload in list_payloads():
        register_restored_quest(payload_to_registrations(payload))


def restore_scene_packages() -> None:
    """Republish the durable scene packages' definition views and live issuances.

    Runs after :func:`restore_generated_quests` so an activated package
    commission can register against an already-registered definition. Package
    definitions and spawn requirements are re-registered first (an equal
    registration is a no-op); only then are the grants whose issuance was
    actually activated re-registered, so a merely planned symbolic declaration
    never becomes runtime authority across a restart (design §5.1).
    """
    from world.rules.quest_issuance import Settlement

    from . import scene_store
    from .compile import publish_activated_commission
    from .encounters import _publish_definition_views_for
    from .scene_package import validate_scene_package

    for row in scene_store.list_packages():
        if row.status != scene_store.PACKAGE_STATUS_PUBLISHED:
            continue
        definition = validate_scene_package(row.payload)
        _publish_definition_views_for(row, definition)
        for grant in scene_store.list_commission_grants(row.package_id):
            if not grant.registered:
                continue
            if grant.npc_id <= 0:
                raise scene_store.SceneStoreError(
                    f"commission {grant.definition_key!r} of role "
                    f"{grant.role_id!r} is marked registered without its assigned "
                    "actor; refusing to fabricate runtime authority"
                )
            publish_activated_commission(
                grant.definition_key,
                grant.issuer_key,
                definition.quest.reward,
                Settlement.AUTO,
            )


def sync_quest_runtime() -> None:
    """Restore generated content, register catalog content, the action planner,
    and deadline settlement.

    Idempotent: repeated server starts replace the planner by name and
    overwrite the clock source, and equal definition registrations are no-ops.
    """
    restore_generated_quests()
    restore_scene_packages()
    register_catalog()
    register_event_effect_planner("quest", quest_event_effect_planner)
    register_event_source(
        "quest_deadlines",
        settle_quest_deadlines,
        snapshot_quest_deadline_surfaces,
    )
