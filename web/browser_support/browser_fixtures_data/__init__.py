"""Shipped-mode fixture values for the managed browser harness.

This package is NOT a test path (the lint gate only scans ``*/tests/`` and
``test_*.py``), so it can name shipped catalog identifiers - and it is the
ONLY place the managed browser harness may name them. Test-path files
(``web/tests/browser/*.py``) import shipped values from here and resolve
synthetic values from the kit (``world.tests.synthetic_data``), so the
behavior suites themselves carry zero shipped content.

The synth-mode block names only ``t_``-keyed kit rows and authored fixture
identity (free-form object keys); the shipped block is read only when the
harness boots with ``ELOSERN_BROWSER_SYNTH_CATALOGS`` overridden to "0".

The single-module history is split into modules of a shared surface (the
``world.tests.synthetic_data`` package precedent applies here):
``shipped_seed`` holds the shipped-mode seed values; ``mode`` the boot-mode
flag; ``grafting`` the registry grafts closing the production seams the
t_-only install opens; ``creation`` the CONCEPT/custom-draft journey
helpers; ``probes`` the runtime catalog probes; ``services_catalog`` the
shared synthetic guild-economy catalog; ``fixture_values`` the synth-mode
fixture identity shared by the seed and the migrated tests;
``store_bag`` the store/bag fixture roles and webclient display
vocabulary; ``combat_fixtures`` the combat grant sets and menu roles;
``titles_fixtures`` the codex title rows.

Every name resolves through this package's namespace exactly as the single
``web/browser_support/browser_fixtures_data.py`` module exported it:
consumers keep importing ``web.browser_support.browser_fixtures_data``.
"""

from __future__ import annotations

import os
from types import MappingProxyType

# NOTE: no world/evennia imports at module scope (in any slice). The
# Playwright-side process runs plain ``python -m unittest`` with no Django
# settings, and migrated test modules import this package at module scope;
# every catalog owner module is imported lazily inside the helpers.
from web.browser_support.browser_fixtures_data.mode import synth_mode_enabled

from web.browser_support.browser_fixtures_data.shipped_seed import (
    SHIPPED_ART_ARCHETYPE,
    SHIPPED_BASE_RACE,
    SHIPPED_BASE_SUBRACE,
    SHIPPED_COMBAT_ACTIVE_SKILLS,
    SHIPPED_COMBAT_DEBUFF_KEY,
    SHIPPED_COMBAT_LADDER_LEVEL,
    SHIPPED_COMBAT_LADDER_SKILL,
    SHIPPED_COMBAT_MONSTERS,
    SHIPPED_COMBAT_PASSIVE_SKILLS,
    SHIPPED_DIALOGUE_KEY,
    SHIPPED_DRAFT_RACE,
    SHIPPED_DRAFT_SUBRACE,
    SHIPPED_GUILD_OFFER_KEY,
    SHIPPED_MEAL_KEY,
    SHIPPED_MONSTER_TIER_ATTR,
    SHIPPED_MONSTER_TIER_KEY,
    SHIPPED_POTION_KEY,
    SHIPPED_PRESET_KEY,
    SHIPPED_TITLE_RANK_E_KEY,
    SHIPPED_TITLE_RANK_F_KEY,
    SHIPPED_WEAPON_KEY,
    SHIPPED_WILDERNESS_ENTRY_KEY,
)

from web.browser_support.browser_fixtures_data.grafting import (
    SHIPPED_COMBAT_MODIFIER_RULE_ID,
    SYNTH_ENTRY_RANK_KEY,
    SYNTH_INNATE_ATTACK_KEY,
    SYNTH_INNATE_FLEE_KEY,
    SYNTH_RACE_AFFINITY_BOUND,
    SYNTH_STATUS_DISPLAY_ROWS,
    combat_modifier_condition_rule_id,
    graft_synth_affinity_bounds,
    graft_synth_combat_modifier,
    graft_synth_defeat_rulebook,
    graft_synth_entry_rank,
    graft_synth_innate_skills,
    graft_synth_state_reaction_rulebook,
    graft_synth_status_display,
    graft_synth_wilderness_terrain,
    synth_next_entry_rank_key,
)

