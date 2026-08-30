"""Pure skill-lineage read model (skill-lineage-panel D8, design DD1/DD2).

One source, zero writes: every view here derives from ``SKILL_REGISTRY``
prerequisite edges (plus the load-time reverse-edge cache), the entity's
``db.skill_proficiency``, and the shared ``can_use_skill`` predicate. No
function in this module creates, mutates, or persists any entity or world
state; consumers (the WebClient panel presenter, the ``lineage`` command) are
serialization only.

A chain (系譜樹) is the reverse-edge closure of one lineage root. A root is a
skill that declares no prerequisites AND is consumed by at least one
prerequisite edge: a prerequisite-less skill nobody consumes is not a tree,
it is an isolated skill, and emitting one-node chains for every such skill
would bury the real trees (design DD2). Nodes are emitted in topological
order, so a branch-or-merge content drop upgrades every renderer without a
contract change (design §9.1).
"""

from collections.abc import Mapping
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
from world.skills.registry import SKILL_REGISTRY, prerequisite_consumers

# Wire bound for every rendered lineage text (design DD1): mirrors the panel
# contract's MAX_TEXT_CODE_POINTS in web/webclient/presentation/lineage.py.
# A registry label is legal up to LABEL_MAX (128), so the rendered
# 「需「label Lv.N」」 wrapper CAN overshoot the bound. The read model clamps
# deterministically — the wrapper keeps its fixed parts, the label is
# truncated and marked with a single ellipsis — so a legal maximum-length
# label can never fail the panel closed for every player. The panel mirror
# pins this constant's value against its own cap.
LINEAGE_TEXT_WIRE_MAX = 128


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
    level: int
    xp_into_level: float
    xp_to_next_level: float
    capped: bool
    prereq_text_zh: str


@dataclass(frozen=True)
class LineageChainView:
    """One root's reachable subtree in topological order."""

    root_skill_key: str
    element_or_style_zh: str
    nodes: tuple[LineageNodeView, ...]
    consumed: bool
    meter: float


@dataclass(frozen=True)
class LineageView:
    """The whole lineage ledger; counts describe the FULL untruncated view."""

    chains: tuple[LineageChainView, ...]
    completed_count: int
    total_count: int


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


def _chain_root_keys() -> tuple[str, ...]:
    """Root keys (prereq-less AND consumed) in registry insertion order."""
    return tuple(
        key
        for key, skill in SKILL_REGISTRY.items()
        if not skill.prerequisites and prerequisite_consumers(key)
    )


def _chain_nodes(root_key: str) -> tuple[str, ...]:
    """Reverse-edge closure of ``root_key`` in deterministic topological order.

    Kahn topological sort over the subgraph induced by the closure, keyed by
    registry insertion order, so the sequence is stable and prerequisite
    edges always point backwards. A merging node (two root ancestors)
    legitimately appears in both roots' closures; degree never special-cases.
    """
    closure: set[str] = set()
    frontier = [root_key]
    while frontier:
        current = frontier.pop()
        if current in closure:
            continue
        closure.add(current)
        frontier.extend(key for key, _ in prerequisite_consumers(current))
    indegree = {
        key: sum(1 for pre in SKILL_REGISTRY[key].prerequisites if pre.skill_key in closure)
        for key in closure
    }
    registry_order = {key: index for index, key in enumerate(SKILL_REGISTRY)}
    queue = sorted((key for key, degree in indegree.items() if degree == 0), key=registry_order.get)
    ordered: list[str] = []
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for consumer_key, _ in prerequisite_consumers(current):
            if consumer_key not in closure:
                continue
            indegree[consumer_key] -= 1
            if indegree[consumer_key] == 0:
                queue.append(consumer_key)
                queue.sort(key=registry_order.get)
    # The canonical graph is acyclic (load-time validation), so the sort
    # always drains; anything left would be a bug, not content.
    if len(ordered) != len(closure):
        raise LineageQueryError(
            f"lineage chain from {root_key!r} hit a cycle the registry "
            "validator should have rejected"
        )
    return tuple(ordered)


def _chain_label(root_key: str) -> str:
    """The chain's 元素／風格 label: the root's element, else its category."""
    skill = SKILL_REGISTRY[root_key]
    if skill.element is not None:
        return skill.element.display_name_zh
    return CATEGORY_LABELS[skill.category]


def _node_view(entity: Any, skill_key: str, owned: set, xp: dict[str, float]) -> LineageNodeView:
    skill = SKILL_REGISTRY[skill_key]
    stored = xp.get(skill_key, 0.0)
    level = int(stored // SKILL_PROFICIENCY_XP_PER_LEVEL)
    cap = proficiency_cap(skill_key)
    capped = level >= cap
    xp_into_level = stored - level * SKILL_PROFICIENCY_XP_PER_LEVEL
    prereq = missing_prerequisite(entity, skill)
    prereq_text = ""
    if prereq is not None:
        prereq_skill = SKILL_REGISTRY[prereq.skill_key]
        prereq_text = _fit_wire_text(prereq_skill.label, prereq.min_proficiency)
    return LineageNodeView(
        skill_key=skill_key,
        display_name_zh=skill.label,
        owned=skill_key in owned,
        usable=can_use_skill(entity, skill),
        level=level,
        xp_into_level=xp_into_level,
        xp_to_next_level=0.0 if capped else SKILL_PROFICIENCY_XP_PER_LEVEL - xp_into_level,
        capped=capped,
        prereq_text_zh=prereq_text,
    )


def _chain_meter(nodes: tuple[LineageNodeView, ...]) -> float:
    """0..1 shallowest-uncapped progress (design DD2).

    All-capped → exactly 1.0. Otherwise, walking the topological order, every
    node before the first uncapped one is capped and contributes a full step;
    the first uncapped node contributes its XP fraction; nothing after it
    counts: ``meter = (i + fraction) / len(nodes)``.
    """
    total = len(nodes)
    for index, node in enumerate(nodes):
        if not node.capped:
            fraction = node.xp_into_level / SKILL_PROFICIENCY_XP_PER_LEVEL
            return (index + fraction) / total
    return 1.0


def build_lineage_view(entity: Any) -> LineageView:
    """Return the entity's full lineage ledger; mutates nothing.

    Raises :class:`LineageQueryError` when stored proficiency data is
    structurally invalid, before producing any partial view.
    """
    xp = _proficiency_map(entity)
    owned = set(entity.skills.owned_keys())
    chains: list[LineageChainView] = []
    for root_key in _chain_root_keys():
        nodes = tuple(
            _node_view(entity, key, owned, xp) for key in _chain_nodes(root_key)
        )
        consumed = all(node.capped for node in nodes)
        chains.append(
            LineageChainView(
                root_skill_key=root_key,
                element_or_style_zh=_chain_label(root_key),
                nodes=nodes,
                consumed=consumed,
                meter=_chain_meter(nodes),
            )
        )
    return LineageView(
        chains=tuple(chains),
        completed_count=sum(1 for chain in chains if chain.consumed),
        total_count=len(chains),
    )
