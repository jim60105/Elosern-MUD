# Content-aware publication baseline

## Context

The shared wire and batch ownership contract is `../webclient-delta-contract/design.md`. Current coordinator full_snapshot/panel_update allocate revisions and send directly; dispatcher duplicates rendering in `_publish_presentation`; ingress refreshes all text settlements through synchronize_session. Push services pass already rendered candidate objects. There is no isolated published baseline. `art_push.py` consumes the returned envelope's revision, so suppression requires an explicit result type rather than a None/dict ambiguity.

## Goals / Non-Goals

Deliver complete content comparison and one publication owner within one engineer-day. Never persist synchronization state or compute world mutation counters. Baseline is eager-only, bounded by registered panel schemas and the 16MiB general logical ceiling introduced by C; on-demand map cache stays separate.

## Decisions

### Exact planning and public API

Add `web/webclient/presentation/publication.py` with `json_value_equal(old,new)`, `copy_json_value(value)` and frozen `PublicationReceipt(epoch:str, revision:int, kind:Literal["snapshot","delta","unchanged"], published:bool)`. Compare JSON type categories (null, bool, number, string, list, object); bool never equals a number, dict key sets/content ignore order, lists compare length/ordered elements, finite int/float share number semantics. Validate before comparison. Copy only newly adopted candidate values into owned plain JSON containers; do not use serialize/parse, sort, hashes, deepcopy of the whole baseline or aliases to mutable presenter results. Retain unchanged owned values.

Coordinator public entry is `publish(context, *, affected_panels=None, candidate_panels=None, removed_panels=(), force_snapshot=False, expected_epoch=None) -> PublicationReceipt`. affected_panels and candidate_panels are mutually exclusive. `None`/empty/invalid affected declaration means unknown scope: recompute every eager panel, transmit only differences. candidate_panels means already-rendered validated candidates from a push, with the same dependency expansion. Unknown candidate names fail preflight, never silently omit a panel. `removed_panels` is an explicit registered eager set, separate from candidates. Additions absent from baseline are replacements. A registered presenter returning unavailable is always a replacement candidate.

Keep full_snapshot, panel_update and synchronize as semantic entry points on the SAME coordinator if their callers still use them: full_snapshot/synchronize delegate force_snapshot=True; panel_update delegates candidate_panels and returns PublicationReceipt. Remove duplicate `_publish_presentation` implementations in dispatcher/coordinator in favor of publish. These are live APIs with a single implementation, no legacy-return shims. Migrate every return-value consumer from envelope indexing to receipt fields; frame assertions inspect sent frames instead.

Baseline fields are `{epoch, revision, panels, mode, layout_version, server_time, valid}` on the attached per-session coordinator. An absent/invalid baseline always selects a freshly rendered full eager snapshot, even for a candidate-only push. Each session's baseline is separate even when sessions share a puppet; expected_epoch checks remain. reset/detach/unpuppet discard baseline and pending sequence work. Baseline metadata owns copies too.

### Publication boundary

At the existing serialized reactor boundary, recompute current mode/time and candidate companions before comparison. Dialogue is a candidate in dialogue mode, and transition-dependent payloads stay coupled. `combat_round` remains solely completing-context data; a no-round later push may replace combat_beats with its current unavailable form according to existing semantics. No presenter gains write authority.

Plan logical document and validate logical content plus every frame and associated action-result envelope before first send. No-op has receipt published=False, kind=unchanged and current revision; its result is still prevalidated and sent. Any metadata change alone creates a delta. Snapshot checkpoints bypass comparison and freshly render all eager panels, then use one new revision even when equal. Pre-admission stale recovery also sends its complete snapshot before the matching stale result; amend the full existing non-success-result requirement's stale scenario without changing its one-message/creation/fallback behavior.

Reserve next target R without publishing it during preflight. On first attempted presentation send, advance the sequence's issued revision to R so any later frame never reuses an escaped revision. Only after all presentation frames return successfully install the isolated new baseline at R. If any send raises, retain the last complete baseline values for diagnostics but set valid=False. Never create a delta from it; next publication freshly snapshots at a later revision. If result send alone fails after full publication, baseline remains published/valid; normal disconnect uncertainty rules still apply. Preflight failure before first send consumes no revision and emits no presentation bytes. No client acknowledgement is added.

