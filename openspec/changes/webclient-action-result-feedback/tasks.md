# Tasks — webclient-action-result-feedback

## 1. Store append rule

- [ ] 1.1 In `web/webclient-app/stores/elosern.js` `handleActionResult`: on a recognized non-success match (outcome `rejected`, `stale`, or `error`) outside creation-overlay presentation, `appendText("err", message)` once (verbatim message; stable fallback 「動作未生效，請重試或返回上層。」 only when the message is unusable); creation-overlay condition reuses the existing `panelAvailable('creation')` + mode gate; lock/uncertain/revision code paths byte-identical otherwise

## 2. Vitest

- [ ] 2.1 Store tests: a rejected result appends one `err` line verbatim; a `stale` result appends one `err` line while the lock still holds until the recovery revision commits; re-delivery of the same result appends nothing; success appends nothing; creation-overlay-present suppresses the line; message-less non-success falls back; narrative bound respected under repeated distinct failures

## 3. Browser evidence

- [ ] 3.1 Browser methods (existing exploration browser class): one drives a real `stale` admission via a tampered `base_revision` over the test transport and asserts the stale message renders as a visible narrative error line with no modal, no resubmission, and the recovery snapshot landing after it; one drives a real domain `rejected` result (a stale `explore.move` after a committed move) and asserts its message renders. Annotate each with `covers_requirement` (IDs from `uv run --locked python -m tools.spec_traceability list` after the delta syncs at archive time)

## 4. Gates

- [ ] 4.1 `npm test` green; `tools.spec_traceability check` green; `git diff --check` clean
