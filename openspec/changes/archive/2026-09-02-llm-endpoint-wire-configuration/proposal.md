# llm-endpoint-wire-configuration

## Why

The predecessor change (`env-overridable-llm-profiles`) made every profile field
configurable and stored the optional endpoint fields, but the transport still ignores them:
an authenticated gateway (OpenRouter) cannot be used at all (no `Authorization` header
path), OpenRouter attribution (`X-Title`/`HTTP-Referer`) is impossible, and none of the
vLLM sampling/reasoning knobs reach the request body. This change makes the stored
configuration observable on the wire, completing the operator story of
`docs/superpowers/specs/2026-09-01-llm-endpoint-configuration-design.md`
(decisions C-5, C-6, C-8, C-9, C-10).

## What Changes

- `OpenAICompatClient._format_request_body` composes the request body in the design §4.2
  order: `model`/`messages`/`temperature`; `max_completion_tokens` **supersedes**
  `max_tokens` when set (C-10); every non-`None` sampling field verbatim
  (`frequency_penalty`, `presence_penalty`, `top_k`, `top_p`, `repetition_penalty`,
  `min_p`, `top_a`); reasoning per `reasoning_style` — `openrouter` → nested
  `{"reasoning": {"enabled", "effort"}}` omitting `None` sub-keys, `vllm` →
  `chat_template_kwargs.enable_thinking` dropping `effort`, `off` → nothing (C-6);
  `response_format` unchanged. Omitted fields never serialize (C-5): with no optional
  field set the body is byte-identical to today's.
- Request headers gain, from the profile, only when non-empty: `Authorization: Bearer
  <api_key>`, `X-Title: <app_title>`, `HTTP-Referer: <app_url>` (C-9). The key never
  appears in any log line, error string, or profile repr (repr exclusion shipped by the
  predecessor; this change guards the log/error paths).
- **BREAKING (policy)** `LLM_API_KEY` becomes a sanctioned environment-delivered credential:
  `docs/development/settings-and-environment.md` reverses the no-secrets-in-environment
  rule scoped to this single knob, naming the leak vectors (`/proc/<pid>/environ`,
  `podman compose config`, `docker inspect`) and mitigations (`env_file:` over inline
  `environment:`, or staying on `secret_settings.py`). `ART_SD_USERNAME`/`ART_SD_PASSWORD`
  keep the old rule verbatim.
- `compose.yaml` forwards the optional `LLM_*` knobs through `${LLM_X:-}` so unset host
  variables arrive blank (= omit) rather than literal; `LLM_API_KEY` forwarding uses an
  empty default so no host value silently leaks beyond the operator's own `.env`.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `llm-client`: the chat-completions client requirement gains the serialization contract
  (sampling passthrough, `max_completion_tokens` supersession, reasoning-style mapping,
  omission rule) and the header-composition requirement (bearer auth, attribution pair,
  key never logged).
- `settings-environment-overrides`: the credential requirement carves out the scoped
  `LLM_API_KEY` exception; the inventory guide documents the reversed policy.

## Impact

- `world/ai/client.py` (body composition + header builder); no change to the Twisted
  skeleton, timeout, or error mapping.
- Tests: `world/ai/tests/test_client.py` (serialization/header matrices via the existing
  injected-reactor local-endpoint harness); container contract test gains the forwarded
  optional knobs; policy doc tests (inventory guide table) unchanged mechanism.
- No DB, no command surface, no deterministic-core code. Degradation semantics untouched:
  a 401/400 from a mis-set key or field degrades exactly as any HTTP failure does today.
- Depends on: `env-overridable-llm-profiles` (profile fields + env knobs must exist).
  Blocks: nothing.
