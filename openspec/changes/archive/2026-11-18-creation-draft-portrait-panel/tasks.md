# Tasks

## 1. Read-only portrait state

- [x] 1.1 Add the immutable receipt/job/card/error reader to `world/rules/creation_portrait.py`, consuming the request slice's pure cached-availability reader, and exact-card descriptor builder in `world/art/presenter.py`. Implement the design's explicit precedence including transient service-unavailable reason without a presenter probe/state write. Test every state, cache expiry/config change on explicit refresh, ready-card preservation, admitted pending work, foreign image and reconnect; ordinary eligibility stays unchanged.
- [x] 1.2 Extend presenter `_serialize`/`validate_creation`, immutable view plumbing and browser mirror with required portrait union; move 7 to 8 and reject all other versions. Add identical state/field/URL/reason rejection matrices in Python and `protocol_creation.test.js`; focused commands in design must pass without increasing byte caps.
- [x] 1.3 Update every affected synthetic panel builder/story fixture and `docs/development/webclient-synchronization.md` to schema 8 and the closed union. Expected state is valid fixtures, unchanged optional proposal semantics and no duplicate panel-version requirement.

## 2. Completion publication

- [x] 2.1 Change worker batch results/signal contract to bounded `(subject_key, image_id)` completions for each actually applied success/failure. Return `_fail_batch`'s applied failures on client-construction failure; omit stale no-ops and never merge distinct images by subject. Migrate all producers/receivers/signal-shape fixtures without an alias or old-payload fallback. Extend real worker tests for normal success/failure, client-constructor failure and stale token outcomes.
- [x] 2.2 Extend `web/webclient/presentation/art_push.py` matching to actor-owned current receipt/image, including pending/failed states without artwork; recheck inside the coordinator's current-context factory. Extend `test_art_push.py` with worker-to-coordinator success/failure, canceled/foreign job, older completion after newer admission, retired epoch and no duplicate publication. Focused worker/art-push commands in design must pass.
- [x] 2.3 Keep store navigation signature independent of portrait. Guard `use-creation-form.js::syncFromDraft` with existing `stable_stringify.js` content comparison; wire `{generation, epoch}` context through `AppClient`/overlay, preserving genuine save/reset/new-context synchronization. Add store and mounted-real-overlay regressions starting from a saved custom draft with unsent edits, then fresh equal-draft pending/ready/failed panels. Assert every field/step/concept survives; test changed draft/reset/save/context controls. The focused Vitest command in design must pass.

## 3. Delivery acceptance

- [x] 3.1 Run the focused commands in design independently, register new modules via `uv run --locked python -m tools.shard_register fix`, then run `uv run --locked python -m tools.contract_gate` and `openspec validate creation-draft-portrait-panel --strict`; expect no warning/failure and no unrelated manifest loss.
