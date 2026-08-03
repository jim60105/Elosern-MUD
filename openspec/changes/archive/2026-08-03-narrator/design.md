## Context

The deterministic engine is complete and playable (change-16 milestone). Change 17 supplied the generative foundation: `OpenAICompatClient`, per-layer `LLM_PROFILES` (including the `narrator` layer), the validation–retry–degrade guardrail with per-layer semantic-validator and degrade-fallback registries, `FakeLLMClient`, and the schema registry seam. No layer consumes that foundation yet.

Design §7.3 fixes the Narrator's contract: it is a *pure function* `EventLog → Traditional Chinese prose`, has no access to a write API, returns plain text that is never parsed back, and — critically — **if the Narrator fails, the game remains fully playable, with prose degraded to template rendering**. Design §7.5 fixes the degradation: the `narrator` layer falls back to template-rendering the EventLog. Design §10 fixes the test rule: generative tests use `FakeLLMClient` and never contact a real endpoint.

Two architectural constraints shape every decision here:

1. **The single-writer / transport boundary.** No module under `world/ai/` imports a state writer (`world.rules`, `world.maps`, `world.quests`, `typeclasses`, spawner, create). The repository-wide contract test (`tests/test_ai_transport_contract.py`) also bans `world/rules`, `world/maps`, `world/quests`, and `commands` from referencing `world.ai`, and bans every `world/ai` production module except `client.py` from importing the live transport. Consequences: the Narrator must consume the client through an injected protocol, it must **not** import `world.rules.event_log`, and it cannot be wired into the deterministic emission path (`world/rules/combat_result.py`, `commands/action.py`) at all.
2. **The deterministic renderer is read-only and belongs to `world/rules`.** `render_plain_text(event_log)` is the canonical template renderer. The Narrator needs it only for degradation, but cannot import it — so it must be injected from the registration site (which may import both worlds).

The change-17 foundation explicitly defers layer content: "No production layer consumes this foundation until changes 18–21 land." Change 18 therefore delivers the Narrator as a consumable, fully guarded seam rather than rewiring player-facing presentation (that wiring belongs to the webclient narrative changes, which sit outside `world/rules`/`commands` and may import `world.ai`).

## Goals / Non-Goals

**Goals:**

- Provide `world/ai/narrator.py` with `narrate_event_logs(event_logs, client) -> Deferred[str]`, mapping deterministic EventLog data to Traditional Chinese prose through the `narrator` layer's guarded pipeline. `client` is a **required** injected argument: the module must never construct or import a live transport, and a call with `client=None` (or an omitted client) must fail with a named `NarratorClientRequiredError` before any transport interaction, rather than crashing on `None.get_response()` inside the guardrail.
- Provide `build_narrator_prompt(event_logs)` — deterministic, bounded, entity-key-only prompt construction that instructs the model to narrate exactly the recorded events and never invent outcomes, numbers, or state.
- Register the `narrator` layer's guardrail hooks: semantic prose validators (non-empty, bounded length, at least one CJK ideograph for Traditional Chinese, no leaked template placeholders) and a degrade fallback that renders the same EventLogs through the injected template renderer.
- Provide `register_narrator(template_renderer)` so production wires the deterministic `render_plain_text` (or a join of it) from the registration site, keeping `world/ai/` free of `world.rules` imports. The registration gate is bound to the guardrail's actual registry state, so a `NarratorNotRegisteredError` fires whenever the narrator hooks are genuinely absent — including after a test has reset the shared registries.
- Preserve the single-writer and transport boundaries exactly as the existing contract test enforces them, and keep every generative test offline via `FakeLLMClient`.

**Non-Goals:**

- Wiring the Narrator into `world/rules/combat_result.py`, `commands/action.py`, `commands/combat.py`, or any webclient adapter. Those paths cannot import `world.ai` (deterministic packages) or are owned by later webclient narrative changes. This change ships the seam, not the splice.
- Structured/JSON narration output, tool calls, or streaming. Narrator output is free prose, so the call carries no output schema and never requests `response_format`.
- Any change to `world/rules/event_log.py`, `world/ai/guardrail.py`, `world/ai/client.py`, or `world/ai/profiles.py`; all of those contracts are frozen by changes 8/17.
- New settings keys, dependencies, container changes, or persisted-data migrations. `LLM_PROFILES["narrator"]` already exists with the local-first default.
- Backward-compatibility adapters; the project is unreleased.

## Decisions

### D1. `narrate_event_logs` is a thin guarded mapping that consumes the client by injection

