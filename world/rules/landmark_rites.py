"""Deterministic landmark rite settlement (landmark-rite-settlement).

A landmark rite is the deliberate act performed at a district's landmark: it
costs the option's full authored duration of world time, moves the acting
body's sexual state through exactly one climax, and records the completion on
the record owner -- the controlling player character, never the acting body.

Everything here is one atomic unit (design §9.3): the two-call pleasure
sequence that walks the phase into 進行中, the option's shame and exposure
steps, one ``advance_wait`` whose own settlement loop closes the climax, and the
record write. A failure anywhere restores the clock, every registered advance
surface and the record attribute, so no time, sexual state or completion
survives a failed rite.

Refusals are stable codes raised before any write (:data:`REFUSAL_MESSAGES`).
The request identity is replayed from this module's own commit-only cache and
is never handed to the time advance, whose in-memory ledger no rollback clears
(design §16.1).

The district and the archetype are always resolved by the server from the
record owner's canonical node; nothing a client supplies is trusted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world.lore.rites.shape import RiteArchetype, RiteOption
from world.lore.scenes import Scene
from world.observability import log_info, log_warn
from world.rules.landmark_rite_record import (
    RECORD_ATTR,
    LandmarkRiteRecordError,
    read_record,
    with_completion,
    write_record,
)
from world.rules.map_knowledge import node_id_for
from world.rules.party_scope import (
    PURPOSE_ACT,
    PartyScopeError,
    authorize_member,
    party_in_combat,
    present_party_scope,
    resolve_commander,
)

__all__ = [
    "REFUSAL_MESSAGES",
    "RitePlan",
    "RiteRefused",
    "RiteResult",
    "RiteSite",
    "eligible_performers",
    "perform_rite",
    "preflight",
    "record_owner_for",
    "rite_site_for",
]

#: The player-facing line of every stable refusal code, in Traditional Chinese.
REFUSAL_MESSAGES: dict[str, str] = {
    "rite_no_landmark": "這裡沒有可以進行儀式的地標。",
    "rite_unknown_option": "這個地標沒有這樣的儀式。",
    "rite_member_unavailable": "這位隊友現在無法進行儀式。",
    "rite_no_watch_scene": "這個儀式只能親自進行。",
    "rite_record_corrupt": "儀式紀錄無法讀取，請聯絡管理者。",
    "rite_unavailable": "現在無法進行儀式。",
    "rite_unsafe": "附近有危險，無法進行儀式。",
    "rite_interrupted": "現在沒有足夠的時間完成儀式。",
}

#: How many committed rite receipts the replay cache keeps.
_RECEIPT_LIMIT = 256


class RiteRefused(Exception):
    """A deterministic rite refusal with a stable code and its player-facing line."""

    def __init__(self, code: str) -> None:
        self.code = code
        self.message = REFUSAL_MESSAGES[code]
        super().__init__(self.message)


@dataclass(frozen=True, slots=True)
class RiteSite:
    """The rite landmark the record owner stands on."""

    district_key: str
    district_name: str
    landmark_name: str
    archetype: RiteArchetype


@dataclass(frozen=True, slots=True)
class RitePlan:
    """One resolved rite request: record owner, acting body and server-side site."""

    owner: Any
    body: Any
    site: RiteSite
    option: RiteOption
    perspective: str


@dataclass(frozen=True, slots=True)
class RiteResult:
    """One committed rite: its delivered scene, tick and mechanical outcome."""

    plan: RitePlan
    scene: Scene
    tick: int
    elapsed_seconds: int
    first_completion: bool
    climax: bool
    #: The committed time advance's own receipt identity, never the request identity.
    operation_id: str


#: Committed rite results by (acting body, request identity); written only after
#: commit. A request identity is scoped to the body that asked, so a colliding
#: identity from another character replays nothing that character never did.
_RECEIPTS: dict[tuple[int | None, str], RiteResult] = {}

#: ``(published district snapshot, node id -> district key)``, rebuilt only when
#: the published snapshot object changes: ``landmark_node_ids()`` rebuilds a
#: reference index over every settlement node on each call and this read runs on
#: every presentation snapshot.
_DISTRICTS_BY_NODE: tuple[Any, dict[str, str]] | None = None


# --------------------------------------------------------------------------- reads


def record_owner_for(actor: Any) -> Any:
    """The player character whose record this actor's rite completes."""
    from typeclasses.characters import PlayerCharacter

    try:
        owner = resolve_commander(actor)
    except PartyScopeError as error:
        raise RiteRefused("rite_unavailable") from error
    if not isinstance(owner, PlayerCharacter):
        raise RiteRefused("rite_unavailable")
    return owner


