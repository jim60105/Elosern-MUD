"""Pure skill-lineage read model (skill-lineage-panel v2, design §5).

One source, zero writes: every view here derives from ``SKILL_REGISTRY``
prerequisite edges (plus the load-time reverse-edge cache), the entity's
``db.skill_proficiency``, and the shared ``can_use_skill`` predicate. No
function in this module creates, mutates, or persists any entity or world
state; consumers (the WebClient panel presenter, the ``lineage`` command) are
serialization only.

A lineage graph (系譜圖) is one connected component of the identity-eligible
prerequisite graph: a merge node appears once, in the single graph that owns
both of its parents, and every prerequisite edge is carried explicitly with
its minimum level. A component qualifies when it contains at least one edge,
or when its single skill is owned — an unowned isolated skill is not a graph,
and emitting one for every such registry row would bury the real trees.
Nodes are emitted in topological order with their longest prerequisite depth,
so a branch-or-merge content drop upgrades every renderer without a contract
change (design §9.1).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any

from world.rules.combat_view import CATEGORY_LABELS
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
    missing_prerequisite,
    proficiency_cap,
)
from world.skills.registry import (
    SKILL_REGISTRY,
    declared_prerequisites,
    prerequisite_consumers,
)
from world.skills.eligibility import skill_identity_eligible

# Wire bound for every rendered lineage text (design DD1): mirrors the panel
# contract's MAX_TEXT_CODE_POINTS in web/webclient/presentation/lineage.py.
# A registry label is legal up to LABEL_MAX (128), so the rendered
# 「需「label Lv.N」」 wrapper CAN overshoot the bound. The read model clamps
# deterministically — the wrapper keeps its fixed parts, the label is
# truncated and marked with a single ellipsis — so a legal maximum-length
# label can never fail the panel closed for every player. The panel mirror
# pins this constant's value against its own cap.
LINEAGE_TEXT_WIRE_MAX = 128

#: The read model's bound on each side of a lineage position (the selected
#: skill's prerequisites and its immediate consumers). The wire validator in
#: ``web/webclient/presentation/character.py`` pins the same value.
MAX_LINEAGE_POSITION_ROWS = 8


def _fit_wire_text(label: str, threshold: int) -> str:
    """Render 「需「label Lv.N」」 clamped to ``LINEAGE_TEXT_WIRE_MAX``.

    Over-long labels lose their tail to a one-character ellipsis; the 需「
    prefix and the Lv.N」 suffix always survive, so the gate reads as a gate
    at every label length. Pure and total: even a legal threshold whose digit
    count alone overshoots the budget loses its digit tail instead of
    breaking the bound.
    """
    text = f"需「{label} Lv.{threshold}」"
    if len(text) <= LINEAGE_TEXT_WIRE_MAX:
        return text
    suffix = f" Lv.{threshold}」"
    keep = LINEAGE_TEXT_WIRE_MAX - len("需「") - len(suffix) - 1
    if keep >= 0:
        return f"需「{label[:keep]}…{suffix}"
    # Pathological legal input: a threshold whose digit count alone exceeds
    # the budget (>= 121 digits — unmeetable by rule, since proficiency tips
    # at 10, so this branch is a totality guarantee, never content
    # behaviour). Ellipsize both parts; the bound still holds.
    head = LINEAGE_TEXT_WIRE_MAX - len("需「") - len("」") - 2
    return f"需「…{str(threshold)[:head]}…」"


class LineageQueryError(Exception):
    """Stored proficiency data is structurally invalid; the view fails closed.

    Raised BEFORE any partial view is returned so presenters surface the
    common unavailable form instead of fabricating node values.
    """


@dataclass(frozen=True)
class LineageNodeView:
    """One registry node with the entity's live proficiency state."""

    skill_key: str
    display_name_zh: str
    owned: bool
    usable: bool
    ready: bool
    level: int
    xp_into_level: float
    xp_to_next_level: float
    capped: bool
    prereq_text_zh: str
    depth: int


@dataclass(frozen=True)
class LineageEdgeView:
    """One prerequisite edge of a graph: parent key, child key, minimum level."""

    from_key: str
    to_key: str
    min_level: int


