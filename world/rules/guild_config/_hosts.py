"""The service-host roster derived from the place registry.

One row per host-declaring place, carrying that place's validated direct
capability declarations plus the place lookup the shop join shares
(``_place_for_shop``). Nothing here consults a blueprint: a place's
``components`` ARE the host's capabilities.
"""

from world.lore.church.places import CHURCH_VENUE_KEY
from world.lore.settlements.places import PLACE_REGISTRY, place_is_hostless
from world.lore.settlements.places import place_shop_identity
from world.rules.npc_capabilities import CapabilityValidationError, validate_capabilities

from ._loaders import _commerce_error, _error, _require_text
from ._types import ServiceHostRow


def validate_service_hosts() -> tuple[ServiceHostRow, ...]:
    """Batch-validate the service-host roster derived from the place registry.

    The roster is not authored separately: each place that declares a host
    yields one row carrying the host identity (``name``/``title``), the
    canonical authored profile identity, the interior room tag its host is
    created in (the place key), and the place's direct capability
    declarations.

    Rejections are named and complete before any write: an incomplete host
    identity, a duplicate canonical host identity, a capability declaration
    the shared core rejects, a place-bound capability anchored anywhere but its
    own place (or a person-bound/unbound one, which no authored host can
    mean), a non-canonical church venue identity, and a service anchor two
    rows both claim. A hosted place MAY declare zero capabilities.

    Config load never touches the database: anchor rooms are validated as
    their authored tags only (existence and uniqueness are facts the sync
    resolves inside its transaction).
    """
    rows: list[ServiceHostRow] = []
    seen_host_keys: set[str] = set()
    seen_service_ids: set[str] = set()
    for place in PLACE_REGISTRY.values():
        if place_is_hostless(place):
            continue
        what = f"place {place.key!r}"
        name = _require_text(place.host_name, f"{what}.host_name")
        title = _require_text(place.host_title, f"{what}.host_title")
        spawn_room = _require_text(place.key, f"{what}.key (spawn room tag)")
        profile_key = _require_text(place.host_profile_key, f"{what}.host_profile_key")
        if profile_key in seen_host_keys:
            raise _error(
                f"duplicate host_key {profile_key!r} in the place registry; "
                "one roster row per canonical host identity"
            )
        seen_host_keys.add(profile_key)
        try:
            validate_capabilities(place.components)
        except CapabilityValidationError as error:
            raise _error(f"{what} declares unusable capabilities: {error}") from error
        row_service_ids: set[str] = set()
        for declaration in place.components:
            binding = declaration.binding
            if binding is None or binding.kind != "place":
                raise _error(
                    f"{what} declares {declaration.type!r} without a place "
                    f"binding; a roster host anchors every capability at {place.key!r}"
                )
            if binding.anchor_room != place.key:
                raise _error(
                    f"{what} declares {declaration.type!r} anchored at "
                    f"{binding.anchor_room!r}, not at its own room {place.key!r}"
                )
            if declaration.type == "church_host":
                venue = declaration.kwargs.get("church")
                if venue != CHURCH_VENUE_KEY:
                    raise _error(
                        f"{what} declares church_host venue {venue!r}, expected the "
                        f"canonical {CHURCH_VENUE_KEY!r}"
                    )
            service_id = declaration.kwargs.get("service_id")
            if isinstance(service_id, str) and service_id:
                row_service_ids.add(service_id)
        duplicated = sorted(row_service_ids & seen_service_ids)
        if duplicated:
            raise _error(
                f"duplicate service_id {duplicated[0]!r} in the place registry; "
                "one roster row per service anchor"
            )
        seen_service_ids |= row_service_ids
        rows.append(
            ServiceHostRow(
                name=name,
                title=title,
                spawn_room=spawn_room,
                components=place.components,
                profile_key=profile_key,
                host_key=profile_key,
            )
        )
    return tuple(rows)


def _place_for_shop(shop_key: str):
    """Return the place row declaring this shop identity.

    A shop identity is declared on exactly one place (the derived
    ``SHOP_REGISTRY`` fails a duplicate at load), so the first match is the
    owning place, and every place-level operation (display name, scale,
    additions, removals) always has a row to resolve against.
    ``validate_shop_configs`` has already rejected any ``shop_key`` outside
    ``SHOP_REGISTRY``, so a miss here is an internal load invariant violating
    fail-closed rather than a user error.
    """
    for place in PLACE_REGISTRY.values():
        if place_shop_identity(place) == shop_key:
            return place
    raise _commerce_error(f"shops.{shop_key} has no owning place row")
