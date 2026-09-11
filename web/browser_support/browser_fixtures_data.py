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

import os
from types import MappingProxyType

# NOTE: no world/evennia imports at module scope. The Playwright-side
# process runs plain ``python -m unittest`` with no Django settings, and
# migrated test modules import this one at module scope; every catalog
# owner module is imported lazily inside the helpers below.


def synth_mode_enabled() -> bool:
    """Whether the harness boots with the synthetic catalogs (harness default)."""
    return os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS", "1") == "1"

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


def graft_synth_entry_rank() -> None:
    """Ensure the production entry-rank row exists in the live registry.

    Called by the flagged seed and server processes after
    ``install_synthetic_catalogs()`` swapped the guild-rank catalog to the
    kit's t_-only rows, so guild registration keeps working on its hardcoded
    entry-rank seam while every referenced title stays synthetic.
    """
    from world.lore.guild import GUILD_RANK_REGISTRY, GuildRank

    row = GuildRank(
        SYNTH_ENTRY_RANK_KEY,
        # Same order as the kit's entry rank: board eligibility needs the entry
        # rank at or above the kit's lowest quest rank, while the next-rank
        # derivation (exact order+1 match over the registry) still resolves the
        # kit's second rank unambiguously.
        1,
        0,
        99,
        "Synthetic entry-rank tasks for the managed browser harness.",
        "t_synth_first_hunt",
        "霧鱗・灰秤",
        "合成公會見習考官",
    )
    GUILD_RANK_REGISTRY.setdefault(SYNTH_ENTRY_RANK_KEY, row)


#: Authored display bindings for the kit's condition rows, keyed by kit buff
#: key. The status-display table validates its coverage against the catalogs
#: at import (shipped data, via the pre-install import seam); the kit's own
#: buffs are grafted afterwards so the status presenter can label them
#: without the table ever learning shipped drift.
SYNTH_STATUS_DISPLAY_ROWS: MappingProxyType = MappingProxyType(
    {
        "t_moss_veil": ("苔幕", "beneficial"),
        "t_ash_burn": ("燼灼", "harmful"),
    }
)


def graft_synth_status_display() -> None:
    """Ensure every installed kit buff has one status-display row.

    ``world.rules.status_display.STATUS_DISPLAY`` is built at import from
    the shipped rulebook; under the process install the kit adds its own
    buff keys, and the status presenter fails closed on an unlabeled code.
    Graft one authored row per live kit buff that the shipped table cannot
    know about (``setdefault``: a code the table already covers keeps its
    shipped row).
    """
    from world.rules.status_display import ConditionDisplay, STATUS_DISPLAY
    from world.tests.synthetic_data import SYNTH_BUFFS

    for key in SYNTH_BUFFS:
        if key in STATUS_DISPLAY:
            continue
        label, severity = SYNTH_STATUS_DISPLAY_ROWS[key]
        STATUS_DISPLAY[key] = ConditionDisplay(key, label, severity)


def graft_synth_wilderness_terrain() -> None:
    """Make the coordinate-keyed wilderness terrain model resolve kit rows.

    Production's terrain partition (``region_for_coordinates``) is closed-form
    integer arithmetic returning the shipped region keys, and the monster
    population tables are import-built immutable mappings over the same keys.
    The synthetic install swaps the region registry to t_-only rows, so every
    wilderness room activation (seed, server, or traversal) KeyErrors on a
    shipped key no installed row answers. Graft one kit-authored row per
    partition key (idempotent setdefault) and rebind the population tables so
    every region answers with the live registry's first threat tier.
    """
    from types import MappingProxyType

    from dataclasses import replace

    import world.lore.wilderness_regions as _regions
    import world.maps.wilderness_population as _population
    from world.lore.monsters import MONSTER_TIER_REGISTRY
    from world.tests.synthetic_data import SYNTH_REGIONS
    from world.maps.wilderness_provider import region_for_coordinates

    partition_keys = {
        region_for_coordinates(x, y)
        for x in range(0, 224, 7)
        for y in range(0, 224, 7)
    }
    template = next(iter(SYNTH_REGIONS.values()))
    for key in sorted(partition_keys):
        _regions.WILDERNESS_REGION_REGISTRY.setdefault(key, replace(template, key=key))

    tier_key = next(iter(MONSTER_TIER_REGISTRY))
    _population._REGION_TIER = MappingProxyType(
        {key: tier_key for key in _population._REGION_TIER}
    )
    _population._REGION_DENSITY = MappingProxyType(
        {key: 3 for key in _population._REGION_DENSITY}
    )


