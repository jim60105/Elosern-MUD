"""The service-host roster derived from the place registry.

Batch validation of the derived rows plus the two place lookups the shop join
shares (``_require_place_kwargs`` / ``_place_for_shop``).
"""

from typing import Any

from world.lore.settlements.places import PLACE_REGISTRY

from ._loaders import _commerce_error, _error, _require_text
from ._types import ServiceHostRow


def validate_service_hosts() -> tuple[ServiceHostRow, ...]:
    """Batch-validate the service-host roster derived from the place registry (design §3.2).

    The roster is no longer authored: each place yields one row declaring
    ``name``/``title`` (the host identity), ``profession``, the interior room
    tag the place anchors to (its key), ``service_id``, and the authored
    component identity kwargs. Every rejection the hand-authored roster
    carried runs unchanged over the derived rows: a profession naming no
    registry row, a blueprint component whose identity kwargs the place fails
    to supply, surplus kwargs no component consumes, a person-bound profession
    anchored to a row, a duplicate service anchor, or a non-text field each
    raise the catalog's named error family.

    Config load never touches the database: ``anchor_room`` is validated as a
    non-empty tag string only (room existence is a sync-time fact), and the
    profession prerequisite is the YAML-only profession registry. A malformed
    professions rulebook surfaces inside this catalog's named error family
    rather than escaping as ``ProfessionConfigError``.
    """
    from world.rules import profession_config
    from world.rules.profession_assembly import identity_fields

    rows: list[ServiceHostRow] = []
    seen_service_ids: set[str] = set()
    for place in PLACE_REGISTRY.values():
        what = f"place {place.key!r}"
        name = _require_text(place.host_name, f"{what}.host_name")
        title = _require_text(place.host_title, f"{what}.host_title")
        anchor_room = _require_text(place.key, f"{what}.key (anchor room tag)")
        service_id = _require_text(place.service_id, f"{what}.service_id")
        profession_key = _require_text(place.profession, f"{what}.profession")
        if service_id in seen_service_ids:
            raise _error(
                f"duplicate service_id {service_id!r} in the place registry; "
                "one roster row per service anchor"
            )
        seen_service_ids.add(service_id)
        try:
            profession = profession_config.get_profession(profession_key)
        except profession_config.ProfessionConfigError as error:
            raise _error(f"{what} profession {profession_key!r} cannot load: {error}") from error
        if profession is None:
            raise _error(
                f"{what} profession {profession_key!r} "
                "is not a profession rulebook row"
            )
        # A roster row IS an anchor registration: its mandatory anchor_room
        # only means something to ``place``-bound components. A ``person``
        # component here would silently carry an anchor — the invalid
        # combination the service-anchoring change forbids at authoring time.
        person_bound = sorted(
            component.type_key
            for component in profession.components
            if component.default_binding == "person"
        )
        if person_bound:
            raise _error(
                f"{what} profession {profession_key!r} "
                f"component(s) {person_bound} are person-bound; a roster row "
                "anchors only place-bound components"
            )
        authored = _require_place_kwargs(place)
        # Blueprint coverage: every component's identity fields except the
        # row-level service_id anchor must be authored by the place.
        consumed: set[str] = set()
        for component in profession.components:
            needed = set(identity_fields(component.type_key)) - {"service_id"}
            lacking = sorted(needed - set(authored))
            if lacking:
                raise _error(
                    f"{what} profession {profession_key!r} "
                    f"component {component.type_key!r} needs authored kwargs {lacking}"
                )
            consumed |= needed
        dead = sorted(set(authored) - consumed)
        if dead:
            raise _error(
                f"{what} authors kwargs {dead} that no component "
                f"of profession {profession_key!r} consumes"
            )
        rows.append(
            ServiceHostRow(
                name=name,
                title=title,
                profession=profession,
                anchor_room=anchor_room,
                service_id=service_id,
                authored_kwargs=authored,
            )
        )
    return tuple(rows)


def _require_place_kwargs(place: Any) -> dict[str, str]:
    """Flatten a place's authored kwargs, rejecting a non-mapping shape."""
    authored = place.authored_kwargs
    if not isinstance(authored, (tuple, list)):
        raise _error(f"place {place.key!r} authored_kwargs must be a sequence of pairs")
    out: dict[str, str] = {}
    for position, pair in enumerate(authored):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise _error(f"place {place.key!r} authored_kwargs[{position}] must be a pair")
        key, value = pair
        out[key] = _require_text(value, f"place {place.key!r}.authored_kwargs[{position}]")
    return out


def _place_for_shop(shop_key: str):
    """Return the place row authoring this shop identity (design §3.2).

    A shop identity is authored on exactly one place (the derived
    ``SHOP_REGISTRY`` fails a duplicate at load), so the first match is the
    owning place, and every place-level operation (display name, scale,
    additions, removals) always has a row to resolve against.
    ``validate_shop_configs`` has already rejected any ``shop_key`` outside
    ``SHOP_REGISTRY``, so a miss here is an internal load invariant violating
    fail-closed rather than a user error.
    """
    for place in PLACE_REGISTRY.values():
        if dict(place.authored_kwargs).get("shop_key") == shop_key:
            return place
    raise _commerce_error(f"shops.{shop_key} has no owning place row")
