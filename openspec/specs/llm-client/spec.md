## Purpose

Defines the OpenAI-compatible chat completions client contract: an asynchronous, timeout-bounded client whose failures signal safely, backed by a local-first default endpoint configured from the environment.

## Requirements

### Requirement: OpenAI-compatible chat completions client
`world/ai/client.py` SHALL define `OpenAICompatClient`, a subclass of Evennia's `LLMClient` that keeps the Twisted async HTTP skeleton and overrides the request to OpenAI's `/v1/chat/completions` contract. Each call SHALL accept a layer-neutral per-call request descriptor containing the chat `messages` sequence of role/content pairs and, optionally, an output jsonschema and a schema identifier. The client SHALL build a JSON request body containing the profile's `model`, the messages, the profile's `temperature` and `max_tokens` settings, and a `response_format` hint exactly when the profile's `supports_response_format` flag is true and the descriptor declares a schema. A successful response SHALL be parsed from the OpenAI envelope and SHALL return `choices[0].message.content` as the generated text.

#### Scenario: A valid chat completion returns the message content
- **WHEN** the client posts a valid `/v1/chat/completions` request and the endpoint returns HTTP 200 with a body whose `choices[0].message.content` is a non-empty string
- **THEN** the client resolves with exactly that string and no additional interpretation of the content

#### Scenario: The payload uses the OpenAI chat contract
- **WHEN** a caller submits a descriptor with messages `[{"role": "system", "content": "…"}, {"role": "user", "content": "…"}]`
- **THEN** the request body contains the configured model name, the identical messages sequence, and the profile's temperature and max-token bounds under their OpenAI field names

#### Scenario: A structured-output hint is transmitted only when both sides opt in
- **WHEN** a descriptor declares an output schema and the profile's `supports_response_format` flag is true
- **THEN** the request body includes a `response_format` hint derived from that schema and identifier, and when either side is absent the field is omitted entirely

### Requirement: Asynchronous calls with bounded request timeouts
Every client call SHALL be asynchronous, returning a Twisted Deferred rather than blocking the Evennia server, and SHALL honor a per-request timeout from the governing profile. The timeout SHALL cover the complete exchange from request establishment through response-body parsing, so an endpoint that sends headers but never completes the body still errbacks within the bound. A call that exceeds the timeout SHALL resolve as a failure on the error path rather than hanging indefinitely, SHALL cancel or abort the underlying request to the extent Twisted supports, and SHALL NOT be retried by the client itself.

#### Scenario: A slow endpoint is abandoned at the timeout bound
- **WHEN** an endpoint does not respond within the profile's timeout
- **THEN** the client errbacks the pending call within a bounded delay after that timeout and the caller observes a failure rather than an unresolved Deferred

#### Scenario: A response that never finishes its body is abandoned
- **WHEN** an endpoint sends HTTP headers but never delivers the response body
- **THEN** the pending call errbacks within the timeout bound rather than waiting forever

#### Scenario: The server is not blocked while waiting
- **WHEN** a chat completion request is in flight against a slow endpoint
- **THEN** the client returns a Deferred immediately and no synchronous network or event-loop work is performed by the caller

### Requirement: Safe failure signaling without exceptions escaping
A connection error, HTTP error status, malformed response body, or timeout SHALL be reported as a failed Deferred (or an empty result per the governing call contract) and SHALL NOT raise an exception into the caller or leave a partially consumed state. Debug logging SHALL record a safe error summary that contains no player content, prompt text, or local file path.

#### Scenario: A non-200 status resolves as a safe failure
- **WHEN** the endpoint returns a non-200 status for a request
- **THEN** the call fails gracefully, no exception propagates to the caller, and the logged summary identifies the status without echoing the request payload

#### Scenario: A malformed response body fails without crashing
- **WHEN** an endpoint returns HTTP 200 with a body that is not valid JSON or lacks the expected OpenAI field
- **THEN** the call resolves as a failure, the Evennia process continues running, and no raw body or prompt is written to the log

### Requirement: Local-first default endpoint from the environment
The default profile SHALL target a local Ollama-compatible endpoint. The base URL SHALL come from the `OLLAMA_BASE_URL` environment variable when present, defaulting to `http://127.0.0.1:11434` otherwise, and the default chat path SHALL be `/v1/chat/completions`. No commercial API endpoint SHALL be configured as a built-in default.

#### Scenario: The default profile points at local Ollama
- **WHEN** no `LLM_PROFILES` setting overrides the default narrator profile
- **THEN** its base URL is taken from `OLLAMA_BASE_URL` (or the localhost fallback) and its path is `/v1/chat/completions`

#### Scenario: The environment variable selects the host
- **WHEN** `OLLAMA_BASE_URL` is set to a non-empty value
- **THEN** the default profile's base URL equals that value exactly
