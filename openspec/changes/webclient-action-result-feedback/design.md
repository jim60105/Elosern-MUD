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

**D-C: Creation-overlay exclusion via the existing panel gate.** When `panelAvailable('creation')` and the mode is creation, the overlay is the presenting surface and the store skips the narrative append; this is a one-condition guard on the same append rule, not a new mode system. If the overlay is somehow not mounted while creation mode is committed, the narrative line still appears — degradation favors visibility.

**D-D: Empty/absent message falls back to a stable local line.** The envelope shape guarantees a message (1..512 code points), so the fallback 「動作未生效，請重試或返回上層。」 exists only for malformed-edge safety and never paraphrases server text.

## Risks / Trade-offs

- [Double statement when the overlay and narrative both show it] → excluded by D-C; a Vitest pins creation-mode suppression.
- [Err-line spam under a hostile/failing server] → narrative is already bounded (`MAX_NARRATIVE_LINES`); each failed request produces at most one line.
- [`stale` lines feel noisy during rapid recovery] → one line per failed request is the point (the alternative is silence); the recovery snapshot already lands after it, so the feed reads failure → fresh state.
- [Race with the frame-refresh changes' store surgery] → this change lands first and the others start after it (design doc §9); the append is additive inside one function.

## Migration Plan

One commit in `stores/elosern.js` plus tests; revert is trivial.

## Open Questions

None.
