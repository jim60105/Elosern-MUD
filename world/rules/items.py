"""Deterministic item-use resolution (add-declarative-item-actions D1/D2/D9).

Item mechanics identity lives in the immutable lore registry; the ordered,
typed effect profile of every usable item lives in the validated
``rulebook/item_effects.yaml`` rulebook and is resolved through the
module-level map in ``world.rules.item_effects`` at call time. This module is
the sole writer of item-use state: a side-effect-free ``preflight_item_use()``
shared by presentation and settlement, one atomic plan application, and the
public out-of-combat facade that composes the item plan with the canonical
command-source clock advance inside one outer transaction and rollback
journal (mirroring ``cast_settlement``).

Targeting (add-item-effect-targeting): every effect resolves its targets
through the shared ``world.rules.targeting.resolve_targets`` with the
``TargetRequirement`` its scope maps to — the identical presence/alive/range/
faction pipeline a skill's targets pass — and group scopes expand through the
caller-supplied action context (battlefield shorthand in a session, room
occupants out of one). The rollback journal is multi-entity: per-touched-
entity traits, buffs, and sexual state keyed by primary key, with the
in-process cache drop running per captured entity.

A successful use emits one ``item_used`` EventLog entry per executed effect
step, in profile order, each carrying ``item_key``, ``consumable``, and the
per-family payload: gauge steps add ``stat`` plus the signed ``amount``
actually applied (never the configured magnitude), and status steps add
``status_keys`` plus the ``count`` actually applied or removed.
"""

from copy import deepcopy
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from django.db import transaction

from world.lore.items import ITEM_REGISTRY
from world.observability import log_warn
from world.quests.transitions import restore_quest_log, snapshot_quest_log
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    active_buff_keys_from_storage,
    apply_buff,
    remove_by_selector,
)
from world.rules.clock import (
    MAX_ADVANCE_SECONDS,
    AdvanceSource,
    ScheduledEvent,
    WorldClock,
    _flush_deleted_instance,
    _refresh_advance_entity_caches,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
    get_world_clock,
)
from world.rules.equipment import (
    apply_inventory_plan,
    plan_inventory_delta,
    registry_key_for_object,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules import item_effects
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
    StatusApplyEffect,
    StatusRemoveEffect,
    scope_targeting_rule,
)
from world.rules.pleasure import apply_pleasure_gain
from world.rules.status_display import (
    MissingDisplayMetadataError,
    display_for,
)
from world.rules.targeting import (
    Relation,
    RoomActionContext,
    expand_target_shorthand,
    resolve_targets,
)
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
    restore_traits,
    snapshot_traits,
)


class ItemUseError(ValueError):
    """An item-use settlement failed mid-application and was rolled back."""


class ItemUseReason(StrEnum):
    """Stable named rejection reasons for item-use preflight and settlement."""

    UNKNOWN_ITEM = "unknown_item"
    NOT_USABLE = "not_usable"
    ITEM_NOT_HELD = "item_not_held"
    HP_FULL = "hp_full"
    MP_FULL = "mp_full"
    NOT_ALIVE = "not_alive"
    NO_DEBUFFS = "no_debuffs"
    COMBAT_NOT_ALLOWED = "combat_not_allowed"
    UNKNOWN_EFFECT = "unknown_effect"
    ACTIVE_SESSION = "active_combat"
    MALFORMED_TRAITS = "malformed_traits"
    MALFORMED_INVENTORY = "malformed_inventory"
    SP_FULL = "sp_full"
    PLEASURE_FULL = "pleasure_full"
    NO_EFFECT = "no_effect"
    STATUS_BLOCKED = "status_blocked"
    NOTHING_TO_REMOVE = "nothing_to_remove"
    NO_TARGET = "no_target"
    TARGET_INVALID = "target_invalid"


@dataclass(frozen=True)
class ItemUseRequest:
    """The closed deterministic request to use one held item.

    ``target`` is the caller's single explicit choice for the whole use —
    consumed only by ``single``-scoped effects, never a sequence and never a
    group shorthand (design D1): an item's reach is fixed by the rulebook, so
    a list or shorthand would let the caller widen a single-scope item into
    an area item. Two single-scope effects share the one supplied target.
    """

    actor: Any
    item_key: str
    target: Any | None = None


