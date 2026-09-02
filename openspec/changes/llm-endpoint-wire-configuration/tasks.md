# tasks — llm-endpoint-wire-configuration

Depends on `env-overridable-llm-profiles` being implemented (the optional `LLMProfile`
fields and `LLM_ENV_NAMES` must exist).

## 1. Request-body composition (world/ai/client.py)

- [x] 1.1 Rework `_format_request_body` per design D-B1: base `{model, messages, temperature}`; `max_completion_tokens` supersession branch (C-10); verbatim loop over the seven sampling fields with `None` omission; then the existing `response_format` gate untouched.
- [x] 1.2 Add `_apply_reasoning(body, profile)` per D-B1: fires only when `reasoning_enabled is not None or reasoning_effort is not None`; `openrouter` → nested `reasoning` object with `None` sub-keys omitted (empty object ⇒ key omitted); `vllm` → `chat_template_kwargs.enable_thinking` only when `reasoning_enabled is not None`, effort dropped; `off` → nothing.

## 2. Header composition

- [x] 2.1 Add `_request_headers(profile)` exactly per design D-B2: derived entries (`Authorization: Bearer <api_key>`, `X-Title`, `HTTP-Referer` — each only when non-empty) inserted FIRST, then every explicit `profile.headers` entry overlaid (exact-case key wins). Wire `get_response` to build `Headers(self._request_headers(profile))`.
- [x] 2.2 Key-leak audit: assert no code path stringifies the key into logs or failures — `_safe_log_error` stays kind-only; `_handle_llm_error` message templates carry no header/body material. Add a static-style guard test that constructs a failed request under a non-empty key and asserts the failure message and captured log line exclude the key substring.
- [x] 2.3 Credential-smuggling counterpart (the upstream rejection lands in `env-overridable-llm-profiles`): a profile whose `headers` carry `Authorization` must already fail construction — add a client-side regression asserting `_request_headers` on a legitimately constructed profile never double-emits `Authorization` and that the upstream deny-set makes the smuggling repr test impossible by construction.

## 3. Client tests (world/ai/tests/test_client.py)

- [x] 3.0 Extend the `StubAgent` harness to record every `request(...)` call's args/kwargs (method, url, `Headers`, body producer); add an assertion path that reads the raw header values off the captured `Headers` object and decodes the captured `StringProducer` body — every wire-level assertion below goes through the captured `get_response` request, never the builder helpers alone (a correct `_request_headers` that `get_response` forgot to wire must fail).
- [x] 3.1 Serialization matrix on the captured requests: byte-identity default body (no optional field set); each sampling field present/absent; `max_completion_tokens` wins, never both keys; `response_format` opt-in unaffected. Reasoning per the D-B1 case table — `openrouter`: enabled-only, **effort-only (`{"reasoning": {"effort": …}}`)**, both; `vllm`: enabled-only, enabled+effort (effort dropped), **enabled=false → `enable_thinking: false`**, **effort-only → no reasoning key and no empty `chat_template_kwargs`**; **`off` with both fields set → nothing**; both-unset under each style → nothing.
- [x] 3.2 Header matrix on the captured `Headers`: key set/unset → `Authorization` present/absent; title/url combos → `X-Title`/`HTTP-Referer` independently; **explicit profile `X-Title` wins over the derived value** (exact-case overlay); default profile sends exactly the frozen mapping.
- [x] 3.3 Annotate every new/changed behaviour test with `covers_requirement` using the `llm-client` delta IDs from `uv run --locked python -m tools.spec_traceability list`; keep `tools.spec_traceability check` green.

## 4. Compose and inventory

- [x] 4.1 `compose.yaml`: forward each optional `LLM_*` knob as `${LLM_X:-}` (empty default, never a literal secret); `LLM_BASE_URL` keeps the host-gateway default.
- [x] 4.2 `tests/test_container_contract.py`: rendered compose shows the forwarded optional keys with empty defaults, `LLM_BASE_URL` host-gateway default intact, and no non-empty `LLM_API_KEY` literal.
- [x] 4.3 `.env.example`: expand the `LLM_API_KEY` entry's comment to the exception wording (leak vectors + `env_file:` / `secret_settings.py` mitigations) per the doc task.

## 5. Documentation policy reversal

- [x] 5.1 `docs/development/settings-and-environment.md`: move `LLM_API_KEY` from "not via environment" standing to a scoped-exception entry naming leak vectors (`/proc/<pid>/environ`, `podman compose config`, `docker inspect`) and both mitigations; keep `ART_SD_USERNAME`/`ART_SD_PASSWORD` and the `SECRET_KEY` class rows unchanged; add the compose optional-knob blank-forwarding note.
- [ ] 5.2 Verify the traceability gate and docs links, then focused labels (`world.ai.tests.test_client`, `tests.test_container_contract`) and `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 commands server typeclasses world web.webclient`; `uv run --locked python -m tools.spec_traceability check`; `openspec validate llm-endpoint-wire-configuration --strict`; `git diff --check` clean.
