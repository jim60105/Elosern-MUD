# Design: Party unlock notifications and session unread state

## Context

See proposal.md. `grant_skill_practice_xp(..., unlocks_out)` appends `unlock_line(candidate)` strings and cross-lineage grant lines; `ActionResolver` appends them to `ActionResult.notifications` only after `_commit` succeeds; combat delivers via `_deliver_after_commit(commander, notifications)`; `grant_study_practice_xp` passes no sink; `ScheduledEvent` is a plain JSON-compatible record with no live entity references.

## Goals / Non-Goals

**Goals:** one structured notice type on both entry points; commander delivery naming the learner; session-only unread state written by a rules module; nothing persisted.

**Non-Goals:** rendering the dot or the 新 tag (client changes), any persistent unread record (design §13).

## Decisions

- **`UnlockNotice(learner_id, learner_name, skill_key, line)`** frozen dataclass. `grant_skill_practice_xp` and `grant_study_practice_xp` append notices to an optional sink; existing callers that only need lines render `notice.line`. Alternative: parse learner from strings; rejected as fragile.
- **Study path** gets a sink inside `_practice_settlement`; each notice becomes a `ScheduledEvent(kind="practice_unlock", payload={"learner_id", "skill_key", "line"})` in the advance's returned events, so delivery happens only after the advance commits and rollback discards them with the event list.
- **Delivery helper** `deliver_unlocks(acting, notices)` in `world/rules/unlock_notices.py`: messages each line to the commander (`resolve_commander(acting).msg`, which reaches the puppeted session even during possession through the owner's account) — and records unread marks on every session of the commander's account (`account.sessions.all()`), writing `session.ndb.party_unlocks = {learner_id: {"unread": True, "recent": frozenset}}`. Called by every post-commit owner listed in the proposal.
- **Clear** `mark_unlocks_seen(session, learner_id)` flips `unread` only. It is called by the `party.view_member` adapter (next change) when the skills tab is opened.
- **Context snapshot**: `PresentationContext.unlocks` is a copied immutable mapping built by the coordinator from `session.ndb.party_unlocks`, so presenters never read `ndb` directly.
- **Possession**: state is keyed by account sessions, not puppets, so possession neither clears nor duplicates it; disconnect drops `ndb`.

## Risks / Trade-offs

- [Message reaching the commander while possessing] → `msg` to the commander object delivers to the account's puppet session only if Evennia routes it; the helper instead messages the sessions directly (`session.msg`) to be deterministic. Tests cover possession.

## Migration Plan

Pre-release; revert the implementation commit.

## Verification and documentation ownership

EvenniaTest: companion field-cast unlock line and marks, booked-study unlock event rendered after commit, combat-round companion unlock delivered to the commander, rollback marks nothing, clear keeps the recent set, reconnect (new session) has no marks, possession keeps marks, no persistent attribute written (attribute snapshot). No command syntax change. Observability lint if any logging is added; shard contract; `tools.contract_gate`.
