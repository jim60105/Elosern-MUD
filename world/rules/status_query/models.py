"""Frozen read-model dataclasses, vocabularies, and labels for the status package.

Presentation must never materialize lazy handlers or default state. This module
owns only the immutable value types, the stable label contracts, and the closed
breakdown vocabularies the readers and builders share; it reads nothing.
"""

from dataclasses import dataclass
from typing import Any

from world.skills.registry import SkillCategory

# Stable Traditional Chinese labels for the canonical trait keys, shared by
# every presentation surface: the WebClient character panel and the
# displayed-stats block appended on ``look <target>`` (displayed-stats-view
# A2). Consumers must read this map instead of duplicating the labels.
TRAIT_LABELS = {
    "hp": "生命",
    "mp": "魔力",
    "sp": "耐力",
    "atk_phys": "攻擊",
    "agility": "敏捷",
    "defense": "防禦",
    "magic_power": "魔力",
    "guild_merit": "功績",
}

_GAUGE_KEYS = ("hp", "mp", "sp")
_STATIC_KEYS = ("atk_phys", "agility", "defense", "magic_power")
_COUNTER_KEYS = ("guild_merit",)
_EQUIPMENT_SLOTS = ("weapon_main", "weapon_off", "armor")
_BUFF_CACHE_KEY = "buffs"
_SEXUAL_TRAITS_KEY = "sexual_traits"
_SEXUAL_TRAITS_CATEGORY = "traits"

# Breakdown vocabulary (expose-stat-breakdown-read-model D1): the eight panel
# rows in display order and the closed layer alphabets/bounds mirrored by the
# wire validators.
_BREAKDOWN_ROW_ORDER = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_power",
    "guild_merit",
)
_LAYER_SOURCES = ("skill", "condition", "equipment")
_LAYER_KINDS = ("mult", "flat", "pct")
MAX_BREAKDOWN_ROWS = 32
MAX_LAYERS_PER_STAT = 16


@dataclass(frozen=True)
class StatLayer:
    """One named contribution to a stat, from a closed source/kind alphabet.

    ``amount`` is signed and non-zero: ``mult`` carries the multiplier factor
    itself (e.g. ``1.1``), ``flat`` the additive amount (int, or the exact
    fractional float a scaled rule-table grant produces), ``pct`` the signed
    percentage number (e.g. ``-10`` for ``-10%``).
    """

    source: str
    name: str
    kind: str
    amount: int | float


@dataclass(frozen=True)
class StatBreakdownRow:
    """One breakdown row: literal base, accounting-complete layers, effective.

    ``effective`` is composed FROM the layers' sources replaying the shipped
    authoritative operations bit-for-bit (see the breakdown section at the end
    of this module). For gauges the layers decompose the ``maximum`` and
    ``effective`` equals that maximum; gauge ``current`` is persisted resource
    state and carries no layers. On every row ``current`` mirrors the
    displayed total.
    """

    key: str
    base: int
    current: int | float
    effective: int | float
    layers: tuple[StatLayer, ...]


# Stable Traditional Chinese labels for the skill-category taxonomy, shared by
# the out-of-combat character listing. The combat panel's equivalent mapping
# lives in combat_view.py; both iterate ``SkillCategory``'s declaration order,
# so the label text is the only deliberately duplicated part (see the
# skill-category-status-listing design D-2).
_CATEGORY_LABELS = {
    SkillCategory.ELEMENTAL_MAGIC: "元素魔法",
    SkillCategory.MARTIAL_ARTS: "武技",
    SkillCategory.ENHANCEMENT: "強化",
    SkillCategory.DIVINE_MYSTERY: "神之秘法",
    SkillCategory.UTILITY: "特殊",
    SkillCategory.SEXUAL_ACT: "性愛行為",
    SkillCategory.HOLY_RITE: "神聖聖儀",
}
# Presentation-only fallback bucket for keys absent from ``SKILL_REGISTRY``.
# ``"unknown"`` is a plain string sentinel, never a ``SkillCategory`` member:
# it has no position in that enum's declaration order and is appended after
# every real category.
_UNKNOWN_CATEGORY = "unknown"
_UNKNOWN_CATEGORY_LABEL = "未知技能"


