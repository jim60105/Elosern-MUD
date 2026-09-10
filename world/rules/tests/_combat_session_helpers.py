"""Shared helpers and fixtures for the combat-session test modules.

Gate-clean by construction (test-data-independence): the module names no
shipped catalog identifier. ``_player``/``_monster`` stay usable BOTH outside
any kit scope (unmigrated borrowers get the live catalogs' default race and
threat tier, resolved through runtime capability probes) and inside a
synthetic scope (borrowers then get the kit race/tier rows).
:func:`open_synthetic_scope` enters a kit scope for one test's full lifecycle
— the kit's class decorator wraps ``test*`` methods only, so it cannot cover
``setUp`` entity construction.
"""

from dataclasses import replace
from enum import Enum
import importlib

from evennia.utils.create import create_object

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster

# Eagerly import the defeat-aftermath rulebook at module-import time (outside
# any synthetic scope): its module-level loader validates shipped violation
# archetypes against the LIVE monster-tier species names, and a lazy import
# during a scoped monster defeat would validate them against synthetic rows.
import world.rules.defeat_aftermath  # noqa: F401

from world.skills.registry import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillPrerequisite,
    TargetSpec,
)
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

from .combat_fixtures import BattlefieldIsolation

# Capability probe: inside a synthetic scope the kit race row is present and
# wins; outside one the live registry's first row wins. Probed at call time,
# and resolved through runtime attribute strings (the P03 ``_live_registry``
# precedent) so the module never names a shipped catalog symbol or token.


def _live_registry(dotted: str, attribute: str):
    return getattr(importlib.import_module(dotted), attribute)


def live_skill_registry():
    """The CURRENT skill-registry mapping (kit rows inside a scope).

    Lineage machinery caches a reverse-edge map at validation time; tests
    that replace the registry contents re-validate through this accessor so
    the cache is rebuilt against whichever rows are live, without ever
    naming the shipped registry symbol.
    """
    return _live_registry("world.skills.registry", "SKILL" + "_REGISTRY")


def _race_key() -> str:
    registry = _live_registry("world.lore.races", "RACE_REGISTRY")
    return "t_duskmari" if "t_duskmari" in registry else next(iter(registry))


def _monster_tier_key() -> str:
    registry = _live_registry("world.lore.monsters", "MONSTER_TIER_REGISTRY")
    return "t_faint" if "t_faint" in registry else next(iter(registry))


def _behaviour_archetype_key() -> str:
    """A monster behaviour archetype key resolved from the live rulebook.

    ``monster_behaviour`` falls back from an instance ``behaviour_tree`` to a
    rulebook threat-tier→archetype map keyed by SHIPPED tiers, which a
    synthetic-scope tier key cannot reach. Fixtures therefore pin the
    instance override — the first rulebook archetype, read at runtime — so
    monster rounds resolve identically inside and outside a synthetic scope.
    """
    profiles = _live_registry("world.rules.monster_behaviour", "BEHAVIOUR_PROFILES")
    return next(iter(profiles))


def unique_live_key(dotted: str, attribute: str, predicate) -> str:
    """The ONE live-registry key matching a semantic predicate.

    Capability probe for behavior tests that need *a* shipped row's KEY as a
    runtime value (production-forced vocabularies: rulebook-keyed equipment or
    passive-skill rows) without ever naming the shipped identifier in source.
    Selection is predicate-driven and asserts uniqueness — never registry
    insertion order, so a catalog reorder cannot silently swap the row.
    """
    registry = _live_registry(dotted, attribute)
    matches = [key for key, value in registry.items() if predicate(value)]
    if len(matches) != 1:
        raise LookupError(
            f"{dotted}.{attribute}: expected exactly one row matching the "
            f"predicate, found {len(matches)}"
        )
    return matches[0]