def synth_next_entry_rank_key() -> str:
    """The rank key exactly one order above the grafted entry rank.

    Mirrors ``service_view._next_rank_and_threshold``'s exact-order+1
    derivation against the live registry, so the exam/next-rank fixtures name
    the promotion target without hardcoding a kit rank key.
    """
    from world.lore.guild import GUILD_RANK_REGISTRY

    entry = GUILD_RANK_REGISTRY[SYNTH_ENTRY_RANK_KEY]
    return next(
        member.key
        for member in GUILD_RANK_REGISTRY.values()
        if member.order == entry.order + 1
    )


#: Borrowed affinity bound per kit race: the kit's subrace seeds borrow the
#: shipped vocabulary's first element (closed combat-element enum cannot be
#: widened), so every kit race may pick exactly ONE element without letting
#: a seed exceed its own race bound at activation.
SYNTH_RACE_AFFINITY_BOUND = 1


def graft_synth_affinity_bounds() -> None:
    """Extend the race-bound mapping with one row per live kit race.

    ``world.rules.character_creation._AFFINITY_INPUT_BOUNDS`` is production
    data keyed by the shipped races (production seam; this change ships no
    production-code edits), while the creation descriptor derives one
    affinity picker per LIVE registry race — under the synthetic install the
    registry is t_-only and ``max_affinity_elements`` raises for every kit
    race. Both flagged processes therefore graft one bound per live race
    AFTER the kit install (``setdefault``: shipped rows keep their shipped
    numbers). Every consumer (panel descriptor, draft normalizer, action
    gate, creation service) resolves through the same live mapping, so the
    custom-form picker, the concept placeholder's empty affinity, and the
    activation seed validation all agree on the kit races.
    """
    from world.lore.races import RACE_REGISTRY
    from world.rules.character_creation import _AFFINITY_INPUT_BOUNDS

    for race_key in RACE_REGISTRY:
        _AFFINITY_INPUT_BOUNDS.setdefault(race_key, SYNTH_RACE_AFFINITY_BOUND)


def concept_affinity_checked_testids(expected: tuple[str, ...]) -> tuple[str, ...]:
    """The affinity checkboxes the CONCEPT placeholder journey must find checked.

    The shipped proposal names two shipped elements, so the journey pins
    their exact checkbox testids (``creation-affinity-<element>``). The
    synthetic placeholder deliberately carries an EMPTY affinity — the
    closed element enum makes a shipped-name check meaningless, while the
    journey still proves the placeholder prefills the picker region (the
    checkboxes are rendered and nothing is checked) — so synthetic mode
    expects no checked box.
    """
    return () if synth_mode_enabled() else tuple(
        f"creation-affinity-{key}" for key in expected
    )


def concept_placeholder_values(panel: dict) -> dict:
    """The identity the CONCEPT placeholder journey must observe pre-filled.

    Re-derives, purely from the panel the server just presented (no Django
    settings needed — safe in the Playwright-side process), exactly what the
    browser-settings resolver proposes: shipped mode forwards the wizard's
    own snapshot values verbatim; synthetic mode derives the FIRST advertised
    race/subrace pair from the custom block and the greedy span-fill of the
    matching advertised profile (the same rule the server applies against
    the live profile), with the empty affinity the placeholder always carries.
    """
    proposal = panel["proposal"]
    if not synth_mode_enabled():
        return {
            "race": proposal["race"],
            "subrace": proposal["subrace"],
            "allocations": dict(proposal["allocations"]),
            "affinity_elements": list(proposal["affinity_elements"]),
            "affinity_checked": concept_affinity_checked_testids(
                proposal["affinity_elements"]
            ),
        }
    custom = panel["custom"]
    race = custom["races"][0]
    race_key = race["key"]
    subrace_key = (race["subraces"] or [None])[0]
    profile = next(
        p for p in custom["profiles"]
        if p["race"] == race_key and p["subrace"] == subrace_key
    )
    remaining = profile["budget"]
    allocations: dict[str, int] = {}
    for axis in profile["axes"]:
        value = min(axis["maximum"] - axis["minimum"], remaining)
        allocations[axis["axis"]] = value
        remaining -= value
    if remaining != 0:
        raise AssertionError("profile budget exceeds allocatable axis spans")
    return {
        "race": race_key,
        "subrace": subrace_key,
        "allocations": allocations,
        "affinity_elements": [],
        "affinity_checked": (),
    }


# ---------------------------------------------------------------------------
# Runtime catalog probes (shared by the synthetic-aware seed fixtures).
#
# Reading the CURRENT owner-module registry attributes keeps every fixture
# valid under either boot mode: the shipped registries when the kit flag is
# overridden off, the kit's installed rows when it is on (the harness
# default). The probes never name a registry key.
# ---------------------------------------------------------------------------


