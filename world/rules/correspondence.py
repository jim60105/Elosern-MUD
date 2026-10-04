"""Restricted remote relationship validation; no dialogue or quest appliers."""

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules.affinity import AffinitySource, apply_affinity_change


def apply_letter_relationship(npc, correspondent, delta):
    """Use the existing bounded interaction budget without a co-location gate."""
    if (
        not isinstance(npc, NPC) or not isinstance(correspondent, PlayerCharacter)
        or isinstance(delta, bool) or not isinstance(delta, int) or not 0 <= delta <= 10
    ):
        return None
    return apply_affinity_change(npc, correspondent, AffinitySource.AI_DIALOGUE, delta)
