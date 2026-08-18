## Purpose

The `options.dismiss` action: an exact-empty-payload UI action that clears the AI action-option display and its caches through the trigger service's per-session eviction, plus the unified three-parameter adapter ABI (`adapter(actor, payload, session=None)`) that makes dispatcher-held session targeting possible without runtime introspection.

## ADDED Requirements

### Requirement: The dismiss action accepts exactly an empty payload

The `options.dismiss` action SHALL be registered in the production action registry with a payload validator accepting exactly the empty object `{}` and no other value, and with `affected_panels=("context_actions",)`. A payload carrying any field or a non-object SHALL be rejected as `malformed_payload` without invoking the adapter.

#### Scenario: An empty payload dispatches

- **WHEN** a puppeted WebClient submits `options.dismiss` with `payload: {}` and a current epoch/revision
- **THEN** the action passes admission and the dismiss adapter runs

#### Scenario: A non-empty payload is rejected before the adapter

- **WHEN** a client submits `options.dismiss` with an extra field, a list, or a non-object payload
- **THEN** the dispatcher returns a `malformed_payload` rejection and the adapter does not run

### Requirement: Dismiss clears the displayed proposal state through per-session eviction

The dismiss adapter SHALL call the trigger service's `evict(session, actor)` with the dispatcher-held session, which SHALL evict the session's displayed fingerprint from the global cache and negative memo, invalidate that session's in-flight generation (token bump), set its `options_state` to `unavailable`, and leave every other session's state, tokens, and cached publications untouched.

#### Scenario: A dismiss in one window leaves the other window intact

- **WHEN** a puppeted player dismisses suggestions in window A while window B still shows a ready set
- **THEN** window A's options state becomes `unavailable` and its cached fingerprint is evicted, while window B's state, token, and future publications are unchanged

#### Scenario: A later trigger for the dismissed situation regenerates

- **WHEN** the player dismisses and then returns to (or re-enters) the same situation
- **THEN** the service schedules a new generation rather than replaying the evicted cached set

### Requirement: Dismissal publishes exactly one state-backed unavailable update

The dismiss adapter SHALL NOT send any message itself. Its success result SHALL declare `affected_panels=("context_actions",)`, so the normal dispatcher completion publication builds the panel from the now-`unavailable` `options_state` and emits exactly one `ui_update` with `suggestions.status == "unavailable"` before the matching success result.

#### Scenario: Dismiss emits one update then one result

- **WHEN** a dismiss action settles successfully
- **THEN** the session receives exactly one `ui_update` whose `context_actions.suggestions.status` is `unavailable`, followed by a `ui_action_result` naming the same revision, and no additional presentation send from the eviction path

### Requirement: Adapters receive the authenticated session through a fixed optional parameter

Every registered adapter SHALL declare the callable signature `adapter(actor, payload, session=None)`, and the dispatcher SHALL invoke it with the authenticated session as the third positional argument. The dispatcher SHALL NOT use runtime signature introspection to decide what to pass. Two-argument invocations of an adapter (direct test calls) SHALL remain valid through the default. The session SHALL be used only for per-session presentation targeting (for example dismiss eviction); adapters SHALL NOT read or write character state through it.

#### Scenario: A proof adapter receives the session

- **WHEN** a proof adapter is dispatched in a test with the registry's current ABI
- **THEN** it receives the exact authenticated session as its third argument and the exact puppet as the first

#### Scenario: A two-argument direct call still works

- **WHEN** a test invokes a production adapter directly as `adapter(actor, payload)`
- **THEN** the call succeeds with `session=None` and behaves exactly as before this change

#### Scenario: No introspection at the call site

- **WHEN** the dispatcher invokes any adapter
- **THEN** it always passes the session positionally and never inspects the callable's signature