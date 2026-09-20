"""Registry target table (design D1/D2): logical names, content factories, dependencies.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from world.lore.magic import MagicTier

from world.tests.synthetic_data.vocab import _synth_elements
from world.tests.synthetic_data.data_items import SYNTH_ITEMS, SYNTH_ITEM_EFFECT_PROFILES, SYNTH_PRICES
from world.tests.synthetic_data.data_skills import SYNTH_ACTS, SYNTH_MP_COST_TIERS, SYNTH_SKILLS
from world.tests.synthetic_data.data_characters import (
    SYNTH_MONSTER_TIERS,
    SYNTH_NPC_TIERS,
    SYNTH_RACES,
    SYNTH_STARTING_KITS,
    SYNTH_STATIC_TIERS,
    SYNTH_SUBRACES,
)
from world.tests.synthetic_data.data_world import (
    SYNTH_ANCHORS,
    SYNTH_ANCHOR_PLACEMENTS,
    SYNTH_ARCHETYPES,
    SYNTH_BUFFS,
    SYNTH_CITY_GATES,
    SYNTH_DIALOGUE,
    SYNTH_GUILD_BRANCHES,
    SYNTH_GUILD_RANKS,
    SYNTH_NAME_PACKS,
    SYNTH_NATIONS,
    SYNTH_REGIONS,
    SYNTH_SHOPS,
    SYNTH_TITLES,
    SYNTH_WILDERNESS_ENTRIES,
)
from world.tests.synthetic_data.data_presets_quests import SYNTH_PRESETS, SYNTH_QUESTS, _build_issuances

# ---------------------------------------------------------------------------
# Registry target table (design D1/D2) — the kit is its only home.
# Values are content factories (re-evaluated per scope) so cross-registry
# rows can resolve through the already-patched registries.
# ---------------------------------------------------------------------------

def _content_by_logical() -> dict[str, Callable[[], Mapping[str, object]]]:
    return {
        "items": lambda: SYNTH_ITEMS,
        "item_effect_profiles": lambda: SYNTH_ITEM_EFFECT_PROFILES,
        "skills": lambda: SYNTH_SKILLS,
        "races": lambda: SYNTH_RACES,
        "static_tiers": lambda: SYNTH_STATIC_TIERS,
        "subraces": lambda: SYNTH_SUBRACES,
        "starting_kits": lambda: SYNTH_STARTING_KITS,
        "presets": lambda: SYNTH_PRESETS,
        "npc_tiers": lambda: SYNTH_NPC_TIERS,
        "monster_tiers": lambda: SYNTH_MONSTER_TIERS,
        "anchors": lambda: SYNTH_ANCHORS,
        "anchor_placements": lambda: SYNTH_ANCHOR_PLACEMENTS,
        "regions": lambda: SYNTH_REGIONS,
        "wilderness_entries": lambda: SYNTH_WILDERNESS_ENTRIES,
        "city_gates": lambda: SYNTH_CITY_GATES,
        "archetypes": lambda: SYNTH_ARCHETYPES,
        "shops": lambda: SYNTH_SHOPS,
        "prices": lambda: SYNTH_PRICES,
        "mp_cost_tiers": lambda: SYNTH_MP_COST_TIERS,
        "titles": lambda: SYNTH_TITLES,
        "dialogue": lambda: SYNTH_DIALOGUE,
        "buffs": lambda: SYNTH_BUFFS,
        "sexual_acts": lambda: SYNTH_ACTS,
        "guild_ranks": lambda: SYNTH_GUILD_RANKS,
        "guild_branches": lambda: SYNTH_GUILD_BRANCHES,
        "nations": lambda: SYNTH_NATIONS,
        "elements": _synth_elements,
        "magic_tiers": lambda: {
            "t_flicker": MagicTier(
                "t_flicker", "微明", 0, 20, ("燼火爆發",), "Synthetic magic tier."
            ),
        },
        "name_packs": lambda: SYNTH_NAME_PACKS,
        "quest_definitions": lambda: SYNTH_QUESTS,
        "quest_issuances": _build_issuances,
        "lore_sync": lambda: _synth_sync_capture(),
    }


def _synth_sync_capture() -> dict[str, Mapping[str, object]]:
    """Mirror the lore-sync capture dict category-for-category with synthetic data."""
    content: dict[str, Callable[[], Mapping[str, object]]] = _content_by_logical()
    return {
        "races": content["races"](),
        "static_tiers": content["static_tiers"](),
        "subraces": content["subraces"](),
        "elements": content["elements"](),
        "magic_tiers": content["magic_tiers"](),
        "nations": content["nations"](),
        "guild_ranks": content["guild_ranks"](),
        "titles": content["titles"](),
        "monster_tiers": content["monster_tiers"](),
        "anchors": content["anchors"](),
        "anchor_placements": content["anchor_placements"](),
        "name_packs": content["name_packs"](),
        "wilderness_regions": content["regions"](),
        "wilderness_entries": content["wilderness_entries"](),
        "prices": content["prices"](),
    }


# logical name -> (owning module, attribute). Attribute strings are assembled
# from fragments so this source never carries a catalog symbol literally.
REGISTRY_TARGETS: dict[str, tuple[str, str]] = {
    "items": ("world.lore.items", "ITEM" + "_REGISTRY"),
    "item_effect_profiles": ("world.rules.item_effects", "ITEM" + "_EFFECT_PROFILES"),
    "skills": ("world.skills.registry", "SKILL" + "_REGISTRY"),
    "races": ("world.lore.races", "RACE" + "_REGISTRY"),
    "static_tiers": ("world.lore.races", "STATIC_TIER" + "_REGISTRY"),
    "subraces": ("world.lore.races", "SUBRACE" + "_REGISTRY"),
    "starting_kits": ("world.lore.starting_kits", "SUBRACE_STARTING_KIT" + "_REGISTRY"),
    "presets": ("world.lore.player_presets", "PLAYER_PRESET" + "_REGISTRY"),
    "npc_tiers": ("world.lore.npc_tiers", "NPC_TIER" + "_REGISTRY"),
    "monster_tiers": ("world.lore.monsters", "MONSTER_TIER" + "_REGISTRY"),
    "anchors": ("world.lore.anchors", "ANCHOR" + "_REGISTRY"),
    "anchor_placements": ("world.lore.anchor_placement", "ANCHOR_PLACEMENT" + "_REGISTRY"),
    "regions": ("world.lore.wilderness_regions", "WILDERNESS_REGION" + "_REGISTRY"),
    "wilderness_entries": ("world.lore.wilderness_entry", "WILDERNESS_ENTRY" + "_REGISTRY"),
    "city_gates": ("world.maps.city_gates", "CITY_GATE" + "_REGISTRY"),
    "archetypes": ("world.lore.scene_archetypes", "SCENE_ARCHETYPE" + "_REGISTRY"),
    "shops": ("world.lore.shops", "SHOP" + "_REGISTRY"),
    "prices": ("world.lore.economy", "PRICE" + "_TABLE"),
    "mp_cost_tiers": ("world.skills.cost_tiers", "MP_COST" + "_TIERS"),
    "titles": ("world.lore.titles", "FIXED_TITLE" + "_REGISTRY"),
    "dialogue": ("world.rules.dialogue", "DIALOGUE" + "_TABLE"),
    "buffs": ("world.rules.buffs", "BUFF" + "_DEFINITIONS"),
    "sexual_acts": ("world.skills.sexual_acts", "SEXUAL_ACT" + "_REGISTRY"),
    "guild_ranks": ("world.lore.guild", "GUILD_RANK" + "_REGISTRY"),
    "guild_branches": ("world.lore.guild", "GUILD_BRANCH" + "_REGISTRY"),
    "nations": ("world.lore.nations", "NATION" + "_REGISTRY"),
    "elements": ("world.lore.elements", "ELEMENT" + "_REGISTRY"),
    "magic_tiers": ("world.lore.magic", "MAGIC_TIER" + "_REGISTRY"),
    "name_packs": ("world.lore.names", "NAME_PACK" + "_REGISTRY"),
    "quest_definitions": ("world.quests.definitions", "QUEST_DEFINITION" + "_REGISTRY"),
    "quest_issuances": ("world.rules.quest_issuance", "QUEST_ISSUANCE" + "_REGISTRY"),
    # The import-time capture the lore DB mirror iterates.
    "lore_sync": ("world.lore.sync", "_ALL" + "_REGISTRIES"),
}

_CONTENT: dict[str, Callable[[], Mapping[str, object]]] = _content_by_logical()

# logical target -> targets that must already be patched when its content
# factory constructs rows: QuestIssuance.__post_init__ resolves its
# definition key against the (patched) definition registry and its reward
# items against the (patched) item registry.
_TARGET_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "quest_issuances": ("quest_definitions", "items"),
    # The rulebook-side profiles belong to the same usable-item closure: a
    # scoped item registry must carry its scoped profiles with it.
    "item_effect_profiles": ("items",),
    # The sync capture's content factories read module-level catalogs, so no
    # target must be patched before the capture dict itself is swapped.
    "lore_sync": (),
}
