## Why

狀態偽裝 has a cast path that does nothing. `commands/action.py` builds its `event_context` by reading
`self.caller.db.disguised_stats` and the handler writes that same dict straight back, so casting the
skill re-applies whatever a preset or import already declared — an entity with no authored declaration
casts it and stays exactly as visible as before. In combat no caller supplies the key at all, so the
skill is advertised and then refused. There is also no way to place a veil on anyone else. The
divine-mystery 帷幕線 puts three further nodes on this verb
(`docs/lore/skill-trees/divine-mystery.md` §2) and its root has to actually veil someone first.

## What Changes

- The veil's displayed values are **derived deterministically from the race registry**, not supplied by
  a caller: the displayed combat five are rendered at the top of the mundane (human) bands the registry
  already declares, so a veiled elf reads as an exceptional human rather than as an elf.
- `set_disguise` drops its required `event_context` key, so preflight and the shared preview stop
  advertising and then refusing the skill, and it becomes castable in combat like any other skill.
- The layer records the **provenance** of the veil it holds — divine when a divine cast wrote it,
  mundane for every authored import/preset/companion seed — stored beside the display mapping so the
  mapping's shape, schema and readers are untouched.
- A veil cast at **another** entity applies the veil to that entity. A veil cast at **self** toggles
  only against a veil this verb itself placed: it lifts a DIVINE veil, and applies (refreshing) over a
  mundane one, so a caster is never trapped behind their own face and never accidentally strips the
  authored disguise their character card starts the game wearing.
- Authored preset/import declarations keep working untouched: they are seeded at construction and this
  change does not read or rewrite them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-handler`: MODIFIED — the 狀態偽裝 requirement gains the derivation rule, the
  provenance-scoped self-toggle, and the other-target application, while keeping its existing
  single-writer scenarios intact.
- `disguised-stats-boundary`: ADDED — the provenance record, its storage separation from the display
  mapping, and its mundane default.
- `effect-context-validation`: MODIFIED — `set_disguise` declares an empty required set.

## Impact

`world/rules/skill_effects.py` (the derived-veil recipe and the provenance write beside the existing
write); `world/rules/action.py` (`_handle_set_disguise`, its registration, and
`_snapshot_entity_state`/`_restore_entity_state` for the new attribute); the explicit snapshot tuples
in `world/rules/cast_settlement.py` and `world/rules/clock.py` that already carry `disguised_stats`;
`commands/action.py` (drop the now-dead `status_disguise` context special case);
`world/rules/tests/test_disguise_boundary.py` (extend the forbidden-module scan to the new attribute
name — the per-file writer ledger needs no new entry, because both writes stay in
`world/rules/skill_effects.py`); tests plus `.github/evennia-shards.json`.

## Batch

- depends-on: none
- Code conflict note for the supervisor: this change and `conferral-grant-store` both MODIFY the
  `effect-context-validation` "handlers declare their required event context" requirement and both edit
  `world/rules/action.py`'s handler registrations. Whichever lands second rebases its MODIFIED copy onto
  the synced main spec so the requirement names both empty-set handlers. They touch different handler
  functions and different `skill-handler` requirements.
