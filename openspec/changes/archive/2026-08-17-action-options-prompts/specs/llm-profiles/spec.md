## MODIFIED Requirements

### Requirement: Per-layer profile registry
`world/ai/profiles.py` SHALL define a frozen `LLMProfile` dataclass and a `LLM_PROFILES` registry
read from the Django settings. The registry SHALL map the six layer names `narrator`,
`npc_dialogue`, `scenario_director`, `scene_builder`, `character_creation`, and `action_options`
to exactly one profile each. Each profile SHALL carry `base_url`, `path`, `headers`, `model`,
`temperature`, `max_tokens`, `timeout_seconds`, `max_retries`, `supports_response_format`, and
`enabled`. Layer keys outside the fixed set SHALL be rejected.

#### Scenario: Every layer resolves to a complete profile
- **WHEN** a consumer requests the profile for any of the six layer names
- **THEN** the registry returns a frozen profile with a base URL, chat path, model name, bounded
  temperature and max tokens, a timeout, a retry budget, a structured-output capability flag, and
  an enabled flag

#### Scenario: Unknown layer keys are rejected
- **WHEN** a consumer requests a profile for a key outside the six known layers
- **THEN** profile resolution raises a named error and no partial or default profile is returned

#### Scenario: The action_options profile requires structured output
- **WHEN** the effective `LLM_PROFILES` map is validated at settings load
- **THEN** the `action_options` layer's `supports_response_format` is true, or startup fails
  naming the layer and field — the one JSON-schema consumer cannot run without it