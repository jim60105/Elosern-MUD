"""Server-startup composition root for the deterministic quest runtime (D-7)."""

from .catalog import register_catalog
from .deadlines import settle_quest_deadlines
from .planner import quest_event_effect_planner
from world.rules.action import register_event_effect_planner
from world.rules.clock import register_event_source


def sync_quest_runtime() -> None:
    """Register catalog content, the action planner, and deadline settlement.

    Idempotent: repeated server starts replace the planner by name and
    overwrite the clock source, and equal definition registrations are no-ops.
    """
    register_catalog()
    register_event_effect_planner("quest", quest_event_effect_planner)
    register_event_source("quest_deadlines", settle_quest_deadlines)