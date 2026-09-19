"""Prompt assembly (pipeline design doc §3).

Builds the deterministic (system, user) message pair for one proposal from the
frozen ``ActionOptionsContext`` through the prompt library's two
``action_options`` keys. The same import discipline holds: no Evennia import,
no state writer, and no module-level logger binding at module time.
"""

from __future__ import annotations

import json
from typing import Any

from world.prompts.loader import render_prompt

from world.ai.action_options.context import ActionOptionsContext

# ==== Prompt assembly (pipeline design doc §3) ====


def _serialize_structured(value: Any) -> str:
    """Deterministic stable-key JSON with non-ASCII kept literal."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def build_action_options_prompt(
    context: ActionOptionsContext,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build the deterministic (system, user) message pair for one proposal.

    Both messages render through the prompt library's two ``action_options``
    keys: the system key with no substitution values (empty allowlist), the
    user key with exactly the seven serialized ``ActionOptionsContext`` fields
    (``leak_blocklist`` is never rendered). Structured fields are
    pre-serialized: NPC entries carry their stable positional ``npc_index`` so
    freeform cards reference a present person without the model typing an id,
    and the affordance list carries each entry's canonical ``action_id`` +
    typed params (navigation entries have no dispatcher code and are excluded).
    Identical input always produces byte-identical messages with no live entity
    references.
    """
    system = {"role": "system", "content": render_prompt("action_options.system")}
    npc_entries = [
        {
            "npc_index": index,
            "npc_id": entry.npc_id,
            "display_name": entry.display_name,
            "dialogue_key": entry.dialogue_key,
            "persona_digest": entry.persona_digest,
            "public_tier": entry.public_tier,
        }
        for index, entry in enumerate(context.npc_entries)
    ]
    monster_entries = [
        {
            "monster_id": entry.monster_id,
            "display_name": entry.display_name,
            "threat_tier": entry.threat_tier,
        }
        for entry in context.monster_entries
    ]
    affordances = [
        {
            "action_id": entry.action_id,
            "label": entry.label,
            "params": dict(entry.params or {}),
        }
        for entry in context.affordances
        if not entry.navigation
    ]
    user = {
        "role": "user",
        "content": render_prompt(
            "action_options.user",
            room_name=context.room_name,
            room_summary=context.room_summary,
            npc_entries=_serialize_structured(npc_entries),
            monster_entries=_serialize_structured(monster_entries),
            objective=context.objective or "",
            narrative_tail=context.narrative_tail,
            affordances=_serialize_structured(affordances),
        ),
    }
    return system, user
