# llm-client Delta Spec

## MODIFIED Requirements

### Requirement: Local-first default endpoint from the environment
The default profile SHALL target a local OpenAI-compatible endpoint. The base URL SHALL come from the `LLM_BASE_URL` environment variable when present (resolved in `server/conf/settings.py` and injected into the profile defaults), defaulting to `http://127.0.0.1:11434` otherwise, and the default chat path SHALL be `/v1/chat/completions`. No commercial API endpoint SHALL be configured as a built-in default: a hosted gateway is reachable only when an operator explicitly sets `LLM_BASE_URL`.

#### Scenario: The default profile points at the local endpoint
- **WHEN** no `LLM_PROFILES` setting overrides the default narrator profile and no `LLM_BASE_URL` is set
- **THEN** its base URL is `http://127.0.0.1:11434` and its path is `/v1/chat/completions`

#### Scenario: The environment variable selects the host
- **WHEN** `LLM_BASE_URL` is set to a non-empty value
- **THEN** the default profile's base URL equals that value exactly