@dataclass(frozen=True)
class ItemEffectStep:
    """One planned effect execution: what to run, on whom, with what payload.

    ``amount`` is the signed gauge delta actually applicable to the target's
    current state (never the configured magnitude) and is ``0`` for status
    steps. ``status_keys`` names the concrete status keys a status step
    touches — the applied key for an apply, the matched definition keys for
    a removal — and is empty for gauge steps.
    """

    effect: ItemEffect
    target: Any
    amount: int = 0
    status_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class ItemUsePlan:
    """The complete, immutable settlement computed by a side-effect-free preflight.

    ``steps`` holds one step per EFFECTIVE declared effect in profile order
    (design §5.1); an item whose every effect is ineligible never produces a
    plan. ``mirror_pk`` is the single existing contained-object mirror
    selected for consumption (``None`` for a key-only holding), never a
    fabricated object.
    """

    actor: Any
    item_key: str
    consumable: bool
    steps: tuple[ItemEffectStep, ...]
    mirror_pk: int | None


@dataclass(frozen=True)
class ItemUsePreflight:
    """The outcome of one side-effect-free eligibility check."""

    allowed: bool
    reason: ItemUseReason | None = None
    detail: str | None = None
    plan: ItemUsePlan | None = None


#: Every ``sexual_state``-category attribute the sexual surface writes,
#: snapshotted per touched entity by the journal. The handler-published state
#: lives in ``sexual_traits`` (category ``traits``); the climax pipeline
#: additionally stages ``pending_climax_extension`` — which
#: ``apply_pleasure_gain`` may write for a target mid-climax — plus the
#: identity/experience and per-turn fields that share the category. Capturing
#: the whole category (mirroring the shipped round-touched sexual surface)
#: keeps a rolled-back settlement byte-identical on every writer surface,
#: including the ``pending_climax_extension`` a handler-read-only rollback
#: test would otherwise leave behind as a phantom extension.
_SEXUAL_STATE_KEYS = (
    "virgin",
    "experience_types",
    "climax_turns",
    "pending_climax_extension",
)


def _entity_identity(entity: Any) -> tuple[str, int]:
    """Key one captured journal record by the entity's own identity.

    Primary key plus ``str`` identity: the assert on restore may only write a
    record back to the entity it came from, and an unsaved/pk-less entity
    still keys distinctly through ``id()``.
    """
    pk = getattr(entity, "pk", None) or getattr(entity, "id", None)
    if pk is None:
        return ("id", id(entity))
    return ("pk", int(pk))


@dataclass
class _EntitySnapshot:
    """The per-entity half of the rollback journal (design D3).

    Traits, buffs, and the full sexual surface for one touched entity — the
    surfaces every effect family can write on anyone the plan steps on.
    Restore asserts the identity of the entity it writes back to.
    """

    entity: Any
    traits: tuple[bool, Any] | None = None
    buffs: tuple[bool, Any] | None = None
    sexual_traits: tuple[bool, Any] | None = None
    sexual_state: dict[str, tuple[bool, Any]] = field(default_factory=dict)

    @classmethod
    def capture(cls, entity: Any) -> "_EntitySnapshot":
        """Snapshot this entity's writable surfaces, pre-write."""
        return cls(
            entity=entity,
            traits=snapshot_traits(entity),
            buffs=attribute_snapshot(entity, "buffs"),
            sexual_traits=attribute_snapshot(
                entity, "sexual_traits", category="traits"
            ),
            sexual_state={
                key: attribute_snapshot(entity, key, category="sexual_state")
                for key in _SEXUAL_STATE_KEYS
            },
        )

    def restore(self) -> None:
        """Write this entity's snapshot back, best-effort per surface."""
        entity = self.entity
        if self.traits is not None:
            restore_traits(entity, self.traits)
        if self.buffs is not None:
            restore_attribute_best_effort(entity, "buffs", self.buffs)
        if self.sexual_traits is not None:
            restore_attribute_best_effort(
                entity, "sexual_traits", self.sexual_traits, category="traits"
            )
        for key, surface in self.sexual_state.items():
            if surface is None:
                continue
            existed, value = surface
            if not existed:
                # The settlement (or the climax pipeline) created the
                # attribute after capture: the pre-write state was its
                # absence, so removal — not a value write — is the restore.
                try:
                    entity.attributes.remove(key, category="sexual_state")
                except Exception as error:
                    log_warn(
                        "rollback_restore_failed",
                        exc=error,
                        context={
                            "stage": "item_journal_attribute_remove",
                            "obj": str(entity),
                            "key": key,
                        },
                    )
                continue
            restore_attribute_best_effort(
                entity, key, surface, category="sexual_state"
            )


