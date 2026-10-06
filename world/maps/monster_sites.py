"""Monster site lifecycle owner: camps, nests, and boss sites (monster-site-placement).

The authored site records live in ``world.lore.monster_placement``; this module
owns their execution. It materializes each site's individuals through the one
construction entry point (``world.rules.monster_individual``), keeps the
minimal per-site durable state the design asks for (``state`` and
``cleared_at_tick``) on the wilderness script, and settles clearings and
in-game-clock recoveries inside the registered ``monster_site_lifecycle`` world
clock stage — never on room entry, quest acceptance, or elapsed wall-clock
time (design D-P3/D-P6).

Ownership (design D-P2): every individual created here carries the site's key
as its persistent ``db.site_key`` marker and is registered in the wilderness
script's ``itemcoordinates`` bookkeeping at the site's coordinate, so it is the
only kind of object this module ever reads, writes, or deletes. Ambient-,
quest-, story-, combat-session-, or other-site-owned monsters are never
touched, and the ambient owner never resumes a site's lifecycle.

Recovery creates fresh individuals with fresh persistent identities through the
construction owner and leaves the defeated rows dead: identity continuity
across a recovery would let an old quest binding count new monsters (design
D-P4). A one-shot site stays cleared until an author-side re-issue, which the
authoring registry expresses — this module deliberately offers no player
command and no re-issue verb.

The quest layer's binding source is the pure read below (``site_living_members``):
it answers which of a site's own individuals stand and what the site's durable
state is, and a clear-out's bound set is exactly that answer. It populates,
recovers, moves, and deletes nothing — a site's first population and its
recovery stay this module's own clock-settled decisions — so no quest, board
read, or acceptance can become a second population owner (design D-C2).

The settlement runs inside ``WorldClock.advance()``'s transaction, so its
declared advance-surface contract (``snapshot_monster_site_surfaces``) snapshots
the wilderness bookkeeping and per-site state it may write, and every created
individual is flushed from Evennia's instance cache so a rolled-back row can
never be served for a recycled primary key.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from evennia.contrib.grid.wilderness.wilderness import WildernessScript

from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    MONSTER_SITE_REGISTRY,
    MonsterSite,
    variant_species_key,
)
from world.maps.wilderness_population import _session_participant_ids
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.observability import log_info, log_warn
from world.rules.clock import ScheduledEvent, SurfaceSnapshot, register_event_source
from world.rules.monster_individual import construct_species_individual
from world.rules.surfaces import attribute_snapshot

# The registered world-clock stage kind this module's settlement owns.
SITE_STAGE_KIND = "monster_site_lifecycle"

# The two per-site lifecycle states. A populated site holds living individuals;
# a cleared site holds none and remembers the in-game tick it was cleared at.
SITE_STATE_POPULATED = "populated"
SITE_STATE_CLEARED = "cleared"

# The closed verdict vocabulary of ``site_living_members`` (monster-site-clear-out
# -hunts D-C2/D-C3). ``None`` is the "the site can supply its individuals"
# answer; each value below names why it cannot. A shortfall against a caller's
# own required quantity is deliberately absent: that comparison belongs to the
# caller's objective, not to the site's state.
SITE_READ_WORLD_UNAVAILABLE = "world_unavailable"
SITE_READ_UNKNOWN_SITE = "unknown_site"
SITE_READ_UNPOPULATED = "site_unpopulated"
SITE_READ_CLEARED = "site_cleared"

# The wilderness script attribute holding the per-site durable state.
_SITES_ATTRIBUTE = "monster_sites"
_ITEMCOORDINATES_ATTRIBUTE = "itemcoordinates"


@dataclass(frozen=True, slots=True)
class SiteState:
    """One site's durable lifecycle state, as the quest layer reads it."""

    key: str
    state: str
    cleared_at_tick: int | None


@dataclass(frozen=True, slots=True)
class SiteLivingMembers:
    """One site's own living individuals plus the state that answered.

    ``reason`` is ``None`` exactly when the site could answer; otherwise it is
    one of the ``SITE_READ_*`` verdicts. ``members`` is always the site's own
    living set at the moment of the read, so a refused read never carries a
    partial set a caller could mistake for a binding source.
    """

    site_key: str
    site: MonsterSite | None
    state: str | None
    cleared_at_tick: int | None
    members: tuple[Monster, ...]
    reason: str | None

    @property
    def available(self) -> bool:
        """Whether the site answered with a usable set of living individuals."""
        return self.reason is None


def _wilderness() -> Any | None:
    """The live wilderness script, or ``None`` before the world is provisioned.

    Discovered at call time rather than captured at import: the settlement is
    registered during startup before ``sync_wilderness`` builds the wilderness,
    so a clock advance in that window (a restored session settling) must find
    no world and change nothing.
    """
    return WildernessScript.objects.filter(db_key=WILDERNESS_NAME).first()


