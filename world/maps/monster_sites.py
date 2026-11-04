"""Monster site lifecycle owner: authored manual sites (monster-site-placement).

The authored site records live in ``world.lore.monster_placement``; this module
owns their execution. Each site holds one complete authored composition, so a
mixed group, a same-variant group, and a solitary stray each place exactly the
rows their composition declares. The owner keeps the per-site durable state the
design asks for — ``state``, ``cleared_at_tick``, and the saved occurrence
``seed``, ``generation_sequence`` and authoritative ``member_ids`` — on the
wilderness script, and settles clearings and in-game-clock recoveries inside
the registered ``monster_site_lifecycle`` world clock stage — never on room
entry, quest acceptance, or elapsed wall-clock time (design D-P3/D-P6).

Ownership (design D-P2): every individual created here carries the site's key
as its persistent ``db.site_key`` marker, is registered through the regional
population owner's explicit-placement operation (which validates the shared
wilderness surface without applying ordinary birth exclusions or density), and
is recorded in the site's own ``member_ids``. That identity list is the site's
authority: a member is resolved by persistent identity wherever it currently
stands or however temporarily absent it is, so a living detached member never
lets the site be declared clear. Ambient-, quest-, story-, combat-session-, or
other-site-owned monsters are never touched, and the ambient owner never
resumes a site's lifecycle.

The site's occurrence state derives from the world seed the regional
population owner supplies plus the site's own key, and a missing or malformed
seed refuses before any site write: there is no implicit default. Recovery
creates fresh individuals with fresh persistent identities through the
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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from typing import Any

from django.db import transaction
from evennia.contrib.grid.wilderness.wilderness import WildernessScript

from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    ENCOUNTER_COMPOSITION_REGISTRY,
    MONSTER_SITE_REGISTRY,
    MonsterSite,
    composition_variant_keys,
    variant_species_key,
)
from world.maps.regional_population import (
    MALFORMED_STATE,
    MalformedPopulationState,
    read_population_seed,
    register_explicit_individual,
    restore_population_surfaces,
    sample_composition_counts,
    snapshot_population_surfaces,
)
from world.maps.wilderness_population import _session_participant_ids
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.observability import log_info, log_warn
from world.rules.clock import ScheduledEvent, SurfaceSnapshot, register_event_source
from world.rules.monster_individual import construct_species_individual
from world.rules.surfaces import attribute_snapshot
from world.rules.surfaces import persisted_hp as _persisted_hp

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
SITE_READ_STATE_UNREADABLE = "state_unreadable"

# The wilderness script attribute holding the per-site durable state.
_SITES_ATTRIBUTE = "monster_sites"
_ITEMCOORDINATES_ATTRIBUTE = "itemcoordinates"


@dataclass(frozen=True, slots=True)
class SiteState:
    """One site's durable lifecycle state, as the quest layer reads it.

    ``seed``, ``generation_sequence`` and ``member_ids`` are the site's saved
    occurrence and member-identity authority, exposed so the recovery slice and
    the GM inspection read the same state the owner decides from. ``readable``
    is ``False`` when an existing record cannot be interpreted: the owner then
    refuses lifecycle work instead of reinterpreting it as an empty site.
    """

    key: str
    state: str
    cleared_at_tick: int | None
    seed: int | None = None
    generation_sequence: int | None = None
    member_ids: tuple[int, ...] = ()
    readable: bool = True


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


def _saved_occurrence(site_key: str, record: Mapping[str, object]) -> tuple[int, int] | None:
    """The saved ``(seed, generation_sequence)`` of one record, or ``None``.

    ``None`` means the record cannot be interpreted; a lifecycle decision must
    then refuse rather than treat a corrupt save as an empty site.
    """
    seed = record.get("seed")
    sequence = record.get("generation_sequence")
    if isinstance(seed, bool) or not isinstance(seed, int):
        return None
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        return None
    return seed, sequence


def _require_occurrence(site: MonsterSite, record: Mapping[str, object]) -> tuple[int, int]:
    """The record's saved occurrence, refusing a malformed record by name."""
    occurrence = _saved_occurrence(site.key, record)
    if occurrence is None:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: site {site.key!r} has no readable saved seed "
            "and generation sequence"
        )
    return occurrence


def _saved_member_ids(record: Mapping[str, object]) -> tuple[int, ...] | None:
    """The site's authoritative member IDs, or ``None`` when unreadable.

    Evennia hands an attribute value back as its own mutation-aware sequence
    type, so the check accepts any non-text sequence, not just ``list``.
    """
    ids = record.get("member_ids")
    if isinstance(ids, (str, bytes)) or not isinstance(ids, Sequence):
        return None
    members: list[int] = []
    for value in ids:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return None
        members.append(value)
    return tuple(members)


def _require_member_ids(site: MonsterSite, record: Mapping[str, object]) -> tuple[int, ...]:
    """The record's authoritative member IDs, refusing a malformed record by name."""
    member_ids = _saved_member_ids(record)
    if member_ids is None:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: site {site.key!r} has no readable member IDs"
        )
    return member_ids


