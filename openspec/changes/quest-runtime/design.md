## Context

Roadmap item 15 owns the deterministic quest entity, stage progression, completion, and failure. It
depends on the player-driven clock and map-instance lifecycle, and it precedes both guild economy and
the generative layer. The implementation must therefore be useful with hand-written content and no AI,
while exposing stable inputs for later changes without implementing their responsibilities early.

The landed repository provides these seams:

- `PlayerCharacter.quest_log` is an unused persistent list attribute.
- `ActionResolver` commits skill effects atomically and emits structured `EventLog` records.
- Combat and `CmdCast` both invoke `ActionResolver`, but neither dispatches successful logs to consumers.
- `WorldClock` reserves `quest_deadlines` before `instance_reclamation` in `_STAGE_ORDER`.
- Anchor and grid rooms have stable `anchor_key`/`xyz` identities. Instance rooms have stable dbrefs and
  idempotent pin/unpin APIs, but their creation from AI requirements belongs to SceneBuilder.
- The normal grid/instance traversal path calls `at_object_receive`; the wilderness contrib's normal
  movement path assigns `.location` directly and does not.

The previous draft coupled change 15 to the future AI `QuestBlueprint`, tried to spawn generated
instances at acceptance, and invented a gathering skill. It also left static destinations
unrepresentable and normal action progress manually dispatched. This rewrite replaces those choices
with a normalized runtime definition, production event wiring, and explicit future-change boundaries.

## Goals / Non-Goals

**Goals:**

- Provide immutable, validated `QuestDefinition` content suitable for a hand-written catalog.
- Persist deterministic per-character quest state and support accept, abandon, advance, complete, fail,
  and retry-after-terminal behavior.
- Drive progress automatically from successful player actions, combat actions, and room arrival.
- Use stable dbrefs for concrete entities and stable anchor/XYZ locators for permanent destinations.
- Settle deadlines through the existing clock stage and release instance pins on every stage exit.
- Keep action-caused quest progress atomic with the action that produced it.
- Leave a narrow conversion boundary for change 20 and an instance-binding boundary for change 21.
- Prove a no-AI hand-written API-level accept-to-completion seam that change 16 can expose through guild
  commands, a player-reachable combat entry, and reward settlement.

**Non-Goals:**

- No AI `QuestBlueprint` JSON schema, semantic guardrail, retries, or template degradation; change 20
  owns those proposal-layer concerns.
- No instance spawning, prototype construction, NPC generation, or `location_req` interpretation;
  change 21 owns SceneBuilder and binds its created objects into this runtime.
- No guild board, quest-giver component, turn-in command, reward payout, merit, rank, wallet, or shop
  behavior; change 16 owns those player-facing economy concerns.
- No fake gathering skill, general pickup command, loot table, or inventory transaction.
- No wilderness-coordinate destination until movement exposes a reliable arrival event.
- No party sharing or companion kill credit. A DEFEAT objective advances only from an action whose actor
  is the quest-owning `PlayerCharacter`.
- No migration or compatibility layer for the discarded draft; the project is unreleased.

## Decisions

### D-1. Runtime input is `QuestDefinition`; change 20 owns AI `QuestBlueprint`

`world/quests/definitions.py` defines the normalized deterministic input:

```python
class QuestType(StrEnum):
    GATHER = "採集"
    DEFEAT = "討伐"
    ESCORT = "護衛"
    EXPLORE = "探索"
    EMERGENCY = "緊急"

class ObjectiveKind(StrEnum):
    DEFEAT = "defeat"
    REACH = "reach"
    ESCORT = "escort"

class DestinationKind(StrEnum):
    ANCHOR = "anchor"
    GRID = "grid"
    BOUND_INSTANCE = "bound_instance"

@dataclass(frozen=True)
class RoomLocator:
    kind: DestinationKind
    anchor_key: str | None = None
    xyz: tuple[int, int, str] | None = None

@dataclass(frozen=True)
class QuestObjective:
    kind: ObjectiveKind
    quantity: int = 1
    monster_tier: str | None = None
    destination: RoomLocator | None = None
    requires_bound_targets: bool = False

@dataclass(frozen=True)
class QuestStage:
    index: int
    objective: QuestObjective

@dataclass(frozen=True)
class QuestDefinition:
    key: str
    display_name: str
    quest_type: QuestType
    rank: str
    stages: tuple[QuestStage, ...]
    deadline_hours: int | None
```