@dataclass
class ItemTouchedJournal:
    """Pre-write snapshots of every surface an item-use settlement may touch.

    Multi-entity since add-item-effect-targeting (design D3): ``entities``
    holds one per-entity record — traits, buffs, and the sexual surface —
    keyed by entity identity and captured for **every** entity the plan
    touches, the actor included, through the same capture path (no special
    case). Only the actor consumes, so the actor-owned surfaces (inventory,
    quest log, the deleted-mirror instance, and the contents-cache re-seed)
    are captured once, actor-only — a per-target capture would invite a
    restore that writes inventory onto a companion.

    The resolver captures this before any write (a lazy per-target capture
    taken after an earlier target's write cannot restore state that earlier
    step's cascade touched — pleasure moves four sexual values at once) and
    hands it to the caller on success, so an outer combat transaction whose
    later phase fails can restore the trait, inventory, quest-progress, buff,
    sexual, and mirror/contents/idmapper caches the resolver committed.
    Restoration is best-effort per surface with a logged diagnostic and is
    safe to run twice (idempotent value writes). The buff surface restores
    through the attribute handler, which Evennia's ``BuffHandler`` re-reads on
    every access, so live handler reads recover together with persistence.
    **The in-process cache drop runs per captured entity, not only the
    actor**: ``restore_traits`` alone clears only the trait cache, while
    ``_refresh_advance_entity_caches`` additionally pops the memoized
    ``entity.sexual`` handler off ``entity.__dict__`` — skipping the drop for
    a companion would roll back stored sexual state while leaving a stale
    in-memory ``companion.sexual`` readable in the same process.
    """

    actor: Any
    entities: dict[tuple[str, int], "_EntitySnapshot"] = field(default_factory=dict)
    inventory: tuple[bool, Any] | None = None
    quest_log: tuple[bool, Any] | None = None
    mirror: Any | None = None
    mirror_pk: int | None = None

    @classmethod
    def capture(cls, actor: Any, targets: Sequence[Any] = ()) -> "ItemTouchedJournal":
        """Snapshot every surface one settlement may reach, pre-write.

        ``targets`` is every entity the plan will step on; the actor is
        captured through the same per-entity path as any target (the plan
        steps the actor for self-scoped effects, so the actor is normally in
        ``targets`` already; dedup keeps one record either way).
        """
        journal = cls(
            actor=actor,
            inventory=attribute_snapshot(actor, "inventory"),
            quest_log=snapshot_quest_log(actor),
        )
        for entity in dict.fromkeys((actor, *targets)):
            journal.entities[_entity_identity(entity)] = _EntitySnapshot.capture(entity)
        return journal

    def note_mirror(self, mirror: Any) -> None:
        """Record the live mirror instance before its deletion."""
        self.mirror = mirror
        self.mirror_pk = mirror.id

    def restore(self) -> None:
        """Restore every snapshotted surface after a rolled-back settlement."""
        for identity, record in self.entities.items():
            entity = record.entity
            if _entity_identity(entity) != identity:
                # Identity assert (design Risks): a record may only be
                # written back to the entity it came from. A mismatch means
                # the journal data itself was corrupted (a crossed pairing);
                # writing either entity's snapshot onto the other would be a
                # silent data-destroying "fix", so the record is skipped with
                # a loud diagnostic instead.
                log_warn(
                    "rollback_restore_failed",
                    context={
                        "stage": "item_journal_identity",
                        "obj": str(entity),
                        "key": str(identity),
                    },
                )
                continue
            record.restore()
            try:
                _refresh_advance_entity_caches(entity)
            except Exception as error:
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={
                        "stage": "item_journal_entity_caches",
                        "obj": str(entity),
                        "key": "traits",
                    },
                )
        actor = self.actor
        if self.inventory is not None:
            restore_attribute_best_effort(actor, "inventory", self.inventory)
        if self.quest_log is not None:
            restore_quest_log(actor, self.quest_log)
        if self.mirror is not None:
            try:
                _flush_deleted_instance(self.mirror)
            except Exception as error:
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={
                        "stage": "item_journal_mirror_flush",
                        "obj": str(actor),
                        "key": str(self.mirror_pk),
                    },
                )
        try:
            contents_cache = getattr(actor, "contents_cache", None)
            if contents_cache is not None:
                contents_cache.init()
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "item_journal_contents_cache",
                    "obj": str(actor),
                    "key": "contents_cache",
                },
            )