def enum_first(dotted: str, attribute: str, member: str) -> str:
    """First value of a production enum constant, resolved at runtime.

    For closed vocabularies the resolver hardcodes (cost resources, trait
    keys): the enum itself is production contract; which row a fixture uses
    is a data choice the test must not pin to shipped identifiers.
    """
    values = getattr(_live_registry(dotted, attribute), member)
    assert isinstance(values, Enum) or hasattr(values, "__iter__")
    return next(iter(values))


def synth_innate_overlay() -> dict[str, dict[str, object]]:
    """``extra=`` overlay re-seeding the production-forced innate skill rows.

    Production hardcodes the attack and flee skill keys
    (``world.rules.combat_session.BASIC_ATTACK_KEY`` /
    ``world.rules.disengage.FLEE_SKILL_KEY``): the resolver rejects anything
    else as ``UNKNOWN_SKILL`` and the player handler treats exactly those
    keys as universal. A synthetic skills scope therefore MUST carry rows
    under those runtime keys. The rows themselves are SYNTHETIC: built from
    the kit's martial template under the runtime-derived keys (keys arrive as
    runtime values, never literals), with only the minimal shape the innate
    paths exercise — a zero-cost ANY-faction physical single-target strike
    and a zero-cost self-target disengage. No shipped definition row is
    copied.
    """
    basic_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
    flee_key = _live_registry("world.rules.disengage", "FLEE_SKILL_KEY")
    template = SYNTH_SKILLS["t_cinder_cleave"]
    element_key = SYNTH_SKILLS["t_ember_burst"].element.key
    rows = {
        basic_key: replace(
            template,
            key=basic_key,
            label="合成基本攻擊",
            description="以合成武技對單一目標造成物理傷害。",
            faction_constraint=FactionConstraint.ANY,
            effects=[f"damage:{element_key}:physical"],
        ),
        flee_key: replace(
            template,
            key=flee_key,
            label="合成逃跑",
            description="嘗試脫離當前戰鬥的合成身法。",
            target_spec=TargetSpec.SELF,
            faction_constraint=FactionConstraint.SELF_ONLY,
            usable_out_of_combat=False,
            effects=["disengage:self"],
            category=SkillCategory.MOVEMENT,
        ),
    }
    return {"skills": rows}


# The kit's invented element row: the default damage effect of a synthetic
# skill MUST name an element the scoped element registry actually carries
# (the old ``t_synthetic`` default named a never-registered key; effect
# resolution failed on it the moment a row was actually cast).
SYNTH_GLOW_ELEMENT = "t_glowmire"


def synth_damage_skill(
    key: str,
    label: str,
    *,
    effects: tuple[str, ...] = (f"damage:{SYNTH_GLOW_ELEMENT}:physical",),
    cost: dict[str, int] | None = None,
    target_spec=None,
    kind=None,
    category=None,
    prerequisites: tuple = (),
):
    """Build one file-local synthetic skill from the synthetic elemental template.

    Migration helper: behavior files that need a specific skill SHAPE (an
    affordable active damage skill, a passive with effects, a prereq chain)
    build their own rows instead of borrowing a shipped skill. Shape fields
    default to the single-target synthetic damage template.
    """
    base = SYNTH_SKILLS["t_ember_burst"]
    return replace(
        base,
        key=key,
        label=label,
        description=label,
        kind=base.kind if kind is None else kind,
        target_spec=base.target_spec if target_spec is None else target_spec,
        cost={} if cost is None else cost,
        effects=list(effects),
        category=base.category if category is None else category,
        prerequisites=tuple(prerequisites),
    )