`narrate_event_logs(event_logs, client)` builds a `ChatRequestDescriptor` whose `messages` come from `build_narrator_prompt(event_logs)` and no `output_schema`, then yields the `narrator` layer's `guarded_call("narrator", client, descriptor)`. **`client` is a required positional argument and is validated at the top of the function**: the first statement rejects `client is None` with a named `NarratorClientRequiredError` errback before any prompt build or transport interaction. This covers both an omitted argument (native `TypeError` from the signature) and an explicit `None` (the named error), so an injection failure can never surface as `None.get_response()` inside the guardrail. The module never constructs, imports, or defaults a live client (it cannot: the transport contract forbids it). The client is passed in exactly like the guardrail's own callers do — `narrator.py` never imports `OpenAICompatClient`, `LLMClient`, an `Agent`, or a reactor, so the existing `tests/test_ai_transport_contract.py` stays green for the new module with no edits.

Because the narrator output is free prose, no output schema is declared; the guardrail's `_validate_output` with `output_schema=None` treats the returned text as the parsed instance and runs only the registered semantic validators. `supports_response_format` never produces a `response_format` hint because there is no schema to transmit — matching design §7.5's "only when the endpoint supports it" gating.

Alternative considered: building the request and calling `client.get_response` directly. Rejected — design §7.5 mandates the shared validation/retry/degrade pipeline, and D4 of change 17 explicitly says every layer must behave identically offline through the guardrail.

### D2. The prompt is deterministic, bounded, faithful, and entity-key-only

`build_narrator_prompt(event_logs)` returns a `(system, user)` message pair. The system message fixes the role (narrator of 伊洛瑟恩大陸), the language (正體中文), and the fidelity rule (describe exactly the recorded events; never invent outcomes, numbers, dialogue, or state; no meta-commentary; output only prose). The user message serializes the event record with `json.dumps(..., sort_keys=True, ensure_ascii=False)`:

- actor, skill_key, targets, time_cost_seconds;
- every entry's `kind`, `actor`, `target`, and `data`, plus its `text_template` as the faithful canonical baseline;
- hard bounds: a fixed maximum number of entries (later entries truncated with an explicit marker), per-field string-length caps, a bounded total, and structural caps on log count, per-log target count, and per-node `data` item count — so a large combat round, a wide encounter, or pathological inputs cannot produce an unbounded prompt. If the serialized text still exceeds the total bound, trailing entries and then whole logs are dropped (each drop updating the truncation marker) until the result fits; the user message is therefore always valid, parseable JSON within `MAX_TOTAL_SIZE`, never a mid-string slice.

The prompt contains only entity **keys** and plain JSON-compatible data — never live entity references — consistent with the change-8 `EventLog` contract that EventLogs are entity-key-only and JSON-round-trippable. Determinism (sorted keys, stable ordering) makes the same EventLog always produce byte-identical prompts, satisfying the project's replayability and reproducibility rules.

**Overflow strategy.** Because the model can only narrate what the prompt shows it, silently dropping entries above the cap would contradict the "narrate exactly the recorded events" instruction. The overflow policy is therefore explicit: when the input exceeds the prompt bounds, `narrate_event_logs()` resolves directly to the injected template renderer's output for the **full** event set instead of sending a truncated prompt. The prompt builder still documents and tests the bounded serialization, but the narrate entry point never claims completeness it cannot deliver — truncation is reserved for the deterministic template path, where it is lossless-by-construction. This keeps the "faithful to the record" contract honest for both the bounded and unbounded cases.

Alternative considered: sending the raw `text_template` only, or a free-form natural-language summary. Rejected — the raw template alone under-specifies the structured data the model must narrate, and a pre-summarized natural-language prompt would be a second, unverified narration step before the LLM.

### D3. Degradation uses a sentinel fallback mapped to an injected template renderer

The guardrail's registered degrade fallback is a zero-argument, global-per-layer callable — it cannot know which EventLogs the failing call was narrating. `register_degrade_fallback`'s contract (change 17) is "return the layer's registered degrade fallback rather than raising"; the Narrator therefore registers a **module-level sentinel** as its fallback, and `narrate_event_logs` maps that sentinel to the actual template render of *its own* event logs:

```python
_NARRATOR_DEGRADED = object()
register_degrade_fallback("narrator", lambda: _NARRATOR_DEGRADED)

# inside narrate_event_logs:
result = yield guarded_call("narrator", client, descriptor)
if result is _NARRATOR_DEGRADED:
    return _template_renderer(event_logs)
return result
```

`_template_renderer` is installed by `register_narrator(template_renderer)` (see D5). This covers all three degrade triggers uniformly — profile disabled, transport failure, exhausted retries — because the guardrail already short-circuits each to `_degrade(layer)`. The sentinel is a module-level `object()`, so identity comparison (`is`) can never collide with a legitimate prose string. The injected renderer receives the same `event_logs` sequence and renders each through `render_plain_text` (a pure join in production), so degraded output is byte-identical to today's deterministic emission.