def _district_key_for_node(node: str) -> str | None:
    """The district whose landmark is the canonical node ``node``, or ``None``."""
    from world.lore import map_districts

    global _DISTRICTS_BY_NODE
    snapshot = map_districts.current()
    cached = _DISTRICTS_BY_NODE
    if cached is None or cached[0] is not snapshot:
        mapping: dict[str, str] = {}
        for district_key, node_id in map_districts.landmark_node_ids().items():
            mapping.setdefault(node_id, district_key)
        cached = (snapshot, mapping)
        _DISTRICTS_BY_NODE = cached
    return cached[1].get(node)


def rite_site_for(owner: Any) -> RiteSite | None:
    """The rite site the record owner stands on, or ``None`` (pure read).

    A landmark node is always a grid or terrain room, so any other room -- an
    ordinary interior, an instance -- has no rite before its node is even
    derived, and its node table is never built.
    """
    from typeclasses.rooms import GridRoom, TerrainRoom
    from world.lore import map_districts, rites as rite_content

    location = getattr(owner, "location", None)
    if not isinstance(location, (GridRoom, TerrainRoom)):
        return None
    try:
        node = node_id_for(location)
    except (TypeError, ValueError):  # observability: ignore R2: a room whose xyz/coordinates cannot produce a canonical node ID has no rite site (design D3's `None -> None`); this presentation read writes nothing and the node grammar owns the diagnostic
        return None
    if node is None:
        return None
    district_key = _district_key_for_node(node)
    if district_key is None:
        return None
    declaration = map_districts.current().districts.get(district_key)
    if declaration is None:
        return None
    try:
        archetype = rite_content.current().archetype_for(district_key)
    except rite_content.RitesNotLoaded:  # observability: ignore R2: a process that adopted no rite document has no rite site; this presentation read writes nothing and the adoption step owns the missing-document report
        return None
    if archetype is None:
        return None
    return RiteSite(
        district_key=district_key,
        district_name=declaration.district_name_zh,
        landmark_name=declaration.landmark_name_zh,
        archetype=archetype,
    )


def eligible_performers(actor: Any) -> tuple[Any, ...]:
    """The bodies that may perform here: the actor, then the present party.

    The actor leads even when it is a possessed companion; each present member
    follows when the member-scoped act authorization admits it. Pure read.
    """
    performers: list[Any] = [actor]
    try:
        owner = record_owner_for(actor)
        scope = present_party_scope(actor)
    except (RiteRefused, PartyScopeError):  # observability: ignore R2: a body without a resolvable owner or present party simply has no other eligible performer, and the eligibility read writes nothing
        return tuple(performers)
    for member in scope:
        if member is actor:
            continue
        try:
            authorize_member(
                owner, getattr(member, "id", None), PURPOSE_ACT, anchor=actor
            )
        except PartyScopeError:  # observability: ignore R2: an unavailable member is simply not offered, and the eligibility read writes nothing
            continue
        performers.append(member)
    return tuple(performers)


# --------------------------------------------------------------------------- preflight


