## Context

The deterministic engine is complete and playable. The generative layer — Narrator, NPC dialogue, ScenarioDirector, and SceneBuilder — is entirely unbuilt: `world/ai/` currently contains only package stubs and an empty `schemas/` seam, and no LLM setting or client exists. The approved engine design assigns change 17 the client foundation: an OpenAI-compatible async client, per-layer `LLM_PROFILES`, the guardrail skeleton, and a deterministic test double.

The upstream dependency is already pinned and verified: `evennia.contrib.rpg.llm.llm_client.LLMClient` is importable in Evennia 6.1.0 (asserted by `tests/test_contrib_matrix.py`) and is a small Twisted HTTP client with an `Agent`, a connection pool, a `StringProducer` body, and a `SimpleResponseReceiver`. Its default configuration reads a single global setting set, sends one `prompt` key, and parses a `text-generation-webui` envelope — none of which matches per-layer OpenAI chat completion. Design §4 mandates subclassing it and keeping the Twisted async skeleton while overriding the `/v1/chat/completions` payload.

Design §7.5 fixes the guardrail shape (jsonschema → semantic validation → retry-with-error-appended → degrade), §7.1–§7.4 fixes the layer fallbacks, and §10 fixes the test rule: generative tests use a `FakeLLMClient` that replays fixed JSON and never contact a real endpoint. The project additionally enforces the single-writer invariant: no module under `world/ai/` may mutate game state, so this change's modules only read configuration and produce validated proposals.

## Goals / Non-Goals

**Goals:**

- Provide `OpenAICompatClient`, a subclass of Evennia's `LLMClient` that keeps the Twisted async skeleton and speaks OpenAI `/v1/chat/completions`.
- Provide `LLM_PROFILES`, a strictly validated, frozen per-layer profile registry with a local-first default derived from `OLLAMA_BASE_URL`.
- Provide the `guardrail` validation–retry–degrade pipeline from design §7.5 with pluggable per-layer semantic-validator and degrade hooks.
- Provide `FakeLLMClient`, a deterministic Deferred-returning double with scriptable failure modes, and keep every generative test offline and deterministic.
- Preserve the single-writer invariant: client, profiles, and guardrail never write game state.

**Non-Goals:**

- Narrator, NPC dialogue, ScenarioDirector, or SceneBuilder behavior — changes 18–21 consume this foundation.
- Streaming responses, tool calling, embeddings, or image generation.
- Any built-in commercial API endpoint; the only default is local Ollama.
- Persisting prompts, responses, profiles, or degrade results anywhere in the game DB.
- Backward-compatibility adapters or data migrations; the project is unreleased.

## Decisions

### D1. Subclass Evennia's LLMClient and override the config, payload, parse, timeout, and reactor seams

`OpenAICompatClient` subclasses `evennia.contrib.rpg.llm.llm_client.LLMClient` and keeps its Twisted plumbing: the quiet `_HTTP11ClientFactory`, the `Agent`, `StringProducer`, and `SimpleResponseReceiver`. It overrides:

- `__init__(self, profile, reactor=None)` — takes a frozen `LLMProfile` instead of reading the global `LLM_*` settings, so each client instance is governed by exactly one layer's profile. Because the upstream constructor builds its connection pool and `Agent` from the module-global reactor, the subclass re-creates the pool and agent with an injected reactor when one is supplied (falling back to the global), so tests can use `twisted.internet.task.Clock` without monkey-patching the global reactor. This is the one place the "keep the inherited skeleton" rule is relaxed — the transport is rebuilt on the injected reactor.
- `_format_request_body(descriptor)` — builds the OpenAI `/v1/chat/completions` body from a layer-neutral per-call descriptor carrying `messages` and optional `output_schema`/`schema_id`: `model`, `messages`, `temperature`, `max_tokens`, plus `response_format` only when the profile's `supports_response_format` flag is true and the descriptor declares a schema.
- response parsing — reads `choices[0].message.content` from the OpenAI envelope instead of `results[0].text`.
- `get_response(descriptor)` — stays a Deferred-returning method (see D3 for the timeout).

The contrib-matrix import test already guards the base class path, and the subclass surface is limited to these overridden seams, so an Evennia upgrade risk stays bounded.

