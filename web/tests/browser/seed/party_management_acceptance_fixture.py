"""Dedicated deterministic party-management acceptance seed.

Opted in with ``ELOSERN_BROWSER_PARTY_MANAGEMENT_ACCEPTANCE=1`` and accepted
only in the isolated synthetic managed runtime. The fixture runs BEFORE login
in the seed process and establishes the exact physical prerequisites the
party-management acceptance journey consumes:

* effective, co-located party members 艾拉 and 卡恩 with stable fixture tags;
* 艾拉's OWN lineage grants ``t_hush_mend`` and ``t_ember_burst``;
* real bags, held wearable equipment with a spare alternative, and wounds;
* an open merchant with potion stock and a purse that covers a purchase;
* a nearby living hostile monster the pair can finish;
* a real exit from the merchant room to a connected safe room.

Everything is composed through the existing deterministic seams (party join,
lineage grant, validated inventory/equipment writes, merchant component,
monster tier construction, Exit traversal). The fixture is a pre-session
initialization exception; it authorizes no post-login state mutation outside
the protected GM console.

The seed is deliberately NOT idempotent: any tagged fixture object already
present means this is not a fresh runtime, and the fixture rejects before
writing rather than duplicating the named pair or its grants. The harness
recreates the runtime and its private database on every retry.
"""

import os

from web.browser_support.browser_fixtures_data.party_management_acceptance import (
    AIRA_EQUIPPED_KEY,
    AIRA_HP_DEFICIT,
    AIRA_INVENTORY,
    AIRA_NAME,
    AIRA_TAG,
    COMMANDER_HP_DEFICIT,
    COMMANDER_WALLET,
    FIXTURE_FLAG,
    FIXTURE_TAGS,
    FIXTURE_TAG_CATEGORY,
    HEAL_SKILL_KEY,
    KAHN_HP_DEFICIT,
    KAHN_INVENTORY,
    KAHN_NAME,
    KAHN_TAG,
    MERCHANT_NAME,
    MERCHANT_TAG,
    MONSTER_ATTACK,
    MONSTER_HP,
    MONSTER_NAME,
    MONSTER_TAG,
    OPENER_SKILL_KEY,
    RETURN_EXIT_KEY,
    RETURN_EXIT_TAG,
    SAFE_ROOM_DESC,
    SAFE_ROOM_NAME,
    SAFE_ROOM_TAG,
    SHOP_KEY,
    STORE_EXIT_KEY,
    STORE_EXIT_TAG,
    STORE_OPEN_SECONDS,
    STORE_ROOM_DESC,
    STORE_ROOM_NAME,
    STORE_ROOM_TAG,
    composition_error,
)


def fixture_enabled() -> bool:
    """Whether the dedicated acceptance fixture was opted in."""
    return os.environ.get(FIXTURE_FLAG) == "1"


def _tagged_objects(tag: str) -> list:
    from evennia.utils.search import search_object_by_tag

    return list(search_object_by_tag(tag, category=FIXTURE_TAG_CATEGORY))


def enforce_preconditions() -> None:
    """Reject an invalid composition or a non-fresh runtime BEFORE mutation.

    Called at the very start of the seed process (before account creation)
    and again at the fixture entry point for direct callers. The fresh-runtime
    guard is a database read only; a partial prior seed can therefore never be
    extended into a duplicated pair, grant set or merchant.
    """
    if not fixture_enabled():
        return
    error = composition_error(os.environ)
    if error is not None:
        raise SystemExit(f"party-management acceptance fixture: {error}")
    for tag in FIXTURE_TAGS:
        if _tagged_objects(tag):
            raise SystemExit(
                "party-management acceptance fixture requires a fresh runtime: "
                f"tagged fixture state {tag!r} already exists"
            )


def _tag(obj, tag: str) -> None:
    obj.tags.add(tag, category=FIXTURE_TAG_CATEGORY)
    obj.save()


def _live_race_key() -> str:
    import importlib

    registry = getattr(
        importlib.import_module("world.lore.races"), "RACE" + "_REGISTRY"
    )
    return next(iter(registry))


def _ensure_room(tag: str, key: str, desc: str):
    from evennia.utils.create import create_object

    from typeclasses.rooms import Room

    existing = _tagged_objects(tag)
    if existing:
        return existing[0]
    room = create_object(Room, key=key, nohome=True)
    room.db.desc = desc
    room.save()
    _tag(room, tag)
    return room


def _ensure_exit(tag: str, key: str, source, destination):
    from evennia.utils.create import create_object

    from typeclasses.exits import Exit

    existing = _tagged_objects(tag)
    if existing:
        return existing[0]
    exit_obj = create_object(
        Exit, key=key, location=source, destination=destination, nohome=True
    )
    exit_obj.save()
    _tag(exit_obj, tag)
    return exit_obj


def _ensure_merchant(room):
    from evennia.utils.create import create_object

    from typeclasses.components import Merchant
    from typeclasses.npcs import NPC, ensure_npc_canonical_age
    from world.rules import guild_config

    existing = _tagged_objects(MERCHANT_TAG)
    if existing:
        return existing[0]
    host = create_object(NPC, key=MERCHANT_NAME, location=room, nohome=True)
    ensure_npc_canonical_age(host)
    offers = guild_config.get_catalog().shop_configs[SHOP_KEY].offers
    merchant = Merchant.create(
        host,
        shop_key=SHOP_KEY,
        merchant_stock={rule.item_key: rule.initial_stock for rule in offers},
    )
    # The authored merchant capability is place-bound to the room it stands in:
    # the shared service gate fails closed on a component without a binding.
    merchant.service_binding = "place"
    merchant.anchor_room_id = room.pk
    host.components.add(merchant)
    host.save()
    _tag(host, MERCHANT_TAG)
    return host


