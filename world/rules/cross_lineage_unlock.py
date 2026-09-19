"""Cross-lineage unlock rulebook: declarative ownership grants.

One declarative table grants skill OWNERSHIP when an entity's practice
proficiency across *other* lineage trees reaches declared depths. Ownership
and usability stay separate (``skill-lineage``): prerequisites still gate use,
``cap(S)`` still derives from consuming edges, and practice still accrues
exactly as before. This module only ever adds keys to the stored owned set —
never proficiency, never a removal. The same table shape that grants a single
passive can open an entire new lineage tree by granting its root nodes.

Evaluation is push-based by contract: the only trigger is a practice award
(see ``world/rules/progression.grant_skill_practice_xp`` and
``grant_study_practice_xp``), because practice XP is the only quantity a
clause reads. No read path evaluates or writes. Loading is fail-closed: a rule
that can never fire is a data defect and raises ``ValueError`` naming the rule
rather than shipping a silently dead row.

Import layering: this module imports ``world.rules.progression`` at module
top, while progression imports this module lazily inside its award helpers —
so importing progression never imports this module, and importing this module
never observes a half-initialized progression.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from world.rules.progression import proficiency_cap, skill_proficiency_level
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillDef, SkillKind


@dataclass(frozen=True)
class UnlockClause:
    """One AND-ed condition clause of a cross-lineage unlock rule.

    ``groups`` holds the clause's resolved registry key groups in
    deterministic order; a group qualifies when at least one member's derived
    proficiency level reaches ``min_level``, and the clause is satisfied when
    at least ``distinct_groups`` groups qualify.
    """

    min_level: int
    distinct_groups: int
    groups: tuple[tuple[str, ...], ...]
    scope_desc: str


@dataclass(frozen=True)
class CrossLineageUnlockRule:
    """One rule: every clause AND-ed, then every grant key appended."""

    id: str
    requires: tuple[UnlockClause, ...]
    grants: tuple[str, ...]


@dataclass(frozen=True)
class UnlockRulebook:
    """A validated rule set plus its load-time caches.

    ``registry`` is the exact mapping the rules were validated against, so
    runtime grant writes resolve the same rows the loader saw. ``by_id`` maps
    rule id to rule and ``reverse_index`` maps each scoped skill key to the
    ordered rule ids whose clauses sample it (design D4: an award evaluates
    only the rules its skill key could have changed).
    """

    rules: tuple[CrossLineageUnlockRule, ...]
    by_id: Mapping[str, CrossLineageUnlockRule]
    reverse_index: Mapping[str, tuple[str, ...]]
    registry: Mapping[str, SkillDef]


def _clause_scope_desc(scope_raw: Mapping[str, Any], category: SkillCategory | None, group: str | None) -> str:
    """One stable human-readable description of a scope for error messages."""
    if category is None:
        return f"keys({len(scope_raw['keys'])})"
    if group is None:
        return f"category {category.value}"
    return f"category {category.value} group {group}"


def _resolve_scope_groups(
    rule_id: str,
    scope_raw: Mapping[str, Any],
    registry: Mapping[str, SkillDef],
) -> tuple[tuple[tuple[str, ...], ...], str]:
    """Resolve one clause scope into concrete key groups.

    Declarative ``{category, group?}`` scopes sample ACTIVE nodes only and
    partition them by their ``group`` field; an explicit ``{keys: [...]}``
    scope forms exactly one group. Every fail-closed scope defect raises
    ``ValueError`` naming the rule id.
    """
    has_category = "category" in scope_raw
    has_keys = "keys" in scope_raw
    if has_category == has_keys:
        raise ValueError(
            f"rule {rule_id!r}: scope must declare exactly one of "
            f"'category' or 'keys', got {dict(scope_raw)!r}"
        )
    if has_keys:
        keys_raw = scope_raw["keys"]
        if isinstance(keys_raw, (str, bytes)) or not isinstance(keys_raw, Sequence):
            raise ValueError(
                f"rule {rule_id!r}: explicit scope 'keys' must be a list, "
                f"got {keys_raw!r}"
            )
        keys = tuple(keys_raw)
        if not keys:
            raise ValueError(
                f"rule {rule_id!r}: scope selects no nodes (empty keys list)"
            )
        resolved: list[tuple[str, ...]] = [[]]
        for key in keys:
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    f"rule {rule_id!r}: scope key must be a non-empty string, "
                    f"got {key!r}"
                )
            definition = registry.get(key)
            if definition is None:
                raise ValueError(
                    f"rule {rule_id!r}: scope names unknown skill {key!r}"
                )
            if definition.kind is not SkillKind.ACTIVE:
                raise ValueError(
                    f"rule {rule_id!r}: scope names {key!r}, a non-ACTIVE "
                    "node; only ACTIVE nodes can hold practice proficiency"
                )
            resolved[0].append(key)
        return (tuple(resolved[0]),), _clause_scope_desc(scope_raw, None, None)

    category_raw = scope_raw["category"]
    if not isinstance(category_raw, str) or not category_raw.strip():
        raise ValueError(
            f"rule {rule_id!r}: scope category must be a non-empty string, "
            f"got {category_raw!r}"
        )
    try:
        category = SkillCategory(category_raw)
    except ValueError:
        raise ValueError(
            f"rule {rule_id!r}: scope names unknown category {category_raw!r}"
        ) from None
    group = scope_raw.get("group")
    if group is not None and (not isinstance(group, str) or not group):
        raise ValueError(
            f"rule {rule_id!r}: scope group must be a non-empty string when "
            f"present, got {group!r}"
        )
    rows = [
        definition
        for definition in registry.values()
        if definition.category is category
        and definition.kind is SkillKind.ACTIVE
        and (group is None or definition.group == group)
    ]
    if not rows:
        raise ValueError(
            f"rule {rule_id!r}: scope selects no ACTIVE nodes"
        )
    if group is not None:
        groups = (tuple(sorted(row.key for row in rows)),)
    else:
        by_group: dict[str | None, list[str]] = {}
        for row in rows:
            by_group.setdefault(row.group, []).append(row.key)
        ordered = sorted(
            by_group.items(), key=lambda item: (item[0] is None, item[0] or "")
        )
        groups = tuple(tuple(sorted(keys)) for _, keys in ordered)
    return groups, _clause_scope_desc(scope_raw, category, group)


def _parse_clause(
    rule_id: str,
    clause_raw: Any,
    registry: Mapping[str, SkillDef],
    cap: Callable[[str], int],
) -> UnlockClause:
    """Parse and fail-closed-validate one clause (spec requirements 2-3)."""
    if not isinstance(clause_raw, Mapping):
        raise ValueError(
            f"rule {rule_id!r}: requires entries must be mappings, got "
            f"{type(clause_raw).__name__}"
        )
    min_level = clause_raw.get("min_level")
    if isinstance(min_level, bool) or not isinstance(min_level, int) or min_level < 1:
        raise ValueError(
            f"rule {rule_id!r}: min_level must be an integer >= 1, got "
            f"{min_level!r}"
        )
    distinct_groups = clause_raw.get("distinct_groups", 1)
    if (
        isinstance(distinct_groups, bool)
        or not isinstance(distinct_groups, int)
        or distinct_groups < 1
    ):
        raise ValueError(
            f"rule {rule_id!r}: distinct_groups must be an integer >= 1, got "
            f"{distinct_groups!r}"
        )
    scope_raw = clause_raw.get("scope")
    if not isinstance(scope_raw, Mapping):
        raise ValueError(
            f"rule {rule_id!r}: clause must declare a scope mapping, got "
            f"{scope_raw!r}"
        )
    groups, scope_desc = _resolve_scope_groups(rule_id, scope_raw, registry)
    # Reachability: at least distinct_groups groups must hold a node whose
    # derived proficiency cap clears min_level, or the rule can never fire.
    reachable = sum(
        1 for group in groups if any(cap(key) >= min_level for key in group)
    )
    if reachable < distinct_groups:
        raise ValueError(
            f"rule {rule_id!r}: unreachable threshold — {reachable} of "
            f"{len(groups)} groups can reach min_level {min_level}, below "
            f"distinct_groups {distinct_groups} ({scope_desc})"
        )
    return UnlockClause(
        min_level=min_level,
        distinct_groups=distinct_groups,
        groups=groups,
        scope_desc=scope_desc,
    )


def load_rules(
    raw_rules: Any,
    *,
    registry: Mapping[str, SkillDef] = SKILL_REGISTRY,
    cap: Callable[[str], int] = proficiency_cap,
) -> UnlockRulebook:
    """Build and validate an :class:`UnlockRulebook` from raw YAML-shaped data.

    Every spec fail-closed condition (duplicate ``id``, unknown key, empty
    scope, unreachable threshold, PASSIVE key in an explicit scope, non-positive
    ``min_level``/``distinct_groups``, empty ``grants``/``requires``) and the
    structural no-cycle check raise ``ValueError`` naming the offending rule
    id(s). ``registry`` and ``cap`` are injectable so behavior tests can load
    synthetic tables against synthetic rows without touching the live catalogs.
    """
    if raw_rules is None:
        raw_rules = []
    if isinstance(raw_rules, (str, bytes)) or not isinstance(raw_rules, Sequence):
        raise ValueError(
            "cross-lineage unlock table must be a list of rules, got "
            f"{type(raw_rules).__name__}"
        )
    parsed: list[CrossLineageUnlockRule] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_rules):
        if not isinstance(raw, Mapping):
            raise ValueError(
                f"cross-lineage unlock rule #{index} must be a mapping, got "
                f"{type(raw).__name__}"
            )
        rule_id = raw.get("id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise ValueError(
                f"cross-lineage unlock rule #{index} must declare a "
                f"non-empty string id, got {rule_id!r}"
            )
        if rule_id in seen_ids:
            raise ValueError(
                f"cross-lineage unlock rule id {rule_id!r} is duplicated"
            )
        seen_ids.add(rule_id)

        grants_raw = raw.get("grants")
        if isinstance(grants_raw, (str, bytes)) or not isinstance(grants_raw, Sequence):
            raise ValueError(
                f"rule {rule_id!r}: grants must be a non-empty list of "
                f"registry keys, got {grants_raw!r}"
            )
        if not grants_raw:
            raise ValueError(f"rule {rule_id!r}: grants must be non-empty")
        grants: list[str] = []
        for grant_key in grants_raw:
            if not isinstance(grant_key, str) or not grant_key.strip():
                raise ValueError(
                    f"rule {rule_id!r}: grant must be a non-empty string, "
                    f"got {grant_key!r}"
                )
            if grant_key not in registry:
                raise ValueError(
                    f"rule {rule_id!r}: grant names unknown skill "
                    f"{grant_key!r}"
                )
            grants.append(grant_key)

        requires_raw = raw.get("requires")
        if isinstance(requires_raw, (str, bytes)) or not isinstance(requires_raw, Sequence):
            raise ValueError(
                f"rule {rule_id!r}: requires must be a non-empty list of "
                f"clauses, got {requires_raw!r}"
            )
        if not requires_raw:
            raise ValueError(f"rule {rule_id!r}: requires must be non-empty")
        clauses = tuple(
            _parse_clause(rule_id, clause_raw, registry, cap)
            for clause_raw in requires_raw
        )
        parsed.append(
            CrossLineageUnlockRule(id=rule_id, requires=clauses, grants=tuple(grants))
        )

    _check_no_grant_is_a_condition_source(parsed)
    return _bundle(parsed, registry)


def _check_no_grant_is_a_condition_source(
    rules: Sequence[CrossLineageUnlockRule],
) -> None:
    """D6: no granted key may ever be sampled by any clause scope.

    The grant graph is therefore depth 1 by construction — a set intersection
    at load is total, no traversal needed. Raises ``ValueError`` naming both
    rule ids (the granting rule and the sampling rule; the same id twice for a
    self-referential rule).
    """
    granters: dict[str, str] = {}
    for rule in rules:
        for key in rule.grants:
            granters.setdefault(key, rule.id)
    samplers: dict[str, str] = {}
    for rule in rules:
        for clause in rule.requires:
            for group in clause.groups:
                for key in group:
                    samplers.setdefault(key, rule.id)
    for key in sorted(set(granters) & set(samplers)):
        raise ValueError(
            f"cross-lineage unlock cycle: rule {granters[key]!r} grants "
            f"{key!r}, which rule {samplers[key]!r} samples as a condition "
            "source"
        )


def _bundle(
    rules: Sequence[CrossLineageUnlockRule],
    registry: Mapping[str, SkillDef],
) -> UnlockRulebook:
    """Build the rulebook caches (by-id map and the reverse index, design D4)."""
    by_id = {rule.id: rule for rule in rules}
    reverse_index: dict[str, list[str]] = {}
    for rule in rules:
        sampled = {
            key
            for clause in rule.requires
            for group in clause.groups
            for key in group
        }
        for key in sorted(sampled):
            reverse_index.setdefault(key, []).append(rule.id)
    return UnlockRulebook(
        rules=tuple(rules),
        by_id=MappingProxyType(by_id),
        reverse_index=MappingProxyType(
            {key: tuple(rule_ids) for key, rule_ids in reverse_index.items()}
        ),
        registry=registry,
    )


def load_rulebook(path: Path) -> UnlockRulebook:
    """Load and fail-closed validate one YAML rulebook file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return load_rules(raw)


