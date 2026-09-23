"""Ownership/passive effect declarations and the routing-strength vocabularies.

Part of :mod:`world.skills.effects`; every name is re-exported from the
package root.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

# Continuous-valued ownership effects read by deterministic consumers.
# ``StatMultiplyEffect`` is consumed by ``SkillHandler.effective_value``;
# ``GrowthRateEffect`` is consumed by ``world/rules/progression.py``'s
# practice-growth composite via the scoped ``growth_rate:practice:<multiplier>:<scope>``
# convention (the retired unscoped ``growth_rate:practice:<N>`` and
# ``growth_rate:magic:<N>`` forms fail closed at parse).
@dataclass(frozen=True)
class StatMultiplyEffect:
    """Multiply one stored trait by a fixed factor while owned."""

    trait: str
    multiplier: float


@dataclass(frozen=True)
class GrowthRateEffect:
    """Multiply one growth stat by a fixed factor while owned.

    ``scope`` names the single ``ELEMENT_REGISTRY`` key whose practice the
    factor accelerates; a growth rate that does not name its tree is not
    expressible (the unscoped three-segment form fails closed at parse).
    """

    stat: str
    multiplier: float
    scope: str


def _known_buff_keys() -> frozenset[str]:
    """Return known buff keys for policy validation without importing world.rules.

    The single-writer boundary forbids world.skills from importing world.rules.
    When world.rules.buffs is loaded in memory, read BUFF_DEFINITIONS directly
    from sys.modules to observe live and synthetic test definitions. Otherwise,
    parse world/rules/rulebook/buffs.yaml directly.
    """
    import sys

    rules_buffs = sys.modules.get("world.rules.buffs")
    if rules_buffs is not None and hasattr(rules_buffs, "BUFF_DEFINITIONS"):
        return frozenset(rules_buffs.BUFF_DEFINITIONS)

    import yaml
    from pathlib import Path

    # One level deeper than the retired flat module: effects/passives.py
    # resolves the rulebook via effects -> skills -> world.
    buffs_path = Path(__file__).parent.parent.parent / "rules" / "rulebook" / "buffs.yaml"
    if not buffs_path.exists():
        return frozenset()
    try:
        data = yaml.safe_load(buffs_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return frozenset(
                entry["key"]
                for entry in data
                if isinstance(entry, dict) and "key" in entry
            )
    except (OSError, yaml.YAMLError):
        return frozenset()
    return frozenset()


@dataclass(frozen=True)
class SexualMasteryEffect:
    """Unlock casting of the sex-magic skill family regardless of magic level."""


class EffectAudience(StrEnum):
    """Routing scope for an individual skill effect component."""

    SELECTED = "selected"
    SELF = "self"
    ALLIES = "allies"
    ENEMIES = "enemies"


# Ownership-triggered adjustment bundles resolved by the rule-table engine
# (``combat_modifiers.yaml``) via the ``skill_owned`` condition.
@dataclass(frozen=True)
class RuleTableEffect:
    """Name the rule-table key this passive resolves against."""

    rule_key: str


@dataclass(frozen=True)
class FlavorEffect:
    """A deliberately inert descriptive passive; no consumer reads it."""

    name: str


# Ownership-triggered movement waivers (flight/flash_step are PASSIVE).
@dataclass(frozen=True)
class MovementEffect:
    """Name the movement mode granted by owning this skill.

    The waiver set is consumed by ``world.rules.movement.charge_movement``:
    owning ``flight`` waives the ``wilderness_move`` clock cost, and owning
    either mode passes any exit marked ``requires_flight``.
    """

    mode: Literal["flight", "flash_step"]


@dataclass(frozen=True)
class WeaponStyleEffect:
    """Name the weapon stance this skill enters.

    ``light_sword`` is no longer a ``weapon_style`` value — its skill moved to
    the ``damage`` convention. The remaining stance case (``dual_wield``) is
    consumed by the ``combat_modifiers.yaml`` rule table via the ``skill_owned``
    and ``dual_wielding`` conditions.
    """

    style: str


@dataclass(frozen=True)
class DivineMysteryEffect:
    """One divine-mystery entry; ``mechanized`` flags a real cast path."""

    name: str
    mechanized: bool = False


# Thin wrappers for the prefixes with already-working cast handlers in
# ``world/rules/action.py`` and siblings. Their handlers still receive the raw
# string today; the typed instances exist so every declared prefix has one
# faithful representation and later proposals can source handlers from them.
@dataclass(frozen=True)
class ConferralEffect:
    """Grant the target a fractional share of one owned skill's effect."""


@dataclass(frozen=True)
class DisguiseEffect:
    """Replace the target's displayed stats with a disguise override."""


@dataclass(frozen=True)
class RevealDisguiseEffect:
    """Lift a target's veil, whatever it is.

    This world admits exactly one grade of veil (collapse-veil-reveal-line):
    only the bloodline-gated divine mystery can write one, so a reveal either
    lifts the veil it finds or finds none. The bare prefix is the whole
    grammar; any payload fails at parse, and therefore at registry load.
    """


@dataclass(frozen=True)
class BuffApplyEffect:
    """Apply one definition-keyed buff to every target."""

    buff_key: str


@dataclass(frozen=True)
class SelfBuffApplyEffect:
    """Apply one definition-keyed buff to the caster."""

    buff_key: str


@dataclass(frozen=True)
class SessionStampEffect:
    """Stamp one named session-record field with the caster's durable session id.

    Mounted by the church martyrdom-vow rail (design §5.8): casting the vow
    writes the current session's id into the field the effect names, so the
    defeat-aftermath pool filter can identify the marked martyr and stale
    stamps (a foreign session id) can never fire.
    """

    key: str


@dataclass(frozen=True)
class ConferGrowthRateEffect:
    """Confer the caster's magic-growth rate on one target."""


@dataclass(frozen=True)
class RevokeGrantsEffect:
    """Remove every conferral on one target: all skill grants and every
    ``conferred_growth_rate`` buff instance, whatever their source."""
