"""Handler-free skill-ownership fact read (saintess-vessel D2a).

One neutral leaf for the rules layer's ownership-gated settlement branches
(``sexual_state.lifecycle.decay_tick`` and ``pleasure.saintess_trickle_step``)
to ask whether an entity's STORED skill lists name one key, without ever
mounting ``entity.skills`` — the same no-create discipline
``stored_sexual_reads`` and ``dual_wielding_from_storage`` establish for the
sexual and equipment facts. Malformed storage fails closed to ``False``:
settlement branches must degrade to the non-holder path, never raise inside
the clock transaction.

Deliberately the raw stored lists only — no innate keys, no unlocked sexual
acts, no conferred grants: a qualifier passive like ``saintess_vessel`` is
non-conferrable and never unlocked, so the stored passive list is exactly its
ownership surface. Evennia deserializes stored list attributes as
``_SaverList`` (a ``Sequence``, NOT a ``list`` subclass — the same note
``items/reads.py`` and ``progression/_scaling.py`` record), so the check
accepts any non-string sequence plus the plain set/tuple forms the original
callers could hand it; every other stored shape fails closed.
"""

from collections.abc import Mapping, Sequence
from typing import Any


def owns_stored_skill(entity: Any, skill_key: str) -> bool:
    """Whether the entity's stored skill lists name one key, without a handler."""
    raw = getattr(entity, "db", None)
    stored = getattr(raw, "skills", None) if raw is not None else None
    if not isinstance(stored, Mapping):
        return False
    for field in ("active", "passive"):
        values = stored.get(field)
        if (
            (isinstance(values, Sequence) and not isinstance(values, (str, bytes)))
            or isinstance(values, (set, frozenset))
        ) and skill_key in values:
            return True
    return False