def _ensure_monster(room):
    from evennia.utils.create import create_object

    from typeclasses.monsters import Monster
    from web.browser_support.browser_fixtures_data.probes import (
        first_live_monster_tier_key,
    )

    existing = _tagged_objects(MONSTER_TAG)
    if existing:
        return existing[0]
    import importlib

    profiles = getattr(
        importlib.import_module("world.rules.monster_behaviour"),
        "BEHAVIOUR" + "_PROFILES",
    )
    monster = create_object(Monster, key=MONSTER_NAME, location=room, nohome=True)
    monster.threat_tier = first_live_monster_tier_key()
    # A never-fleeing profile keeps the seeded encounter finishable: the
    # pair defeats it instead of it disengaging at the flee boundary.
    monster.behaviour_tree = next(
        key for key, profile in profiles.items() if profile.flee_hp_fraction is None
    )
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = MONSTER_HP
    monster.traits.hp.current = MONSTER_HP
    monster.traits.atk_phys.base = MONSTER_ATTACK
    monster.save()
    _tag(monster, MONSTER_TAG)
    return monster


def _make_member(tag: str, name: str, room, race_key: str):
    from evennia.utils.create import create_object

    from typeclasses.npcs import LLMNPC, ensure_npc_canonical_age

    npc = create_object(LLMNPC, key=name, location=room, nohome=True)
    npc.race = race_key
    npc.apply_race_baseline()
    npc.db.age = 30
    npc.db.apparent_age = 30
    ensure_npc_canonical_age(npc)
    # The fixture action paths are deterministic: no wall-clock gauge regen.
    npc.traits.mp.rate = 0
    npc.traits.mp.current = int(npc.traits.mp.max)
    npc.save()
    _tag(npc, tag)
    return npc


def _replace_inventory(entity, entries) -> None:
    """Reset one entity's bag through the validated inventory boundary."""
    from world.rules.equipment import (
        add_item,
        apply_inventory_plan,
        normalized_equipment,
        plan_inventory_delta,
        toggle_equipment,
    )

    equipment = normalized_equipment(entity)
    if equipment is not None:
        worn = [
            *(equipment.get(slot) for slot in ("weapon_main", "weapon_off", "armor")),
            *equipment.get("accessories", ()),
        ]
        for key in worn:
            if isinstance(key, str) and key:
                toggle_equipment(entity, key)
    held = list(entity.db.inventory or ())
    if held:
        apply_inventory_plan(plan_inventory_delta(entity, removals=tuple(held)))
    for item_key, quantity in entries:
        for _ in range(quantity):
            add_item(entity, item_key)


def _wound(entity, deficit: int) -> None:
    maximum = int(entity.traits.hp.max)
    entity.traits.hp.current = max(1, maximum - deficit)
    entity.save()


def _acceptance_fixture(character) -> None:
    """Install the dedicated fixture on ``character``'s fresh runtime."""
    if not fixture_enabled():
        return
    enforce_preconditions()

    from world.rules.party import (
        PARTY_MAX_COMPANIONS,
        join_party,
        live_companions,
        party_size,
    )

    required_slots = party_size(character) + 2
    if required_slots > PARTY_MAX_COMPANIONS:
        raise SystemExit(
            "party-management acceptance fixture: the base party already holds "
            f"{party_size(character)} general companions; capacity "
            f"{PARTY_MAX_COMPANIONS} cannot also seat {AIRA_NAME} and {KAHN_NAME}"
        )

    store = _ensure_room(STORE_ROOM_TAG, STORE_ROOM_NAME, STORE_ROOM_DESC)
    safe_room = _ensure_room(SAFE_ROOM_TAG, SAFE_ROOM_NAME, SAFE_ROOM_DESC)
    _ensure_exit(STORE_EXIT_TAG, STORE_EXIT_KEY, store, safe_room)
    _ensure_exit(RETURN_EXIT_TAG, RETURN_EXIT_KEY, safe_room, store)
    _ensure_merchant(store)
    _ensure_monster(store)

    character.location = store
    character.save()
    # An ordinary preset companion may remain only while it fits the quota,
    # and only when it stays co-located with the named pair.
    for member in live_companions(character):
        member.location = store
        member.save()

    race_key = _live_race_key()
    aira = _make_member(AIRA_TAG, AIRA_NAME, store, race_key)
    kahn = _make_member(KAHN_TAG, KAHN_NAME, store, race_key)
    join_party(aira, character)
    join_party(kahn, character)

    from world.rules.tests.combat_fixtures import grant_lineage

    grant_lineage(aira, [HEAL_SKILL_KEY, OPENER_SKILL_KEY])

    _replace_inventory(aira, AIRA_INVENTORY)
    _replace_inventory(kahn, KAHN_INVENTORY)

    from world.rules.equipment import toggle_equipment

    toggle_equipment(aira, AIRA_EQUIPPED_KEY)

    # Wounds after equipment settlement: the heal target stays wounded after
    # the free shopping/equipment steps, and each member's own potion is a
    # legal self-heal choice.
    _wound(character, COMMANDER_HP_DEFICIT)
    _wound(aira, AIRA_HP_DEFICIT)
    _wound(kahn, KAHN_HP_DEFICIT)

    character.db.wallet = COMMANDER_WALLET
    character.save()

    from world.rules.clock import get_world_clock

    get_world_clock()._persist(STORE_OPEN_SECONDS)

    print(
        "seeded party management acceptance fixture: "
        f"{AIRA_NAME}={aira.pk} {KAHN_NAME}={kahn.pk} store={store.pk} "
        f"wire={aira.db.skills} mp={int(aira.traits.mp.current)}"
    )