The structures contain no mutable dict/list fields. Registration validates a non-empty contiguous stage
sequence; positive quantities; exactly the fields required by each objective kind; known monster tiers,
anchor keys present in `ANCHOR_PLACEMENT_REGISTRY`, and grid-map keys; and unambiguous locator shapes.
Lore-known anchors without a landed placement are rejected because no reachable `AnchorRoom` can emit
their arrival. `None` has one
deadline meaning only: no deadline. A positive integer is converted to ticks at acceptance. There is no
implicit third state or default.

`QuestType` classifies the whole quest and does not determine its stage mechanics. An emergency quest can
contain any objective kind. ACQUIRE is deliberately absent until change 16 can define it at the real
inventory transaction boundary; a public caller-supplied "item acquired" assertion would permit forged
quest progress. Change 20 may define a richer proposal containing `location_req`, `npc_req`, reward, and
failure requirements; after guardrail validation it must translate that proposal into this closed
deterministic type. AI-originated dicts never enter the registry directly.

Alternative rejected: naming this structure `QuestBlueprint` and matching the §7.1 JSON now. That would
make the deterministic runtime own an AI proposal contract before the guardrail and SceneBuilder exist.

### D-2. Definitions are process-local source data; records are plain persistent data

`QUEST_DEFINITION_REGISTRY` is populated by one `register_quest_definition()` function. Registering an
equal definition under an existing key is an idempotent no-op; registering different content under that
key raises before replacement. A
`world/quests/catalog.py` module declares at least one fixed, no-AI introductory hunt definition, and
`world/quests/bootstrap.py::sync_quest_runtime()` imports/registers the catalog idempotently before
registering event consumers and deadline settlement.

Each accepted quest is stored as a JSON-safe dict in `PlayerCharacter.db.quest_log` and viewed through a
frozen dataclass:

```python
@dataclass(frozen=True)
class QuestRecord:
    quest_id: str
    definition_key: str
    state: QuestState
    stage_index: int
    stage_progress: int
    deadline_tick: int | None
    accepted_tick: int
    stage_room_id: int | None
    objective_target_ids: tuple[int, ...]
    protected_entity_ids: tuple[int, ...]
    failure_reason: str | None
```

`QuestState` contains `IN_PROGRESS`, `COMPLETED`, and `FAILED`. Unaccepted is absence. Abandonment is a
failed record with reason `abandoned`. A character may have at most one active record for a definition;
completed or failed definitions may be accepted again. The deterministic quest ID is
`<definition-key>:<acceptance-number-for-that-character>` so reproducibility does not depend on a random
UUID.

Every interactive operation parses all records it touches before writing a replacement list. Invalid
records raise a named `QuestDataError` without a partial write. Deadline settlement catches that error
at the character boundary, records a diagnostic, and continues with other characters without changing
the malformed owner's records or pins. Startup always registers definitions before the clock source; an
active record whose definition is absent is reported as `QuestDataError` rather than silently
interpreted against different content.

### D-3. Stage targets and generated instances are bound to records, not definitions

Static destinations use `RoomLocator(ANCHOR, anchor_key=...)` or `RoomLocator(GRID, xyz=...)` and need no
database identity at definition-registration time. A stage expecting generated content uses
`BOUND_INSTANCE`; its accepted record starts with `stage_room_id=None` and cannot complete until a caller
binds a room.

