# Design

## Context

Observed pure effective_exposure uses stored_sexual_level plus worn equipment bias and canonical EXPOSURE_LEVELS. SkillHandler.owned_keys reads owned/innate/unlocked skills, skill_proficiency_level is the canonical XP-to-level reader. is_companion uses bidirectional bindings. read_world_clock().calendar is read-only; CLOCK_YAML[dayparts] defines midnight/dawn/noon/dusk boundaries.

## Goals / Non-Goals

**Goals:** Actor identity, inventory, present companion, time, skills and exposure conditions. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Implement evaluate_condition and condition_hint for All/Any and the seven physical/identity leaf families from Shared contract v1. Every projection/selection uses one read-only DialogueContext snapshot for actor/owner/host; no reader calls get_world_clock, entity.sexual, mutating handlers, practice grant, equipment toggle or inventory consumption. `RaceIs` reads actor.race against RACE_REGISTRY and canonical display labels; SocialIdentityIs uses read_social_identities(actor). Carries uses `world.rules.party_inventory._strict_inventory(actor)` (canonical Sequence of repeated item keys), using list.count(item_key) on actor bag holdings only (no commander pooled/member bag fallback); malformed sequences fail closed; never reinterpret the inventory as a quantity mapping. CompanionPresent(source_kind, source_key) accepts source_kind `profile` or `preset`; validate against NPC_PROFILE_REGISTRY or PLAYER_PRESET_REGISTRY respectively, then match profile-kind provenance_profile_key or companion-kind validated npc_persona_meta.provenance.profile plus db.creation_preset_key among live_companions(owner), requires is_companion and actual actor.location co-location; an imported name or stale roster id never matches. Multiple valid profile matches use existential presence and no identity substitution.

TimePeriod uses read_world_clock().calendar and the two named CLOCK_YAML daypart hour boundaries as a cyclic half-open [start,end) world-day interval, wrapping midnight; equal endpoints invalid. Derive elapsed seconds from calendar using CLOCK_YAML seconds_per_hour, no wall time or invented daypart bands. Hint labels for midnight/dawn/noon/dusk reuse existing time-skip UI translations. Clock absence fails closed. SkillOwned requires exact owned_keys membership; a conferred scale-only grant does not establish ownership. Optional min_proficiency is a nonnegative integer canonical skill_proficiency_level threshold, never raw XP or a new formula. Exposure compares effective_exposure(actor) in exact EXPOSURE_LEVELS order, supports >=, <=, inclusive two-bound range and rejects inverted/unknown bands. Do not materialize SexualStateHandler and do not auto-change affinity for exposure.

Hints recurse over the SAME All/Any tree with explicit parentheses and localized conjunction/disjunction. Resolve item label from lore item registry, companion public label from PLAYER_PRESET_REGISTRY[source_key].display_name for preset sources, or the canonical settlement service-host row.name whose profile_key matches for profile sources (reject ambiguous/missing labels), skill.label, race registry label and canonical exposure terms. No free-form per-topic duplicate hint, hidden numeric affinity, alternate rank/status table, or persona parsing. Invalid declaration keys raise an identity-named validation error before publishing a shipped registry; invalid runtime state returns false plus bounded facade integrity event. Variant evaluation chooses unique highest priority and fallback, without changing reading identity or current delivered variant mid-play.

This is independently runnable by applying conditions to synthetic complete scenes through select_authored_topic and text output. Availability UI is a separate owner; selection must already reject unmet formal requires so protected data cannot leak in the intermediate runtime. Default unavailable hidden when that UI has not landed. Extend the existing possessed browser fixture to show real race-qualified variant and equipped exposure variant after a fresh selection.

Canonical source paths are world/lore/races.py, world/lore/items.py, world/lore/npc_profiles/__init__.py, world/lore/player_presets/__init__.py, world/rules/npc_persona.py::provenance_profile_key, world/rules/party_inventory.py::_strict_inventory and world/rules/starting_companions.py::build_starting_companion. No companion condition relies on an editable display name.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/rules/dialogue_conditions.py (new)`
- `world/lore/dialogue/conditions.py`
- `world/rules/dialogue.py`
- `world/rules/progression/_gates.py (read only)`
- `world/rules/equipment_effects.py (read only)`

## Risks / Trade-offs

Owns new condition evaluator. Progression slice extends same files after this. Shared browser fixture and dialogue.py are serialized; equipment/progression sources stay read-only. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_dialogue_physical_conditions
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
