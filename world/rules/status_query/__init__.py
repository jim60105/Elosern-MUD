"""Frozen no-create status read model for the WebClient status presenter.

Presentation must never materialize lazy handlers or default state. This
package reads only the persistent trait attribute, optional buff cache, sexual
baseline or materialized traits, creation flag, disguise record, and
combat-session record, and interprets them in memory. It never constructs
``entity.traits``, ``entity.buffs``, or ``entity.sexual`` and never writes to
storage.

The split:

- :mod:`world.rules.status_query.models` — frozen dataclasses, label maps,
  closed vocabularies/constants, ``StatusQueryError``, ``_LevelRef``.
- :mod:`world.rules.status_query.readers` — strict no-create attribute readers
  (gauge, buff cache, static/counter traits, equipment, disguise, combat
  record) and the active/passive skill-key split.
- :mod:`world.rules.status_query.sexual` — the no-create sexual-level,
  counter, and intimate-view readers.
- :mod:`world.rules.status_query.context` — the pure stored-snapshot facade
  plus the combat-modifier condition context both read models evaluate
  through.
- :mod:`world.rules.status_query.assembly` — the once-per-read fully
  validated input assembly (design D3).
- :mod:`world.rules.status_query.status` — ``build_status_read_model`` and the
  buff/rule condition projection.
- :mod:`world.rules.status_query.breakdown` — the stat-breakdown parity-replay
  core (per-source layers + ``build_stat_breakdown``).
- :mod:`world.rules.status_query.character` — the version-5 character panel
  build plus ``group_skill_keys``.

Everything the historical ``world.rules.status_query`` module exposed is
re-exported here.
"""

from world.rules.status_query.assembly import (  # noqa: F401
    _Assembly,
    _assemble,
)
from world.rules.status_query.breakdown import (  # noqa: F401
    _validated_row,
    build_stat_breakdown,
)
from world.rules.status_query.character import (  # noqa: F401
    build_character_read_model,
    group_skill_keys,
)
from world.rules.status_query.models import (  # noqa: F401
    _COUNTER_KEYS,
    _EQUIPMENT_SLOTS,
    _GAUGE_KEYS,
    _STATIC_KEYS,
    MAX_BREAKDOWN_ROWS,
    MAX_LAYERS_PER_STAT,
    TRAIT_LABELS,
    CharacterCategoryGroupView,
    CharacterEquipmentView,
    CharacterReadModel,
    CharacterSkillGroupView,
    CharacterSkillRow,
    CharacterTraitView,
    ConditionValue,
    GaugeValue,
    IntimateView,
    StatBreakdownRow,
    StatLayer,
    StatusQueryError,
    StatusReadModel,
    _LevelRef,
)
from world.rules.status_query.status import (  # noqa: F401
    build_status_read_model,
)
