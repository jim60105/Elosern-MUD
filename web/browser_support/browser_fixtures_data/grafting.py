"""Registry grafts closing the production seams the t_-only install opens.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every body ships verbatim (the rulebook-path probe follows
the package depth)."""

from __future__ import annotations

from types import MappingProxyType

from web.browser_support.browser_fixtures_data.mode import synth_mode_enabled

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
            category=SkillCategory.MARTIAL_ARTS,
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
    from web.browser_support.browser_fixtures_data.combat_fixtures import (
        SYNTH_COMBAT_DEBUFF_KEY,
    )

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
        from web.browser_support.browser_fixtures_data.combat_fixtures import (
            SYNTH_COMBAT_DEBUFF_KEY,
        )

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


def graft_synth_state_reaction_rulebook() -> None:
    """Close the state-reaction load seams the t_-only install opens.

    ``world.rules.state_reactions`` validates its shipped YAML at import
    against the LIVE ``BUFF_DEFINITIONS`` and ``MP_COST_TIERS``. The
    synthetic install replaces both with t_-only rows, which removes
    vocabulary the shipped rulebook legitimately names: every buff key the
    shipped reaction rules reference (markers, counters, ignite/ward marks).
    (``pleasure_gain`` rows are loss-fraction shapes since the
    pain-to-pleasure repricing, so they no longer name tier vocabulary.)
    Importing the module after the install then fail-closes, and the browser
    seed dies inside the first ``apply_buff`` dispatch. Same seam class as
    ``graft_synth_defeat_rulebook``: restore both vocabularies ADDITIVELY
    (``setdefault``), so kit ``t_``-keyed lookups keep resolving their own
    rows first.

    The buff rows are DERIVED, not hand-listed: every buff key named by a
    ``then`` action of the shipped ``state_reactions.yaml`` is re-grafted
    from its shipped ``buffs.yaml`` definition (parsed through the real
    loader, so duration/polarity/round_order parity is structural, not a
    comment promise). Per-wave hand-listing repeatedly drifted (light
    marker, earth carapace, water suffocation, fire ignite, lightning
    wards each needed a follow-up graft); this closes the seam class.

    Ordering invariant: nothing may import ``world.rules.state_reactions``
    between the install and this graft (the seed reaches it lazily via the
    first ``apply_buff``; the server boot imports it as a startup step
    after ``at_server_init``). The assertion below fails loudly if a future
    resequencing breaks that.
    """
    import sys
    from pathlib import Path

    assert "world.rules.state_reactions" not in sys.modules, (
        "state_reactions was imported before the synth graft; the "
        "install-time validation already fail-closed against t_-only data"
    )
    import yaml

    from world.rules.buffs import BUFF_DEFINITIONS, load_buff_definitions
    from world.skills.cost_tiers import MP_COST_TIERS, MP_SHIPPED_COST_TIERS

    rulebook_dir = Path(__file__).resolve().parents[3] / "world" / "rules" / "rulebook"
    reactions_raw = yaml.safe_load(
        (rulebook_dir / "state_reactions.yaml").read_text(encoding="utf-8")
    )
    shipped_buffs = load_buff_definitions(rulebook_dir / "buffs.yaml")
    for rule in reactions_raw or []:
        when = rule.get("when") or {}
        then = rule.get("then") or {}
        referenced: set[str] = set()
        # then-actions are validated at import; when.buff_active mounts are
        # resolved against BUFF_DEFINITIONS at dispatch.
        mount = when.get("buff_active")
        if isinstance(mount, str):
            referenced.add(mount)
        for action in ("apply_buff", "remove_buff", "apply_buff_to_source", "mark_order_op"):
            buff_key = then.get(action)
            if not isinstance(buff_key, str):
                continue
            referenced.add(buff_key)
        for buff_key in referenced:
            # A referenced key missing from shipped buffs.yaml is a rulebook
            # bug; the real loader's dict access fails loudly here instead of
            # silently leaving the import-time validation to fail later.
            BUFF_DEFINITIONS.setdefault(buff_key, shipped_buffs[buff_key])
    # Re-add the shipped CostTier rows beside the installed t_ rows. The
    # shipped state reactions no longer name tier vocabulary (pleasure_gain
    # is loss-fraction shaped), but the rows stay for other shipped-data
    # consumers; this also widens spell_tier_for's area band to include
    # 91-110 for future kit spells (no kit row lands there today); harmless
    # for tier-label reads.
    for tier_key, tier in MP_SHIPPED_COST_TIERS.items():
        MP_COST_TIERS.setdefault(tier_key, tier)


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
