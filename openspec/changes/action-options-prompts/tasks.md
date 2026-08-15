## 1. Prompt file and registry

- [ ] 1.1 Create `prompts/action_options.yaml` (schema_version 1) with `action_options.system` and
  `action_options.user` keys per the pipeline design doc §3: system = curator role, Traditional
  Chinese output, affordance-code discipline for `known_action`, `freeform` only as plausible
  speech, hard rules (no numbers, no hidden values, no fabricated targets, present entities only,
  3–5 actions, exact JSON schema output); user = serialized context block.
- [ ] 1.2 Register both `PromptSpec` entries in `world/prompts/registry.py` with
  `allowed_placeholders` exactly equal to the `ActionOptionsContext` fields (`room_name`,
  `room_summary`, `npc_entries`, `monster_entries`, `objective`, `narrative_tail`,
  `affordances`) and sensible `max_length` bounds.
- [ ] 1.3 Extend `world/prompts/tests/test_loader.py` (every-layer-has-a-prompt parity,
  placeholder allowlist checks: system = empty, user = seven context fields) and
  `test_verbatim_shipment.py` to cover both new keys; add a hostile fixture `prompts/tests/` whose
  `{nmme}`-style typo records a `PromptLibraryError` whose `problem` names "unknown placeholder"
  and the offending token.

## 2. Profile slot

- [ ] 2.1 Add `"action_options"` to `LAYER_NAMES` in `world/ai/profiles.py`.
- [ ] 2.2 Extend `default_profiles()` with the action_options defaults: `temperature` 0.7,
  `max_tokens` 320, `supports_response_format: true`, remaining fields shared with the
  local-first default.
- [ ] 2.3 Add a per-layer required-flag constant map and enforce it in `build_profiles`
  (raise `ProfileValidationError` naming layer and field on violation).
- [ ] 2.4 Add the import-time validation call in `server/conf/settings.py` beside
  `LLM_PROFILES = default_profiles()` (`build_profiles(LLM_PROFILES)`), so a disabled
  structured-output action_options slot fails at startup.

## 3. Tests and verification

- [ ] 3.1 `world/ai/tests/test_profiles.py`: action_options slot present in the effective
  profiles; defaults assert `supports_response_format == True` and `max_tokens == 320`;
  construction with `supports_response_format: false` for action_options raises
  `ProfileValidationError`; another layer with the flag false still builds; settings-import
  validation test proves the fail-at-startup path.
- [ ] 3.2 Update the `llm-profiles` layer-enumeration assertion in the profile/prompt tests and
  re-check `covers_requirement` annotations against `uv run --locked python -m
  tools.spec_traceability list` after sync (delta: six layer names).
- [ ] 3.3 Assert the effective `settings.LLM_PROFILES` exposes the slot (no other settings diff
  required).
- [ ] 3.4 Run the owned package tests:
  `uv run --locked evennia test --settings settings.py world.prompts.tests world.ai.tests.test_profiles`
  plus `uv run --locked python -m tools.spec_traceability check`; `git diff --check` clean.