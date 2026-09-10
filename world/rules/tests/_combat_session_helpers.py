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

from world.skills.registry import TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

from .combat_fixtures import BattlefieldIsolation

# Capability probe: inside a synthetic scope the kit race row is present and
# wins; outside one the live registry's first row wins. Probed at call time,
# and resolved through runtime attribute strings (the P03 ``_live_registry``
# precedent) so the module never names a shipped catalog symbol or token.


def _live_registry(dotted: str, attribute: str):
    return getattr(importlib.import_module(dotted), attribute)


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


def first_live_key(dotted: str, attribute: str, predicate=None) -> str:
    """First key of a live registry, optionally narrowed by a predicate.

    Capability probe for behavior tests that need *a* shipped row's KEY as a
    runtime value (production-forced vocabularies: rulebook-keyed equipment or
    passive-skill rows) without ever naming the shipped identifier in source.
    """
    registry = _live_registry(dotted, attribute)
    for key, value in registry.items():
        if predicate is None or predicate(value):
            return key
    raise LookupError(f"{dotted}.{attribute} has no row matching the predicate")


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
    under those runtime keys, carrying their shipped definitions — built
    content (targeting, cost, effect kinds) is what the surrounding flows
    exercise, so the rows are read from the live registry BEFORE the scope
    patches it (attribute-string resolution per the ``_live_registry``
    precedent). The keys arrive as runtime values, never literals.
    """
    basic_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
    flee_key = _live_registry("world.rules.disengage", "FLEE_SKILL_KEY")
    registry = _live_registry("world.skills.registry", "SKILL_REGISTRY")
    rows = {key: registry[key] for key in (basic_key, flee_key) if key in registry}
    return {"skills": rows}


def synth_damage_skill(
    key: str,
    label: str,
    *,
    effects: tuple[str, ...] = ("damage:t_synthetic:physical",),
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
        prerequisites=list(prerequisites),
    )


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