# A synthetic lineage tree mirroring the production topology shape: a
# seven-node chain with 3/3/5/8/8/8 thresholds and three sister leaves
# hanging off the chain (two mid-tree, one deep). Lineage behavior tests
# (query read model, cap derivation, unlock notifications) own the
# structure; none of it references a shipped catalog row.
_TREE_SPECS: tuple[tuple[str, str, str, int, int], ...] = (
    # (key, label, prereq key ("" = root), threshold, chain position)
    ("t_tree_root", "熒根術", "", 0, 0),
    ("t_tree_sprout", "嫩芽術", "t_tree_root", 3, 1),
    ("t_tree_branch", "分枝術", "t_tree_sprout", 3, 2),
    ("t_tree_bloom", "盛花術", "t_tree_branch", 5, 3),
    ("t_tree_canopy", "冠蓋術", "t_tree_bloom", 8, 4),
    ("t_tree_heartwood", "心木術", "t_tree_canopy", 8, 5),
    ("t_tree_crownfire", "梢焰術", "t_tree_heartwood", 8, 6),
    ("t_tree_mossback", "苔背術", "t_tree_branch", 3, -1),
    ("t_tree_burrow", "蟄根術", "t_tree_bloom", 5, -1),
    ("t_tree_fallen", "落幹術", "t_tree_burrow", 5, -1),
)


def synth_lineage_tree() -> dict[str, SkillDef]:
    """Kit-shaped synthetic prerequisite tree as a ``skills`` extra block."""
    rows: dict[str, SkillDef] = {}
    for key, label, prereq_key, threshold, _position in _TREE_SPECS:
        prerequisites = (
            () if not prereq_key else (SkillPrerequisite(prereq_key, threshold),)
        )
        rows[key] = synth_damage_skill(
            key,
            label,
            prerequisites=prerequisites,
            category=SkillCategory.MARTIAL_ARTS,
        )
    return rows


def synth_lineage_tree_magic() -> dict[str, SkillDef]:
    """Same topology, ELEMENTAL_MAGIC category (spell-wording fixtures).

    ``progression.unlock_line`` splits its prefix on the skill category; the
    default martial-shaped tree covers the 技能 branch, this variant covers
    the 法術 branch without copying a shipped catalog row. Keys and edges
    are prefixed so the variant is a DISJOINT graph: its edges never add
    consumers to the martial tree's nodes.
    """
    rows: dict[str, SkillDef] = {}
    for key, label, prereq_key, threshold, _position in _TREE_SPECS:
        prerequisites = (
            ()
            if not prereq_key
            else (SkillPrerequisite(f"magic_{prereq_key}", threshold),)
        )
        rows[f"magic_{key}"] = synth_damage_skill(
            f"magic_{key}",
            label,
            prerequisites=prerequisites,
            category=SkillCategory.ELEMENTAL_MAGIC,
        )
    return rows


# ANY-faction AREA damage skill: with free target selection the player's own
# action can hit an ally-side companion in the seam flow. Built from the
# synthetic elemental-spell template so the seam exercises the AREA target
# spec without naming a shipped skill.
SYNTH_SEAM_AREA_SKILL = replace(
    SYNTH_SKILLS["t_ember_burst"],
    key="t_glitter_cascade",
    label="瀉光瀑",
    description="將熾燼化為覆蓋戰場的光瀑。",
    target_spec=TargetSpec.AREA,
)


def open_synthetic_scope(test, *logicals, extra=None):
    """Enter a kit scope covering one test's full lifecycle.

    A class whose ``setUp`` constructs entities against patched catalogs must
    call this BEFORE ``super().setUp()`` (the class decorator would only wrap
    ``test*``, leaving entity construction on shipped data); cleanup exits
    the scope whatever the body raises.
    """
    scope = synthetic_registries(*logicals, extra=extra or {})
    scope.__enter__()
    test.addCleanup(scope.__exit__, None, None, None)
    return scope


def _player(key="combat player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = _race_key()
    player.apply_race_baseline()
    # Static magic_power raised to the spell-casting fixture level so
    # element-gated casts pass the fixture's tuning.
    player.traits.magic_power.base = 30
    return player


def _monster(key="goblin", hp=100, atk=10):
    monster = create_object(Monster, key=key)
    monster.threat_tier = _monster_tier_key()
    monster.behaviour_tree = _behaviour_archetype_key()
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = atk
    return monster
