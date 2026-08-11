## Why

Two art-pipeline contract defects from audit run-1: (F16) portrait stable keys containing `/` or exceeding length limits pass producer validation, generate `done` assets, and then fail the media route (404) or the OOB panel bounds (whole panel degrades) — permanent unviewable art; (F17) the worker persists `in_progress`, the presenter emits it verbatim, and both wire allowlists reject it, degrading the entire art panel while a generation runs.

## What Changes

- One shared stable-key contract across producers, queue, media route, and wire: reject `/`, `:`, control characters, and over-length keys at every producer boundary, and align length limits with the wire.
- The presenter normalizes internal `in_progress` to the wire-stable `pending` (or the wire schema gains an explicit generating status) so a claim-to-settle window never degrades the panel.
- Regression coverage for slash/long keys and in-flight panel snapshots.

## Capabilities

### New Capabilities

- `art-stable-key-contract`: uniform stable-key validation shared by all producers and consumers.

### Modified Capabilities

- `art-subject-model`: producer validation rejects `/` and over-length keys.
- `webclient-art-panel`: wire accepts a stable generating state (normalized from `in_progress`).
- `art-queue-worker`: claimed records expose a wire-normalized status.

## Impact

- `world/art/subjects.py::_validate_subject_key`, `world/art/presenter.py`, `world/imports/loader.py` + `world/imports/schema.py` (key pattern/length), `world/quests/characterization.py`, `web/webclient/presentation/art.py` (length constants), `web/static/webclient/js/elosern/protocol.js`, tests.
