# Design

## Context

Observed world/rules/unlock_notices.py stores party skill notices in session.ndb, with commander_sessions discovering owner connections including possession. Its ephemeral storage cannot distinguish first-ever topic opening across reconnect. Narrative reading Attribute supplies the durable topic identity and revision needed here.

## Goals / Non-Goals

**Goals:** Persistent unread markers and deferred deduplicated unlock batches. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Implement Shared contract v2 for static YAML/generated phases. Observe deterministically after successful open/committed refresh, never in presenters. Guarded owner UPDATE/raw Attribute merge persists host_key/topic history. First observation is per unseen topic ID, including newly permitted phase IDs: insert all declared IDs, initially open announced/unread without popup, locked/hidden ever_open=false. Host initialized alone cannot classify unseen phase IDs as later unlocks. Existing locked/hidden later opening announces once unless complete. Refusal changes no formal history. Phase return retains prior completion/ever_open/announced. No static registry gate.

Use one owner/host_key batch per committed refresh with <=16 ordered IDs, batch_id/created_revision, no persisted recipient context. Claim marks announced/clears pending under owner lock before at-most-once fan-out. Wrap separately with each current authenticated watcher's physical host_id/context_id and permitted phase; never ship foreign-phase IDs. Phase retirement suppresses obsolete pending announcements while retaining reading/history. No watcher/failure/disconnect consumes popup eligibility while preserving unread markers. Snapshots/reconnect never replay popup; each relevant connection may show one toast per live batch.

Client holds a Set of seen batch_ids per current character/control context and a bounded pending list. While typing/reading, defer all batches until explicit finish returns to choices; then show ONE non-focus-stealing toast summarizing all pending topic openings for that refresh, with persistent unread dots in the list. Keep lock marker over unread. Drop obsolete host/context batches, preserve focus, do not automatically open choices/topics, and discard on reload/character switch. Concurrent reading completion before display suppresses topics now saved/read; an empty batch produces no toast. Rapid separate refreshes retain one toast per server batch, not one per topic.

Own integration acceptance here for first-open versus first-unlock, refusal then unlock, read relock/reopen, unread relock/reopen, variant change, two clients and reconnect suppression, dedup and post-scene deferral. Do not repurpose party skill session flags as durable reading and do not expand a generic notification framework.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/narrative/dialogue_reading.py`
- `world/rules/dialogue_availability.py`
- `world/rules/dialogue.py (first-observation refresh on open/selection)`
- `web/webclient/presentation/dialogue_push.py`
- `web/webclient-app/stores/elosern/dialogue_reading.js`
- `web/webclient-app/stores/elosern/toasts.js`
- `web/webclient-app/components/DialogueChoices.vue`

## Risks / Trade-offs

Use the exact review-resolved narrative storage and unlock_batch schemas in the shared contract. Persist no originating recipient context. A stable owner/host batch is wrapped separately for each live watcher current context_id: contexts C1 and C2 at host 41 receive the same batch U wrapped as C1 and C2. Another account character receives nothing. Compare saved completed_topic_ids before displaying deferred topics. Snapshots/reconnect never contain U; recipient retirement drops only its ephemeral notice.

Sequentially extends narrative Attribute, availability writer, pusher and frontend completion module. The complete physical and lifecycle refresh source matrices are prerequisites; observation attaches to those canonical commit callbacks, not WebClient-only command observers. Existing party unlock_notices.py remains unchanged except reuse of commander_sessions discovery. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.narrative.tests.test_dialogue_unread
pnpm exec vitest run web/webclient-app/tests/stores/dialogue_reading.test.js web/webclient-app/tests/dialogue_choices.test.js
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
