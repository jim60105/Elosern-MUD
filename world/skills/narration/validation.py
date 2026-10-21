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
    SPECIAL_POOLS,
    SEXUAL_COUNTER_LINES,
    TERMINAL_OUTCOME_MESSAGES,
    TRANSITION_LINES,
)
from .vocab import (
    MAX_COMPACT_CODE_POINTS,
    NarrationCatalogError,
    NarrationRow,
    RoleClause,
    composed_fits,
    contains_ascii_digit,
    slot_count,
    validate_line,
)

#: The effect prefixes through which an act's ``SkillDef`` names one sexual
#: transition event. Every one of them stages the same ``sexual_transition``
#: entry, so the narration pool is keyed by the bare event name.
_EVENT_EFFECT_PREFIXES = (
    "sexual_event:",
    "sexual_event_actor:",
    "sexual_event_target:",
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
    if (
        not row.action
        and not row.kind_lines
        and not row.performer_lines
        and not row.participant_lines
    ):
        raise NarrationCatalogError(
            f"narration row {row.key!r} declares neither an action clause nor "
            "an outcome override"
        )
    for index, line in enumerate(row.action):
        validate_line(line, owner=f"row {row.key!r} action[{index}]")
    for field in ("kind_lines", "performer_lines", "participant_lines"):
        for kind, lines in getattr(row, field).items():
            if kind not in NARRATION_KINDS:
                raise NarrationCatalogError(
                    f"row {row.key!r} {field} names unknown kind {kind!r}"
                )
            for index, line in enumerate(lines):
                validate_line(
                    line,
                    owner=f"row {row.key!r} {field} {kind!r}[{index}]",
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
    for pool_name, lines in SPECIAL_POOLS.items():
        if not lines:
            raise NarrationCatalogError(
                f"special pool {pool_name!r} must declare at least one line"
            )
        for index, line in enumerate(lines):
            validate_line(line, owner=f"special pool {pool_name!r}[{index}]")


def _validate_composed_pairs(rows: Iterable[NarrationRow]) -> None:
    outcomes: list[tuple[str, str]] = []
    for kind in COMPOSABLE_KINDS:
        for line in KIND_POOLS.get(kind, ()):
            outcomes.append((kind, line))
        compact = COMPACT_POOLS.get(kind)
        if compact is not None:
            outcomes.append((kind, compact))
    for pool_name, lines in SPECIAL_POOLS.items():
        for line in lines:
            outcomes.append((pool_name, line))
    for row in rows:
        for kind, lines in row.kind_lines.items():
            for line in lines:
                outcomes.append((kind, line))
        for field in ("performer_lines", "participant_lines"):
            for kind, lines in getattr(row, field).items():
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
        if skill.category.value in pending:
            continue
        raise NarrationCatalogError(
            f"active skill {key!r} has no narration row and its family "
            f"{skill.category.value!r} is not declared pending"
        )
    for key in acts:
        if key in catalog:
            continue
        raise NarrationCatalogError(
            f"sexual act {key!r} has no narration row"
        )

    _validate_composed_pairs((*catalog.values(), *family_rows.values()))


def declared_sexual_events(
    acts: Mapping[str, object],
    skills: Mapping[str, SkillDef] | None = None,
) -> frozenset[str]:
    """Return every transition event name the given acts can emit.

    Reads the act's own declared ``sexual_events`` and ``pair_events`` names
    plus the event effects its skill row stages, so a target-scoped or
    actor-scoped event (``divine_sexual_arts``'s ``stimulus_applied``) counts
    exactly like the tuple-declared ones. ``skills`` is the registry holding
    the act rows; it is omitted only by callers that have the sidecars alone.
    """
    names: set[str] = set()
    for key, act in acts.items():
        skill = skills.get(key) if skills is not None else None
        if skill is not None:
            for effect in skill.effects:
                for prefix in _EVENT_EFFECT_PREFIXES:
                    if effect.startswith(prefix):
                        names.add(effect[len(prefix):])
                        break
        names.update(getattr(act, "sexual_events", ()))
        names.update(event for _pair, event in getattr(act, "pair_events", ()))
    return frozenset(names)


def declared_sexual_counters(acts: Mapping[str, object]) -> frozenset[str]:
    """Return every lifetime counter name the given acts credit."""
    return frozenset(
        name
        for act in acts.values()
        for name in (
            *getattr(act, "actor_counters", ()),
            *getattr(act, "participant_counters", ()),
        )
    )


def validate_sexual_pools(
    acts: Mapping[str, object],
    skills: Mapping[str, SkillDef] | None = None,
    *,
    transitions: Mapping[str, tuple[str, ...]] = TRANSITION_LINES,
    counters: Mapping[str, RoleClause] = SEXUAL_COUNTER_LINES,
) -> None:
    """Validate the transition and counter pools against the acts in scope.

    Both key sets must equal the catalogue-derived sets exactly, and every
    counter entry must carry both role clauses. A new act that names an
    unknown event or counter therefore fails at import instead of narrating
    through a generic line.
    """
    events = declared_sexual_events(acts, skills)
    for name in sorted(events - set(transitions)):
        raise NarrationCatalogError(
            f"sexual transition event {name!r} has no narration clause"
        )
    for name in sorted(set(transitions) - events):
        raise NarrationCatalogError(
            f"sexual transition pool declares unemitted event {name!r}"
        )
    declared_counters = declared_sexual_counters(acts)
    for name in sorted(declared_counters - set(counters)):
        raise NarrationCatalogError(
            f"sexual counter {name!r} has no narration clause"
        )
    for name in sorted(set(counters) - declared_counters):
        raise NarrationCatalogError(
            f"sexual counter pool declares unknown counter {name!r}"
        )
    for name, clause in counters.items():
        if not isinstance(clause, RoleClause):
            raise NarrationCatalogError(
                f"sexual counter {name!r} must declare a role clause pair"
            )


__all__ = [
    "build_catalog",
    "declared_sexual_counters",
    "declared_sexual_events",
    "validate_catalog",
    "validate_sexual_pools",
]