def clause_satisfied(entity: Any, clause: UnlockClause) -> bool:
    """Return whether ``clause`` is satisfied for ``entity``.

    A group qualifies when at least one sampled node's derived proficiency
    level reaches ``min_level``; the clause is satisfied when the qualifying
    group count reaches ``distinct_groups``.
    """
    qualifying = 0
    for group in clause.groups:
        if any(
            skill_proficiency_level(entity, key) >= clause.min_level
            for key in group
        ):
            qualifying += 1
            if qualifying >= clause.distinct_groups:
                return True
    return False


def grant_owned_skill(
    entity: Any, skill_key: str, registry: Mapping[str, SkillDef]
) -> bool:
    """Append one missing grant to the entity's stored owned set (design D5).

    The key lands under the ``db.skills`` list matching its ``SkillDef.kind``
    (``active`` or ``passive``) so the stored shape stays honest for the
    character panel and the import round-trip. Append-if-absent makes the
    write idempotent: an already-owned key — from an earlier rule, a preset,
    or an import — is left untouched. Proficiency is never written.
    """
    definition = registry.get(skill_key)
    if definition is None:
        raise ValueError(f"cannot grant unknown skill {skill_key!r}")
    list_name = "active" if definition.kind is SkillKind.ACTIVE else "passive"
    stored = dict(entity.db.skills or {})
    owned = list(stored.get(list_name, []))
    if skill_key in owned:
        return False
    owned.append(skill_key)
    stored[list_name] = owned
    entity.db.skills = stored
    return True


