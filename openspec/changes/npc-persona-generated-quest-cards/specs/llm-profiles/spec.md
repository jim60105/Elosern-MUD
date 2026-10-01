## MODIFIED Requirements

### Requirement: Per-layer profile registry
`world/ai/profiles.py` SHALL define a frozen `LLMProfile` dataclass and a `LLM_PROFILES` registry read from the Django settings. The registry SHALL map the seven layer names `narrator`, `npc_dialogue`, `scenario_director`, `scene_builder`, `character_creation`, `action_options`, and `title_nomination` to exactly one profile each. Each profile SHALL carry `base_url`, `path`, `headers`, `model`, `temperature`, `max_tokens`, `timeout_seconds`, `max_retries`, `supports_response_format`, and `enabled`, and additionally the optional endpoint-configuration fields `api_key`, `app_title`, and `app_url` (each a string defaulting to the empty string), `frequency_penalty`, `presence_penalty`, `top_p`, `repetition_penalty`, `min_p`, and `top_a` (each a float or `None`), `top_k` and `max_completion_tokens` (each an int or `None`), `reasoning_enabled` (bool or `None`), `reasoning_effort` (a closed-set string or `None`), and `reasoning_style` (a closed-set string defaulting to `openrouter`). Layer keys outside the fixed set SHALL be rejected. The `api_key` value SHALL be excluded from the dataclass `repr` so a profile can be logged or debugged without disclosing the credential. The `scenario_director` code default SHALL carry a 8,192-token `max_tokens` so a quest blueprint whose occupants carry complete compact cards fits one response.

#### Scenario: Every layer resolves to a complete profile
- **WHEN** a consumer requests the profile for any of the seven layer names
- **THEN** the registry returns a frozen profile with a base URL, chat path, model name, bounded temperature and max tokens, a timeout, a retry budget, a structured-output capability flag, an enabled flag, and every optional endpoint-configuration field at its omit default (empty string or `None`)

#### Scenario: Unknown layer keys are rejected
- **WHEN** a consumer requests a profile for a key outside the seven known layers
- **THEN** profile resolution raises a named error and no partial or default profile is returned

#### Scenario: The action_options profile requires structured output
- **WHEN** the effective `LLM_PROFILES` map is validated at settings load
- **THEN** the `action_options` layer's `supports_response_format` is true, or startup fails naming the layer and field — the one JSON-schema consumer cannot run without it

#### Scenario: The per-layer code defaults survive
- **WHEN** all seven profiles resolve from code defaults with no injected overrides
- **THEN** `action_options` carries its 320-token `max_tokens`, `title_nomination` carries its 640-token `max_tokens`, `scenario_director` carries its 8,192-token `max_tokens`, and the remaining layers carry the 250-token generic default

#### Scenario: The api key never reaches the profile repr
- **WHEN** a profile is constructed with a non-empty `api_key` and formatted with `repr()` or `str()`
- **THEN** the produced text does not contain the key value
