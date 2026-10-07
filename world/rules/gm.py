"""Validated operator adapters to the deterministic inventory/trait/clock owners."""

from django.db import transaction

from server.console.errors import ConsoleError
from server.console.validation import integer, resolve_target, text
from world.lore.items import ITEM_REGISTRY
from world.rules import equipment
from world.rules.clock import AdvanceSource, MAX_ADVANCE_SECONDS, read_world_clock, _flush_deleted_instance, _flush_rolled_back_instances
from world.rules.surfaces import snapshot_attributes, restore_attributes, snapshot_traits, restore_traits


def _identity(entity):
    return {"target": f"#{entity.pk}"}


def _inventory(target, key, quantity, *, removing):
    entity = resolve_target(target, {"characters"})
    text(key)
    integer(quantity, minimum=1)
    if key not in ITEM_REGISTRY:
        raise ConsoleError("registry_key_not_found")
    if removing and list(entity.db.inventory or []).count(key) < quantity:
        raise ConsoleError("invalid_argument")
    from world.quests.transitions import snapshot_pin_reasons, restore_pin_reasons
    from world.quests.settlement import plan_auto_settlement_chain

    surfaces = snapshot_attributes(entity, ("inventory", "equipment", "buffs", "wallet", "guild_reward_claims", "quest_log"))
    traits = snapshot_traits(entity)
    mirrors = [(obj, obj.pk) for obj in entity.contents if equipment.registry_key_for_object(obj) == key][:quantity] if removing else []
    created = []
    pins = []
    try:
        with transaction.atomic():
            if removing and equipment.equipped_removal_conflict(entity, (key,) * quantity) is not None:
                result = equipment.toggle_equipment(entity, key)
                if result.outcome != "success":
                    raise ConsoleError("invalid_argument")
            plan = equipment.plan_inventory_delta(entity, removals=(key,) * quantity if removing else (), additions=() if removing else (key,) * quantity)
            pin_operations = list(equipment._acquire_pins(plan))
            if plan.acquire is not None:
                settlement = plan_auto_settlement_chain(entity, list(entity.db.quest_log or []), list(plan.acquire[0]))
                pin_operations.extend(settlement.chain_pins)
            pins = [(room, snapshot_pin_reasons(room)) for room in dict.fromkeys(room for room, _, _ in pin_operations)]
            equipment.apply_inventory_plan(plan)
            if removing:
                for obj, _ in mirrors:
                    if not obj.delete():
                        raise RuntimeError("item deletion refused")
            else:
                for _ in range(quantity):
                    created.append(equipment.materialize_registry_object(entity, key))
    except Exception:
        restore_attributes(entity, surfaces)
        restore_traits(entity, traits)
        for room, before in pins:
            restore_pin_reasons(room, before)
        for obj, pk in (*mirrors, *((obj, obj.pk) for obj in created)):
            _flush_deleted_instance(obj)
        _flush_rolled_back_instances()
        entity.contents_cache.init()
        raise
    return _identity(entity)


def give_item(target, key, quantity):
    return _inventory(target, key, quantity, removing=False)


def take_item(target, key, quantity):
    return _inventory(target, key, quantity, removing=True)


def set_wallet(target, copper):
    entity = resolve_target(target, {"characters"})
    integer(copper)
    before = snapshot_attributes(entity, ("wallet",))
    try:
        with transaction.atomic():
            entity.db.wallet = copper
    except Exception:
        restore_attributes(entity, before)
        raise
    return _identity(entity)


def _trait_entity(target, key):
    entity = resolve_target(target, {"characters", "monsters"})
    text(key)
    trait = entity.traits.get(key)
    if trait is None:
        raise ConsoleError("registry_key_not_found")
    return entity, trait


def _base_band(entity, key):
    from typeclasses.monsters import Monster
    from world.lore.monsters import MONSTER_TIER_REGISTRY
    from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
    from world.rules.traits import GAUGE_KEYS

    if key == "guild_merit":
        return (0, None)
    if isinstance(entity, Monster):
        tier = MONSTER_TIER_REGISTRY.get(entity.threat_tier)
        if tier is None:
            raise ConsoleError("registry_key_not_found")
        if key == "hp":
            return tier.hp_band
        if key in {"mp", "sp"}:
            return (0, None)
        return getattr(tier.static_band, key)
    race = RACE_REGISTRY.get(entity.attributes.get("race"))
    if race is None:
        raise ConsoleError("registry_key_not_found")
    band = getattr(race.vital_baseline if key in GAUGE_KEYS else race.static_baseline, key)
    subrace = SUBRACE_REGISTRY.get(entity.attributes.get("subrace"))
    if subrace is not None and subrace.vital_overrides and key in subrace.vital_overrides:
        band = subrace.vital_overrides[key]
    return band


def set_trait_base(target, trait, value):
    from world.rules.traits import TRAIT_KEYS, GAUGE_KEYS, GAUGE_REGEN_RATE_PCT

    entity, selected = _trait_entity(target, trait)
    if trait not in TRAIT_KEYS:
        raise ConsoleError("registry_key_not_found")
    lower, upper = _base_band(entity, trait)
    integer(value, minimum=lower, maximum=upper)
    before = snapshot_traits(entity)
    try:
        with transaction.atomic():
            selected.base = value
            if trait in GAUGE_KEYS:
                selected.rate = value * GAUGE_REGEN_RATE_PCT
                selected.current = min(selected.current, selected.max)
                equipment.sync_equipment_gauge_limits(entity)
    except Exception:
        restore_traits(entity, before)
        raise
    return _identity(entity)


def set_gauge(target, gauge, value):
    from world.rules.traits import GAUGE_KEYS

    entity, selected = _trait_entity(target, gauge)
    if gauge not in GAUGE_KEYS or selected.trait_type != "gauge":
        raise ConsoleError("registry_key_not_found")
    integer(value, minimum=int(selected.min), maximum=selected.max)
    before = snapshot_traits(entity)
    try:
        with transaction.atomic():
            selected.current = value
    except Exception:
        restore_traits(entity, before)
        raise
    return _identity(entity)


def advance_clock(seconds):
    from typeclasses.entities import LivingEntity

    integer(seconds, maximum=MAX_ADVANCE_SECONDS)
    clock = read_world_clock()
    if clock is None:
        raise ConsoleError("target_not_found")
    entities = tuple(LivingEntity.objects.all_family())
    clock.advance(seconds, AdvanceSource.GM, entities)
    return {"target": "world", "tick": clock.tick}
