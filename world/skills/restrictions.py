"""Pure execution/effect reads of rules-owned examination restrictions."""

from collections.abc import Mapping, Sequence
from typing import Any


def exam_restriction(entity: Any) -> Mapping | None:
    """Read the persisted overlay without mounting handlers or writing state."""
    record = getattr(getattr(entity, "db", None), "guild_exam_restriction", None)
    if record is None:
        return None
    if not isinstance(record, Mapping) or record.get("host_id") != entity.pk:
        raise ValueError("malformed examination restriction identity")
    if not isinstance(record.get("exam_id"), str) or not record["exam_id"]:
        raise ValueError("malformed examination restriction identity")
    allowed = record.get("allowed_skills")
    if isinstance(allowed, str) or not isinstance(allowed, Sequence):
        raise ValueError("malformed examination restriction skill policy")
    return record


def skill_effect_allowed(entity: Any, skill_key: str) -> bool:
    """Return execution/effect eligibility, independently of learned ownership."""
    from world.skills.registry import SKILL_REGISTRY
    from world.skills.eligibility import skill_identity_eligible

    skill = SKILL_REGISTRY.get(skill_key)
    if skill is not None and not skill_identity_eligible(entity, skill):
        return False
    record = exam_restriction(entity)
    return record is None or skill_key in record["allowed_skills"]


def restricted_neutral_value(entity: Any, trait_key: str, value: int) -> int:
    """Reduce the permitted neutral value before transient combat modifiers."""
    record = exam_restriction(entity)
    if record is None:
        return value
    ceiling = record["neutral_ceilings"].get(trait_key)
    return value if ceiling is None else min(value, ceiling)

