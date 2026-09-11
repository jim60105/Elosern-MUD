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

#: Production-forced innate skill keys the resolver and player handler
#: hardcode (``world.rules.combat_session.BASIC_ATTACK_KEY`` /
#: ``world.rules.disengage.FLEE_SKILL_KEY`` — production seams; this change
#: ships no production-code edits). The t_-only install leaves no rows under
#: these keys, so combat flows cannot submit their universal attack/flee.
SYNTH_INNATE_ATTACK_KEY = "basic_attack"
SYNTH_INNATE_FLEE_KEY = "flee"


def graft_synth_innate_skills() -> None:
    """Ensure the production innate-attack/flee rows exist in the live registry.

    Called by the flagged seed and server processes after
    ``install_synthetic_catalogs()`` swapped the skill catalog to the kit's
    t_-only rows. The rows are the kit's martial template under the
    production seam keys (the ``synth_innate_overlay`` precedent — a
    zero-cost ANY-faction physical strike and a zero-cost self disengage),
    grafted with ``setdefault`` so no installed row is ever overwritten.
    """
    from dataclasses import replace

    from world.skills.registry import (
        SKILL_REGISTRY,
        FactionConstraint,
        SkillCategory,
        TargetSpec,
    )
    from world.tests.synthetic_data import SYNTH_SKILLS

    template = SYNTH_SKILLS["t_cinder_cleave"]
    element_key = SYNTH_SKILLS["t_ember_burst"].element.key
    SKILL_REGISTRY.setdefault(
        SYNTH_INNATE_ATTACK_KEY,
        replace(
            template,
            key=SYNTH_INNATE_ATTACK_KEY,
            label="合成基本攻擊",
            description="以合成武技對單一目標造成物理傷害。",
            faction_constraint=FactionConstraint.ANY,
            effects=[f"damage:{element_key}:physical"],
        ),
    )
    SKILL_REGISTRY.setdefault(
        SYNTH_INNATE_FLEE_KEY,
        replace(
            template,
            key=SYNTH_INNATE_FLEE_KEY,
            label="合成逃跑",
            description="嘗試脫離當前戰鬥的合成身法。",
            target_spec=TargetSpec.SELF,
            faction_constraint=FactionConstraint.SELF_ONLY,
            usable_out_of_combat=False,
            effects=["disengage:self"],
            category=SkillCategory.MOVEMENT,
        ),
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

    Production's terrain model is closed-form integer arithmetic keyed by the
    shipped region and threat-tier vocabularies: ``region_for_coordinates``
    returns shipped partition keys (and the hunting band hardcodes the
    ``"low"`` tier), while the synthetic install swaps the region registry and
    the threat-tier registry to t_-only rows — every wilderness room
    activation would KeyError on a key no installed row answers (the same
    seam class as the F-rank entry graft). Graft one kit-authored row per
    shipped partition/tier key (idempotent ``setdefault``) derived from the
    kit's own templates, so the arithmetic resolves against synthetic content
    without the model ever learning shipped drift.
    """
    from dataclasses import replace

    import world.lore.wilderness_regions as _regions
    import world.lore.monsters as _monsters
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

    # Threat tiers: the population model hardcodes the shipped tier keys
    # (hunting band "low", region tables low/mid/high). Graft one kit-authored
    # tier row per key the closed-form model can name, derived from the kit's
    # own first tier — the shipped-keyed tables and any shipped-keyed rulebook
    # YAML then resolve without seeing t_ rows they would reject.
    tier_template = next(iter(_monsters.MONSTER_TIER_REGISTRY.values()))
    for key in ("low", "mid", "high", "calamity"):
        _monsters.MONSTER_TIER_REGISTRY.setdefault(key, replace(tier_template, key=key))


def graft_synth_combat_modifier() -> None:
    """Give the kit debuff one matched-condition agility-penalty rule.

    The status panel's condition chips come from the combat-modifier rule
    table's per-rule matches; the shipped damaging-buff row is keyed to a
    shipped buff the synthetic install never mounts. Append one authored kit
    rule (id derived from the kit debuff key, same percent the shipped
    analogue carries) to the loaded rule list, so the seeded kit debuff
    surfaces its own modifier-bearing condition row under the synthetic
    install. The table module's ``_RULES`` list is the single match source
    every consumer reads at query time, and the grafted rule names only the
    kit debuff key — shipped rows never match it.
    """
    import world.rules.combat_modifiers as _modifiers
    from world.rules.rulebook.schema import Rule

    rule_id = f"{SYNTH_COMBAT_DEBUFF_KEY}_agility_penalty"
    if any(rule.id == rule_id for rule in _modifiers._RULES):
        return
    _modifiers._RULES.append(
        Rule(
            rule_id,
            {"buff_active": SYNTH_COMBAT_DEBUFF_KEY},
            {"agility": "-10%"},
        )
    )
    # The panel names every matched rule ID through the same coverage table
    # as buff codes; graft the authored chip row alongside the rule.
    from world.rules.status_display import ConditionDisplay, STATUS_DISPLAY

    STATUS_DISPLAY.setdefault(
        rule_id,
        ConditionDisplay(rule_id, "燼灼敏捷減損", "harmful"),
    )


def combat_modifier_condition_rule_id() -> str:
    """The condition code the status panel shows for the seeded debuff's
    modifier rule in the current boot mode."""
    if synth_mode_enabled():
        return f"{SYNTH_COMBAT_DEBUFF_KEY}_agility_penalty"
    return SHIPPED_COMBAT_MODIFIER_RULE_ID


#: The shipped rule-table condition code the status fixture asserts with the
#: shipped debuff (read only when the synthetic flag is OFF).
SHIPPED_COMBAT_MODIFIER_RULE_ID = "poison_agility_penalty"


def graft_synth_defeat_rulebook() -> None:
    """Close the two rulebook seams the combat settlement paths read late.

    ``world.rules.defeat_aftermath`` is imported lazily on the first round
    submit and validates the frozen defeat-aftermath rulebook against the
    live ``BUFF_DEFINITIONS``; under the t_-only install the three marker
    buffs the shipped YAML names are unresolvable, so the import raises
    mid-settlement and every submit answers ``internal_error``. Graft the
    three authored marker buffs with the shipped bounds-only contract
    (``setdefault``: a live install row is never overwritten).

    ``world.rules.monster_behaviour`` resolves every monster without an
    instance behaviour override through the frozen
    ``tier_default_archetype`` table keyed by the shipped tier vocabulary;
    the kit's live threat tiers KeyError there on the first monster policy
    call. Add one archetype mapping per live kit tier key (existing keys,
    including the shipped ones, are untouched).

    The same rulebook's violation table is keyed by lore monster species
    names (the registry's ``example_monsters_zh``), so its fail-closed
    validator rejects every shipped archetype once the install swaps the
    bestiary to t_-only rows. Read the rulebook's own archetype keys and
    union the missing species into one live tier row's example list, so the
    frozen table validates against synthetic content (a shipped install
    already names them and the graft is inert).
    """
    import world.rules.monster_behaviour as _behaviour
    from world.rules.buffs import BUFF_DEFINITIONS, BuffDefinition

    BUFF_DEFINITIONS.setdefault(
        "defeat_weak",
        BuffDefinition(
            key="defeat_weak",
            duration=300,
            tick_interval=None,
            stacking="refresh",
            modifiers={
                "bounds": [
                    {"target": "atk_phys", "ceiling": -5},
                    {"target": "agility", "ceiling": -5},
                    {"target": "defense", "ceiling": -5},
                ]
            },
            polarity="debuff",
        ),
    )
    BUFF_DEFINITIONS.setdefault(
        "aftermath_residue",
        BuffDefinition(
            key="aftermath_residue",
            duration=900,
            tick_interval=None,
            stacking="refresh",
            modifiers={"bounds": [{"target": "agility", "ceiling": -2}]},
            polarity="debuff",
        ),
    )
    BUFF_DEFINITIONS.setdefault(
        "aftermath_humiliated",
        BuffDefinition(
            key="aftermath_humiliated",
            duration=600,
            tick_interval=None,
            stacking="refresh",
            modifiers={"bounds": [{"target": "accuracy", "ceiling": -3}]},
            polarity="debuff",
        ),
    )
    from world.tests.synthetic_data import SYNTH_MONSTER_TIERS

    archetype_defaults = _behaviour.MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]
    ladder = ("instinctive", "pack_hunter")
    for index, tier_key in enumerate(sorted(SYNTH_MONSTER_TIERS)):
        archetype_defaults.setdefault(tier_key, ladder[min(index, len(ladder) - 1)])

    import yaml
    from dataclasses import replace
    from pathlib import Path

    import world.lore.monsters as _monster_lore
    import world.rules as _rules

    rulebook = yaml.safe_load(
        (Path(_rules.__file__).parent / "rulebook" / "defeat_aftermath.yaml").read_text(
            encoding="utf-8"
        )
    )
    needed = set(rulebook["violation"]["archetypes"])
    registry = _monster_lore.MONSTER_TIER_REGISTRY
    live = {name for tier in registry.values() for name in tier.example_monsters_zh}
    missing = sorted(needed - live)
    if missing:
        key = next(iter(registry))
        tier = registry[key]
        registry[key] = replace(
            tier, example_monsters_zh=tuple(tier.example_monsters_zh) + tuple(missing)
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


def lineage_rungs_for(keys) -> dict:
    """Maximum prerequisite-edge level per edge-target over ``keys``.

    ``seed_lineage_proficiency`` honours an already-stored proficiency even
    when it leaves an edge unmet, so a grant set whose prerequisite row
    carries a lower explicit value must raise that row through
    ``grant_lineage``'s ``rungs``. Reads the live registry, so it works
    under either catalog install.
    """
    from world.skills.registry import SKILL_REGISTRY

    rungs: dict = {}
    for key in keys:
        definition = SKILL_REGISTRY.get(key)
        for edge in getattr(definition, "prerequisites", ()):
            rungs[edge.skill_key] = max(
                rungs.get(edge.skill_key, 0), edge.min_proficiency
            )
    return rungs


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
        synth_offer_rule,
        synth_shop_config,
    )

    # The grafted F entry rank promotes to the kit's second rank; the exam
    # section needs a threshold + profile keyed by THAT rank key, derived
    # from the live registry (never a hardcoded rank key).
    next_rank = synth_next_entry_rank_key()
    # The potion (first offered item) ships below its stock cap so selling
    # the single held unit has headroom: the sell journey sells it out and
    # the row disappears — the shipped story's exact shape.
    potion_rule = synth_offer_rule(
        SYNTH_SHOP_OFFERED_ITEM_KEYS[0], max_stock=20, initial_stock=18
    )
    offers = tuple(
        potion_rule if rule.item_key == SYNTH_SHOP_OFFERED_ITEM_KEYS[0] else rule
        for rule in (synth_offer_rule(key) for key in SYNTH_SHOP_OFFERED_ITEM_KEYS)
    )
    return synth_catalog(
        shop_configs={
            SYNTH_SHOP_KEY: synth_shop_config(
                SYNTH_SHOP_KEY, (), offer_rules=offers
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



def store_fixture_values() -> dict:
    """The store fixture's two held-item roles for the current boot mode.

    - ``potion``: the held SELF_HEAL use-deal. At full HP the server refuses
      it with the stable ``hp_full`` reason, and the shop offers it below its
      stock cap (stock headroom), so selling the single held unit is accepted
      and its row disappears — the shipped shop's potion story mirrors here.
    - ``staple``: the other held pair; the shop stocks it AT its cap, so it
      never appears as sellable and its inventory row survives the sale.

    The ``*_display``/``*_rarity`` fields pin what the fixture's item rows
    must present (kit rows differ from shipped ones), so inventory journeys
    compare the committed panel against a mode-derived expectation instead
    of a shipped literal.
    """
    if synth_mode_enabled():
        return {
            "potion_key": "t_ember_spray",
            "staple_key": "t_huskapple",
            "potion_display": "熾焰噴射劑",
            "staple_display": "燼殼果",
            "potion_rarity": "common",
            "staple_rarity": "common",
            "potion_kind": "potion",
            "staple_kind": "material",
        }
    return {
        "potion_key": "healing_potion",
        "staple_key": "meal",
        "potion_display": "治療藥水",
        "staple_display": "普通餐食",
        "potion_rarity": "rare",
        "staple_rarity": "common",
        "potion_kind": "potion",
        "staple_kind": "food",
    }


#: The webclient's closed display vocabulary (mirrors
#: ``web/webclient-app/components/item-icons.js``): the bag inspector spells
#: every committed kind/rarity enum value with these words. Closed client UI
#: vocabulary, not catalog data — some words coincide with shipped catalog
#: tokens, so test paths resolve them through these helpers.
_ITEM_KIND_WORDS = {
    "food": "食物",
    "potion": "藥水",
    "weapon": "武器",
    "armor": "裝甲",
    "accessory": "飾品",
    "ammunition": "彈藥",
    "tool": "工具",
    "material": "素材",
    "misc": "雜項",
}
_ITEM_RARITY_WORDS = {
    "common": "普通",
    "uncommon": "罕見",
    "rare": "稀有",
    "epic": "史詩",
    "legendary": "傳說",
}


def kind_word(kind: str) -> str:
    """The inspector's Traditional-Chinese word for a committed kind value."""
    return _ITEM_KIND_WORDS[kind]


def bag_action_fixture_values() -> dict:
    """The inventory-actions fixture's roles for the current boot mode.

    The fixture seeds one INJURED holder of two potion units and one
    slotted weapon; the combat-bag journey engages the start room's first
    living combat monster. The kit rows differ from the shipped ones in
    every identifier, so the journeys resolve all four through here.
    """
    if synth_mode_enabled():
        return {
            "potion_key": "t_ember_spray",
            "potion_display": "熾焰噴射劑",
            "weapon_key": "t_thorn_knife",
            "engage_target": SYNTH_COMBAT_MONSTERS[0][0],
        }
    return {
        "potion_key": "healing_potion",
        "potion_display": "治療藥水",
        "weapon_key": "plain_sword",
        "engage_target": "goblin",
    }


def rarity_word(rarity: str) -> str:
    """The inspector's Traditional-Chinese word for a committed rarity."""
    return _ITEM_RARITY_WORDS[rarity]


#: Kit combat grant set: actives, passives, and the freeform ladder. The
#: ladder rides ``t_glowmire_bloom`` (its own element's mastery passive
#: ``t_glowmire_mastery`` is granted alongside), mirroring the shipped
#: wind-blade/mastery pairing without naming shipped skills. Ownership order
#: is the panel's intra-group row order: the borrowed-element group carries
#: the deep canopy cast ``t_ember_comet`` first (``grant_lineage`` closes its
#: prereq ``t_ember_burst`` in BEHIND it, the shipped fire tree's exact
#: two-row shape), the utility group carries the context-less disabled row
#: BEFORE the NONE-shape cast carrier so the disabled row is the frame's
#: first focus in both modes.
SYNTH_COMBAT_ACTIVE_SKILLS = (
    "t_ember_comet",
    "t_glowmire_bloom",
    "t_cinder_cleave",
    "t_moss_veil",
    "t_rock_quietus",
    "t_cinder_breath",
)
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


def combat_journey_values() -> dict:
    """The combat-menu journeys' skill roles for the current boot mode.

    Every role is a skill KEY plus the owned-order position that puts it at
    the start of its group/category frame:

    - ``attack_key``: the innate universal-attack seam row (identical key in
      both modes — the production seam, grafted under the synthetic install).
    - ``spell_key``: the first owned elemental spell, first skill of the
      first element sub-group (SINGLE target, borrows the first registered
      element so its sub-group shares the shipped first element's label).
    - ``prereq_key``: the prereq row ``grant_lineage`` closes in behind the
      spell, second in the same sub-group's ownership order.
    - ``ladder_key``: the mastery-entitled second element sub-group's active
      (the scale-step/AREA journey's cast target).
    - ``none_key``: the owned NONE-shape active the NONE-payload journey
      submits (enhancement in shipped mode; utility under the kit install).
    - ``none_category``: the ``SkillCategory`` value ``none_key`` lives in.
    - ``self_disabled_key``: the utility active whose effect handler
      declares an event-context key the combat session never supplies, so
      the menu exposes it disabled.
    - ``spell_element`` / ``ladder_element``: the ELEMENT_REGISTRY keys the
      sub-groups of the elemental category are named after (the spell borrows
      the shipped first element in both modes; the ladder's element differs).
    - ``element_group_order``: the elemental sub-group keys in the live
      ELEMENT_REGISTRY declaration order the panel sorts by (the borrowed
      shipped element is grafted after the kit's own rows under the synthetic
      install, so the pair is reversed relative to shipped mode).
    - ``spell_group_index`` / ``ladder_group_index``: the positions of those
      sub-groups inside the elemental category frame under that order.
    - ``spell_element_label``: the display label the spell's sub-group renders.
    - ``ladder_mp_cost``: the ladder's base MP cost (the detail pane's 威力
      scale rows render the ascending multiples of this value).
    - ``enhancement_key``: the owned active of the enhancement category's
      null-keyed sub-group (NONE-shape in shipped mode).
    - ``engage_target``: the first living combat monster in the start room
      (the journeys' ``engage`` argument).
    """
    if synth_mode_enabled():
        return {
            "attack_key": SYNTH_INNATE_ATTACK_KEY,
            "spell_key": "t_ember_comet",
            "prereq_key": "t_ember_burst",
            "ladder_key": "t_glowmire_bloom",
            "none_key": "t_cinder_breath",
            "none_category": "utility",
            "self_disabled_key": "t_rock_quietus",
            "spell_element": "fire",
            "ladder_element": "t_glowmire",
            # The kit install registers t_glowmire first; the borrowed shipped
            # ``fire`` row is grafted in afterwards, so the registry order is
            # reversed relative to shipped mode.
            "element_group_order": ("t_glowmire", "fire"),
            "spell_group_index": 1,
            "ladder_group_index": 0,
            "spell_element_label": "火",
            "ladder_mp_cost": 14,
            "enhancement_key": "t_moss_veil",
            "engage_target": SYNTH_COMBAT_MONSTERS[0][0],
        }
    return {
        "attack_key": SHIPPED_INNATE_ATTACK_KEY,
        "spell_key": SHIPPED_COMBAT_SPELL_KEY,
        "prereq_key": SHIPPED_COMBAT_SPELL_PREREQ_KEY,
        "ladder_key": SHIPPED_COMBAT_LADDER_SKILL,
        "none_key": SHIPPED_COMBAT_NONE_SKILL,
        "none_category": "enhancement",
        "self_disabled_key": SHIPPED_COMBAT_DISABLED_SKILL,
        "spell_element": "fire",
        "ladder_element": "wind",
        "element_group_order": ("fire", "wind"),
        "spell_group_index": 0,
        "ladder_group_index": 1,
        "spell_element_label": "火",
        "ladder_mp_cost": 14,
        "enhancement_key": SHIPPED_COMBAT_NONE_SKILL,
        "engage_target": SHIPPED_COMBAT_MONSTERS[0][0],
    }


#: Combat-menu shipped-mode roles (read only when the synthetic flag is OFF).
SHIPPED_INNATE_ATTACK_KEY = "basic_attack"
SHIPPED_COMBAT_SPELL_KEY = "fire_ball"
SHIPPED_COMBAT_SPELL_PREREQ_KEY = "fire_arrow"
SHIPPED_COMBAT_NONE_SKILL = "concentration"
SHIPPED_COMBAT_DISABLED_SKILL = "status_disguise"


def title_codex_values() -> dict:
    """The codex fixture's fixed-title rows for the current boot mode.

    (banked keys, banked displays in bank order, the display the freshly
    registered character previews — the FIRST banked row auto-equips the
    empty fixed slot — and the deliberately-locked row's key/display/hint).
    The kit displays mirror the kit rows' authored text: the Playwright-side
    process has no Django settings, so they are mirrored here exactly like
    the art scene label.
    """
    if synth_mode_enabled():
        return {
            "banked_keys": tuple(SYNTH_TITLE_BANKED_KEYS),
            "banked_displays": ("初獵合成者", "驛站常客"),
            "banked_categories": ("combat", "romance"),
            "locked_key": SYNTH_TITLE_LOCKED_KEY,
            "locked_display": "深霧行者",
            "locked_hint": "在合成荒野深處留下足夠多的到訪紀錄即可獲得。",
            "locked_category": "explore",
        }
    return {
        "banked_keys": (SHIPPED_TITLE_RANK_F_KEY, SHIPPED_TITLE_RANK_E_KEY),
        "banked_displays": ("F級冒險者", "E級斥候"),
        "banked_categories": ("guild", "guild"),
        "locked_key": "g_s_rank",
        "locked_display": "S級傳說",
        "locked_hint": "通過 S 級公會考核即可獲得。",
        "locked_category": "guild",
    }
