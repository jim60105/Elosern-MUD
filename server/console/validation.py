"""Non-creating console identities and explicit numeric validation."""

import re

from server.console.errors import ConsoleError


def integer(value, *, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ConsoleError("invalid_argument")
    return value


def text(value):
    if not isinstance(value, str) or not value:
        raise ConsoleError("invalid_argument")
    return value


def resolve_target(target, kinds=None):
    from evennia.objects.models import ObjectDB
    from typeclasses.characters import PlayerCharacter
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC
    from evennia import DefaultRoom

    if not isinstance(target, str) or re.fullmatch(r"#[1-9][0-9]*", target) is None:
        raise ConsoleError("invalid_argument")
    entity = ObjectDB.objects.filter(pk=int(target[1:])).first()
    if entity is None:
        raise ConsoleError("target_not_found")
    if kinds is not None:
        allowed = {"characters": PlayerCharacter, "monsters": Monster, "npcs": NPC, "rooms": DefaultRoom}
        # NPCs are not player characters, even when their lineage overlaps.
        kind = next((name for name in ("monsters", "npcs", "characters", "rooms") if isinstance(entity, allowed[name])), None)
        if kind not in kinds:
            raise ConsoleError("target_kind_mismatch")
    return entity
