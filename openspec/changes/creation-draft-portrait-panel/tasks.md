# Tasks

## 1. Read-only portrait state

- [ ] 1.1 Add the immutable receipt/job/card/error reader to `world/rules/creation_portrait.py` and exact-card descriptor builder in `world/art/presenter.py`. Add synthetic `test_creation_panel/test_portrait.py` cases for each state, missing/corrupt receipt, foreign image control and reconnect/reload reconstruction; assert zero writes, no prompt exposure and unchanged ordinary-character eligibility rejection.
- [ ] 1.2 Extend presenter `_serialize`/`validate_creation`, immutable view plumbing and browser mirror with required portrait union; move 7 to 8 and reject all other versions. Add identical state/field/URL/reason rejection matrices in Python and `protocol_creation.test.js`; focused commands in design must pass without increasing byte caps.
- [ ] 1.3 Update every affected synthetic panel builder/story fixture and `docs/development/webclient-synchronization.md` to schema 8 and the closed union. Expected state is valid fixtures, unchanged optional proposal semantics and no duplicate panel-version requirement.

## 2. Completion publication

- [ ] 2.1 Extend `art_push.py` matching to the actor-owned receipt, including pending/failed states without artwork. Extend `test_art_push.py` for success, failure, canceled/foreign job, retired epoch and no duplicate candidate publication; the focused art-push command in design must pass.
- [ ] 2.2 Keep `stores/elosern/creation.js` navigation signature independent of portrait state. Add `tests/store/creation_portrait.test.js` proving art-only replacement leaves mode, unsent values, local step and concept revision unchanged; the focused Vitest command in design must pass.

## 3. Delivery acceptance

- [ ] 3.1 Run the focused commands in design independently, register new modules via `uv run --locked python -m tools.shard_register fix`, then run `uv run --locked python -m tools.contract_gate` and `openspec validate creation-draft-portrait-panel --strict`; expect no warning/failure and no unrelated manifest loss.