def preflight(actor: Any, option_key: str, member_id: int | None = None) -> RitePlan:
    """Resolve one rite request without writing; the first failure refuses."""
    from world.rules.clock import advance_scope, read_world_clock
    from world.rules.dialogue import live_dialogue_session
    from world.rules.fatigue import sleep_blocks_actions
    from world.rules.mental_time import planned_seconds

    owner = record_owner_for(actor)
    if owner.location is not actor.location:
        raise RiteRefused("rite_unavailable")
    site = rite_site_for(owner)
    if site is None:
        raise RiteRefused("rite_no_landmark")
    option = site.archetype.option(option_key)
    if option is None:
        raise RiteRefused("rite_unknown_option")
    if member_id is None or member_id == getattr(actor, "id", None):
        body = actor
    else:
        try:
            body = authorize_member(owner, member_id, PURPOSE_ACT, anchor=actor)
        except PartyScopeError as error:
            raise RiteRefused("rite_member_unavailable") from error
    perspective = "self" if body is owner else "watch"
    # The handler's class presence, not a materializing instance read: a refused
    # request must leave the named body's baseline uncreated too.
    if getattr(type(body), "sexual", None) is None:
        raise RiteRefused("rite_member_unavailable")
    if perspective == "watch" and option.watch_scene is None:
        raise RiteRefused("rite_no_watch_scene")
    try:
        read_record(owner)
    except LandmarkRiteRecordError as error:
        log_warn(
            "landmark_rite_record_corrupt",
            exc=error,
            context={"char": owner.pk, "district": site.district_key},
        )
        raise RiteRefused("rite_record_corrupt") from error
    if (
        party_in_combat(actor, body)
        or live_dialogue_session(owner) is not None
        or sleep_blocks_actions(actor)
    ):
        raise RiteRefused("rite_unavailable")
    entities = present_party_scope(actor)
    clock = read_world_clock()
    tick = 0 if clock is None else int(clock.tick)
    with advance_scope(entities):
        planned = planned_seconds(entities, option.seconds, tick=tick)
    if planned != option.seconds:
        raise RiteRefused("rite_interrupted")
    return RitePlan(
        owner=owner,
        body=body,
        site=site,
        option=option,
        perspective=perspective,
    )


# --------------------------------------------------------------------------- settlement


def _receipt_key(actor: Any, operation_id: str) -> tuple[int | None, str]:
    """The replay key: one request identity, scoped to the acting body."""
    pk = getattr(actor, "pk", None)
    return (pk if isinstance(pk, int) else None, operation_id)


def _refusal_identity(actor: Any) -> tuple[Any, str]:
    """The diagnostic owner and district of a refusal, degrading to the actor.

    This runs on the failure path only, once the refusal code is already
    determined: an unreadable owner, site or room must never replace it.
    """
    owner: Any = None
    try:
        owner = record_owner_for(actor)
        site = rite_site_for(owner)
    except Exception:  # observability: ignore R2: a diagnostic re-read must never mask the refusal it annotates; an unresolvable owner degrades to the acting body, and an unreadable site keeps the owner and reports no district
        return (actor if owner is None else owner), ""
    return owner, "" if site is None else site.district_key


def _refusal_context(
    actor: Any, code: str, plan: RitePlan | None = None
) -> dict[str, Any]:
    """The refused event's context: owner-first character, district, and reason."""
    if plan is None:
        owner, district = _refusal_identity(actor)
    else:
        owner, district = plan.owner, plan.site.district_key
    return {"char": getattr(owner, "pk", None), "district": district, "reason": code}


def _publish_commit(
    actor: Any, operation_id: str | None, result: RiteResult
) -> None:
    """Post-commit publication: the replay receipt and the committed event."""
    if operation_id is not None:
        _RECEIPTS[_receipt_key(actor, operation_id)] = result
        while len(_RECEIPTS) > _RECEIPT_LIMIT:
            del _RECEIPTS[next(iter(_RECEIPTS))]
    plan = result.plan
    log_info(
        "landmark_rite_committed",
        context={
            "char": plan.owner.pk,
            "district": plan.site.district_key,
            "archetype": plan.site.archetype.key,
            "option": plan.option.key,
            "body": plan.body.pk,
            "seconds": plan.option.seconds,
            "elapsed": result.elapsed_seconds,
            "climax": result.climax,
        },
    )


