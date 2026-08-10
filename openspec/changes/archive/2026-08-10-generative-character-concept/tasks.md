# generative-character-concept — Tasks

## 1. Prompt library activation

- [x] 1.1 Extend `world/prompts/registry.py`'s `character_creation.system` spec: allowlist gains
      `concept` and `race_catalog` placeholders; remove the forward-declared-seam comment
- [x] 1.2 Update `prompts/character_creation.yaml`: template text uses `{concept}` and
      `{race_catalog}`, keeps the adult framing, and states the output contract (only real
      registry keys, no numbers, no age)
- [x] 1.3 Add a `race_catalog` renderer (deterministic, registry-derived, hard size bound) that
      emits the bounded race/subrace and selectable-skill brief for the prompt; validate it
      against the prompt-library contract (no Python prompt constants)

## 2. Generative layer

- [x] 2.1 Add `character_creation` to `world/ai/profiles.py::LAYER_NAMES`; confirm
      `default_profiles()` in `server/conf/settings.py` constructs the profile without manual
      entries
- [x] 2.2 Create the `world/ai/` layer module for character creation: output jsonschema for the
      exact contract `{race_key, subrace_key, allocations, suggested_skills,
      persona{personality, life_story, habit}}`, semantic validators (race/subrace registry
      existence and compatibility, allocations inside race bands, skill keys in the skill
      registry, persona exactly three bounded text fields, no age field and no numeric field
      outside `allocations`), retry-with-appended-error, and the stable degrade fallback
      (生成不可用，請手動創角). Any persona shape or length failure rejects the whole proposal
- [x] 2.3 Register the layer through the guardrail's existing registration mechanism
      (`register_semantic_validator` / degrade fallback / schema), keeping `world/ai/` free of
      writer and typeclass imports
- [x] 2.4 Add the idempotent `character_creation` startup registration helper and call it from
      `server/conf/at_server_startstop.py::at_server_start()` alongside the existing layers;
      verify the layer is registered (and prompt-unavailable degradation works) under a real
      startup path
- [x] 2.5 Reuse `preflight_character_creation`-style checks for allocations/race validation where
      possible instead of duplicating band logic

## 3. Command surface

- [x] 3.1 Add `character concept <構想>` (aliases 構想) to the pending-character command set:
      bounded concept input validation (empty/over-bound rejected with a named error, no
      generative call), guarded pipeline invocation with the injected client, proposal summary
      presentation (race/subrace/allocations, suggested skills and persona as informational
      preview), interactive collection of display name and both ages through the existing prompts
      and the adult gate, and activation through the ordinary `CharacterCreationRequest` path
- [x] 3.2 Confirm the ordinary custom flow, activation semantics, and the adult gate are untouched
      (no new path around them); no draft, persona, or suggested-skill persistence in this change
- [x] 3.3 Update `docs/game/commands.md`, `docs/game/command-reference.md`, and
      `tests/test_command_docs.py` for the new command surface

## 4. Tests

- [x] 4.1 Layer tests with `FakeLLMClient` replays: valid proposal accepted; unregistered
      race/subrace/skill keys rejected and retried; out-of-band allocations rejected; age or
      extra numeric fields rejected; invalid persona (missing/extra field, over-length) rejects
      the whole proposal; non-JSON/schema-invalid output for every retry degrades without
      touching the DB
- [x] 4.2 Command integration tests: concept → summary → interactive name/ages → activation;
      underage entered values rejected by preflight; empty/over-bound input rejected before any
      call; offline degrade message with no character/account state change; deterministic
      preset/custom flows still work
- [x] 4.3 Startup test: `at_server_start()` installs the `character_creation` schema, validators,
      and degrade fallback; a broken `character_creation.system` key degrades the layer without
      blocking startup
- [x] 4.4 Prompt-library tests: `character_creation.system` allowlist contains `concept` and
      `race_catalog`; template text lives only in `prompts/*.yaml`
- [x] 4.5 Offline-playability regression: with every LLM profile failing, `character concept`
      degrades cleanly and the full deterministic creation flow still completes

## 5. Traceability and verification

- [x] 5.1 Annotate the discoverable tests covering the new and modified requirements with
      `covers_requirement` using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`
- [x] 5.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the
      generative-character-concept, character-creation-ux, and prompt-library requirements are
      covered
- [x] 5.3 Run the focused test packages (world ai, world prompts, commands creation tests) and
      confirm green; keep `git diff --check` clean
