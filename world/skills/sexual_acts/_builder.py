"""The ``SexualActDef`` sidecar and the ``_act_family()`` construction helper.

A sex act is an ordinary ``SkillDef`` row in ``SKILL_REGISTRY`` (so the
existing ``ActionResolver`` pipeline, ownership model, and combat panel
consume it unchanged) plus a parallel frozen ``SexualActDef`` carrying the
act-specific metadata a ``SkillDef`` has no field for: counter-based unlock
requirements, participant body parts, base pleasure magnitude, the actor's
share of that pleasure, the lifetime counters an execution touches, the
``sexual.yaml`` events it emits, and whether the target may resist.

``line`` is deliberately not a field of ``SexualActDef``: ``SkillDef.group``
carries it, mirroring how ``_elemental_spells()`` writes ``group=element``
once per family. Storing the line twice would create two sources of truth
for the same fact; consumers read ``SKILL_REGISTRY[key].group`` instead.
"""

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from world.lore.sexual_vocab import BODY_PARTS, GENERIC_BODY_PART
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

# Lines whose acts never target a body part: interspecies partners are
# arbitrarily shaped monsters and divine arts operate through divinity.
_PARLESS_LINES = ("異種", "神之秘法")

# Events an act's ``sexual_events`` tuple may never declare (design D-8):
# the first three target the pleasure gauge directly and would double-count
# against the act's own scaled ``pleasure:`` effect, and the last two are
# owned exclusively by the climax-settlement mechanism (combat/clock upkeep
# calls), never by an individual act's cast.
_FORBIDDEN_SEXUAL_EVENTS = frozenset(
    {
        "stimulus_applied",
        "sustained_stimulus_applied",
        "extreme_stimulus_applied",
        "climax_ends",
        "climax_extended",
    }
)


@dataclass(frozen=True)
class SexualActDef:
    """Immutable act-specific metadata paired with one ``SkillDef`` row.

    ``unlock`` is frozen at construction: the dataclass's frozenness only
    blocks field reassignment, so the mapping is copied into a read-only
    ``MappingProxyType`` to keep the registry's unlock thresholds immutable
    even when a consumer holds the caller's original mapping.
    """

    key: str
    unlock: Mapping[str, int]
    base_pleasure: int
    actor_part: str | None
    target_part: str | None
    actor_pleasure_ratio: float
    actor_counters: tuple[str, ...]
    participant_counters: tuple[str, ...]
    sexual_events: tuple[str, ...]
    resistible: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "unlock", MappingProxyType(dict(self.unlock)))


def _act_family(
    line: str,
    *rows: tuple[
        str,
        str,
        str,
        TargetSpec,
        Mapping[str, int],
        int,
        str | None,
        str | None,
        float,
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        bool,
    ],
    requires_divine_arts: bool = False,
) -> tuple[tuple[SkillDef, SexualActDef], ...]:
    """Build one line's paired ``SkillDef``/``SexualActDef`` rows.

    Each row is ``(key, label, description, target_spec, unlock,
    base_pleasure, actor_part, target_part, actor_pleasure_ratio,
    actor_counters, participant_counters, sexual_events, resistible)`` in
    the exact order of the resolution design doc. The line is written once
    per family; every produced ``SkillDef`` is an ACTIVE, zero-cost,
    out-of-combat-castable skill categorised ``SEXUAL_ACT`` whose ``effects``
    list carries the ``pleasure:<key>``/``sexual_counter:<key>`` prefixes for
    its own key plus one ``sexual_event:<name>`` string per declared event,
    resolving through the handlers ``sexual-act-effects`` registers.

    Runs the per-row structural checks (design D-6 items 1-5 plus the
    forbidden-events check) before returning, raising ``ValueError`` naming
    the offending key so a catalog author's mistake fails at import time
    rather than at play time.
    """
    pairs: list[tuple[SkillDef, SexualActDef]] = []
    for row in rows:
        (
            key,
            label,
            description,
            target_spec,
            unlock,
            base_pleasure,
            actor_part,
            target_part,
            actor_pleasure_ratio,
            actor_counters,
            participant_counters,
            sexual_events,
            resistible,
        ) = row
        forbidden = _FORBIDDEN_SEXUAL_EVENTS & set(sexual_events)
        if forbidden:
            raise ValueError(
                f"act {key!r}: forbidden sexual_event names {sorted(forbidden)}"
            )
        if (
            isinstance(actor_pleasure_ratio, bool)
            or not isinstance(actor_pleasure_ratio, (int, float))
            or not isfinite(actor_pleasure_ratio)
        ):
            raise ValueError(f"act {key!r}: actor_pleasure_ratio must be a finite number")
        if not requires_divine_arts and actor_pleasure_ratio <= 0:
            raise ValueError(
                f"act {key!r}: actor_pleasure_ratio must be positive "
                "unless the family requires divine arts"
            )
        if (
            not isinstance(unlock, Mapping)
            or any(not isinstance(name, str) for name in unlock)
            or any(
                isinstance(threshold, bool) or not isinstance(threshold, int)
                for threshold in unlock.values()
            )
        ):
            raise ValueError(
                f"act {key!r}: unlock must map counter attribute names to "
                "integer thresholds"
            )
        if actor_part == GENERIC_BODY_PART or target_part == GENERIC_BODY_PART:
            raise ValueError(
                f"act {key!r}: generic body part is not a declared part"
            )
        if line in _PARLESS_LINES and target_part is not None:
            raise ValueError(
                f"act {key!r}: {line} acts must not declare a target part"
            )
        for part_field, part in (
            ("actor_part", actor_part),
            ("target_part", target_part),
        ):
            if part is not None and part not in BODY_PARTS:
                raise ValueError(
                    f"act {key!r}: {part_field} {part!r} is not a BODY_PARTS member"
                )
        if (
            isinstance(base_pleasure, bool)
            or not isinstance(base_pleasure, int)
            or base_pleasure <= 0
        ):
            raise ValueError(f"act {key!r}: base_pleasure must be a positive integer")
        if not isinstance(resistible, bool):
            raise ValueError(f"act {key!r}: resistible must be a bare bool")

        skill = SkillDef(
            key=key,
            label=label,
            description=description,
            kind=SkillKind.ACTIVE,
            target_spec=target_spec,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=[
                f"pleasure:{key}",
                f"sexual_counter:{key}",
                *(f"sexual_event:{name}" for name in sexual_events),
            ],
            category=SkillCategory.SEXUAL_ACT,
            group=line,
            requires_divine_arts=requires_divine_arts,
        )
        act = SexualActDef(
            key=key,
            unlock=dict(unlock),
            base_pleasure=base_pleasure,
            actor_part=actor_part,
            target_part=target_part,
            actor_pleasure_ratio=actor_pleasure_ratio,
            actor_counters=actor_counters,
            participant_counters=participant_counters,
            sexual_events=sexual_events,
            resistible=resistible,
        )
        pairs.append((skill, act))
    return tuple(pairs)
