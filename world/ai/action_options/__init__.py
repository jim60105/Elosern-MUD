"""Frozen action-options card vocabulary and the validation ladder (proposals only).

This package owns the immutable ``OptionSet``/``SuggestionCard`` vocabulary
exchanged between the generative layer, the trigger service, and the
``context_actions`` presentation. It is a pure, proposal-only package: it
imports no Evennia typeclasses and no state writer at module time, holds no
module-level logger binding, and never mutates game state. The single-writer
boundary is untouched — this vocabulary is proposal-only by construction.

The vocabulary-lock contract (overview D-1): a validated card's payload is a
copy of one *currently executable* affordance. The ladder's stage 9 resolves
``action_code`` against the caller-supplied affordance list and unconditionally
replaces the card's ``params`` with that affordance's canonical payload, so a
card shipped to the client is byte-for-byte the payload the dispatcher accepts.
The single exception is the ``freeform`` card, whose ``{"npc_id": int}`` params
are binding-only: no registered validator produces that shape without
``speech``, so the full dispatcher validator runs only on the client-composed
dispatch payload (webclient change).

The 12-stage ladder order (stages 0-11) is public contract: the pipeline reuses
the stage numbers for retry messages, and the first failing stage wins and maps
to degrade. ``validate_optionset`` returns an ``OptionSet`` on success and
raises ``OptionsValidationError`` carrying one named rejection code on the
first failure.

The generative layer (pipeline design doc) extends this vocabulary with the
bounded-context serializer, the prompt assembly, and the guarded generation
pipeline: ``build_options_context`` truncates the deterministic view in fixed
order, ``build_action_options_prompt`` renders the two ``action_options``
prompt-library keys, and ``generate_action_options`` runs the guardrail's
validation-retry-degrade loop (with the degrade fallback and the raw-wire
output schema installed by ``register_action_options``). The same import
discipline holds: no Evennia import, no state writer, no live transport, and
no module-level logger binding at module time; the only outputs are the frozen
``OptionSet`` proposal and ``None``.

The bounds constants below are the single source mirrored later by
``protocol.js`` under the dual-direction parity test.

Module map: :mod:`~world.ai.action_options.cards` owns the frozen vocabulary
and bounds table; :mod:`~world.ai.action_options.context` the bounded-context
serializer and named error classes; :mod:`~world.ai.action_options.prompt` the
prompt assembly; :mod:`~world.ai.action_options.ladder` the 12-stage ladder,
the exact-field parser, and the stage table; and
:mod:`~world.ai.action_options.generation` the generation pipeline and the
identity-referenced guardrail hooks (``_degrade_fallback``,
``ACTION_OPTIONS_OUTPUT_SCHEMA``, ``_ACTION_OPTIONS_DEGRADED``). This namespace
is the public surface: every name below is a pass-through binding of its single
owning module, so hook identity round-trips through the package path.
"""

from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.ai import guardrail
from world.ai.guardrail import (
    GuardrailRegistrationError,
    guarded_call,
    register_degrade_fallback,
)
from world.ai.immutable import (
    reject_mutable_containers as _reject_mutable_containers,
)
from world.ai.profiles import get_profile
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)
from world.prompts.loader import PromptUnavailableError, render_prompt

