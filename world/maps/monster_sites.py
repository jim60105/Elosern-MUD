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
from world.lore.monster_activity import movement_units
from world.maps.regional_population import (
    MALFORMED_STATE,
    MalformedPopulationState,
    presence_at,
    protected_cells,
    read_population_seed,
    read_population_timeline,
    register_explicit_group,
    restore_population_surfaces,
    sample_composition_counts,
    snapshot_population_surfaces,
)
from world.maps.regional_population import _session_participant_ids
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.observability import log_info, log_warn
from world.rules.clock import ScheduledEvent, SurfaceSnapshot
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


#: The closed durable lifecycle-state vocabulary of one site record.
_SITE_STATES: tuple[str, ...] = (SITE_STATE_POPULATED, SITE_STATE_CLEARED)


def _read_state_map(wilderness: Any) -> dict[str, dict] | None:
    """The durable per-site state map, or ``None`` when it cannot be read.

    A pure reader answers a corrupt container with its named verdict rather
    than an exception; a lifecycle decision refuses through
    :func:`_state_map` instead.
    """
    raw = wilderness.db.monster_sites or {}
    if not isinstance(raw, Mapping):
        return None
    states: dict[str, dict] = {}
    for key, value in raw.items():
        if not isinstance(value, Mapping):
            return None
        states[str(key)] = dict(value)
    return states


def _state_map(wilderness: Any) -> dict[str, dict]:
    """The durable per-site state map, copied out for a whole-value write."""
    states = _read_state_map(wilderness)
    if states is None:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: the monster-site state map is unreadable"
        )
    return states


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


def _saved_state(record: Mapping[str, object]) -> str | None:
    """The record's lifecycle state, or ``None`` when it is inconsistent.

    A cleared record must remember a non-negative clearing tick; a populated
    one must not. The closed vocabulary is the one this owner writes.
    """
    state = record.get("state")
    if state not in _SITE_STATES:
        return None
    cleared_at = record.get("cleared_at_tick")
    if state == SITE_STATE_CLEARED:
        if isinstance(cleared_at, bool) or not isinstance(cleared_at, int) or cleared_at < 0:
            return None
    elif cleared_at is not None:
        return None
    return state


def _require_state(site: MonsterSite, record: Mapping[str, object]) -> str:
    """The record's lifecycle state, refusing a malformed record by name."""
    state = _saved_state(record)
    if state is None:
        raise MalformedPopulationState(
            f"{MALFORMED_STATE}: site {site.key!r} has no readable lifecycle state"
        )
    return state


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
    if not members or len(set(members)) != len(members):
        # Every lawful composition has positive membership, so an empty or
        # duplicated identity list is a corrupt save, never an empty site.
        return None
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
    states = _read_state_map(wilderness)
    if states is None:
        return ()
    record = states.get(site.key)
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


def _member_ids(wilderness: Any, site: MonsterSite) -> tuple[int, ...]:
    """The site's saved member identities, or nothing when it has no record."""
    states = _read_state_map(wilderness) or {}
    record = states.get(site.key)
    if record is None:
        return ()
    return _saved_member_ids(record) or ()