from web.browser_support.browser_fixtures_data.creation import (
    concept_affinity_checked_testids,
    concept_placeholder_values,
)

from web.browser_support.browser_fixtures_data.probes import (
    custom_draft_form_values,
    first_live_monster_tier_key,
    first_live_wilderness_entry,
    lineage_rungs_for,
    scene_archetype_registered,
    synth_concept_proposal_values,
    synth_first_preset_key,
)

from web.browser_support.browser_fixtures_data.services_catalog import (
    SYNTH_SHOP_OFFERED_ITEM_KEYS,
    build_synth_services_catalog,
    install_synth_affinity_config,
    install_synth_services_catalog,
)

from web.browser_support.browser_fixtures_data.fixture_values import (
    SHIPPED_ART_ROOM_MONSTER_KEY,
    SHIPPED_ART_SCENE_LABEL,
    SHIPPED_GUILD_OFFER_REWARD_COPPER,
    SHIPPED_HUD_PARTY_MEMBER_NAME,
    SHIPPED_HUD_SKILL,
    SYNTH_ART_ARCHETYPE,
    SYNTH_ART_ROOM_MONSTER_KEY,
    SYNTH_ART_SCENE_LABEL,
    SYNTH_BARD_KEY,
    SYNTH_BPLAZA_PARTNER_KEY,
    SYNTH_DEFEATED_MONSTER_KEY,
    SYNTH_DIALOGUE_HOST_KEY,
    SYNTH_DIALOGUE_TABLE_KEY,
    SYNTH_EMPTY_GROUND_KEY,
    SYNTH_GUILD_OFFER_QUEST_KEY,
    SYNTH_HOSTILE_MONSTER_KEY,
    SYNTH_HUD_PARTY_MEMBER_NAME,
    SYNTH_HUD_SKILL,
    SYNTH_INVENTORY_BY_MODE,
    SYNTH_ITEM_DISPLAYS,
    SYNTH_PLAZA_MONSTER_KEY,
    SYNTH_PLAZA_ROOM_KEY,
    SYNTH_SHOP_KEY,
    SYNTH_STORE_CLOSED_SECONDS,
    SYNTH_STORE_OPEN_SECONDS,
    art_room_monster_key,
    art_scene_values,
    guild_offer_quest_key,
    guild_offer_reward_copper,
    hud_combat_fixture_values,
)

from web.browser_support.browser_fixtures_data.store_bag import (
    _ITEM_KIND_WORDS,
    _ITEM_RARITY_WORDS,
    bag_action_fixture_values,
    kind_word,
    rarity_word,
    store_fixture_values,
)

from web.browser_support.browser_fixtures_data.combat_fixtures import (
    SHIPPED_COMBAT_DISABLED_SKILL,
    SHIPPED_COMBAT_NONE_SKILL,
    SHIPPED_COMBAT_SPELL_KEY,
    SHIPPED_COMBAT_SPELL_PREREQ_KEY,
    SHIPPED_INNATE_ATTACK_KEY,
    SYNTH_COMBAT_ACTIVE_SKILLS,
    SYNTH_COMBAT_DEBUFF_KEY,
    SYNTH_COMBAT_LADDER_LEVEL,
    SYNTH_COMBAT_LADDER_SKILL,
    SYNTH_COMBAT_MONSTERS,
    SYNTH_COMBAT_PASSIVE_SKILLS,
    combat_journey_values,
)

from web.browser_support.browser_fixtures_data.titles_fixtures import (
    SYNTH_TITLE_BANKED_KEYS,
    SYNTH_TITLE_LOCKED_KEY,
    title_codex_values,
)

# Valueless re-annotation mirrors the original single module's annotated
# binding, so the package namespace carries the same lazy module annotation
# dunders the pre-split module exposed (no new name enters ``dir()``).
SYNTH_STATUS_DISPLAY_ROWS: MappingProxyType