from world.ai.action_options.cards import (
    CARD_KINDS,
    CONTEXT_KIND,
    FREEFORM_ACTION_CODE,
    MAX_CARDS,
    MAX_HINT_LENGTH,
    MAX_LABEL_LENGTH,
    MAX_OPTIONSET_CACHE_ENTRIES,
    MAX_PARAM_STRING_LENGTH,
    MAX_PARAMS,
    MIN_CARDS,
    NEGATIVE_MEMO_TTL,
    OptionSet,
    OptionsValidationError,
    READY_STATUS,
    SuggestionCard,
    _validate_params_shape,
)
from world.ai.action_options.context import (
    ActionOptionsBindingError,
    ActionOptionsClientRequiredError,
    ActionOptionsContext,
    ActionOptionsInputError,
    ActionOptionsMonsterEntry,
    ActionOptionsNPCEntry,
    ActionOptionsNotRegisteredError,
    MAX_AFFORDANCES,
    MAX_MONSTER_ENTRIES,
    MAX_MONSTER_ENTRY_LENGTH,
    MAX_NARRATIVE_TAIL_LENGTH,
    MAX_NPC_DIGEST_LENGTH,
    MAX_NPC_ENTRIES,
    MAX_OBJECTIVE_LENGTH,
    MAX_ROOM_NAME_LENGTH,
    MAX_ROOM_SUMMARY_LENGTH,
    build_options_context,
    _build_monster_entry,
    _build_npc_entry,
)
from world.ai.action_options.prompt import (
    build_action_options_prompt,
    _serialize_structured,
)
from world.ai.action_options.ladder import (
    LADDER_CODES,
    CARD_COUNT_OUT_OF_RANGE,
    DIGIT_IN_LABEL,
    EMPTY_LABEL,
    HINT_TOO_LONG,
    LABEL_TOO_LONG,
    LEAK_DETECTED,
    NO_SUCH_AFFORDANCE,
    NON_CJK_LABEL,
    PLACEHOLDER_LABEL,
    SCHEMA_VIOLATION,
    UNKNOWN_ACTION_CODE,
    UNKNOWN_TARGET,
    enrich_options_payload,
    parse_action_options_payload,
    validate_optionset,
    _has_cjk,
    _leaked,
    _registered_action_codes,
    _resolve_freeform,
    _resolve_known_action,
    _STAGE_BY_CODE,
)
from world.ai.action_options.generation import (
    ACTION_OPTIONS_OUTPUT_SCHEMA,
    generate_action_options,
    register_action_options,
    _ACTION_OPTIONS_DEGRADED,
    _degrade_fallback,
    _evaluate_enriched,
    _is_registered,
    _log_bounded_diagnostic,
    _make_enriched_validator,
    _require_registered,
    _resolve_freeform_bindings,
    _stage_message,
    _uninstall_all_own_hooks,
    _uninstall_fallback,
    _uninstall_schema,
)

__all__ = [
    "ACTION_OPTIONS_OUTPUT_SCHEMA",
    "ActionOptionsBindingError",
    "ActionOptionsClientRequiredError",
    "ActionOptionsContext",
    "ActionOptionsInputError",
    "ActionOptionsMonsterEntry",
    "ActionOptionsNPCEntry",
    "ActionOptionsNotRegisteredError",
    "CARD_KINDS",
    "CARD_COUNT_OUT_OF_RANGE",
    "CONTEXT_KIND",
    "DIGIT_IN_LABEL",
    "EMPTY_LABEL",
    "FREEFORM_ACTION_CODE",
    "HINT_TOO_LONG",
    "LABEL_TOO_LONG",
    "LADDER_CODES",
    "LEAK_DETECTED",
    "MAX_AFFORDANCES",
    "MAX_CARDS",
    "MAX_HINT_LENGTH",
    "MAX_LABEL_LENGTH",
    "MAX_MONSTER_ENTRIES",
    "MAX_MONSTER_ENTRY_LENGTH",
    "MAX_NARRATIVE_TAIL_LENGTH",
    "MAX_NPC_DIGEST_LENGTH",
    "MAX_NPC_ENTRIES",
    "MAX_OBJECTIVE_LENGTH",
    "MAX_OPTIONSET_CACHE_ENTRIES",
    "MAX_PARAMS",
    "MAX_ROOM_NAME_LENGTH",
    "MAX_ROOM_SUMMARY_LENGTH",
    "MAX_SAFE_INTEGER",
    "MIN_CARDS",
    "NEGATIVE_MEMO_TTL",
    "NO_SUCH_AFFORDANCE",
    "NON_CJK_LABEL",
    "OptionsValidationError",
    "OptionSet",
    "PLACEHOLDER_LABEL",
    "READY_STATUS",
    "SCHEMA_VIOLATION",
    "SuggestionCard",
    "UNKNOWN_ACTION_CODE",
    "UNKNOWN_TARGET",
    "build_action_options_prompt",
    "build_options_context",
    "enrich_options_payload",
    "generate_action_options",
    "parse_action_options_payload",
    "register_action_options",
    "validate_optionset",
]
