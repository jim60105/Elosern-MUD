"""Deterministic sexual state from design section 6.4 and change 7.

The split:

- :mod:`world.rules.sexual_state.pleasure` — the ``sexual_pleasure.yaml``
  rulebook owner: band table, multiplier tables, ``PLEASURE_CONFIG``.
- :mod:`world.rules.sexual_state.traits` — the ordered-level primitives:
  ``OrderedLevelTrait``, the sensitivity proxy, the generic baselines, and
  the derived arousal view.
- :mod:`world.rules.sexual_state.handler` — the ``SexualState`` handler
  mounted as ``entity.sexual``.
- :mod:`world.rules.sexual_state.lifecycle` — lifetime counter keys, the
  climax-cycle guard, decay, and climax-settlement bookkeeping.

Everything the historical ``world.rules.sexual_state`` module exposed is
re-exported here, including the vocabulary tuples it leaked from
``world.lore.sexual_vocab``. Pickled ``OrderedLevelTrait``/``SexualState``
attributes keep resolving through this package path.

The event rules in ``rulebook/sexual.yaml``, ``apply_event()``, and their
per-rule tests belong to the follow-on ``sexual-transition-rules`` change.
"""

from world.rules.sexual_state.handler import (  # noqa: F401
    SexualState,
)

#: Historical re-exports: the old flat module leaked these vocabulary binding
#: names for consumers that introspected its namespace.
from world.rules.sexual_state.lifecycle import (  # noqa: F401
    DECAY_CONFIG,
    _LIFETIME_COUNTER_KEYS,
    _VALID_CLIMAX_TRANSITIONS,
    _apply_climax_phase_set,
    climax_settlement_action,
    decay_tick,
    reset_daily_counters,
)
from world.lore.sexual_vocab import (  # noqa: F401
    AROUSAL_LEVELS,
    BODY_PARTS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    GENERIC_BODY_PART,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.sexual_state.pleasure import (  # noqa: F401
    PLEASURE_CONFIG,
    PleasureBand,
    PleasureConfig,
    PleasureConfigError,
    load_pleasure_config,
)
from world.rules.sexual_state.pleasure import (  # noqa: F401
    _PLEASURE_RULEBOOK,
    _error,
    _load_multiplier_table,
    _require_positive_number,
)
from world.rules.sexual_state.traits import (  # noqa: F401
    _ORDERED_FIELDS,
    _STATE_CATEGORY,
    _DerivedArousal,
    _SensitivityProxy,
    _generic_default_baseline,
    build_monster_sexual_baseline,
)
from world.rules.sexual_state.traits import (  # noqa: F401
    OrderedLevelTrait,
)

__all__ = [
    "DECAY_CONFIG",
    "PLEASURE_CONFIG",
    "OrderedLevelTrait",
    "PleasureBand",
    "PleasureConfig",
    "PleasureConfigError",
    "SexualState",
    "_VALID_CLIMAX_TRANSITIONS",
    "_apply_climax_phase_set",
    "build_monster_sexual_baseline",
    "climax_settlement_action",
    "decay_tick",
    "load_pleasure_config",
    "reset_daily_counters",
]
