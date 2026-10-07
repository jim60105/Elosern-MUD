# GM Portal S6 Design: Developer Console

- Date: 2026-10-06
- Status: Approved design
- Parent: `docs/superpowers/specs/2026-10-06-gm-portal-design.md` (sub-project S6)
- Depends on: S1 (portal skeleton), S3 (entity pages and raw tab), S5 (saves)

## 1. Responsibility

S6 is a developer console: general-purpose tools that change the world state
on the operator's command, for repairing a broken save and for setting up test
situations.

### Why a console and not a catalogue of repairs

A catalogue of detected problems with predefined repairs only covers faults
someone anticipated. The faults that most need rescuing are the unanticipated
ones, which by definition have no predefined repair. S6 therefore provides
general tools, and the operator decides what is wrong and how to fix it.

### Two layers

- **Raw editing** is the general core: it can fix any fault expressible as
  object Attributes, tags, or location.
- **Domain verbs** cover the operations where raw editing is error-prone
  because the change cascades into other state or the stored shape is complex.
  The first batch is deliberately small; verbs are added when a need appears.

### No audit trail

The operator is the only user and does not audit themselves. S6 has no audit
model. Every operation still emits a `gm_action` log event under the ordinary
observability rules, which lets a later investigation line up timestamps.

## 2. Snapshot policy

A console write is undoable by restoring the save taken before it. A new save
is needed only when the game has progressed since the last one, measured by
in-game time.

- `server/console/snapshot_policy.py` keeps a baseline world clock `tick` in
  process memory.
- Before every console write (verb or raw edit): read the current `tick`. If
  there is no baseline (first write since server start) or the `tick` differs
  from the baseline, create an `auto_intervention` save through S5
  `create_snapshot`.
- After every console write, set the baseline to the current `tick`. This
  absorbs the console's own clock advance verb.
- A manual save from the S5 page also sets the baseline.
- If the snapshot fails, the operation is not executed (`snapshot_failed`).
  Without a save there is no undo.

Known trade-off: player actions that change state without advancing in-game
time (for example a conversation that does not pass time) do not trigger a new
save. Chosen for simplicity.

## 3. Domain verbs (first batch)

Each verb lives in the single-writer package that owns its data, in a `gm.py`
module. Every verb validates its input (types, ranges, registry keys) before
writing, is all-or-nothing, and returns a stable error code with state
unchanged on failure.

| Verb | Module | Why raw editing is not enough |
| --- | --- | --- |
| `give_item` / `take_item` (key, quantity) | `world/rules/gm.py`, via `equipment.plan_inventory_delta` and `apply_inventory_plan` | Items are materialised objects matched to registry keys; removing an equipped item must sync equipment state and gauge limits |
| `set_wallet` (integer copper ≥ 0) | `world/rules/gm.py` | Enforces the integer-copper invariant; no wallet writer exists today |
| `set_trait_base` / `set_gauge` | `world/rules/gm.py` | The traits handler shape is complex; base values must stay literal (no multipliers) and within the trait scale |
| `advance_clock` (seconds) | `world/rules/gm.py`, new `AdvanceSource.GM` | Must run the full clock settlement; not bound to a character, unlike `time_skip.advance_skip` |
| `teleport` (entity, room) | `world/maps/gm.py`, settling in `world/rules/movement_settlement.settle_relocation` | Must run departure and arrival consequences (dialogue session, party, instance pins) without movement cost; the settlement owns every write, so the adapter never imports a map-knowledge write helper |
| `spawn_monster` (species, variant, room) / `delete_entity` | `world/maps/gm.py` | Spawning goes through `monster_individual.construct_species_individual`; deletion must run Evennia delete hooks and release skip-safety and combat registrations |
| `set_quest_state` / `set_quest_stage` / `issue_quest` | `world/quests/gm.py` | Quest records are frozen structures with bindings and pins to release or create |
| `retract_memory` / `supersede_memory` | `world/narrative/gm.py`, via `memory.revise_memory` and `supersede_memory` | Narrative models are append-only; raw editing cannot reach them |

