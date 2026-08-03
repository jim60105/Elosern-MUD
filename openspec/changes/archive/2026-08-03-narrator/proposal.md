## Why

The change-16 milestone left the game fully playable offline, and change 17 delivered the generative foundation — `OpenAICompatClient`, per-layer `LLM_PROFILES`, the validation-retry-degrade guardrail, and `FakeLLMClient` — but no layer consumes it yet. The Narrator is the first generative consumer: it is the pure-function mapping from a deterministic `EventLog` to Traditional Chinese prose (design §7.3), and it is the load-bearing seam that must keep the game fully playable when the LLM is slow, wrong, or entirely offline. Change 18 builds that layer now, so later generative layers (ScenarioDirector, SceneBuilder, NPC dialogue) and the webclient narrative panels can consume the same guarded, degradable path instead of each re-inventing transport handling.

## What Changes

- Add `world/ai/narrator.py` with `narrate_event_logs(event_logs, client) -> Deferred[str]`, a pure mapping from deterministic EventLog data to Traditional Chinese prose that runs the `narrator` layer's guarded pipeline (design §7.5) and resolves to the recorded event description, never parsed back. The client is a required injected argument, mirroring the guardrail's own callers; when the input exceeds the prompt bounds, or the layer is disabled/unreachable/retry-exhausted, the call degrades to the deterministic template rendering of the same EventLogs instead of inventing a truncated narration.
- Add `build_narrator_prompt(event_logs)` that serializes the event record deterministically and with hard bounds (capped entry count, truncated string fields, entity keys only, no live references) and instructs the model to narrate exactly the recorded events without inventing outcomes, numbers, or state.
- Register the `narrator` layer's guardrail hooks: semantic validators (prose non-empty, bounded length, contains at least one CJK ideograph, no leaked template placeholders) that drive validation retries, and a degrade fallback that renders the same EventLogs through the deterministic template path.
- Add `register_narrator(template_renderer)` so the deterministic renderer is injected from the registration site (production supplies `render_plain_text`), keeping `world/ai/` free of any `world.rules` import while preserving byte-identical degrade output. `narrate_event_logs()` raises a named `NarratorNotRegisteredError` when the layer hooks are not installed yet, and rejects an explicit `None` client with a named `NarratorClientRequiredError` before any transport work, so a missing renderer or client never silently fabricates prose or crashes inside the guardrail.
- Keep the single-writer and transport boundaries intact: `narrator.py` imports no state writer, no live transport, and no socket; it consumes the client through an injected protocol exactly like `guardrail.py`; tests use `FakeLLMClient` only, per design §10.
- Add no backward-compatibility adapter or persisted-data migration; the project is unreleased. The Narrator layer is delivered as a consumable seam; player-facing presentation wiring belongs to the webclient narrative changes, not this one.

## Capabilities

### New Capabilities

- `narrator`: The generative EventLog-to-prose mapping — deterministic, bounded prompt construction from EventLog data; a guarded, Deferred-returning narrate entry point; semantic prose validation; and degrade-to-template rendering so the game remains fully playable with the LLM offline.

### Modified Capabilities

- None. The `llm-profiles` spec already names `narrator` as one of the four layer keys, and the `guardrail` spec already supports per-layer semantic-validator and degrade-fallback registration, so no existing requirement changes. The repository-wide transport-boundary contract (`tests/test_ai_transport_contract.py`) already scans every production module under `world/ai/` and will enforce the new module's compliance without modification.

## Impact

- Adds `world/ai/narrator.py` and package-local tests under `world/ai/tests/test_narrator.py`.
- Adds narrator-layer hook registration (semantic validators + degrade fallback wired to `render_plain_text`) to `server/conf/at_server_startstop.py`'s `at_server_start()` hook — the earliest point guaranteed to run after `evennia._init()`, because `world.ai.guardrail` captures `evennia.logger` at import time and registering during settings load would break every degrade path.
- Subclasses nothing new; consumes the change-17 `guardrail`, `profiles`, `schemas.descriptor`, and the existing deterministic `world.rules.event_log` template renderer through an injected callable.
- No container, dependency, or settings-schema change beyond the startup registration line; `LLM_PROFILES["narrator"]` already exists with the local-first default.
- Establishes the Narrator interface consumed by change 20 (ScenarioDirector) and 21 (SceneBuilder) and by webclient narrative presentation; those consumers remain outside this change.
