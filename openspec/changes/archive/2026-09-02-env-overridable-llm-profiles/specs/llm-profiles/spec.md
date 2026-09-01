# llm-profiles Delta Spec

## MODIFIED Requirements

### Requirement: Per-layer profile registry
`world/ai/profiles.py` SHALL define a frozen `LLMProfile` dataclass and a `LLM_PROFILES` registry read from the Django settings. The registry SHALL map the seven layer names `narrator`, `npc_dialogue`, `scenario_director`, `scene_builder`, `character_creation`, `action_options`, and `title_nomination` to exactly one profile each. Each profile SHALL carry `base_url`, `path`, `headers`, `model`, `temperature`, `max_tokens`, `timeout_seconds`, `max_retries`, `supports_response_format`, and `enabled`, and additionally the optional endpoint-configuration fields `api_key`, `app_title`, and `app_url` (each a string defaulting to the empty string), `frequency_penalty`, `presence_penalty`, `top_p`, `repetition_penalty`, `min_p`, and `top_a` (each a float or `None`), `top_k` and `max_completion_tokens` (each an int or `None`), `reasoning_enabled` (bool or `None`), `reasoning_effort` (a closed-set string or `None`), and `reasoning_style` (a closed-set string defaulting to `openrouter`). Layer keys outside the fixed set SHALL be rejected. The `api_key` value SHALL be excluded from the dataclass `repr` so a profile can be logged or debugged without disclosing the credential.

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
- **THEN** `action_options` carries its 320-token `max_tokens`, `title_nomination` carries its 640-token `max_tokens`, and the remaining layers carry the 250-token generic default

#### Scenario: The api key never reaches the profile repr
- **WHEN** a profile is constructed with a non-empty `api_key` and formatted with `repr()` or `str()`
- **THEN** the produced text does not contain the key value

### Requirement: Startup profile validation is strict
Profile values SHALL be validated at settings/registry construction time. `temperature` SHALL be a finite number in `0..2`; `max_tokens`, `timeout_seconds`, `top_k`, and `max_completion_tokens` (when not `None`) SHALL be positive integers; `max_retries` SHALL be a non-negative integer; `base_url` and `path` SHALL be non-empty strings; `model` SHALL be a non-empty string; `enabled` and `supports_response_format` SHALL be booleans; `api_key`, `app_title`, and `app_url` SHALL be strings; `frequency_penalty` and `presence_penalty` SHALL be `None` or finite floats in `-2..2`; `top_p` SHALL be `None` or a finite float in `0 < x <= 1`; `repetition_penalty` SHALL be `None` or a finite float greater than 0; `min_p` SHALL be `None` or a finite float in `0..1`; `top_a` SHALL be `None` or a finite float not less than 0; `reasoning_enabled` SHALL be a bool or `None`; `reasoning_effort` SHALL be `None` or one of `minimal`, `low`, `medium`, `high`; `reasoning_style` SHALL be one of `openrouter`, `vllm`, `off`. `headers` SHALL be an immutable `Mapping[str, tuple[str, ...]]` (or equivalent frozen representation) whose keys and string values SHALL be validated at construction time; the profile SHALL NOT expose the caller's original mutable dict. A profile failing any bound SHALL fail closed at construction rather than being silently clamped, and SHALL report which layer and field failed.

#### Scenario: Out-of-range sampling fails construction
- **WHEN** a profile declares a temperature outside `0..2` or a negative timeout
- **THEN** registry construction fails with a named error naming the layer and field, and no usable profile is installed

#### Scenario: Non-numeric token bounds fail construction
- **WHEN** a profile declares a non-integer `max_tokens` or a boolean where a bound integer is required
- **THEN** registry construction fails with a named error and the layer is unavailable rather than auto-corrected

#### Scenario: Headers are validated and frozen
- **WHEN** a profile supplies headers whose keys or values are not strings, or mutates the source dict after construction
- **THEN** construction fails for the invalid profile, and a successfully constructed profile holds an immutable copy that the caller's original dict cannot change

#### Scenario: An out-of-set reasoning effort fails construction
- **WHEN** a profile declares `reasoning_effort` outside the closed set or a `reasoning_style` outside `openrouter`/`vllm`/`off`
- **THEN** registry construction fails with a named error naming the layer and field