@dataclass(frozen=True)
class ItemUseResult:
    """The result of one item-use resolution, shaped for round settlement."""

    outcome: Literal["success", "rejected"]
    event_log: EventLog | None = None
    time_cost_seconds: int = 0
    reason: ItemUseReason | None = None
    detail: str | None = None
    journal: ItemTouchedJournal | None = None


@dataclass(frozen=True)
class ItemUseSettlement:
    """The committed out-of-combat item use and its clock events."""

    result: ItemUseResult
    events: tuple[ScheduledEvent, ...] = ()


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


_FULL_REASON_BY_STAT: dict[ItemStat, ItemUseReason] = {
    ItemStat.HP: ItemUseReason.HP_FULL,
    ItemStat.MP: ItemUseReason.MP_FULL,
    ItemStat.SP: ItemUseReason.SP_FULL,
    ItemStat.PLEASURE: ItemUseReason.PLEASURE_FULL,
}
_GAUGE_NOUN_ZH: dict[ItemStat, str] = {
    ItemStat.HP: "生命值",
    ItemStat.MP: "魔力值",
    ItemStat.SP: "體力值",
    ItemStat.PLEASURE: "快感值",
}
_REMOVAL_NOUN_ZH: dict[str, str] = {
    "negative": "負面狀態",
    "positive": "增益狀態",
    "all": "狀態",
}


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


def _plan_gauge_step(
    effect: GaugeAdjustEffect, target: Any
) -> ItemEffectStep | ItemUseReason:
    """Compute the applicable signed delta for one gauge effect.

    Positive amounts restore up to the gauge maximum, negative amounts drain
    down to zero (design §5.3). An ineligible adjustment names its stat's
    bound-reached reason: a full gauge at the top reports ``*_FULL``; a
    drain blocked at zero reports the same stat code because the settlement
    vocabulary carries no separate floor code (tasks 4.4).
    """
    if effect.stat is ItemStat.PLEASURE:
        try:
            current = _pleasure_current(target)
        except TypeError:  # observability: ignore R2: malformed intimate storage fails closed as a validation rejection
            return ItemUseReason.MALFORMED_TRAITS
        maximum = 100
    else:
        gauge = _gauge_from_storage(target, effect.stat.value)
        if gauge is None:
            return ItemUseReason.MALFORMED_TRAITS
        current, maximum = gauge
    if effect.amount > 0:
        if current >= maximum:
            return _FULL_REASON_BY_STAT[effect.stat]
        return ItemEffectStep(effect=effect, target=target, amount=min(effect.amount, maximum - current))
    if current <= 0:
        return _FULL_REASON_BY_STAT[effect.stat]
    return ItemEffectStep(effect=effect, target=target, amount=max(effect.amount, -current))


def _status_matches(effect: StatusRemoveEffect) -> Callable[[str], bool]:
    """The definition-key predicate one removal selector names."""
    if effect.selector == "all":
        return lambda key: True
    if effect.selector == "negative":
        return lambda key: BUFF_DEFINITIONS[key].polarity == "debuff"
    if effect.selector == "positive":
        return lambda key: BUFF_DEFINITIONS[key].polarity == "buff"
    return lambda key: key == effect.selector


