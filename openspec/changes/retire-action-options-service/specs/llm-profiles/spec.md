## MODIFIED Requirements

### Requirement: Per-layer profile registry
`world/ai/profiles.py` SHALL define a frozen `LLMProfile` dataclass and a `LLM_PROFILES` registry
read from the Django settings. The registry SHALL map the six layer names `narrator`,
`npc_dialogue`, `scenario_director`, `scene_builder`, `character_creation`, and
`title_nomination` to exactly one profile each. Layer keys outside the fixed set SHALL be
rejected. The `api_key` value SHALL be excluded from the dataclass `repr`.

#### Scenario: Every layer resolves to a complete profile
- **WHEN** a consumer requests the profile for any of the six layer names
- **THEN** the registry returns a frozen profile with a base URL, chat path, model name, bounded temperature and max tokens, a timeout, a retry budget, a structured-output capability flag, an enabled flag, and every optional endpoint-configuration field at its omit default (empty string or `None`)

#### Scenario: Unknown layer keys are rejected
- **WHEN** a consumer requests a profile for a key outside the six known layers, including the retired `action_options` key
- **THEN** profile resolution raises a named error and no partial or default profile is returned

#### Scenario: The action_options profile requires structured output
- **WHEN** the effective `LLM_PROFILES` map is validated at settings load
- **THEN** no `action_options` layer exists and no per-layer required-flag rule runs: the retired layer cannot be requested or overridden, and startup validation covers only the generic bounds of the six surviving profiles

#### Scenario: The per-layer code defaults survive
- **WHEN** all six profiles resolve from code defaults with no injected overrides
- **THEN** `title_nomination` carries its 640-token `max_tokens`, `scenario_director` carries its 8,192-token `max_tokens`, and the remaining layers carry the 250-token generic default

#### Scenario: The api key never reaches the profile repr
- **WHEN** a profile is constructed with a non-empty `api_key` and formatted with `repr()` or `str()`
- **THEN** the produced text does not contain the key value

#### Scenario: Profiles carry the full field set
- **WHEN** a profile is constructed
- **THEN** it carries `base_url`, `path`, `headers`, `model`, `temperature`, `max_tokens`,
  `timeout_seconds`, `max_retries`, `supports_response_format`, and `enabled`
- **AND** additionally the optional endpoint-configuration fields `api_key`, `app_title`, and
  `app_url` (each a string defaulting to the empty string), `frequency_penalty`,
  `presence_penalty`, `top_p`, `repetition_penalty`, `min_p`, and `top_a` (each a float or
  `None`), `top_k` and `max_completion_tokens` (each an int or `None`), `reasoning_enabled`
  (bool or `None`), `reasoning_effort` (a closed-set string or `None`), and `reasoning_style`
  (a closed-set string defaulting to `openrouter`)

#### Scenario: The api key exclusion keeps profiles loggable
- **WHEN** a profile is logged or debugged through its `repr`
- **THEN** the exclusion lets this happen without disclosing the credential

#### Scenario: The scenario_director default fits a full blueprint
- **WHEN** the `scenario_director` code default is constructed
- **THEN** it carries a 8,192-token `max_tokens` so a quest blueprint whose occupants carry
  complete compact cards fits one response
