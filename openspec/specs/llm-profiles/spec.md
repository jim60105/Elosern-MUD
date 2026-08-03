## Purpose

Defines the per-layer LLM profile registry contract: a frozen, strictly validated profile per generative layer, with structured output opt-in and local disablement.

## Requirements

### Requirement: Per-layer profile registry
`world/ai/profiles.py` SHALL define a frozen `LLMProfile` dataclass and a `LLM_PROFILES` registry read from the Django settings. The registry SHALL map the four layer names `narrator`, `npc_dialogue`, `scenario_director`, and `scene_builder` to exactly one profile each. Each profile SHALL carry `base_url`, `path`, `headers`, `model`, `temperature`, `max_tokens`, `timeout_seconds`, `max_retries`, `supports_response_format`, and `enabled`. Layer keys outside the fixed set SHALL be rejected.

#### Scenario: Every layer resolves to a complete profile
- **WHEN** a consumer requests the profile for any of the four layer names
- **THEN** the registry returns a frozen profile with a base URL, chat path, model name, bounded temperature and max tokens, a timeout, a retry budget, a structured-output capability flag, and an enabled flag

#### Scenario: Unknown layer keys are rejected
- **WHEN** a consumer requests a profile for a key outside the four known layers
- **THEN** profile resolution raises a named error and no partial or default profile is returned

### Requirement: Startup profile validation is strict
Profile values SHALL be validated at settings/registry construction time. `temperature` SHALL be a finite number in `0..2`; `max_tokens` and `timeout_seconds` SHALL be positive integers; `max_retries` SHALL be a non-negative integer; `base_url` and `path` SHALL be non-empty strings; `model` SHALL be a non-empty string; `enabled` and `supports_response_format` SHALL be booleans. `headers` SHALL be an immutable `Mapping[str, tuple[str, ...]]` (or equivalent frozen representation) whose keys and string values SHALL be validated at construction time; the profile SHALL NOT expose the caller's original mutable dict. A profile failing any bound SHALL fail closed at construction rather than being silently clamped, and SHALL report which layer and field failed.

#### Scenario: Out-of-range sampling fails construction
- **WHEN** a profile declares a temperature outside `0..2` or a negative timeout
- **THEN** registry construction fails with a named error naming the layer and field, and no usable profile is installed

#### Scenario: Non-numeric token bounds fail construction
- **WHEN** a profile declares a non-integer `max_tokens` or a boolean where a bound integer is required
- **THEN** registry construction fails with a named error and the layer is unavailable rather than auto-corrected

#### Scenario: Headers are validated and frozen
- **WHEN** a profile supplies headers whose keys or values are not strings, or mutates the source dict after construction
- **THEN** construction fails for the invalid profile, and a successfully constructed profile holds an immutable copy that the caller's original dict cannot change

### Requirement: Structured output is opt-in per layer
A profile SHALL request `response_format` / json-schema structured output only when its `supports_response_format` flag is true. Profiles that do not declare the capability SHALL be called without any structured-output hint, so that backends which reject the field remain usable.

#### Scenario: Capable profile requests structured output
- **WHEN** a guarded call runs under a profile with `supports_response_format: true`
- **THEN** the request includes a structured-output hint bounded by the profile's declared schema support

#### Scenario: Incapable profile never sends the hint
- **WHEN** a guarded call runs under a profile with `supports_response_format: false`
- **THEN** the request body contains no `response_format` field and still completes as an ordinary chat completion

### Requirement: Profiles are locally disableable
A profile with `enabled: false` SHALL be treated as offline without making any network request. Guarded calls governed by a disabled profile SHALL short-circuit directly to that layer's degrade path, and the client SHALL NOT be invoked.

#### Scenario: A disabled profile short-circuits to degrade
- **WHEN** a guarded call runs under a profile with `enabled: false`
- **THEN** the call returns the layer's degrade fallback without any attempt to reach the endpoint

#### Scenario: Every registered guarded call is offline-safe when disabled
- **WHEN** all four `LLM_PROFILES` entries are disabled and any registered guarded call is invoked
- **THEN** each call returns its injected degrade fallback, no network request is made, and no state changes