def _plan_status_step(
    effect: StatusApplyEffect | StatusRemoveEffect, target: Any
) -> ItemEffectStep | ItemUseReason:
    """Decide eligibility for one status effect without materializing handlers.

    An apply is blocked only by the same equipment-immunity gate
    ``apply_buff`` enforces for debuffs (grant-time polarity immunity). A
    removal is eligible when at least one active instance matches; the empty
    result of the ``negative`` selector keeps the shipped ``no_debuffs``
    code, every other empty removal names ``nothing_to_remove``.
    """
    if isinstance(effect, StatusApplyEffect):
        from world.rules.equipment_effects import equipment_immune_buff_keys

        definition = BUFF_DEFINITIONS.get(effect.status)
        if definition is None:
            # A profile injected past the loader naming an undefined status
            # fails closed like the scope seam, never as an unhandled
            # KeyError at the command/web boundary.
            return ItemUseReason.UNKNOWN_EFFECT
        if (
            definition.polarity == "debuff"
            and effect.status in equipment_immune_buff_keys(target)
        ):
            return ItemUseReason.STATUS_BLOCKED
        return ItemEffectStep(
            effect=effect, target=target, status_keys=(effect.status,)
        )
    try:
        matched = _active_matching_keys(target, _status_matches(effect))
    except TypeError:  # observability: ignore R2: a malformed buff cache is a validation rejection returned as malformed_traits
        return ItemUseReason.MALFORMED_TRAITS
    if not matched:
        return (
            ItemUseReason.NO_DEBUFFS
            if effect.selector == "negative"
            else ItemUseReason.NOTHING_TO_REMOVE
        )
    return ItemEffectStep(effect=effect, target=target, status_keys=matched)


def preflight_item_use(
    request: ItemUseRequest,
    *,
    in_combat: bool,
    context: Any | None = None,
) -> ItemUsePreflight:
    """Evaluate item-use eligibility against current state, writing nothing.

    Resolves the canonical registry definition and the profile's live
    effect-map entry, verifies at least one held key in the canonical
    inventory, validates the current mode against the definition, then
    computes one step per EFFECTIVE EFFECT-AND-TARGET pair in profile order
    (design §5.1/§5.2). Each effect resolves its targets through the shared
    ``resolve_targets`` with the requirement its scope maps to — the
    identical presence/alive/range/faction pipeline a skill's targets pass —
    and group scopes expand through the caller-supplied action context
    (battlefield roster shorthand in a session, room occupants out of one;
    design D2/D6). ``in_combat`` stays an independent parameter: it gates the
    item's ``combat_allowed`` permission, which is a question about the item,
    while the context is a question about the world. When ``context`` is
    omitted, resolution builds the room context from the actor's location —
    the exploration-side convenience; a resolving request in combat without a
    context is a caller error and raises ``TypeError`` rather than silently
    validating against the wrong world. A single-scope effect with no
    supplied target rejects ``no_target``; a rejected resolver rejects
    ``target_invalid`` carrying the resolver's own reason as ``detail``
    (design D5). An item whose every effect is ineligible against every of
    its targets rejects with the uniform bound reason when every step names
    the same one, otherwise with ``no_effect`` — one effective pair anywhere
    carries the whole use (design §5.4). It never mutates inventory, traits,
    quest state, equipment, combat state, clock, sexual state, or
    presentation.
    """
    definition = ITEM_REGISTRY.get(request.item_key)
    if definition is None:
        return _rejected(ItemUseReason.UNKNOWN_ITEM)
    mechanics = definition.use_mechanics
    if mechanics is None:
        return _rejected(ItemUseReason.NOT_USABLE)
    if in_combat and not mechanics.combat_allowed:
        return _rejected(ItemUseReason.COMBAT_NOT_ALLOWED)
    inventory = _inventory_list(request.actor)
    if inventory is None:
        return _rejected(ItemUseReason.MALFORMED_INVENTORY)
    if request.item_key not in inventory:
        return _rejected(ItemUseReason.ITEM_NOT_HELD)
    # Call-time resolution through the module attribute (never a name copy)
    # so reloads and the synthetic kit's scoped profile map reach settlement.
    profile = item_effects.ITEM_EFFECT_PROFILES.get(request.item_key)
    if not isinstance(profile, ItemEffectProfile):
        return _rejected(ItemUseReason.UNKNOWN_EFFECT)
    hp_gauge = _gauge_from_storage(request.actor, "hp")
    if hp_gauge is None:
        return _rejected(ItemUseReason.MALFORMED_TRAITS)
    if hp_gauge[0] <= 0:
        return _rejected(ItemUseReason.NOT_ALIVE)
    steps: list[ItemEffectStep] = []
    reasons: list[ItemUseReason] = []
    needs_resolution = any(
        effect.scope is not ItemTargetScope.SELF for effect in profile.effects
    )
    if context is None:
        # Legacy no-context callers keep working: out of combat the room
        # context is the only world view a preflight needs. In combat the
        # session's BattlefieldActionContext is mandatory the moment an
        # effect reaches beyond the actor (design D2).
        if in_combat and needs_resolution:
            raise TypeError(
                "preflight_item_use requires the caller's action context "
                "to resolve non-self scopes in combat (design D2); pass "
                "the BattlefieldActionContext the session already holds"
            )
        context = RoomActionContext(request.actor.location)
    for effect in profile.effects:
        resolved = _resolve_effect_targets(request, effect, context)
        if isinstance(resolved, ItemUsePreflight):
            return resolved
        for target in resolved:
            if isinstance(effect, GaugeAdjustEffect):
                step = _plan_gauge_step(effect, target)
            else:
                step = _plan_status_step(effect, target)
            if isinstance(step, ItemEffectStep):
                steps.append(step)
            else:
                reasons.append(step)
    if not steps:
        if len(reasons) == 1 or len(set(reasons)) == 1:
            return _rejected(reasons[0])
        return _rejected(ItemUseReason.NO_EFFECT)
    mirror = (
        _select_mirror(request.actor, request.item_key)
        if mechanics.consumable
        else None
    )
    plan = ItemUsePlan(
        actor=request.actor,
        item_key=request.item_key,
        consumable=mechanics.consumable,
        steps=tuple(steps),
        mirror_pk=mirror.id if mirror is not None else None,
    )
    return ItemUsePreflight(allowed=True, reason=None, plan=plan)