#### Scenario: Omitted optional fields construct cleanly
- **WHEN** a profile is constructed without any of the optional endpoint-configuration fields
- **THEN** construction succeeds and each optional field holds its omit default (`None`, or the empty string for the string fields)

## ADDED Requirements

### Requirement: Default profiles are injected, not environment-read
`world/ai/profiles.py` SHALL NOT read the process environment. `default_profiles(defaults=None)` SHALL return the pure code-default profile map when `defaults` is omitted, and SHALL merge a caller-injected mapping of per-layer field overrides over the code defaults when provided, with every injected value passing the same construction-time validation. Environment parsing for these values SHALL live exclusively in `server/conf/settings.py`.

#### Scenario: Injected defaults merge over code defaults
- **WHEN** `default_profiles` is called with a per-layer mapping that sets `model` for `character_creation`
- **THEN** that layer's profile carries the injected model, every other layer keeps its code default, and no environment variable is consulted

#### Scenario: Invalid injected values still fail closed
- **WHEN** an injected mapping carries a `top_p` of `1.5` for any layer
- **THEN** construction fails naming the layer and field, exactly as a hand-written `LLM_PROFILES` entry would

#### Scenario: The profiles module performs no environment reads
- **WHEN** the source of `world/ai/profiles.py` is inspected
- **THEN** it contains no `os.environ` access and importing it under a populated environment observes no environment reads

### Requirement: Credential-bearing standard headers are rejected in profile headers
The `headers` validation SHALL reject, case-insensitively, the sensitive header names
`authorization`, `proxy-authorization`, `x-api-key`, and `api-key` with the standard
named construction error, naming the layer and the `headers` field and stating that the
`api_key` profile field is the sanctioned credential route. Credentials supplied through
the dedicated field are excluded from the profile `repr`; a credential smuggled into the
frozen header mapping — which the dataclass `repr` does include — would defeat that
exclusion, so it fails closed instead. All other header names (including `X-Title` and
`HTTP-Referer`) SHALL remain freely settable.

#### Scenario: An Authorization header in the mapping fails construction
- **WHEN** a profile supplies `headers` containing `Authorization` (in any casing) with a bearer-style value
- **THEN** construction fails naming the layer, the `headers` field, and the `api_key` route, and no profile is installed

#### Scenario: Non-credential headers still pass
- **WHEN** a profile supplies `headers` containing `X-Title` and a custom `X-Request-Tag`
- **THEN** construction succeeds and both headers are present in the frozen mapping

### Requirement: Secret-settings profile entries merge per layer over environment-resolved defaults
When `server/conf/secret_settings.py` defines `LLM_PROFILES`, the effective profile map SHALL be resolved per layer: each layer named by the secret-settings map SHALL take its entry wholesale from the secret file (no field-level merge within that layer), and every layer NOT named SHALL keep its fully environment-resolved entry (per-layer override, then global override, then code default). A secret-settings map naming fewer than all layers SHALL NOT discard the environment configuration of the remaining layers. Validation of the merged map SHALL be as strict as today.

#### Scenario: A one-layer secret entry preserves other layers' environment values
- **WHEN** `LLM_MODEL=llama3.2` is set in the environment, `LLM_CHARACTER_CREATION_MODEL=qwen2.5-32b-instruct` is set, and `secret_settings.py` defines an `LLM_PROFILES` map containing only a complete `character_creation` entry
- **THEN** the six layers absent from the secret map resolve their model from the environment chain (character_creation's from its own per-layer value is replaced by the secret entry), and none of them falls back to a code default

#### Scenario: A secret layer entry replaces its layer wholesale
- **WHEN** a secret-settings `character_creation` entry omits `model` while `LLM_CHARACTER_CREATION_MODEL` is set in the environment
- **THEN** settings import fails with the strict named validation error naming the `character_creation` layer and the `model` field — the environment value reached neither the entry nor any partial merge, and a wholesale secret entry must be complete

#### Scenario: An unknown secret layer still fails the boot
- **WHEN** `secret_settings.py` defines `LLM_PROFILES` containing a key outside the seven layer names
- **THEN** settings import fails with the existing named unknown-layer error
