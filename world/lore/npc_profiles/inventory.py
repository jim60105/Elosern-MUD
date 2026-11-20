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

    ``kind`` is one of seven closed source kinds, each keyed differently:
    ``place_host`` (keyed by the place's ``service_id``), ``dialogue_table``
    (keyed by the table's ``dialogue_key``), ``starting_companion`` (keyed
    ``<declaring preset>:<partner preset>``), ``quest_template_occupant``
    (keyed ``<template name>:<stage index>:<position in that stage's
    npc_reqs>``), and ``import_example`` (keyed by the example file's stem).
    ``persistent_adventurer`` is keyed by authored person identity, and
    ``resident`` is keyed by the authored resident key.
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

    # eolas_homes_a: the three 幽月谷村 homes and their tables.
    NpcSource("place_host", "eolas_naelara", "eolas_homes_a"),
    NpcSource("place_host", "eolas_sirelwen", "eolas_homes_a"),
    NpcSource("place_host", "eolas_taelith", "eolas_homes_a"),
    NpcSource("dialogue_table", "eolas_naelara_home", "eolas_homes_a"),
    NpcSource("dialogue_table", "eolas_sirelwen_home", "eolas_homes_a"),
    NpcSource("dialogue_table", "eolas_taelith_home", "eolas_homes_a"),

    # eolas_homes_b: the three 幽月谷村 fare homes and their tables.
    NpcSource("place_host", "eolas_nirnel", "eolas_homes_b"),
    NpcSource("place_host", "eolas_raellin", "eolas_homes_b"),
    NpcSource("place_host", "eolas_saelnel", "eolas_homes_b"),
    NpcSource("dialogue_table", "eolas_nirnel_home", "eolas_homes_b"),
    NpcSource("dialogue_table", "eolas_raellin_home", "eolas_homes_b"),
    NpcSource("dialogue_table", "eolas_saelnel_home", "eolas_homes_b"),

    # fionnen_homes_a: the three 翠綠森林村 craft homes and their tables.
    NpcSource("place_host", "fionnen_corith", "fionnen_homes_a"),
    NpcSource("place_host", "fionnen_gwynnel", "fionnen_homes_a"),
    NpcSource("place_host", "fionnen_ithrlin", "fionnen_homes_a"),
    NpcSource("dialogue_table", "fionnen_corith_home", "fionnen_homes_a"),
    NpcSource("dialogue_table", "fionnen_gwynnel_home", "fionnen_homes_a"),
    NpcSource("dialogue_table", "fionnen_ithrlin_home", "fionnen_homes_a"),

    # fionnen_homes_b: the four 翠綠森林村 fare homes and their tables.
    NpcSource("place_host", "fionnen_elunwen", "fionnen_homes_b"),
    NpcSource("place_host", "fionnen_firwen", "fionnen_homes_b"),
    NpcSource("place_host", "fionnen_lumeth", "fionnen_homes_b"),
    NpcSource("place_host", "fionnen_sylara", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_elunwen_home", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_firwen_home", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_lumeth_home", "fionnen_homes_b"),
    NpcSource("dialogue_table", "fionnen_sylara_home", "fionnen_homes_b"),

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

    # eolas_residents: 15 chat-only residents and their 15 dialogue tables.
    NpcSource("resident", "eolas_resident_perenlin", "eolas_residents", "eolas_resident_perenlin", 1000, 10),
    NpcSource("resident", "eolas_resident_taellin", "eolas_residents", "eolas_resident_taellin", 544, 10),
    NpcSource("resident", "eolas_resident_yrenlin", "eolas_residents", "eolas_resident_yrenlin", 280, 10),
    NpcSource("resident", "eolas_resident_liathiel", "eolas_residents", "eolas_resident_liathiel", 1090, 10),
    NpcSource("resident", "eolas_resident_fenlin", "eolas_residents", "eolas_resident_fenlin", 616, 10),
    NpcSource("resident", "eolas_resident_bremnel", "eolas_residents", "eolas_resident_bremnel", 240, 10),
    NpcSource("resident", "eolas_resident_quennel", "eolas_residents", "eolas_resident_quennel", 1030, 10),
    NpcSource("resident", "eolas_resident_niriel", "eolas_residents", "eolas_resident_niriel", 568, 10),
    NpcSource("resident", "eolas_resident_caeleth", "eolas_residents", "eolas_resident_caeleth", 300, 10),
    NpcSource("resident", "eolas_resident_iolowen", "eolas_residents", "eolas_resident_iolowen", 1120, 10),
    NpcSource("resident", "eolas_resident_aranith", "eolas_residents", "eolas_resident_aranith", 520, 10),
    NpcSource("resident", "eolas_resident_vaelara", "eolas_residents", "eolas_resident_vaelara", 260, 10),
    NpcSource("resident", "eolas_resident_bremiel", "eolas_residents", "eolas_resident_bremiel", 1060, 10),
    NpcSource("resident", "eolas_resident_alarith", "eolas_residents", "eolas_resident_alarith", 592, 10),
    NpcSource("resident", "eolas_resident_ondwyn", "eolas_residents", "eolas_resident_ondwyn", 320, 10),
    NpcSource("dialogue_table", "eolas_resident_perenlin", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_taellin", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_yrenlin", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_liathiel", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_fenlin", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_bremnel", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_quennel", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_niriel", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_caeleth", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_iolowen", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_aranith", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_vaelara", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_bremiel", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_alarith", "eolas_residents"),
    NpcSource("dialogue_table", "eolas_resident_ondwyn", "eolas_residents"),

    # ciaran_residents: 15 chat-only residents and their 15 dialogue tables.
    NpcSource("resident", "ciaran_resident_thalara", "ciaran_residents", "ciaran_resident_thalara", 860, 38),
    NpcSource("resident", "ciaran_resident_eryniel", "ciaran_residents", "ciaran_resident_eryniel", 542, 29),
    NpcSource("resident", "ciaran_resident_sylwen", "ciaran_residents", "ciaran_resident_sylwen", 332, 22),
    NpcSource("resident", "ciaran_resident_bremith", "ciaran_residents", "ciaran_resident_bremith", 962, 41),
    NpcSource("resident", "ciaran_resident_faellin", "ciaran_residents", "ciaran_resident_faellin", 608, 29),
    NpcSource("resident", "ciaran_resident_serlin", "ciaran_residents", "ciaran_resident_serlin", 280, 20),
    NpcSource("resident", "ciaran_resident_erynwyn", "ciaran_residents", "ciaran_resident_erynwyn", 894, 39),
    NpcSource("resident", "ciaran_resident_naernel", "ciaran_residents", "ciaran_resident_naernel", 564, 29),
    NpcSource("resident", "ciaran_resident_nimnel", "ciaran_residents", "ciaran_resident_nimnel", 358, 23),
    NpcSource("resident", "ciaran_resident_nimara", "ciaran_residents", "ciaran_resident_nimara", 996, 42),
    NpcSource("resident", "ciaran_resident_rellara", "ciaran_residents", "ciaran_resident_rellara", 520, 29),
    NpcSource("resident", "ciaran_resident_yrenwen", "ciaran_residents", "ciaran_resident_yrenwen", 306, 21),
    NpcSource("resident", "ciaran_resident_rellwen", "ciaran_residents", "ciaran_resident_rellwen", 928, 40),
    NpcSource("resident", "ciaran_resident_coriel", "ciaran_residents", "ciaran_resident_coriel", 586, 29),
    NpcSource("resident", "ciaran_resident_maethiel", "ciaran_residents", "ciaran_resident_maethiel", 384, 24),
    NpcSource("dialogue_table", "ciaran_resident_thalara", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_eryniel", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_sylwen", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_bremith", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_faellin", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_serlin", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_erynwyn", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_naernel", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_nimnel", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_nimara", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_rellara", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_yrenwen", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_rellwen", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_coriel", "ciaran_residents"),
    NpcSource("dialogue_table", "ciaran_resident_maethiel", "ciaran_residents"),

    # fionnen_residents: 15 chat-only residents and their 15 dialogue tables.
    NpcSource("resident", "fionnen_resident_alarnel", "fionnen_residents", "fionnen_resident_alarnel", 860, 38),
    NpcSource("resident", "fionnen_resident_cyrwen", "fionnen_residents", "fionnen_resident_cyrwen", 542, 29),
    NpcSource("resident", "fionnen_resident_naereth", "fionnen_residents", "fionnen_resident_naereth", 332, 22),
    NpcSource("resident", "fionnen_resident_aelith", "fionnen_residents", "fionnen_resident_aelith", 962, 41),
    NpcSource("resident", "fionnen_resident_maethith", "fionnen_residents", "fionnen_resident_maethith", 608, 29),
    NpcSource("resident", "fionnen_resident_saeliel", "fionnen_residents", "fionnen_resident_saeliel", 280, 20),
    NpcSource("resident", "fionnen_resident_berenara", "fionnen_residents", "fionnen_resident_berenara", 894, 39),
    NpcSource("resident", "fionnen_resident_lornnel", "fionnen_residents", "fionnen_resident_lornnel", 564, 29),
    NpcSource("resident", "fionnen_resident_ondeth", "fionnen_residents", "fionnen_resident_ondeth", 358, 23),
    NpcSource("resident", "fionnen_resident_relllin", "fionnen_residents", "fionnen_resident_relllin", 996, 42),
    NpcSource("resident", "fionnen_resident_ithrwen", "fionnen_residents", "fionnen_resident_ithrwen", 520, 29),
    NpcSource("resident", "fionnen_resident_mirara", "fionnen_residents", "fionnen_resident_mirara", 306, 21),
    NpcSource("resident", "fionnen_resident_nymwen", "fionnen_residents", "fionnen_resident_nymwen", 928, 40),
    NpcSource("resident", "fionnen_resident_lumwyn", "fionnen_residents", "fionnen_resident_lumwyn", 586, 29),
    NpcSource("resident", "fionnen_resident_elunlin", "fionnen_residents", "fionnen_resident_elunlin", 384, 24),
    NpcSource("dialogue_table", "fionnen_resident_alarnel", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_cyrwen", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_naereth", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_aelith", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_maethith", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_saeliel", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_berenara", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_lornnel", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_ondeth", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_relllin", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_ithrwen", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_mirara", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_nymwen", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_lumwyn", "fionnen_residents"),
    NpcSource("dialogue_table", "fionnen_resident_elunlin", "fionnen_residents"),
)
