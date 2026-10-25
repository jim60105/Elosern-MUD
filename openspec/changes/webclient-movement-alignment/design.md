# Movement event alignment and settlement ownership

## Context

B compares all candidate publications and D defines snapshots/deltas. Movement commits in `world/rules/movement_settlement.py::settle_movement/settle_relocation`; TerrainRoom objects are pooled across coordinates. `area_map.py` already identifies grid areas by z-map-key, wilderness by WILDERNESS_MAP_ID and coordinate-free areas by the minimum dbref of their connected same-family component. Instance spawn stores origin_room and scene_identity. These authoritative facts must be captured before traversal, never recovered from display labels afterward.

## Goals / Non-Goals

Deliver movement checkpoint classification using the completed P causal group implementation; S reuses the same fact API. Do not change movement cost, rollback, map knowledge, game-state schemas or command syntax. Never call area_map/world_map presenters to discover identity or force-load them during alignment.

## Decisions

### Authoritative identity

Add read-only `world/maps/area_identity.py::read_alignment_identity(actor) -> AlignmentIdentity|None`, a frozen value containing `(layer, area_key, instance_key)` copied at capture time. Grid/Anchor uses layer=grid, area_key=location.xyz[2], instance_key=None. Wilderness uses layer=wilderness and the registered wilderness map identity/name (the same WILDERNESS_MAP_ID coordinate frame used by area_map), instance_key=None. Coordinates and terrain/district/display labels are excluded. Moving within this continuous wilderness map stays incremental even if a terrain label changes. Grid-to-wilderness and grid map-key changes align.

For plain coordinate-free interiors, share the existing read-only `_room_component` traversal from area_map.py as `world/maps/area_identity.py::room_component` and use `room:<minimum component dbref>` as area_key. Preserve existing same-family filtering/edge semantics; reuse it in area_map rather than establishing two definitions. For InstanceRoom use `instance:<minimum instance component dbref>` as area_key and `(root dbref, root.scene_identity)` as instance_key, with the root's authoritative origin/scene identity captured as plain values. This distinguishes entry/exit/replacement even when labels are equal. Moving within one instance component is incremental. Unknown/unreadable identity returns None and a successful non-comparable transition aligns conservatively. Failure/rollback with no committed traversal emits no event. Test source identity capture before a pooled wilderness room is repurposed.

### Committed fact and grouping contract

The completed `../webclient-publication-settlements/design.md` (P) owns world/rules/presentation_events.py including AlignmentIdentity/PresentationAlignmentFact/emit_alignment_fact, causal group capture across exact on-commit registrations, multiwatcher grouping and independent overlapping command semantics. Reuse those exact frozen values/APIs. Do not add begin_settlement/finish_settlement session tokens or change B's always-Deferred API. P supplies group_id; the producer registers delivery with on_publication_commit inside its successful owning boundary. Observer exceptions isolate/log via world.observability.

Wrap settle_movement/settle_relocation in P publication_group before their transaction begins, so existing nested dialogue/party/lore/options callbacks inherit one causal ID. Successful committed boundary classification emits the fact to all lawful current watchers through ingress's registered observer; coordinator promotes that group entry to force_snapshot with a fresh canonical context at drain. Group callbacks may arrive in either order, including a watcher without any initiating request. No intermediate group delta is sent. Existing later async pushes use fresh groups.

Wrap graphical _move_adapter's synchronous core call/result normalization in the same group and return its internal publication_group_id for dispatcher completion attachment before reactor drain. Plain Exit return values do not need to change. Text commands need no pending session token; their original Deferred value/Failure and independent completion refresh are preserved by P. Explicit sync remains a separate queued forced snapshot while either kind of operation is pending. M's tests include reverse-completing text Deferreds and two watchers as regressions of P, without reimplementing its mechanism.

### Production hook inventory

Capture old/new immutable identities at settle_movement's successful compensated boundary and settle_relocation's successful commit. Wilderness/grid/plain/instance Exit traversals, NPC.move_to (including possessed NPCs) and graphical `_move_adapter` use those owners; do not classify requested explore.move as success. PlayerCharacter direct move_to can bypass settle_movement, so add capture in its existing at_pre_move after movement admission and compare in its at_post_move commit callback; use a per-invocation copied source identity, never retain the mutable source room. When settle_movement already owns the traversal, use that owner's capture and suppress the duplicate player hook fact. Failed hooks/rollback/compensation (move_hooks=False) publish none. `typeclasses/characters.py::_schedule_projection_refresh_after_activation` queues ordinary unknown eager candidates under the same causal group; adding occupants alone is not an area checkpoint. Actual room entry is classified by the movement owner, and login activation is already covered by full baseline establishment. Source and destination cannot be inferred merely from a final location poll. Explicit sync/login/reconnect/puppet/recovery already force snapshots in B and need no checkpoint fact.

Exact owned files are new world/maps/area_identity.py, movement_settlement.py grouped identity/fact hooks, area_map.py shared reader extraction, ingress.py alignment observer registration, exploration_actions.py::_move_adapter internal group capture, and typeclasses/characters.py direct-move identity capture. P owns the complete presentation_events.py value/observer API and shared queue/Deferred/push callback plumbing; S owns terminal/skip causes. Preserve active dialogue lifecycle refresh callbacks and their transaction semantics. Direct-player at_pre/at_post movement capture must bind its on_publication_commit to the same source group and avoid duplicate fact emission when the settlement owner is active.

## Verification and documentation

New `presentation/tests/test_movement_alignment.py` exercises real deterministic exit traversal through both UI dispatcher and WebClient text input, with synthetic grid keys, identical display names, pooled wilderness reuse, interior components, instance replacement and unreadable identity. Assert one freshly rendered complete eager publication instead of a delta; deliberately omit one panel candidate before checkpoint and prove checkpoint restores it from canonical state. Verify failed move/rollback sends no checkpoint, same-area move stays incremental, unopened map presenter call counts stay zero, and captured old-epoch group cannot publish into replacement. Document authoritative identity and finish ownership alongside the approved design implementation notes. Focused commands are in tasks.md.

## Risks / Trade-offs

Semantic facts cross deterministic/presentation layers only as read-only observer data; web code is never imported by a state writer. Observer registration is idempotent and tests restore registration. Shared room traversal extraction preserves current map behavior without building a map payload. P's captured causal callback groups avoid Deferred context leakage and duplicate refreshes.
