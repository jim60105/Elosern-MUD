## Context

The trigger service (change `action-options-trigger-service`) owns `evict(session, actor)` and `session.ndb.options_state`; the `context_actions` v5 panel (change `context-actions-suggestions`) renders `suggestions` from the `options_state` snapshot on every presenter render. The round-three architecture review (rubber-duck R3-2) decided session targeting comes from the dispatcher — it already holds the session — which forces a fixed adapter ABI. The webclient dock and narrative choice-points render the dismiss control later (`webclient-options-surface`), but the action, the ABI, and the publication semantics land here.

## Goals / Non-Goals

**Goals:**
- Ship `options.dismiss` with exact-empty validation, thin adapter, and exactly one state-backed `unavailable` publication per dismissal.
- Land the unified `adapter(actor, payload, session=None)` ABI across every registered adapter in one change, with no introspection.
- Keep the dismiss semantics per-session: other windows of the same puppet are untouched.

**Non-Goals:**
- The dock/choice-point dismiss controls and card surfaces (later change).
- The service internals of eviction (cache, tokens, pending registry) — owned by `action-options-trigger-service`.
- Any new OOB message, panel-schema change, or player command.

## Decisions

### D1: `evict` is state-only; the completion path publishes

Alternatives:
- `evict` sends the `unavailable` update itself and the adapter returns success with no affected panels — two sends (evict's update + the dispatcher's required after-completion publication) or a contrived empty-affected contract.
- `evict` mutates (cache + memo + options_state) and the adapter returns `affected_panels=("context_actions",)` — the normal completion critical section builds the panel from the mutated state and emits exactly one `ui_update` before the matching result.

Chosen: the latter. `evict` never sends; the dispatcher's single publication is the only send. The upstream design documents currently describe `evict` publishing the `unavailable` state itself (`trigger-service-design.md` §4 step 4 and `webclient-design.md` §5) — **this change amends both** (task 4.1) and pins the state-only contract, so the not-yet-written `action-options-trigger-service` change adopts it. Overview A-4/D-5 do not claim a direct publish and stay as they are.

### D2: One-shot ABI migration, no introspection

Alternatives:
- Runtime signature introspection (`inspect.signature` / `len(co_signature)` with a two-arg fallback) — rejected: it makes the adapter ABI implicit, untestable, and fragile.
- Unified ABI with a defaulted third parameter for every adapter, updated in the same change, `_invoke_adapter` passing `(actor, normalized, session)` unconditionally — chosen. Two-argument direct test calls keep working through the default; the project has no released users, so no backward-compatibility layer is needed (propose.md directive).

The migration covers **every registered adapter**, including test-owned registries: dispatcher tests install `ActionSpec`s with two-parameter lambdas (and other test suites may too); once `_invoke_adapter` passes three arguments unconditionally, those would raise `TypeError` into the internal-error path. Task 1.3 therefore inventories and migrates test-owned registered adapters to `session=None` as well; the "two-argument direct call" scenario remains only as a *calling-style* test of a three-parameter adapter.

### D3: The dismiss adapter stays thin

The adapter calls `evict(session, actor)` wrapped in the same exception discipline as other adapters (a failure maps to a rejection, never raises), then returns the standard success dict (`_success("dismissed", …, ("context_actions",))`). All eviction semantics (which fingerprint, token bump, pending removal, other sessions untouched) live in the service; duplicating them in the adapter would create a second writer of options state. Because `evict` is failure-silent (rubber-duck finding: it must never raise into the dispatcher), the service returns a boolean success signal: the adapter rejects with the stable `dismiss_failed` code when `evict` reports `False` (or raises), so a failed eviction never reports success. The return-value contract is pinned in the trigger-service main spec and design doc §4.

### D4: Registration without a full-snapshot fallback

`options.dismiss` declares `affected_panels=("context_actions",)`, so the completion publication is an update, not a full snapshot. Rejection paths (malformed payload, stale, busy) keep the standard dispatcher behavior. The registry-locked contract test in `webclient-action-dispatch` is updated in this change.

### D5: Multi-session behavior is verified by wiring, not by re-implementing the service

The token/pending/cache eviction semantics live in `action-options-trigger-service` (change 5, not yet written). Change 8's tests therefore mock the service boundary: they assert the adapter calls exactly `evict(session, actor)` with the dispatcher-held session and that the dismissal produces exactly one dispatcher publication; cross-session token/cache behavior is exercised by change 5's own integration tests once the service exists (the change-5 scaffold must adopt the state-only contract pinned in D1). A stub that re-implements the service semantics would only prove the stub.

## Risks / Trade-offs

- [ABI migration touches every production adapter] → One mechanical change with a defaulted parameter; the existing adapter unit tests call adapters directly with two arguments and stay green, and the dispatcher suite asserts the three-argument call shape.
- [Double publication if `evict` and the completion path both send] → D1 makes `evict` state-only and a test asserts exactly one `ui_update` per dismissal.
- [A dismissed-but-generating session gets a late ready publish] → The token bump inside `evict` (service-owned) invalidates the in-flight completion before the publication check; the adapter test covers the wiring, the token semantics are tested in the service change.
- [Session param misused for state access] → The ABI requirement forbids reading/writing character state through the session; review happens at adapter review time.

## Open Questions

- None carried: the dismiss control's visual placement and the "clear suggestions" copy belong to the surface change.