def _settle(plan: RitePlan, actor: Any, operation_id: str | None) -> RiteResult:
    """Settle one preflighted rite as a single all-or-nothing unit."""
    from django.db import transaction

    from world.rules.clock import (
        AdvanceSource,
        _restore_advance_registry,
        _restore_clock_tick,
        _snapshot_clock_tick,
        build_advance_snapshot_registry,
        get_world_clock,
    )
    from world.rules.pleasure import apply_pleasure_gain
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
    from world.rules.time_skip import advance_wait

    owner, body, site, option = plan.owner, plan.body, plan.site, plan.option
    clock = get_world_clock()
    entities = present_party_scope(actor)
    registry = build_advance_snapshot_registry(
        clock,
        option.seconds,
        AdvanceSource.SKIP,
        entities,
        mental_scope=entities,
    )
    tick_snapshot = _snapshot_clock_tick(clock)
    record_snapshot = attribute_snapshot(owner, RECORD_ATTR)
    first_completion = site.district_key not in read_record(owner)["completed"]
    try:
        with transaction.atomic():
            # Read inside the transaction: a first-time body's baseline
            # materializes here, so a failure drops it with the savepoint
            # instead of leaving it behind.
            climax_before = body.sexual.climax_today
            apply_pleasure_gain(body, 100)
            apply_pleasure_gain(body, 0)
            body.sexual.shame.value += option.shame
            body.sexual.exposure.value += option.exposure
            # The advance never receives the caller's request identity: its own
            # in-memory ledger survives a rollback, so a retried identity would
            # replay a result whose settlement was discarded.
            advance = advance_wait(actor, option.seconds)
            if advance.elapsed_seconds != option.seconds:
                raise RiteRefused("rite_interrupted")
            tick = int(get_world_clock().tick)
            write_record(
                owner,
                with_completion(
                    read_record(owner), site.district_key, option.key, tick
                ),
            )
            if plan.perspective == "self":
                scene = option.self_scene
            else:
                scene = option.watch_scene
                if scene is None:  # preflight refuses this before any write
                    raise RiteRefused("rite_no_watch_scene")
            result = RiteResult(
                plan=plan,
                scene=scene,
                tick=tick,
                elapsed_seconds=advance.elapsed_seconds,
                first_completion=first_completion,
                climax=body.sexual.climax_today > climax_before,
                operation_id=advance.operation_id,
            )
            transaction.on_commit(
                lambda: _publish_commit(actor, operation_id, result)
            )
    except Exception:
        _restore_clock_tick(clock, tick_snapshot)
        _restore_advance_registry(registry, entities)
        restore_attribute_best_effort(owner, RECORD_ATTR, record_snapshot)
        raise
    return result


def perform_rite(
    actor: Any,
    option_key: str,
    member_id: int | None = None,
    *,
    operation_id: str | None = None,
) -> RiteResult:
    """Perform one rite atomically, or refuse with a stable code and no write."""
    from world.rules.skip_safety import evaluate_skip_safety
    from world.rules.time_skip import admit_contact_before_action

    if operation_id is not None:
        recorded = _RECEIPTS.get(_receipt_key(actor, operation_id))
        if recorded is not None:
            return recorded
    plan: RitePlan | None = None
    try:
        plan = preflight(actor, option_key, member_id)
        admit_contact_before_action(actor)
        if evaluate_skip_safety(actor) is not None:
            raise RiteRefused("rite_unsafe")
        return _settle(plan, actor, operation_id)
    except RiteRefused as refusal:
        log_info(
            "landmark_rite_refused",
            context=_refusal_context(actor, refusal.code, plan),
        )
        raise