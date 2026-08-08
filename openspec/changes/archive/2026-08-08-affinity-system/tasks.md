# affinity-system Tasks

## 1. Record store and handler

- [x] 1.1 Create `world/rules/affinity.py` with the frozen `AffinityRecord` dataclass (`value`,
      `cap`, `daily_gain`, `daily_tick`) plus `to_storage()` / `from_storage()` following the
      `QuestRecord` idiom: tolerant field parsing with defaults, type-violating values reset to a
      fresh record and logged, never raising. No explicit version field; the tolerant parser is
      the evolution mechanism.
- [x] 1.2 Add the `RelationHandler` class with `affinity_for(player)`, `stage_for(player)`,
      `has_record(player)`, and the internal `_load` / `_save` over `npc.db.relations_data`
      (per-player keyed dict). Reads SHALL return defaults without persisting anything — a read
      never creates a record; `has_record` is the only existence check.
- [x] 1.3 Mount the handler on `LivingEntity.relations` as a `@lazy_property`, replacing the
      `AttributeProperty(default=None)` placeholder in `typeclasses/entities.py`; leave `persona`
      as the only remaining `None` placeholder seam and do not touch `sexual`, `buffs`,
      `equipment`, or `skills`.
- [x] 1.4 Update `typeclasses/tests/test_entities.py` seam assertions: `relations` is now a working
      handler backed by `relations_data`; `persona` still equals `None`; the other handlers stay
      instance assertions.

## 2. Rulebook ladder

- [x] 2.1 Add `world/rules/rulebook/affinity.yaml` with `invite_threshold: 70`,
      `daily_interaction_cap: 5`, `quest_completion_gain: 2`, and exactly seven stage rules
      (初識 0 / 熟識 10 / 親睦 30 / 信賴 50 / 羈絆 70 / 至愛 90 / 絕對羈絆 100), each with a stable
      ID, floor, display name, and a look-flavor template.
- [x] 2.2 Add loading/validation for the ladder: exactly seven stages, floors strictly increasing
      and equal to the canonical sequence 0/10/30/50/70/90/100 (no duplicates, no deviation);
      thresholds positive; failure closes with a named validation error before any write.
- [x] 2.3 Implement stage resolution ("last stage with `floor <= value`") and stage-name lookup for
      display; values >= 100 resolve to the topmost stage.
- [x] 2.4 Add one test per rule ID in `world/rules/tests/` (stage boundaries, deviant-floor
      rejection, constants from YAML, 100+ topmost resolution).

## 3. Sole-writer API

- [x] 3.1 Implement `apply_affinity_change(npc, player, source, delta)` in `world/rules/affinity.py`
      as the only affinity writer: closed source set (`talk` / `trade` / `guild` / `ai_dialogue` /
      `quest_completion`) with unknown sources rejected without writing; non-NPC owners rejected
      without writing; lazy `daily_gain` reset only before a capped positive delta (stored tick vs
      current world day); capped sources share the cap of 5, `quest_completion` and negative
      deltas bypass it; `applied = min(requested, remaining_budget, cap - value)` with the daily
      counter accruing only the actual increase (zero applied consumes no budget); negative deltas
      floored at 0, never resetting or restoring budget.
- [x] 3.2 Return a structured `AffinityChangeOutcome` (applied, delta used, budget capped, source
      rejected) for caller feedback; render no player-facing numbers anywhere; provide the fixed
      non-numeric Traditional Chinese capped-hint string for call sites.
- [x] 3.3 Add the named party auto-leave recheck hook (`run_auto_leave_recheck(npc, player)`),
      invoked after every negative delta, currently a deterministic side-effect-free no-op.
- [x] 3.4 Add pure unit tests for the writer: budget exhaustion, partial delta (budget-limited),
      zero-applied-at-cap consumes no budget, cross-day reset, quest exemption, negative-delta
      path (never resets/restores), unknown-source rejection, non-NPC owner rejection, corruption
      recovery, hook invocation.

## 4. Call-site wiring

- [x] 4.1 Add the deterministic talk writer (shared by `commands/talk.py` and the webclient
      `explore.talk_scripted` path): resolves known vs unknown keyword through the dialogue
      service, snapshots the player's `guide_progress` and the host's affinity record, applies the
      authored response plus any `guide_progress` update plus the +1 `talk` gain in one
      transaction, and restores both surfaces on failure. Unknown keywords and no-keyword paths
      write nothing.
- [x] 4.2 Wire the `trade` gain: successful `buy()` / `sell()` in `world/rules/economy.py` grant +1
      (`trade` source) with the local Merchant host; extend `_snapshot_trade` / `_restore_trade`
      with the host's `relations_data` surface.
- [x] 4.3 Wire the `guild` gains: successful `register_adventurer()` grants +1 (`guild` source)
      with the staff host (affinity joins its snapshot/restore surfaces); `accept_guild_offer()`
      gains an outer all-or-nothing commit (snapshot of the actor's quest-log and pin surfaces
      plus the host's affinity record, `accept_quest()` and the gain in one transaction, restore
      on failure); a started `start_guild_exam()` grants +1 inside the same atomic block that
      creates the exam record and session, with the examiner's affinity record joining the exam
      snapshot/restore surfaces.
- [x] 4.4 Add integration tests proving all-or-nothing behavior: rejected or failing host
      operations grant no affinity; fault injection restores the affinity surface alongside the
      host surfaces for talk, trade, registration, acceptance, and exam.

## 5. Display

- [x] 5.1 Render the NPC affinity stage line in the shared appearance layer (the same module the
      text look command, `at_look`, and webclient explore-look use), gated on `has_record(player)`
      and rendering the YAML flavor template from `stage_for(player)`; the read never persists.
- [x] 5.2 Extend the three-path appearance parity tests: add a webclient action test under
      `web/webclient/actions/` covering `explore.look`, plus an NPC holding a stage record and a
      recordless monster/NPC — identical stage line across paths, no numeric value, cap, threshold,
      or English frame anywhere, and a look at a recordless entity persists nothing. Add one
      managed browser explore-look regression so the UI action transport keeps the stage line.

## 6. Verification

- [x] 6.1 Run the focused affinity, dialogue, economy, guild, appearance, entity, and web-action
      test labels (`uv run --locked evennia test --settings test_settings.py` for the touched
      packages).
- [x] 6.2 Run `uv run --locked python -m compileall -q world typeclasses commands server` and keep
      `git diff --check` clean.
- [x] 6.3 Run `openspec validate affinity-system --strict` and the spec-traceability check
      (`uv run --locked python -m tools.spec_traceability check`).
- [x] 6.4 Confirm no player command surface changed (no new commands in this change) so
      `docs/game/commands.md` / `command-reference.md` need no edit; run
      `tests/test_command_docs.py` to prove it.
