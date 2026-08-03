## 1. Prompt construction

- [x] 1.1 Add `world/ai/narrator.py` with `build_narrator_prompt(event_logs) -> tuple[dict[str, str], dict[str, str]]` returning a deterministic system/user message pair serialized from the event record (actor, skill key, targets, time cost, and every entry's kind/actor/target/data and `text_template`) using stable sorted JSON serialization with `ensure_ascii=False`
- [x] 1.2 Enforce hard bounds in the prompt builder: a fixed maximum entry count, per-field string-length caps, and a bounded total size, truncating deterministically with an explicit marker
- [x] 1.3 Write the system message: Traditional Chinese narration of 伊洛瑟恩大陸, output-only-prose, and an explicit fidelity rule forbidding invented events, outcomes, or numbers
- [x] 1.4 Add unit tests under `world/ai/tests/test_narrator.py` proving byte-identical prompts for identical input, bounded output for oversized combat rounds, entity-key-only serialization with no live references, the fidelity instruction in the system message, and that an `overwhelm_resolution` summary entry preserves team keys and `data` within bounds

## 2. Guarded narrate entry point

- [x] 2.1 Add `narrate_event_logs(event_logs, client) -> Deferred[str]` in `world/ai/narrator.py` with the client as a required argument, that rejects an explicit `None` client with a named `NarratorClientRequiredError` before any prompt construction or transport work, builds the prompt descriptor (messages only, no output schema), and yields `guarded_call("narrator", client, descriptor)`, mapping the module-level degrade sentinel to the injected template renderer
- [x] 2.2 Add the overflow policy: when the input exceeds the prompt bounds, resolve directly to the injected template renderer's output for the full event set instead of sending a truncated prompt, making zero client calls
- [x] 2.3 Add tests proving a valid client response resolves to the prose with no state change, multiple EventLogs narrate as one coherent passage, an explicit `None` client errbacks with `NarratorClientRequiredError` before any transport work, the returned value is a plain string with no parser or write-back path, and an oversized input degrades to the full deterministic template with zero client calls

## 3. Degrade fallback and registration

- [x] 3.1 Add the `_NARRATOR_DEGRADED` sentinel (module-level `object()`), the `NarratorNotRegisteredError` and `NarratorClientRequiredError` exceptions, and a registration gate at the top of `narrate_event_logs()` that reads the guardrail's actual `_degrade_fallbacks` registry for the `narrator` layer's sentinel rather than a separate module flag
- [x] 3.2 Add `register_narrator(template_renderer)` that atomically installs the sentinel fallback and every semantic validator with rollback on partial failure, then installs the injected template renderer and marks the layer registered only after all hooks succeed; a second call is a no-op that keeps the first renderer and swallows only this module's own duplicate-registration error, never an incompatible one
- [x] 3.3 Add tests covering: disabled narrator profile returns template prose with zero client calls; transport failure and exhausted-retry degrade to template prose; degraded output is byte-identical to joining `render_plain_text` over the same EventLogs; narrating before `register_narrator()` errbacks with `NarratorNotRegisteredError`; narrating after the guardrail registries are reset (and before re-registration) again errbacks with `NarratorNotRegisteredError`; duplicate registration keeps the first renderer; and a partial hook-registration failure leaves no narrator hooks installed
- [x] 3.4 Add a startup integration test that invokes `server/conf/at_server_startstop.py`'s narrator registration seam (the post-`evennia._init()` hook) and asserts the narrator layer is registered with a working renderer

## 4. Semantic validators

- [x] 4.1 Register `narrator`-layer semantic validators rejecting empty/whitespace-only prose, prose over the length cap, prose with no CJK Unified Ideograph, and prose containing template-placeholder syntax (`{actor}`, `{target}`, `{data[...]}`)
- [x] 4.2 Add tests proving empty prose, non-Chinese prose, and template-placeholder leakage are rejected and retried with the error appended, and bounded-length Traditional Chinese prose passes on the first attempt

## 5. Boundary and settings wiring

- [x] 5.1 Verify `world/ai/narrator.py` imports no state writer, no live transport symbol, and no socket, and consumes the client and renderer only through injected protocols (repository contract test stays green with no edits)
- [x] 5.2 Add `register_narrator(lambda event_logs: "\n".join(render_plain_text(log) for log in event_logs))` to the `at_server_start()` hook in `server/conf/at_server_startstop.py` (post-`evennia._init()`), keeping `world/ai/` free of `world.rules` imports
- [x] 5.3 Run focused `world.ai` tests, the repository-wide contract test, the full Evennia suite, `python -m tools.spec_traceability check`, and `openspec validate narrator --strict`
