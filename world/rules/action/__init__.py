"""Atomic, deterministic skill-action resolution.

The package splits the single-writer action pipeline into cohesive modules:

- :mod:`world.rules.action.contracts` — request/result contracts, the
  rejection vocabulary, and the handler/planner registries.
- :mod:`world.rules.action.gates` — steps 1-4b validation gates.
- :mod:`world.rules.action.routing` — audience planning and step-5 dispatch.
- :mod:`world.rules.action.effects` — the effect-handler modules; importing
  them registers every effect prefix as an import side effect.
- :mod:`world.rules.action.costs` — steps 6/8 cost, practice, and time.
- :mod:`world.rules.action.event_log` — step 7 event-log construction.
- :mod:`world.rules.action.transaction` — the snapshot/restore commit point.
- :mod:`world.rules.action.resolver` — ``ActionResolver``.

Everything the pipeline's callers imported from the historical
``world.rules.action`` module is re-exported here.
"""

from world.rules.action.contracts import (
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_REQUIRED_CONTEXT,
    _EFFECT_HANDLER_SURFACES,
    _EVENT_EFFECT_PLANNERS,
    _entity_key,
    _event_context,
    _effect_prefix,
    DEFAULT_CAST_SECONDS,
    SKILL_TIME_OVERRIDES,
    ActionRequest,
    ActionResult,
    CommitFailed,
    EffectHandler,
    PendingEffect,
    RejectedAction,
    RejectReason,
    SNAPSHOTTED_SURFACES,
    UnsnapshottedSurfaceError,
    parse_effect_key,
    register_effect_handler,
    register_event_effect_planner,
)
from world.rules.action.costs import (
    _apply_practice,
    _deduct_resource,
    _step6_resource_deduction,
    _step6_skill_practice,
    _step8_time_cost,
)
from world.rules.action.effects import (  # noqa: F401  (import for handler registration)
    buffs as _effects_buffs,
    conferral as _effects_conferral,
    divine as _effects_divine,
    gauge_transfer as _effects_gauge_transfer,
    sexual as _effects_sexual,
)
from world.rules.action.effects.buffs import (
    recovery_snapshot_kwargs,
    resolve_source_tier,
    source_attribution_kwargs,
    stage_buff_pending,
)
from world.rules.action.effects.conferral import (
    _CONFERRAL_EMPTY_SET_DETAIL,
    _conferral_empty_set_failure,
    _handle_confer_growth_rate,
    _handle_confer_skill_partial,
    _handle_divine_mystery,
    _handle_revoke_grants,
    _handle_reveal_disguise,
    _handle_set_disguise,
)
from world.rules.action.effects.buffs import (
    _handle_buff_apply,
    _handle_self_buff_apply,
)
from world.rules.action.effects.divine import (
    _drain_resources,
    _handle_clamp_shame,
    _handle_climax_extension_stage,
    _handle_divine_pleasure_max,
    _handle_mark_submission,
    _handle_pleasure_peak,
    _handle_restore_purity,
    _handle_saturate_sensitivity,
    _handle_sexual_drain,
    _stage_non_actor_targets,
    _stored_pleasure_value,
)
from world.rules.action.effects.gauge_transfer import _handle_gauge_transfer
from world.rules.action.effects.sexual import (
    _counter_pending_effect,
    _get_stimulus_interval,
    _handle_act_pair_event,
    _handle_actor_sexual_event,
    _handle_pleasure_effect,
    _handle_sexual_counter_effect,
    _handle_sexual_event,
    _handle_stimulus,
    _handle_target_sexual_event,
    _resolve_act,
    _stage_apply_event,
    _stimulus_rng,
)
from world.rules.action.event_log import (
    _ENTRY_TEMPLATES,
    _defeated_entry,
    _entries_from_effect,
    _logged_targets,
    _step7_build_event_log,
)
from world.rules.action.gates import (
    _adjusted_costs,
    _resist_pending_effect,
    _step1_divine_arts_gate,
    _step1_freeform_gate,
    _step1_ownership,
    _step2_resource_check,
    _step3_targeting,
    _step4_capability,
    _step4a_spell_conditions,
    _step4b_sexual_resist_gate,
    _stored_trait_value,
    stored_gauge_pair,
)
from world.rules.action.resolver import ActionResolver
from world.rules.action.routing import (
    _bind_resolved_effect,
    _matches_audience_condition,
    _occurrence_scale,
    _require_context,
    _step5_effect_resolution,
    plan_effect_audiences,
)
from world.rules.action.transaction import (
    _ENTITY_SURFACES,
    _attribute_snapshot,
    _commit,
    _is_battlefield_like,
    _restore_attribute,
    _restore_entity_state,
    _restore_touched,
    _restore_touched_best_effort,
    _snapshot_entity_state,
    _snapshot_touched,
)

# Historical self-registration tail: importing the package registers the
# action-evidence planner exactly once.
from world.rules.action_evidence import register_action_evidence_planner

register_action_evidence_planner()

__all__ = [
    "DEFAULT_CAST_SECONDS",
    "SNAPSHOTTED_SURFACES",
    "ActionRequest",
    "ActionResult",
    "ActionResolver",
    "CommitFailed",
    "EffectHandler",
    "PendingEffect",
    "RejectReason",
    "RejectedAction",
    "SNAPSHOTTED_SURFACES",
    "UnsnapshottedSurfaceError",
    "parse_effect_key",
    "register_effect_handler",
    "register_event_effect_planner",
    "resolve_source_tier",
    "recovery_snapshot_kwargs",
    "source_attribution_kwargs",
    "stage_buff_pending",
    "stored_gauge_pair",
]
