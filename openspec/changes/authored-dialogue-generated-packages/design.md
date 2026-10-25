# Design

## Context

CodeGraph discovery established the actual production chain. `world/narrative/dispatch_runner.py::_advance` handles STAGE_SCENE by calling `generate_beat_scene_blueprint`; `_publish` wraps `settle_decision` and dispatch arrangement in one transaction. `world/narrative/quest_beats.py::to_scene_package/publish_quest_beat/_publish_scene_package` preserve package sections and call `world/quests/encounters.py::publish_scene_package`, which validates before writes and uses publication_scope plus atomic scene_store.publish_package. The immutable payload already belongs in DB.

The generator is `world/ai/scenario_director/generation.py::generate_beat_scene_blueprint`, using inline EXTENDED_BLUEPRINT_SCHEMA composed from PACKAGE_PAYLOAD_SCHEMA in packages.py, but its system message comes from `prompt.py::build_scenario_prompt` and `prompts/scenario_director.yaml` key scenario_director.system. `_TOPIC` currently requires keyword/response and optional effect_verb/effect_reference. `world/quests/scene_package.py::PhaseTopic` duplicates this shape; `_validate_dialogue` builds it. `world/rules/dialogue.py::_generated_dialogue_for_key` extracts `(topic.keyword,topic.response)`. `story_effects.py::effect_for_keyword/_resolve_context/apply_story_effect` authorizes commission effects; `story_dialogue.py::transition_story_dialogue` owns committed fact/revision phase selection. These exact seams require cutover, not future discovery tasks.

## Goals / Non-Goals

Within one GPT-Luna workday, connect actual dream authoring dispatch to common scene definitions and the already completed selection/conditions/gates/reading/player pipeline. Five 60-90 minute units reuse existing owners; no new UI, state tables, quest engine, source-file writes, migration/shim or effect verbs. Preserve freeform generation and offline restored playback. Private source lore remains an implementation authoring prerequisite and was not read for planning.

## Decisions

### Exact generated schema and normalization

Shared contract v2 is authoritative. Keep role dialogue entries `{role_id,initial_phase,phases}` and each phase's existing exact fields `phase_id,conditions,greeting,topics,freeform_situation,freeform_goals,offline_response`. Phase conditions keep their existing deterministic observation language. Replace topics with exact common topic primitives, except generated authoring `topic_id`, `scene_id` and predecessor strings are local IDs matching `[a-z][a-z0-9_]{0,31}`. Topic required/optional fields, conditions, variants, refusal, lines, actor-first and byte budgets match the common codec. Allow <=16 topics per phase; retain existing bounded phase/role counts. Reject old response/effect_verb/effect_reference fields.

Add OPTIONAL phase `topic_effects` (default []) with exact rows `{topic_id,verb,reference}`. topic_id is a unique declared local topic. Verb is only existing offer_commission; reference must match that role's declared commission definition. Effect-bearing topics must be qualified and provide a safe refusal scene, including hidden topics that later qualify but fail deterministic domain authority. Common hidden refusal is retained as data and never projected while ineligible. Static YAML cannot declare effects. Conditions/variants never alter effects. Pre-delivered pure-chain nodes carry no effect or affinity; their informational selected root may retain its existing selection effect, which is never attached to successors.

Replace PhaseTopic with shared AuthoredTopic; DialoguePhase stores `topics:tuple[AuthoredTopic,...]` plus frozen `topic_effects`. At compile time `GeneratedDialogueIdentity(package_id,role_id,phase_id)` namespaces local topic/scene/predecessor IDs using the common g: base64url codec. The original canonical proposal payload retains local IDs in immutable DB JSON; revalidation deterministically reconstructs identical full IDs, with no dependence on display names, object dbids or mutable persona. Include dialogue schema/bytes in existing content identity computation so differing dialogue cannot overwrite an immutable package identity. Reject duplicate/cross-phase/dangling/cyclic IDs before publication.

### Production prompt, schema and permitted references

Add a dedicated prompt-library key `scenario_director.scene_system` in existing prompts/scenario_director.yaml and `build_scene_scenario_prompt(context)` alongside the generic prompt builder. The scene route uses this complete extended-blueprint schema instruction, actor-first speech/narration examples, all condition kinds/field bounds, variants, qualification/refusal, chains and existing allowlisted effects. Generic QuestBlueprint prompt/degrade behavior stays unchanged. Reuse the deterministic name-inspiration bank; no embedded duplicate prompt prose in Python. Update prompt shipment/contracts and existing prompt documentation at apply time.

