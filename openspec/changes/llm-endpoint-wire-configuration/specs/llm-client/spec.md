# llm-client Delta Spec

## MODIFIED Requirements

### Requirement: OpenAI-compatible chat completions client
`world/ai/client.py` SHALL define `OpenAICompatClient`, a subclass of Evennia's `LLMClient` that keeps the Twisted async HTTP skeleton and overrides the request to OpenAI's `/v1/chat/completions` contract. Each call SHALL accept a layer-neutral per-call request descriptor containing the chat `messages` sequence of role/content pairs and, optionally, an output jsonschema and a schema identifier. The client SHALL build a JSON request body containing the profile's `model`, the messages, and the profile's `temperature`. For output length the body SHALL carry the profile's `max_completion_tokens` under that field name when the profile sets it, and the profile's `max_tokens` under `max_tokens` otherwise — never both. Each configured sampling field (`frequency_penalty`, `presence_penalty`, `top_k`, `top_p`, `repetition_penalty`, `min_p`, `top_a`) SHALL appear verbatim under its OpenAI field name, and every sampling field the profile leaves unset SHALL be absent from the body entirely, so a default-configured profile produces a byte-identical body to the pre-configuration client. Reasoning control SHALL follow the profile's `reasoning_style` only when `reasoning_enabled` or `reasoning_effort` is set: `openrouter` emits a nested `reasoning` object carrying the non-`None` subset of `enabled` and `effort`; `vllm` emits `chat_template_kwargs.enable_thinking` when `reasoning_enabled` is set and never sends `effort`; `off` emits neither. A `response_format` hint SHALL be included exactly when the profile's `supports_response_format` flag is true and the descriptor declares a schema. A successful response SHALL be parsed from the OpenAI envelope and SHALL return `choices[0].message.content`.

#### Scenario: A valid chat completion returns the message content
- **WHEN** the client posts a valid `/v1/chat/completions` request and the endpoint returns HTTP 200 with a body whose `choices[0].message.content` is a non-empty string
- **THEN** the client resolves with exactly that string and no additional interpretation of the content

#### Scenario: The payload uses the OpenAI chat contract
- **WHEN** a caller submits a descriptor with messages `[{"role": "system", "content": "…"}, {"role": "user", "content": "…"}]`
- **THEN** the request body contains the configured model name, the identical messages sequence, and the profile's temperature under its OpenAI field name

#### Scenario: A structured-output hint is transmitted only when both sides opt in
- **WHEN** a descriptor declares an output schema and the profile's `supports_response_format` flag is true
- **THEN** the request body includes a `response_format` hint derived from that schema and identifier, and when either side is absent the field is omitted entirely

#### Scenario: Configured sampling fields pass through verbatim
- **WHEN** a profile sets `top_p = 0.9` and `frequency_penalty = -1.0` and leaves the other sampling fields unset
- **THEN** the request body carries exactly those two fields with those values and contains no other sampling key

#### Scenario: max_completion_tokens supersedes max_tokens
- **WHEN** a profile sets `max_completion_tokens = 400` and a `max_tokens` default of 250
- **THEN** the request body carries `"max_completion_tokens": 400` and carries no `max_tokens` key

#### Scenario: OpenRouter-style reasoning maps to the nested object
- **WHEN** a profile with `reasoning_style = "openrouter"` sets `reasoning_enabled = true` and leaves `reasoning_effort` unset
- **THEN** the request body contains `"reasoning": {"enabled": true}` and no top-level flat `reasoning`, `enable_thinking`, or `chat_template_kwargs` key

#### Scenario: vLLM-style reasoning maps to chat template kwargs
- **WHEN** a profile with `reasoning_style = "vllm"` sets `reasoning_enabled = true` and `reasoning_effort = "high"`
- **THEN** the request body contains `chat_template_kwargs` with `enable_thinking: true`, no nested `reasoning` object, and no effort value

#### Scenario: vLLM-style reasoning false is transmitted as false
- **WHEN** a profile with `reasoning_style = "vllm"` sets `reasoning_enabled = false`
- **THEN** the request body contains `chat_template_kwargs.enable_thinking: false`

#### Scenario: vLLM-style effort alone sends nothing
- **WHEN** a profile with `reasoning_style = "vllm"` sets only `reasoning_effort` (enabled unset)
- **THEN** the request body contains no `chat_template_kwargs` (not even an empty object) and no reasoning-related key of any shape

#### Scenario: Off style sends nothing even with reasoning configured
- **WHEN** a profile with `reasoning_style = "off"` sets `reasoning_enabled = true` and `reasoning_effort = "high"`
- **THEN** the request body contains no reasoning-related key of any shape

#### Scenario: An unset reasoning configuration sends nothing
- **WHEN** a profile leaves both `reasoning_enabled` and `reasoning_effort` unset, under any `reasoning_style`
- **THEN** the request body contains no reasoning-related key of any shape

## ADDED Requirements

### Requirement: Request headers carry authentication and attribution without leaking the key
The client SHALL build the request headers passed to the transport by first deriving, only when the corresponding profile field is non-empty, an `Authorization` header of the exact form `Bearer <api_key>`, an `X-Title` header carrying `app_title`, and an `HTTP-Referer` header carrying `app_url`, and then overlaying the profile's frozen `headers` mapping so that an explicitly configured header of the same (exact-case) name wins over the derived one. Credential-bearing standard header names are rejected in the profile mapping upstream, so the `Authorization` escape hatch cannot smuggle a bearer value past the `repr` exclusion. The api key SHALL NOT appear in any log line, any error message or failure representation, or any client/profile debug output produced on any success or failure path.

#### Scenario: Explicit headers win over derived attribution
- **WHEN** a profile sets `app_title = "Elosern"` AND an explicit `headers` mapping entry `X-Title: Other`
- **THEN** the transmitted headers carry `X-Title: Other`

#### Scenario: A configured key authenticates the request
- **WHEN** a profile carries a non-empty `api_key` and the client sends a request
- **THEN** the request headers include `Authorization: Bearer <api_key>` exactly

#### Scenario: An empty key sends no Authorization header
- **WHEN** a profile's `api_key` is the empty string
- **THEN** the request headers contain no `Authorization` entry

#### Scenario: Attribution headers appear only when configured
- **WHEN** a profile sets `app_title = "Elosern"` and leaves `app_url` empty
- **THEN** the request headers include `X-Title: Elosern` and contain no `HTTP-Referer` entry

#### Scenario: A transport failure never surfaces the key
- **WHEN** a request governed by a profile with a non-empty `api_key` fails with any transport error (connection, HTTP status, malformed body, or timeout)
- **THEN** the failure representation, the safe log line, and every message observable by the calling layer contain no trace of the key

### Requirement: A default profile produces an unchanged wire format
When every optional endpoint-configuration field of the profile holds its omit default (empty string or `None`), the serialized request body and headers SHALL equal the pre-configuration client's byte-for-byte, so existing local endpoints observe no difference from this change.

#### Scenario: Byte identity under defaults
- **WHEN** the client serializes a request under a profile with no optional field set
- **THEN** the body JSON contains exactly `model`, `messages`, `temperature`, `max_tokens` (plus `response_format` under the existing opt-in rule) and the headers are exactly the profile's frozen mapping