def _members_from_ids(
    site: MonsterSite, member_ids: tuple[int, ...]
) -> tuple[Monster, ...]:
    """Resolve one site's authoritative IDs to the rows that still exist.

    Identity, not presence, is the authority: a member that moved away, lost
    its room, or was detached is still this site's own individual, so a living
    absent member keeps the site from being declared clear. A recycled primary
    key that now carries another site's marker is never adopted.
    """
    if not member_ids:
        return ()
    return tuple(
        member
        for member in Monster.objects.filter(pk__in=member_ids).order_by("pk")
        if member.db.site_key == site.key
    )


def _members(wilderness: Any, site: MonsterSite) -> tuple[Monster, ...]:
    """Every individual this site owns, by its saved member identity.

    Tolerant for the pure read path: a missing record means the site was never
    populated, and an unreadable one yields no answer rather than an inferred
    set. Lifecycle decisions go through :func:`_require_member_ids` first.
    """
    record = _state_map(wilderness).get(site.key)
    if record is None:
        return ()
    member_ids = _saved_member_ids(record)
    if member_ids is None:
        return ()
    return _members_from_ids(site, member_ids)


def _living_members(wilderness: Any, site: MonsterSite) -> tuple[Monster, ...]:
    return tuple(
        member for member in _members(wilderness, site) if _persisted_hp(member) > 0
    )


def site_state(site_key: str, *, wilderness: Any | None = None) -> SiteState | None:
    """One authored site's durable state, or ``None`` when it has none yet.

    The visible state the quest layer reads so its republish decisions and the
    site's lifecycle cannot contradict each other. A present-but-unreadable
    record is answered with ``readable=False`` and no member IDs; it is never
    reinterpreted as an empty site.
    """
    wilderness = _wilderness() if wilderness is None else wilderness
    if wilderness is None:
        return None
    record = _state_map(wilderness).get(site_key)
    if record is None:
        return None
    occurrence = _saved_occurrence(site_key, record)
    member_ids = _saved_member_ids(record)
    return SiteState(
        site_key,
        record.get("state"),
        record.get("cleared_at_tick"),
        seed=None if occurrence is None else occurrence[0],
        generation_sequence=None if occurrence is None else occurrence[1],
        member_ids=() if member_ids is None else member_ids,
        readable=occurrence is not None and member_ids is not None,
    )


def site_living_members(
    site_key: str, *, wilderness: Any | None = None
) -> SiteLivingMembers:
    """One site's own living individuals and its durable state (a pure read).

    The quest layer's binding source (monster-site-clear-out-hunts D-C2): a
    clear-out's bound set is exactly what this answers, so it decides nothing
    and therefore writes nothing, moves nothing, emits no event, and never
    treats a not-yet-populated, cleared, unknown, absent world, or unreadable
    save as a recovery opportunity. Every one of those conditions is a named
    verdict rather than an exception, so a caller can refuse by name.
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
    if not state.readable:
        return SiteLivingMembers(
            site_key,
            site,
            state.state,
            state.cleared_at_tick,
            (),
            SITE_READ_STATE_UNREADABLE,
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


def _populate(
    wilderness: Any,
    site: MonsterSite,
    *,
    seed: int,
    sequence: int,
    tick: int,
) -> tuple[Monster, ...]:
    """Create one complete sampled composition through the construction owner.

    Fresh rows every time: the site's occurrence selects one inclusive
    count vector of its authored composition, every row of which is constructed
    with its own identity and stored resources, marked with the site key, and
    registered through the regional population owner's explicit-placement
    operation at the site's coordinate. That operation validates the shared
    wilderness surface while deliberately applying no ordinary settlement
    buffer, zone/cell density or wave budget, so an explicit manual site is
    never culled or capped by automatic maintenance. No shipped number is
    duplicated here: the traits come from the construction owner's
    balance-gated rule. ``seed``/``sequence`` are the site's saved occurrence
    (the tick is reporting context only, so a retry at a later tick selects the
    same complete group).
    """
    created: list[Monster] = []
    rows = sample_composition_counts(
        site.composition_key,
        seed=seed,
        stream_key=site.key,
        sequence=sequence,
        budget=site.capacity,
    )
    for variant_key, count in rows:
        species_key = variant_species_key(variant_key)
        for _ in range(count):
            individual = construct_species_individual(species_key, variant_key)
            individual.db.site_key = site.key
            register_explicit_individual(
                wilderness, individual, site.coordinates, tick=tick
            )
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
    composition = ENCOUNTER_COMPOSITION_REGISTRY[site.composition_key]
    variants = composition_variant_keys(composition)
    context: dict[str, object] = {
        "site": site.key,
        "region": site.region_key,
        "coordinate": site.coordinates,
        "species": tuple(sorted({variant_species_key(key) for key in variants})),
        "variant": variants,
    }
    context.update(extra)
    return context


def _condition_matured(site: MonsterSite, cleared_at_tick: object, tick: int) -> bool:
    """Whether a cleared site's authored in-game condition is satisfied."""
    if isinstance(cleared_at_tick, bool) or not isinstance(cleared_at_tick, int):
        return False
    return cleared_at_tick + site.recover_after_ticks <= tick


