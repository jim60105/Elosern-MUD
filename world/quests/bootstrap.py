"""Server-startup composition root for the deterministic quest runtime (D-7)."""

from .catalog import register_catalog
from .compile import payload_to_registrations, register_restored_quest
from .deadlines import settle_quest_deadlines
from .generated_quest_store import list_payloads
from .planner import quest_event_effect_planner
from world.rules.action import register_event_effect_planner
from world.rules.clock import register_event_source


def restore_generated_quests() -> None:
    """Repopulate the three process-local registries from the durable store.

    Called at startup before any player quest-log read (D3): every stored
    payload is reconstructed and registered definition-first (offer validation
    requires the registered definition), then the offer and the spawn
    requirements. Equal registrations are no-ops and the requirement entry is
    written with ``setdefault``, so repeated restarts are idempotent and a
    crash mid-restore self-heals on the next start; a payload that fails to
    reconstruct or register raises loudly instead of being silently dropped.
    """
    for payload in list_payloads():
        definition, offer, requirements = payload_to_registrations(payload)
        register_restored_quest(definition, offer, requirements)


def sync_quest_runtime() -> None:
    """Restore generated content, register catalog content, the action planner,
    and deadline settlement.

    Idempotent: repeated server starts replace the planner by name and
    overwrite the clock source, and equal definition registrations are no-ops.
    """
    restore_generated_quests()
    register_catalog()
    register_event_effect_planner("quest", quest_event_effect_planner)
    register_event_source("quest_deadlines", settle_quest_deadlines)