A single synchronous coordinator publication critical section sends a prepared presentation batch and, when present, matching action result, with no await/Deferred between frames. Reentrant sync/push attempts queue immutable publication INTENT (context rebuilt at execution, expected epoch rechecked), rather than pre-rendered stale snapshots. This is one serialized coordinator, not a second queue-owned baseline. Drain in order after result, discard retired-epoch intents, and bound pending intents to 64; overflow invalidates baseline and reports presentation failure, never silently drops a requested completion. Domain action in-flight and dedup cache remain dispatcher-owned. `ui_sync` still works while an adapter Deferred is pending, but cannot interleave its presentation/result send batch.

### Complete production caller inventory and ownership

Migrate these direct callers and their tests in this slice. No caller owns a second baseline or bypasses the preflight/send owner.

| Caller | Current symbol/path | Required behavior |
|---|---|---|
| Graphical completion, rejection, stale/internal recovery | actions/dispatcher.py::_publish_completion, _publish_presentation, _send_stale | success/domain rejection compare known/unknown scope; stale/internal recovery force fresh snapshot; preserve no_presentation result-only and scheduled sequence-retiring action exceptions |
| Explicit sync/login/reconnect/puppet | presentation/ingress.py::synchronize_session, _coordinator_for; coordinator.synchronize/reset/detach | force complete baseline; retain session-derived puppet authentication |
| Text completion success/errback | ingress.py::observe_command_settlement/refresh_after_command; server/conf/inputfuncs.py::text | unknown eager candidate scope unless committed checkpoint; preserve original Deferred value/Failure and Telnet exclusion |
| Art completion | presentation/art_push.py (direct panel_update) | compare matching rendered candidates; consume receipt.revision/published for existing logs, no duplicate snapshots |
| Current-state panel fan-out | presentation/push.py::make_panel_pusher plus dialogue_push.py, party_push.py, lore_codex_push.py | same epoch guard, per-session comparison, fresh canonical state |
| Options async generation | server/option_proposal_service/state.py push at lines 141-148 | route pre-rendered context_actions through publish_panel_update |
| Title ballot async generation | server/title_nomination_service.py::_push_ballot | route current title_ballot candidates through same helper |
| Dream refresh | server/dream_service.py::_refresh | ordinary unknown candidate recomputation; later completed-sleep hook owned by S |
| Scene activation refresh | typeclasses/characters.py::_schedule_projection_refresh_after_activation | unknown eager scope; instance transition fact owned by M |
| Map request | coordinator.py::_publish_with_maps; actions/map_actions.py | keep specialized map preflight/order; map revision synchronizes eager baseline revision without retaining map payload in eager baseline |
| Guarded shared helper | coordinator.py::publish_panel_update | return receipt for unchanged or published; None only for retired/absent sequence or reported failure, preserve isolation/logging |

Map plans may contain eager companion publication and one or two distinct on-demand map publications. Prevalidate ALL their frames before ANY send, assign ordered R/B per logical map, and advance baseline's revision after each successful logical publication without changing eager values except its explicit eager companion delta. Partial map send invalidates baseline. On-demand values are not compared/stored as eager candidates. Preserve specialized world-map allowance and area-map part schema; unopened maps are never rendered.

### Verification and documentation

Add new focused `presentation/tests/test_incremental_publication.py`, plus existing coordinator, coordinator_push, art_push, dialogue_panel, map_panel_protocol and actions/tests/test_dispatcher coverage. Assertions independently count renders and frames, mutate source objects after publication, compare two sessions and inject failure on first/middle/final send and reentrant sync. Unchanged completion, metadata-only delta and unavailable/removal must be separate cases. Update existing foundation design's superseded publication/revision wording and traceability with implementation; do not claim measured work reduction.

## Risks / Trade-offs

The issued revision and last successful baseline revision differ after partial send. Invalid baseline forbids deltas until snapshot repair. Async callback fan-out remains a separate ordered publication after a settlement unless an active settlement scope defers it under M. Domain refresh callbacks remain intact. No fake publisher or optional integration path is authorized.
