# Design

## Context

Observed world/rules/unlock_notices.py stores party skill notices in session.ndb, with commander_sessions discovering owner connections including possession. Its ephemeral storage cannot distinguish first-ever topic opening across reconnect. Narrative reading Attribute supplies the durable topic identity and revision needed here.

## Goals / Non-Goals

**Goals:** Persistent unread markers and deferred deduplicated unlock batches. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Implement the exact first-observation, first-unlock, relock and notification semantics from Shared contract v1. Observation is a deterministic writer called from successful talk-open and refresh_dialogue_availability after originating changes commit, never from project_topics/presenter. Before writing, obtain owner SQLite guarded UPDATE lock and raw Attribute state as in reading-server. Persist per-host initialized flag plus topic ever_open/announced, completed and owner revision. Every known topic's first snapshot records open versus locked/hidden, so a later locked-to-open transition is distinguishable from first opening this host. Initially open topics become unread but announced=true without popup; hidden/locked initial topics stay ever_open=false/announced=false. Reading a refusal does not change these fields. A never-open topic becoming open becomes unread and announcement-eligible, unless already complete through another valid session; mark announced once. Relock/reopen of read or unread ever-open content sends no repeated notice; tone/revision change sends none.

Use a single owner/host batch per committed refresh with ordered unique newly-ever-open unread IDs (<=16), batch_id and originating context_id, persisted only until claim. Collapse changes inside one action settlement through availability refresh's batch cause. claim_unlock_batch marks announcement delivered and removes pending batch atomically before live fan-out; fan-out is at-most-once. Only currently connected authenticated owner contexts receive the live ephemeral payload; no reconnect snapshot contains it. If no watcher, failure or disconnect occurs, consume/suppress the popup and keep unread markers; no durable retry announcement on reconnect. This deliberate loss tolerance prevents repeated notifications and does not lose reading status. Cross-session fan-out may show one notice on each currently open relevant connection, with one per batch per connection; do not interpret owner claim as single browser election.

Client holds a Set of seen batch_ids per current character/control context and a bounded pending list. While typing/reading, defer all batches until explicit finish returns to choices; then show ONE non-focus-stealing toast summarizing all pending topic openings for that refresh, with persistent unread dots in the list. Keep lock marker over unread. Drop obsolete host/context batches, preserve focus, do not automatically open choices/topics, and discard on reload/character switch. Concurrent reading completion before display suppresses topics now saved/read; an empty batch produces no toast. Rapid separate refreshes retain one toast per server batch, not one per topic.

Own integration acceptance here for first-open versus first-unlock, refusal then unlock, read relock/reopen, unread relock/reopen, variant change, two clients and reconnect suppression, dedup and post-scene deferral. Do not repurpose party skill session flags as durable reading and do not expand a generic notification framework.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/narrative/dialogue_reading.py`
- `world/rules/dialogue_availability.py`
- `web/webclient/presentation/dialogue_push.py`
- `web/webclient-app/stores/elosern/dialogue_reading.js`
- `web/webclient-app/stores/elosern/toasts.js`
- `web/webclient-app/components/DialogueChoices.vue`

## Risks / Trade-offs

Sequentially extends narrative Attribute, availability writer, pusher and frontend completion module. Existing party unlock_notices.py remains unchanged except reuse of commander_sessions discovery. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.narrative.tests.test_dialogue_unread
pnpm exec vitest run web/webclient-app/tests/stores/dialogue_reading.test.js web/webclient-app/tests/dialogue_choices.test.js
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
