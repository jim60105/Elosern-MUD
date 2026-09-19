"""Deterministic item-use resolution (add-declarative-item-actions D1/D2/D9).

Item mechanics identity lives in the immutable lore registry; the ordered,
typed effect profile of every usable item lives in the validated
``rulebook/item_effects.yaml`` rulebook and is resolved through the
module-level map in ``world.rules.item_effects`` at call time. This package is
the sole writer of item-use state: a side-effect-free ``preflight_item_use()``
shared by presentation and settlement, one atomic plan application, and the
public out-of-combat facade that composes the item plan with the canonical
command-source clock advance inside one outer transaction and rollback
journal (mirroring ``cast_settlement``).

Targeting (add-item-effect-targeting): every effect resolves its targets
through the shared ``world.rules.targeting.resolve_targets`` with the
``TargetRequirement`` its scope maps to — the identical presence/alive/range/
faction pipeline a skill's targets pass — and group scopes expand through the
caller-supplied action context (battlefield shorthand in a session, room
occupants out of one). The rollback journal is multi-entity: per-touched-
entity traits, buffs, and sexual state keyed by primary key, with the
in-process cache drop running per captured entity.

A successful use emits one ``item_used`` EventLog entry per executed effect
step, in profile order, each carrying ``item_key``, ``consumable``, and the
per-family payload: gauge steps add ``stat`` plus the signed ``amount``
actually applied (never the configured magnitude), and status steps add
``status_keys`` plus the ``count`` actually applied or removed.

The split:

- :mod:`world.rules.items.contracts` — ``ItemUseError``, ``ItemUseReason``,
  and the frozen request/step/plan/preflight/result/settlement dataclasses.
- :mod:`world.rules.items.journal` — ``_EntitySnapshot`` and
  ``ItemTouchedJournal``, the capture/restore machinery of the rollback
  journal (design D3).
- :mod:`world.rules.items.reads` — the handler-free storage, mirror,
  inventory, and pleasure reads (mirroring ``status_query``'s strict
  no-create reads) plus group-candidate expansion and effect-target
  resolution.
- :mod:`world.rules.items.planning` — the gauge/status step planners and
  ``preflight_item_use``.
- :mod:`world.rules.items.settlement` — the appliers, the ``item_used``
  event log, ``resolve_item_use``, and the public ``use_item`` facade.

Everything the historical ``world.rules.items`` module exposed is re-exported
here.
"""

from world.rules.items.contracts import (  # noqa: F401
    ItemEffectStep,
    ItemUseError,
    ItemUsePlan,
    ItemUsePreflight,
    ItemUseReason,
    ItemUseRequest,
    ItemUseResult,
    ItemUseSettlement,
)
from world.rules.items.journal import (  # noqa: F401
    _SEXUAL_STATE_KEYS,
    ItemTouchedJournal,
    _EntitySnapshot,
    _entity_identity,
)
from world.rules.items.planning import (  # noqa: F401
    _FULL_REASON_BY_STAT,
    _plan_gauge_step,
    _plan_status_step,
    _status_matches,
    preflight_item_use,
)
from world.rules.item_effects import (  # noqa: F401
    GaugeAdjustEffect,
    ItemEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
    StatusApplyEffect,
    StatusRemoveEffect,
    scope_targeting_rule,
)
from world.rules.items.reads import (  # noqa: F401
    _active_matching_keys,
    _gauge_from_storage,
    _group_candidates,
    _inventory_list,
    _pleasure_current,
    _rejected,
    _resolve_effect_targets,
    _select_mirror,
)
from world.rules.items.settlement import (  # noqa: F401
    _GAUGE_NOUN_ZH,
    _REMOVAL_NOUN_ZH,
    _apply_gauge_step,
    _apply_plan,
    _apply_status_step,
    _delete_mirror,
    _item_used_event_log,
    _step_text,
    _write_gauge,
    resolve_item_use,
    use_item,
)