def first_live_wilderness_entry():
    """The first registered wilderness entry (registry insertion order)."""
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    return next(iter(WILDERNESS_ENTRY_REGISTRY.values()))


def first_live_monster_tier_key() -> str:
    """The first registered monster threat tier key."""
    from world.lore.monsters import MONSTER_TIER_REGISTRY

    return next(iter(MONSTER_TIER_REGISTRY))


def synth_concept_proposal_values() -> dict:
    """One valid concept-proposal identity derived from the live registries.

    Resolves the first registered race, its first subrace, the exact
    budget-conforming balanced allocation the rule layer demands (the same
    greedy span-fill the seed's preset fixture uses), and the first
    registered skill key — so the synthetic-mode concept placeholder names
    no registry symbol or shipped key on any test path (the gate denies
    registry symbol-refs there).
    """
    from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
    from world.rules.character_creation import resolve_starting_profile
    from world.skills.registry import SKILL_REGISTRY

    race_key = next(iter(RACE_REGISTRY))
    subrace_key = next(
        key for key, sub in SUBRACE_REGISTRY.items() if sub.race_key == race_key
    )
    profile = resolve_starting_profile(race_key, subrace_key)
    remaining = profile.budget
    allocations: dict[str, int] = {}
    for axis, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        allocations[axis] = value
        remaining -= value
    if remaining != 0:
        raise AssertionError("starting profile budget exceeds allocatable spans")
    return {
        "race_key": race_key,
        "subrace_key": subrace_key,
        "allocations": allocations,
        "suggested_skills": (next(iter(SKILL_REGISTRY)),),
    }


def synth_first_preset_key() -> str:
    """The first registered player-preset card key (server-side probe).

    The creation fixture seeds its preset draft from the first registered
    card in both boot modes, and the preset journeys open that same first
    card — so journeys and the seed agree without naming a card key.
    """
    from world.lore.player_presets import PRESET_REGISTRY

    return next(iter(PRESET_REGISTRY))


def custom_draft_form_values(
    panel: dict, *, race_index: int = 0, last_subrace: bool = False
) -> dict:
    """(race, subrace, subrace presses, budget, per-axis allocation strings)
    for a keyboard-driven custom-form journey.

    Mirrors the journey exactly: the race select's keyboard lands on the
    ``race_index``-th advertised race (clamped, so one ArrowRight reaches
    the second race or stays on a single-race registry), the subrace select
    on the LAST (``last_subrace``, Home + n-1 ArrowDown) or FIRST (one
    ArrowDown from the unopened select) subrace of that race, and the
    allocation strings are one exact greedy budget spend of the MATCHING
    advertised profile — the same span-fill rule the server validates — so
    the journeys fill what the CURRENT registry offers without naming
    shipped race keys or point totals.
    """
    custom = panel["custom"]
    race = custom["races"][min(race_index, len(custom["races"]) - 1)]
    race_key = race["key"]
    subrace_keys = list(race["subraces"] or [])
    subrace_key = subrace_keys[-1] if last_subrace else subrace_keys[0]
    profile = next(
        p for p in custom["profiles"]
        if p["race"] == race_key and p["subrace"] == subrace_key
    )
    remaining = profile["budget"]
    allocations: dict[str, str] = {}
    for axis in profile["axes"]:
        value = min(axis["maximum"] - axis["minimum"], remaining)
        allocations[axis["axis"]] = str(value)
        remaining -= value
    if remaining != 0:
        raise AssertionError("profile budget exceeds allocatable axis spans")
    return {
        "race": race_key,
        "subrace": subrace_key,
        "subrace_presses": max(len(subrace_keys) - 1, 0) if last_subrace else 1,
        "budget": profile["budget"],
        "allocations": allocations,
    }


def scene_archetype_registered(key: str) -> bool:
    """Whether one scene archetype resolves in the CURRENT live registry."""
    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

    return key in SCENE_ARCHETYPE_REGISTRY


# ---------------------------------------------------------------------------
# The shared synthetic guild-economy catalog.
#
# The seed process and the managed server must agree on ONE catalog (same
# shop, offers, thresholds, exam profiles): the seed builds DB state against
# it and the server answers the services view from it. Both flagged
# processes call ``install_synth_services_catalog()`` right after the kit
# install — direct process-global assignment, because the shipped
# YAML-validated loader (``load_catalog_into_cache``) cannot resolve t_-only
# registries.
# ---------------------------------------------------------------------------

