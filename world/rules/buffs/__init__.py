"""BuffHandler integration for design sections 5.2 and 6.4.

The split:

- :mod:`world.rules.buffs.definitions` — the YAML schema validator and
  loader, the definition/policy/tick dataclasses, the selector and marker
  vocabularies, ``BUFF_DEFINITIONS`` (the shipped rulebook), and the
  blocking/no-op key sets.
- :mod:`world.rules.buffs.buff_class` — the single generic
  ``RulebookBuff`` class every definition key is mounted through, plus the
  divert-budget accessors.
- :mod:`world.rules.buffs.rates` — the rate/recovery tick machinery:
  ``tick_buffs``, ``_apply_rate_modifier``, the sustained-recovery tick,
  the damaging-rate predicates, and the caster-share credit path.
- :mod:`world.rules.buffs.surface` — the apply/read/remove/cleanse surface:
  ``apply_buff``, the active-buff readers, the selector-driven removal
  vocabulary, the marker/growth-rate helpers, and ``_handle_cleanse``.

Everything the historical ``world.rules.buffs`` module exposed is
re-exported here.
"""

from world.rules.buffs.buff_class import (  # noqa: F401
    RulebookBuff,
    get_divert_consumed,
    update_divert_consumed,
)
from world.rules.buffs.definitions import (  # noqa: F401
    BLOCKING_BUFF_KEYS,
    BUFF_DEFINITIONS,
    MARKER_VOCABULARY,
    ROUND_ORDER_VOCABULARY,
    BuffDefinition,
    RecoveryRatePolicy,
    TickRecord,
    _NO_OP_RATE_TARGETS,
    _REMOVE_SELECTORS,
    _parse_percent_value,
    get_recovery_policy,
    load_buff_definitions,
)
from world.rules.buffs.rates import (  # noqa: F401
    _active_buff_instances,
    _apply_rate_modifier,
    _apply_recovery_tick,
    _credit_caster_share,
    _is_damaging_gauge_rate,
    _is_damaging_rate,
    _resolve_source_origin,
    tick_buffs,
)
from world.rules.buffs.surface import (  # noqa: F401
    _handle_cleanse,
    _remove_buff_keys,
    active_buff_keys_from_storage,
    active_stack_count,
    apply_buff,
    blocks_action,
    cleanse_debuffs,
    clear_conferred_growth_rates,
    entity_active_buffs,
    grant_conferred_growth_rate,
    growth_rate_multiplier,
    has_positional_marker,
    remove_by_selector,
    remove_ground_markers,
    remove_positional_markers,
)

#: Historical re-exports: the old flat module leaked these binding names for
#: consumers that introspected its namespace.
from world.rules.quantum import SETTLEMENT_QUANTUM_SECONDS  # noqa: F401
from world.rules.traits import GAUGE_KEYS  # noqa: F401
