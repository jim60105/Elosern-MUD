"""The shipped NPC source inventory: every authored NPC source, with an owner.

Pure data only -- no imports besides ``dataclasses`` -- so the data-contract
test (``world/lore/tests/test_npc_profile_inventory.py``) can derive the
actual source set from the live registries independently and assert the two
agree. Grouped by owner exactly as the binding owner assignment list in
``openspec/changes/npc-persona-profile-registry/design.md`` (D1) states.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NpcSource:
    """One shipped NPC source and the content-change slice that owns its persona.

    ``kind`` is one of six closed source kinds, each keyed differently:
    ``place_host`` (keyed by the place's ``service_id``), ``dialogue_table``
    (keyed by the table's ``dialogue_key``), ``starting_companion`` (keyed
    ``<declaring preset>:<partner preset>``), ``quest_template_occupant``
    (keyed ``<template name>:<stage index>:<position in that stage's
    npc_reqs>``), and ``import_example`` (keyed by the example file's stem).
    ``persistent_adventurer`` is keyed by authored person identity.
    ``owner`` is the owning content change's slice label.
    """

    kind: str
    key: str
    owner: str
    profile_key: str | None = None
    age: int | None = None
    apparent_age: int | None = None


NPC_SOURCE_INVENTORY: tuple[NpcSource, ...] = (
    # altoria_lower: the lower-terrace attendant hosts and their tables.
    NpcSource("place_host", "altoria_eatery_owner", "altoria_lower"),
    NpcSource("place_host", "altoria_tavern_keeper", "altoria_lower"),
    NpcSource("place_host", "altoria_innkeeper", "altoria_lower"),
    NpcSource("place_host", "altoria_bathhouse_keeper", "altoria_lower"),
    NpcSource("place_host", "altoria_guard_captain", "altoria_lower"),
    NpcSource("dialogue_table", "altoria_eatery", "altoria_lower"),
    NpcSource("dialogue_table", "altoria_tavern", "altoria_lower"),
    NpcSource("dialogue_table", "altoria_lodging", "altoria_lower"),
    NpcSource("dialogue_table", "altoria_bathhouse", "altoria_lower"),
    NpcSource("dialogue_table", "altoria_guardhouse", "altoria_lower"),

    # altoria_trade: the capital's six merchants and their tables.
    NpcSource("place_host", "altoria_merchant", "altoria_trade"),
    NpcSource("place_host", "altoria_blacksmith", "altoria_trade"),
    NpcSource("place_host", "altoria_tailor", "altoria_trade"),
    NpcSource("place_host", "altoria_jeweller", "altoria_trade"),
    NpcSource("place_host", "altoria_alchemist", "altoria_trade"),
    NpcSource("place_host", "altoria_merchant_master", "altoria_trade"),
    NpcSource("dialogue_table", "altoria_general_store", "altoria_trade"),
    NpcSource("dialogue_table", "altoria_forge", "altoria_trade"),
    NpcSource("dialogue_table", "altoria_tailor", "altoria_trade"),
    NpcSource("dialogue_table", "altoria_jeweller", "altoria_trade"),
    NpcSource("dialogue_table", "altoria_alchemist", "altoria_trade"),
    NpcSource("dialogue_table", "altoria_merchant_hall", "altoria_trade"),

    # altoria_guild: the guild master, the guild-staff table, and the
    # branch's persistent adventurers (examination hosts).
    NpcSource("place_host", "altoria_guild_master", "altoria_guild"),
    NpcSource("dialogue_table", "guild_staff", "altoria_guild"),
    NpcSource("persistent_adventurer", "altoria_hok", "altoria_guild", "altoria_hok_adventurer", 45, 45),
    NpcSource("persistent_adventurer", "altoria_cassandra", "altoria_guild", "altoria_cassandra_adventurer", 40, 40),
    NpcSource("persistent_adventurer", "altoria_augustine", "altoria_guild", "altoria_augustine_adventurer", 68, 52),

    # altoria_upper: the upper-terrace hosts and their tables.
    NpcSource("place_host", "altoria_high_priestess", "altoria_upper"),
    NpcSource("place_host", "altoria_sanctum_deacon", "altoria_upper"),
    NpcSource("place_host", "altoria_noble_watch_captain", "altoria_upper"),
    NpcSource("place_host", "altoria_drill_instructor", "altoria_upper"),
    NpcSource("place_host", "altoria_academy_dean", "altoria_upper"),
    NpcSource("dialogue_table", "altoria_temple", "altoria_upper"),
    NpcSource("dialogue_table", "altoria_sanctum", "altoria_upper"),
    NpcSource("dialogue_table", "altoria_noble_watch", "altoria_upper"),
    NpcSource("dialogue_table", "altoria_drill_yard", "altoria_upper"),
    NpcSource("dialogue_table", "altoria_academy", "altoria_upper"),

    # ciaran_homes_a: the first four 暗影谷村 homes and their tables.
    NpcSource("place_host", "ciaran_elenis", "ciaran_homes_a"),
    NpcSource("place_host", "ciaran_gwenaera", "ciaran_homes_a"),
    NpcSource("place_host", "ciaran_hailiel", "ciaran_homes_a"),
    NpcSource("place_host", "ciaran_lareneth", "ciaran_homes_a"),
    NpcSource("dialogue_table", "ciaran_elenis_home", "ciaran_homes_a"),
    NpcSource("dialogue_table", "ciaran_gwenaera_home", "ciaran_homes_a"),
    NpcSource("dialogue_table", "ciaran_hailiel_home", "ciaran_homes_a"),
    NpcSource("dialogue_table", "ciaran_lareneth_home", "ciaran_homes_a"),

    # ciaran_homes_b: the remaining four 暗影谷村 homes and their tables.
    NpcSource("place_host", "ciaran_nireth", "ciaran_homes_b"),
    NpcSource("place_host", "ciaran_teliel", "ciaran_homes_b"),
    NpcSource("place_host", "ciaran_valwyn", "ciaran_homes_b"),
    NpcSource("place_host", "ciaran_vethiel", "ciaran_homes_b"),
    NpcSource("dialogue_table", "ciaran_nireth_home", "ciaran_homes_b"),
    NpcSource("dialogue_table", "ciaran_teliel_home", "ciaran_homes_b"),
    NpcSource("dialogue_table", "ciaran_valwyn_home", "ciaran_homes_b"),
    NpcSource("dialogue_table", "ciaran_vethiel_home", "ciaran_homes_b"),

    # companions: the four starting-companion declarations.
    NpcSource("starting_companion", "violet_altoria:lidzia_rosenthal", "companions"),
    NpcSource("starting_companion", "lidzia_rosenthal:violet_altoria", "companions"),
    NpcSource("starting_companion", "yuka_darknight:yuna_darknight", "companions"),
    NpcSource("starting_companion", "yuna_darknight:yuka_darknight", "companions"),

    # generated_quest_cards: the single offline quest-template occupant.
    NpcSource("quest_template_occupant", "討伐林間盜匪:0:0", "generated_quest_cards"),

    # import_cards: shipped NPC import cards, including the W1 demonstration.
    NpcSource("import_example", "example_character", "import_cards"),
    NpcSource("import_example", "yohanna_cooper", "import_cards"),
)
