## ADDED Requirements

### Requirement: Browser test waits gate on deterministic state within a bounded deadline
The managed Playwright acceptance journeys SHALL gate every test wait by polling the committed
store view and, where an assertion is genuinely DOM-bound, the surface DOM, within a single
bounded monotonic deadline. Waits SHALL NOT depend on a single raw DOM-visibility wait that a
delayed server publish or client render would exhaust under a loaded CI runner. The shared wait
helper in `web/tests/browser/browser_helpers.py` SHALL expose one bounded polling loop that
reads the committed store view (via `store_state_or_none`, tolerating a one-shot recovery reload),
SHALL accept an optional DOM-readiness predicate that is evaluated within the same polling loop
under the same monotonic deadline (so the store gate and the DOM gate share one bounded window),
SHALL treat a `None` store read (mid-reload) as "not ready yet" without invoking the store
predicate on `None`, and SHALL raise an `AssertionError` on timeout carrying the last non-`None`
store state, whether any `None` reads occurred, the last evaluation error, and — where a
DOM-readiness predicate is supplied — the relevant selector's connected/visible/enabled state and
the current `activeElement`. Focus operations (e.g. `focus_action_dock`) SHALL gate on the store
state first, then poll the target element's DOM readiness in the same loop, then verify
`document.activeElement` is the target or its delegated focus target.

#### Scenario: A journey wait is gated on the store state
- **WHEN** a browser journey waits for a gameplay surface to become available or a mode to change
- **THEN** the wait polls the committed store view (and the surface DOM only where the assertion
  is DOM-bound) within a single bounded deadline, and does not depend on a single raw-visibility
  wait that a delayed render under a loaded CI runner would exhaust

#### Scenario: A bounded wait failure reports the last observed state
- **WHEN** a bounded wait exhausts its deadline
- **THEN** the helper raises an `AssertionError` carrying the last non-`None` store state, whether
  `None` reads occurred, the last evaluation error, and — when a DOM predicate is present — the
  selector's connected/visible/enabled state and the `activeElement`, so the failure is a precise
  diagnostic rather than a bare `TimeoutError`

#### Scenario: A focus wait verifies the focused element
- **WHEN** a journey focuses the action dock
- **THEN** it first gates on the store state, then polls the dock's DOM readiness in the same
  bounded loop, focuses it, and verifies `document.activeElement` is the dock or its delegated
  focus target, so a swallowed focus fails with a precise diagnostic instead of a bare timeout
