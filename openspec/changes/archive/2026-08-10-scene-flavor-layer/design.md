# scene-flavor-layer — Design

## Context

The `scene_builder` LLM profile is registered in `world/ai/profiles.py` (`LAYER_NAMES` includes
it, and `default_profiles()` generates a settings entry for every layer name), but nothing consumes
it. The master design (§3.1 amendment) reserves it as a seam for a future generative scene-flavor
layer. Quest scenes are materialized by the deterministic SceneBuilder (`world/quests/
scene_builder.py`), which writes `room.db.desc` from the requirement's `scene_sentence` or the
archetype's `scene_sentence` — a single deterministic sentence with no atmosphere prose.

The project has a proven layer pattern to mirror: `world/ai/narrator.py` and
`world/ai/npc_dialogue.py` are pure modules (no state writer, no live transport, no socket), take
an injected client, build a deterministic prompt from bounded inputs, run through the guardrail
(`guarded_call` with per-layer semantic validators and a degrade fallback sentinel), and resolve
their sentinel to a deterministic fallback at the entry point. `world/ai/schemas/
ChatRequestDescriptor` carries the message pair; `FakeLLMClient` covers all tests.

This change builds the layer only. Scheduling, writing, and pushing the flavor to players are
deliberately owned by the subsequent `scene-flavor-apply` change so each change stays one working
day and independently verifiable.

## Goals / Non-Goals

**Goals:**
- Add a pure, guardrail-registered `scene_builder`-profile generative layer that turns a bounded
  scene context into a Traditional Chinese atmosphere paragraph.
- Add `prompts/scene_builder.yaml` with the `scene_builder.system` key and its four placeholders,
  wired into `world/prompts/registry.py` with an exact placeholder allowlist.
- Deterministically validate output: non-empty, 50–200 characters, and **no digit characters**
  (the mechanical "no fabricated numbers" gate).
- Degrade to `None` on any failure (offline, disabled profile, transport, validation exhaustion,
  prompt unavailability) with no state change and no network call under a disabled profile.
- First consumer of the existing `scene_builder` profile; testable entirely with `FakeLLMClient`.

**Non-Goals:**
- No scheduling, writing, or pushing of flavor (scene-flavor-apply).
- No room/description/`look` changes.
- No changes to `world/ai/profiles.py` or `llm-profiles` requirements (the profile already exists).
- No player identity or live entity data in the prompt context.
- No JSON output contract — the flavor is plain text (a JSON shape would invite fabricated
  structure; plain text with a length/digit gate is simpler and sufficient).

## Decisions

### D1: The layer mirrors the narrator/npc_dialogue module pattern
`world/ai/scene_flavor.py` with: module constants for bounds, `_cap_string` capping of context
fragments, a frozen `SceneFlavorContext` dataclass, `build_scene_flavor_prompt(context)` pure
function, semantic validators registered under the `scene_builder` layer key (the guardrail and
profile registries key strictly by `LAYER_NAMES`, so the layer key is the profile name, never a
separate `scene_flavor` key), a `_SCENE_FLAVOR_DEGRADED` sentinel fallback,
`register_scene_flavor()` (idempotent, atomic, identity-based uninstall on partial failure —
exactly the narrator pattern), and `generate_scene_flavor(context, client)` entry point rejecting
an explicit `None` client.

Rationale: every existing layer follows this shape; consistency keeps the transport-boundary
contract test (no imports of state writers, typeclasses, or sockets from `world/ai`) trivially
green. Alternative considered: a bespoke non-guardrail call path — rejected because it would
bypass retry-with-error and the per-layer degrade contract the project already owns.

### D2: Prompt contract — `scene_builder.system` with four allowlisted placeholders
`prompts/scene_builder.yaml` declares `schema_version: 1` and one key, `scene_builder.system`,
whose text instructs: Traditional Chinese atmosphere prose, 50–200 characters, describe
atmosphere/senses only, never invent entities, numbers, or world state, output plain text only.
`world/prompts/registry.py` gains
`PromptSpec("scene_builder.system", "scene_builder.yaml", ("scene_sentence", "quest_context",
"room_name", "region"))`. The system message renders with the four fragments; the user message
carries the bounded structured context (stable sorted JSON, `ensure_ascii=False`), mirroring
npc_dialogue's split (role instruction in system, data in user).

Rationale: the prompt library is the sole prompt-text source (prompt-library requirement); the
allowlist catches consumer typos and unknown tokens at load time. Alternative considered: an
art-style template key — rejected; flavor is a distinct domain from art prompts.

