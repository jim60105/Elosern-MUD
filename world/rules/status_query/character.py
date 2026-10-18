"""The version-8 ``character`` panel read model plus the skill-grouping helper.

``build_character_read_model`` shares the compact ``status`` panel's canonical
trait storage and single assembly, so the expanded character surface and the
compact status surface agree on every shared value; equipment, disguise, guild,
wallet, and the condition rows are read strictly and fail closed when
malformed. The subject is the member the caller names: guild, merit, wallet and
the composed title are that member's own values, never a possession owner's,
so the panel reports the same facts with and without possession. Persona prose
and intimate state are not read here at all; ``party_member`` publishes them.
"""

from collections.abc import Sequence
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.rules.wallet import read_wallet
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillDef

from .assembly import _assemble
from .breakdown import build_stat_breakdown
from .conditions import condition_source, condition_values
from .models import (
    _CATEGORY_LABELS,
    _COUNTER_KEYS,
    _GAUGE_KEYS,
    _STATIC_KEYS,
    _UNKNOWN_CATEGORY,
    _UNKNOWN_CATEGORY_LABEL,
    CharacterCategoryGroupView,
    CharacterConditionView,
    CharacterReadModel,
    CharacterSkillGroupView,
    CharacterSkillRow,
    CharacterTraitView,
    StatusQueryError,
)
from .readers import (
    _read_full_title,
    _read_guild_merit,
    _read_disguise,
    _split_active_passive_keys,
)


def group_skill_keys(keys: Sequence[str]) -> tuple[CharacterCategoryGroupView, ...]:
    """Group plain skill keys into the character panel's category structure.

    Category order follows ``SkillCategory``'s declaration order; sub-group
    order within ``elemental_magic`` follows ``ELEMENT_REGISTRY``'s declaration
    order; within ``enhancement`` sub-groups follow fixed ``None`` -> ``"天賦"`` ->
    ``"身法"`` order; within ``holy_rite`` sub-groups follow fixed ``None`` ->
    ``"聖禮"`` order; and ``sexual_act`` follows first-seen ``group`` order among the given
    keys. Every other category emits exactly one ``group=None`` sub-group, and
    each row's ``label`` is the registry label. Categories and sub-groups with
    zero matching keys are omitted. Keys absent from ``SKILL_REGISTRY`` land in
    one synthetic ``unknown`` category appended after every real category, with
    each row's ``label`` equal to its own key — never raising, mirroring the
    presenter's existing unknown-key degradation.
    """
    buckets: dict[str, dict[str | None, list[SkillDef]]] = {}
    unregistered: list[str] = []
    for key in keys:
        skill = SKILL_REGISTRY.get(key)
        if skill is None:
            unregistered.append(key)
            continue
        buckets.setdefault(skill.category.value, {}).setdefault(skill.group, []).append(skill)

    views: list[CharacterCategoryGroupView] = []
    for category in SkillCategory:
        category_buckets = buckets.get(category.value)
        if not category_buckets:
            continue
        if category is SkillCategory.ELEMENTAL_MAGIC:
            ordered_groups = [group for group in ELEMENT_REGISTRY if group in category_buckets]
        elif category is SkillCategory.ENHANCEMENT:
            ordered_groups = [group for group in (None, "天賦", "身法") if group in category_buckets]
        elif category is SkillCategory.SEXUAL_ACT:
            ordered_groups = list(category_buckets)
        elif category is SkillCategory.HOLY_RITE:
            ordered_groups = [group for group in (None, "聖禮") if group in category_buckets]
        else:
            ordered_groups = [None]
        views.append(
            CharacterCategoryGroupView(
                category=category.value,
                label=_CATEGORY_LABELS[category],
                groups=tuple(
                    CharacterSkillGroupView(
                        group=group_key,
                        label=_group_label(category, group_key),
                        skills=tuple(
                            CharacterSkillRow(key=skill.key, label=skill.label)
                            for skill in category_buckets[group_key]
                        ),
                    )
                    for group_key in ordered_groups
                ),
            )
        )
    if unregistered:
        views.append(
            CharacterCategoryGroupView(
                category=_UNKNOWN_CATEGORY,
                label=_UNKNOWN_CATEGORY_LABEL,
                groups=(
                    CharacterSkillGroupView(
                        group=None,
                        label=None,
                        skills=tuple(
                            CharacterSkillRow(key=key, label=key) for key in unregistered
                        ),
                    ),
                ),
            )
        )
    return tuple(views)


def _group_label(category: SkillCategory, group: str | None) -> str | None:
    """Return the display label for one sub-group key, if any."""
    if group is None:
        return None
    if category is SkillCategory.ELEMENTAL_MAGIC:
        element = ELEMENT_REGISTRY.get(group)
        if element is not None:
            return element.display_name_zh
    return group


def build_character_read_model(entity: Any) -> CharacterReadModel:
    """Build the frozen character read model or raise :class:`StatusQueryError`.

    Reads the same canonical trait dict the status model reads, so the expanded
    character surface and the compact status surface agree on every shared
    value. Equipment, disguise, guild, wallet, and the condition rows are read
    strictly and fail closed when malformed; no handler is materialized and
    nothing is written. Every value belongs to ``entity`` itself: the model
    never substitutes a possession owner's guild, merit, wallet or title.
    """
    assembly = _assemble(entity)
    traits: list[CharacterTraitView] = []
    for key in _GAUGE_KEYS:
        gauge = assembly.gauges[key]
        traits.append(CharacterTraitView(key, gauge.current, gauge.maximum))
    for key in _STATIC_KEYS + _COUNTER_KEYS:
        traits.append(CharacterTraitView(key, assembly.trait_values[key], None))

    disguise_active, disguise_displayed = _read_disguise(entity)
    active_keys, passive_keys = _split_active_passive_keys(entity)
    conditions = tuple(
        CharacterConditionView(
            code=row.code,
            label=row.label,
            severity=row.severity,
            remaining_seconds=row.remaining_seconds,
            modifiers=tuple(row.modifiers.items()),
            source=condition_source(row.provenance),
        )
        for row in condition_values(assembly)
    )

    return CharacterReadModel(
        traits=tuple(traits),
        active_keys=active_keys,
        passive_keys=passive_keys,
        equipment=assembly.equipment,
        disguise_active=disguise_active,
        disguise_displayed=disguise_displayed,
        guild_rank=getattr(entity, "guild_rank", None),
        guild_merit=_read_guild_merit(assembly.traits_data),
        wallet=read_wallet(entity, StatusQueryError),
        full_title=_read_full_title(entity),
        conditions=conditions,
        breakdown=build_stat_breakdown(entity, assembly),
    )