## 4. Raw editing

`server/console/raw.py` applies a batch of changes to one Evennia object
inside one transaction; any failure rolls back the whole batch.

- Operations: `set_attr` (key, optional category, JSON value), `del_attr`,
  `add_tag`, `remove_tag` (with category), `set_location` (no movement
  settlement).
- Values use the S3 serialisation: `{"$ref": "#123"}` is resolved back to an
  object reference.
- Typeclass changes are not offered.
- No rule validation or invariant check runs. The UI states this permanently
  while edit mode is on.

Out of scope: raw editing of narrative models (append-only by design; use the
memory verbs), editing other Django models, and arbitrary code execution (the
Django shell still exists; the console does not rebuild it).

## 5. Execution flow

Verbs and raw edits share one flow:

1. Apply the snapshot policy (§2).
2. Execute the operation.
3. Emit `gm_action` with the verb (or `raw_edit`), target, argument summary,
   and result in `context`.
4. Return the target's updated state so the page refreshes that section.

## 6. Portal

Operations appear where the problem is seen:

- **S3 entity pages**: a 主控台 button in the header opens a side drawer
  listing only the verbs that apply to that entity kind (player character:
  items, wallet, traits and gauges, teleport, quests; monster: traits and
  gauges, teleport, delete; room: spawn monster).
- **S3 raw tab**: an 編輯 toggle makes Attributes, tags, and location editable,
  with a permanent 繞過規則層 warning bar.
- **S3 NPC memory tab**: 撤銷 and 取代 actions on each record.
- **S2 dashboard world section**: 推進時鐘.
- Confirmation dialogs list the operation and state whether a save will be
  taken first (in-game time advanced since the last save) or not.
- Results show as a toast and refresh the affected section; failures show the
  error code and message.

## 7. API

| Route | Purpose |
| --- | --- |
| `POST /gm/api/console/<verb>` | Run a domain verb; JSON body of arguments |
| `POST /gm/api/state/object/<dbref>/raw` | Raw edit batch |
| `GET /gm/api/console/status` | Current tick, baseline tick, whether the next write takes a save |

- `<verb>` must be a registered verb name.
- Responses include `snapshot: {"taken": bool, "save_id": str | null}`.
- Error codes: `unknown_verb`, `invalid_argument`, `registry_key_not_found`,
  `target_not_found`, `target_kind_mismatch`, `raw_edit_invalid`,
  `snapshot_failed`.

## 8. Documentation amendments (applied by the S6 change)

- `AGENTS.md`: name the `gm.py` modules in `world/rules/`, `world/maps/`,
  `world/quests/`, and `world/narrative/` as console verbs owned by their
  packages, and `server/console/raw.py` as the console's raw editing path.
- `AGENTS.md` and `docs/gm/overview.md`: replace the ban on hand-patching
  quest records, money, experience, inventory, and combat results with: manual
  patching happens only through the GM console, which snapshots first when
  in-game time has advanced since the last save; never in a Django shell.

## 9. Tests

- Each verb: normal path, every validation failure, all-or-nothing (state
  unchanged after failure).
- `teleport`: dialogue session, party, and instance pin consequences.
- `delete_entity`: skip-safety and combat participant registrations released.
- `advance_clock`: full settlement with `AdvanceSource.GM`.
- Memory verbs: only append revisions; original records unchanged.
- Raw edit: `$ref` resolution, batch atomicity, typeclass not editable.
- Snapshot policy: unchanged tick takes no save; changed tick takes one; the
  first write after start takes one; snapshot failure blocks the operation;
  manual save resets the baseline.
- Contract: `web/gm/` writes state only through the registered `gm.py` verbs
  and `server/console/raw.py`. The S3 read-only AST contract keeps covering
  `web/gm/readers/`.
- Vitest: drawer verb filtering per entity kind, edit-mode warning bar,
  confirmation dialog save notice. Storybook stories for new components.
- New Python test modules registered in `.github/evennia-shards.json`.