**Registration gate.** The sentinel fallback, the semantic validators, and the injected renderer are installed **atomically** by `register_narrator()`. `narrate_event_logs()` begins by checking, against the **guardrail's actual registry state**, that the narrator layer is registered: it inspects `guardrail._degrade_fallbacks` for the `narrator` key holding this module's sentinel, rather than trusting a separate module-level flag that could desync from the shared registry when tests reset it. If the narrator layer is genuinely absent, it raises `NarratorNotRegisteredError` before ever reaching `guarded_call`. Because the gate reads the real registry, a test that clears the guardrail registries automatically makes the gate fire again, and the next `register_narrator()` genuinely reinstalls the hooks. This makes the "narrate before registration" case a named, deterministic error of the narrator's own instead of relying on the guardrail's `NoDegradeFallbackError`, and it removes the temptation to register hooks at module import time.

Alternative considered: catching exceptions around `guarded_call`. Rejected — `guarded_call` never raises on degrade; it returns the fallback value, so a sentinel is the only unambiguous signal. Alternative considered: registering a per-call degrade closure. Rejected — the guardrail registry is global per layer; a sentinel plus post-mapping is simpler and keeps the guardrail contract intact.

### D4. Semantic validators bound prose shape and drive retry-then-degrade

The `narrator` layer registers semantic validators under stable names so the shared pipeline retries on shape violations and degrades on exhaustion (design §7.5). Validators operate on the returned text and reject:

- empty / whitespace-only prose;
- prose exceeding a fixed length cap;
- prose containing no CJK Unified Ideograph (`\u4e00`–`\u9fff`), which means the model did not produce Traditional Chinese as the output contract requires;
- prose containing template-placeholder syntax (a `{`-`}` brace pair wrapping a known field name such as `{actor}`, `{target}`, `{data[...]}`), which indicates the model echoed the deterministic `text_template` formatting syntax rather than writing finished prose.

Each failure appends a concrete validation message to the prompt and retries within the `1 + max_retries` budget; the final fallback is the template render (D3). These are deliberately conservative shape checks, not quality scoring — the CJK check only requires *at least one* ideograph (rejecting obviously non-Chinese output) and the brace check targets known template placeholders rather than every `{`/`}` character, so legitimate prose with quotation marks or numerals is not penalized. The fidelity guarantee comes from the prompt instruction (D2), and design §7.3 says prose is never parsed back, so a slightly off-tone sentence must not trigger an unbounded retry storm.

### D5. `register_narrator(template_renderer)` wires hooks idempotently from the registration site

`register_narrator(template_renderer)` installs the sentinel degrade fallback, all semantic validators, and the injected template renderer in one operation, and marks the layer registered only after every hook is installed. It is **atomic with rollback**: if any individual hook registration fails mid-way, already-installed narrator hooks are removed so the layer is never left in a partially-registered state. Idempotence is defined precisely: a **second call is a no-op that keeps the first renderer**, and it swallows only the `GuardrailRegistrationError` that a genuine duplicate registration of this module's own hooks raises — it does not silently override an incompatible registration. If a caller passes a second, different renderer, the first is retained and documented.

Tests that reset the shared guardrail registries between cases (as `test_guardrail.py` already does) re-call `register_narrator` with a fresh stub in `setUp`; because the D3 gate reads the actual registry, a reset automatically forces the next call through the not-registered path, and `register_narrator` reinstalls the hooks from scratch rather than trusting a stale flag.

Production calls it once from `server/conf/at_server_startstop.py`'s `at_server_start()` hook (after `evennia._init()` has populated `evennia.logger`):

```python
def _register_narrator_layer():
    from world.ai.narrator import register_narrator
    from world.rules.event_log import render_plain_text

    register_narrator(
        lambda event_logs: "\n".join(render_plain_text(log) for log in event_logs)
    )
```

This is the only place that imports `world.rules` on the narrator's behalf; it is outside `world/ai/`, so the contract test is unaffected. **It must run after `evennia._init()`.** The guardrail module performs `from evennia import logger` at import time, so importing `world.ai.guardrail` during settings load (before `evennia._init()`) would permanently bind the module's `logger` name to `None` and break every degrade path — a class of bug the settings-load integration test would never catch because `settings.py` is imported before evennia initializes. The `at_server_start` hook is the earliest point guaranteed to be post-`_init`, and it already runs the deterministic startup syncs, so the narrator registration sits beside them. `world.rules.event_log` is a pure dataclass module with no model imports, so importing it there is safe. The startup path is locked with one integration test that invokes the registration seam and asserts the narrator layer is registered with a working renderer.