def _state_map(wilderness: Any) -> dict[str, dict]:
    """The durable per-site state map, copied out for a whole-value write."""
    return {
        str(key): dict(value)
        for key, value in (wilderness.db.monster_sites or {}).items()
    }


def _write_state(wilderness: Any, states: Mapping[str, dict]) -> None:
    """Persist the whole per-site state map (Evennia saves a top-level write)."""
    wilderness.db.monster_sites = dict(states)


def site_state(site_key: str, *, wilderness: Any | None = None) -> SiteState | None:
    """One authored site's durable state, or ``None`` when it has none yet.

    The visible state the quest layer reads so its republish decisions and the
    site's lifecycle cannot contradict each other.
    """
    wilderness = _wilderness() if wilderness is None else wilderness
    if wilderness is None:
        return None
    record = _state_map(wilderness).get(site_key)
    if record is None:
        return None
    return SiteState(site_key, record.get("state"), record.get("cleared_at_tick"))


def _members(wilderness: Any, site: MonsterSite) -> tuple[Monster, ...]:
    """Every individual this site owns, by its own marker, at its coordinate."""
    return tuple(
        obj
        for obj in wilderness.get_objs_at_coordinates(site.coordinates)
        if isinstance(obj, Monster) and obj.db.site_key == site.key
    )


def _persisted_hp(member: Monster) -> float:
    """The individual's persisted HP, read without materializing its Trait.

    ``world.maps.wilderness_population::_stored_hp`` reads ``member.traits.hp``,
    which constructs the ``Trait``; Evennia's ``TraitHandler.get`` builds it from
    the persisted ``_SaverDict`` and the constructor's validation calls
    ``trait_data.update(...)``, and ``_SaverDict.update`` saves the attribute on
    every call. Both this module's settlement and the binding-source read below
    must leave storage alone, so they read the persisted trait record directly
    (the ``world/rules/status_query`` no-create read) and apply the same stored
    gauge rule, failing closed to "not living" on anything unreadable instead of
    raising.
    """
    traits = member.attributes.get("traits", category="traits")
    record = None if not isinstance(traits, Mapping) else traits.get("hp")
    if not isinstance(record, Mapping):
        return 0.0
    if "current" in record:
        return float(record["current"])
    return float(record.get("base", 0) + record.get("mod", 0)) * float(
        record.get("mult", 1)
    )


def _living_members(wilderness: Any, site: MonsterSite) -> tuple[Monster, ...]:
    return tuple(
        member for member in _members(wilderness, site) if _persisted_hp(member) > 0
    )


def site_living_members(
    site_key: str, *, wilderness: Any | None = None
) -> SiteLivingMembers:
    """One site's own living individuals and its durable state (a pure read).

    The quest layer's binding source (monster-site-clear-out-hunts D-C2): a
    clear-out's bound set is exactly what this answers, so it decides nothing
    and therefore writes nothing, moves nothing, emits no event, and never
    treats a not-yet-populated, cleared, unknown, or absent world as a recovery
    opportunity. Every one of those four conditions is a named verdict rather
    than an exception, so a caller can refuse by name.
    """
    world = _wilderness() if wilderness is None else wilderness
    if world is None:
        return SiteLivingMembers(
            site_key, None, None, None, (), SITE_READ_WORLD_UNAVAILABLE
        )
    site = MONSTER_SITE_REGISTRY.get(site_key)
    if site is None:
        return SiteLivingMembers(
            site_key, None, None, None, (), SITE_READ_UNKNOWN_SITE
        )
    state = site_state(site_key, wilderness=world)
    if state is None:
        return SiteLivingMembers(
            site_key, site, None, None, (), SITE_READ_UNPOPULATED
        )
    if state.state == SITE_STATE_CLEARED:
        return SiteLivingMembers(
            site_key,
            site,
            state.state,
            state.cleared_at_tick,
            (),
            SITE_READ_CLEARED,
        )
    return SiteLivingMembers(
        site_key,
        site,
        state.state,
        state.cleared_at_tick,
        _living_members(world, site),
        None,
    )


def _populate(wilderness: Any, site: MonsterSite) -> tuple[Monster, ...]:
    """Create the site's individuals through the construction owner.

    Fresh rows every time, marked with the site key and registered in the
    wilderness bookkeeping at the site's coordinate so the contrib attaches
    them to whichever room is active there. No shipped number is duplicated
    here: the individual's traits come from the construction owner's
    balance-gated rule and the site's own authored variants.
    """
    created = []
    for slot in range(site.capacity):
        variant_key = site.variant_keys[slot % len(site.variant_keys)]
        individual = construct_species_individual(
            variant_species_key(variant_key), variant_key
        )
        individual.db.site_key = site.key
        wilderness.db.itemcoordinates[individual] = site.coordinates
        room = wilderness.db.rooms.get(site.coordinates)
        if room is not None:
            individual.location = room
        created.append(individual)
    return tuple(created)