`bind_stage_runtime(actor, quest_id, *, room=None, objective_targets=(), protected_entities=())`
validates that the record is active, the stage still matches, `room` is an `InstanceRoom` when supplied,
and all targets are live `LivingEntity` objects. Objective-target dbrefs drive DEFEAT progress;
protected-entity dbrefs drive ESCORT presence and key-entity-death failure. Preflight rejects any dbref
present in both sets, and strict record parsing rejects persisted overlap, so defeating an objective
target can never fail the same quest. It stores integer dbrefs and pins the room with
`quest:<character-id>:<quest-id>:stage:<stage-index>`. Repeating the same binding is idempotent; attempting
to replace an existing binding raises before mutation. Change 21 will call this API after SceneBuilder
successfully creates the room and NPCs. Change 15 may use a pre-created instance only in integration
tests; it never calls `spawn_instance_room()`.

The transition helper releases the exact pin before clearing the binding whenever a stage advances or
the quest completes, fails, or is abandoned. Deleted bound targets simply stop matching progress. A
missing/deleted bound room is treated as already unpinned, allowing the quest to fail or be abandoned
without crashing.

### D-4. Action events carry stable identity and quest effects join the action commit

The existing human-readable `actor`, `target`, and `targets` keys remain for rendering. Action-generated
lethal damage additionally emits `target_defeated` with integer `target_id` and `monster_tier` data.
Runtime matching never treats a display key as unique.

Step 7 computes lethal crossings from projected HP in pending-effect order. It emits one
`target_defeated` only when projected HP crosses from positive to zero-or-lower, so multiple damage
effects against one target neither use stale HP nor emit duplicate defeat events.

`register_event_effect_planner(name, planner)` adds a deterministic extension seam to the action module.
After step 7 builds the successful `EventLog`, each planner returns additional `PendingEffect` values.
The quest planner returns quest-log and instance-pin mutations derived from the immutable event data and
the `ActionRequest`. These pending effects join the same `_commit()` transaction as damage, resource
cost, and progression. Planner failure rejects before commit; commit failure restores the action and
quest surfaces together. The resulting EventLog describes the player action, not internal quest bookkeeping.

The quest planner applies DEFEAT progress only to the acting `PlayerCharacter`'s active current stage.
It matches an explicitly bound target dbref when `requires_bound_targets=True`; otherwise it matches the
definition's monster tier. Protected-entity defeat failure may inspect every player character because a
hostile actor can kill a bound escort, but it matches the exact protected dbref and this is a
single-player system. For one AREA EventLog, matching defeat entries are aggregated per quest, progress
is capped at the current objective quantity, at most one stage transition occurs, and surplus kills are
not carried into the next stage.

Alternative rejected: asking every command and combat caller to manually invoke `observe_event_log()`.
That duplicates composition logic and permits successful actions to omit quest progress.

### D-5. Arrival hooks resolve static and bound destinations

`QuestObservableRoomMixin.at_object_receive()` calls `super()` and then invokes
`observe_room_entry(self, obj)` for `PlayerCharacter`. `GridRoom` adopts it, so `AnchorRoom` inherits it;
`InstanceRoom` adopts it while preserving its existing interacted flag behavior.

For REACH, arrival matches the objective's static locator or the record's bound instance dbref. For
ESCORT, the destination must match and every currently protected entity must be alive and present.
ESCORT requires at least one protected entity before it can complete. One arrival may advance multiple
independent active quests, but each quest transitions at most once per hook call.

`TerrainRoom` does not adopt the mixin. The installed wilderness movement implementation bypasses
`move_to()` during ordinary entry and stepping, so advertising wilderness support through this hook
would create a silently unreachable objective.

### D-6. All lifecycle transitions use one validated replacement operation

`accept_quest()`, `abandon_quest()`, room progress, deadline failure, and instance binding
all route through helpers that follow the same order:

