## 1. Unified adapter ABI

- [x] 1.1 Update `ActionSpec.adapter` typing in `web/webclient/actions/registry.py` to the `(actor, payload, session=None)` callable shape
- [x] 1.2 Update `_invoke_adapter` in `web/webclient/actions/dispatcher.py` to pass `(actor, normalized, session)` positionally with no signature introspection
- [x] 1.3 Migrate every registered adapter in one change: combat (`combat_actions.py`), services (`guild_actions.py`, `shop_actions.py`), creation, exploration (`exploration_actions.py`) — all become `adapter(actor, payload, session=None)`; behavior unchanged
- [x] 1.4 Migrate **test-owned registered adapters** too: inventory every `ActionSpec` installed by tests (dispatcher proof adapter lambdas and any other test registry) and give them the same three-parameter shape with a `session=None` default, so unconditional session injection cannot raise `TypeError` into the internal-error path
- [x] 1.5 Tests: a proof adapter dispatched through the registry receives the exact session third; a direct two-argument call of a three-parameter adapter behaves as before (`session=None`); the dispatcher never introspects (assert the call site passes three arguments unconditionally)

## 2. `options.dismiss` action (`web/webclient/actions/options.py`)

- [x] 2.1 Add `validate_options_dismiss_payload`: accepts exactly `{}`, rejects any other value
- [x] 2.2 Add the dismiss adapter: calls `evict(session, actor)` (service API from `action-options-trigger-service`) with the dispatcher-held session, wrapped in the standard rejection discipline, then returns success with `affected_panels=("context_actions",)`; `evict` itself never sends
- [x] 2.3 Register `options.dismiss` in `build_production_action_registry()`
- [x] 2.4 Unit tests: empty payload dispatches; non-empty payload rejects as `malformed_payload` without adapter invocation; adapter failure maps to a rejection

## 3. Publication and registry contract

- [x] 3.1 Enforce the single-publication rule in tests: a dismiss settlement emits exactly one `ui_update` with `context_actions.suggestions.status == "unavailable"` followed by a success result naming the same revision, and no extra send from the eviction path (service stub records no publish)
- [x] 3.2 Update the registry-locked contract test to include `options.dismiss` (exact production action-ID set)
- [x] 3.3 Integration test (service boundary mocked, not re-implemented): the dismiss adapter calls exactly `evict(session, actor)` with the dispatcher-held session; dismiss in window A publishes exactly one `ui_update` (state-backed) while window B's state and token remain untouched per the mocked service contract — cross-session token/cache semantics themselves are owned by `action-options-trigger-service`

## 4. Design-doc amendment and handoff

- [x] 4.1 Amend both upstream design documents to the state-only `evict` contract: `docs/superpowers/specs/2026-08-15-ai-action-options-trigger-service-design.md` §4 step 4 (remove the publish step from `evict`'s own description; the completion path is the single publication site) and `docs/superpowers/specs/2026-08-15-ai-action-options-webclient-design.md` §5 (reword "publishes suggestions.status" to "the completion publication renders suggestions.status from the mutated state")
- [x] 4.2 Add `covers_requirement` annotations to the new dismiss/ABI requirements; run the affected package tests (`web.webclient` + `evennia test` touch scope) and `uv run --locked python -m tools.spec_traceability check`