Alternative considered: author a fresh `Agent`-based client. Rejected because design §4 explicitly mandates subclassing and the Evennia skeleton already handles connection pooling and body/response plumbing.

### D2. Profiles are frozen per-layer dataclasses read from a single setting

`world/ai/profiles.py` defines a frozen `LLMProfile` carrying `base_url`, `path`, `headers`, `model`, `temperature`, `max_tokens`, `timeout_seconds`, `max_retries`, `supports_response_format`, and `enabled`. The registry is built from Django's `LLM_PROFILES` dict keyed by exactly the four layer names `narrator`, `npc_dialogue`, `scenario_director`, and `scene_builder`. Construction validates every field with named errors that report the layer and field; validation fails closed, never clamps.

`get_profile(layer)` raises a named `UnknownLayerError` for keys outside the fixed set. The default profile set targets local Ollama: `base_url` from `OLLAMA_BASE_URL` (falling back to `http://127.0.0.1:11434`), path `/v1/chat/completions`, a bounded temperature/token budget, and `supports_response_format` false unless a backend declares it — the safe default, because design §7.5 only requests structured output when the endpoint supports it.

`headers` is carried as an immutable `Mapping[str, tuple[str, ...]]` (validated and defensively copied at construction) so the frozen-profile and fail-closed contracts survive a caller mutating the source dict. The two runtimes are explicit: when `OLLAMA_BASE_URL` is unset the profile falls back to `127.0.0.1:11434` for bare-metal use, while the compose deployment injects `host.containers.internal:11434` unchanged; both behaviors are tested.

Alternative considered: keep reading Evennia's existing global `LLM_*` settings. Rejected because those are single-endpoint globals and cannot express per-layer model selection (design D6).

### D3. Bound every request with a timeout that covers the full exchange

A slow or hung endpoint must not stall Evennia. `get_response` wraps the complete agent request — request establishment through response-body parsing — with a timeout derived from the profile, so an endpoint that delivers headers but never finishes the body still errbacks within the bound. The reactor used for the timeout is injectable so unit tests can use `twisted.internet.task.Clock` and advance time deterministically instead of waiting on a real reactor: the subclass rebuilds the pool and agent on the injected reactor (D1).

The timeout errbacks the returned Deferred within a bounded delay after `timeout_seconds`; on timeout the underlying request is cancelled/aborted to the extent Twisted's `Agent` supports, and the connection pool bounds any lingering socket. Transport-level failures (timeout, connection error, HTTP error, malformed non-JSON body) resolve as failures and are the guardrail's responsibility to map to degrade. Timeouts and retries are distinct: the client times out a single attempt, and the guardrail owns the retry budget.

Alternative considered: rely on TCP/OS connect timeouts alone. Rejected because a server that accepts the connection but never responds would block forever.

### D4. The guardrail is one generic pipeline with registered layer hooks

`world/ai/guardrail.py` exposes a single async `guarded_call` with this shape:

1. Resolve the layer's profile. If `enabled` is false, short-circuit to the layer's degrade fallback with no network attempt.
2. Call the client through an injected client protocol (never by importing `OpenAICompatClient` directly). Any transport failure (timeout, connection, HTTP, unparseable non-JSON body) degrades immediately without entering the validation retry loop.
3. Parse the returned text and run the declared output jsonschema, then every registered semantic validator for that layer in stable order.
4. On validation failure, append each error message to the prompt and retry, up to `1 + max_retries` total calls (the initial attempt plus `max_retries` retries), leaving the original messages unchanged.
5. When the budget is exhausted, return the layer's registered degrade fallback.

Semantic validators and degrade fallbacks are registered per layer by name so changes 18–21 add their rank, reward, archetype, and whitelist checks and their template-pool/greeting fallbacks without editing the pipeline. The guardrail returns a Deferred and never writes state; its only side effects are the network calls it issues and the logged safe error summaries.

Alternative considered: fold validation into each generative module. Rejected because design §7.5 prescribes one shared retry/degrade contract and every layer must behave identically offline.

### D5. FakeLLMClient is a real Deferred-returning double with scriptable failure modes