def _step_text(display_name: str, step: ItemEffectStep, applied: int) -> str:
    """Render one stable ``item_used`` line for one settled step."""
    effect = step.effect
    if isinstance(effect, GaugeAdjustEffect):
        noun = _GAUGE_NOUN_ZH[effect.stat]
        rendered = str(abs(applied)).replace("{", "{{").replace("}", "}}")
        if applied < 0:
            return f"你使用了「{display_name}」，失去了 {rendered} 點{noun}。"
        verb = "提升" if effect.stat is ItemStat.PLEASURE else "恢復"
        return f"你使用了「{display_name}」，{verb}了 {rendered} 點{noun}。"
    if isinstance(effect, StatusApplyEffect):
        try:
            label = display_for(effect.status).label
        except MissingDisplayMetadataError:  # observability: ignore R2: only a synthetic status lacks display coverage (the shipped coverage test forbids a gap); the raw key keeps the line deterministic instead of failing settlement for presentation
            label = effect.status
        label = label.replace("{", "{{").replace("}", "}}")
        return f"你使用了「{display_name}」，獲得了「{label}」狀態。"
    noun = _REMOVAL_NOUN_ZH.get(effect.selector, "狀態")
    verb = "淨化" if effect.selector == "negative" else "清除"
    return f"你使用了「{display_name}」，{verb}了 {applied} 個{noun}。"


def _item_used_event_log(
    plan: ItemUsePlan, actor_key: str, time_cost_seconds: int, settled: list[tuple[ItemEffectStep, int]]
) -> EventLog:
    """Build one ``item_used`` entry per settled step, in profile order.

    Every entry carries the item key, the consumable flag, and the per-family
    payload: the signed gauge delta actually applied, or the matched status
    keys plus the count actually applied/removed (settlement truth, never the
    preflight estimate). ``status_keys`` are the distinct definition keys
    involved; ``count`` counts buff **instances**, so a multi-instance
    ``unique_per_source`` removal (the same status from several items) reports
    the instance count over deduplicated keys by design. The shipped
    single-effect wording is reproduced byte-for-byte: a restored gauge
    renders the shipped 恢復 sentence.
    """
    definition = ITEM_REGISTRY[plan.item_key]
    display_name = definition.display_name_zh.replace("{", "{{").replace("}", "}}")
    entries: list[EventEntry] = []
    for step, applied in settled:
        effect = step.effect
        data: dict[str, Any] = {
            "item_key": plan.item_key,
            "consumable": plan.consumable,
        }
        if isinstance(effect, GaugeAdjustEffect):
            data["stat"] = effect.stat.value
            data["amount"] = applied
        else:
            data["status_keys"] = list(step.status_keys)
            data["count"] = applied
        entries.append(
            EventEntry(
                kind="item_used",
                actor=actor_key,
                target=str(step.target.key),
                data=data,
                text_template=_step_text(display_name, step, applied),
            )
        )
    return EventLog(
        actor=actor_key,
        skill_key=plan.item_key,
        targets=tuple(dict.fromkeys(str(step.target.key) for step, _ in settled)),
        entries=tuple(entries),
        time_cost_seconds=time_cost_seconds,
    )


