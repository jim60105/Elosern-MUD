"""Deterministic wilderness monster population model and spawn service
(wilderness-monster-population).

A pure, closed-form coordinate-to-monster mapping mirrors the terrain model
(``region_for_coordinates`` / ``terrain_description``): the same large-hash
multipliers, no LLM, no RNG, no database reads. A guaranteed hunting band around
``capital_altoria``'s wilderness entry always hosts a low-tier monster, so the
introductory hunt (討伐低階魔物) is completable immediately after leaving the
East Gate.

``ensure_population`` is the idempotent spawn/respawn service and the sole
writer of wilderness monster presence. It registers created ``Monster`` objects
in the wilderness script's ``itemcoordinates`` (never room contents, which the
contrib's pooled-room design would strand), and it reconciles only monsters it
owns via the ``population_key`` marker so future scripted encounters, bosses,
or event content are never deleted, moved, or modified.

Two disjoint ambient branches cover the bounded map (monster-site-placement
design D-P5): a coordinate whose region carries an authored species placement
rule (``world.lore.monster_placement``) is reconciled by that rule, building
species-bearing individuals through the one construction entry point, and every
other coordinate keeps the tier-example model above exactly as it was. The
hunting band always stays with the tier-example branch, so the introductory
hunt's pinned behaviour is untouched until species content covers the whole
map. Both branches use this module's one ownership marker, and neither ever
acts on a site-, quest-, story-, session-, or foreign-owned monster.
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from collections.abc import Iterable

from django.db import transaction
from evennia.utils.create import create_object

from world.observability import log_info, log_warn
from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    AMBIENT_PLACEMENT_REGISTRY,
    AmbientPlacementRule,
    variant_species_key,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore import wilderness_entry as _wilderness_entry_module
from world.rules.monster_individual import construct_species_individual
from world.maps.wilderness_provider import region_for_coordinates
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    is_valid_wilderness_cell,
)
from world.lore.monster_visuals import BASELINE_VISUAL_ROWS
from world.rules.surfaces import persisted_hp as _persisted_hp

# D-2 / wilderness-anchor-footprint: the entry coordinate is the capital's
# EAST-GATE approach cell -- the exterior cell a traveler lands on leaving 東門
# toward the open wilderness -- read from the entry registry rather than
# duplicated (AGENTS.md: consumers read registry values). The old (60, 100) is
# a footprint cell the provider refuses, and the capital's second gate is the
# 東門 since altoria-capital-replan, so the hunting band centers here; the
# introductory hunt stays reliably completable straight outside the East Gate.
# Read by both the model (band membership) and the tests. The gate approach
# cell needs the published frame bounds, so it is resolved on first use
# (``CAPITAL_ENTRY_XY`` stays the module attribute consumers read) instead of
# deriving map state at import.
def capital_entry_xy() -> tuple[int, int]:
    """The hunting-band centre: the capital's east-gate approach cell."""

    entry = _wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
    return entry.approach_cell(entry.gate_for("w"))


def __getattr__(name: str):
    if name == "CAPITAL_ENTRY_XY":
        return capital_entry_xy()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# D-2: immutable region tables, covering every key of WILDERNESS_REGION_REGISTRY.
# MappingProxyType enforces the spec's "immutable mapping" contract at runtime,
# so a same-process consumer cannot silently rebalance the closed model.
_REGION_TIER = MappingProxyType({
    "western_hills_valleys": "low",
    "southwest_coast": "low",
    "southeast_coast": "low",
    "eastern_plains": "low",
    "northwest_highland_forest": "mid",
    "north_deep_forest": "high",
    "central_mountains": "high",
})

_REGION_DENSITY = MappingProxyType({
    "western_hills_valleys": 6,
    "southwest_coast": 3,
    "southeast_coast": 3,
    "eastern_plains": 3,
    "northwest_highland_forest": 7,
    "north_deep_forest": 8,
    "central_mountains": 8,
})

# D1: baseline visual keys corresponding to (low, mid, high, calamity) bands
_TIER_VISUAL_ROWS = MappingProxyType({
    "low": BASELINE_VISUAL_ROWS[0:3],
    "mid": BASELINE_VISUAL_ROWS[3:6],
    "high": BASELINE_VISUAL_ROWS[6:9],
    "calamity": BASELINE_VISUAL_ROWS[9:12],
})

_HUNTING_BAND_DISTANCE = 3
_HASH_MULTIPLIER_X = 92821
_HASH_MULTIPLIER_Y = 68917


