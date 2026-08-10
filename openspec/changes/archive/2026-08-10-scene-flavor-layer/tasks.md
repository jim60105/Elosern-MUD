## 1. Prompt library

- [x] 1.1 Add `prompts/scene_builder.yaml` with `schema_version: 1` and the
      `scene_builder.system` key: Traditional Chinese atmosphere prose, 50–200 characters,
      atmosphere/senses only, never invent entities/numbers/world state, plain-text output.
- [x] 1.2 Register `PromptSpec("scene_builder.system", "scene_builder.yaml",
      ("scene_sentence", "quest_context", "room_name", "region"))` in
      `world/prompts/registry.py`.
- [x] 1.3 Add/extend prompt-library tests: the file list includes `scene_builder.yaml`; the
      `scene_builder.system` key validates with exactly the four placeholders; an unknown
      placeholder in the file is a load-time error.

## 2. Scene-flavor layer module

- [x] 2.1 Create `world/ai/scene_flavor.py` following the narrator module pattern: module
      constants for bounds (min 50 / max 200 flavor length, per-field caps), the frozen
      `SceneFlavorContext` dataclass, `_cap_string` capping of context fragments.
- [x] 2.2 Implement `build_scene_flavor_prompt(context)` returning a deterministic (system, user)
      pair: system renders `scene_builder.system` with the four capped values; user serializes the
      bounded structured context with stable sorted JSON and `ensure_ascii=False`.
- [x] 2.3 Implement the four semantic validators (`flavor_non_empty`, `flavor_bounded_length`,
      `flavor_has_cjk` — at least one CJK Unified Ideograph, mirroring the narrator gate, and
      `flavor_no_digits` — any ASCII/Unicode decimal digit rejects) and the
      `_SCENE_FLAVOR_DEGRADED` sentinel fallback.
- [x] 2.4 Implement `register_scene_flavor()` with the narrator's idempotent, atomic registration
      and identity-based uninstall-on-partial-failure pattern, plus `_is_registered` /
      `_require_registered`. Add the `_register_scene_flavor_layer()` boot-tolerant seam in
      `server/conf/at_server_startstop.py` (mirroring `_register_character_creation_layer`), called
      from `at_server_start` after the other layer registrations.
- [x] 2.5 Implement `generate_scene_flavor(context, client)` (Deferred → `str | None`): rejects an
      explicit `None` client with a named error, requires registration, builds the prompt, runs
      `guarded_call("scene_builder", client, descriptor)` (the guardrail and profile registries key
      strictly by `LAYER_NAMES`, so the layer key is the `scene_builder` profile name), maps the
      sentinel to `None`, and catches `PromptUnavailableError` to `None`.

## 3. Tests

- [x] 3.1 Pure tests (`unittest.TestCase`, FakeLLMClient): valid flavor resolves; digit-containing
      flavor rejects and retries then degrades; non-Chinese flavor rejects; under/over-length
      rejects; exhaustion resolves `None`; explicit `None` client raises before any work; identical
      context yields byte-identical prompts; capped context stays within bounds;
      `PromptUnavailableError` degrades to `None`.
- [x] 3.2 Guardrail registration tests: idempotent re-registration; partial-failure rollback leaves
      no half-installed hooks; disabled `scene_builder` profile short-circuits to `None` with no
      network request.
- [x] 3.3 Update the `world/ai` transport-boundary contract test to cover `scene_flavor.py` (no
      state writer, no typeclass, no live transport, no socket imports).
- [x] 3.4 Write the substantive behavior tests above first; add `covers_requirement` annotations
      for the new `scene-flavor` requirements and the `prompt-library` delta scenario only after
      the change is archived and the canonical requirement IDs exist in the main specs (then run
      `uv run --locked python -m tools.spec_traceability check`).

## 4. Docs and validation

- [x] 4.1 Run `uv run --locked python -m world.prompts.validate` to confirm the new prompt file
      validates.
- [x] 4.2 Run `uv run --locked openspec validate scene-flavor-layer --strict` and confirm all
      artifacts pass. At archive time: sync the delta specs into the main specs, add the
      `covers_requirement` annotations from task 3.4, and run
      `uv run --locked python -m tools.spec_traceability check`.