@dataclass(frozen=True)
class LineageGraphView:
    """One connected component: its roots, unique nodes, edges and counts."""

    graph_id: str
    group_label_zh: str
    root_keys: tuple[str, ...]
    nodes: tuple[LineageNodeView, ...]
    edges: tuple[LineageEdgeView, ...]
    owned_count: int
    total_count: int
    consumed: bool


@dataclass(frozen=True)
class LineageView:
    """The whole lineage ledger; counts describe the FULL untruncated view."""

    graphs: tuple[LineageGraphView, ...]
    completed_count: int
    total_count: int


@dataclass(frozen=True)
class ProficiencyProgress:
    """One skill's derived proficiency state (the panel's compact growth facts).

    ``xp_into_level`` and ``xp_to_next_level`` are the same band values the
    lineage node reports, so the proficiency meter and the 系譜 tab can never
    disagree. A capped skill reports ``xp_to_next_level`` zero.
    """

    level: int
    xp_into_level: float
    xp_to_next_level: float
    capped: bool


@dataclass(frozen=True)
class LineagePositionEdge:
    """One lineage edge at the selected skill's position: key, label, level."""

    skill_key: str
    display_name_zh: str
    level: int


@dataclass(frozen=True)
class LineagePositionView:
    """The selected skill's declared prerequisites and its next unlocks.

    Each side is bounded to :data:`MAX_LINEAGE_POSITION_ROWS`; ``next`` keeps
    only consumers the entity's stored identity may ever own.
    """

    prerequisites: tuple[LineagePositionEdge, ...]
    next: tuple[LineagePositionEdge, ...]


def _proficiency_map(entity: Any) -> dict[str, float]:
    """Return the validated stored proficiency map, failing closed on junk.

    A missing/empty record is the all-zero baseline. Any non-mapping record,
    or a stored value for a registry skill that is not a finite non-negative
    number (booleans included), raises :class:`LineageQueryError` before any
    view is built. Keys absent from the registry are unrenderable here and
    ignored, exactly as the proficiency readers ignore them. Evennia persists
    the record as a save-backed mapping (``_SaverDict``), so the structural
    check is over ``Mapping``, not the concrete ``dict``.
    """
    raw = entity.db.skill_proficiency
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise LineageQueryError("db.skill_proficiency is not a mapping")
    validated: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or key not in SKILL_REGISTRY:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LineageQueryError(f"proficiency entry {key!r} is not a number")
        number = float(value)
        if not isfinite(number) or number < 0:
            raise LineageQueryError(f"proficiency entry {key!r} is not valid")
        validated[key] = number
    return validated