@dataclass(frozen=True)
class MonsterPopulation:
    """One deterministic monster the wilderness hosts at a coordinate."""

    tier: str
    art_species_key: str
    name_zh: str
    combat_traits: tuple[str, ...] = ()


def _coordinate_hash(x: int, y: int) -> int:
    """Return the closed-form coordinate hash shared with the terrain model."""
    return x * _HASH_MULTIPLIER_X + y * _HASH_MULTIPLIER_Y


def _in_hunting_band(x: int, y: int) -> bool:
    """Return whether ``(x, y)`` is within Chebyshev distance 3 of the entry."""
    entry_x, entry_y = capital_entry_xy()
    return max(abs(x - entry_x), abs(y - entry_y)) <= _HUNTING_BAND_DISTANCE


def population_for_coordinates(x: int, y: int) -> MonsterPopulation | None:
    """Return the deterministic monster population at ``(x, y)``, or ``None``.

    Pure closed-form arithmetic on the two coordinates alone -- no database
    read, no RNG, no wall-clock input. Coordinates inside the hunting
    band around ``CAPITAL_ENTRY_XY`` are always present at ``low`` tier;
    elsewhere presence is ``(x * 92821 + y * 68917) % 10 < density`` and the
    name is ``(x * 92821 + y * 68917) % len(example_monsters_zh)`` on every
    branch, hunting band included.
    """
    if _in_hunting_band(x, y):
        tier = "low"
    else:
        region = region_for_coordinates(x, y)
        tier = _REGION_TIER[region]
        if _coordinate_hash(x, y) % 10 >= _REGION_DENSITY[region]:
            return None
    examples = MONSTER_TIER_REGISTRY[tier].example_monsters_zh
    visual_rows = _TIER_VISUAL_ROWS[tier]
    idx = _coordinate_hash(x, y) % len(examples)
    selected_visual = visual_rows[idx]
    return MonsterPopulation(
        tier=tier, art_species_key=selected_visual.stable_key, name_zh=examples[idx]
    )


def _population_key(x: int, y: int) -> str:
    """Return the ownership marker this service stamps on every created monster."""
    return f"wilderness:{x}:{y}"


def ambient_slots_in_use(wilderness, coordinates: tuple[int, int]) -> set[int]:
    """The population slots the ambient individuals at ``coordinates`` claim.

    A slot is an individual's observation identity, stamped once at
    construction and never reassigned, so any second creator at the same
    coordinate must pick a free slot from this set -- otherwise two living
    individuals would share one identity.
    """
    marker = _population_key(*coordinates)
    slots: set[int] = set()
    for obj in wilderness.get_objs_at_coordinates(coordinates):
        if not isinstance(obj, Monster) or obj.db.population_key != marker:
            continue
        slot = obj.db.population_slot
        if isinstance(slot, int) and not isinstance(slot, bool):
            slots.add(slot)
    return slots


def _emit_ambient(event: str, context: Mapping[str, object]) -> None:
    """Schedule one ambient decision event on the enclosing durable commit.

    Room preparation runs inside transactional movement, so a boundary line for
    a placement that the transaction then rolled back must never be written
    (the same commit contract ``clock_advance`` follows).
    """
    frozen = dict(context)
    transaction.on_commit(lambda: log_info(event, context=frozen))


def species_rule_for_coordinates(x: int, y: int) -> AmbientPlacementRule | None:
    """The authored species placement rule covering ``(x, y)``, or ``None``.

    A coordinate is covered by *exactly one* ambient branch (design D-P5):
    coordinates inside the hunting band stay with the tier-example branch
    because their cells are contract-pinned to the introductory hunt, and a
    region without an authored rule keeps its tier-example behaviour until
    species content covers it.
    """
    if _in_hunting_band(x, y):
        return None
    return AMBIENT_PLACEMENT_REGISTRY.get(region_for_coordinates(x, y))


def ambient_variant_for_slot(
    rule: AmbientPlacementRule, x: int, y: int, slot: int
) -> str:
    """The variant the rule's ``slot`` selects at ``(x, y)`` -- pure and shared.

    The same closed-form coordinate hash the terrain and tier models use, mixed
    with the rule's authored determinism salt and the individual's creation
    slot: no RNG, no database state, and no wall clock, so the same coordinate
    selects the same variant in every process.
    """
    index = (
        _coordinate_hash(x, y) + rule.selection_salt + slot
    ) % len(rule.variant_keys)
    return rule.variant_keys[index]


