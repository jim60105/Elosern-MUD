## Why

The deterministic game is complete and playable (the change-16 milestone), but the generative half of the product — Narrator, NPC dialogue, ScenarioDirector, SceneBuilder — has no foundation. Every later generative change needs one OpenAI-compatible async client, per-layer model selection, and a guardrail that keeps the deterministic game fully playable when the LLM is slow, wrong, or entirely offline. Change 17 supplies that foundation now, independently of any specific layer.

## What Changes

- Add `world/ai/client.py` defining `OpenAICompatClient`, a subclass of Evennia's `LLMClient` that keeps the Twisted async skeleton and overrides the payload for OpenAI's `/v1/chat/completions`, returning `choices[0].message.content`; local-first by default via `OLLAMA_BASE_URL`.
- Add `world/ai/profiles.py` and the `LLM_PROFILES` setting: named per-layer profiles (`narrator`, `npc_dialogue`, `scenario_director`, `scene_builder`), each an OpenAI-compatible endpoint configuration (base URL, path, headers, model, temperature, max tokens, request timeout, retry count, structured-output capability, enabled flag), validated at startup with sane local defaults.
- Add `world/ai/guardrail.py`: the validation–retry–degrade pipeline from design §7.5 — local jsonschema validation against each call's declared output schema, pluggable semantic-validator hooks, bounded retries that append the validation error message, and a registered per-layer degrade fallback. `response_format`/json-schema is requested only when the profile declares endpoint support.
- Add `world/ai/fake_client.py` defining `FakeLLMClient`, a deterministic fixed-JSON replay double with the same Deferred-returning interface; tests never contact a real endpoint, per design §10.
- Add the OpenAI chat-completion response envelope schema under `world/ai/schemas/` and a registry/interface seam that accepts caller-supplied per-call output schemas. No layer-specific output schema (rank, reward, archetype, prototype) is defined in this change; those belong to changes 18–21.
- Keep the single-writer invariant: no module under `world/ai/` mutates game state. Only `world/ai/client.py` owns the live transport; `guardrail.py`, `profiles.py`, schemas, and the fake client never import a network client and consume transport through an injected interface.
- Keep the single-writer invariant: no module under `world/ai/` mutates game state; the client, profiles, and guardrail only read configuration and emit validated proposals for later layers to submit.
- Add no backward-compatibility adapter or persisted-data migration; the project is unreleased. No production layer consumes this foundation in this change.

## Capabilities

### New Capabilities

- `llm-client`: OpenAI-compatible asynchronous client transport, including the `/v1/chat/completions` payload, response parsing, Twisted async error handling, request timeouts, and the local-first Ollama default.
- `llm-profiles`: The `LLM_PROFILES` settings registry with per-layer endpoint configuration, startup validation, structured-output capability flags, and offline-disable semantics.
- `guardrail`: The validation–retry–degrade pipeline — local jsonschema validation, semantic-validator hooks, bounded error-appending retries, registered degrade fallbacks, and offline-playability guarantees.
- `fake-llm-client`: The deterministic replay test double used by every generative-layer test so no suite depends on a network service.

### Modified Capabilities

- None. The client reads the existing `OLLAMA_BASE_URL` environment variable already declared by `container-image`/compose; no existing requirement changes. The compose/image/env contract, including the container default `host.containers.internal:11434`, is untouched — this change only adds an application-side consumer of that variable, so no `container-image` delta is needed.

## Impact

- Adds `world/ai/client.py`, `world/ai/errors.py`, `world/ai/profiles.py`, `world/ai/guardrail.py`, `world/ai/fake_client.py`, `world/ai/schemas/*`, package-local tests under `world/ai/tests/`, and a repository-wide transport-boundary contract test under `tests/`.
- Adds `LLM_PROFILES` and its helper settings to `server/conf/settings.py`, defaulting from the `OLLAMA_BASE_URL` environment variable.
- Subclasses `evennia.contrib.rpg.llm.llm_client.LLMClient` (verified importable in Evennia 6.1.0 by `tests/test_contrib_matrix.py`); uses the already-pinned `jsonschema` dependency.
- No container change: Ollama remains an external service reached via `OLLAMA_BASE_URL`, as `container-image` and `compose.yaml` already declare.
- Establishes the client, profile, guardrail, and fake-client interfaces consumed by changes 18 (Narrator), 19 (NPC dialogue), 20 (ScenarioDirector), and 21 (SceneBuilder); those layers remain outside this change.
