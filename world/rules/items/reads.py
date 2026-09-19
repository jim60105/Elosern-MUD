"""Handler-free storage, mirror, inventory, and pleasure reads for item use.

Part of the ``world.rules.items`` package. These deliberately mirror
``world.rules.status_query``'s strict no-create reads: a preflight eligibility
check must never materialize a lazy handler (traits, buffs, or ``sexual``).
Also owns target resolution: the group-scope room expansion and the shared
resolver hop every effect's candidate set passes through.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from world.rules.buffs import BUFF_DEFINITIONS, active_buff_keys_from_storage
from world.rules.equipment import registry_key_for_object
from world.rules import item_effects
from world.rules.item_effects import ItemEffect, ItemTargetScope
from world.rules.items.contracts import (
    ItemUsePreflight,
    ItemUseReason,
    ItemUseRequest,
)
from world.rules.targeting import (
    Relation,
    expand_target_shorthand,
    resolve_targets,
)


def _gauge_from_storage(entity: Any, key: str) -> tuple[int, int] | None:
    """Read one gauge's ``(current, maximum)`` without materializing a handler.

    Mirrors the strict no-create parser in ``world.rules.status_query``; a
    missing or malformed record returns ``None`` so callers fail closed.
    """
    traits = entity.attributes.get("traits", default=None, category="traits")
    if not isinstance(traits, Mapping):
        return None
    raw = traits.get(key)
    if not isinstance(raw, Mapping):
        return None
    base = raw.get("base")
    mod = raw.get("mod", 0)
    mult = raw.get("mult", 1)
    if isinstance(base, bool) or not isinstance(base, int):
        return None
    if isinstance(mod, bool) or not isinstance(mod, (int, float)):
        return None
    if isinstance(mult, bool) or not isinstance(mult, (int, float)):
        return None
    maximum = int(round((base + mod) * mult))
    if maximum <= 0:
        return None
    current = raw.get("current")
    if current is None:
        current = maximum
    if isinstance(current, bool) or not isinstance(current, int):
        return None
    if current < 0 or current > maximum:
        return None
    return current, maximum


def _inventory_list(entity: Any) -> list[str] | None:
    """Return a copy of the canonical key list, or ``None`` when malformed.

    Accepts Evennia's ``_SaverList`` storage (a Sequence, not a ``list``
    subclass); a bare string, mapping, or non-string entry fails closed.
    """
    raw = entity.db.inventory
    if raw is None:
        return []
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        return None
    if not all(isinstance(item, str) for item in raw):
        return None
    return list(raw)


def _select_mirror(entity: Any, item_key: str) -> Any | None:
    """Select at most one existing contained mirror in deterministic order.

    Matching contained objects are ordered by primary key (unsaved objects,
    which cannot legitimately occur, sort last) so every preflight of the same
    state names the same mirror.
    """
    contents = getattr(entity, "contents", None)
    if contents is None:
        return None
    matches = [obj for obj in contents if registry_key_for_object(obj) == item_key]
    if not matches:
        return None
    matches.sort(key=lambda obj: (obj.id is None, obj.id or 0))
    return matches[0]


def _rejected(reason: ItemUseReason) -> ItemUsePreflight:
    return ItemUsePreflight(allowed=False, reason=reason, plan=None)


def _group_candidates(context: Any, actor: Any, shorthand: str) -> list[Any]:
    """Expand a group scope's candidates through a context without a battlefield.

    ``expand_target_shorthand`` is battlefield-only (it rejects a context
    without one). Outside a session the same self/ally/enemy filter runs
    over the room's present entities through the very
    ``context.relation_to`` the resolver itself will consult, so the room
    expansion cannot disagree with the validation that follows: out of
    combat every non-actor is allied (design D6), which makes ``all`` and
    ``all-allies`` coincide and leaves ``all-enemies`` with no candidate.
    Candidates are deduplicated by identity — a room's contents include the
    actor, and the resolver rejects repeated AREA identities.
    """
    room = getattr(context, "room", None)
    if room is None:
        return []
    wanted = (
        {Relation.ENEMY}
        if shorthand == "all-enemies"
        else {Relation.SELF, Relation.ALLY}
    )
    seen: dict[int, Any] = {}
    for entity in getattr(room, "contents", ()):
        if id(entity) in seen:
            continue
        if context.relation_to(actor, entity) in wanted:
            seen[id(entity)] = entity
    return list(seen.values())


def _resolve_effect_targets(
    request: ItemUseRequest, effect: ItemEffect, context: Any
) -> list[Any] | ItemUsePreflight:
    """Resolve one effect's targets through the shared resolver (design D2/D5).

    Self scopes bind the actor through the requirement's SELF spec; single
    scopes consume the request's one explicit target (never supplied →
    ``no_target``); group scopes expand their shorthand through the context.
    Every candidate set then passes the same
    ``resolve_targets(actor, context, requirement, candidates)`` a skill's
    targets pass — presence, aliveness, range, faction, no second resolver.
    A rejected resolver surfaces as ``target_invalid`` with the resolver's
    own reason as detail (D5). A non-entity target (a raw string key left
    unresolved, a group shorthand token) fails closed the same way before
    reaching validators that require entity surface.
    """
    rule = item_effects.scope_targeting_rule(effect.scope)
    if effect.scope is ItemTargetScope.SELF:
        candidates: list[Any] = [request.actor]
    elif effect.scope is ItemTargetScope.SINGLE:
        if request.target is None:
            return _rejected(ItemUseReason.NO_TARGET)
        target = request.target
        if not hasattr(target, "location"):
            # Entities carry a location; a bare key or shorthand token
            # never resolves. Naming the resolver's own presence reason
            # keeps the detail contract uniform with a refused candidate.
            return _rejected(ItemUseReason.TARGET_INVALID)
        candidates = [target]
    else:
        candidates = (
            expand_target_shorthand(request.actor, context, rule.shorthand)
            if context.battlefield is not None
            else _group_candidates(context, request.actor, rule.shorthand)
        )
    try:
        return resolve_targets(
            request.actor, context, rule.requirement, candidates
        )
    except Exception as error:  # observability: ignore R1: only the resolver's own typed rejection is translated; anything else propagates
        from world.rules.action import RejectedAction

        if not isinstance(error, RejectedAction):
            raise
        return ItemUsePreflight(
            allowed=False,
            reason=ItemUseReason.TARGET_INVALID,
            detail=f"{error.reason.value}: {error.detail}",
            plan=None,
        )


def _active_matching_keys(entity: Any, matches: Callable[[str], bool]) -> tuple[str, ...]:
    """Handler-free sorted definition keys whose active instances match.

    Uses the storage accessor exactly like every presentation surface, so a
    conditional read never materializes the buff handler. Raises ``TypeError``
    on malformed buff storage for the caller to fail closed.
    """
    return tuple(
        sorted(
            key
            for key in active_buff_keys_from_storage(entity)
            if BUFF_DEFINITIONS.get(key) is not None and matches(key)
        )
    )
def _pleasure_current(entity: Any) -> int:
    """Handler-free read of the pleasure gauge counter, clamped to its bounds.

    Mirrors the strict no-create reads in ``world.rules.status_query``: an
    unmaterialized ``sexual_traits`` record has a zero pleasure counter (the
    shipped handler's floor), a materialized record missing the counter or
    carrying a malformed entry fails closed by raising ``TypeError`` (the
    ``SexualState`` handler always writes every intimate entry, so a missing
    entry is corruption). Never creates ``entity.sexual``.
    """
    traits = entity.attributes.get("sexual_traits", default=None, category="traits")
    if not isinstance(traits, Mapping):
        return 0
    if "pleasure" not in traits:
        raise TypeError("materialized sexual state is missing pleasure")
    raw = traits["pleasure"]
    if not isinstance(raw, Mapping):
        raise TypeError("materialized pleasure counter is malformed")
    base = raw.get("current", raw.get("base"))
    if isinstance(base, bool) or not isinstance(base, int):
        raise TypeError("materialized pleasure counter base is malformed")
    return max(0, min(100, base))