`quest_beats.quest_context` adds bounded immutable `dialogue_references` to the captured scene planning frame, populated by deterministic canonical readers for permitted race/social/item/skill/rank/stage/quest/preset/profile labels. Package-local role/quest references resolve from the proposed package itself at compile time, never by inventing global registry entries. Package-only CompanionPresent uses source_kind package_role and role_id; QuestIs may reference the current compiled package quest. No private location, hidden phase body or private affinity numeral goes into this public reference catalog. Keep all existing confirmed requirements and permitted role knowledge context unchanged. `dispatch_runner._advance` captures the frame; generation uses the scene-specific builder and exact inline EXTENDED_BLUEPRINT_SCHEMA; checkpoint retains full scene/condition/effect declarations. `to_scene_package` must preserve these nested bytes unchanged. Semantic validation and final deterministic compiler both reject unknown/out-of-permission references. State publication still rechecks captured quest_context before commit. No template filler is introduced for disabled scene generation.

The common scene schema fragment belongs in pure world/lore/dialogue/codec.py and is reused by packages.py and the deterministic parser. AI imports that pure module, never world/quests writers. Keep package envelope/phase fact schemas owned by their current packages. No duplicated common validator or import-boundary exemption for a writer.

### Atomic publication and trusted runtime provider

`scene_package._validate_dialogue` invokes common parse/validate against its package identity and permitted reference catalog, then verifies external topic_effects/role commission scope and every possible scene/public bundle byte budget. Entire package validates before existing encounters.publish_scene_package transaction; scene_store.publish_package remains immutable/idempotent/conflict-rejecting. Faults roll back durable rows, commission grants, views and dispatch publication references through existing publication_scope. Publication never activates roles, accepts quests or applies dialogue effects. No private/generated dialogue is inserted into the static snapshot or written to git/source directories.

Implement generated branch of `dialogue_sources.resolve_dialogue_source`: re-resolve trusted package_id+role_id binding, published status, role capability and current selected phase/revision. Return common AuthoredDialogue and effects association, stable host_key, source identity. Replace `_generated_dialogue_for_key` response extraction with this complete scene provider and migrate every caller/test fixture. Remove PhaseTopic, MAX_TOPIC_RESPONSE and obsolete generated response/keyword-action APIs; keep existing generated host-binding format where it identifies the trusted package/role, not as topic identity. Never require NpcProfile membership for a generated role.

Text and web select `select_authored_topic` by stable ID, with identical composed topic/context/request payload, before qualification/effects. Shared conditions, hints, hidden/locked/open, variants, pure-chain receipts, unread observation, completion persistence, notifications and useAuthoredScene run unchanged. Preserve scene-specific reference catalog in context on server only. All Python/UMD/Vue/session/action/reading validators already accept the v2 source-aware <=2048 ID union; this slice tests actual maximal Unicode source components and keeps full ID bytes in every receipt/wire field. Full Scene <=8192 bytes, delivery+bundle <=16384, panel <=24576, envelope conditional allowance <=98304 remain unchanged. Oversize is pre-effect rejection, never truncation.

### Effect authority, protected content and invalidation

Replace effect_for_keyword with `effect_for_topic(npc,topic_id,context)` and migrate apply_story_effect/_resolve_context and callers to topic identity plus expected phase revision. Recheck source binding, current phase, qualification, commission declaration/registered issuer and all existing possession/domain authority immediately before settlement. No model-invented verb/reference, new reward, automatic affinity or knowledge mutation. Informational selections retain existing capped host-to-owner talk affinity; effect topics never add talk affinity. Operational/domain refusal returns safe refusal/rejection without protected success body or formal receipt. Successful existing story effect and delivery/session receipt commit atomically with owning quest/Attribute cache compensation. A fault after quest acceptance rolls back acceptance/session and in-memory surfaces. Retry selection_id/replay/completion never repeats effects.

