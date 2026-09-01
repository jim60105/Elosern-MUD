# design — llm-endpoint-wire-configuration

## Context

`OpenAICompatClient` (`world/ai/client.py`) today: `_format_request_body` emits
`{model, messages, temperature, max_tokens}` plus an optional `response_format`; `get_response`
builds `Headers(self.profile.headers)` verbatim. The predecessor change
`env-overridable-llm-profiles` added the optional profile fields (`api_key`, `app_title`,
`app_url`, seven sampling fields, `reasoning_*`, `max_completion_tokens`) and made them
env-settable, but the client does not read them yet. Constraints from the master design and
AGENTS.md: transport-boundary (only `world/ai/client.py` touches the Twisted transport),
safe-log (no prompt/body/player text in logs — `_safe_log_error` logs only
`LLMTransportError.kind`), and offline playability (a bad config degrades exactly like any
HTTP failure).

## Goals / Non-Goals

**Goals:**
- Request-body composition exactly as design §4.2, omission-first (C-5, C-10, C-6).
- Header composition adding bearer auth and the OpenRouter attribution pair when non-empty
  (C-9), with the api key excluded from every observable string (logs, errors, repr).
- Scoped, documented policy reversal for `LLM_API_KEY` (C-8) in
  `docs/development/settings-and-environment.md`.
- compose forwarding of the optional knobs with blank-means-omit semantics.

**Non-Goals:**
- Parsing a `reasoning_content` field on responses (out of scope, design §7).
- Any provider health probe, per-request model routing, or cost accounting.
- Touching the retry budget, semantic validators, degrade hooks, prompt registry, or the
  `response_format` gate.
- Moving any non-LLM secret to the environment (`ART_SD_USERNAME`/`PASSWORD` keep the rule).

## Decisions

### D-B1 `_format_request_body` becomes a small ordered builder

Keep one method, build a `dict` in the design §4.2 order. Two helper branches:

```python
_TOKEN_FIELDS = ("frequency_penalty","presence_penalty","top_k",
                 "top_p","repetition_penalty","min_p","top_a")
...
if profile.max_completion_tokens is not None:
    body["max_completion_tokens"] = profile.max_completion_tokens
else:
    body["max_tokens"] = profile.max_tokens
for f in _TOKEN_FIELDS:
    v = getattr(profile, f)
    if v is not None:
        body[f] = v
self._apply_reasoning(body, profile)
```

`_apply_reasoning(body, profile)` — the exhaustive case table (no empty containers ever
emitted):

| style | enabled | effort | emitted |
|---|---|---|---|
| any | `None` | `None` | nothing |
| `off` | any (even set) | any (even set) | nothing |
| `openrouter` | `True`/`False` | `None` | `{"reasoning": {"enabled": v}}` |
| `openrouter` | `None` | `"high"` | `{"reasoning": {"effort": "high"}}` |
| `openrouter` | set | set | both sub-keys |
| `vllm` | `True`/`False` | any | `{"chat_template_kwargs": {"enable_thinking": v}}` (effort never emitted) |
| `vllm` | `None` | set | **nothing** (effort has no vLLM carrier; an empty `chat_template_kwargs` is never emitted) |

Rationale: matches vLLM's `chat_template_kwargs.enable_thinking` and OpenRouter's nested
`reasoning` object exactly; a flat `reasoning` key 400s vLLM's OpenAI server (design C-6).
The `vllm`+effort-only cell emitting nothing is deliberate: inventing a carrier would be a
guess, and an empty dict invites a 400. Alternative: always nest reasoning — rejected,
breaks the byte-identity default.

### D-B2 Header builder: derived first, explicit profile headers win

One unambiguous algorithm, applied in `get_response` (not just a helper):

```python
def _request_headers(profile) -> dict[str, list[str]]:
    headers: dict[str, list[str]] = {}
    if profile.api_key:
        headers["Authorization"] = [f"Bearer {profile.api_key}"]
    if profile.app_title:
        headers["X-Title"] = [profile.app_title]
    if profile.app_url:
        headers["HTTP-Referer"] = [profile.app_url]
    for name, values in profile.headers.items():   # explicit wins, exact key casing
        headers[name] = list(values)
    return headers
```

Derived headers are inserted **first** and the frozen `profile.headers` mapping overwrites
them, so an operator's explicit `secret_settings` header always wins (the documented
escape hatch; matching the delta requirement's precedence wording). Key comparison is
exact-string (the project's header-map semantics), documented as such. The constructed
dict is what `Headers(...)` receives — `_safe_log_error` stays kind-only, and the key is
never interpolated into an error/`repr`.

**Credential-in-headers hazard (duck MAJOR).** `LLMProfile`'s dataclass `repr` includes
`headers`, so an operator who puts `Authorization: Bearer sk-…` into `profile.headers`
instead of `api_key` reintroduces exactly the leak `field(repr=False)` prevents. Fix:
`_normalize_headers` rejects the sensitive header names case-insensitively —
`authorization`, `proxy-authorization`, `x-api-key`, `api-key` — with a
`ProfileValidationError(layer, "headers", ...)` naming `api_key` as the sanctioned route;
`X-Title`/`HTTP-Referer` remain freely settable (not credentials). The escape hatch stays
for non-credential headers. Alternative considered: redact sensitive values in the repr —
rejected as a footgun (silent mutation of logged data) where a fail-closed rejection is
clearer and consistent with the registry's philosophy.

### D-B3 The api-key is a documented, scoped exception

`settings-environment-overrides` currently forbids *all* credentials in the environment. The
reversal is worded narrowly: `LLM_API_KEY` MAY read the environment; the `ART_SD_*`
credential pair and `SECRET_KEY` class explicitly retain the prohibition. The guide states
the leak vectors and that `secret_settings.py` remains available for operators who decline
the exposure. Rationale: preserves the anti-pattern warning where it still applies rather
than deleting it; the user's explicit requirement (keyless-file hosted-provider deploy) is
met for the one knob that needs it.

### D-B4 compose forwarding is opt-in-blank, never host-leaking

Each optional knob is forwarded as `LLM_X: ${LLM_X:-}` (empty default), so a host without
the variable set contributes a blank value (omit semantics), and `LLM_API_KEY:
${LLM_API_KEY:-}` never defaults to any literal. `LLM_BASE_URL` keeps the host-gateway
default. Rationale: blank is the settings.py omit sentinel, so unset host vars add nothing;
no secret is baked into the compose file.

## Risks / Trade-offs

- [A vLLM `chat_template_kwargs` shape differs across versions] → mapping is isolated in
  `_apply_reasoning`; the `vllm` style is opt-in (`LLM_REASONING_STYLE=vllm`), so the
  default OpenRouter style can never 400 a vLLM-agnostic deployment and an operator who
  picks `vllm` owns that endpoint's shape; documented, not silently guessed.
- [Sending `reasoning`/Extras to an endpoint that rejects unknown body fields] → every
  field serializes only when explicitly configured (C-5); a default-configured deployment is
  byte-identical to today, so no existing endpoint regresses. A mis-set knob fails as an
  HTTP error → degrade, exactly like today.
- [Two changes must land in order] → B imports nothing new from A's code beyond the profile
  fields; if A is not merged B cannot construct profiles carrying the fields, so B's tests
  fail loudly rather than half-working. Sequencing is enforced by the shared `LLMProfile`
  signature, not a runtime guard.
- [Header dict-update lets an operator override the derived bearer] → intentional: explicit
  `secret_settings` headers are the documented escape hatch; documented precedence note.
