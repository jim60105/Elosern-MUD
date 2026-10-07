"""Universal raw inventory of any Evennia object (design §2/§3).

``raw_object`` lists every stored Attribute with its key, category and
converted value, every categorized Tag, the existing components (with the field
Attributes they own on the host), the typeclass path, the location and the
creation date. Nothing is provisioned, normalized or repaired: an object
outside every curated kind is inspectable too, which is why this projection
never assumes a curated shape.
"""

from __future__ import annotations

from typing import Any

from web.gm.readers._entities import (
    attribute_rows,
    component_rows,
    dbref_of,
    key_of,
    label_of,
    ref_of,
    tag_rows,
    typeclass_of,
)
from web.gm.readers._json import json_value


def raw_object(entity: Any) -> dict[str, Any]:
    """The complete raw inventory of one Evennia entity."""
    created = getattr(entity, "db_date_created", None)
    location = getattr(entity, "location", None)
    return {
        "ref": ref_of(entity),
        "dbref": dbref_of(entity),
        "key": key_of(entity),
        "label": label_of(entity),
        "typeclass": typeclass_of(entity),
        # Object-only facts stay null for entities that have none (an Account
        # has no location), rather than inventing ObjectDB-only fields.
        "location": ref_of(location) if location is not None else None,
        "date_created": json_value(created) if created is not None else None,
        "attributes": attribute_rows(entity),
        "tags": tag_rows(entity),
        "components": component_rows(entity),
    }


def raw_identity(entity: Any) -> dict[str, Any]:
    """The identity envelope the raw endpoint returns beside ``raw``."""
    from web.gm.readers._entities import object_kind

    return {
        "id": str(dbref_of(entity)),
        "kind": object_kind(entity) or "object",
        "label": label_of(entity),
        "dbref": dbref_of(entity),
        "typeclass": typeclass_of(entity),
    }


__all__ = ["raw_identity", "raw_object"]
