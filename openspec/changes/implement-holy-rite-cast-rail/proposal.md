# Proposal: implement-holy-rite-cast-rail

## Why

The church redemption catalogue grants two ACTIVE skills whose use-surface never
landed (the Series E deferral note in
`openspec/changes/archive/2026-09-23-implement-church-order-catalogue/proposal.md`:
"No player-command surface change … left for a future church rituals/commands
change"). `rite_martial_blessing` and `rite_shelter` have engine APIs
(`cast_martial_blessing` / `apply_shelter_rest`) that only tests call — players
who pay grace for them can never invoke them. Worse, those engine APIs are
undisciplined writers: no transaction, no snapshot/restore, no clock
participation — below the settlement standard every other cast already keeps.
`apply_shelter_rest`'s `shelter_rest_flag` has no reset path anywhere in the
repo: one use and the rite is permanently refused. The approved design
(`docs/superpowers/specs/2026-09-23-holy-rite-cast-rail-design.md` §4–§6)
decides: put both mechanics on the existing cast rail, reuse the
resolver/settlement safety system wholesale, and re-judge `rite_morning_devotion`
as the PASSIVE it actually is.

## What Changes

- New effect grammar + handlers on the existing registry-dispatch seam:
  `rite_blessing:<buff-key>` and bare `rite_shelter` join the closed
  `parse_effect` recognized set (`world/skills/effects.py`), and two new effect
  handlers register in `world/rules/action/effects/church.py` (same home as the
  `session_stamp` handler precedent).
- The church ledger becomes a snapshotted surface: `"church"` joins
  `SNAPSHOTTED_SURFACES` (`battlefield` precedent) and the settlement's
  `_ENTITY_SURFACES`, so every rite write is snapshot/restored by machinery
  that already exists — no new transaction code.
- **BREAKING** (data shape, unreleased project): the cooldown stamp moves from
  `db.martial_blessing_last_tick` into `db.church["blessing_last_tick"]`; the
  shelter flag moves from the root `db.church["shelter_rest_flag"]` into the
  `daily` block (`daily["shelter"]`), so the prayer day-rollover clear resets
  it with zero new reset code. No compat reads, no migrations.
- Four stable reject reasons (`RITE_NOT_ENROLLED`, `RITE_COOLDOWN_ACTIVE`,
  `RITE_OUTSIDE_VENUE`, `RITE_ALREADY_SHELTERED`) join `RejectReason` with their
  fixed zh-TW player lines.
- `rite_morning_devotion` re-judges ACTIVE → PASSIVE: its mechanic is purely
  ownership-triggered (pray daily cap +1); a cast would burn time for nothing.
  The redemption rail already writes grants by kind, so the catalogue row's
  effect is exactly: the cap bonus now rides the passive store.
- Registry rows `rite_martial_blessing` / `rite_shelter` gain their `effects`
  declarations (they live in `holy_rite`, landed by `add-holy-rite-category`).
- **BREAKING** deletions (clean cutover, no shims): `cast_martial_blessing`,
  `apply_shelter_rest`, `MartialBlessingReason`/`Error`, `ShelterReason`/`Error`.
- Observability: one `rite_cast` facade info event at each successful
  settlement boundary, context-carrying (`char`, `rite`, `tick`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-effect-model`: the closed `parse_effect` recognized set grows the two
  rite prefixes with their grammars (typed payload / bare marker, fail-closed).
- `battlefield-commit-surface`: `SNAPSHOTTED_SURFACES` gains the `"church"`
  surface (adding a surface extends the snapshot inventory, not the mechanism).
- `cast-settlement-atomicity`: the settlement snapshot/restore enumeration
  covers the actor's `church` ledger attribute.
- `action-resolution-pipeline`: four new stable `RejectReason` values with
  zh-TW player-message lines, raised by the two rite handlers' gates.
- `church-ordination`: the ledger requirement re-pins its shape (ledger keys
  `blessing_last_tick`, `daily.{day, pray, shelter}`; the single-writer audit
  stays — handler-staged writes execute inside `world/rules/church.py`
  mutators); the Series E requirement re-pins both rites as cast-rail
  mechanics with their stable rejections, day-block reset, and rollback
  promise, and `rite_morning_devotion` as PASSIVE.

## Impact

- Code: `world/skills/effects.py` (grammar), `world/rules/action/contracts.py`
  (`RejectReason`), `world/rules/action/effects/church.py` (two handlers),
  `world/rules/action/` surfaces constant, `world/rules/cast_settlement.py`
  (`_ENTITY_SURFACES`), `world/rules/church.py` (mutators in, engine APIs out),
  `world/rules/player_messages.py` (four lines),
  `world/skills/registry/data_church.py` (two `effects=` additions, one kind
  swap), `world/lore/church/` redemption row (morning devotion grant kind).
- Tests: `world/rules/tests/test_church_rulebook.py` Series E block re-anchors
  to the resolver face (cooldown, venue, same-day, day-rollover, rollback
  proofs); `skill-effect-model` grammar tests gain the rite prefixes;
  classification/panel anchors for the morning-devotion kind swap; the
  observability lint stays green (`rite_cast` event).
- Traceability: the `church-ordination::series-e-utility-rows-feed-the-core-loop`
  and `church-ordination::merit-ledger-is-persisted-character-state-with-a-single-writer`
  requirement anchors move to the new cast-behaviour tests.
- No player-command surface change (the `cast` command is already documented);
  the docs trio and `tests/test_command_docs.py` are untouched.
- Depends on: `add-holy-rite-category` (rows must already live in `holy_rite`).