`world/ai/fake_client.py` defines `FakeLLMClient` with the same `get_response` interface as `OpenAICompatClient`. It resolves recorded fixtures keyed by a stable request matcher, and supports scripted failure modes (timeout, HTTP error, connection error, unparseable non-JSON body) keyed the same way, so guardrail tests can drive the degrade path without a network. Because unparseable bodies are transport failures per the guardrail contract, validation retries are exercised with fixtures that parse as JSON but fail the declared output schema. Unmatched requests errback with a named missing-fixture error.

Because it returns real Deferreds and honors the same failure signatures, guarded pipelines run against it with no behavioral branching. The generative test rule from design §10 is enforced by convention and by a repo-level contract check with a precise boundary: `world/ai/client.py` is the only module allowed to import the live transport (`OpenAICompatClient`, Evennia's `LLMClient`, or a Twisted `Agent`); `guardrail.py`, `profiles.py`, schemas, the fake client, and future layer modules must consume transport only through an injected client protocol, and tests must never construct `OpenAICompatClient`.

Alternative considered: patch the real client with `Mock`/`patch`. Rejected because `Mock` bypasses the Deferred interface and the failure-signature contract that the guardrail depends on.

### D6. Schemas live in the existing `world/ai/schemas/` seam

The package already declares `world/ai/schemas/` for generative-layer data. This change adds only the chat-completion response envelope schema used by the client's parse path and by guardrail output validation, plus a small registry seam for caller-supplied per-call output schemas. Layer output schemas (rank, reward, archetype, prototype) are owned by changes 18–21 and are explicitly out of scope here; the guardrail accepts an output schema as a per-call descriptor argument so later layers supply their own without touching this change's code.

Alternative considered: move schemas into the guardrail module. Rejected because the design's directory layout fixes `world/ai/schemas/` as the schema home.

## Risks / Trade-offs

- [Evennia's `LLMClient` internals are lightly tested upstream and assume one global endpoint] → Keep the subclass surface small, override only the config/payload/parse/timeout/reactor seams, preserve the contrib-matrix import test, and pin each overridden seam with focused unit tests.
- [A timed-out request's underlying HTTP exchange may not be fully cancelled on timeout] → The returned Deferred errbacks on schedule so callers never hang; the client aborts the request to the extent Twisted's `Agent` supports and the connection pool bounds lingering sockets. Timeout coverage includes the response-body phase.
- [Real-reactor dependencies make unit tests slow or flaky] → The subclass rebuilds its pool and agent on an injected reactor/clock (D1) so tests advance time deterministically with `task.Clock` instead of patching the global reactor.
- [Django settings import time can be awkward for a module-level registry] → Build and validate the profile registry at construction time through an explicit factory call, and keep the module import side-effect-free so tests can override `LLM_PROFILES` freely.
- [The live transport could leak into deterministic or layer code] → Enforce a precise contract: only `world/ai/client.py` may import `OpenAICompatClient`/`LLMClient`/Twisted `Agent`; guardrail and friends consume transport through an injected client protocol; a repo-level contract test checks imports and that tests never construct the real client.
- [Local-first defaults could still point at a non-Ollama backend] → `supports_response_format` defaults false, base URL only ever comes from `OLLAMA_BASE_URL` or the localhost fallback, the endpoint path is fixed to `/v1/chat/completions`, and both runtime defaults (bare-metal localhost and compose-injected host endpoint) are tested.

## Migration Plan

1. Add `world/ai/profiles.py` (frozen profile, strict validation, `get_profile`), `world/ai/client.py` (`OpenAICompatClient`), `world/ai/guardrail.py` (pipeline + hook registries), `world/ai/fake_client.py`, and `world/ai/schemas/` response-schema additions, each with package-local unit tests.
2. Add `LLM_PROFILES` defaults to `server/conf/settings.py` deriving `base_url` from `OLLAMA_BASE_URL`.
3. Run the focused `world.ai` tests, then the full Evennia suite, spec-traceability check, and strict OpenSpec validation.

No persisted-game-data migration applies: this change stores nothing in the DB, so rollback is a clean removal of the new modules, the settings block, and their tests. No production layer consumes this foundation until changes 18–21 land.

## Open Questions

None. The client contract, profile shape, guardrail stages, degrade behavior, and offline test rule are fixed by the approved engine design (§4, §7.5, §10, D6) and the delta specs above.