1. Parse and validate the current list and referenced definition.
2. Compute the complete replacement record and required pin delta without writes.
3. Enter `transaction.atomic()` and apply pin delta plus one replacement quest-log assignment.
4. On an exception, restore the pre-operation attribute values so Evennia's in-process attribute cache
   agrees with the database rollback.

Action-caused transitions use the same replacement computation but expose it as `PendingEffect` values,
allowing `ActionResolver` to own the surrounding transaction and snapshot restoration. A quest-log
effect names a `PlayerCharacter` and declares `quest_log`; a pin effect names an `InstanceRoom` and
declares `instance_pin`. `_commit()` aggregates declared surfaces per touched object,
`_snapshot_touched(obj, surfaces)` snapshots `quest_log` or `pin_reasons` through surface-specific
handlers, and restore applies those snapshots even when the object was not in the original request.
Existing living-entity and battlefield surfaces retain their current handlers. State-transition helpers
are idempotent for already-terminal records and reject stale stage indices before changing pins.

Alternative rejected: spawn/pin/update as separate best-effort operations. That can leave an orphan pin
or an active record referring to work that never started.

### D-7. Deadline settlement uses the existing ordered clock stage

Acceptance computes `deadline_tick = accepted_tick + deadline_hours * seconds_per_hour` or `None` for no
deadline. `settle_quest_deadlines(start_tick, end_tick)` fails every active record with a non-`None`
deadline at or before `end_tick`, releases its current instance pin, and emits JSON-safe
`ScheduledEvent` payloads.

`sync_quest_runtime()` registers this source as `quest_deadlines`. The server startup composition root
calls quest sync after lore and map sync, rather than making `world/maps/bootstrap.py` import quests.
`_STAGE_ORDER` remains unchanged, so deadline failure releases a pin before instance reclamation runs in
the same `WorldClock.advance()` call.

### D-8. Rulebook YAML is used only for tunable numbers

This change adds no transition-rule YAML. Stage advancement, completion, and failure are the closed quest
state machine, not balance knobs. Deadlines are explicit definition data. This follows D9 without adding
a decorative table whose effects merely duplicate hard-coded transitions. If change 16 adds a tunable
active-quest cap or reward parameters, those numeric values belong in rulebook YAML then.

## Risks / Trade-offs

- **[Risk] Change 20 must translate its richer AI proposal into a smaller runtime type.** → Keep one
  documented registration boundary and test that no raw dict enters the runtime registry.
- **[Risk] Attribute-backed multi-object writes can leave stale process caches after database rollback.**
  → Snapshot and restore every touched attribute in the shared transition helper and fault-inject every
  lifecycle operation involving a pin.
- **[Trade-off] Companion kills do not advance DEFEAT progress.** → Player kill credit is deterministic
  and sufficient for change 15's API-level integration; party/companion attribution needs a separate policy.
- **[Trade-off] ACQUIRE is absent from change 15.** → Change 16 must add it at the inventory-owning
  transaction boundary, where progress can be derived from a real item delta rather than caller claims.
- **[Trade-off] Dynamic instance stages cannot progress before binding.** → This is fail-closed and keeps
  SceneBuilder in change 21. Permanent anchor/grid quests remain runtime-completable without AI.
- **[Risk] Linear scans inspect every active record and, for bound-entity death, every player character.**
  → Accepted for a single-player game; exact dbref matching prevents key collisions.

## Migration Plan

No migration is required. The previous artifacts were planning only and no quest runtime has shipped.

## Open Questions

None. Change 16 must use the lifecycle APIs for guild accept/turn-in, add ACQUIRE only at its real
inventory transaction boundary, and include a player-command integration test that can enter the landed
combat runtime. Change 15's API-level test alone does not satisfy the player-playable Phase-4 milestone.
Change 20 must translate validated AI proposals into `QuestDefinition`; change 21 must spawn before
calling `bind_stage_runtime()`.
