"""Shared helpers and fixtures for the combat-session test modules."""

from evennia.utils.create import create_object

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster

from .combat_fixtures import BattlefieldIsolation


def _player(key="combat player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    # Human static magic_power at 術師 tier so element-gated spell casts pass.
    player.traits.magic_power.base = 30
    return player


def _monster(key="goblin", hp=100, atk=10):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = atk
    return monster


# Shipped ANY-faction AREA damage skill: with free target selection the
# player's own action can hit an ally-side companion in the seam flow.
SEAM_AREA_KEY = "wind_blade"