def _stored_hp(monster: Monster) -> float:
    """Read the monster's stored HP without advancing a wall-clock gauge."""
    return _persisted_hp(monster)


@dataclass(frozen=True, slots=True)
class PopulationFact:
    """One entity visible in the wilderness population view."""

    observation_key: str
    cell: tuple[int, int]
    kind: str
    hostile: bool
    label: str


@dataclass(frozen=True, slots=True)
class ExpectedSlot:
    """One deterministic slot expected by ambient population rules."""

    slot: int
    observation_key: str
    name_zh: str
    tier: str
    art_species_key: str | None = None
    species_key: str | None = None
    variant_key: str | None = None
    combat_traits: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PopulationDecision:
    """The immutable ambient population decision for one wilderness coordinate.

    Reconciliation and the read-only population view both consume this common decision.
    """

    coordinates: tuple[int, int]
    branch: str  # "hunting_band", "species", "baseline", "none"
    rule: AmbientPlacementRule | None
    expected_baseline: MonsterPopulation | None
    slots: tuple[ExpectedSlot, ...]
    assigned: tuple[tuple[ExpectedSlot, Monster | None], ...]
    is_session_protected: bool
    living_ambient: tuple[Monster, ...]
    stale_ambient: tuple[Monster, ...]
    spawns_needed: tuple[ExpectedSlot, ...]


def ambient_observation_key(
    wilderness_name: str, x: int, y: int, branch: str, slot: int
) -> str:
    """Format the stable observation key for an ambient population slot."""
    return f"population:{wilderness_name}:{x}:{y}:{branch}:{slot}"


