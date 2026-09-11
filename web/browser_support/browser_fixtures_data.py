"""Shipped-mode fixture values for the managed browser harness.

This module is NOT a test path (the lint gate only scans ``*/tests/`` and
``test_*.py``), so it can name shipped catalog identifiers - and it is the
ONLY place the managed browser harness may name them. Test-path files
(``web/tests/browser/*.py``) import shipped values from here and resolve
synthetic values from the kit (``world.tests.synthetic_data``), so the
behavior suites themselves carry zero shipped content.

The synth-mode block names only ``t_``-keyed kit rows and authored fixture
identity (free-form object keys); the shipped block is read only when the
harness boots with ``ELOSERN_BROWSER_SYNTH_CATALOGS`` overridden to "0".
"""

from __future__ import annotations

from types import MappingProxyType

from world.lore.guild import GuildRank

# ---------------------------------------------------------------------------
# Shipped-mode seed values (used only when the synthetic flag is OFF).
# ---------------------------------------------------------------------------

#: Wilderness-entry registry key whose gate rooms anchor the minimap fixture's
#: wilderness layer.
SHIPPED_WILDERNESS_ENTRY_KEY = "capital_altoria"

#: Scene-archetype registry key the art fixture rooms carry.
SHIPPED_ART_ARCHETYPE = "tavern_interior"

#: Scripted-dialogue table the art/exploration fixture hosts carry.
SHIPPED_DIALOGUE_KEY = "guild_staff"

#: Inventory keys the services fixture deals out.
SHIPPED_POTION_KEY = "healing_potion"
SHIPPED_WEAPON_KEY = "plain_sword"
SHIPPED_MEAL_KEY = "meal"

#: Guild-offer registry key the quest-board modes accept.
SHIPPED_GUILD_OFFER_KEY = "introductory_hunt"

#: Fixed-title rows the titles fixture banks (locked rows stay unbanked).
SHIPPED_TITLE_RANK_F_KEY = "g_f_rank"
SHIPPED_TITLE_RANK_E_KEY = "g_e_rank"

#: Creation fixtures: preset card and custom-draft race/subrace pair.
SHIPPED_PRESET_KEY = "elysa_snow"
SHIPPED_DRAFT_RACE = "beastfolk"
SHIPPED_DRAFT_SUBRACE = "foxkin"
SHIPPED_BASE_RACE = "human"
SHIPPED_BASE_SUBRACE = "human_commoner"

#: Monster tier attribute value / registry key the combat fixtures apply.
SHIPPED_MONSTER_TIER_ATTR = "low"
SHIPPED_MONSTER_TIER_KEY = "floor"

#: Combat fixture grant set: active skills, passive skills, and the
#: skill-anchored freeform ladder rung (``use-driven-skill-lineage`` DC5).
SHIPPED_COMBAT_ACTIVE_SKILLS = ("fire_ball", "wind_blade", "status_disguise", "concentration")
SHIPPED_COMBAT_PASSIVE_SKILLS = ("defense_instinct", "wind_mastery")
SHIPPED_COMBAT_LADDER_SKILL = "wind_blade"
SHIPPED_COMBAT_LADDER_LEVEL = 10
#: Status-panel condition with a deterministic applied-modifier row.
SHIPPED_COMBAT_DEBUFF_KEY = "poisoned"
#: (object key, hp) pairs for the two living combat monsters.
SHIPPED_COMBAT_MONSTERS = (("goblin", 200), ("wolf", 200))

# ---------------------------------------------------------------------------
# Production entry-rank vocabulary under the synthetic install.
#
# ``world.rules.guild.register_adventurer`` hardcodes the entry rank "F"
# (production seam; this change ships no production-code edits) while the
# kit's guild-rank rows are t_-only. Both flagged processes therefore graft
# one entry-rank row into the live registry AFTER the kit install, keyed by
# the production seam constant and carrying only t_-keyed content (its title
# is a kit row). The row lives solely in the private harness database and
# process; shipped catalogs never see it.
# ---------------------------------------------------------------------------

SYNTH_ENTRY_RANK_KEY = "F"

SYNTH_ENTRY_RANK_ROW = GuildRank(
    "F",
    # One below the kit's lowest rank so the shared next-rank derivation
    # (exact order+1 match) resolves the kit's first rank unambiguously.
    0,
    0,
    99,
    "Synthetic entry-rank tasks for the managed browser harness.",
    "t_synth_first_hunt",
    "霧鱗・灰秤",
    "合成公會見習考官",
)


def graft_synth_entry_rank() -> None:
    """Ensure the production entry-rank row exists in the live registry.

    Called by the flagged seed and server processes after
    ``install_synthetic_catalogs()`` swapped the guild-rank catalog to the
    kit's t_-only rows, so guild registration keeps working on its hardcoded
    entry-rank seam while every referenced title stays synthetic.
    """
    from world.lore.guild import GUILD_RANK_REGISTRY

    GUILD_RANK_REGISTRY.setdefault(SYNTH_ENTRY_RANK_KEY, SYNTH_ENTRY_RANK_ROW)


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

#: Authored room keys unique to the options-surface fixture.
SYNTH_PLAZA_ROOM_KEY = "合成測試廣場"
SYNTH_EMPTY_GROUND_KEY = "合成測試空地"
SYNTH_BPLAZA_PARTNER_KEY = "廣場合成夥伴"

#: Kit archetype the art fixture room carries; its settled scene output file.
SYNTH_ART_ARCHETYPE = "t_synth_bazaar"

#: Kit dialogue table the art/exploration fixture hosts carry.
SYNTH_DIALOGUE_TABLE_KEY = "t_synth_lodgekeeper"

#: The kit quest the guild-board modes offer/accept.
SYNTH_GUILD_OFFER_QUEST_KEY = "t_ember_cull"

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

#: Kit combat grant set: actives, passives, and the freeform ladder. The
#: ladder rides ``t_glowmire_bloom`` (its own element's mastery passive
#: ``t_glowmire_mastery`` is granted alongside), mirroring the shipped
#: wind_blade/wind_mastery pairing without naming shipped skills.
SYNTH_COMBAT_ACTIVE_SKILLS = ("t_ember_burst", "t_cinder_cleave", "t_moss_veil", "t_glowmire_bloom")
SYNTH_COMBAT_PASSIVE_SKILLS = ("t_steady_stride", "t_glowmire_mastery")
SYNTH_COMBAT_LADDER_SKILL = "t_glowmire_bloom"
SYNTH_COMBAT_LADDER_LEVEL = 10
#: Kit debuff with a deterministic applied-modifier row (status panel).
SYNTH_COMBAT_DEBUFF_KEY = "t_ash_burn"
#: (object key, hp) pairs for the two living synth combat monsters.
SYNTH_COMBAT_MONSTERS = (("燼殼工蟲", 200), ("燼殼兵蟲", 200))

#: Fixed-title rows the synth titles fixture banks; registration already
#: banked the entry-rank title through the grafted F row, so the fixture
#: banks it idempotently alongside the second kit row.
SYNTH_TITLE_BANKED_KEYS = ("t_synth_first_hunt", "t_synth_lodging_friend")
#: A third kit title kept UNbanked so the codex renders a locked row.
SYNTH_TITLE_LOCKED_KEY = "t_synth_deep_walker"
