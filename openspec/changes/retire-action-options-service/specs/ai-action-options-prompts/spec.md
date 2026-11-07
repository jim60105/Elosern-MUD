## REMOVED Requirements

### Requirement: prompts/action_options.yaml ships the system and user prompt keys
**Reason**: `prompts/action_options.yaml` is deleted with the retired action-options layer; no generative layer consumes those keys.
**Migration**: None. The prompt library keeps every other layer's keys.

### Requirement: The registry declares the action_options entries with an exact placeholder allowlist
**Reason**: The two `PromptSpec` entries are deleted with the prompt file, so no allowlist entry remains for a layer that does not exist.
**Migration**: None.

### Requirement: LAYER_NAMES gains the action_options slot with structured-output defaults
**Reason**: The `action_options` profile slot is deleted from `LAYER_NAMES` and `default_profiles()`; the layer registry maps the six remaining generative layers.
**Migration**: `llm-profiles` states the six-layer registry contract.

### Requirement: Construction-time validation rejects a structured-output-disabled action_options profile at settings load
**Reason**: The per-layer required-flag rule existed solely to force `action_options.supports_response_format`; with no such layer there is no required flag and the mechanism is deleted.
**Migration**: None.
