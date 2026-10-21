# Tasks

## 1. Narration catalog foundation

- [x] 1.1 Create `world/skills/narration/` with `vocab.py` holding the frozen `NarrationRow`,
  `NarrationBands`, the line bounds (`MAX_LINE_CODE_POINTS`, `MAX_NAME_CODE_POINTS`,
  `MAX_SLOTS`) and the damage/heal/pleasure band tables; verify with a pure test that each
  band table is finite, inside `(0, 1]`, strictly ascending and closed, and that an invalid
  table raises.
- [x] 1.2 Create the shared pools module (kind pools with 3–5 variants each, the compact
  fallbacks, the verdict clauses, the structural lines) using the design D7 kind inventory;
  verify every non-internal `_ENTRY_TEMPLATES` key has a pool plus a compact fallback, and that
  every internal-only key still renders an empty line.
- [x] 1.3 Create `world/skills/narration/families.py` with the family-tier rows (element ×
  shape for elemental magic, line of act for sexual acts, category rows for the remaining
  families) so every ACTIVE skill resolves through
  the chain exact → family → kind pool → compact; verify with a synthetic-registry test that
  each tier step is reachable and that a miss degrades instead of raising.
- [x] 1.4 Declare `PENDING_FAMILIES` as the frozen set of all six ACTIVE families and pin it
  with a test that fails if a family is re-opened; verify the coverage validator accepts the
  shipped catalog with every family pending.
- [x] 1.5 Create `catalog.py` (frozen `NARRATION_CATALOG` aggregate) and `validation.py`
  (coverage against `SHIPPED_SKILL_REGISTRY` and `SEXUAL_ACT_REGISTRY`, unknown/duplicate key
  rejection, per-line and per-composed-pair bound arithmetic, no-digit and placeholder
  allowlist); verify a deleted row, an unknown key, a duplicate key, an over-bound row and a
  digit-bearing row each raise a named error via temp-catalog fixtures.

## 2. Deterministic selection

- [x] 2.1 Implement `select.py`: canonical seed assembly, `zlib.crc32` variant index, band
  resolution from `amount` and the target's max value, composed action-plus-outcome rendering,
  and the actual-rendered-length filter with compact-fallback degradation; verify identical
  seeds select identically, different scopes may differ, and a 300-code-point name still
  produces a line within `MAX_BEAT_TEXT`.
- [x] 2.2 Add the narration scope to the action context contract and supply it from
  `world/rules/combat/rounds.py` (`session_id|round_index|slot_index`) and from the
  out-of-combat settlement path (`field|tick|actor_key`); verify both paths produce distinct
  scopes for distinct actions and that a scope-less context still resolves.

## 3. Pipeline integration

- [x] 3.1 Rewire `_step7_build_event_log` to narrate the built entries (compose the first
  entry's action clause, pool every later entry, emit the single action-narration entry for an
  otherwise-empty successful log) and replace `_ENTRY_TEMPLATES` with the numberless fallbacks;
  verify with a pipeline test that entry kinds, order and numeric data are unchanged, that a
  `damage` line carries no digit while `data["amount"]` is exact, and that an effect-less skill
  renders one action line.
- [x] 3.2 Verify narration consumes no gameplay randomness: patch the dice entry point to raise
  when called from narration, resolve a real cast, and assert success with unchanged hit and
  damage draw counts.
- [x] 3.3 Narrate the non-pipeline combat prose: the end-of-round upkeep tick and defeat lines
  (with `settle_upkeep`'s optional narration scope), the skipped-action line, the party-retreat
  line, the commanded-action marker, and the overwhelm summary (counts leave the prose, stay in
  `data`); verify a damaging upkeep tick's line carries no digit while its entry data keeps the
  amount, and a lopsided engagement's summary line has no digit while its `data` keeps rounds,
  hits and total damage.

## 4. Structural prose

- [x] 4.1 Rewrite `CONTINUE_MESSAGE`, the terminal outcome announcements, and the engagement
  opening as authored lines that name the foe where one exists, keeping each a single stable
  line; verify the engagement opening names the engaged monster and that the round marker is
  reachable as one exported constant used by both the command and adapter paths.
- [x] 4.2 Update the exact-prose test sites listed in design D12 (combat-result, combat-actions,
  command-branch, attribution seam, freeform text commands, quest integration, and the three
  browser modules' closing-line constants) to mechanics assertions or shared constants; verify
  the focused modules pass.
- [x] 4.3 Register the two new `world.rules.tests` modules in exactly one shard of
  `.github/evennia-shards.json` (no entry needed for the new `world.skills.tests` module, which
  the existing `world.skills` label covers) and register the coverage-contract slice in
  `tools/test_data_freeze.json` as a `Data-contract test:` module; verify with
  `python -m tools.contract_gate`.

## 5. Integration verification

- [x] 5.1 Run the focused Python modules (narration catalog, narration selection, pipeline
  narration, combat beats, event log, combat result, combat actions, quest integration) and the
  traceability check; verify every new requirement has a matching annotated test.
- [x] 5.2 Verify the player-visible result by hand: a `cast` of two different skills and one
  resisted sexual act each print skill-specific, numberless prose, and an engaged round prints
  story lines with the round marker and terminal announcement.

## Workflow follow-up

- Archive the change after review and merge, syncing the `action-narration` capability into
  `openspec/specs/`.
