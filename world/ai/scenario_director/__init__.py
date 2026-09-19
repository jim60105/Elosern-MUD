"""ScenarioDirector layer: validated quest-proposal generation (design §7.1/§7.5).

The ``scenario_director`` generative layer maps a request context to a closed,
deeply immutable ``QuestBlueprint`` proposal through the shared
validation-retry-degrade guardrail. The blueprint emits requirements, not
entities: stages carry objective kinds, ``location_req`` scene requirements,
and ``npc_req`` role tiers, so the output is fully validatable before it
touches the runtime registry. On any degrade trigger (disabled profile,
transport failure, exhausted retries, or a schema-valid-but-context-misfitting
proposal) the call resolves to a deterministic draw from the hand-written
template pool that also fits the request context, never to invalid output or
``None``.

Boundary contract (``tests/test_ai_transport_contract.py``): no module of this
package imports a state writer, a typeclass, a live transport, or a socket. The
package reads only the immutable ``world.lore`` registries and the
side-effect-free ``world.rules.namegen`` pure rollers (documented read-only-rule
exemption, namegen-npc-flow design D6), and consumes the client through the
injected protocol exactly like ``narrator.py`` and ``npc_dialogue.py``. The
request context is plain data supplied by the future composition root; this
package never reads player state.

Module map: :mod:`~world.ai.scenario_director.blueprints` owns the prompt
bounds and the frozen ``QuestBlueprint`` vocabulary;
:mod:`~world.ai.scenario_director.validators` owns the named errors, the output
schema, the semantic validators, the sentinel degrade fallback, and the
identity-referenced ``_HOOKS`` bundle; :mod:`~world.ai.scenario_director.prompt`
owns the bounded context serializer, the name-inspiration bank, and
``build_scenario_prompt``; and :mod:`~world.ai.scenario_director.generation`
owns the registration seam, the context-fit gate, and the
``generate_quest_blueprint`` entry point. This namespace is the public surface:
every name is a pass-through binding of its single owning module (the old flat
module had no ``__all__``, so the namespace exposes exactly its import surface),
and hook object identity round-trips through the package path.
"""

from __future__ import annotations

from world.ai import guardrail
from world.ai.guardrail import (
    GuardrailHooks,
    GuardrailRegistrationError,
    guarded_call,
)
from world.ai.immutable import (
    reject_mutable_containers as _reject_mutable_containers,
)
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.prompts.loader import PromptUnavailableError, render_prompt
from world.rules.namegen import roll_name_for_race
from world.quests.characterization import (
    characterize_errors,
    duplicate_display_name_errors,
    duplicate_stable_key_errors,
    race_lifespan_upper_bound,
)

from world.ai.scenario_director.blueprints import (
    MAX_CONTEXT_FIELD_LENGTH,
    MAX_NAME_LENGTH,
    MAX_SCENE_SENTENCE_LENGTH,
    MAX_TOTAL_SIZE,
    BlueprintFailure,
    BlueprintItemQuantity,
    BlueprintLocation,
    BlueprintLocationLayer,
    BlueprintNpcReq,
    BlueprintObjective,
    BlueprintObjectiveKind,
    BlueprintPortrait,
    BlueprintQuestType,
    BlueprintReward,
    BlueprintStage,
    QuestBlueprint,
    _CJK_END,
    _CJK_START,
    _TEMPLATE_PLACEHOLDER_RE,
)
from world.ai.scenario_director.validators import (
    SCENARIO_DIRECTOR_OUTPUT_SCHEMA,
    ScenarioDirectorClientRequiredError,
    ScenarioDirectorNotRegisteredError,
    ScenarioDirectorTemplateError,
    _HOOKS,
    _SCENARIO_DIRECTOR_DEGRADED,
    _VALIDATORS,
    _degrade_fallback,
    _is_cjk,
    _stages,
    _validate_anchor_known,
    _validate_archetype_known,
    _validate_deadline_valid,
    _validate_defeat_selector,
    _validate_issuer_known,
    _validate_monster_tier_known,
    _validate_no_template_placeholder,
    _validate_npc_characterization,
    _validate_npc_tier_known,
    _validate_objective_selectors,
    _validate_rank_known,
    _validate_reward_in_band,
    _validate_reward_items_known,
    _validate_scene_bound_rules,
    _validate_stage_indices_contiguous,
    _validate_strings_bounded_cjk,
)
from world.ai.scenario_director.prompt import (
    build_scenario_prompt,
    _CONTEXT_DROP_ORDER,
    _CONTEXT_KEYS,
    _INSPIRATION_COUNT,
    _INSPIRATION_SEPARATOR,
    _bounded_context,
    _cap_string,
    _name_inspirations,
)
from world.ai.scenario_director.generation import (
    _draw_template,
    _fits_context,
    _is_registered,
    _rank_order,
    _require_registered,
    _uninstall_schema,
    generate_quest_blueprint,
    get_template_pool,
    register_scenario_director,
)