def _living_member_ids(
    wilderness: Any, site: MonsterSite, tick: int
) -> frozenset[int]:
    """The site's own members that are alive at ``tick`` (projected presence).

    The projection is the same evidence the regional owner accounts with, so a
    member whose loss is committed at a later tick still counts before it, and
    a deleted member never keeps a clear-out waiting merely because its row is
    gone.
    """
    ids = set(_member_ids(wilderness, site))
    if not ids:
        return frozenset()
    presence = presence_at(wilderness, at_tick=tick)
    return frozenset(
        individual_id
        for individual_id in ids
        if (fact := presence.get(individual_id)) is not None and fact.alive
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
    states = _read_state_map(wilderness)
    if states is None:
        return SiteState(site_key, None, None, readable=False)
    record = states.get(site_key)
    if record is None:
        return None
    occurrence = _saved_occurrence(site_key, record)
    member_ids = _saved_member_ids(record)
    state = _saved_state(record)
    return SiteState(
        site_key,
        state,
        record.get("cleared_at_tick") if state == SITE_STATE_CLEARED else None,
        seed=None if occurrence is None else occurrence[0],
        generation_sequence=None if occurrence is None else occurrence[1],
        member_ids=() if member_ids is None else member_ids,
        readable=(
            occurrence is not None and member_ids is not None and state is not None
        ),
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


def site_occurrence_groups(
    site: MonsterSite, *, seed: int, sequence: int
) -> tuple[tuple[str, int], ...]:
    """The complete sampled composition of one site occurrence (pure).

    The shared sampler: ``_populate`` constructs exactly these rows, and the
    read-only forecast counts them without creating anything. The saved
    occurrence ``(seed, sequence)`` alone identifies the outcome, so a forecast
    and the later commit select the same group across restarts and retries.
    """
    return sample_composition_counts(
        site.composition_key,
        seed=seed,
        stream_key=site.key,
        sequence=sequence,
        budget=site.capacity,
    )


def recovery_condition_matured(site_key: str, cleared_at_tick: Any, tick: int) -> bool:
    """Whether a cleared site's authored in-game condition is satisfied (pure)."""
    site = MONSTER_SITE_REGISTRY.get(site_key)
    if site is None:
        return False
    return _condition_matured(site, cleared_at_tick, tick)


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
    with its own identity and stored resources and marked with the site key.
    The complete composition then forms movement groups by the site binding's
    policy and registers each group through the regional population owner's
    explicit-placement operation at the site's coordinate: a stationary or
    solitary override leaves one group per individual while a cohesive override
    keeps the whole sampled group together. That operation validates the shared
    wilderness surface while deliberately applying no ordinary settlement
    buffer, zone/cell density or wave budget, so an explicit manual site is
    never culled or capped by automatic maintenance. No shipped number is
    duplicated here: the traits come from the construction owner's
    balance-gated rule. ``seed``/``sequence`` are the site's saved occurrence
    (the tick is reporting context only, so a retry at a later tick selects the
    same complete group).
    """
    created: list[Monster] = []
    rows = site_occurrence_groups(site, seed=seed, sequence=sequence)
    for variant_key, count in rows:
        species_key = variant_species_key(variant_key)
        for _ in range(count):
            individual = construct_species_individual(species_key, variant_key)
            individual.db.site_key = site.key
            created.append(individual)
    units = movement_units(rows, (site.activity_key,) * len(rows))
    for ordinal, unit in enumerate(units):
        register_explicit_group(
            wilderness,
            [created[index] for index in unit.member_indices],
            site.coordinates,
            tick=tick,
            owner_kind="site",
            owner_key=site.key,
            activity_key=unit.activity_key,
            operation_id=f"site:{site.key}:{sequence}",
            ordinal=ordinal,
        )
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
    elif _living_member_ids(wilderness, site, tick):
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
        _require_state(site, record)
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


def _last_member_loss_tick(wilderness: Any, individual_id: int) -> int | None:
    """The committed tick of one member's latest loss, or ``None``.

    Only the durable transition evidence answers: a raw repair that zeroed HP
    without recording a transition has no normal guarantee and yields no tick.
    """
    timeline = read_population_timeline(wilderness)
    latest: Any = None
    for transition in timeline.transitions:
        if transition.individual_id != individual_id:
            continue
        if latest is None or transition.occurred_tick >= latest.occurred_tick:
            latest = transition
    if latest is None or latest.after.alive:
        return None
    return latest.occurred_tick


def _clear_boundary(
    wilderness: Any, site: MonsterSite, start_tick: int
) -> int | None:
    """The tick at which this populated site's last own member is lost.

    ``None`` while any own member is still alive. A member already lost at the
    interval start (its loss committed before this interval) contributes the
    interval start; a member whose committed loss is still pending contributes
    that exact occurrence tick, so the site clears on the loss boundary rather
    than at the interval end and never on mere absence.
    """
    member_ids = _member_ids(wilderness, site)
    if not member_ids:
        return start_tick
    presence = presence_at(wilderness)
    boundaries: list[int] = []
    for individual_id in member_ids:
        fact = presence.get(individual_id)
        if fact is not None and fact.alive:
            return None
        loss_tick = _last_member_loss_tick(wilderness, individual_id)
        boundaries.append(start_tick if loss_tick is None else loss_tick)
    return max(boundaries) if boundaries else start_tick


def _birth_cell_protected(wilderness: Any, site: MonsterSite, tick: int) -> bool:
    """Whether this site's coordinate holds no lawful birth space at ``tick``."""
    return site.coordinates in protected_cells(wilderness, at_tick=tick)


def retained_loss_ids(wilderness: Any | None = None) -> frozenset[int]:
    """Owned IDs whose committed loss a deferred site clear still needs.

    A populated site whose members are all lost cannot be declared clear while
    a persisted combat session still references them. Its members' loss
    transitions are the evidence that carries the true occurrence tick to the
    later clear, so the coordinator must not consume them yet. IDs are
    retained only for a populated site with no living member and a session
    reference, and are otherwise consumed normally.
    """
    wilderness = _wilderness() if wilderness is None else wilderness
    if wilderness is None:
        return frozenset()
    states = _read_state_map(wilderness)
    if states is None:
        return frozenset()
    presence = presence_at(wilderness)
    retained: set[int] = set()
    for key, site in MONSTER_SITE_REGISTRY.items():
        record = states.get(key)
        if record is None or _saved_state(record) != SITE_STATE_POPULATED:
            continue
        member_ids = _saved_member_ids(record) or ()
        if not member_ids:
            continue
        living = {
            individual_id
            for individual_id in member_ids
            if (fact := presence.get(individual_id)) is not None and fact.alive
        }
        if living:
            continue
        members = _members_from_ids(site, member_ids)
        if not members:
            continue
        if not _session_participant_ids().intersection(
            member.pk for member in members
        ):
            continue
        retained.update(int(member.pk) for member in members)
    return frozenset(retained)


def next_site_boundary(start_tick: int, end_tick: int) -> int | None:
    """The earliest site lifecycle boundary up to ``end_tick`` (pure read).

    An uninitialized site's first creation boundary is the interval start, a
    cleared recoverable site's boundary is its exact
    ``cleared_at_tick + recover_after_ticks``, and a populated site's boundary
    is the committed loss occurrence of its last own member. A site whose state
    cannot be interpreted contributes no boundary here; the settlement answers
    with the population owner's named malformed-state refusal instead.
    """
    wilderness = _wilderness()
    if wilderness is None:
        return None
    states = _read_state_map(wilderness)
    if states is None:
        return None
    uninitialized = False
    candidates: list[int] = []
    for key, site in MONSTER_SITE_REGISTRY.items():
        record = states.get(key)
        if record is None:
            uninitialized = True
            continue
        state = _saved_state(record)
        if state == SITE_STATE_POPULATED:
            boundary = _clear_boundary(wilderness, site, start_tick)
            if boundary is not None:
                # A boundary already reached is re-evaluated at the interval
                # start (a deferred clear or an avoided protected cell), so a
                # later pass is not stranded behind it.
                candidates.append(boundary if boundary > start_tick else start_tick)
        elif state == SITE_STATE_CLEARED and not site.one_shot:
            cleared_at = record.get("cleared_at_tick")
            if isinstance(cleared_at, int) and not isinstance(cleared_at, bool):
                due = cleared_at + site.recover_after_ticks
                candidates.append(due if due > start_tick else start_tick)
    if uninitialized:
        candidates.append(start_tick)
    due = [candidate for candidate in candidates if start_tick < candidate <= end_tick]
    if uninitialized and start_tick <= end_tick:
        due.append(start_tick)
    later = [candidate for candidate in due if candidate > start_tick]
    return min(later) if later else None


def settle_monster_sites_at(tick: int) -> list[ScheduledEvent]:
    """Settle every authored site decision at one chronological boundary.

    The site-owner operation the merged population coordinator calls at each
    boundary it merges. A site with no durable state yet is populated for the
    first time at this tick; a populated site whose last own member's committed
    loss boundary has been reached is marked cleared at exactly this tick
    (skipped while a persisted combat session still references one of its
    individuals, so a committed defeat settles before the site is declared
    clear); a cleared recoverable site repopulates when its authored in-game
    condition matured at this tick. Liveness is the projected owned-ID
    presence, so no member is resurrected and absence alone never clears a
    site. One-shot sites never recover, and no pass writes anything for a site
    whose state did not change. A present record that cannot be interpreted
    raises the population owner's named malformed-state refusal before any
    write. No wilderness script means no world to settle, and the pass returns
    silently. Sites settle in stable key order.
    """
    wilderness = _wilderness()
    if wilderness is None:
        return []
    states = _state_map(wilderness)
    events: list[ScheduledEvent] = []
    changed = False
    for key in sorted(MONSTER_SITE_REGISTRY):
        site = MONSTER_SITE_REGISTRY[key]
        record = states.get(key)
        if record is None:
            if _birth_cell_protected(wilderness, site, tick):
                # An encounter owns this cell during the evaluated interval:
                # no individual is placed, and the site retries at the next
                # interval start once protection has passed.
                continue
            seed = _site_seed(wilderness, site)
            created = _populate(
                wilderness, site, seed=seed, sequence=0, tick=tick
            )
            states[key] = _populated_record(seed, 0, created)
            changed = True
            _emit(
                "monster_site_populated",
                _site_context(site, tick=tick, created=len(created)),
            )
            continue
        state = _require_state(site, record)
        seed, saved_sequence = _require_occurrence(site, record)
        member_ids = _require_member_ids(site, record)
        if state == SITE_STATE_POPULATED:
            if _living_member_ids(wilderness, site, tick):
                continue
            members = _members_from_ids(site, member_ids)
            if members and _session_participant_ids().intersection(
                member.pk for member in members
            ):
                # A committed combat session still owns this defeat: the
                # clearing decision waits for the session to settle.
                continue
            clear_tick = _clear_boundary(wilderness, site, tick)
            if clear_tick is None or clear_tick > tick:
                clear_tick = tick
            # The defeated identities stay recorded: they are the site's
            # ownership history and no recovered group may reuse them.
            states[key] = {
                **record,
                "state": SITE_STATE_CLEARED,
                "cleared_at_tick": clear_tick,
            }
            changed = True
            _emit(
                "monster_site_cleared",
                _site_context(site, tick=tick, cleared_at_tick=clear_tick),
            )
            continue
        if site.one_shot:
            continue
        if not _condition_matured(site, record.get("cleared_at_tick"), tick):
            continue
        if _recovery_refusal(wilderness, site, record, tick) is not None:
            continue
        if _birth_cell_protected(wilderness, site, tick):
            continue
        created = _apply_recovery(
            wilderness,
            states,
            site,
            seed=seed,
            sequence=saved_sequence + 1,
            tick=tick,
        )
        changed = True
        composition = ENCOUNTER_COMPOSITION_REGISTRY[site.composition_key]
        events.append(
            ScheduledEvent(
                "monster_site_recovered",
                tick,
                {
                    "site": key,
                    "variants": list(composition_variant_keys(composition)),
                    "created": len(created),
                    "tick": tick,
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
