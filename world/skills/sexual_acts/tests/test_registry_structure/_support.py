"""Data-contract test: sexual act registry structure contract
File-local rulebook probes and check helpers for the
``test_registry_structure`` slices.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
"""

from tools.spec_traceability import covers_requirement
import inspect
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import BODY_PARTS, GENERIC_BODY_PART
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.rules.rulebook.schema import load_rules
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.skills import handler
from world.skills.handler import SkillHandler
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)
import world.skills.registry as registry_module
from world.skills import sexual_acts
import world.skills.sexual_acts._builder as _builder_module
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.effects import TargetSexualEventEffect
from world.skills.sexual_acts.divine import DIVINE_ACTS
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    _FORBIDDEN_SEXUAL_EVENTS,
    SexualActDef,
    _act_family,
)

_SEXUAL_YAML_PATH = Path(__file__).parents[4] / "rules" / "rulebook" / "sexual.yaml"

# The two pre-existing mastery/mystery skills categorised SEXUAL_ACT that
# carry no SexualActDef by design (acquisition-path skills, not acts).
# divine_sexual_arts joined the catalogue as the eighth hand-built divine row
# (integrate-divine-sexual-arts-catalog), so it participates in the agreement
# comparison on both sides and must never return to this set.
_MASTERY_EXCLUSIONS = frozenset(
    {"divine_sexual_mastery", "reincarnation_boon_yuna"}
)

_KNOWN_EVENTS = frozenset(
    rule.when["event"]
    for rule in load_rules(_SEXUAL_YAML_PATH)
    if "event" in rule.when
)

def check_names_resolve(act: SexualActDef) -> None:
    """Assert every counter/event an act names actually exists.

    Raises ``AssertionError`` naming the act's key and the unrecognized
    string, so the failure points at the offending catalog row. Pair-event
    names are checked exactly like ``sexual_events`` names: both are
    rulebook ``when["event"]`` values.
    """
    for name in (*act.unlock, *act.actor_counters, *act.participant_counters):
        if name not in _LIFETIME_COUNTER_KEYS:
            raise AssertionError(
                f"act {act.key!r} names unknown counter {name!r}"
            )
    for name in (*act.sexual_events, *(event for _, event in act.pair_events)):
        if name not in _KNOWN_EVENTS:
            raise AssertionError(f"act {act.key!r} names unknown event {name!r}")

def check_registries_agree(act_registry, skill_registry) -> None:
    """Assert both registries carry exactly the same act keys.

    ``SKILL_REGISTRY``'s ``SEXUAL_ACT``-categorised keys must equal
    ``SEXUAL_ACT_REGISTRY``'s keys, modulo the named mastery/mystery
    exclusions. Raises ``AssertionError`` naming any unmatched key.
    """
    skill_act_keys = {
        key
        for key, skill in skill_registry.items()
        if skill.category is SkillCategory.SEXUAL_ACT
    } - _MASTERY_EXCLUSIONS
    unmatched = skill_act_keys ^ set(act_registry)
    if unmatched:
        raise AssertionError(
            "SEXUAL_ACT_REGISTRY and SKILL_REGISTRY disagree on act keys: "
            f"{sorted(unmatched)}"
        )

def check_solo_acts_declare_no_participant_counters(act_registry, skill_registry) -> None:
    """Assert every SELF-target act declares ``participant_counters=()``.

    A solo act has no other participant to credit, so a non-empty
    participant counter list would silently mis-credit nobody.
    """
    for key, act in act_registry.items():
        skill = skill_registry[key]
        if skill.target_spec is TargetSpec.SELF and act.participant_counters:
            raise AssertionError(
                f"act {key!r} is SELF-targeted but declares "
                f"participant_counters {act.participant_counters}"
            )

def check_external_acts_declare_a_target_part(act_registry, skill_registry) -> None:
    """Assert every non-異種/神之秘法 act targeting others declares a target part.

    The two parless lines may omit ``target_part`` by design (monsters are
    arbitrarily shaped, divine arts operate through divinity); any other line
    targeting a second entity must declare the part that entity's pleasure is
    computed against, or ``resolve_part`` would silently fall back to the
    generic channel (design risk mitigation).
    """
    for key, act in act_registry.items():
        skill = skill_registry[key]
        if skill.group in ("異種", "神之秘法"):
            continue
        if skill.target_spec in (TargetSpec.SELF, TargetSpec.NONE):
            continue
        if act.target_part is None:
            raise AssertionError(
                f"act {key!r} on line {skill.group!r} targets others "
                "but declares no target_part"
            )

def _seed_act_row(
    key: str = "test_act",
    *,
    line: str = "獨處線",
    target_spec: TargetSpec = TargetSpec.SELF,
    unlock: dict[str, int] | None = None,
    base_pleasure: int = 10,
    actor_part: str | None = "私處",
    target_part: str | None = None,
    actor_pleasure_ratio: float = 0.5,
    actor_counters: tuple[str, ...] = ("restraint_count",),
    participant_counters: tuple[str, ...] = (),
    sexual_events: tuple[str, ...] = (),
    resistible: bool = True,
    pair_events: tuple[tuple[tuple[str, str], str], ...] = (),
    requires_divine_arts: bool = False,
) -> tuple[SkillDef, SexualActDef]:
    """Build one synthetic act row for contract tests without catalog content.

    A non-empty ``pair_events`` table becomes the row's optional 14th field,
    keeping ordinary rows at the 13-field length.
    """
    row = (
        key,
        "測試行為",
        "僅存在於測試中的合成行為。",
        target_spec,
        {} if unlock is None else unlock,
        base_pleasure,
        actor_part,
        target_part,
        actor_pleasure_ratio,
        actor_counters,
        participant_counters,
        sexual_events,
        resistible,
    )
    if pair_events:
        row = (*row, pair_events)
    (skill, act), = _act_family(
        line,
        row,
        requires_divine_arts=requires_divine_arts,
    )
    return skill, act

# The seven pairs the 神之秘法 line shipped before the integration landed.
_PRE_INTEGRATION_DIVINE_KEYS = (
    "divine_extreme_climax_command",
    "divine_timed_copulation",
    "divine_realm_drain",
    "divine_sensitivity_creation",
    "divine_shame_deprivation",
    "divine_absolute_submission",
    "divine_purity_restoration",
)

def _main_registry_source() -> str:
    import world.skills.registry as main_registry

    # The registry is a package now: cover every shipped data/assembly module
    # (the former single-module source) so the absence assertion still spans
    # all hand-written registry rows.
    package_root = Path(inspect.getsourcefile(main_registry)).parent
    sources = [inspect.getsource(main_registry)]
    for module_path in sorted(package_root.glob("*.py")):
        sources.append(module_path.read_text(encoding="utf-8"))
    return "\n".join(sources)
