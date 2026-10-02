# Design: Configurable HTTP User-Agent

## Context

Three runtime transports build request headers their own way today:

- `world/art/translate_ct2.py::_download_model` — `urllib.request.Request(url, headers={"User-Agent": _DOWNLOAD_USER_AGENT})`, the constant added by e1923447 after the argos-net.com edge 403-blocked urllib's default agent.
- `world/art/sd_worker.py::_http_request` — `http.client` `.request(method, path, body, headers=headers)` with a per-request dict (Content-Type, Basic auth); no User-Agent, so sd-webui sees no declared identity.
- `world/ai/client.py::_request_headers` — a `dict[str, list[str]]` of derived headers fed to Twisted's `Headers`; no User-Agent, so Twisted's Agent sends none.

The settings layer already has the `_env_str` free-text helper and the exact-inventory contract tests (`server/conf/tests/test_env_overrides/`): `ENV_BACKED` map, `.env.example` completeness check, `test_settings.py` pop-list, and the developer-guide row check. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- One env-overridable value, three transports, no per-call-site literals.
- Deterministic, network-free tests that pin the header on the wire at each transport's existing stubbing seam.
- Keep the determinism guard intact: nothing under `world/rules/` gains a path to this helper.

**Non-Goals:**

- Monkey-patching rembg's internal weight-download session (`world/art/cutout.py`) — no header seam exists; the spec documents the gap.
- Sharing the constant with dev/CI scripts (`tools/import_mono_font.py`, `web/tests/browser/fixtures.py`, `scripts/*.sh`) — they are not the server's runtime traffic; wiring them is optional churn, not behavior.
- Per-endpoint UA profiles or version-string automation (below).

## Decisions