def ambient_population_decision(
    wilderness,
    coordinates: tuple[int, int],
    *,
    session_participants: frozenset[int] | None = None,
    existing_objs: Iterable[Any] | None = None,
    capital_entry: tuple[int, int] | None = None,
) -> PopulationDecision:
    """Calculate the pure immutable population decision for one coordinate.

    Consumes currently registered objects and active combat sessions to determine
    living occupancy, stale cleanup, and missing slot deficit under the shared rules.
    """
    x, y = coordinates
    wilderness_name = WILDERNESS_NAME
    marker = _population_key(x, y)

    if existing_objs is None:
        matching = [
            obj
            for obj in wilderness.get_objs_at_coordinates(coordinates)
            if isinstance(obj, Monster) and obj.db.population_key == marker
        ]
    else:
        matching = [
            obj
            for obj in existing_objs
            if isinstance(obj, Monster) and obj.db.population_key == marker
        ]

    if session_participants is None:
        session_participants = _session_participant_ids()

    is_protected = bool(matching and any(m.pk in session_participants for m in matching))

    rule = species_rule_for_coordinates(x, y)
    if rule is not None:
        branch = "species"
        target = min(rule.quantity, rule.capacity)
        from world.lore.monster_species import MONSTER_VARIANT_REGISTRY

        expected_slots: list[ExpectedSlot] = []
        for slot in range(target):
            v_key = ambient_variant_for_slot(rule, x, y, slot)
            v_row = MONSTER_VARIANT_REGISTRY.get(v_key)
            name_zh = v_row.display_name_zh if v_row else v_key
            tier = v_row.threat_tier if v_row else "low"
            s_key = variant_species_key(v_key)
            obs_key = ambient_observation_key(wilderness_name, x, y, branch, slot)
            expected_slots.append(
                ExpectedSlot(
                    slot=slot,
                    observation_key=obs_key,
                    name_zh=name_zh,
                    tier=tier,
                    art_species_key=None,
                    species_key=s_key,
                    variant_key=v_key,
                )
            )

        living: list[Monster] = []
        stale: list[Monster] = []
        for m in matching:
            if m.species_key and _persisted_hp(m) > 0:
                living.append(m)
            else:
                stale.append(m)

        # Sort living deterministically by pk so a repeated slot stays stable
        living.sort(key=lambda obj: int(getattr(obj, "pk", 0) or 0))

        # The persisted slot is the individual's observation identity, assigned
        # once at construction. Matching survivors by variant would hand a dead
        # individual's identity to whoever survives it, corrupting every
        # before/after sight comparison; the slot is validated here and never
        # reassigned. Members outside the expected slots (supplementary
        # provisioning, legacy reads) keep their own object identity and stay
        # living, but occupy no slot.
        expected_by_slot = {entry.slot: entry for entry in expected_slots}
        occupied: dict[int, Monster] = {}
        for m in living:
            slot = m.db.population_slot
            if (
                isinstance(slot, int)
                and not isinstance(slot, bool)
                and slot in expected_by_slot
                and slot not in occupied
            ):
                occupied[slot] = m

        assigned_pairs = tuple(
            (slot_entry, occupied.get(slot_entry.slot))
            for slot_entry in expected_slots
        )
        vacant_slots = tuple(
            slot_entry
            for slot_entry in expected_slots
            if slot_entry.slot not in occupied
        )
        # Spawn only into genuinely vacant slots, and never beyond the authored
        # quantity, so a surplus living member can never be doubled.
        budget = max(0, target - len(living))
        spawns_needed = () if is_protected else vacant_slots[:budget]

        return PopulationDecision(
            coordinates=coordinates,
            branch=branch,
            rule=rule,
            expected_baseline=None,
            slots=tuple(expected_slots),
            assigned=tuple(assigned_pairs),
            is_session_protected=is_protected,
            living_ambient=tuple(living),
            stale_ambient=tuple(stale),
            spawns_needed=spawns_needed,
        )

    # Not species rule: hunting band or baseline model
    in_band = (
        max(abs(x - capital_entry[0]), abs(y - capital_entry[1])) <= _HUNTING_BAND_DISTANCE
        if capital_entry is not None
        else _in_hunting_band(x, y)
    )
    branch = "hunting_band" if in_band else "baseline"
    expected = population_for_coordinates(x, y)

    if expected is None:
        # A frozen (session-protected) pass keeps every living marker-matching
        # monster exactly as materialization does; only the dead ones are stale,
        # and no prospective replacement is reported.
        living = (
            sorted(
                (m for m in matching if _stored_hp(m) > 0),
                key=lambda obj: int(getattr(obj, "pk", 0) or 0),
            )
            if is_protected
            else []
        )
        living_pks = {m.pk for m in living}
        return PopulationDecision(
            coordinates=coordinates,
            branch="none",
            rule=None,
            expected_baseline=None,
            slots=(),
            assigned=(),
            is_session_protected=is_protected,
            living_ambient=tuple(living),
            stale_ambient=tuple(m for m in matching if m.pk not in living_pks),
            spawns_needed=(),
        )

    obs_key = ambient_observation_key(wilderness_name, x, y, branch, 0)
    slot0 = ExpectedSlot(
        slot=0,
        observation_key=obs_key,
        name_zh=expected.name_zh,
        tier=expected.tier,
        art_species_key=expected.art_species_key,
        combat_traits=expected.combat_traits,
    )

    # The slot-0 ambient individual is the one living, model-conformant member:
    # duplicates beyond the first stay registered but cannot occupy the slot.
    living = sorted(
        (m for m in matching if _stored_hp(m) > 0),
        key=lambda obj: int(getattr(obj, "pk", 0) or 0),
    )
    conformant = [m for m in living if _matches_expected(m, expected)]
    retained = conformant[0] if conformant else None
    living_pks = {m.pk for m in living}
    retained_pks = {retained.pk} if retained is not None else set()
    if is_protected:
        # A session freezes reconciliation, so materialization keeps every
        # living marker-matching monster -- drifted names/tiers and duplicates
        # included. Report exactly those and no prospective replacement.
        stale = tuple(m for m in matching if m.pk not in living_pks)
        living_ambient = tuple(living)
    else:
        stale = tuple(m for m in matching if m.pk not in retained_pks)
        living_ambient = (retained,) if retained is not None else ()

    assigned_pair = (slot0, retained)
    spawns_needed = () if (retained is not None or is_protected) else (slot0,)

    return PopulationDecision(
        coordinates=coordinates,
        branch=branch,
        rule=None,
        expected_baseline=expected,
        slots=(slot0,),
        assigned=(assigned_pair,),
        is_session_protected=is_protected,
        living_ambient=living_ambient,
        stale_ambient=stale,
        spawns_needed=spawns_needed,
    )


def _remove_monster(wilderness, monster: Monster) -> None:
    """Pop ``monster`` from the wilderness bookkeeping and delete it."""
    wilderness.db.itemcoordinates.pop(monster, None)
    monster.delete()


