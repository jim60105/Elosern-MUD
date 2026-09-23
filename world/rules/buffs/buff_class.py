"""The generic buff class and divert-budget accessors.

Extracted from :mod:`world.rules.buffs` as the instance layer of the package:
:class:`RulebookBuff` is the single Evennia buff class every definition key is
mounted through, and the divert accessors read/write its per-instance budget.
"""

from typing import Any

try:
    from evennia.contrib.rpg.buffs import BaseBuff
except Exception:  # pragma: no cover # observability: ignore R2: fallback when django settings not loaded
    class BaseBuff:  # type: ignore[no-redef]
        pass

from .definitions import BUFF_DEFINITIONS, get_recovery_policy


def get_divert_consumed(buff: Any) -> int:
    """Return the consumed divert budget for one buff instance."""
    val = getattr(buff, "divert_consumed", None)
    if val is None and hasattr(buff, "cache") and isinstance(buff.cache, dict):
        val = buff.cache.get("divert_consumed")
    if val is None and hasattr(buff, "handler") and hasattr(buff.handler, "buffcache"):
        entry = buff.handler.buffcache.get(getattr(buff, "buffkey", None))
        if isinstance(entry, dict):
            val = entry.get("divert_consumed")
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return 0
    return max(0, int(val))


def update_divert_consumed(buff: Any, consumed: int) -> None:
    """Update the consumed divert budget on a buff instance cache."""
    consumed_int = max(0, int(consumed))
    if hasattr(buff, "cache") and isinstance(buff.cache, dict):
        buff.cache["divert_consumed"] = consumed_int
    if hasattr(buff, "handler") and hasattr(buff.handler, "buffcache"):
        key = getattr(buff, "buffkey", None)
        if key and key in buff.handler.buffcache:
            buff.handler.buffcache[key]["divert_consumed"] = consumed_int
    try:
        setattr(buff, "divert_consumed", consumed_int)
    except Exception:  # observability: ignore R2: optional write-through on foreign test instances
        pass


def get_charges(buff: Any, default: int = 0) -> int:
    """Return the remaining charge pool of one buff instance.

    The charge-on-event counter (church design §5.7) rides the same persisted
    cache channels as the divert budget; ``default`` is used when the instance
    has never recorded a value (a freshly mounted charge-carrying buff falls
    back to its declared pool). Unreadable values fail closed to the default.
    """
    val = getattr(buff, "charges", None)
    if val is None and hasattr(buff, "cache") and isinstance(buff.cache, dict):
        val = buff.cache.get("charges")
    if val is None and hasattr(buff, "handler") and hasattr(buff.handler, "buffcache"):
        entry = buff.handler.buffcache.get(getattr(buff, "buffkey", None))
        if isinstance(entry, dict):
            val = entry.get("charges")
    if isinstance(val, bool) or not isinstance(val, int) or val < 0:
        return default
    return val


def update_charges(buff: Any, charges: int) -> None:
    """Persist the remaining charge pool on a buff instance cache."""
    charges_int = max(0, int(charges))
    if hasattr(buff, "cache") and isinstance(buff.cache, dict):
        buff.cache["charges"] = charges_int
    if hasattr(buff, "handler") and hasattr(buff.handler, "buffcache"):
        key = getattr(buff, "buffkey", None)
        if key and key in buff.handler.buffcache:
            buff.handler.buffcache[key]["charges"] = charges_int
    try:
        setattr(buff, "charges", charges_int)
    except Exception:  # observability: ignore R2: optional write-through on foreign test instances
        pass


class RulebookBuff(BaseBuff):
    """One generic buff class parameterized by persistent definition data."""

    key = "rulebook"
    duration = -1
    tickrate = 0
    refresh = True
    unique = True

    def at_tick(self, initial: bool = False, *args, **kwargs) -> None:
        """Apply this definition's rate modifier when explicitly ticked."""
        # Imported function-locally: ``rates`` depends on this module for its
        # instance type annotation, so the cycle stays out of import time.
        from .rates import _apply_rate_modifier

        rate = BUFF_DEFINITIONS[self.definition_key].modifiers.get("rate")
        recovery = get_recovery_policy(BUFF_DEFINITIONS[self.definition_key])
        if rate and recovery is None:
            source_tier = getattr(self, "source_tier", None) or "學徒"
            source_skill = getattr(self, "source_skill", None)
            source_pk = None
            if "caster_share" in rate:
                source_pk = getattr(self, "source_pk", None)
                if source_pk is None and hasattr(self, "cache") and isinstance(self.cache, dict):
                    source_pk = self.cache.get("source_pk")
            _apply_rate_modifier(
                self.owner,
                rate,
                source_tier=source_tier,
                source_skill=source_skill,
                source_pk=source_pk,
            )