**D1 — One global UA string, no per-service suffixes.** The alternatives were `HTTP_USER_AGENT` as a base that each call-site appends its purpose to (`... (prompt-translation model fetch)`) or a per-service knob family. Rejected: the field motivation is "an edge blocks generic Python agents", solved by any declared identity; per-service decoration is derivable server-side from URL/path anyway, and the operator-facing contract is simpler when the wire value is byte-for-byte the configured value at every endpoint — with the one carried-forward exception that the LLM transport's existing profile-overlay rule lets a profile's explicit `User-Agent` mapping entry replace the derived one on that transport (preserving the llm-client capability's precedence contract; the outbound-http-identity spec exempts exactly those requests). A deployment that wants to distinguish endpoints from its logs can front the requests with a proxy; the setting is the identity, not the telemetry channel. The `_DOWNLOAD_USER_AGENT` string's parenthetical is therefore dropped rather than generalized.

**D2 — Default value `elosern-mud/1.0`, not a URL-bearing or version-embedding string.** Contract floated `elosern-mud/1.0 (+https://localhost; prompt-translation,sd-webui,llm)`. Rejected: `localhost` is a lie in production, embedding the purpose list duplicates D1's rejected coupling, and the repo has no single source-of-truth app version to interpolate (`pyproject` version is the package's, not the game's), so an interpolated version would be a second inventory to keep honest. `elosern-mud/1.0` matches the already-proven-working shape of the e1923447 constant (a `name/version` token is what Cloudflare-class edges check for) and gives operators a stable grep target. If the project later gains a canonical version setting, folding it in is a one-line change with a default-only spec edit.

**D3 — Helper lives at `world/http_identity.py`, exposing two tiny functions: `http_user_agent() -> str` and `user_agent_headers() -> dict[str, str]`.** The helper reads `django.conf.settings.HTTP_USER_AGENT` at call time (per-request), so `override_settings` in tests and a settings reload in production both take effect without reimport gymnastics; `user_agent_headers()` returns a fresh `{"User-Agent": ...}` dict safe to `dict.update()` into any caller's header dict. Alternatives considered: a constant computed once in `settings.py` and imported directly (rejected — couples the three call sites to import order and makes per-request settings-reload semantics invisible), and a method on an existing module such as `world/observability` or a new `world/http/` package (rejected — the observability facade is log-only by charter, and a package for one function is ceremony). The module must NOT sit under `world/rules/`' import closure — the determinism tests (`world/rules/tests/test_monster_behaviour_determinism.py`) AST-scan rules modules for urllib/transport imports; `world/http_identity.py` itself imports only `django.conf.settings`, and nothing in `world/rules/` will import it, but placement outside `rules/` keeps the boundary structural rather than conventional. No new shard entry is needed since the helper's behavior is pinned inside the three existing test modules rather than a new one.

**D4 — `HTTP_USER_AGENT` is env-overridable via `_env_str`, unlike the deliberately code-only settings.** `ART_TRANSLATE_BACKEND` et al. stay code-only because they are import-executing dotted paths, and `ART_SD_USERNAME`/`ART_SD_PASSWORD` because they are credentials (see `settings-environment-overrides`). A UA string is neither: it is public request metadata that appears on other parties' wire logs anyway, so the env layer poses no secret-leak or code-injection risk. It is the exact class of deployment-tunable identity that motivated the whole knob layer, and the e1923447 incident is the proof that operators need to change it without a code deploy. The one wrinkle: the existing `_env_str` contract maps blank to the *passed default*, which for the generation free-text knobs is the empty "server default" sentinel — for this knob the passed default is `elosern-mud/1.0`, so blank-to-default lands on the right behavior for free (D5).

**D5 — Empty means default, never an empty header.** An empty `User-Agent` header can fail edge validation as hard as `Python-urllib/*`, so `present-but-empty ⇒ elosern-mud/1.0` (spec delta), implemented by `_env_str("HTTP_USER_AGENT", "elosern-mud/1.0")` whose stripped-blank fallback already does this; the helper additionally guards `or DEFAULT`-style against a settings reload injecting an empty override — belt, one line.

**D6 — Call-site adaptation is shape-specific and minimal.** translate_ct2: `Request(_MODEL_URL, headers=user_agent_headers())`, constant and its docstring reference deleted, existing regression test re-pinned to `settings.HTTP_USER_AGENT` via `override_settings`. sd_worker: `headers.update(user_agent_headers())` beside the Content-Type/Basic-auth assembly in `_http_request`, so every POST, GET enumeration, and probe rides it for free. ai/client: `_request_headers` seeds `headers["User-Agent"] = [http_user_agent()]` in the derived block *before* the profile overlay loop, preserving the "explicit profile header wins" rule (Twisted `Headers` normalization then guarantees no doubling) and the key-deny-set is untouched since `User-Agent` is not credential-bearing.

## Risks / Trade-offs

- [A hostile override value (CRLF injection) could corrupt the request line] → The header value passes through `urllib`/`http.client`/Twisted `Headers` validation, each of which rejects embedded CR/LF in header values at send time; the value is operator-supplied through the same trusted channel as every other knob, so no extra filtering is added beyond `_env_str`'s strip.
- [Changing the LLM client's default wire headers breaks the "byte-for-byte unchanged wire format" guarantee] → The `llm-client` delta amends that requirement in the same change; the Ollama local endpoint and OpenAI-compatible gateways accept an added `User-Agent` unconditionally.
- [Settings reload changing `HTTP_USER_AGENT` mid-flight yields mixed identities across in-flight requests] → Accepted: each request carries the value current at construction, matching how every other per-request setting read behaves here.
- [rembg weight downloads still ship the library default agent] → Documented non-coverage in the spec; a future rembg header seam (or pinning a session) can close it without changing this capability's contract.

## Migration Plan

No data, no interface removal operators depend on: pre-release, so the `_DOWNLOAD_USER_AGENT` constant is deleted outright. Rollback is reverting the commit — the default value reproduces today's effective behavior everywhere except sd-webui/LLM, which gain a header that is strictly additive.