@dataclass(frozen=True)
class PopulationDepartureTicket:
    """A committed logical departure awaiting its physical deletion.

    ``revert`` undoes the logical departure (marker and bookkeeping back in
    place) both in-process and in the database; it is idempotent for a
    monster whose row no longer exists.
    """

    monster: Monster
    wilderness: Any
    saved_marker: str
    saved_coordinates: tuple[int, int] | None

    def revert(self) -> None:
        """Restore the marker and the bookkeeping entry."""
        if self.monster.pk is None:
            # A deleted settlement is never restored.
            return
        self.monster.db.population_key = self.saved_marker
        if self.saved_coordinates is not None:
            self.wilderness.db.itemcoordinates[self.monster] = (
                self.saved_coordinates
            )


def depart_population_monster(
    wilderness, monster: Monster
) -> PopulationDepartureTicket:
    """In-transaction departure phase for the defeat aftermath (D-C3).

    The defeat writer requests the departure, but this module stays the sole
    writer of the population lifecycle: the ownership marker is cleared and
    the bookkeeping entry dropped inside the caller's open transaction, so a
    settlement rollback restores the winner together with every other
    aftermath write — the population model reads the marker and the
    bookkeeping, not object lifetime. The physical ``delete()`` is
    deliberately NOT part of this primitive: Evennia cannot resurrect a
    deleted instance in-process (the idmapper cache is not transaction-aware,
    the same wall that keeps exam-opponent deletion post-commit), so the
    caller deletes the departed monster only after its transaction commits.
    A crash in that window leaves a marker-less live monster — the accepted
    restart-refresh risk the parent design already carries.

    Returns a :class:`PopulationDepartureTicket` whose ``revert`` serves both
    the caller's rollback path and the post-commit delete-failure recovery.
    """
    if not monster.db.population_key:
        raise ValueError(f"{monster} carries no population marker")
    saved_marker = monster.db.population_key
    saved_coordinates = wilderness.db.itemcoordinates.get(monster)
    monster.db.population_key = None
    wilderness.db.itemcoordinates.pop(monster, None)

    return PopulationDepartureTicket(
        monster=monster,
        wilderness=wilderness,
        saved_marker=saved_marker,
        saved_coordinates=saved_coordinates,
    )


def _spawn(wilderness, coordinates: tuple[int, int], expected: MonsterPopulation) -> None:
    """Create one fresh population monster registered at ``coordinates``."""
    x, y = coordinates
    monster = create_object(Monster, key=expected.name_zh)
    monster.threat_tier = expected.tier
    monster.art_species_key = expected.art_species_key
    monster.apply_monster_tier("floor")
    if expected.combat_traits:
        from world.rules.traits import set_combat_traits

        set_combat_traits(monster, expected.combat_traits)
    monster.db.population_key = _population_key(x, y)
    monster.db.population_slot = 0
    wilderness.db.itemcoordinates[monster] = coordinates
    room = wilderness.db.rooms.get(coordinates)
    if room is not None:
        monster.location = room


def _spawn_species_individual(
    wilderness,
    coordinates: tuple[int, int],
    variant_key: str,
    population_key: str,
    *,
    slot: int,
) -> Monster:
    """Create one species-bearing ambient individual through the construction owner.

    Identity comes from the approved species/variant registries (the variant's
    species key is read from the one variant registry, never duplicated here)
    and the numbers from the construction owner's balance-gated rule, so no
    species constant is restated in this module. The individual carries the
    same ambient ownership marker as the tier-example population and is
    registered in the wilderness bookkeeping like every other wilderness
    monster.

    ``slot`` is required: it is the individual's permanent observation
    identity, so a caller creating into a coordinate that already holds
    individuals must pass a free slot from :func:`ambient_slots_in_use`
    rather than silently reusing another individual's identity.
    """
    individual = construct_species_individual(
        variant_species_key(variant_key), variant_key
    )
    individual.db.population_key = population_key
    individual.db.population_slot = slot
    wilderness.db.itemcoordinates[individual] = coordinates
    room = wilderness.db.rooms.get(coordinates)
    if room is not None:
        individual.location = room
    return individual


