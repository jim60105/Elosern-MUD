# scene-flavor-layer

## Why

The `scene_builder` LLM profile has been registered since `scene-builder` but has no consumer —
the master design's §3.1 amendment reserves it as a seam for a future generative scene-flavor
layer. Quest scenes currently get only the deterministic one-line scene sentence as their
description; there is no atmospheric, story-echoing flavor text, and the seam is dormant.

## What Changes

- **Add the `scene_builder.yaml` prompt file.** New `scene_builder.system` prompt key with four
  placeholders (`{scene_sentence}`, `{quest_context}`, `{room_name}`, `{region}`), registered and
  validated through the existing prompt-library mechanism.
- **Add a generative scene-flavor layer in `world/ai/`.** A pure module (no typeclass, no state
  writer, no live transport) registered with the guardrail: bounded plain-text output schema,
  semantic validation (length bounds; any digit character rejects), bounded retry, and a stable
  degrade-to-None fallback. It is the first consumer of the existing `scene_builder` profile.
- **Define the deterministic input-context contract.** The layer accepts bounded context fragments
  (archetype scene sentence, quest name/type, room name, region) supplied by the caller — the
  generative layer never touches entities or state.
- **No gameplay or state change yet.** Application (scheduling, writing, pushing) is owned by the
  subsequent `scene-flavor-apply` change.

## Capabilities

### New Capabilities
- `scene-flavor`: The generative scene-flavor layer — prompt contract, bounded context input,
  deterministic output validation (length and no-digit gates), retry, and offline-safe
  degrade-to-none.

### Modified Capabilities
- `prompt-library`: The prompt-file enumeration and registry requirement gains `scene_builder.yaml`
  and the `scene_builder.system` key with its placeholder allowlist.

## Impact

- New: `prompts/scene_builder.yaml`; a new layer module under `world/ai/` (e.g.
  `world/ai/scene_flavor.py`) with its own tests; guardrail registration for the new layer.
- Modified: `world/prompts/registry.py` (new `PromptSpec` entry).
- Unchanged: `world/ai/profiles.py` (the `scene_builder` profile already exists in `LAYER_NAMES`
  and `default_profiles()`), `world/quests/scene_builder.py`, room descriptions, the look path.
- No new dependencies; `FakeLLMClient` covers all tests.
