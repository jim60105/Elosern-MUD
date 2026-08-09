# scene-flavor-apply — Design

## Context

`scene-flavor-layer` will land a pure, guardrail-registered generative layer
(`world/ai/scene_flavor.py::generate_scene_flavor(context, client)`) with a degrade-to-`None`
outcome. Nothing consumes it yet. Quest scenes are materialized by `world/quests/
scene_builder.py::materialize_stage(actor, quest_id, *, origin_room=None)` inside one outer
`transaction.atomic()`: a freshly spawned `InstanceRoom` gets `room.db.desc` from the requirement's
`scene_sentence` (or the archetype's), occupants spawn, the stage binds, and the caller then walks
through the created exit (`commands/scene.py::CmdEnterScene`).

The repository contract `tests/test_ai_transport_contract.py` bans the string fragments
`"ollama"`, `"llm_client"`, and `"world.ai"` from the production source of `world/rules`,
`world/maps`, `world/quests`, `world/art`, and `commands`. `server/` is scanned by neither the
transport-boundary test nor the deterministic-path ban, which is why the scenario-director
composition root lives there (`server/ai_director_service.py`, called from `commands/guild.py`).
The flavor application must follow the same shape: deterministic helpers in `world/quests` that
never reference `world.ai`, and the composition (client acquisition + layer call) in `server/`.

## Goals / Non-Goals

**Goals:**
- Wire the flavor layer into instance-scene materialization: one post-commit generation per
  freshly spawned scene with a scene-sentence context.
- Keep every deterministic-path module free of `world.ai` references (contract stays green without
  modification).
- The write (`room.db.scene_flavor`) is deterministic, idempotent, and never blocks or rolls back
  materialization.
- Completed flavor is pushed to players present in the room and rendered in `look` on every entry
  path.
- Any failure — offline profile, transport, validation exhaustion, missing context, vanished room —
  resolves to "no flavor" with no gameplay impact.

**Non-Goals:**
- No changes to the flavor layer itself (generation contract, gates, degrade) — owned by
  scene-flavor-layer.
- No regeneration, per-entry variation, or time-of-day flavor.
- No WebClient OOB panel for flavor (plain text push + look rendering only).
- No flavor on permanent-layer destinations or already-bound stages.
- No changes to `world/ai/profiles.py` or `llm-profiles` requirements.

## Decisions

### D1: Deterministic context is a plain bounded dict produced by scene_builder
`world/quests/scene_builder.py` gains a pure helper that builds
`flavor_context: dict | None` from the requirement, definition, room, and origin: keys
`scene_sentence` (requirement's or the archetype registry's), `quest_context` (the definition's
`display_name` plus its `quest_type`), `room_name` (the room's key / `_scene_name`), and `region`
(the anchor placement display name when `anchor_near` is set, else empty). `None` when no
scene-sentence context exists (e.g. a requirement with neither sentence nor archetype) or the
stage was already bound.

Rationale: the deterministic-path ban forbids `world/quests` from importing `world.ai.scene_flavor`
(whose `SceneFlavorContext` lives in the layer). A plain dict with the exact four bounded keys is
the seam: scene_builder stays ban-clean, and the composition root adapts the dict into the layer's
frozen context. Alternative considered: duplicating the frozen dataclass in `world/quests` —
rejected, two shapes drift; a dict is value-only.

### D2: The composition root lives in server/, scheduled on commit by the enter command
`server/scene_flavor_service.py::schedule_scene_flavor(room, flavor_context)` mirrors
`ai_director_service.py`: it validates the plain dict at the adapter boundary (exactly the four
keys, all string values — a cross-layer contract test locks the shape), builds the `scene_builder`
profile client function-locally (live `OpenAICompatClient` when the profile is enabled, the
non-`None` offline stub otherwise — deferred imports, so a cold import never binds the guardrail
logger or loads transport), wraps the dict into the layer's context, and fires
`generate_scene_flavor(context, client)` as a fire-and-forget Deferred. `CmdEnterScene` registers
the scheduling through `transaction.on_commit(...)` so it fires only after the spawn transaction
actually commits — a nested outer transaction that rolls back never schedules a generation
(mirroring `_schedule_occupant_portraits`'s on-commit precedent).

Every synchronous step — dict validation, client construction, context wrapping, and obtaining the
Deferred — is wrapped in a `try/except` that logs a bounded diagnostic and returns normally, so an
unregistered layer, a malformed context, or a client-construction failure can never propagate into
the 進入 command. The Deferred's errbacks log and resolve to nothing.

Rationale: `commands/` may import `server/` modules (the established ai_director_service pattern);
`world/quests` must not. Scheduling at the command site keeps materialization itself free of any
generative concern, and on-commit registration honors the "only after the spawn transaction
commits" contract even under nesting.

### D3: The write is deterministic and idempotent, guarded by an authoritative existence check
`world/quests/scene_builder.py::apply_scene_flavor(room, text) -> bool` is the sole writer of
`room.db.scene_flavor`. Because the completion callback may hold a stale cached typeclass after
instance reclamation deletes the `ObjectDB` row, it first verifies the row authoritatively
(`ObjectDB.objects.filter(pk=room.pk).exists()`), then no-ops (`False`) when the room is gone or
already carries a flavor; database/object-deletion exceptions are caught and also return `False`.
The write never touches `room.db.desc` and never raises from flavor application. The completion
callback checks idempotency again before writing, so a race between completion and a re-materialized
room can never overwrite.

Rationale: single-writer boundary; regeneration is impossible by construction (a flavor already
present never regenerates, and scheduling happens only for freshly spawned rooms); the
authoritative check makes "vanished room → no write, no error" provable rather than cache-dependent.

### D4: Push and look rendering
On a successful write, the completion path messages every `PlayerCharacter` whose location is the
room (the flavor paragraph as plain text; players who left are not chased). The shared appearance
layer renders `room.db.scene_flavor` as a paragraph after the room description and before the
「出口」 line: the insertion point is `typeclasses/rooms.py::Room.get_display_desc` — the room base
class's description hook, which Evennia's `return_appearance` calls for every room and which the
text 看 command, the character `at_look` seam (via `super().at_look`), and the webclient
`explore.look` path all share (the same layer that owns `get_display_exits` and friends). The
flavor paragraph renders only when the attribute is present; flavor-less rooms render byte-identical
output.

Rationale: the flavor is prose, not state; the shared room frame keeps Telnet and browser identical
with no panel work. Alternative considered: an OOB art-panel-style update — rejected as overkill
for a text paragraph; look re-rendering covers late players.

### D5: Failure is always "no flavor"
Offline/disabled profile (guardrail short-circuit → `None`), transport failure, validation
exhaustion, missing context, and vanished room all resolve to no write and no push. No retry loop
beyond the layer's own guardrail budget; no staff operation in this change.

Rationale: the offline-playability criterion; flavor is decoration.

## Risks / Trade-offs

- [Completion races with instance reclamation] → `apply_scene_flavor` verifies the room still
  exists before writing; a reclaimed room simply has no flavor.
- [Player leaves before completion] → Push targets only present players; a later `look` in the
  room shows the flavor.
- [The `region` fragment may be empty for non-anchored scenes] → The prompt placeholder renders
  empty (bounded); flavor quality varies, never correctness.
- [A flavor could contradict a later quest stage's story] → Out of scope; flavor is bounded
  atmosphere prose validated to contain no numbers or fabricated entities; prompt tuning is data.
- [Fire-and-forget Deferred errbacks could spam logs] → Bounded diagnostic logging per failure,
  mirroring art-queue failure logging; no retry storm.

## Migration Plan

No migration; the project is unreleased. The change is additive: a new `server/` module, new
functions in scene_builder, a new result field, and the appearance-frame paragraph. Rollback is
reverting the command call and the frame rendering; a stray `scene_flavor` attribute is inert and
can be ignored or cleared.

## Open Questions

- None blocking. Whether flavor should later appear in a WebClient panel, vary by time of day, or
  be staff-regenable is deferred; `room.db.scene_flavor` and the shared frame are the seams.
