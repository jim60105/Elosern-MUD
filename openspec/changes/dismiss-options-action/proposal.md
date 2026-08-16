## Why

The AI action-option surface can show suggestions the player does not want, and a cached set the player dismissed must not come back with the AI's cached content (user-confirmed: dismissal clears the display *and* the cache so re-entry regenerates). There is no player-facing way to clear it today. In parallel, the round-three architecture review pinned session targeting for the suggestion state: the dispatcher already holds the session, so adapters must be able to receive it — which requires a fixed adapter ABI rather than the current two-parameter one. This change lands both together: the `options.dismiss` action and the unified three-parameter adapter ABI.

## What Changes

- New action `options.dismiss` in `web/webclient/actions/options.py` with payload validator requiring exactly `{}`; the adapter calls the service's `evict(session, actor)` (change `action-options-trigger-service`) with the dispatcher-held session, then returns success declaring `affected_panels=("context_actions",)` so exactly one publication — via the normal completion path — renders `suggestions.status="unavailable"` from state.
- **BREAKING (internal only):** the adapter ABI becomes `adapter(actor, payload, session=None)` for **every** registered adapter; `ActionSpec` typing and `_invoke_adapter` update in the same change, and the dispatcher passes the authenticated session positionally with no runtime signature introspection. Existing two-argument direct adapter invocations (tests) remain valid through the default.
- `options.dismiss` joins `build_production_action_registry()`; the registered-action allowlist contract (`webclient-action-dispatch`) is updated.
- Design-doc amendments: `evict` is state-only (cache/memo/options-state mutation); the dismissal's single publication happens through the dispatcher completion path, never directly from `evict`. This contract is pinned **here** and amends both `trigger-service-design.md` §4 (which today describes `evict` publishing) and `webclient-design.md` §5 (which today says `evict` publishes), so the not-yet-written `action-options-trigger-service` change must adopt it.

## Capabilities

### New Capabilities
- `dismiss-options-action`: the `options.dismiss` action contract (exact empty payload, thin adapter, state-backed unavailable publication through `evict`), and the unified three-parameter adapter ABI with session injection.

### Modified Capabilities
- `webclient-action-dispatch`: the registered-allowed-action list gains `options.dismiss` (requirement and its production-registry scenario), and a new requirement pins the optional-session adapter ABI without introspection.

## Impact

- `web/webclient/actions/registry.py`: `ActionSpec.adapter` annotation; `dispatcher.py::_invoke_adapter` call shape.
- Every production adapter module (combat, services, creation, exploration) and `web/webclient/actions/options.py` (new): signature updates in one change.
- `build_production_action_registry()`: gains the dismiss action; registry-locked tests updated.
- Depends on `action-options-trigger-service` (`evict`, `options_state`, push seam — scaffolded, not yet implemented) and `context-actions-suggestions` (the `suggestions` field the publication renders).
- No player command changes (`game-command-docs` untouched); no OOB message or panel-schema changes; dock/choice-point dismiss controls are rendering work in a later change.