## Why

The action-options generative layer (change `action-options-layer`) needs its shipped prompt text,
its registry contract, and its LLM profile slot. Without these, the layer has no sanctioned prompt
to render, the loader cannot police placeholder typos, and the profile cannot declare structured
output — the feature cannot run end-to-end.

## What Changes

- New `prompts/action_options.yaml` with `action_options.system` and `action_options.user` prompt
  keys (Traditional Chinese player-facing direction; hard rules: 3–5 actions, no numbers, no
  hidden values, no fabricated targets, present entities only, `{npc_index}` references).
- `world/prompts/registry.py` gains the two `PromptSpec` entries with an allowed-placeholder
  allowlist exactly matching the `ActionOptionsContext` fields of the pipeline design doc §2.
- `world/ai/profiles.py`: `LAYER_NAMES` gains the `action_options` slot; `default_profiles()`
  emits the layer defaults (`temperature` 0.7, `max_tokens` ≈ 320, `supports_response_format:
  true`); a per-layer required-flag rule makes construction reject
  `supports_response_format: false` for the action_options layer.
- `server/conf/settings.py`: one import-time `build_profiles(LLM_PROFILES)` validation call after
  every settings override (at the end of the module, past `secret_settings`), so a misconfigured
  slot fails at startup.
- `openspec/specs/llm-profiles` main contract gains a MODIFIED delta (the layer-enumeration
  requirement updates from the current five layer names to six, adding `action_options` —
  audit check: the codebase already has five layers incl. `character_creation`, which the main
  spec's stale four-name list omits).
- Registry/loader and profile tests updated to cover the new key and slot.

## Capabilities

### New Capabilities
- `ai-action-options-prompts`: shipped prompt text, registry placeholder contract, and the
  `action_options` LLM-profile slot with strict construction-time validation.

## Impact

- **New file:** `prompts/action_options.yaml`.
- **Modified:** `world/prompts/registry.py`, `world/ai/profiles.py`, `server/conf/settings.py`
  (one validation line); the `llm-profiles` main capability spec gets a MODIFIED delta — all
  registry-only/read-only data and contract surfaces.
- **Tests:** `world/prompts/tests/test_loader.py`, `world/prompts/tests/test_verbatim_shipment.py`,
  `world/ai/tests/test_profiles.py` (incl. re-annotated `covers_requirement` for the layer-set
  contract).
- **Dependencies:** change 1 `action-options-affordance-contract` (establishing the affordance
  vocabulary the prompt references in later changes); `server/conf/settings.py` is untouched but
  its `LLM_PROFILES = default_profiles()` result changes.
- **No backward compatibility:** unreleased project, zero users — no migrations or compatibility
  layers.