"""Runtime catalog probes (shared by the synthetic-aware seed fixtures).

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every body ships verbatim."""

from __future__ import annotations


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
