## ADDED Requirements

### Requirement: prompts/action_options.yaml ships the system and user prompt keys
`prompts/action_options.yaml` SHALL ship exactly the keys `action_options.system` and
`action_options.user` (schema_version 1, matching the existing prompt files' format). The system
key SHALL direct the model as a game-design curator for an adult single-player world proposing 3–5
actions in Traditional Chinese, always choosing `known_action` cards from the provided affordance
codes and using `freeform` only for speech a present person could plausibly be addressed with. The
user key SHALL carry the serialized context block. Both keys SHALL repeat the hard rules: no
numbers, no hidden values, no fabricated targets, cards reference only present people/places/things,
and exactly the documented JSON schema output (pipeline design doc §3).

#### Scenario: Both prompt keys resolve through the loader
- **WHEN** `world/prompts/loader.py` loads the prompt library
- **THEN** both `action_options.system` and `action_options.user` are present and non-empty

#### Scenario: The system prompt forbids hidden values
- **WHEN** the `action_options.system` text is inspected
- **THEN** it explicitly forbids numbers, hidden values, and fabricated targets

### Requirement: The registry declares the action_options entries with an exact placeholder allowlist
`world/prompts/registry.py` SHALL register `action_options.system` and `action_options.user`
`PromptSpec` entries with **different allowlists**: `action_options.system` SHALL have an empty
`allowed_placeholders` (its text is static role/hard-rule direction and must never carry context
tokens), and `action_options.user` SHALL have `allowed_placeholders` exactly equal to the
`ActionOptionsContext` fields of the pipeline design doc §2 (`room_name`, `room_summary`,
`npc_entries`, `monster_entries`, `objective`, `narrative_tail`, `affordances`), with `max_length`
bounds consistent with the other system prompts. The loader SHALL reject any `{token}` in the YAML
text not on the registered allowlist (typo like `{nmme}` fails validation), and the
registry/loader parity contract SHALL cover both new keys.

#### Scenario: A placeholder typo in action_options.yaml is caught
- **WHEN** the YAML text contains a `{token}` not in the registered allowlist
- **THEN** loader validation records a `PromptLibraryError` whose `problem` names the offending
  token (e.g. "unknown placeholder 'nmme'") and the allowed set

#### Scenario: The user allowlist matches the context fields exactly
- **WHEN** `action_options.user`'s `allowed_placeholders` are compared with the
  `ActionOptionsContext` field names
- **THEN** they are exactly equal — the parity contract test covers both new keys

#### Scenario: The system prompt carries no allowlisted tokens
- **WHEN** `action_options.system`'s `allowed_placeholders` are inspected
- **THEN** the allowlist is empty — a context token accidentally placed in the system text fails
  loading instead of being silently rendered

### Requirement: LAYER_NAMES gains the action_options slot with structured-output defaults
`world/ai/profiles.py` SHALL add `"action_options"` to `LAYER_NAMES`, and `default_profiles()`
SHALL emit its defaults with `temperature` 0.7, `max_tokens` sized for a 5-card JSON payload
(≈ 320), and `supports_response_format: true`. `server/conf/settings.py`'s
`LLM_PROFILES = default_profiles()` SHALL therefore expose the slot without an edit; a test SHALL
assert the effective profile for the new layer.

#### Scenario: The effective default profile supports structured output
- **WHEN** `build_profiles(default_profiles())["action_options"]` is inspected
- **THEN** `supports_response_format` is true and `max_tokens` is ≈ 320

### Requirement: Construction-time validation rejects a structured-output-disabled action_options profile at settings load
`world/ai/profiles.py` SHALL enforce a per-layer required-flag rule: building profiles with
`action_options.supports_response_format: false` SHALL raise `ProfileValidationError` naming the
layer and field. `server/conf/settings.py` SHALL validate the effective profile map at import time
(one `build_profiles(LLM_PROFILES)` call beside the existing
`LLM_PROFILES = default_profiles()`), so a misconfigured endpoint for the one layered
JSON-schema consumer fails **at startup** rather than at the first live call (pipeline design doc
§5). All other bounds and layers SHALL behave exactly as today.

#### Scenario: A disabled structured-output action_options profile fails at settings load
- **WHEN** the settings module is imported with an `action_options` entry carrying
  `supports_response_format: false`
- **THEN** startup fails with `ProfileValidationError` naming layer `action_options` and field
  `supports_response_format` — before any server command can run

#### Scenario: Other layers are unaffected
- **WHEN** the same validator builds a map with another layer's
  `supports_response_format: false`
- **THEN** it builds normally — only the action_options layer carries the requirement