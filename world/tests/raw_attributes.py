"""Rollback-proof raw Attribute reads for the world test suites.

Several Evennia integration suites must prove the DATABASE row behind an
Attribute after a rollback (fault-injection persistence tests), not the
idmapper-cached model instance: a passed assertion against the cached model
would prove nothing about what survived the transaction. The shared probe
reads through the ``db_attributes`` M2M join with pure SQL (``values_list``
on the through rows), exactly as the six per-suite ``_raw_attribute``
methods it replaces did.
"""

from __future__ import annotations


def raw_attribute_value(obj, key):
    """The raw stored Attribute row value for ``key``, read via SQL only.

    Reads through the ``db_attributes`` M2M join without instantiating any
    idmapper-cached Attribute model, so the value proves the database row
    (after rollback) rather than any in-process cache.
    """
    row = (
        obj.db_attributes.through.objects.filter(
            objectdb_id=obj.pk, attribute__db_key=key
        )
        .values_list("attribute__db_value", flat=True)
        .first()
    )
    return None if row is None else row