def _reconcile_ambient_species(
    wilderness, coordinates: tuple[int, int], rule: AmbientPlacementRule
) -> None:
    """Reconcile the species-bearing ambient individuals of one coordinate.

    Only monsters carrying this coordinate's ambient ownership marker are
    considered. When a persisted active combat session references any matching
    monster, the whole pass is skipped. Stale and dead monsters are removed, and
    deficits up to the authored quantity/capacity are spawned using the shared
    immutable decision.
    """
    decision = ambient_population_decision(wilderness, coordinates)
    if decision.is_session_protected:
        return

    for monster in decision.stale_ambient:
        reason = "dead" if monster.species_key else "branch_migration"
        _remove_monster(wilderness, monster)
        _emit_ambient(
            "monster_ambient_removed",
            {
                "region": rule.region_key,
                "coordinate": coordinates,
                "species": monster.species_key,
                "variant": monster.variant_key,
                "reason": reason,
            },
        )

    population_key = _population_key(*coordinates)
    for slot_entry in decision.spawns_needed:
        individual = _spawn_species_individual(
            wilderness, coordinates, slot_entry.variant_key, population_key, slot=slot_entry.slot
        )
        _emit_ambient(
            "monster_ambient_placed",
            {
                "region": rule.region_key,
                "coordinate": coordinates,
                "species": individual.species_key,
                "variant": individual.variant_key,
            },
        )


def _matches_expected(monster: Monster, expected: MonsterPopulation) -> bool:
    """Return whether ``monster`` is a living, model-conformant population entry.

    The idempotency special case requires not just any living marker-matching
    monster but one that still matches the model -- so a tier or name that no
    longer matches (after a model or registry fix) is reconciled rather than
    kept stale. Compare the monster's stored tier and its key against the
    expected population to close the drift gap.
    """
    from world.rules.target_facts import get_combat_traits

    return (
        _stored_hp(monster) > 0
        and monster.threat_tier == expected.tier
        and getattr(monster, "art_species_key", None) == expected.art_species_key
        and monster.key == expected.name_zh
        and get_combat_traits(monster) == frozenset(expected.combat_traits)
    )


def _session_participant_ids() -> frozenset[int]:
    """Return the dbrefs referenced by any persisted active combat session.

    Defense in depth for ``ensure_population`` (fix-startup-session-restore-
    order D2): scans every ``PlayerCharacter``'s persisted ``active_combat``
    record and collects its participant dbrefs, so reconciliation can leave
    session-referenced monsters untouched. Records that cannot be parsed are
    skipped -- their dbrefs are unknown, so they protect nothing and the
    startup restore step handles them separately.
    """
    from typeclasses.characters import PlayerCharacter
    from world.rules.combat_session import from_storage

    participants: set[int] = set()
    for player in PlayerCharacter.objects.all_family():
        raw = player.db.active_combat
        if raw is None:
            continue
        try:
            record = from_storage(dict(raw))
        except Exception as error:
            log_warn(
                "combat_session_payload_unparseable_skip",
                exc=error,
                context={"char": player.key or str(player.pk), "key": "active_combat"},
            )
            continue
        participants.update(record.player_ids)
        participants.update(record.enemy_ids)
    return frozenset(participants)


def ensure_population(wilderness, coordinates: tuple[int, int]) -> None:
    """Reconcile one wilderness coordinate against its deterministic population.

    Two disjoint ambient branches cover the map: authored species placement rules
    or the tier-example model (hunting band and baseline). When a persisted active
    combat session references any marker-matching monster, reconciliation is skipped.
    When the model returns None, stale monsters are removed. Otherwise, the coordinate
    is reconciled to exactly one living, model-conformant monster.
    """
    x, y = coordinates
    rule = species_rule_for_coordinates(x, y)
    if rule is not None:
        _reconcile_ambient_species(wilderness, coordinates, rule)
        return

    decision = ambient_population_decision(wilderness, coordinates)
    if decision.is_session_protected:
        return

    if decision.expected_baseline is None:
        for monster in decision.stale_ambient:
            _remove_monster(wilderness, monster)
        return

    if len(decision.living_ambient) == 1 and not decision.stale_ambient:
        # Idempotency: exactly one living, model-conformant monster already exists
        return

    for monster in decision.stale_ambient:
        _remove_monster(wilderness, monster)

    if decision.spawns_needed:
        _spawn(wilderness, coordinates, decision.expected_baseline)