def evaluate_cross_lineage_unlocks(
    entity: Any,
    skill_key: str,
    rulebook: UnlockRulebook | None = None,
) -> list[str]:
    """Evaluate the rules a just-practised ``skill_key`` could have changed.

    Walks only the reverse-indexed rules for ``skill_key`` (design D4), skips
    any rule whose grants the entity already fully owns, and returns the list
    of newly granted keys in the order their rules declared them. Grants are
    applied immediately; the caller owns any announcement.
    """
    rulebook = RULEBOOK if rulebook is None else rulebook
    newly: list[str] = []
    for rule_id in rulebook.reverse_index.get(skill_key, ()):
        rule = rulebook.by_id[rule_id]
        if all(key in entity.skills.owned_keys() for key in rule.grants):
            continue
        if not all(clause_satisfied(entity, clause) for clause in rule.requires):
            continue
        for grant_key in rule.grants:
            if grant_owned_skill(entity, grant_key, rulebook.registry):
                newly.append(grant_key)
    return newly


def unlock_line_for_grant(
    skill_key: str, registry: Mapping[str, SkillDef]
) -> str:
    """The one player-facing announcement line for one granted skill.

    Reuses the shipped ``unlock_line`` wording verbatim (design non-goals), so
    a cross-lineage grant announces exactly like a newly usable skill.
    """
    from world.rules.progression import unlock_line

    return unlock_line(registry[skill_key])


# The shipped rulebook, validated against the live registry at import. Tests
# that need synthetic tables load them through :func:`load_rules` and patch
# this binding; the module must be imported outside any synthetic catalog
# scope so this load always sees the shipped registry.
RULEBOOK: UnlockRulebook = load_rulebook(
    Path(__file__).parent / "rulebook" / "cross_lineage_unlock.yaml"
)