def _progress_from_stored(stored: float, skill_key: str) -> ProficiencyProgress:
    """Derive one skill's proficiency progress from its stored XP.

    The single computation both the lineage node and the character panel's
    growth facts read, so the proficiency meter and the 系譜 tab agree. The
    level is whole levels of ``SKILL_PROFICIENCY_XP_PER_LEVEL``; ``capped`` is
    the derived tip cap being reached.
    """
    level = int(stored // SKILL_PROFICIENCY_XP_PER_LEVEL)
    capped = level >= proficiency_cap(skill_key)
    xp_into_level = stored - level * SKILL_PROFICIENCY_XP_PER_LEVEL
    return ProficiencyProgress(
        level=level,
        xp_into_level=xp_into_level,
        xp_to_next_level=(
            0.0 if capped else SKILL_PROFICIENCY_XP_PER_LEVEL - xp_into_level
        ),
        capped=capped,
    )


def proficiency_progress_for_keys(
    entity: Any, keys: Sequence[str]
) -> dict[str, ProficiencyProgress]:
    """Return the progress of each requested registry key in one read.

    The stored proficiency record is validated once (the same fail-closed read
    every lineage view uses) and each requested key is derived from it. Keys
    absent from the registry are not returned: no proficiency band exists for a
    row the registry cannot resolve. Never writes entity state.
    """
    xp = _proficiency_map(entity)
    return {
        key: _progress_from_stored(xp.get(key, 0.0), key)
        for key in keys
        if key in SKILL_REGISTRY
    }


def _components(eligible: set[str]) -> tuple[tuple[str, ...], ...]:
    """Connected components of the eligible prerequisite graph, in registry order.

    Union-find over identity-eligible skills, joining each skill to every
    declared prerequisite that is itself eligible. Components are emitted in
    the registry order of their first member, and members keep registry order,
    so the sequence is deterministic without any set iteration.
    """
    parent = {key: key for key in eligible}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for key in SKILL_REGISTRY:
        if key not in eligible:
            continue
        for prereq in SKILL_REGISTRY[key].prerequisites:
            if prereq.skill_key not in eligible:
                continue
            root, other = find(key), find(prereq.skill_key)
            if root != other:
                parent[other] = root

    grouped: dict[str, list[str]] = {}
    for key in SKILL_REGISTRY:
        if key in eligible:
            grouped.setdefault(find(key), []).append(key)
    return tuple(tuple(members) for members in grouped.values())


def _topological_order(component: set[str]) -> tuple[str, ...]:
    """Kahn topological sort of one component, registry order as tie-break.

    Prerequisite edges always point backwards in the emitted order, so a merge
    node follows both of its parents. The canonical graph is acyclic
    (load-time validation), so the sort always drains; anything left would be
    a bug, not content.
    """
    indegree = {
        key: sum(
            1
            for pre in SKILL_REGISTRY[key].prerequisites
            if pre.skill_key in component
        )
        for key in component
    }
    registry_order = {key: index for index, key in enumerate(SKILL_REGISTRY)}
    queue = sorted(
        (key for key, degree in indegree.items() if degree == 0),
        key=registry_order.get,
    )
    ordered: list[str] = []
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for consumer_key, _ in prerequisite_consumers(current):
            if consumer_key not in component:
                continue
            indegree[consumer_key] -= 1
            if indegree[consumer_key] == 0:
                queue.append(consumer_key)
                queue.sort(key=registry_order.get)
    if len(ordered) != len(component):
        raise LineageQueryError(
            "lineage graph hit a cycle the registry validator should have rejected"
        )
    return tuple(ordered)


def _group_label(root_keys: Sequence[str]) -> str:
    """The graph's 元素／風格 label: shared root label, else joined labels."""
    labels: list[str] = []
    for root_key in root_keys:
        skill = SKILL_REGISTRY[root_key]
        label = (
            skill.element.display_name_zh
            if skill.element is not None
            else CATEGORY_LABELS[skill.category]
        )
        if label not in labels:
            labels.append(label)
    text = "‧".join(labels)
    if len(text) <= LINEAGE_TEXT_WIRE_MAX:
        return text
    return f"{text[: LINEAGE_TEXT_WIRE_MAX - 1]}…"


def _node_view(
    entity: Any,
    skill_key: str,
    owned: set,
    xp: dict[str, float],
    depth: int,
) -> LineageNodeView:
    """One node with its live state, unlock gate, readiness and graph depth."""
    skill = SKILL_REGISTRY[skill_key]
    progress = _progress_from_stored(xp.get(skill_key, 0.0), skill_key)
    prereq = missing_prerequisite(entity, skill, owned_keys=owned)
    prereq_text = ""
    if prereq is not None:
        prereq_skill = SKILL_REGISTRY[prereq.skill_key]
        prereq_text = _fit_wire_text(prereq_skill.label, prereq.min_proficiency)
    is_owned = skill_key in owned
    ready = not is_owned and all(
        int(xp.get(edge.skill_key, 0.0) // SKILL_PROFICIENCY_XP_PER_LEVEL)
        >= edge.min_proficiency
        for edge in skill.prerequisites
    )
    return LineageNodeView(
        skill_key=skill_key,
        display_name_zh=skill.label,
        owned=is_owned,
        usable=can_use_skill(entity, skill, owned_keys=owned),
        ready=ready,
        level=progress.level,
        xp_into_level=progress.xp_into_level,
        xp_to_next_level=progress.xp_to_next_level,
        capped=progress.capped,
        prereq_text_zh=prereq_text,
        depth=depth,
    )


def build_lineage_view(entity: Any) -> LineageView:
    """Return the entity's full lineage ledger as connected graphs.

    One graph per identity-eligible prerequisite component (a lone skill only
    when owned), nodes in topological order with their longest prerequisite
    depth, and every in-component edge with its minimum level. Mutates nothing.

    Raises :class:`LineageQueryError` when stored proficiency data is
    structurally invalid, before producing any partial view.
    """
    xp = _proficiency_map(entity)
    owned = set(entity.skills.owned_keys())
    eligible = {
        key
        for key, skill in SKILL_REGISTRY.items()
        if skill_identity_eligible(entity, skill)
    }
    registry_order = {key: index for index, key in enumerate(SKILL_REGISTRY)}
    graphs: list[LineageGraphView] = []
    for members in _components(eligible):
        component = set(members)
        has_edge = any(
            edge.skill_key in component
            for key in members
            for edge in SKILL_REGISTRY[key].prerequisites
        )
        if not has_edge and (len(members) != 1 or members[0] not in owned):
            continue
        ordered = _topological_order(component)
        depth: dict[str, int] = {}
        for key in ordered:
            parents = [
                edge.skill_key
                for edge in SKILL_REGISTRY[key].prerequisites
                if edge.skill_key in component
            ]
            depth[key] = 0 if not parents else max(depth[parent] for parent in parents) + 1
        nodes = tuple(
            _node_view(entity, key, owned, xp, depth[key]) for key in ordered
        )
        roots = tuple(
            sorted(
                (
                    key
                    for key in ordered
                    if not any(
                        edge.skill_key in component
                        for edge in SKILL_REGISTRY[key].prerequisites
                    )
                ),
                key=registry_order.get,
            )
        )
        edges = tuple(
            LineageEdgeView(
                from_key=edge.skill_key,
                to_key=key,
                min_level=edge.min_proficiency,
            )
            for key in ordered
            for edge in SKILL_REGISTRY[key].prerequisites
            if edge.skill_key in component
        )
        consumed = all(node.capped for node in nodes)
        graphs.append(
            LineageGraphView(
                graph_id=roots[0],
                group_label_zh=_group_label(roots),
                root_keys=roots,
                nodes=nodes,
                edges=edges,
                owned_count=sum(1 for node in nodes if node.owned),
                total_count=len(nodes),
                consumed=consumed,
            )
        )
    graphs.sort(key=lambda graph: registry_order[graph.graph_id])
    return LineageView(
        graphs=tuple(graphs),
        completed_count=sum(1 for graph in graphs if graph.consumed),
        total_count=len(graphs),
    )


def lineage_position_for(entity: Any, skill_key: str) -> LineagePositionView:
    """Return one skill's lineage position: prerequisites and next unlocks.

    ``prerequisites`` are the skill's declared edges in registry order, each
    naming the prerequisite's label and the proficiency level it demands.
    ``next`` are the reverse-edge consumers, ascending by threshold, filtered
    to the consumers this entity's stored identity may ever own (the same
    identity eligibility every lineage read applies) — an unownable row is not
    an unlock the member could reach. Both sides are bounded to
    :data:`MAX_LINEAGE_POSITION_ROWS`. An unknown key raises
    :class:`LineageQueryError`; the function never writes entity state.
    """
    if skill_key not in SKILL_REGISTRY:
        raise LineageQueryError(f"unknown skill {skill_key!r}")
    prerequisites = tuple(
        LineagePositionEdge(
            skill_key=edge.skill_key,
            display_name_zh=SKILL_REGISTRY[edge.skill_key].label,
            level=edge.min_proficiency,
        )
        for edge in declared_prerequisites(skill_key)[:MAX_LINEAGE_POSITION_ROWS]
    )
    next_rows: list[LineagePositionEdge] = []
    for consumer_key, min_level in prerequisite_consumers(skill_key):
        consumer = SKILL_REGISTRY.get(consumer_key)
        if consumer is None or not skill_identity_eligible(entity, consumer):
            continue
        next_rows.append(
            LineagePositionEdge(
                skill_key=consumer_key,
                display_name_zh=consumer.label,
                level=min_level,
            )
        )
        if len(next_rows) == MAX_LINEAGE_POSITION_ROWS:
            break
    return LineagePositionView(
        prerequisites=prerequisites, next=tuple(next_rows)
    )
