# env-overridable-llm-profiles

## Why

The profile registry is only reachable through `secret_settings.py` except for one
`OLLAMA_BASE_URL`-derived base URL, and its built-in model name (`llama3.2`) matches no
realistic vLLM `--served-model-name`, so every guarded call to a non-Ollama endpoint
degrades (the concept seam always answers `concept_unavailable`) with no knob to fix it.
Every other deployment knob in this repository is already environment-overridable with
fail-closed boot validation; the LLM surface is the one gap.

Design source: `docs/superpowers/specs/2026-09-01-llm-endpoint-configuration-design.md`
(decisions C-1..C-5, C-7, C-10).

## What Changes

- `server/conf/settings.py` gains a declarative knob table generating one global
  `LLM_<SUFFIX>` environment variable and one `LLM_<LAYER>_<SUFFIX>` per-layer override
  per knob, read through the existing `_env_*` fail-closed helpers (a new omittable
  variant yields `None` for unset optional knobs).
- **BREAKING** `LLM_BASE_URL` replaces `OLLAMA_BASE_URL` everywhere (compose.yaml,
  `.env.example`, container contract test, inventory allow-list, docs). No alias:
  the project has zero released users.
- `world/ai/profiles.py` becomes environment-free: `default_profiles(defaults=None)`
  accepts injected overrides instead of reading `os.environ`; `server/conf/settings.py`
  is the sole environment reader (C-1).
- `LLMProfile` gains typed, strictly validated, optional fields that are *stored* by this
  change and *serialized* by the follow-up change `llm-endpoint-wire-configuration`:
  `api_key` (frozen field excluded from `repr`), `app_title`, `app_url`,
  `frequency_penalty`, `presence_penalty`, `top_k`, `top_p`, `repetition_penalty`,
  `min_p`, `top_a`, `reasoning_enabled` (tri-state), `reasoning_effort` (closed set),
  `reasoning_style` (closed set, default `openrouter`), `max_completion_tokens` (C-4).
- `validate_profile_values` bounds every new field (finite floats, closed sets,
  positive ints); construction still fails closed naming layer and field.
- `server/conf/test_settings.py` sanitizes every generated `LLM_*` name from
  `os.environ`, so tests never inherit shell configuration.
- Effective precedence: code default < global env < per-layer env < `secret_settings.py`
  (unchanged final authority).
- Wire format is byte-identical to today's when no new knob is set: request bodies and
  headers are untouched by this change; the model name fix (already serialized today)
  lands with the model knob.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `llm-profiles`: profile fields gain the new optional typed set with construction-time
  bounds; defaults become injected rather than environment-read.
- `settings-environment-overrides`: the env-backed deployment surface gains the
  `LLM_*` knob family (global + per-layer generation), the `OLLAMA_BASE_URL` external
  reader entry is retired in favour of settings.py-only reading, and the test-settings
  sanitize list covers the generated names.
- `llm-client`: the "local-first default endpoint from the environment" requirement
  rebinds from `OLLAMA_BASE_URL` to `LLM_BASE_URL`.

## Impact

- `world/ai/profiles.py`, new `server/conf/llm_knobs.py` (inert knob table +
  `llm_env_names()`), `server/conf/settings.py`, `server/conf/test_settings.py`,
  `compose.yaml`, `.env.example`, `docs/development/settings-and-environment.md`
  (LLM knob table; full policy reversal stays with the follow-up change).
- Tests: `world/ai/tests/test_profiles.py`, `server/conf/tests/`
  (`test_env_overrides.py` inventory contract + per-knob boot validation),
  `tests/test_container_contract.py`; the new `server/conf/tests/test_llm_env_overrides.py`
  requires a same-change `.github/evennia-shards.json` ownership entry (exactly one shard).
- No DB, no persisted state, no command surface. Rollback removes the settings knob
  table and reverts the profile constructor signature.
- Depends on: nothing. Blocks: `llm-endpoint-wire-configuration` (serialization of the
  fields this change stores).
