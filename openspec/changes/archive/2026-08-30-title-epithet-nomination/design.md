# Design: title-epithet-nomination

Implements D4 (§7) of
`docs/superpowers/specs/2026-08-30-title-system-design.md`.

## Context

F landed `title_collection` / `title_equipped`, `compose_title`, bank+auto-equip
discipline, and the `title` command surface (list/equip). The options-service
"synchronous-inside-settlement with a bounded timeout" LLM call pattern already
exists; `world/ai/schemas` owns closed output schemas; the EventLog summary feed
for the Director exists. The single-writer boundary admits `world/ai/` writes for
nothing except the pending-ballot attribute, and F's snapshot registration makes
`title_collection` writes atomic-safe.

## Goals / Non-Goals

- Goals: rest-point-only triggers with single-ballot + cooldown throttle;
  5→schema→collision→top-3 pipeline; persisted never-expiring ballot; consent
  writes (`accept_epithet`) and EventLog soft-learning on decline.
- Non-Goals: any programmatic blacklist (deleted names are renominable — that is
  H's collision semantics), free-text ballot answers, LLM-side filtering (the
  collision rule is deliberately NOT in the prompt: fixed token cost, flat
  prompt text), mid-combat triggers.

## Decisions

### DG1: triggers are the four rest points; throttle is ballot + cooldown

`schedule_epithet_nomination(entity)` — the composition-root service
`server/title_nomination_service.py`, because the repo transport contract
(`tests/test_ai_transport_contract.py`) forbids `world/rules` and `commands`
from importing `world/ai` — is fired from logout (`PlayerCharacter.at_post_unpuppet`),
the resting day boundary (typed `rest`/`sleep`/`wait` routes and the WebClient
`explore.wait` adapter, gated on the `daily_reset` advance event), exam pass (an
observer registered inside `settle_exam_outcome`), and quest-arc completion (an
observer fired when any quest-log writer's `fulfill_record` transition lands on
COMPLETED); the two settlement observers defer through
`transaction.on_commit`, so a rolled-back settlement nominates nothing.
Suppression: a pending ballot (silent return — replacement paths deliberately
do not exist) or an active cooldown of `NOMINATION_COOLDOWN_DAYS` (registry
constant 2) day boundaries started by a decline. Decline is the only cooldown
source: ballots never expire, so no expiry transition exists anywhere. An
accepted ballot never starts a cooldown (the next trigger point is the next
gate anyway). Cooldown state is derived from the stored decline log records —
no new subsystem.

### DG2: pipeline stages are pure proposal work; the rules layer persists

Prompt (Director, recent EventLog summary, exactly 5 `{display, basis}`, basis
≤ 80 chars, zh-tw, 2–8 chars, noun phrase, never the player name — form
requirements only). Schema: closed `{candidates: [{display, basis}] × 5}`;
malformed JSON / wrong count / overlong fields void the round whole. Collision
filters run in code, in fixed order, per candidate: form; fixed-registry display
hit; own-collection hit; in-batch duplicate (keep first). First three survivors
form the ballot; 1–3 survivors ballot as-is; 0 voids silently. LLM offline /
timeout / degraded ⇒ the stage does not fire at all. The `world/ai/` module is
pure proposal: it returns the filtered candidates (or nothing) and writes no
attribute. The rules-layer writer
`persist_nomination_ballot` re-checks suppression after the call returns and
persists the ballot itself in one all-or-nothing step (a failed persist voids
the round) — the single-writer boundary is untouched, matching design §14,
and the service schedules the call through the existing fire-and-forget
`option_proposal_service` pattern (offline profile ⇒ no call at all).

### DG3: ballot is persistent; persistence, acceptance, and decline share the rules layer

`db.pending_title_ballot` (`[{display, basis}]`) survives logout; the WebClient
re-renders the OOB menu on sync; Telnet gets `title accept <1|2|3>` /
`title decline`. `accept_epithet(entity, index)` validates the index against the
pending ballot, then banks (display, origin_quote = basis, granted_tick) +
auto-equip-when-empty in one atomic transaction and clears the ballot. Decline
discards the batch and records the rejected displays into a bounded per-entity
decline log (which also starts the cooldown) and emits a
`title_epithet_declined` EventLog entry through the answering surface — the
nomination prompt digests the decline log for Director-facing soft learning;
no blacklist exists. Out-of-range index ⇒ stable reason, no state change.
Repo note: the EventLog is per-action in this codebase and no rolling event
store exists (verified in F/G research); the decline log attribute is the
durable feed, and the spec requirement wording was amended to match.

### DG4: tests mock the client, never a live call

Every nomination test injects the client (same seam as other `world/ai/`
layers): happy path, each rejection stage, offline degradation, cross-session
ballot survival.

## Risks

- Prompt cost per rest point: bounded (5 candidates, fixed prompt, no collision
  text); suppressed by single-ballot + cooldown.
- Stale basis content: basis quotes are read from the EventLog summary the
  Director already consumes.

## Migration Plan

One-shot (unreleased).

## Open Questions

None.