def _emit(
    event: str,
    context: Mapping[str, object],
    *,
    level: str = "info",
) -> None:
    """Schedule one boundary event on the enclosing durable commit.

    A rolled-back advance must leave no boundary line for state that never
    committed (the same contract ``clock_advance`` and
    ``monster_individual_constructed`` follow).
    """
    fire = log_warn if level == "warn" else log_info
    frozen = dict(context)
    transaction.on_commit(lambda: fire(event, context=frozen))


def _site_context(site: MonsterSite, **extra: object) -> dict[str, object]:
    """The boundary-event context every site decision carries."""
    context: dict[str, object] = {
        "site": site.key,
        "region": site.region_key,
        "coordinate": site.coordinates,
        "species": tuple(
            sorted({variant_species_key(key) for key in site.variant_keys})
        ),
        "variant": site.variant_keys,
    }
    context.update(extra)
    return context


def _condition_matured(site: MonsterSite, cleared_at_tick: object, tick: int) -> bool:
    """Whether a cleared site's authored in-game condition is satisfied."""
    if isinstance(cleared_at_tick, bool) or not isinstance(cleared_at_tick, int):
        return False
    return cleared_at_tick + site.recover_after_ticks <= tick


def _recovery_refusal(
    wilderness: Any,
    site: MonsterSite,
    record: Mapping[str, object],
    tick: int,
) -> str | None:
    """The reason this recovery attempt is refused, or ``None`` to proceed.

    Exactly one ``monster_site_recovery_rejected`` warn event is emitted for a
    refusal, so an attempt that cannot proceed is never silent while a pass
    that changes nothing stays so.
    """
    if record.get("state") != SITE_STATE_CLEARED:
        reason = "not_cleared"
    elif isinstance(record.get("cleared_at_tick"), bool) or not isinstance(
        record.get("cleared_at_tick"), int
    ):
        reason = "state_unreadable"
    elif not _condition_matured(site, record.get("cleared_at_tick"), tick):
        reason = "condition_unmet"
    elif _living_members(wilderness, site):
        # The footprint still holds living members: the site's authored
        # capacity is a ceiling, so nothing is added and nothing is deleted to
        # make room for the recovery.
        reason = "capacity_reached"
    else:
        return None
    _emit(
        "monster_site_recovery_rejected",
        _site_context(site, reason=reason, tick=tick),
        level="warn",
    )
    return reason


def _apply_recovery(
    wilderness: Any,
    states: dict[str, dict],
    site: MonsterSite,
    tick: int,
) -> tuple[Monster, ...]:
    """Repopulate a due site inside the caller's in-flight state map."""
    created = _populate(wilderness, site)
    cleared_at_tick = states[site.key].get("cleared_at_tick")
    states[site.key] = {"state": SITE_STATE_POPULATED, "cleared_at_tick": None}
    _emit(
        "monster_site_recovered",
        _site_context(
            site, tick=tick, cleared_at_tick=cleared_at_tick, created=len(created)
        ),
    )
    return created


def settle_site_recovery(
    site_key: str, tick: int, *, wilderness: Any | None = None
) -> bool:
    """Attempt one site recovery now; ``True`` when the site repopulated.

    The one place a site's recovery decision is made. A refusal emits exactly
    one ``monster_site_recovery_rejected`` warn event naming the site and the
    reason (``unknown_site``, ``one_shot``, ``condition_unmet``,
    ``not_cleared``, or ``capacity_reached`` — the last when the site's
    footprint still holds living members, so nothing is added past its
    capacity). The clock settlement pre-filters one-shot and not-yet-due sites
    (a pass that changes nothing stays silent) and calls this for the rest, so
    a due site whose state drifted is still reported.
    """
    site = MONSTER_SITE_REGISTRY.get(site_key)
    if site is None:
        _emit(
            "monster_site_recovery_rejected",
            {"site": site_key, "reason": "unknown_site", "tick": tick},
            level="warn",
        )
        return False
    wilderness = _wilderness() if wilderness is None else wilderness
    if wilderness is None:
        # The world is not provisioned yet: no site exists to recover, and no
        # decision was refused. Startup advances in that window stay silent.
        return False
    if site.one_shot:
        _emit(
            "monster_site_recovery_rejected",
            _site_context(site, reason="one_shot", tick=tick),
            level="warn",
        )
        return False
    states = _state_map(wilderness)
    record = states.get(site.key) or {}
    if _recovery_refusal(wilderness, site, record, tick) is not None:
        return False
    created = _apply_recovery(wilderness, states, site, tick)
    _write_state(wilderness, states)
    return bool(created)


