"""Author-controlled protection encounter using the real party and combat owners."""

import json
from pathlib import Path

from django.db import transaction
from evennia.utils.create import create_object

from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC
from world.imports.loader import instantiate_character
from world.observability import log_info
from world.rules.combat_session import engage, read_session
from world.rules.party import join_party, party_ids
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort


def prepare_protection_demo(player, *, npc_record=None, enemy_name="城郊野獸"):
    """Start a real encounter beside an unbound player in a reachable room.

    The author places the player at the guild's reachable approach beforehand.
    Subsequent attack, dismissal, downtime and revisit use ordinary commands.
    No victory, memory, or response is fabricated by setup.
    """
    if player.location is None or party_ids(player) or read_session(player) is not None:
        raise ValueError("Demo requires a located player with no party or active combat.")
    if npc_record is None:
        path = Path(__file__).parents[1] / "imports/examples/yohanna_cooper.json"
        npc_record = json.loads(path.read_text(encoding="utf-8"))
    snapshots = {key: attribute_snapshot(player, key) for key in ("party", "active_combat")}
    prior_context = player.ndb.action_context
    npc = enemy = None
    try:
        with transaction.atomic():
            npc = instantiate_character(npc_record, typeclass=LLMNPC)
            npc.location = player.location
            npc.db.npc_offline_greeting = "木桶已經修好了。今天想聊些什麼？"
            enemy = create_object(Monster, key=enemy_name, location=player.location)
            # Resolve the lowest authored threat tier, rather than duplicating balance.
            from world.lore.monsters import MONSTER_TIER_REGISTRY

            enemy.threat_tier = next(iter(MONSTER_TIER_REGISTRY))
            enemy.apply_monster_tier()
            join_party(npc, player)
            engage(player, enemy)
            transaction.on_commit(lambda: log_info("protection_demo_prepared", context={
                "char": player.pk, "npc": npc.pk, "enemy": enemy.pk,
                "room": player.location.pk,
            }))
    except Exception:
        from world.rules.clock import _flush_deleted_instance
        from world.rules.skip_safety import unregister_active_battlefield

        for entity in (player, npc, enemy):
            if entity is not None:
                unregister_active_battlefield(entity)
        # Transaction rollback restores rows, not Evennia's object/room caches.
        for entity in (npc, enemy):
            if entity is not None:
                _flush_deleted_instance(entity)
        player.location.contents_cache.init()
        for key, snapshot in snapshots.items():
            restore_attribute_best_effort(player, key, snapshot)
        player.ndb.action_context = prior_context
        raise
    return npc, enemy