def population_view(
    wilderness,
    cells: Iterable[tuple[int, int]],
) -> tuple[PopulationFact, ...]:
    """Project visible population facts across requested cells without mutating state.

    Consumes the shared ``ambient_population_decision`` for ambient slots and
    ``site_living_members`` for monster sites. Foreign registered entities keep
    their stable ``object:<dbid>`` identities, and so does every ambient
    monster that cannot occupy an expected slot -- a retained member of a
    frozen (session-protected) pass, a drifted survivor, or an individually
    provisioned extra -- because those objects are what materialization keeps.
    """
    from typeclasses.characters import PlayerCharacter
    from typeclasses.npcs import LLMNPC, NPC
    from world.maps.monster_sites import site_living_members

    target_cells = set(cells)
    if not target_cells:
        return ()

    wilderness_name = WILDERNESS_NAME

    # 1. Single pass over itemcoordinates to index registrations by cell for requested cells
    items_by_cell: dict[tuple[int, int], list[Any]] = {c: [] for c in target_cells}
    for obj, coords in (wilderness.db.itemcoordinates or {}).items():
        if obj is not None and coords in target_cells:
            items_by_cell[coords].append(obj)

    # 2. Cache session participants and capital entry once for the view pass
    session_participants = _session_participant_ids()
    cap_entry = capital_entry_xy()

    # Cache site living members per site encountered
    site_members_cache: dict[str, set[int]] = {}

    facts: list[PopulationFact] = []

    for cell in sorted(target_cells):
        if not is_valid_wilderness_cell(cell):
            # Materialization never happens on impassable or invalid wilderness cells
            continue

        cell_objs = items_by_cell[cell]

        # A. Ambient decision for this cell
        decision = ambient_population_decision(
            wilderness,
            cell,
            session_participants=session_participants,
            existing_objs=cell_objs,
            capital_entry=cap_entry,
        )

        # Map living ambient monsters to their slots/keys. A prospective slot is
        # reported only when reconciliation may materialize it, which a frozen
        # (session-protected) decision never allows.
        assigned_living: set[int] = set()
        for slot_entry, monster in decision.assigned:
            if monster is not None:
                assigned_living.add(monster.pk)
                facts.append(
                    PopulationFact(
                        observation_key=slot_entry.observation_key,
                        cell=cell,
                        kind="monster",
                        hostile=True,
                        label=monster.key,
                    )
                )
            elif slot_entry in decision.spawns_needed:
                # Prospective slot
                facts.append(
                    PopulationFact(
                        observation_key=slot_entry.observation_key,
                        cell=cell,
                        kind="monster",
                        hostile=True,
                        label=slot_entry.name_zh,
                    )
                )

        # Retained living ambient monsters outside every assigned slot keep a
        # distinct stable object identity, so no living enemy is ever omitted.
        for m in decision.living_ambient:
            if m.pk not in assigned_living and m.pk is not None:
                facts.append(
                    PopulationFact(
                        observation_key=f"object:{m.pk}",
                        cell=cell,
                        kind="monster",
                        hostile=True,
                        label=m.key,
                    )
                )

        # B. Registered non-ambient entities (site monsters, foreign monsters, characters, npcs)
        ambient_marker = _population_key(*cell)
        for obj in cell_objs:
            pk = getattr(obj, "pk", None)
            if pk is None:
                continue

            if isinstance(obj, Monster):
                if obj.db.population_key == ambient_marker:
                    # Already handled by ambient decision
                    continue

                site_key = obj.db.site_key
                if site_key is not None:
                    if site_key not in site_members_cache:
                        res = site_living_members(site_key, wilderness=wilderness)
                        site_members_cache[site_key] = {m.pk for m in res.members}
                    if pk in site_members_cache[site_key]:
                        facts.append(
                            PopulationFact(
                                observation_key=f"object:{pk}",
                                cell=cell,
                                kind="monster",
                                hostile=True,
                                label=obj.key,
                            )
                        )
                    continue

                # Foreign monster
                if _persisted_hp(obj) > 0:
                    facts.append(
                        PopulationFact(
                            observation_key=f"object:{pk}",
                            cell=cell,
                            kind="monster",
                            hostile=True,
                            label=obj.key,
                        )
                    )
            elif isinstance(obj, PlayerCharacter):
                facts.append(
                    PopulationFact(
                        observation_key=f"object:{pk}",
                        cell=cell,
                        kind="character",
                        hostile=False,
                        label=obj.key,
                    )
                )
            elif isinstance(obj, (NPC, LLMNPC)):
                facts.append(
                    PopulationFact(
                        observation_key=f"object:{pk}",
                        cell=cell,
                        kind="npc",
                        hostile=False,
                        label=obj.key,
                    )
                )

    return tuple(facts)
