# Design

## Context

Observed narrative owns deterministic persistent state and uses explicit service APIs; existing party unlock_notices live only in session.ndb and cannot store reading. Watchers are indexed by current puppet, not owning player. Existing npc_persona writer uses a first-statement guarded UPDATE to obtain a SQLite write lock, followed by raw Attribute reads to avoid stale idmapper state.

## Goals / Non-Goals

**Goals:** Narrative-owned formal reading, delivered receipts and pure-chain synchronization. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Implement Shared contract v2 reading on owner Attribute, keyed by stable host_key, never physical dbid. Static s:profile and generated g:package-role share the same lock/merge schema; accept complete source-aware IDs. First SQL inside atomic is guarded owner ObjectDB UPDATE, then raw Attribute read; select_for_update alone is insufficient on SQLite. Merge one host/topic, increment only on change, assign fresh containers and compensate caches on failure. reading_for never creates storage. Completion validates retained receipt/current package-role/phase context without static membership. Same-phase return/save/reload preserve reading; phase change retires receipts only. Log existing-facade identifiers without prose/private values.

A current context holds server delivery receipts independently from the latest scene snapshot. Store one receipt per topic for the most recently issued formal/pure-chain delivery; on repeated delivery of the same topic retain the prior receipt until its acknowledgement or context retirement (bounded 2 receipts per topic, at most 32 for <=16 topics). Older acknowledged completion may return already_saved only after validating it is in the current receipt set; foreign/undelivered claims never succeed. Re-selecting the same topic more than twice retires superseded unacknowledged receipts; client treats that receipt rejection as authoritative, while read completion is monotonic. Across different topics, delayed valid receipts survive later selections. A stale phase/context/control receipt cannot mark new content read. Reconnect republishes the latest stored scene unchanged, retains current valid receipt set and starts presentation at line one.

Expose explore.dialogue_complete with exact payload and authenticated actor. Formal acknowledgement must match delivered kind, host, owner, context, topic and exact scene revision. Refusal/opening/service ack never marks formal reading. Ack does not call eligibility/effect settlement anew; already-delivered qualification may now be false while its unchanged valid context still allows completion. Qualified descendant unlocks require server-saved predecessors and current requires. State fan-out uses commander_sessions only to discover current account connections, then filters by resolve_commander(current puppet)==owner and watcher epoch; never leak reading to another character of the same account. Render each connection's own host/context and preserve its local playback ID if unrelated. Failed fan-out logs and next sync recovers; no rollback of committed read.

Deliver a pure public chain as exact scene descriptors + server-issued receipts for eligible public nodes; exclude all qualified descendants from payload even when reachable in DAG. Local reveal follows predecessor formal completion. Out-of-order pure successor ack rejects `dialogue_predecessor_unread` until predecessor saved. Pure-chain replay/ack never grants talk affinity: select the public root once through normal selection, every pre-delivered successor is effect-free including affinity. Text emits the attributed chain in predecessor order, then completes each successfully emitted node via the same service; if emission fails/partially emits, do not mark that node and stop dependent chain output. Text explicit keyword selection of a pure successor requires saved predecessors and has no affinity, matching browser chain. Unknown/refusal/greeting never completes formal records.

Add synthetic same-owner/two-connection tests, an unrelated account character control, different hosts, possession sharing, write/cache fault, duplicate concurrent acks and delayed topic A completion after selecting B. First-show reading projection now exposes unread=true for uncompleted open formal topics, lock takes precedence. ever_open/announced fields remain false until notification slice adds observation writes. Scene/tone revision changes and relock do not clear completed.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/narrative/dialogue_reading.py (new)`
- `world/rules/dialogue.py`
- `world/rules/dialogue_availability.py`
- `commands/talk.py`
- `web/webclient/actions/exploration_actions.py`
- `web/webclient/presentation/dialogue.py`
- `web/webclient/presentation/dialogue_push.py`
- `web/webclient/presentation/watchers.py`
- `web/webclient/presentation/affordances.py (ACTION_CODE_ALLOWLIST entry)`
- `web/webclient/presentation/options.py (_ACTION_PAYLOAD_VALIDATORS lockstep entry)`
- `web/webclient/actions/registry.py (ActionSpec registration)`
- `web/static/webclient/js/elosern/protocol/constants.js (CONTEXT_ACTIONS_ACTION_CODES entry)`

## Risks / Trade-offs

The complete review-resolved session and wire schemas in the shared contract govern receipt storage, pure_chain entries and completed_topic_ids. Reading-server creates the entire narrative Attribute shape, including initialized false and pending_batch null; observation remains owned by unread-notices. Saved completed_topic_ids accompanies reading_revision so a second connection can suppress already-read notices without interpreting unread flags. Public successor delivery and retained receipts must pass the shared aggregate UTF-8 budget. Reconnect preserves opening line_delivery_id and context, and delayed topic A completion uses receipts independent of latest topic B playback.

Owns narrative Attribute and backend receipt/pusher changes. UI locked change is independent code-wise but reading-client depends on both. Notification slice extends same Attribute after this. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

The new action is exactly `explore.dialogue_complete` with exact composed payload `{npc_id,delivery_id,context_id,topic_id,scene_revision}`, validated by `web/webclient/actions/exploration_actions.py::validate_dialogue_complete_payload` and registered in the same five lockstep points every other exploration action uses. A successful completion commits reading and then queues `refresh_dialogue_availability(owner, cause="reading_completed")` on commit, so a qualified successor that just became eligible is projected without waiting for an unrelated state change; a rejected claim queues nothing.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.narrative.tests.test_dialogue_reading world.rules.tests.test_dialogue_availability
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