class StatusQueryError(ValueError):
    """Required canonical state is missing, malformed, or could not be read."""


@dataclass(frozen=True)
class GaugeValue:
    current: int
    maximum: int


@dataclass(frozen=True)
class _LevelRef:
    """Read-only ordinal comparison mirror for an ordered level trait."""

    value: int
    levels: tuple[str, ...]

    def _ordinal_of(self, other: Any) -> int:
        if isinstance(other, _LevelRef):
            return other.value
        if isinstance(other, str):
            return self.levels.index(other)
        return int(other)

    def __eq__(self, other: object) -> bool:
        return self.value == self._ordinal_of(other)

    def __ge__(self, other: object) -> bool:
        return self.value >= self._ordinal_of(other)

    def __gt__(self, other: object) -> bool:
        return self.value > self._ordinal_of(other)

    def __le__(self, other: object) -> bool:
        return self.value <= self._ordinal_of(other)

    def __lt__(self, other: object) -> bool:
        return self.value < self._ordinal_of(other)


@dataclass(frozen=True)
class ConditionValue:
    code: str
    label: str
    severity: str
    remaining_seconds: int | None
    modifiers: dict[str, Any]


@dataclass(frozen=True)
class StatusReadModel:
    """The complete read-only inputs a presenter may serialize."""

    actor_name: str
    actor_identity: str
    full_title: str
    location_label: str | None
    location_identity: str | None
    resources: dict[str, GaugeValue]
    conditions: tuple[ConditionValue, ...]
    disguise_active: bool
    combat_mode: str | None
    combat_round: int | None
    creation_pending: bool


@dataclass(frozen=True)
class CharacterTraitView:
    """One read-only character trait row: gauges report current/maximum."""

    key: str
    current: int
    maximum: int | None


@dataclass(frozen=True)
class CharacterEquipmentView:
    """One read-only equipped item row (slot plus canonical item key)."""

    slot: str
    item_key: str


@dataclass(frozen=True)
class CharacterSkillRow:
    """One read-only skill row: registry key plus display label."""

    key: str
    label: str


@dataclass(frozen=True)
class CharacterSkillGroupView:
    """One read-only sub-group of skill rows inside a character-panel category.

    ``group``/``label`` are both ``None`` for the single ungrouped sub-group a
    category with no second level emits; otherwise the pair carries the group
    key and its display label.
    """

    group: str | None
    label: str | None
    skills: tuple[CharacterSkillRow, ...]


@dataclass(frozen=True)
class CharacterCategoryGroupView:
    """One read-only category group of owned skill rows."""

    category: str
    label: str
    groups: tuple[CharacterSkillGroupView, ...]


@dataclass(frozen=True)
class IntimateView:
    """Read-only intimate-status values: level words plus the daily climax count."""

    arousal: str
    wetness: str
    shame: str
    exposure: str
    climax_phase: str
    climax_today: int


@dataclass(frozen=True)
class CharacterReadModel:
    """The complete read-only inputs of the version-5 ``character`` panel.

    Shares the same canonical trait storage the compact ``status`` panel reads,
    so the two panels cannot drift apart: gauges go through the same strict
    ``_require_gauge`` parser and statics/counters through the same trait dict.
    Every value is true state; ``disguise_displayed`` is reported separately
    and is never substituted for a true trait.
    """

    traits: tuple[CharacterTraitView, ...]
    active_keys: tuple[str, ...]
    passive_keys: tuple[str, ...]
    equipment: tuple[CharacterEquipmentView, ...]
    disguise_active: bool
    disguise_displayed: tuple[tuple[str, int], ...]
    guild_rank: str | None
    guild_merit: int
    wallet: int
    full_title: str
    intimate: IntimateView | None
    breakdown: tuple[StatBreakdownRow, ...]
