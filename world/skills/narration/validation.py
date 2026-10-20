"""Fail-closed authoring validation for the narration catalog.

Validation runs at import, before any action resolves. Runtime narration never
raises: every miss degrades through the documented lookup chain. Only a bad
*authoring* declaration is fatal, and it fails here with a named
:class:`~world.skills.narration.vocab.NarrationCatalogError`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from world.skills.registry import (
    SHIPPED_SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
)
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

from .families import FAMILY_ROWS, PENDING_FAMILIES
from .pools import (
    COMPACT_POOLS,
    COMPOSABLE_KINDS,
    CONTINUE_MESSAGE,
    ENGAGEMENT_OPENING_TEMPLATE,
    FALLBACK_TEMPLATES,
    INTERNAL_KINDS,
    KIND_POOLS,
    NARRATION_KINDS,
    OVERWHELM_SUMMARY_LINE,
    PARTY_RETREAT_LINES,
    TERMINAL_OUTCOME_MESSAGES,
)
from .vocab import (
    MAX_COMPACT_CODE_POINTS,
    NarrationCatalogError,
    NarrationRow,
    composed_fits,
    contains_ascii_digit,
    slot_count,
    validate_line,
)


def build_catalog(rows: Iterable[NarrationRow]) -> dict[str, NarrationRow]:
    """Return a keyed catalog, rejecting a duplicate or malformed row key."""
    catalog: dict[str, NarrationRow] = {}
    for row in rows:
        if not isinstance(row, NarrationRow):
            raise NarrationCatalogError(
                f"catalog row must be a NarrationRow, got {type(row).__name__}"
            )
        if row.key in catalog:
            raise NarrationCatalogError(
                f"duplicate narration catalog key {row.key!r}"
            )
        catalog[row.key] = row
    return catalog


def _validate_row(row: NarrationRow) -> None:
    if not row.action and not row.kind_lines:
        raise NarrationCatalogError(
            f"narration row {row.key!r} declares neither an action clause nor "
            "a kind override"
        )
    for index, line in enumerate(row.action):
        validate_line(line, owner=f"row {row.key!r} action[{index}]")
    for kind, lines in row.kind_lines.items():
        for index, line in enumerate(lines):
            validate_line(
                line,
                owner=f"row {row.key!r} kind {kind!r}[{index}]",
            )


def _validate_pools() -> None:
    if set(KIND_POOLS) | INTERNAL_KINDS != set(NARRATION_KINDS):
        missing = set(NARRATION_KINDS) - set(KIND_POOLS) - INTERNAL_KINDS
        extra = set(KIND_POOLS) - set(NARRATION_KINDS)
        raise NarrationCatalogError(
            "narration kind inventory and pools disagree: "
            f"missing={sorted(missing)!r} extra={sorted(extra)!r}"
        )
    for kind, lines in KIND_POOLS.items():
        if len(lines) < 3:
            raise NarrationCatalogError(
                f"kind {kind!r} must declare at least three variants"
            )
        for index, line in enumerate(lines):
            validate_line(line, owner=f"kind pool {kind!r}[{index}]")
    for kind in NARRATION_KINDS:
        if kind in INTERNAL_KINDS:
            if FALLBACK_TEMPLATES.get(kind) != "":
                raise NarrationCatalogError(
                    f"internal kind {kind!r} must render an empty fallback"
                )
            continue
        compact = COMPACT_POOLS.get(kind)
        if compact is None:
            raise NarrationCatalogError(
                f"kind {kind!r} has no compact fallback"
            )
        validate_line(compact, owner=f"compact {kind!r}", compact=True)
        if FALLBACK_TEMPLATES.get(kind) != compact:
            raise NarrationCatalogError(
                f"kind {kind!r} fallback template must be its compact line"
            )
        if sum(1 for _ in compact) > MAX_COMPACT_CODE_POINTS:
            raise NarrationCatalogError(
                f"compact fallback for {kind!r} is too long"
            )


def _validate_composed_pairs(rows: Iterable[NarrationRow]) -> None:
    outcomes: list[tuple[str, str]] = []
    for kind in COMPOSABLE_KINDS:
        for line in KIND_POOLS.get(kind, ()):
            outcomes.append((kind, line))
        compact = COMPACT_POOLS.get(kind)
        if compact is not None:
            outcomes.append((kind, compact))
    for row in rows:
        for kind, lines in row.kind_lines.items():
            for line in lines:
                outcomes.append((kind, line))
        for action_index, action in enumerate(row.action):
            for kind, outcome in outcomes:
                if not composed_fits(action, outcome):
                    raise NarrationCatalogError(
                        f"row {row.key!r} action[{action_index}] cannot compose "
                        f"with kind {kind!r} outcome without exceeding the "
                        "authored bound"
                    )


def _validate_structural_lines() -> None:
    validate_line(CONTINUE_MESSAGE, owner="continue message")
    for outcome, line in TERMINAL_OUTCOME_MESSAGES.items():
        validate_line(line, owner=f"terminal outcome {outcome!r}")
    validate_line(OVERWHELM_SUMMARY_LINE, owner="overwhelm summary")
    for verdict, line in PARTY_RETREAT_LINES.items():
        validate_line(line, owner=f"party retreat {verdict!r}")
    template = ENGAGEMENT_OPENING_TEMPLATE
    if contains_ascii_digit(template):
        raise NarrationCatalogError(
            "engagement opening must not carry an ASCII digit"
        )
    if template.count("{name}") != 1 or slot_count(template):
        raise NarrationCatalogError(
            "engagement opening must declare exactly one {name} placeholder"
        )
    if template.replace("{name}", "").count("{") or template.replace(
        "{name}", ""
    ).count("}"):
        raise NarrationCatalogError(
            "engagement opening declares an unsupported placeholder"
        )


def _active_family(skill: SkillDef) -> str:
    return skill.category.value


def _is_pending(skill: SkillDef) -> bool:
    return (
        skill.category is SkillCategory.SEXUAL_ACT
        or skill.category.value in PENDING_FAMILIES
    )


def validate_catalog(
    catalog: Mapping[str, NarrationRow],
    *,
    family_rows: Mapping[str, NarrationRow] = FAMILY_ROWS,
    shipped: Mapping[str, SkillDef] = SHIPPED_SKILL_REGISTRY,
    acts: Mapping[str, object] = SEXUAL_ACT_REGISTRY,
    pending: frozenset[str] = PENDING_FAMILIES,
) -> None:
    """Validate the whole authoring declaration, fail-closed.

    The shipped registries are the source of truth for *which* skills exist.
    A row for an unknown key, a duplicate key (detected by
    :func:`build_catalog`), a missing row for an active skill outside the
    pending-family set, a broken line, and an impossible composed pair each
    raise :class:`NarrationCatalogError`.
    """
    _validate_pools()
    _validate_structural_lines()

    active = {
        key: skill
        for key, skill in shipped.items()
        if skill.kind is SkillKind.ACTIVE
    }
    valid_keys = set(active) | set(acts)

    for key in catalog:
        if key not in valid_keys:
            raise NarrationCatalogError(
                f"narration catalog declares unknown key {key!r}"
            )
        _validate_row(catalog[key])
    for key, row in family_rows.items():
        if row.key != key:
            raise NarrationCatalogError(
                f"family row {key!r} carries key {row.key!r}"
            )
        _validate_row(row)

    for key, skill in active.items():
        if key in catalog:
            continue
        if skill.category is SkillCategory.SEXUAL_ACT:
            # Sexual acts are always pending in this change; their sidecars
            # carry the line, so coverage is deferred to the act change.
            continue
        if skill.category.value in pending:
            continue
        raise NarrationCatalogError(
            f"active skill {key!r} has no narration row and its family "
            f"{_active_family(skill)!r} is not declared pending"
        )

    _validate_composed_pairs((*catalog.values(), *family_rows.values()))


__all__ = ["build_catalog", "validate_catalog"]
