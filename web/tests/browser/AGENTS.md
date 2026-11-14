# Browser acceptance tests guide

These tests drive the real webclient in headless Chromium against a managed
Evennia server (`harness.py`). They are the slowest tests in the repository.
CI owns the full suite; locally you run one method, class or file at a time.

## Run one

```sh
pnpm run build
```

Run that first whenever a JS or Vue source changed since the last build. A
local run serves the prebuilt bundle in `web/static/webclient/app/dist`;
nothing rebuilds it for you, and a stale bundle gives a red or green result
that CI will not reproduce.

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.<file>.<Class>.<method>
```

Several labels may follow the driver in one command. Run the command alone:
no pipe, redirect or `;` (the test guard blocks them). Never loop over whole
files.

## Register every new test

A new test **method** has no CI owner until it is in
`.github/browser-shards.json`. In the same commit run:

```sh
uv run --locked python -m tools.shard_register fix
```

It puts the method in the process list that already runs its class, so the
class still boots its server once. If the shard then exceeds five minutes in
CI, split the file; do not move labels around by guesswork.

## Write a journey that does not race

A fixed sleep, or an assertion made right after a click, fails on a slow CI
runner. Wait for the state the server **committed**, using the helpers in
`browser_helpers.py`:

| You need to | Use |
| --- | --- |
| Log in and reach the shell | `login_and_open`, `wait_for_shell_active` |
| Wait for a store value (and optionally a DOM condition under the same deadline) | `wait_for_store_state` |
| Submit right after another action | `wait_for_submit_ready` |
| Wait until the last action's own publication is adopted | `wait_for_presentation_adopted` |
| Wait for a publication burst to stop | `wait_for_presentation_settled` |
| Activate a control whose answer may be `stale` | `submit_until_admitted` |
| Wait for narrative text to finish appending | `wait_for_narrative_settled` |
| Put a synthetic panel in the client | `inject_snapshot`, `inject_update` with a `valid_*_panel()` builder |
| Count what the client sent | `install_outbound_recorder`, `sent_action_count` |

Rules that follow from how the client works:

- The server admits a `ui_action` only against its newest committed revision.
  An asynchronous publication (an art delivery, a worker settlement) can
  advance that revision between your read and your submit; the answer is then
  `stale` and nothing was applied. Use `submit_until_admitted` instead of
  retrying by hand or adding a delay.
- Read the revision and inject in **one** `page.evaluate` (the `inject_*`
  helpers do). A Python-side read followed by an injection races with a server
  snapshot.
- A puppet change starts a new presentation epoch and restarts the revision
  count. Do not compare revisions across it.
- Assert the committed result first, then its surface. "The panel shows X" is
  a weak assertion if the store never committed X.
- Every non-local request is aborted by `guard_local_only`. A test never
  depends on a CDN or any remote resource.

## Conventions

- Extend the shared base in `browser_base.py`. It boots the per-process
  server in `setUpClass`, opens Chromium and logs in.
- The reference viewport is 1451x790 (`DEFAULT_VIEWPORT`); the acceptance pair
  is 1451x790 and 2560x1440 (`ACCEPTANCE_VIEWPORTS`). Do not invent others.
- Game data comes from the synthetic kit or a file-local synthetic fixture.
  Only a tagged data-contract test names shipped content.
- No assertion on real elapsed time. Prove a performance property with a
  count (requests sent, repaints, publications), not a stopwatch.
- A panel fixture carries the panel's **current** schema version. When a panel
  version is bumped, update the `valid_*_panel()` builder, not each test.

## Mistakes that have happened here

- Asserted on a snapshot before the art scene had arrived: wait for the scene.
- Counted stage layers while the dream stage was still settling: settle first.
- Waited a fixed window for a move: wait for the move's recorded outcome.
- Measured the minimap before it had settled, or timed a repaint that still
  included one-off warm-up costs.
- Left the pointer over a rail, so a hover state changed the layout under
  test: park the pointer.
- Injected a panel before the store was ready: wait for the shell first.
- Added a test method and forgot the shard manifest: the contract test failed
  on every branch after it.