Existing transition_story_dialogue still accepts only committed exact provenance/expected revision, including escort/reunion guards. Its _refresh_sessions/refresh_dialogue_phase route through sole-writer context retirement and the common refresh hooks before new phase choices. Cancelled packages and changed role binding invalidate replay/receipt/notification scope; no stale phase body or old freeform reply/memory is appended. Stable package-role host_key plus phase-scoped topic IDs retain reading across save/reload or a later return to the same phase. Filter completed IDs and batch payloads to currently permitted phase. Freeform uses the existing selected phase's permitted situation/goals/offline_response, not all variants/locked bodies/private authoring or another phase.

## Exact targets

- `world/lore/dialogue/codec.py` common schema fragment/identity reuse
- `world/ai/scenario_director/{packages,prompt,generation}.py`, including _TOPIC/_PHASE/PACKAGE_PAYLOAD_SCHEMA/EXTENDED_BLUEPRINT_SCHEMA and generate_beat_scene_blueprint
- `prompts/scenario_director.yaml`, existing prompt shipment tests/docs
- `world/narrative/quest_beats.py::{quest_context,to_scene_package,publish_quest_beat,_publish_scene_package}`
- `world/narrative/dispatch_runner.py::{_advance,_publish}` checkpoint/schema preservation
- `world/quests/scene_package.py::{PhaseTopic,DialoguePhase,_validate_dialogue}`, `encounters.py::publish_scene_package`, `scene_store.py::{publish_package,cancel_package,bind_role}`
- `world/rules/dialogue_sources.py`, `dialogue.py::{_generated_dialogue_for_key,generated_dialogue_for,refresh_dialogue_phase}` and all old generated response callers
- `world/rules/story_effects.py::{effect_for_keyword,_resolve_context,apply_story_effect}`
- `world/quests/story_dialogue.py::{transition_story_dialogue,_refresh_sessions}`
- Existing generated fixtures/tests in world/quests, world/ai, world/narrative; new focused `world/quests/tests/test_generated_dialogue_scenes.py`; one generated scene browser method in `web/tests/browser/test_browser_exploration_dialogue.py`; existing docs/game/commands.md and ownership manifests

An already-published immutable package whose dialogue parses only to the removed `PhaseTopic.response` shape resolves to no dialogue source: the trusted provider returns `None` for that role, so the host behaves as non-conversable for formal topics, one `dialogue_source_rejected` boundary event reports the package/role identity, and no partial or converted delivery is produced. Presence, movement and native service output are unaffected, and nothing rewrites the immutable row.

## Risks / Trade-offs

Broad existing seams are bounded by reuse: no new player/condition/reading implementation in this slice. All shared engine changes are completed prerequisites, avoiding parallel edits to half-finished backends. Model output may be invalid or exceed total transport budgets; current bounded diagnostics/retries/no-content behavior remains. Generated old payloads are intentionally unsupported after cutover, with no data migrations or aliases.

## Planned end-to-end acceptance

Start from a confirmed dream request with a new conversable role. Drive actual dispatch_runner.run_next with injected fake story/scenario clients, inspect scene-specific prompt and inline schema, checkpoint, publish one immutable DB package and activate its existing role through the real encounter path. With model services now disabled, open/select the actual generated host through web and text. Exercise actor-first multi-line speech/narration/variants, every shared condition family, package-scoped companion/quest reference, hidden/locked sentinel absence from all surfaces/freeform, safe effect refusal, one authorized commission effect, duplicate/replay rollback, pure-chain completion/refusal exclusion, owner/possession sharing and deferred unlock. Save/reload preserves payload/IDs/reading and replay begins line one without a second effect. Commit a guarded phase transition and reject stale selection/completion/freeform work; returning to the prior phase preserves its reading. Verify no generated file or static-registry row exists. Use one focused real browser method for generated multi-line attribution/refusal/reading/reconnect using that persisted fixture.

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.quests.tests.test_generated_dialogue_scenes world.quests.tests.test_story_effects world.quests.tests.test_story_dialogue world.narrative.tests.test_dream_dispatch_runner world.ai.tests.test_scenario_director_package
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_dialogue
uv run --locked python -m tools.contract_gate
```

Use untracked .env.test with MUD_TEST_SETTINGS=1 only at apply time. Commands are planned, not exercised during planning. Parent owns final review/gates/commits.