def _write_gauge(entity: Any, gauge: str, value: int) -> None:
    """Set one gauge through the trait handler (deterministic clamping)."""
    trait = getattr(entity.traits, gauge)
    if hasattr(trait, "current"):
        trait.current = value
    else:
        trait.value = value


def _delete_mirror(actor: Any, plan: ItemUsePlan, journal: ItemTouchedJournal) -> None:
    """Delete exactly the selected contained mirror and journal the instance."""
    if plan.mirror_pk is None:
        return
    contents = getattr(actor, "contents", None)
    if contents is None:
        raise ItemUseError("actor lost its contents during item settlement")
    mirror = next((obj for obj in contents if obj.id == plan.mirror_pk), None)
    if mirror is None:
        raise ItemUseError(
            f"selected mirror {plan.mirror_pk} vanished during item settlement"
        )
    journal.note_mirror(mirror)
    mirror.delete()


def _apply_gauge_step(step: ItemEffectStep) -> int:
    """Write one gauge step and return the signed delta actually applied.

    Re-reads the gauge immediately before the write so the emitted amount is
    what actually moved, not the preflight estimate (design §5.7). The
    pleasure gauge routes through the shared ``apply_pleasure_gain`` writer
    (with its arousal-coupled cascade); every other gauge writes the trait
    handler directly.
    """
    effect = step.effect
    assert isinstance(effect, GaugeAdjustEffect)
    if effect.stat is ItemStat.PLEASURE:
        before = _pleasure_current(step.target)
        apply_pleasure_gain(step.target, step.amount)
        after = _pleasure_current(step.target)
        return after - before
    gauge = _gauge_from_storage(step.target, effect.stat.value)
    if gauge is None:
        # Storage went malformed mid-transaction: fail closed so the outer
        # journal restores every surface instead of writing a guessed value.
        raise ItemUseError(f"{effect.stat.value} gauge vanished during item settlement")
    current, maximum = gauge
    desired = max(0, min(maximum, current + step.amount))
    _write_gauge(step.target, effect.stat.value, desired)
    return desired - current


def _apply_status_step(step: ItemEffectStep, item_key: str) -> int:
    """Write one status step and return the count actually applied/removed.

    Applies route through the published ``apply_buff`` applier with the
    stable ``item:<item key>`` source identity so a ``unique_per_source``
    buff keys to this item's use; removals route through the published
    ``remove_by_selector`` applier. The returned count is the settled truth
    for the event payload.
    """
    effect = step.effect
    if isinstance(effect, StatusApplyEffect):
        definition = BUFF_DEFINITIONS[effect.status]
        source_key = f"item:{item_key}"
        instance_key: str | None = None
        if definition.stacking == "unique_per_source":
            instance_key = f"{effect.status}:{source_key}"
        data: dict[str, Any] = {"source_key": source_key}
        apply_buff(step.target, effect.status, instance_key=instance_key, **data)
        return 1
    assert isinstance(effect, StatusRemoveEffect)
    return remove_by_selector(step.target, effect.selector)


def _apply_plan(
    plan: ItemUsePlan, journal: ItemTouchedJournal
) -> list[tuple[ItemEffectStep, int]]:
    """Commit every planned step in order and return each step's applied count.

    Runs inside the caller's transaction. Each step reaches its own target
    through the published applier for its family (gauge trait write / shared
    pleasure writer / ``apply_buff`` / ``remove_by_selector``); the shipped
    single-effect gauge and cleanse items reproduce their exact prior write.
    Inventory removal goes through the inventory planner so ACQUIRE/quest
    journals compose with it; a key-only consumable deletes nothing and no
    mirror is ever fabricated.
    """
    settled: list[tuple[ItemEffectStep, int]] = []
    for step in plan.steps:
        if isinstance(step.effect, GaugeAdjustEffect):
            applied = _apply_gauge_step(step)
        else:
            applied = _apply_status_step(step, plan.item_key)
        settled.append((step, applied))
    if plan.consumable:
        apply_inventory_plan(
            plan_inventory_delta(plan.actor, removals=(plan.item_key,))
        )
    _delete_mirror(plan.actor, plan, journal)
    return settled