def settle_monster_sites(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """Settle every authored site clear/recover decision for this advance.

    The registered ``monster_site_lifecycle`` stage. A site with no durable
    state yet is populated for the first time; a populated site with no living
    member of its own is marked cleared at ``end_tick`` (skipped while a
    persisted combat session still references one of its individuals, so a
    committed defeat settles before the site is declared clear); a cleared
    recoverable site repopulates when its authored in-game condition matured.
    One-shot sites never recover, and no pass writes anything for a site whose
    state did not change. No wilderness script means no world to settle, and
    the pass returns silently.
    """
    wilderness = _wilderness()
    if wilderness is None:
        return []
    states = _state_map(wilderness)
    events: list[ScheduledEvent] = []
    changed = False
    for key, site in MONSTER_SITE_REGISTRY.items():
        record = states.get(key)
        if record is None:
            created = _populate(wilderness, site)
            states[key] = {"state": SITE_STATE_POPULATED, "cleared_at_tick": None}
            changed = True
            _emit(
                "monster_site_populated",
                _site_context(site, tick=end_tick, created=len(created)),
            )
            continue
        if record.get("state") == SITE_STATE_POPULATED:
            members = _members(wilderness, site)
            if any(_persisted_hp(member) > 0 for member in members):
                continue
            if members and _session_participant_ids().intersection(
                member.pk for member in members
            ):
                # A committed combat session still owns this defeat: the
                # clearing decision waits for the session to settle.
                continue
            states[key] = {"state": SITE_STATE_CLEARED, "cleared_at_tick": end_tick}
            changed = True
            _emit(
                "monster_site_cleared",
                _site_context(site, tick=end_tick, cleared_at_tick=end_tick),
            )
            continue
        if site.one_shot:
            continue
        if not _condition_matured(site, record.get("cleared_at_tick"), end_tick):
            continue
        if _recovery_refusal(wilderness, site, record, end_tick) is not None:
            continue
        created = _apply_recovery(wilderness, states, site, end_tick)
        changed = True
        events.append(
            ScheduledEvent(
                "monster_site_recovered",
                end_tick,
                {
                    "site": key,
                    "variants": list(site.variant_keys),
                    "created": len(created),
                    "tick": end_tick,
                },
            )
        )
    if changed:
        _write_state(wilderness, states)
    return events


def _db_safe_attribute_snapshot(obj: Any, key: str) -> tuple[bool, Any]:
    """Snapshot one attribute whose value embeds live database objects.

    ``itemcoordinates`` is keyed by live ``Monster`` instances, which a plain
    ``deepcopy`` cannot copy; the ``dbserialize`` round-trip is the established
    deepcopy for values that may embed database objects (the same helper
    ``world/maps/instance.py`` uses for ``owned_entities``).
    """
    from evennia.utils.dbserialize import from_pickle, to_pickle

    exists = obj.attributes.has(key)
    value = from_pickle(to_pickle(obj.attributes.get(key))) if exists else None
    return exists, value


def snapshot_monster_site_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """Snapshot the durable surfaces this stage may write (pure read).

    The wilderness script's per-site state and object bookkeeping, plus the
    ``site_key`` marker and location of every site-owned individual the
    settlement's own discovery query finds, so a rolled-back advance restores
    the in-memory values Evennia's non-transaction-aware caches would otherwise
    keep serving.
    """
    wilderness = _wilderness()
    if wilderness is None:
        return {}
    registry: dict[int, SurfaceSnapshot] = {
        id(wilderness): SurfaceSnapshot(
            attributes={
                (_SITES_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                    wilderness, _SITES_ATTRIBUTE
                ),
                (_ITEMCOORDINATES_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                    wilderness, _ITEMCOORDINATES_ATTRIBUTE
                ),
            }
        )
    }
    for site in MONSTER_SITE_REGISTRY.values():
        for member in _members(wilderness, site):
            entry = registry.get(id(member))
            if entry is None:
                entry = SurfaceSnapshot(attributes={})
                registry[id(member)] = entry
            entry.attributes[("site_key", None)] = attribute_snapshot(
                member, "site_key"
            )
            location = member.location
            entry.location = (
                (True, int(location.pk)) if location is not None else (False, None)
            )
    return registry


def register_monster_site_lifecycle() -> None:
    """Register this module's settlement as the live site-lifecycle stage."""
    register_event_source(
        SITE_STAGE_KIND,
        settle_monster_sites,
        snapshot_monster_site_surfaces,
    )
