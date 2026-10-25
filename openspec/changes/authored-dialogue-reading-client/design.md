# Design

## Context

The manual player emits one scene-finished event after an explicit final activation. The reading server now validates delivered context receipts and publishes persistent reading_revision; frontend must not turn an optimistic return to choices into proof of saved qualified eligibility.

## Goals / Non-Goals

**Goals:** Memory-only completion retry and pure-chain progression. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Implement applyDialogueReading(ctx) in a new store module, wired through existing store composition and transport. `finishDialogueDelivery(delivery)` queues exact complete payload and returns to choices; only formal and pure-chain deliveries queue, refusal/opening/service do not. Key pending by context_id + delivery_id and hold bounded <=32 entries matching server receipts. Deduplicate repeated finish events, retry transport failure on same-context restoration or explicit retry, and serialize predecessor-first pure-chain acknowledgements. A response of saved/already_saved removes pending only when response identity/context match. Logical stale/retired/undelivered rejection discards that entry and refreshes canonical state; predecessor_unread keeps it queued behind predecessor. Transport error leaves it pending and displays an unsaved/retry status with no claim of durable progress.

Local completion may reveal pre-delivered pure_chain successors in memory while previous ack is pending. Server-qualified topics remain solely the latest server choices; never unhide one based on optimistic local completion or public-chain cache. A queued successor retry waits for saved predecessor. Completion refresh must not overwrite the currently playing delivery or restart same delivery on reading_revision-only updates. If another connection completes a predecessor, update saved state without auto-advancing current line or stealing focus.

Generation/character exit, leaving dialogue, changed context/control/phase, refresh and tab closure discard pending memory and transient reveal. Do not install beforeunload persistence, localStorage, IndexedDB, service-worker retries or a durable queue. Disconnect alone may retain in-memory pending for same-context retry, but a fresh app mount has no pending and replays latest delivered scene at line one. Pending entries for retired receipts are discarded on explicit server rejection; no immediate compulsory reread while a valid retry can save. The server wins after discarded pending state, so a topic/chain may require rereading and markers reflect saved state.

Tests cover failed ack then successful retry without rereading/effects, duplicate final activation, predecessor-first order, cross-session saved update while B plays, stale response from prior character, refresh discards and same-context reconnect replay. Add one focused browser failure/retry method plus one fresh reload scenario using deterministic transport interception; no real network outage dependencies.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `web/webclient-app/composables/use-authored-scene.js`
- `web/webclient-app/composables/use-dialogue-choices.js`
- `web/webclient-app/stores/elosern/dialogue_reading.js (new)`
- `web/webclient-app/stores/elosern/transport.js`
- `web/webclient-app/stores/dialogue-view.js`
- `web/webclient-app/AppClient.vue`

## Risks / Trade-offs

Touches player composable, choices, transport and AppClient after locked UI. Notifications depend on this return-to-choices boundary; no separate durable client storage. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
pnpm exec vitest run web/webclient-app/tests/stores/dialogue_reading.test.js web/webclient-app/tests/app_client_dialogue_choices.test.js
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