def resolve_item_use(
    request: ItemUseRequest, *, in_combat: bool, context: Any | None = None
) -> ItemUseResult:
    """Atomically settle one item use against current canonical state.

    Repeats preflight (a presented descriptor is advisory only), applies the
    complete multi-step effect/consumption plan inside one transaction, and
    restores the durable and in-process surfaces the journal captured —
    including the per-entity sexual surface a pleasure step writes, for
    **every** touched entity — on any failure before re-raising. A rejection
    performs no write and emits no EventLog, carrying the preflight detail
    (the resolver's own reason for a ``target_invalid``) unchanged.
    """
    preflight = preflight_item_use(request, in_combat=in_combat, context=context)
    if not preflight.allowed or preflight.plan is None:
        return ItemUseResult(
            outcome="rejected", reason=preflight.reason, detail=preflight.detail
        )
    plan = preflight.plan
    # Capture every entity the plan steps on before the first write (design
    # D3): a lazy per-target capture could not restore state an earlier
    # target's write cascade touched.
    journal = ItemTouchedJournal.capture(
        request.actor, [step.target for step in plan.steps]
    )
    try:
        with transaction.atomic():
            settled = _apply_plan(plan, journal)
    except Exception:
        journal.restore()
        raise
    event_log = _item_used_event_log(
        plan,
        str(request.actor.key),
        time_cost_seconds=0,
        settled=settled,
    )
    return ItemUseResult(
        outcome="success",
        event_log=event_log,
        time_cost_seconds=0,
        journal=journal,
    )


def use_item(
    actor: Any,
    item_key: str,
    *,
    target: Any | None = None,
    clock: WorldClock | None = None,
) -> ItemUseSettlement:
    """Settle one out-of-combat item use plus its canonical six-second cost.

    Repeats preflight, then wraps the complete item plan and the
    player-driven world's command-source advance in one outer transaction. On
    any failure the clock tick, every callback-owned advance surface, and the
    item journal's trait/inventory/quest/mirror caches are restored together
    — for every touched entity — before the exception propagates. ``target``
    is the caller's single explicit choice consumed by single-scope effects
    (design D1); resolution uses the room context built from the actor's
    location. An active combat session rejects with ``active_combat`` so item
    consumption can never bypass a combat round; a rejection advances no
    time.
    """
    from world.rules.combat_session import is_in_active_session

    if is_in_active_session(actor):
        return ItemUseSettlement(
            ItemUseResult(
                outcome="rejected", reason=ItemUseReason.ACTIVE_SESSION
            )
        )
    request = ItemUseRequest(actor=actor, item_key=item_key, target=target)
    preflight = preflight_item_use(
        request, in_combat=False, context=RoomActionContext(actor.location)
    )
    if not preflight.allowed:
        return ItemUseSettlement(
            ItemUseResult(
                outcome="rejected", reason=preflight.reason, detail=preflight.detail
            )
        )
    world_clock = clock if clock is not None else get_world_clock()
    registry = build_advance_snapshot_registry(
        world_clock, MAX_ADVANCE_SECONDS, AdvanceSource.COMMAND, (actor,)
    )
    tick_snapshot = _snapshot_clock_tick(world_clock)
    events: tuple[ScheduledEvent, ...] = ()
    result: ItemUseResult | None = None
    try:
        with transaction.atomic():
            result = resolve_item_use(
                request,
                in_combat=False,
                context=RoomActionContext(actor.location),
            )
            if result.outcome == "success":
                events = tuple(
                    world_clock.advance(
                        item_effects.ITEM_USE_SECONDS, AdvanceSource.COMMAND, (actor,)
                    )
                )
    except Exception:
        # The database rows are gone with the rolled-back transaction; the
        # clock seam restores the tick and every callback-owned surface from
        # the pre-transaction snapshots, and the item journal restores the
        # trait/inventory/quest caches plus the deleted-mirror idmapper and
        # contents caches — per captured entity for the multi-entity
        # surfaces. If the resolver itself failed it already restored its own
        # journal; re-running the restore is an idempotent write.
        _restore_clock_tick(world_clock, tick_snapshot)
        _restore_advance_registry(registry, (actor,))
        if result is not None and result.journal is not None:
            result.journal.restore()
        raise
    return ItemUseSettlement(result=result, events=events)
