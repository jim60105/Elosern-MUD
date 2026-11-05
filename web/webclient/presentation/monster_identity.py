"""The ``monster_identity`` wire facts shared by the exploration and combat panels.

``monster_identity`` is ``null`` or exactly ``{individual_name, species_name,
variant_name}`` (monster-individual-names design D4): facts, never a composed
name or tag, because the client owns how identity reads. When it is non-null
the row's ``display_name`` is derived from it -- the individual name, else the
species name -- so a changed object key can never make a payload disagree with
itself, and both validators reject a row that does.

The client mirror lives in ``web/static/webclient/js/elosern/protocol/core.js``
(``validateMonsterIdentity``).
"""

from typing import Any

from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    _require_exact_fields,
)

MONSTER_IDENTITY_FIELDS = frozenset({"individual_name", "species_name", "variant_name"})


def identity_display_name(identity: dict[str, Any]) -> str:
    """The display name a non-null identity implies: individual, else species."""
    individual = identity["individual_name"]
    return individual if individual is not None else identity["species_name"]


def monster_identity_payload(view: Any, maximum: int) -> dict[str, Any] | None:
    """Serialize one ``MonsterIdentityView`` (or ``None``) with bounded values."""
    if view is None:
        return None
    individual = view.individual_name
    return {
        "individual_name": None if individual is None else individual[:maximum],
        "species_name": view.species_name[:maximum],
        "variant_name": view.variant_name[:maximum],
    }


def _require_name(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolValidationError(f"monster_identity {field} must be a non-empty string")
    if len(value) > maximum:
        raise ProtocolValidationError(f"monster_identity {field} exceeds its bound")
    return value


def validate_monster_identity(
    value: Any, display_name: str, maximum: int
) -> dict[str, Any] | None:
    """Validate one row's ``monster_identity`` against its ``display_name``."""
    if value is None:
        return None
    _require_exact_fields(value, "monster_identity", set(MONSTER_IDENTITY_FIELDS), {})
    individual = value["individual_name"]
    if individual is not None:
        individual = _require_name(individual, "individual_name", maximum)
    identity = {
        "individual_name": individual,
        "species_name": _require_name(value["species_name"], "species_name", maximum),
        "variant_name": _require_name(value["variant_name"], "variant_name", maximum),
    }
    if display_name != identity_display_name(identity):
        raise ProtocolValidationError(
            "display_name must equal the identity's individual or species name"
        )
    return identity
