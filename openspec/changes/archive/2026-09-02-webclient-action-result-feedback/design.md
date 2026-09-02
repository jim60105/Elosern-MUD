## Context

The reducer stores `lastActionResult` (validated by request id and epoch in the store's `handleActionResult`, which today only releases the dispatch lock). Narrative lines (`appendText(kind, text)`, kinds `in|out|sys|err`) are the client's established visible-feedback channel with bounded retention, full-log reachability, and existing `err` styling. The creation overlay already renders the result itself; the exploration/combat docks render nothing.

## Goals / Non-Goals

**Goals:**

- Every recognized non-success result (`rejected`, `stale`, `error`) makes its server-authored message visible exactly once, without inventing client copy.
- Zero churn on the lock/uncertain/revision machinery; zero server change.

**Non-Goals:**

- Styling projects, toasts, overlay hosts, per-code tone mapping; success-path echoes; changing `uncertain` semantics; retry UX.

## Decisions

**D-A: Narrative `err` line, not a new surface.** The narrative feed already satisfies visibility (permanently-present caption surface + full log), focus/keyboard neutrality, and screen-reader flow. A toast/overlay would be a second transient state store for one sentence. Alternative considered and rejected: reusing the dock's disabled-reason row — wrong place (the action may come from a card, chip, or drawer) and conflicts with the declarative-frame rules.

**D-B: Append at the `handleActionResult` match point, keyed once.** The match there already enforces result identity (request id + epoch + changed-from-previous), which is exactly the dedup unit, and it already treats every non-success outcome uniformly (only `rejected`+`no_puppet` releases early). The append rule fires for all three non-success outcomes; the `stale` path is the common recovery case and must speak like any rejection. No separate seen-set is introduced: reducer semantics already guarantee `lastActionResult` transitions once per result.

**D-C: Creation-overlay exclusion via the mount predicate, with the overlay upgraded to present every non-success outcome.** The suppression gate is exactly AppClient's `CreationOverlay` mount predicate (`panelAvailable('creation')`). Suppression is only honest if the mounted overlay actually presents the result, so `CreationOverlay` gains one always-reachable result region (inside the `available` branch, above the stage branch) that renders the message verbatim for every recognized non-success outcome (`rejected`/`stale`/`error`) across all wizard stages including confirm, with the same stable fallback; `formMessage` keeps its local-validation-only role (the old `rejected -> code || message` branch paraphrased the server message and only rendered on two stages). The gate is one condition on the store append rule, not a new mode system. If the overlay is somehow not mounted while creation mode is committed, the narrative line still appears — degradation favors visibility.

**D-E: Per-in-flight-result dedup.** The dedup unit is the recognized result recorded on the in-flight record (`inFlight.handledResult`, a stable-stringify fingerprint), not a global "changed from previous" equality: a foreign request's result delivered in between cannot erase the record (no double append on re-delivery), and a result that already sat in the reducer before dispatch started is still recognized once when its request goes in flight (semantically correct — a replayed completed request answers the fresh dispatch, matching the store's intended code-replay behavior). The record is created per dispatch; lock/uncertain/revision semantics are byte-identical.

**D-D: Empty/absent message falls back to a stable local line.** The envelope shape guarantees a message (1..512 code points), so the fallback 「動作未生效，請重試或返回上層。」 exists only for malformed-edge safety and never paraphrases server text.

## Risks / Trade-offs

- [Double statement when the overlay and narrative both show it] → excluded by D-C; a Vitest pins creation-mode suppression and the overlay's verbatim result region.
- [Err-line spam under a hostile/failing server] → narrative is already bounded (`MAX_NARRATIVE_LINES`); each failed request produces at most one line.
- [`stale` lines feel noisy during rapid recovery] → one line per failed request is the point (the alternative is silence); the recovery snapshot already lands after it, so the feed reads failure → fresh state.
- [Race with the frame-refresh changes' store surgery] → this change lands first and the others start after it (design doc §9); the append is additive inside one function.

## Migration Plan

One commit in `stores/elosern.js` and `components/CreationOverlay.vue` plus tests; revert is trivial.

## Open Questions

None.
