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
accepts sequence/set collections the original callers and Evennia storage
produce (``_SaverList``, ``list``, ``tuple``, ``set``, ``frozenset``) while
rejecting every other shape: strings/bytes-like values can never name a
skill key, mappings are not ownership lists, and any container whose
membership test raises (e.g. a ``bytearray`` probed with a string) fails
closed to ``False`` — settlement branches must degrade to the non-holder
path, never raise inside the clock transaction.
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
        if isinstance(values, (str, bytes, bytearray, memoryview, Mapping)):
            continue
        try:
            if skill_key in values:
                return True
        except TypeError:
            # Not a membership-supporting container at all (int, None, ...):
            # malformed storage fails closed, never raises.
            continue
    return False
