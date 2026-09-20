"""Synth-mode fixture values shared between the seed and the migrated tests.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every value ships verbatim."""

from __future__ import annotations

from types import MappingProxyType

from web.browser_support.browser_fixtures_data.mode import synth_mode_enabled
from web.browser_support.browser_fixtures_data.shipped_seed import (
    SHIPPED_ART_ARCHETYPE,
    SHIPPED_GUILD_OFFER_KEY,
)

# ---------------------------------------------------------------------------
# Synth-mode fixture values shared between the seed and the migrated tests.
# These are kit keys and authored fixture identity (room/NPC/monster object
# keys), NOT shipped catalog content.
# ---------------------------------------------------------------------------

#: Authored NPC/monster object keys the synth fixtures place (free-form
#: object names; no registry resolves them).
SYNTH_DIALOGUE_HOST_KEY = "合成櫃檯員"
SYNTH_BARD_KEY = "合成吟遊詩人"
SYNTH_HOSTILE_MONSTER_KEY = "燼殼爬行者"
SYNTH_DEFEATED_MONSTER_KEY = "倒地的燼殼蟲"
SYNTH_PLAZA_MONSTER_KEY = "廣場燼殼蟲"

#: Values the injected combat-HUD fixture borrows from the boot mode's
#: catalogs: the party-member display name rides an NPC-tier row display in
#: shipped mode, and the featured skill row rides a real skill-registry key
#: plus its label (kit skill row under the synthetic install).
SHIPPED_HUD_PARTY_MEMBER_NAME = "法師"
SHIPPED_HUD_SKILL = ("fire_ball", "火球術")
SYNTH_HUD_PARTY_MEMBER_NAME = "合成夥伴"
SYNTH_HUD_SKILL = ("t_ember_burst", "燼火爆發")


def hud_combat_fixture_values() -> dict:
    """(party-member name, skill key, skill label) for the current boot mode."""
    if synth_mode_enabled():
        return {
            "party_name": SYNTH_HUD_PARTY_MEMBER_NAME,
            "skill_key": SYNTH_HUD_SKILL[0],
            "skill_label": SYNTH_HUD_SKILL[1],
        }
    return {
        "party_name": SHIPPED_HUD_PARTY_MEMBER_NAME,
        "skill_key": SHIPPED_HUD_SKILL[0],
        "skill_label": SHIPPED_HUD_SKILL[1],
    }

#: Authored room keys unique to the options-surface fixture.
SYNTH_PLAZA_ROOM_KEY = "合成測試廣場"
SYNTH_EMPTY_GROUND_KEY = "合成測試空地"
SYNTH_BPLAZA_PARTNER_KEY = "廣場合成夥伴"

#: Kit archetype the art fixture room carries; its settled scene output file.
SYNTH_ART_ARCHETYPE = "t_synth_bazaar"

#: Display label of the kit art archetype (mirrors the kit row's authored
#: display; the Playwright-side process has no Django settings, so injected
#: payloads mirror it here instead of querying the registry).
SYNTH_ART_SCENE_LABEL = "苔徑市集"

#: Display label of the shipped art archetype the shipped-mode art fixture
#: rooms carry (used only when the synthetic flag is OFF).
SHIPPED_ART_SCENE_LABEL = "酒館內部"


def art_scene_values() -> "tuple[str, str]":
    """(archetype key, display label) for the current boot mode's art fixture.

    The settled media file is always ``/art/scene/<archetype>.png`` (the art
    service names its output after the archetype key), so journeys derive
    the URL and the caption from this one resolver.
    """
    if synth_mode_enabled():
        return SYNTH_ART_ARCHETYPE, SYNTH_ART_SCENE_LABEL
    return SHIPPED_ART_ARCHETYPE, SHIPPED_ART_SCENE_LABEL

#: Object key of the living monster the art fixture places in the scene room
#: (the combat-portrait journeys' ``engage`` argument — distinct from the
#: combat fixture's start-room monsters).
SHIPPED_ART_ROOM_MONSTER_KEY = "酒館灰狼"
SYNTH_ART_ROOM_MONSTER_KEY = "合成燼殼蟲"


def art_room_monster_key() -> str:
    """The object key of the monster the current boot mode's art fixture seeds."""
    return SYNTH_ART_ROOM_MONSTER_KEY if synth_mode_enabled() else SHIPPED_ART_ROOM_MONSTER_KEY

#: Kit dialogue table the art/exploration fixture hosts carry.
SYNTH_DIALOGUE_TABLE_KEY = "t_synth_lodgekeeper"

#: The kit quest the guild-board modes offer/accept.
SYNTH_GUILD_OFFER_QUEST_KEY = "t_ember_cull"


def guild_offer_quest_key() -> str:
    """The quest definition key the guild-board modes' single offer names."""
    return SYNTH_GUILD_OFFER_QUEST_KEY if synth_mode_enabled() else SHIPPED_GUILD_OFFER_KEY


#: Registered offer copper for the board modes' quest (shipped guild-economy
#: rulebook row vs the kit reward table — the turn-in journey's wallet delta).
SHIPPED_GUILD_OFFER_REWARD_COPPER = 50


def guild_offer_reward_copper() -> int:
    """The registered offer's copper reward for the current boot mode."""
    if synth_mode_enabled():
        from world.tests.synthetic_data import SYNTH_QUEST_REWARDS

        return SYNTH_QUEST_REWARDS[SYNTH_GUILD_OFFER_QUEST_KEY].copper
    return SHIPPED_GUILD_OFFER_REWARD_COPPER

#: Kit shop whose merchant host the store modes trade through.
SYNTH_SHOP_KEY = "t_mossgate_stall"

#: Shop hours the store modes drive with the world clock (mirrors the
#: catalog rulebook's day-window convention: 12h open, 3h closed).
SYNTH_STORE_OPEN_SECONDS = 12 * 3600
SYNTH_STORE_CLOSED_SECONDS = 3 * 3600

#: Inventory deals per services mode (kit item keys).
SYNTH_INVENTORY_BY_MODE = MappingProxyType(
    {
        "guild_registered_board": ("t_ember_spray",),
        "store_open": ("t_huskapple", "t_huskapple", "t_ember_spray"),
        "store_closed": ("t_huskapple",),
        "inventory_only": ("t_huskapple", "t_huskapple", "t_thorn_knife", "t_ember_spray"),
        "inventory_actions": ("t_ember_spray", "t_ember_spray", "t_thorn_knife"),
    }
)

#: Item labels the harness-side journeys match against rendered rows (mirrors
#: of the kit rows' authored display names — the Playwright-side process has
#: no Django settings, same convention as the art scene label mirror).
SYNTH_ITEM_DISPLAYS = MappingProxyType(
    {
        "t_ember_spray": "熾焰噴射劑",
        "t_huskapple": "燼殼果",
        "t_thorn_knife": "荊刺小刀",
        "t_iron_fang": "鐵牙短刃",
    }
)
