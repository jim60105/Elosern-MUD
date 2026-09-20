"""Skill-lineage graph validation (use-driven-progression design §9.3).

Moved verbatim from ``world/skills/registry.py``: the load-time caches and
the fail-closed prerequisite-graph validator the registry assembly and the
sexual-act sidecar both run after extending the registry.
"""

from world.skills.registry.vocab import SkillDef, SkillPrerequisite
# ---------------------------------------------------------------------------
# Skill-lineage graph validation (use-driven-progression design §9.3)
# ---------------------------------------------------------------------------

# skill_key -> the edges that CONSUME it, as ``(consumer_key,
# min_proficiency)`` pairs, ascending by threshold. Computed and cached by
# :func:`validate_prerequisite_graph` at registry load; the tip-cap
# derivation reads this cache in O(1) and never walks the registry again.
_LINEAGE_CONSUMERS: dict[str, tuple[tuple[str, int], ...]] = {}

# skill_key -> declared edges, in registry order (same load-time cache).
_LINEAGE_PREREQS: dict[str, tuple[SkillPrerequisite, ...]] = {}


def prerequisite_consumers(skill_key: str) -> tuple[tuple[str, int], ...]:
    """Return the cached consuming edges ``(consumer_key, min_proficiency)``.

    Reads the load-time cache built by ``validate_prerequisite_graph``; an
    unknown key yields ``()`` (a skill nobody consumes is a lineage canopy).
    """
    return _LINEAGE_CONSUMERS.get(skill_key, ())


def declared_prerequisites(skill_key: str) -> tuple[SkillPrerequisite, ...]:
    """Return the cached declared edges of one skill (``()`` when unknown)."""
    return _LINEAGE_PREREQS.get(skill_key, ())


def validate_prerequisite_graph(
    registry: dict[str, SkillDef],
) -> dict[str, tuple[tuple[str, int], ...]]:
    """Fail closed on an invalid lineage graph; cache and return the reverse map.

    Load-time rules (design §9.3), every violator named:

    1. every ``prerequisites.skill_key`` exists in ``registry``;
    2. the graph is acyclic — a Kahn topological sort; leftover nodes are
       reported as a named cycle;
    3. every ``min_proficiency`` is an int >= 1 (the dataclass constructor
       enforces the same rule per entry; this pass names the owning skill);
    4. a skill with no prerequisites is a tree root (no extra flag exists);
    5. the reverse-edge map is computed and cached for O(1) tip-cap lookup.

    The structure is an n-ary DAG: any number of edges may consume one node
    (branching) and one skill may declare any number of prerequisites
    (merging); the rules above are degree-independent. Idempotent, so the
    sexual-act sidecar re-runs it after extending the registry.
    """
    consumers: dict[str, list[tuple[str, int]]] = {}
    prereqs: dict[str, tuple[SkillPrerequisite, ...]] = {}
    for key, skill in registry.items():
        if not skill.prerequisites:
            continue
        prereqs[key] = tuple(skill.prerequisites)
        for prereq in skill.prerequisites:
            if prereq.skill_key not in registry:
                raise ValueError(
                    f"skill {key!r} declares prerequisite {prereq.skill_key!r} "
                    "which is not in SKILL_REGISTRY"
                )
            if prereq.min_proficiency < 1:
                raise ValueError(
                    f"skill {key!r} declares min_proficiency "
                    f"{prereq.min_proficiency} for {prereq.skill_key!r}; the "
                    "threshold must be >= 1"
                )
            consumers.setdefault(prereq.skill_key, []).append(
                (key, prereq.min_proficiency)
            )

    # Kahn topological sort over the prerequisite edges (prereq -> consumer).
    indegree = {key: len(prereqs.get(key, ())) for key in registry}
    queue = sorted(key for key, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        current = queue.pop(0)
        visited += 1
        for consumer_key, _ in sorted(consumers.get(current, ())):
            indegree[consumer_key] -= 1
            if indegree[consumer_key] == 0:
                queue.append(consumer_key)
                queue.sort()
    if visited != len(registry):
        cycle = sorted(key for key, degree in indegree.items() if degree > 0)
        raise ValueError(
            "skill prerequisite graph is cyclic; the offending nodes are "
            f"{cycle!r} (every listed skill either prereqs a cycle member or "
            "is consumed by one)"
        )

    reverse = {
        key: tuple(sorted(edges, key=lambda edge: (edge[1], edge[0])))
        for key, edges in consumers.items()
    }
    _LINEAGE_CONSUMERS.clear()
    _LINEAGE_CONSUMERS.update(reverse)
    _LINEAGE_PREREQS.clear()
    _LINEAGE_PREREQS.update(prereqs)
    return reverse