def _site_seed(wilderness: Any, site: MonsterSite) -> int:
    """The one saved-occurrence seed a site derives from the world's seed.

    Derivation happens exactly once, when the site owner first creates the
    site's row; recovery reuses the saved value. The world seed is read through
    the regional population owner's already-required access, so an absent or
    malformed seed refuses by name before any construction or site write
    instead of selecting an implicit default.
    """
    world_seed = read_population_seed(wilderness)
    payload = f"{world_seed}:{site.key}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _populated_record(
    seed: int, sequence: int, created: tuple[Monster, ...]
) -> dict[str, object]:
    """The durable record of one complete, freshly placed site composition."""
    return {
        "state": SITE_STATE_POPULATED,
        "cleared_at_tick": None,
        "seed": seed,
        "generation_sequence": sequence,
        "member_ids": [member.pk for member in created],
    }


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
    *,
    seed: int,
    sequence: int,
    tick: int,
) -> tuple[Monster, ...]:
    """Repopulate a due site inside the caller's in-flight state map.

    The recovered group is a fresh sample of the same saved occurrence seed at
    the next generation sequence, so every standing individual has a fresh
    persistent identity and the defeated IDs are replaced rather than reused.
    """
    record = dict(states[site.key])
    cleared_at_tick = record.get("cleared_at_tick")
    created = _populate(
        wilderness, site, seed=seed, sequence=sequence, tick=tick
    )
    states[site.key] = {
        **record,
        "state": SITE_STATE_POPULATED,
        "cleared_at_tick": None,
        "generation_sequence": sequence,
        "member_ids": [member.pk for member in created],
    }
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
    record = states.get(site.key)
    if record is not None:
        # A present record must be interpretable: a corrupt save is never
        # reinterpreted as an empty site, so no replacement group is created
        # over survivors.
        _require_occurrence(site, record)
        _require_member_ids(site, record)
    record = record or {}
    if _recovery_refusal(wilderness, site, record, tick) is not None:
        return False
    seed, saved_sequence = _require_occurrence(site, record)
    states_before = _state_map(wilderness)
    surfaces = snapshot_population_surfaces(wilderness)
    try:
        with transaction.atomic():
            created = _apply_recovery(
                wilderness,
                states,
                site,
                seed=seed,
                sequence=saved_sequence + 1,
                tick=tick,
            )
            _write_state(wilderness, states)
    except Exception:
        _write_state(wilderness, states_before)
        restore_population_surfaces(surfaces)
        raise
    return bool(created)


def settle_monster_sites(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """Settle every authored site clear/recover decision for this advance.

    The registered ``monster_site_lifecycle`` stage. A site with no durable
    state yet is populated for the first time from its derived occurrence;
    a populated site with no *living* member of its own is marked cleared at
    ``end_tick`` (skipped while a persisted combat session still references one
    of its individuals, so a committed defeat settles before the site is
    declared clear); a cleared recoverable site repopulates when its authored
    in-game condition matured. A member resolved by its saved identity counts
    even when it currently stands elsewhere, so a living absent member never
    clears the site. One-shot sites never recover, and no pass writes anything
    for a site whose state did not change. A present record that cannot be
    interpreted raises the population owner's named malformed-state refusal
    before any write. No wilderness script means no world to settle, and the
    pass returns silently.
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
            seed = _site_seed(wilderness, site)
            created = _populate(
                wilderness, site, seed=seed, sequence=0, tick=end_tick
            )
            states[key] = _populated_record(seed, 0, created)
            changed = True
            _emit(
                "monster_site_populated",
                _site_context(site, tick=end_tick, created=len(created)),
            )
            continue
        seed, saved_sequence = _require_occurrence(site, record)
        member_ids = _require_member_ids(site, record)
        if record.get("state") == SITE_STATE_POPULATED:
            members = _members_from_ids(site, member_ids)
            if any(_persisted_hp(member) > 0 for member in members):
                continue
            if members and _session_participant_ids().intersection(
                member.pk for member in members
            ):
                # A committed combat session still owns this defeat: the
                # clearing decision waits for the session to settle.
                continue
            # The defeated identities stay recorded: they are the site's
            # ownership history and no recovered group may reuse them.
            states[key] = {
                **record,
                "state": SITE_STATE_CLEARED,
                "cleared_at_tick": end_tick,
            }
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
        created = _apply_recovery(
            wilderness,
            states,
            site,
            seed=seed,
            sequence=saved_sequence + 1,
            tick=end_tick,
        )
        changed = True
        composition = ENCOUNTER_COMPOSITION_REGISTRY[site.composition_key]
        events.append(
            ScheduledEvent(
                "monster_site_recovered",
                end_tick,
                {
                    "site": key,
                    "variants": list(composition_variant_keys(composition)),
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