The seam is also **boot-tolerant**: a pre-existing `narrator` registration (a foreign one left by an earlier in-process test, for example — `test_guardrail`'s `GuardrailPipelineTests` registers a plain narrator fallback and never unregisters it) must never abort server startup. `register_narrator` itself still surfaces the guardrail's error rather than silently overriding the foreign hooks, and `narrate_event_logs`' D3 gate still fails loudly with `NarratorNotRegisteredError` when the installed fallback is not this module's sentinel, so correctness is preserved even when the startup seam swallows the conflict and logs a warning.

Alternative considered: importing `render_plain_text` directly inside `narrator.py`. Rejected — that would import a `world.rules` module from `world/ai/`, violating `test_no_ai_module_imports_a_state_writer`. Injection is the only route that satisfies the frozen contract.

### D6. No deterministic-path wiring in this change

`commands/action.py`, `commands/combat.py`, and `world/rules/combat_result.py` currently render EventLogs with `render_plain_text`. The transport contract forbids those packages from referencing `world.ai`, so they cannot call the Narrator, and `web/webclient/actions/combat_actions.py` is owned by the archived `webclient-combat-menu` capability whose contract is "preserve narrative logs" on the deterministic text channel. Rewiring presentation here would either break the frozen import contract or modify an archived capability. The Narrator is therefore delivered as a consumable seam: `narrate_event_logs` + registered hooks, ready for change 20/21 and the webclient narrative changes to call. Offline playability is preserved by construction — the deterministic game loop is byte-identical and never imports the Narrator.

## Risks / Trade-offs

- [The guardrail's zero-arg registered fallback cannot render a specific EventLog] → D3's sentinel-then-map: the registered fallback returns a sentinel, and `narrate_event_logs` maps it to the injected renderer over the actual logs. The guardrail contract ("return the layer's registered fallback") is satisfied, and the per-call renderer knows the real logs.
- [`world/ai` cannot import `world.rules`, so the template renderer must be injected] → D5: `register_narrator` accepts the renderer and is called from `server/conf/settings.py`, which may import both worlds. A call before registration raises the named `NarratorNotRegisteredError` via the D3 registration gate, never a silent crash or fabricated prose.
- [`client=None` would crash inside `guarded_call`] → D1 makes the client a required argument and rejects an explicit `None` with `NarratorClientRequiredError` before any prompt or transport work; the missing-client path is tested for both the omitted-argument and explicit-`None` cases.
- [A module flag could desync from the shared guardrail registry] → D3 binds the registration gate to the guardrail's actual `_degrade_fallbacks` state, and D5 makes `register_narrator` atomic-with-rollback and idempotent-by-registry, so test resets can neither fake a registered layer nor strand a half-installed one.
- [Prose could drift from the recorded events] → D2's explicit fidelity instruction plus D4's shape validators (including the CJK-present check) bound the failure mode; design §7.3 makes prose display-only (never parsed back), so drift is cosmetic, never state-corrupting.
- [A long combat round could blow up the prompt] → D2 caps entry count, per-field length, and total prompt size deterministically, and the overflow policy resolves an oversized input directly to the lossless template render instead of narrating a truncated record.
- [Registration order at server startup] → `register_narrator` runs from `at_server_start` after `evennia._init()` (so the guardrail's import-time `from evennia import logger` binds the real logger, not `None`), is idempotent, and `world.rules.event_log` imports no models; one startup integration test invokes the seam and locks the path. Tests re-register fresh stubs in `setUp` to isolate from shared registry resets.
- [Duplicate registration could silently override hooks] → D5 defines idempotence narrowly: only this module's own re-registration is a no-op retaining the first renderer; incompatible registrations surface the guardrail's error.
- [Live transport leaking into the narrator] → the module imports only `guardrail`, `profiles`, `schemas.descriptor`, and `defer`; the existing contract test scans it automatically and fails the build if that changes.

## Migration Plan

1. Add `world/ai/narrator.py` (prompt builder, `narrate_event_logs`, `register_narrator`, sentinel, semantic validators) with package-local tests under `world/ai/tests/test_narrator.py`.
2. Add the one-line `register_narrator(...)` call to `server/conf/at_server_startstop.py`'s `at_server_start()` hook (the post-`evennia._init()` seam), plus one startup integration test that invokes the registration seam and asserts the narrator layer is registered with a working renderer.
3. Run the focused `world.ai` tests, then the repository-wide contract test, the full Evennia suite, the spec-traceability check, and strict OpenSpec validation.

No persisted-game-data migration applies: this change stores nothing in the DB and changes no deterministic behavior, so rollback is a clean removal of the new module, its tests, and the settings registration line. No production layer consumes the Narrator until later changes land.

## Open Questions

None. The Narrator's input (EventLog), output (free Traditional Chinese prose), degradation (template render), boundary constraints (injected client, injected renderer, no state writers), and test rule (FakeLLMClient only) are all fixed by the approved engine design (§3.3, §7.3, §7.5, §10) and the change-8/change-17 contracts.