#: Offered kit items on the synthetic stall (fixed order drives offer rules).
SYNTH_SHOP_OFFERED_ITEM_KEYS = (
    "t_ember_spray",
    "t_huskapple",
    "t_thorn_knife",
    "t_iron_fang",
)


def build_synth_services_catalog():
    """One fully synthetic guild-economy catalog for the harness processes."""
    from world.rules.tests._guild_service_probes import (
        synth_catalog,
        synth_exam_profile,
        synth_exam_profiles,
        synth_merit_thresholds,
        synth_shop_config,
    )

    # The grafted F entry rank promotes to the kit's second rank; the exam
    # section needs a threshold + profile keyed by THAT rank key, derived
    # from the live registry (never a hardcoded rank key).
    next_rank = synth_next_entry_rank_key()
    return synth_catalog(
        shop_configs={
            SYNTH_SHOP_KEY: synth_shop_config(
                SYNTH_SHOP_KEY, SYNTH_SHOP_OFFERED_ITEM_KEYS
            )
        },
        merit_thresholds={**synth_merit_thresholds(), next_rank: 40},
        exam_profiles={
            **synth_exam_profiles(),
            next_rank: synth_exam_profile(next_rank),
        },
    )


def install_synth_services_catalog():
    """Assign the shared catalog process-globally, register offers + clock sources."""
    from world.rules import guild_config
    from world.rules.guild_config import register_catalog_offers

    catalog = build_synth_services_catalog()
    guild_config.CATALOG = catalog
    register_catalog_offers(catalog)
    # The skipped shipped sync normally registers these; both settlement
    # functions resolve exclusively through get_catalog(), so they serve the
    # synthetic shop identically (registration is idempotent).
    from world.rules.guild_economy import _register_clock_sources

    _register_clock_sources()
    return catalog


def install_synth_affinity_config() -> None:
    """Pre-load the affinity rulebook with a registry-resolvable quest key.

    ``world.rules.affinity_config.load_config`` validates every
    ``cap_breaks[].quest_key`` against the live quest-definition registry,
    and the shipped rulebook names the shipped intro quest — unknown under
    the t_-only install, so the first affinity gain would fail closed. The
    harness pre-assigns ``_CONFIG`` from a copy of the shipped rulebook whose
    cap-break quest keys are rewritten to a kit quest; every numeric rule
    (caps, decay, daily limits) stays the shipped rulebook's.
    """
    import tempfile
    from pathlib import Path

    import yaml

    from world.rules import affinity_config

    if affinity_config._CONFIG is not None:
        return
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY
    from world.tests.synthetic_data import SYNTH_QUESTS

    rulebook = Path(affinity_config.__file__).parent / "rulebook" / "affinity.yaml"
    raw = yaml.safe_load(rulebook.read_text(encoding="utf-8"))
    for entry in raw.get("cap_breaks", []):
        if isinstance(entry, dict) and "quest_key" in entry:
            # Every cap-break quest key collapses onto one kit quest; the
            # validator only checks registry membership, and the kit quests
            # are the only definitions the install carries.
            entry["quest_key"] = next(iter(SYNTH_QUESTS))
    with tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as handle:
        yaml.safe_dump(raw, handle, allow_unicode=True)
        temp_path = Path(handle.name)
    try:
        affinity_config._CONFIG = affinity_config.load_config(
            path=temp_path, definition_registry=QUEST_DEFINITION_REGISTRY
        )
    finally:
        temp_path.unlink(missing_ok=True)


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

#: Display name of the wilderness region the minimap fixture's remembered
#: gateway opens onto (the marker's far-side name). Mirrors the boot mode's
#: region-row display the same way the art label mirrors the archetype row —
#: the Playwright-side process has no Django settings to probe.
SYNTH_WILDERNESS_GATE_LABEL = "荊棘荒林"
SHIPPED_WILDERNESS_GATE_LABEL = "西部丘陵與谷地"


def wilderness_gate_marker_label() -> str:
    """Far-side label the remembered minimap gateway must render with."""
    if synth_mode_enabled():
        return SYNTH_WILDERNESS_GATE_LABEL
    return SHIPPED_WILDERNESS_GATE_LABEL


def art_scene_values() -> "tuple[str, str]":
    """(archetype key, display label) for the current boot mode's art fixture.

    The settled media file is always ``/art/scene/<archetype>.png`` (the art
    service names its output after the archetype key), so journeys derive
    the URL and the caption from this one resolver.
    """
    if synth_mode_enabled():
        return SYNTH_ART_ARCHETYPE, SYNTH_ART_SCENE_LABEL
    return SHIPPED_ART_ARCHETYPE, SHIPPED_ART_SCENE_LABEL

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