### D3: Input context is bounded and deterministic
`SceneFlavorContext` (frozen) carries `scene_sentence`, `quest_context` (the quest's name/type
rendered as one bounded string), `room_name`, and `region`; every field is capped with the
project's `_cap_string` idiom before rendering. Identical context produces byte-identical
(system, user) pairs. The caller (future scene-flavor-apply) is responsible for supplying these
fragments from deterministic sources; the layer never touches entities or registries.

Rationale: mirrors narrator's bounded serialization; prevents unbounded prompts; keeps the module
pure.

### D4: Output gates — non-empty, 50–200 characters, CJK, no digits
Four semantic validators: `flavor_non_empty`, `flavor_bounded_length` (min 50, max 200 —
constants at module top), `flavor_has_cjk` (at least one CJK Unified Ideograph, mirroring the
narrator's prose gate), and `flavor_no_digits` (rejects any Unicode decimal digit character).
Validation failure appends the error message and retries under the profile's retry budget;
exhaustion resolves the sentinel → `None`.

Rationale: the digit gate is the mechanical enforcement of "no fabricated numbers" (design B4) —
a flavor paragraph with `"3 隻狼"` or `"500 金幣"` is impossible without a digit. The CJK gate
keeps the Traditional Chinese player-facing surface even when the model drifts to another
language (narrator precedent). The 50-char minimum forces the flavor to be a real paragraph rather
than a one-word echo. Alternatives considered: jsonschema output — unnecessary for plain text;
semantic number-pattern rejection — weaker than the digit gate.

### D5: Degrade-to-`None` is the layer's only pipeline-failure outcome
Disabled profile (enabled: false), offline transport, retry exhaustion, prompt unavailability
(`PromptUnavailableError`), and explicit `None` client all resolve to `None` with no state change.
The entry point returns a Deferred resolving to `str | None`; no exception escapes from the guarded
pipeline except the named client-required error. Calling before the hooks are registered errbacks
with the named `SceneFlavorNotRegisteredError` (a registration-precondition error, exactly the
narrator/npc_dialogue/character_creation convention — never a silent degrade).

Rationale: the deterministic game must remain fully playable with the LLM offline; `None` is the
"no flavor" outcome the apply change consumes.

### D6: Prompt failure never blocks server startup
The new key's validation failure behaves like every other prompt key (prompt-library
requirement): the key is marked unavailable, the layer degrades to `None`, and startup continues.
No special case for the forward-declared seam is needed because the layer is the consumer now.

### D7: The layer is registered at server startup like every other layer
`server/conf/at_server_startstop.py` gains a `_register_scene_flavor_layer()` boot-tolerant seam
(mirroring `_register_character_creation_layer`) invoked from `at_server_start` after the other
layer registrations, so the guardrail hooks are installed for the future scene-flavor-apply
consumer exactly as narrator/npc_dialogue/scenario_director/character_creation are. A foreign
leftover registration must never abort startup; the flavor gate still fails loudly on a
non-scene-flavor registration.

### D7: The layer is registered at server startup like every other layer
`server/conf/at_server_startstop.py` gains a `_register_scene_flavor_layer()` boot-tolerant seam
(mirroring `_register_character_creation_layer`) invoked from `at_server_start` after the other
layer registrations, so the guardrail hooks are installed for the future scene-flavor-apply
consumer exactly as narrator/npc_dialogue/scenario_director/character_creation are. A foreign
leftover registration must never abort startup; the flavor gate still fails loudly on a
non-scene-flavor registration.

## Risks / Trade-offs

- [The 50-char minimum may reject valid short flavors] → Retry may also fail; the outcome is
  `None` (no flavor), never a broken room; the bound is a module constant, tunable without code
  structure changes. Whether the minimum causes unnecessary degrades in practice is a tuning
  question to measure once a real profile is exercised.
- [The digit gate may reject stylized flavor (e.g. "一縷煙") — no, only decimal digits are
  rejected; CJK numerals pass] → Validator only matches ASCII/Unicode decimal digits; Traditional
  Chinese numeric words are unaffected.
- [The prompt text is untested against a real model] → Out of scope by design; `FakeLLMClient`
  tests the pipeline; the prompt is data an admin can tune via the prompt library.
- [A second consumer could later need JSON or more context] → The layer's context dataclass and
  validators are internal; extending them is a delta to this same capability, not a rewrite.

## Migration Plan

No migration. The project is unreleased with zero users; the new prompt key, registry entry, and
layer module are additive. No settings change is needed (`scene_builder` profile already exists).
Rollback is deleting the new module, prompt file, and registry entry.

## Open Questions

- None blocking. Whether flavor should later vary by time of day or player presence is deferred
  to scene-flavor-apply and beyond; the context dataclass is the extension seam.
